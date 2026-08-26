"""FURIA 2 — o servidor da bancada.

O motor do Furia 1 (transcrição, análise, seleção, corte) entra depois que as
telas estiverem aprovadas — ele já foi conferido e importa sozinho, sem
depender de nada da interface velha. Enquanto isso, o que existe aqui é o que
cada tela aprovada precisa para ser VERDADE em vez de maquete: a fonte lista
os vídeos que estão mesmo no disco dele, com o quadro de verdade de cada um.

Roda na porta 5001 de propósito: o Furia 1 roda na 5000, e a combinação foi os
dois abertos lado a lado, para comparar.
"""

import json
import os
import subprocess
import sys
import uuid
from pathlib import Path

from flask import Flask, abort, jsonify, render_template, request, send_file

# O Furia 2 mora dentro do repositório do Furia 1 para poder usar as peças que
# já funcionam sem copiá-las. Nada da interface velha é importado aqui — só
# caminhos, segurança de caminho e as duas funções de fonte.
RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))

from config import ALLOWED_EXTENSIONS, WORKSPACE_DIR
from modules.native_dialogs import DialogError, choose_path
from modules.security import UnsafePathError, safe_workspace_path
from modules.source_ingest import SourceIngestError, probe_public_url

PORTA = 5001

# Os quadros que o programa arranca dos vídeos ficam aqui. Fora do
# repositório, ao lado dos outros dados dele, porque são derivados: dá para
# apagar a pasta inteira a qualquer momento e o programa refaz.
CACHE = Path.home() / "FuriaClipsData" / "furia2" / "quadros"

# Fontes que ele escolheu na janela do Windows nesta sessão. Um arquivo fora do
# workspace só entra aqui depois de ele mesmo apontar para ele numa caixa de
# diálogo do sistema — e some quando o programa fecha. É a única forma de
# mostrar o quadro de um vídeo que não mora na pasta de trabalho sem abrir a
# máquina inteira para leitura.
DE_FORA = {}

# Onde a rodada deixa a folha de decisões. É a mesma pasta que o Furia 1 já
# usa, e ela fica FORA do repositório de propósito: a folha carrega a
# transcrição do material, e transcrição de coisa não publicada não entra em
# pasta versionada.
DIAGNOSTICOS = Path(
    os.environ.get("FURIA_CLIPS_DATA_DIR") or (Path.home() / "FuriaClipsData")
) / "diagnostics"

app = Flask(
    __name__,
    template_folder=str(Path(__file__).parent / "templates"),
    static_folder=str(Path(__file__).parent / "static"),
)


# ── ler o que existe no disco ───────────────────────────────────────────────


def _segundos(caminho):
    """Quanto tempo o vídeo tem. Zero quando não dá para saber."""
    try:
        saida = subprocess.run(
            ["ffprobe", "-v", "error", "-show_entries", "format=duration",
             "-of", "json", str(caminho)],
            capture_output=True, text=True, timeout=20, check=False,
        )
        return float(json.loads(saida.stdout or "{}").get("format", {}).get("duration") or 0)
    except (OSError, ValueError, subprocess.SubprocessError):
        return 0.0


def _ficha(caminho, chave):
    tamanho = caminho.stat().st_size if caminho.exists() else 0
    return {
        "chave": chave,
        "nome": caminho.name,
        "segundos": round(_segundos(caminho), 2),
        "bytes": tamanho,
        "modificado": caminho.stat().st_mtime if caminho.exists() else 0,
    }


@app.route("/api/fonte/lista")
def api_fonte_lista():
    """Os vídeos que já estão na pasta de trabalho.

    Varre as subpastas: ele guarda material em pastas por entrevista, e listar
    só a raiz mostraria uma pasta vazia para quem tem trinta vídeos.

    Fonte é ENTRADA. As pastas de saída ficam de fora, e não é detalhe: a
    primeira leitura desta rota, com o disco de verdade, devolveu 114 cortes já
    exportados misturados com 5 fontes. Um mural com os cortes de ontem dentro
    dele não é uma lista de fontes — é um lugar onde ele reconhece o próprio
    trabalho e não acha o vídeo que veio buscar.
    """
    raiz = Path(WORKSPACE_DIR)
    entradas = [raiz / "uploads", raiz / "input", raiz]
    achados = []
    vistos = set()
    for pasta in entradas:
        if not pasta.is_dir():
            continue
        # A raiz entra sem descer: descer dela seria varrer tudo de novo,
        # inclusive as pastas de saída que acabamos de deixar de fora.
        candidatos = pasta.glob("*") if pasta == raiz else pasta.rglob("*")
        for caminho in candidatos:
            if not caminho.is_file() or caminho.suffix.lower() not in ALLOWED_EXTENSIONS:
                continue
            relativo = str(caminho.relative_to(raiz))
            if relativo in vistos:
                continue
            vistos.add(relativo)
            achados.append(_ficha(caminho, relativo))
    # O mais recente primeiro: o vídeo que ele acabou de baixar é quase sempre
    # o que ele quer cortar agora.
    achados.sort(key=lambda f: f["modificado"], reverse=True)
    for ficha in achados:
        ficha.pop("modificado", None)
    return jsonify({"fontes": achados, "de_fora": list(DE_FORA.values())})


