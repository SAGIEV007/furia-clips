"""O ESTÚDIO — a interface do editor, ligada no motor que já existia.

Ele mandou o `furiastudiofinal_1.zip` e disse: *"Você pode usar apenas essa a
partir de agora ok? não precisa por hora criar mais nada a não ser que seja
necessário, só adapte tudo o que já funcionava aqui antes, console, blocos,
etc..."*

O que veio no zip é uma casa bonita com um motor de brinquedo dentro. O motor
dele escolhia os cortes assim: pegava as oito primeiras faixas com som, dava a
cada uma um título tirado de uma lista de oito frases prontas, e calculava a
nota a partir da duração e da posição na fila. Isso não é seleção — é enfeite
com cara de seleção, e é a coisa mais cara que pode existir num programa de
corte, porque parece que funcionou.

Então a casa fica e o motor de brinquedo vai fora. O que roda por baixo é o
motor de sempre: transcrição, Gemini, CHUB, blocos, seleção, ranqueamento,
corte, legenda, SEO, render. Nada foi copiado para cá e nada foi reescrito lá.

Este arquivo é curto de propósito. Quase tudo que o estúdio precisa já era uma
rota do programa, e a regra aqui foi: se a rota existe, o estúdio chama a rota.
As poucas que moram aqui são as que ninguém tinha ainda — juntar a fonte no
disco com a rodada que saiu dela, e traduzir o corte do motor para o formato
que a tela dele desenha.

    /             o estúdio            (esta interface)
    /classico     a interface antiga   (existe, não é ligada em lugar nenhum)
    /2            a bancada            (continua de pé, mesmo motor)
"""

import json
import os
import subprocess
import sys
from pathlib import Path
from urllib.parse import quote

from flask import Blueprint, jsonify, render_template

RAIZ = Path(__file__).resolve().parent.parent
if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))

from config import ALLOWED_EXTENSIONS, WORKSPACE_DIR
from database import get_all_projects, get_clips, get_project, get_transcription

estudio = Blueprint(
    "estudio",
    __name__,
    template_folder=str(Path(__file__).parent / "templates"),
    static_folder=str(Path(__file__).parent / "static"),
    static_url_path="/estudio",
)


# ── por que este corte entrou ───────────────────────────────────────────────

# O motor devolve as notas por fator com nome de código em inglês. A tela dele é
# em português e ele não lê código, então a tradução acontece aqui — uma vez, no
# lugar que já tem o número na mão, em vez de espalhada pelo JavaScript.
#
# São frases de ofício, não adjetivos: "abre com gancho" diz o que aconteceu no
# material; "hook 78" não diz nada para quem vai decidir se corta.
MOTIVOS = {
    "hook": "abre com gancho",
    "flow": "fala sem tropeço",
    "value": "tem conteúdo",
    "clarity": "ideia clara",
    "completeness": "fecha o raciocínio",
    "argument_structure": "argumento inteiro",
    "audio_energy": "voz com energia",
    "context_match": "bate com o que você pediu",
    "context_quality": "contexto suficiente",
    "duration_fit": "duração publicável",
    "visual_change_density": "imagem muda",
    "speaker_boundary": "não corta a fala de outro",
    "qa_boundary": "pergunta e resposta inteiras",
    "chapter_coherence": "um assunto só",
    "contextual_hook_alignment": "gancho no lugar certo",
    "campaign_hub_prior": "parece com o que já rendeu",
    "campaign_hub_block_evidence": "tem bloco parecido no acervo",
    "instagram_pattern_prior": "formato conhecido de Reels",
    "editor_feedback_alignment": "parecido com o que você aprovou",
    "feedback_reason_alignment": "evita o que você recusou",
}

# Abaixo disto o fator não é motivo de nada: 50 é o meio da régua do motor.
BOM = 62.0


def _motivos(fatores):
    """Os três fatores mais fortes deste corte, em português.

    Três, não todos: uma lista de vinte razões é uma lista que ninguém lê, e a
    quarta razão nunca mudou uma decisão de corte.
    """
    if not isinstance(fatores, dict):
        return []
    fortes = [
        (nome, valor) for nome, valor in fatores.items()
        if nome in MOTIVOS and isinstance(valor, (int, float))
        and not isinstance(valor, bool) and float(valor) >= BOM
    ]
    fortes.sort(key=lambda par: -float(par[1]))
    return [MOTIVOS[nome] for nome, _ in fortes[:3]]


