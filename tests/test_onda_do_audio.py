"""A onda de áudio: o dado que faltava para o corte deixar de ser um número.

O ajuste de corte eram dois campos em segundos absolutos da fonte, "300.0" e
"800.0". O editor: "não sabia o que eu estava medindo, não sabia onde era o
início que eu queria porque o próprio corte não permitia voltar, e eu sequer
sabia se eram segundos".

Som se edita olhando para o som. Este é o desenho.

O primeiro formato que eu escrevi era pico por fatia, e desenhei antes de
entregar: saiu um bloco retangular. Com milhares de amostras por fatia, quase
toda fatia contém algum estalo alto, e o pico satura. Energia média mostra o
contorno da fala — sílaba, pausa, respiração — que é o que os olhos usam para
achar a borda de uma frase.
"""

import subprocess
import wave
from pathlib import Path

import numpy as np
import pytest

import app as aplicacao

# Onde a fala existe neste sinal de teste, e onde há silêncio entre elas.
# Volumes diferentes de propósito: fala real não tem altura constante, e é a
# variação dentro da fala que prova que o desenho não achatou tudo no teto.
FALAS = [(1.0, 4.5, 0.85), (5.2, 9.0, 0.45), (12.0, 18.0, 0.9), (23.0, 29.0, 0.20)]
PAUSAS = [(0.0, 0.9), (4.6, 5.1), (9.1, 11.9), (18.1, 19.4), (29.1, 30.0)]


@pytest.fixture(scope="module")
def fonte(tmp_path_factory):
    """Fala sintética: rajadas moduladas em sílabas, com pausas medidas."""
    destino = tmp_path_factory.mktemp("onda")
    taxa, duracao = 16000, 30
    t = np.arange(taxa * duracao) / taxa
    sinal = np.zeros_like(t)
    sorteio = np.random.default_rng(7)
    for inicio, fim, volume in FALAS:
        dentro = (t >= inicio) & (t < fim)
        silabas = 0.6 + 0.4 * np.sin(2 * np.pi * 4 * t[dentro])
        sinal[dentro] = sorteio.normal(0, volume, dentro.sum()) * silabas
    som = destino / "fala.wav"
    with wave.open(str(som), "wb") as arquivo:
        arquivo.setnchannels(1)
        arquivo.setsampwidth(2)
        arquivo.setframerate(taxa)
        arquivo.writeframes((np.clip(sinal, -1, 1) * 32767).astype("<i2").tobytes())

    video = destino / "fala.mp4"
    subprocess.run(
        ["ffmpeg", "-y", "-loglevel", "error", "-f", "lavfi",
         "-i", f"color=c=black:s=320x240:d={duracao}", "-i", str(som),
         "-shortest", "-pix_fmt", "yuv420p", str(video)],
        check=True,
    )
    return video


@pytest.fixture
def pedir(fonte, monkeypatch):
    monkeypatch.setattr(aplicacao, "_resolve_media_input", lambda pedido: str(fonte) if pedido else None)

    def chamar(**parametros):
        consulta = "&".join(f"{chave}={valor}" for chave, valor in
                            {"video_path": str(fonte), **parametros}.items())
        return aplicacao.app.test_client().get(f"/api/waveform?{consulta}")
    return chamar


def test_a_onda_distingue_fala_de_silencio(pedir):
    """O teste que importa: a forma tem que dizer onde a frase começa."""
    resposta = pedir(start=0, end=30, buckets=300)
    assert resposta.status_code == 200
    picos = resposta.get_json()["peaks"]
    assert len(picos) == 300

    def media(de, ate):
        return float(np.mean(picos[int(de / 30 * 300):max(int(ate / 30 * 300), int(de / 30 * 300) + 1)]))

    for inicio, fim, _ in FALAS:
        for silencio_de, silencio_ate in PAUSAS:
            assert media(inicio, fim) > media(silencio_de, silencio_ate) * 2, (
                f"a fala {inicio}-{fim}s não se destaca da pausa {silencio_de}-{silencio_ate}s"
            )


def test_a_onda_nao_satura(pedir):
    """O defeito da primeira versão: pico por fatia devolvia tudo no teto.

    Desenhado em texto, saiu um retângulo cheio — bonito de código e inútil de
    usar. A prova de que não voltou é a fala ALTA se separar da fala BAIXA: se o
    desenho achatar, as quatro rajadas viram a mesma altura e o editor perde a
    informação que ele usa para achar a frase.

    Medir a mediana do trecho inteiro não serviria: num sinal onde a fala ocupa
    a maior parte do tempo, ela sobe por motivo legítimo. Foi o que essa asserção
    fazia antes, e ela reprovava um código correto.
    """
    picos = np.array(pedir(start=0, end=30, buckets=300).get_json()["peaks"])
    assert picos.max() == pytest.approx(1.0, abs=0.001)
    assert picos.min() < 0.2

    def media(de, ate):
        return float(picos[int(de / 30 * 300):int(ate / 30 * 300)].mean())

    alta = media(12.0, 18.0)   # volume 0,90
    media_ = media(5.2, 9.0)   # volume 0,45
    baixa = media(23.0, 29.0)  # volume 0,20
    assert alta > media_ > baixa, f"as alturas se achataram: {alta:.2f} / {media_:.2f} / {baixa:.2f}"
    assert alta - baixa > 0.2, "a diferença entre fala alta e baixa quase sumiu"


def test_a_margem_de_fora_do_corte_pode_ser_pedida(pedir):
    """A queixa central era não conseguir voltar.

    Para escolher onde entrar é preciso ver e ouvir a frase anterior, então a
    janela pedida é sempre maior que o corte.
    """
    resposta = pedir(start=7, end=23, buckets=120)
    corpo = resposta.get_json()
    assert corpo["start"] == 7 and corpo["end"] == 23
    assert len(corpo["peaks"]) == 120


def test_intervalo_invalido_e_recusado_com_explicacao(pedir):
    for parametros in ({"start": 10, "end": 10}, {"start": 20, "end": 5}):
        resposta = pedir(**parametros)
        assert resposta.status_code == 400
        assert "depois" in resposta.get_json()["error"]


def test_janela_absurda_e_recusada(pedir):
    """Meia hora de áudio já é mais do que qualquer tela consegue mostrar."""
    resposta = pedir(start=0, end=4000)
    assert resposta.status_code == 400
    assert "30 minutos" in resposta.get_json()["error"]


def test_video_inexistente_nao_derruba_o_programa():
    resposta = aplicacao.app.test_client().get("/api/waveform?video_path=/nao/existe.mp4&start=0&end=5")
    assert resposta.status_code == 404


def test_o_numero_de_fatias_fica_dentro_de_limites_uteis(pedir):
    assert len(pedir(start=0, end=30, buckets=1).get_json()["peaks"]) == 40
    assert len(pedir(start=0, end=30, buckets=99999).get_json()["peaks"]) == 1200