def _resolver(chave):
    """De uma chave da lista para um arquivo de verdade, sem sair do permitido."""
    if chave in DE_FORA:
        caminho = Path(DE_FORA[chave]["caminho"])
    else:
        try:
            caminho = Path(safe_workspace_path(WORKSPACE_DIR, chave, allow_missing=False))
        except (UnsafePathError, FileNotFoundError):
            abort(404)
    # Tem de ser ARQUIVO. Uma chave vazia resolve para a própria pasta de
    # trabalho, que existe — e daí o ffmpeg seria chamado em cima de uma pasta.
    if not caminho.is_file():
        abort(404)
    return caminho


@app.route("/api/fonte/quadro")
def api_fonte_quadro():
    """Um quadro do vídeo, para ele escolher a fonte OLHANDO em vez de lendo.

    Arrancado com o ffmpeg um décimo adiante do começo: no zero quase toda
    entrevista está preta ou na vinheta, e um mural de retângulos pretos não
    ajuda ninguém a reconhecer nada.
    """
    caminho = _resolver(request.args.get("chave", ""))
    CACHE.mkdir(parents=True, exist_ok=True)
    try:
        assinatura = f"{caminho}|{caminho.stat().st_mtime_ns}|{caminho.stat().st_size}"
    except OSError:
        abort(404)
    destino = CACHE / (uuid.uuid5(uuid.NAMESPACE_URL, assinatura).hex + ".jpg")

    if not destino.exists():
        dur = _segundos(caminho)
        subprocess.run(
            ["ffmpeg", "-v", "error", "-ss", f"{max(0.5, dur * 0.1):.2f}",
             "-i", str(caminho), "-frames:v", "1", "-vf", "scale=440:-2",
             "-q:v", "4", "-y", str(destino)],
            capture_output=True, timeout=60, check=False,
        )
    if not destino.exists():
        # Sem quadro a fonte ainda aparece na lista, só que sem foto. Vídeo que
        # o ffmpeg não abre é exatamente o que ele precisa ver na lista para
        # descobrir que está corrompido.
        abort(404)
    return send_file(destino, mimetype="image/jpeg", max_age=86400)


# ── trazer material novo ────────────────────────────────────────────────────


@app.route("/api/fonte/escolher", methods=["POST"])
def api_fonte_escolher():
    """A janela do Windows. Ele nunca vai digitar um caminho."""
    try:
        escolhido = choose_path(mode="file", title="Escolher a fonte")
    except (DialogError, OSError, subprocess.SubprocessError) as erro:
        return jsonify({"ok": False, "erro": str(erro)}), 500
    if not escolhido:
        return jsonify({"ok": True, "desistiu": True})

    caminho = Path(escolhido).resolve()
    if caminho.suffix.lower() not in ALLOWED_EXTENSIONS:
        return jsonify({"ok": False, "erro": f"{caminho.suffix} não é vídeo"}), 400

    chave = "fora:" + uuid.uuid5(uuid.NAMESPACE_URL, str(caminho)).hex
    ficha = _ficha(caminho, chave)
    ficha["caminho"] = str(caminho)
    DE_FORA[chave] = ficha
    return jsonify({"ok": True, "desistiu": False, "fonte": ficha})


@app.route("/api/fonte/ler-link", methods=["POST"])
def api_fonte_ler_link():
    """Ler o link ANTES de baixar.

    Baixar uma entrevista de duas horas para descobrir que era o vídeo errado
    é meia hora perdida. Isto só lê o cabeçalho: nome, duração e canal.
    """
    dados = request.get_json(silent=True) or {}
    try:
        return jsonify({"ok": True, "fonte": probe_public_url(str(dados.get("link", "")).strip())})
    except SourceIngestError as erro:
        return jsonify({"ok": False, "erro": str(erro)}), 400


# ── a parede: os cortes que saíram ──────────────────────────────────────────