def _titulo(corte):
    """O nome do corte na tela.

    Primeiro o que o motor sugeriu; se não sugeriu, a primeira frase da própria
    fala. Nunca um texto inventado aqui: a tela dele mostra o material, e um
    título genérico ("O melhor recorte desta fonte") faz onze cortes ficarem
    iguais na hora de escolher — que era o defeito do estúdio que ele mandou.
    """
    try:
        titulos = json.loads(corte.get("suggested_titles") or "[]")
        if isinstance(titulos, list) and titulos:
            return str(titulos[0])[:140]
    except (TypeError, ValueError, json.JSONDecodeError):
        pass
    fala = str(corte.get("transcript") or "").strip()
    if not fala:
        return "corte sem transcrição"
    for fim in (". ", "? ", "! "):
        pedaco = fala.split(fim)[0]
        if 12 <= len(pedaco) <= 120:
            return pedaco + fim.strip()
    return fala[:110].rstrip() + ("…" if len(fala) > 110 else "")


# Estado do corte na tela. O motor guarda dois campos parecidos — `review_status`
# (o que uma PESSOA decidiu) e `status` (onde o arquivo está). Quem manda na cor
# do cartão é a decisão da pessoa; o arquivo pronto só importa para saber se dá
# para abrir o vídeo.
ESTADOS = {
    "approved": "approved",
    "rejected": "rejected",
    "needs_review": "reviewing",
    "pending": "suggested",
}


def _arquivo(caminho):
    """Um arquivo do motor virando endereço que o navegador abre.

    Os cortes e as miniaturas NÃO moram na pasta de trabalho: eles saem em
    `~/FuriaClipsData/exports`, que fica de fora de propósito — é material
    derivado e a pasta de trabalho é de entrada. Por isso não dá para montar
    um `/workspace/...` e pronto: a primeira versão disto fazia isso e todo
    cartão de corte aparecia sem foto.

    Quem já sabe servir arquivo de fora com a regra certa é a rota do próprio
    motor: ela confere se o caminho está debaixo de uma das pastas permitidas
    antes de abrir qualquer coisa. Usar a rota dele é uma regra só no programa
    inteiro, em vez de duas que um dia divergem.
    """
    if not caminho or not os.path.isfile(caminho):
        return ""
    return "/api/output_file?path=" + quote(str(Path(caminho).resolve()), safe="")


def _corte_para_a_tela(corte):
    """Um corte do motor no formato que o desenho dele espera."""
    try:
        fatores = json.loads(corte.get("score_factors") or "{}")
    except (TypeError, ValueError, json.JSONDecodeError):
        fatores = {}
    ajuste = corte.get("latest_adjustment") if isinstance(corte.get("latest_adjustment"), dict) else None
    inicio = float(corte.get("start_time") or 0)
    fim = float(corte.get("end_time") or 0)
    # A borda que vale é a que ELE moveu, se moveu. O ajuste fica guardado à
    # parte do corte renderizado de propósito (o arquivo em disco continua o
    # antigo até render novo), mas na tela quem manda é a decisão dele — senão
    # ele arrasta a alça, salva, e a tela devolve o número velho.
    if ajuste:
        inicio = float(ajuste.get("start", inicio) or inicio)
        fim = float(ajuste.get("end", fim) or fim)
    return {
        "id": corte.get("id"),
        "start": round(inicio, 2),
        "end": round(fim, 2),
        "duration": round(max(0.0, fim - inicio), 2),
        "title": _titulo(corte),
        "score": int(corte.get("viral_score") or 0),
        "reasons": _motivos(fatores),
        "status": ESTADOS.get(str(corte.get("review_status") or "pending"), "suggested"),
        "thumbnail": _arquivo(corte.get("thumbnail_path")),
        "exportUrl": _arquivo(corte.get("file_path")),
        "transcript": str(corte.get("transcript") or ""),
        "ajustado": bool(ajuste),
        # A confiança é do motor sobre o próprio palpite. Vai para a tela como
        # informação, nunca como nota: quem decide continua sendo ele.
        "confianca": round(float(corte.get("score_confidence") or 0), 2),
    }


# ── juntar a fonte no disco com a rodada que saiu dela ──────────────────────


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


