"""Descobrir a hora de cada palavra escutando SÓ os trechos que viraram corte.

O PROBLEMA
----------
O editor pediu, corte a corte:

    "o corte 18 deveria começar em 0:25, em 'candidato'"

Para encostar a borda em "candidato" o programa precisa saber em que segundo
essa palavra começa. Quem escuta o áudio produz isso; um texto colado à mão,
não — e não tem como produzir, porque a informação nunca existiu ali.

Medido no banco dele: de 26 transcrições guardadas, 21 são texto colado. Ou
seja, no material que ele mais moe a borda nunca teve como ser acertada.

A SAÍDA
-------
Escutar o vídeo inteiro de novo custaria dezenas de minutos numa fonte de 1h30
e desperdiçaria quase tudo: só as bordas dos cortes interessam.

Então escutamos apenas as janelas que já viraram corte, com uma folga de cada
lado para a palavra da borda cair dentro. Numa moagem típica são vinte janelas
de um a dois minutos — minutos, não dezenas deles.

O QUE ESTE MÓDULO NÃO FAZ
-------------------------
Não reescreve a transcrição dele. O texto continua sendo o que ele colou; daqui
sai só o relógio das palavras. Um texto colado é o julgamento dele sobre o que
foi dito, e trocá-lo por uma segunda opinião da máquina seria desfazer trabalho
que ele já fez.
"""

import os
import subprocess
import tempfile


# Folga de cada lado da janela. A palavra que abre o corte costuma começar um
# pouco antes do segundo pedido, e sem folga ela sai cortada ao meio — que é
# exatamente o defeito que viemos consertar.
FOLGA_S = 3.0

# Abaixo disto não vale acordar o reconhecedor: a janela é curta demais para
# render palavra útil e o custo fixo domina.
JANELA_MINIMA_S = 1.0

# Teto de janelas por moagem. Vinte cortes com folga já é o caso normal; muito
# além disso alguma coisa está errada e o editor ficaria esperando sem saber
# por quê.
MAXIMO_DE_JANELAS = 60


def _juntar_janelas(intervalos, folga=FOLGA_S):
    """Une janelas que se tocam depois da folga, para não escutar duas vezes."""
    limpos = []
    for item in intervalos or []:
        try:
            inicio = float(item[0])
            fim = float(item[1])
        except (TypeError, ValueError, IndexError):
            continue
        if fim <= inicio:
            continue
        limpos.append((max(0.0, inicio - folga), fim + folga))

    limpos.sort()
    juntos = []
    for inicio, fim in limpos:
        if juntos and inicio <= juntos[-1][1]:
            juntos[-1] = (juntos[-1][0], max(juntos[-1][1], fim))
        else:
            juntos.append((inicio, fim))
    return [(a, b) for a, b in juntos if b - a >= JANELA_MINIMA_S]


def _extrair_audio(caminho_da_midia, inicio, fim, destino):
    """Tira um pedaço de áudio do vídeo, em mono 16 kHz — o que o motor quer."""
    comando = [
        "ffmpeg", "-y", "-loglevel", "error",
        "-ss", f"{inicio:.3f}",
        "-to", f"{fim:.3f}",
        "-i", str(caminho_da_midia),
        "-vn", "-ac", "1", "-ar", "16000",
        "-c:a", "pcm_s16le",
        str(destino),
    ]
    subprocess.run(comando, check=True, capture_output=True, timeout=300)
    return destino


def palavras_das_janelas(caminho_da_midia, intervalos, transcriber,
                         emit_progress=None):
    """A hora de cada palavra dentro das janelas pedidas.

    Devolve uma lista de {"start", "end", "word"} em segundos do vídeo
    original — o deslocamento da janela já somado.

    Nunca levanta por causa do áudio: se o ffmpeg ou o reconhecedor falharem
    numa janela, essa janela fica sem palavras e as outras seguem. Bordas
    melhores são um ganho; perder a moagem inteira por causa delas não.
    """
    if not caminho_da_midia or not os.path.isfile(caminho_da_midia):
        return []

    janelas = _juntar_janelas(intervalos)[:MAXIMO_DE_JANELAS]
    if not janelas:
        return []

    if emit_progress:
        total = sum(fim - inicio for inicio, fim in janelas)
        emit_progress(
            f"[Bordas] Escutando {len(janelas)} trecho(s) "
            f"({total / 60:.1f} min) só para achar a hora de cada palavra.",
            "info",
        )

    palavras = []
    with tempfile.TemporaryDirectory(prefix="furia-bordas-") as pasta:
        for numero, (inicio, fim) in enumerate(janelas, start=1):
            pedaco = os.path.join(pasta, f"janela-{numero}.wav")
            try:
                _extrair_audio(caminho_da_midia, inicio, fim, pedaco)
                resultado = transcriber.transcribe(pedaco)
            except (subprocess.SubprocessError, OSError, ValueError, RuntimeError) as erro:
                if emit_progress:
                    emit_progress(
                        f"[Bordas] Trecho {numero} não pôde ser escutado "
                        f"({str(erro)[:80]}); as bordas dele ficam como estão.",
                        "warning",
                    )
                continue

            for segmento in (resultado or {}).get("segments") or []:
                if not isinstance(segmento, dict):
                    continue
                for palavra in segmento.get("words") or []:
                    if not isinstance(palavra, dict):
                        continue
                    try:
                        comeco = float(palavra.get("start"))
                        acaba = float(palavra.get("end"))
                    except (TypeError, ValueError):
                        continue
                    texto = str(palavra.get("word") or "").strip()
                    if acaba <= comeco or not texto:
                        continue
                    palavras.append({
                        "start": comeco + inicio,
                        "end": acaba + inicio,
                        "word": texto,
                    })

    palavras.sort(key=lambda item: (item["start"], item["end"]))
    if emit_progress:
        if palavras:
            emit_progress(f"[Bordas] {len(palavras)} palavra(s) com hora certa.", "info")
        else:
            emit_progress(
                "[Bordas] Nenhuma palavra veio com hora; as bordas ficam como estão.",
                "warning",
            )
    return palavras