def _folha_da_rodada():
    """A folha de decisões mais recente, e o vídeo de onde ela saiu.

    Devolve `(dados, caminho_da_fonte_ou_None)`. A fonte é procurada pelo nome
    que a própria folha guarda: quem cortou foi outra máquina — a dele — e o
    nome do arquivo é a única ponte entre a decisão e a imagem.
    """
    if not DIAGNOSTICOS.is_dir():
        return None, None
    folhas = sorted(DIAGNOSTICOS.glob("selecao-*.json"), key=lambda p: p.stat().st_mtime, reverse=True)
    if not folhas:
        return None, None
    try:
        dados = json.loads(folhas[0].read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None, None

    nome = str((dados.get("fonte") or {}).get("arquivo") or "")
    fonte = None
    if nome:
        for achado in Path(WORKSPACE_DIR).rglob(nome):
            if achado.is_file():
                fonte = achado
                break
    return dados, fonte


def _corte_para_a_tela(bruto, numero):
    """O que a parede precisa de cada corte, e só isso.

    A folha guarda vinte e quatro campos por corte. A parede mostra sete. Os
    outros são do talho e do painel — mandar tudo para cá seria construir a
    tentação de encher a tela com número que não muda decisão nenhuma.
    """
    inicio = float(bruto.get("start_s") or 0)
    fim = float(bruto.get("end_s") or 0)
    return {
        "n": numero,
        "inicio": round(inicio, 2),
        "fim": round(fim, 2),
        "duracao": round(float(bruto.get("duration_s") or max(0.0, fim - inicio)), 2),
        # `review_required` é o único campo daqui que acende vermelho, e ele é
        # a razão de o vermelho existir: é o corte que pede o olho dele antes
        # de ir para o ar.
        "conferir": bool(bruto.get("review_required")),
        "motivos": [str(m) for m in (bruto.get("review_reasons") or [])][:4],
        "fala": " ".join(str(bruto.get("texto") or "").split()),
        "origem": str(bruto.get("origem") or ""),
    }


@app.route("/api/cortes/lista")
def api_cortes_lista():
    dados, fonte = _folha_da_rodada()
    if not dados:
        return jsonify({"ok": True, "tem_rodada": False, "cortes": []})

    cortes = [_corte_para_a_tela(c, i + 1) for i, c in enumerate(dados.get("cortes_renderizados") or [])]
    diagnostico = (dados.get("selecao") or {}).get("diagnostico") or {}
    conferir = sum(1 for c in cortes if c["conferir"])

    return jsonify({
        "ok": True,
        "tem_rodada": True,
        "fonte": {
            "nome": str((dados.get("fonte") or {}).get("arquivo") or ""),
            "segundos": float((dados.get("fonte") or {}).get("duracao_s") or 0),
            # Se o vídeo não está nesta máquina a parede continua de pé, só
            # sem os quadros. A decisão é o que importa; a imagem é conforto.
            "achada": fonte is not None,
        },
        "cortes": cortes,
        "resumo": {
            "entregues": len(cortes),
            "conferir": conferir,
            "descartados_por_sobreposicao": int(diagnostico.get("fallback_discarded_overlap") or 0),
            "recusados": int(diagnostico.get("hard_negative_count") or 0),
        },
    })


@app.route("/api/cortes/quadro")
def api_cortes_quadro():
    """O quadro de um corte, arrancado no comecinho dele.

    Dois segundos depois do início, e não no início exato: o primeiro quadro de
    um corte cai muitas vezes num piscar de olho ou numa troca de câmera, e um
    mural de gente de olho fechado não ajuda a reconhecer nada.
    """
    dados, fonte = _folha_da_rodada()
    if not dados or fonte is None:
        abort(404)
    try:
        numero = int(request.args.get("n", "0"))
    except ValueError:
        abort(404)
    cortes = dados.get("cortes_renderizados") or []
    if not 1 <= numero <= len(cortes):
        abort(404)

    inicio = float(cortes[numero - 1].get("start_s") or 0)
    CACHE.mkdir(parents=True, exist_ok=True)
    assinatura = f"{fonte}|{fonte.stat().st_mtime_ns}|corte|{inicio:.2f}"
    destino = CACHE / (uuid.uuid5(uuid.NAMESPACE_URL, assinatura).hex + ".jpg")

    if not destino.exists():
        subprocess.run(
            ["ffmpeg", "-v", "error", "-ss", f"{inicio + 2:.2f}",
             "-i", str(fonte), "-frames:v", "1", "-vf", "scale=480:-2",
             "-q:v", "4", "-y", str(destino)],
            capture_output=True, timeout=60, check=False,
        )
    if not destino.exists():
        abort(404)
    return send_file(destino, mimetype="image/jpeg", max_age=86400)


# ── a bancada ───────────────────────────────────────────────────────────────


@app.route("/")
def bancada():
    return render_template("bancada.html")


if __name__ == "__main__":
    print(f"Furia 2 — bancada em http://127.0.0.1:{PORTA}")
    # 127.0.0.1 e não 0.0.0.0: o programa é da máquina dele e não tem por que
    # ficar escutando a rede da casa.
    app.run(host="127.0.0.1", port=PORTA, debug=False)