def _fontes_no_disco():
    """Os vídeos que estão na pasta de trabalho, do mais novo para o mais velho.

    Fonte é ENTRADA. As pastas de saída ficam de fora — a primeira vez que uma
    lista dessas leu o disco de verdade ela devolveu 114 cortes já exportados
    misturados com 5 fontes, e um mural com o trabalho de ontem dentro não é
    uma lista de fontes.
    """
    raiz = Path(WORKSPACE_DIR)
    achados = []
    vistos = set()
    for pasta in (raiz / "uploads", raiz / "input", raiz):
        if not pasta.is_dir():
            continue
        # A raiz entra sem descer: descer dela varreria de novo tudo que
        # acabamos de deixar de fora.
        for caminho in (pasta.glob("*") if pasta == raiz else pasta.rglob("*")):
            if not caminho.is_file() or caminho.suffix.lower() not in ALLOWED_EXTENSIONS:
                continue
            chave = str(caminho.relative_to(raiz)).replace("\\", "/")
            if chave in vistos:
                continue
            vistos.add(chave)
            try:
                estado = caminho.stat()
            except OSError:
                continue
            achados.append({
                "chave": chave,
                "nome": caminho.name,
                "bytes": estado.st_size,
                "_quando": estado.st_mtime,
                "_caminho": str(caminho.resolve()),
            })
    achados.sort(key=lambda f: f["_quando"], reverse=True)
    return achados


def _rodadas_por_fonte():
    """Para cada vídeo, a última rodada que o motor fez em cima dele.

    A chave é o caminho de verdade do arquivo, não o nome: dois vídeos com o
    mesmo nome em pastas diferentes são dois vídeos, e juntar os dois faria a
    tela mostrar os cortes do errado.
    """
    ultima = {}
    for projeto in get_all_projects():
        origem = str(projeto.get("source_video") or "")
        if not origem:
            continue
        try:
            chave = str(Path(origem).resolve())
        except OSError:
            chave = origem
        # get_all_projects já vem do mais recente para o mais antigo.
        ultima.setdefault(chave, projeto)
    return ultima


@estudio.route("/api/estudio/mesa")
def api_mesa():
    """Tudo que a mesa desenha, numa pergunta só.

    Numa chamada por fonte a tela dele piscaria trinta vezes ao abrir. E é uma
    leitura de disco e uma de banco — não vale três rotas.
    """
    rodadas = _rodadas_por_fonte()
    fontes = []
    for fonte in _fontes_no_disco():
        projeto = rodadas.get(fonte["_caminho"])
        fontes.append({
            "chave": fonte["chave"],
            "nome": fonte["nome"],
            "bytes": fonte["bytes"],
            "projeto": projeto.get("id") if projeto else None,
            "estado": (projeto.get("status") if projeto else "") or "",
            "cortes": int(projeto.get("clip_count") or 0) if projeto else 0,
            "aprovados": int(projeto.get("approved_count") or 0) if projeto else 0,
            "para_rever": int(projeto.get("review_count") or 0) if projeto else 0,
            "quando": (projeto.get("created_at") or "") if projeto else "",
        })
    return jsonify({
        "fontes": fontes,
        "resumo": {
            "fontes": len(fontes),
            "moidas": sum(1 for f in fontes if f["cortes"]),
            "cortes": sum(f["cortes"] for f in fontes),
            "para_rever": sum(f["para_rever"] for f in fontes),
            "aprovados": sum(f["aprovados"] for f in fontes),
        },
    })


@estudio.route("/api/estudio/rodada/<int:projeto_id>")
def api_rodada(projeto_id):
    """Uma rodada inteira: a fonte, os cortes e a transcrição."""
    projeto = get_project(projeto_id)
    if not projeto:
        return jsonify({"erro": "essa rodada não existe mais"}), 404

    origem = str(projeto.get("source_video") or "")
    try:
        chave = str(Path(origem).resolve().relative_to(Path(WORKSPACE_DIR).resolve())).replace("\\", "/")
    except (ValueError, OSError):
        chave = ""

    transcricao = get_transcription(projeto_id) or {}
    trechos = transcricao.get("segments") if isinstance(transcricao, dict) else None
    if isinstance(trechos, str):
        try:
            trechos = json.loads(trechos)
        except (TypeError, ValueError, json.JSONDecodeError):
            trechos = []

    cortes = [_corte_para_a_tela(c) for c in get_clips(projeto_id)]
    return jsonify({
        "id": projeto_id,
        "nome": projeto.get("name") or Path(origem).stem,
        "chave": chave,
        "segundos": round(_segundos(origem) if os.path.isfile(origem) else 0, 2),
        "estado": projeto.get("status") or "",
        "quando": projeto.get("created_at") or "",
        "cortes": cortes,
        "trechos": [
            {
                "start": float(t.get("start") or 0),
                "end": float(t.get("end") or 0),
                "text": str(t.get("text") or "").strip(),
            }
            for t in (trechos or []) if isinstance(t, dict)
        ],
    })


@estudio.route("/")
def pagina_do_estudio():
    return render_template("estudio.html")
