"""Olhar o corte pronto antes de entregar: tela preta, silêncio, som fora do lugar.

O QUE JÁ ERA CONFERIDO, E O QUE PASSAVA
----------------------------------------
`validate_media` confere o arquivo pelos METADADOS: duração bate, resolução
bate, existe uma faixa de vídeo, existe uma faixa de áudio.

Existir uma faixa de áudio não é o mesmo que ter som. Um corte inteiramente
mudo tem faixa de áudio, passa na conferência e é entregue. O mesmo vale para
uma tela preta: um trecho onde a transmissão caiu tem faixa de vídeo.

O relatório do estudo que o editor mandou lista exatamente isto na etapa de QA:
"ausência de frames pretos, congelamentos e silêncio inesperado".

O QUE ESTE ARQUIVO FAZ E NÃO FAZ
--------------------------------
Faz uma passada de ffmpeg com dois detectores ligados ao mesmo tempo, sem
gravar nada. Não reprova nada sozinho: **avisa**. Um corte de manifesto com
cinco segundos de silêncio dramático é bom, e quem decide é o editor.

Nunca levanta. Ffmpeg ausente, corte ilegível ou detector que não roda devolvem
"não deu para conferir" — porque perder um corte bom por causa da conferência é
pior do que entregar um corte para ele olhar.
"""

from __future__ import annotations

import re
import subprocess

# Quanto de tela preta ou de silêncio já merece aviso. Meio segundo de preto é
# transição; três segundos é defeito. Silêncio é mais tolerante: pausa é fala.
PRETO_MINIMO_S = 1.5
SILENCIO_MINIMO_S = 3.0

# Abaixo disto o áudio é considerado silêncio, em decibéis. -45 dB deixa passar
# respiração e ruído de rua, e pega faixa de áudio de verdade vazia.
SILENCIO_EM_DB = -45

_PRETO = re.compile(r"black_start:([\d.]+)\s+black_end:([\d.]+)")
_SILENCIO_INICIO = re.compile(r"silence_start:\s*([\d.-]+)")
_SILENCIO_FIM = re.compile(r"silence_end:\s*([\d.]+)")


def _intervalos_de_silencio(saida: str) -> list[tuple[float, float]]:
    """Os pares início/fim que o ffmpeg imprime em linhas separadas."""
    inicios = [float(valor) for valor in _SILENCIO_INICIO.findall(saida)]
    fins = [float(valor) for valor in _SILENCIO_FIM.findall(saida)]
    return [(max(0.0, comeco), fim) for comeco, fim in zip(inicios, fins)]


def conferir(caminho: str, duracao_s: float = 0.0, *, timeout: int = 120) -> dict:
    """O que há de errado com este arquivo, em português.

    Devolve sempre um dicionário: `conferido` diz se a conferência rodou, e
    `avisos` traz uma frase por problema, prontas para a tela.
    """
    resultado = {"conferido": False, "avisos": [], "preto_s": 0.0, "silencio_s": 0.0}
    if not caminho:
        return resultado

    comando = [
        "ffmpeg", "-hide_banner", "-nostats", "-i", str(caminho),
        "-vf", f"blackdetect=d={PRETO_MINIMO_S}:pix_th=0.10",
        "-af", f"silencedetect=n={SILENCIO_EM_DB}dB:d={SILENCIO_MINIMO_S}",
        "-f", "null", "-",
    ]
    try:
        processo = subprocess.run(comando, capture_output=True, text=True,
                                  timeout=timeout, check=False)
    except (OSError, subprocess.SubprocessError):
        return resultado

    saida = (processo.stderr or "") + (processo.stdout or "")
    resultado["conferido"] = True

    pretos = [(float(a), float(b)) for a, b in _PRETO.findall(saida)]
    silencios = _intervalos_de_silencio(saida)
    resultado["preto_s"] = round(sum(fim - inicio for inicio, fim in pretos), 2)
    resultado["silencio_s"] = round(sum(fim - inicio for inicio, fim in silencios), 2)

    if pretos:
        maior = max(fim - inicio for inicio, fim in pretos)
        resultado["avisos"].append(
            f"{len(pretos)} trecho(s) de tela preta, o maior de {maior:.1f}s"
        )
    if silencios:
        maior = max(fim - inicio for inicio, fim in silencios)
        resultado["avisos"].append(
            f"{len(silencios)} trecho(s) sem som, o maior de {maior:.1f}s"
        )

    # O caso grave, e o que o editor de fato vê: o corte inteiro mudo, ou
    # inteiro preto. Aqui não é um aviso entre outros — é um corte que não
    # existe, e precisa aparecer com essas palavras.
    if duracao_s > 0:
        if resultado["silencio_s"] >= duracao_s * 0.95:
            resultado["avisos"].append("ESTE CORTE ESTÁ MUDO DO COMEÇO AO FIM")
        if resultado["preto_s"] >= duracao_s * 0.95:
            resultado["avisos"].append("ESTE CORTE ESTÁ PRETO DO COMEÇO AO FIM")

    return resultado
