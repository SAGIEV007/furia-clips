"""FURIA 2 — a bancada.

A interface nova. O motor é o do Furia 1 e continua onde sempre esteve: as
rotas daqui são um Blueprint que o `app.py` da raiz registra, então a bancada
roda DENTRO do mesmo programa e enxerga tudo que já funciona — transcrição,
Gemini, CHUB, blocos, corte, render. Nada foi copiado e nada foi reescrito.

Isso é a decisão do conceito posta em prática: o que sobrevive é o motor e as
três peças de interface que já funcionavam; o resto da interface morre. Juntar
por Blueprint, e não por porta separada, é o que faz "o resto morre" não
significar "o resto para de funcionar".

    /            a interface antiga, intacta
    /2           a bancada nova
    /api/fonte…  /api/cortes…  /api/talho…  /api/mapa…   as rotas daqui

Este arquivo também sobe sozinho na porta 5001 (`python furia2/app.py`), o que
serve para trabalhar no desenho sem carregar o motor inteiro.
"""

import json
import os
import subprocess
import sys
import uuid
from pathlib import Path

from flask import Blueprint, Flask, abort, jsonify, render_template, request, send_file

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

# Onde a rodada deixa a folha de decisões. É a mesma pasta que o Furia 1 já
# usa, e ela fica FORA do repositório de propósito: a folha carrega a
# transcrição do material, e transcrição de coisa não publicada não entra em
# pasta versionada.
DIAGNOSTICOS = Path(
    os.environ.get("FURIA_CLIPS_DATA_DIR") or (Path.home() / "FuriaClipsData")
) / "diagnostics"

# As rotas moram num Blueprint, não num Flask próprio: assim elas podem ser
# penduradas no programa principal sem duplicar nada. O caminho da estática é
# separado do `/static` da interface antiga de propósito — dois programas
# servindo `style.css` do mesmo endereço é o tipo de confusão que só aparece
# na máquina dele, três dias depois.
bancada = Blueprint(
    "bancada",
    __name__,
    template_folder=str(Path(__file__).parent / "templates"),
    static_folder=str(Path(__file__).parent / "static"),
    static_url_path="/furia2",
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


def _tem_imagem(caminho):
    """O arquivo tem trilha de vídeo?

    Achar a fonte não é o mesmo que ter imagem. Quando ele guardou só o áudio
    de uma entrevista antiga, o talho e o mapa funcionam inteiros e o mural
    não tem quadro nenhum — e pedir onze quadros de um mp3 dá onze erros no
    registro por nada, que é exatamente o tipo de linha falsa que faz procurar
    defeito onde não tem.
    """
    try:
        saida = subprocess.run(
            ["ffprobe", "-v", "error", "-select_streams", "v:0",
             "-show_entries", "stream=codec_type", "-of", "csv=p=0", str(caminho)],
            capture_output=True, text=True, timeout=20, check=False,
        )
        return "video" in (saida.stdout or "")
    except (OSError, subprocess.SubprocessError):
        return False


def _ficha(caminho, chave):
    tamanho = caminho.stat().st_size if caminho.exists() else 0
    return {
        "chave": chave,
        "nome": caminho.name,
        "segundos": round(_segundos(caminho), 2),
        "bytes": tamanho,
        "modificado": caminho.stat().st_mtime if caminho.exists() else 0,
    }


@bancada.route("/api/fonte/lista")
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
    return jsonify({"fontes": achados})


def _resolver(chave):
    """De uma chave da lista para um arquivo de verdade, sem sair do permitido.

    Toda fonte mora dentro da pasta de trabalho — o que vem de fora é importado
    na hora de escolher. Isso deixa esta função com um caminho só, e um caminho
    só é um caminho que não tem como divergir do que o motor aceita.
    """
    try:
        caminho = Path(safe_workspace_path(WORKSPACE_DIR, chave, allow_missing=False))
    except (UnsafePathError, FileNotFoundError):
        abort(404)
    # Tem de ser ARQUIVO. Uma chave vazia resolve para a própria pasta de
    # trabalho, que existe — e daí o ffmpeg seria chamado em cima de uma pasta.
    if not caminho.is_file():
        abort(404)
    return caminho


@bancada.route("/api/fonte/quadro")
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


def _contar_para_a_tela(mensagem):
    """Diz uma linha no mesmo canal que o motor usa.

    A bancada já escuta esse canal, então o que for dito aqui aparece na faixa
    de cima e no registro sem precisar de um segundo caminho. Rodando a bancada
    sozinha, sem o motor, o canal não existe e a linha simplesmente não sai.
    """
    motor = sys.modules.get("app")
    try:
        motor.emit_progress(mensagem)
    except (AttributeError, RuntimeError):
        pass


def _importar_para_a_pasta(origem):
    """Traz o vídeo para dentro da pasta de trabalho.

    Este é o passo que faltava, e ele é a causa de "moer" falhar: o motor só
    aceita vídeo de dentro da pasta de trabalho — regra dele, e uma regra certa,
    porque senão qualquer página aberta no navegador poderia mandar o programa
    ler um arquivo qualquer do computador. Escolher na janela do Windows dá o
    caminho, não a permissão.

    A interface antiga resolvia isso mandando o arquivo pelo navegador. Aqui o
    arquivo já está na mesma máquina, então copiar é mais rápido e mais honesto
    que subir e baixar de volta.

    Copiado em pedaços, contando quanto já foi: um debate de duas horas tem
    gigabytes, e uma tela parada durante um minuto é uma tela que parece
    travada.
    """
    destino_pasta = Path(WORKSPACE_DIR) / "uploads"
    destino_pasta.mkdir(parents=True, exist_ok=True)
    destino = destino_pasta / origem.name

    tamanho = origem.stat().st_size
    if destino.exists() and destino.stat().st_size == tamanho:
        # Mesmo nome e mesmo tamanho: é o que ele já importou antes. Copiar de
        # novo seria um minuto de espera para chegar ao mesmo arquivo.
        _contar_para_a_tela(f"[Fonte] {origem.name} já estava na pasta de trabalho.")
        return destino

    _contar_para_a_tela(f"[Fonte] Importando {origem.name} ({tamanho / 1_048_576:.0f} MB)...")
    PEDACO = 8 * 1024 * 1024
    andado = 0
    ultimo_aviso = 0
    # Nome temporário: se a máquina desligar no meio, o que fica é um `.parcial`
    # que ninguém confunde com vídeo bom — em vez de um mp4 pela metade na
    # lista de fontes.
    parcial = destino.with_suffix(destino.suffix + ".parcial")
    try:
        with open(origem, "rb") as entrada, open(parcial, "wb") as saida:
            while True:
                bloco = entrada.read(PEDACO)
                if not bloco:
                    break
                saida.write(bloco)
                andado += len(bloco)
                por_cento = int(andado * 100 / tamanho) if tamanho else 100
                if por_cento >= ultimo_aviso + 10:
                    ultimo_aviso = por_cento
                    _contar_para_a_tela(f"[Fonte] Importando {origem.name}: {por_cento}%")
        parcial.replace(destino)
    except OSError:
        parcial.unlink(missing_ok=True)
        raise
    _contar_para_a_tela(f"[Fonte] {origem.name} está na pasta de trabalho.")
    return destino


@bancada.route("/api/fonte/escolher", methods=["POST"])
def api_fonte_escolher():
    """A janela do Windows, e a importação logo em seguida.

    Escolher e importar são um gesto só do ponto de vista dele: ele apontou
    para o vídeo, e o que ele espera é que o vídeo esteja no programa. Deixar
    o arquivo do lado de fora e só descobrir isso ao apertar "moer" é a falha
    calada de sempre, com meia hora de atraso.
    """
    try:
        escolhido = choose_path(mode="file", title="Escolher a fonte")
    except (DialogError, OSError, subprocess.SubprocessError) as erro:
        return jsonify({"ok": False, "erro": str(erro)}), 500
    if not escolhido:
        return jsonify({"ok": True, "desistiu": True})

    caminho = Path(escolhido).resolve()
    if caminho.suffix.lower() not in ALLOWED_EXTENSIONS:
        return jsonify({"ok": False, "erro": f"{caminho.suffix} não é vídeo"}), 400
    if not caminho.is_file():
        return jsonify({"ok": False, "erro": "esse arquivo não existe mais"}), 404

    raiz = Path(WORKSPACE_DIR).resolve()
    if raiz not in caminho.parents:
        try:
            caminho = _importar_para_a_pasta(caminho)
        except OSError as erro:
            return jsonify({"ok": False, "erro": f"não deu para importar: {str(erro)[:120]}"}), 500

    # Já dentro da pasta de trabalho, a fonte é como qualquer outra: chave
    # relativa, que é exatamente o que o motor aceita.
    return jsonify({
        "ok": True, "desistiu": False,
        "fonte": _ficha(caminho, str(caminho.relative_to(raiz))),
    })


@bancada.route("/api/fonte/video")
def api_fonte_video():
    """A fonte para o navegador tocar.

    `conditional=True` liga a resposta por faixa, que é o que deixa arrastar a
    linha do tempo sem baixar o arquivo inteiro antes.
    """
    return send_file(_resolver(request.args.get("chave", "")), conditional=True, max_age=3600)


@bancada.route("/api/fonte/ler-link", methods=["POST"])
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
        if fonte is None:
            # O mesmo nome com outra extensão serve. O talho e o mapa só
            # precisam do SOM: a onda, os tempos e a escuta saem do áudio. É
            # comum ele guardar só o áudio de uma entrevista antiga — vídeo de
            # meia hora ocupa disco, áudio de meia hora não — e nesse caso o
            # ajuste fino continua funcionando inteiro, só sem os quadros.
            haste = Path(nome).stem
            for achado in Path(WORKSPACE_DIR).rglob(f"{haste}.*"):
                if achado.is_file():
                    fonte = achado
                    break
    return dados, fonte


def _corte_para_a_tela(bruto, numero, inicio, fim, ajustado):
    """O que a parede precisa de cada corte, e só isso.

    A folha guarda vinte e quatro campos por corte. A parede mostra nove. Os
    outros são do talho e do painel — mandar tudo para cá seria construir a
    tentação de encher a tela com número que não muda decisão nenhuma.

    `inicio` e `fim` chegam de fora, já resolvidos: se ele mexeu na borda no
    talho, é a borda DELE que a parede mostra. A parede lendo direto da folha
    foi o defeito mais caro do Furia 1 — o ajuste gravado que a tela continuava
    ignorando.
    """
    return {
        "n": numero,
        "inicio": round(inicio, 2),
        "fim": round(fim, 2),
        # A duração é a CONTA, nunca o campo `duration_s` da folha. Lendo o
        # campo, um corte ajustado saía na parede com a borda nova e a duração
        # velha — dois números na mesma linha discordando um do outro, que é
        # a forma mais barata de fazer alguém desconfiar do programa inteiro.
        "duracao": round(max(0.0, fim - inicio), 2),
        # `review_required` é o único campo daqui que acende vermelho, e ele é
        # a razão de o vermelho existir: é o corte que pede o olho dele antes
        # de ir para o ar.
        "conferir": bool(bruto.get("review_required")),
        "motivos": [str(m) for m in (bruto.get("review_reasons") or [])][:4],
        "fala": " ".join(str(bruto.get("texto") or "").split()),
        "origem": str(bruto.get("origem") or ""),
        "ajustado": bool(ajustado),
    }


@bancada.route("/api/cortes/lista")
def api_cortes_lista():
    dados, fonte = _folha_da_rodada()
    if not dados:
        return jsonify({"ok": True, "tem_rodada": False, "cortes": []})

    cortes = []
    for i, c in enumerate(dados.get("cortes_renderizados") or []):
        inicio, fim, ajustado = _bordas(dados, i + 1)
        cortes.append(_corte_para_a_tela(c, i + 1, inicio, fim, ajustado))
    diagnostico = (dados.get("selecao") or {}).get("diagnostico") or {}
    conferir = sum(1 for c in cortes if c["conferir"])

    return jsonify({
        "ok": True,
        "tem_rodada": True,
        "fonte": {
            "nome": str((dados.get("fonte") or {}).get("arquivo") or ""),
            "segundos": float((dados.get("fonte") or {}).get("duracao_s") or 0),
            # Duas coisas diferentes, e a parede precisa das duas separadas:
            # sem som não há onda nem escuta no talho; sem imagem não há
            # quadro no mural. A decisão é o que importa — a imagem é conforto.
            "tem_som": fonte is not None,
            "tem_imagem": fonte is not None and _tem_imagem(fonte),
        },
        "cortes": cortes,
        "resumo": {
            "entregues": len(cortes),
            "conferir": conferir,
            "descartados_por_sobreposicao": int(diagnostico.get("fallback_discarded_overlap") or 0),
            "recusados": int(diagnostico.get("hard_negative_count") or 0),
        },
    })


@bancada.route("/api/cortes/quadro")
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

    # A borda dele, não a da máquina: mexeu no começo, o quadro do mural muda
    # junto. Um mural que continua mostrando o quadro velho depois do ajuste é
    # a mesma falha calada de sempre, só que em imagem.
    inicio, _fim, _ = _bordas(dados, numero)
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


# ── o talho: o ajuste fino da borda ─────────────────────────────────────────

# Onde ficam as bordas que ELE decidiu, por cima do que a máquina decidiu.
# Arquivo simples e legível, ao lado da folha: a decisão dele é a mais cara do
# programa inteiro e não pode morar só na memória de uma aba aberta.
AJUSTES = Path.home() / "FuriaClipsData" / "furia2" / "ajustes.json"

# Quanto de fora do corte a onda mostra. A queixa original dele sobre o ajuste
# do Furia 1 foi não conseguir VOLTAR: para escolher onde entrar é preciso
# ouvir a frase anterior. A margem é metade da duração do corte, entre 8 e 45
# segundos — num corte de 30 s isso dá 15 s de cada lado; num de 3 min, 45.
MARGEM_MIN, MARGEM_MAX = 8.0, 45.0


def _ler_ajustes():
    try:
        return json.loads(AJUSTES.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def _gravar_ajuste(chave, numero, inicio, fim):
    tudo = _ler_ajustes()
    tudo.setdefault(chave, {})[str(numero)] = {"inicio": round(inicio, 3), "fim": round(fim, 3)}
    AJUSTES.parent.mkdir(parents=True, exist_ok=True)
    AJUSTES.write_text(json.dumps(tudo, ensure_ascii=False, indent=2), encoding="utf-8")


def _chave_da_folha(dados):
    return f"{(dados.get('job_id') or '')}|{(dados.get('fonte') or {}).get('arquivo') or ''}"


def _bordas(dados, numero):
    """As bordas valendo agora: as dele se existirem, as da máquina se não.

    A ordem importa e é a correção do defeito mais caro do Furia 1 — o ajuste
    gravado que o programa continuava ignorando, devolvendo 200 e mostrando o
    corte velho. Todo lugar que precisa de uma borda passa por aqui.
    """
    cortes = dados.get("cortes_renderizados") or []
    bruto = cortes[numero - 1]
    inicio = float(bruto.get("start_s") or 0)
    fim = float(bruto.get("end_s") or 0)
    dele = _ler_ajustes().get(_chave_da_folha(dados), {}).get(str(numero))
    if dele:
        return float(dele["inicio"]), float(dele["fim"]), True
    return inicio, fim, False


def _corte_pedido(dados):
    try:
        numero = int(request.args.get("n", "0"))
    except ValueError:
        abort(404)
    if not 1 <= numero <= len(dados.get("cortes_renderizados") or []):
        abort(404)
    return numero


@bancada.route("/api/talho/trecho")
def api_talho_trecho():
    """Tudo que o talho precisa de um corte, numa chamada só."""
    dados, fonte = _folha_da_rodada()
    if not dados:
        abort(404)
    numero = _corte_pedido(dados)
    bruto = (dados.get("cortes_renderizados") or [])[numero - 1]
    inicio, fim, ajustado = _bordas(dados, numero)

    margem = min(MARGEM_MAX, max(MARGEM_MIN, (fim - inicio) / 2))
    duracao_fonte = float((dados.get("fonte") or {}).get("duracao_s") or 0)
    janela_ini = max(0.0, inicio - margem)
    janela_fim = (min(duracao_fonte, fim + margem) if duracao_fonte else fim + margem)

    return jsonify({
        "ok": True,
        "n": numero,
        "de": len(dados.get("cortes_renderizados") or []),
        "inicio": round(inicio, 3),
        "fim": round(fim, 3),
        # O que a máquina propôs, sempre junto: ele precisa poder comparar com
        # a proposta e voltar para ela sem refazer a conta de cabeça.
        "proposto": {"inicio": round(float(bruto.get("start_s") or 0), 3),
                     "fim": round(float(bruto.get("end_s") or 0), 3)},
        "ajustado": ajustado,
        "janela": {"inicio": round(janela_ini, 3), "fim": round(janela_fim, 3)},
        "tem_som": fonte is not None,
        # As frases com hora. É com elas que ele vê, ao arrastar, qual frase
        # está ganhando e qual está perdendo — que é a pergunta do ofício.
        "frases": [
            {"t": round(float(f.get("t") or 0), 2),
             "fim": round(float(f.get("fim") or 0), 2),
             "texto": str(f.get("texto") or "")}
            for f in (bruto.get("transcricao") or [])
        ],
    })


@bancada.route("/api/talho/onda")
def api_talho_onda():
    """A forma do som na janela pedida.

    Vem inteira do Furia 1, onde já funciona: energia média em vez de pico
    (com milhares de amostras por fatia o pico satura e desenha um bloco
    retangular, inútil para achar onde a frase começa), e raiz de novo para
    levantar o que é baixo, porque fala normal ocupa uma faixa estreita perto
    do chão.
    """
    import numpy as np

    from modules.speaker_id import read_pcm

    dados, fonte = _folha_da_rodada()
    if not dados or fonte is None:
        abort(404)
    try:
        inicio = max(0.0, float(request.args.get("inicio", 0)))
        fim = float(request.args.get("fim", 0))
        fatias = max(60, min(1200, int(request.args.get("fatias", 520))))
    except (TypeError, ValueError):
        return jsonify({"ok": False, "erro": "intervalo inválido"}), 400
    if fim <= inicio or fim - inicio > 1800:
        return jsonify({"ok": False, "erro": "intervalo inválido"}), 400

    try:
        amostras = read_pcm(str(fonte), inicio, fim)
    except (OSError, ValueError, subprocess.SubprocessError) as erro:
        return jsonify({"ok": False, "erro": f"não deu para ler o áudio: {str(erro)[:120]}"}), 500
    if amostras.size == 0:
        return jsonify({"ok": True, "inicio": inicio, "fim": fim, "picos": [0.0] * fatias, "mudo": True})

    largura = max(1, amostras.size // fatias)
    aparadas = amostras[: largura * fatias].reshape(fatias, largura)
    picos = np.sqrt((aparadas.astype(np.float64) ** 2).mean(axis=1))
    picos = np.sqrt(picos)
    teto = float(picos.max()) or 1.0
    return jsonify({
        "ok": True,
        "inicio": inicio,
        "fim": fim,
        "picos": [round(float(v) / teto, 4) for v in picos],
        "mudo": teto < 0.005,
    })


@bancada.route("/api/talho/som")
def api_talho_som():
    """A fonte inteira, para o navegador tocar e procurar dentro dela.

    `conditional=True` liga a resposta por faixa: sem isso o navegador baixaria
    meia hora de mídia para ouvir três segundos de borda.
    """
    _, fonte = _folha_da_rodada()
    if fonte is None:
        abort(404)
    return send_file(fonte, conditional=True, max_age=3600)


@bancada.route("/api/talho/guardar", methods=["POST"])
def api_talho_guardar():
    """Grava a borda que ELE decidiu — e devolve o que ficou gravado.

    Devolver os valores relidos do disco não é formalidade: o defeito mais caro
    do Furia 1 foi um ajuste que respondia 200 e guardava o valor velho, e
    ninguém percebeu por duas versões porque a tela nunca conferiu. Aqui quem
    responde é o arquivo, não a intenção.
    """
    dados, _ = _folha_da_rodada()
    if not dados:
        abort(404)
    corpo = request.get_json(silent=True) or {}
    try:
        numero = int(corpo.get("n", 0))
        inicio = float(corpo.get("inicio"))
        fim = float(corpo.get("fim"))
    except (TypeError, ValueError):
        return jsonify({"ok": False, "erro": "valores inválidos"}), 400
    if not 1 <= numero <= len(dados.get("cortes_renderizados") or []):
        return jsonify({"ok": False, "erro": "corte inexistente"}), 404
    if fim - inicio < 1.0:
        return jsonify({"ok": False, "erro": "o corte ficaria com menos de um segundo"}), 400

    _gravar_ajuste(_chave_da_folha(dados), numero, inicio, fim)
    gravado_inicio, gravado_fim, _ = _bordas(dados, numero)
    return jsonify({"ok": True, "inicio": gravado_inicio, "fim": gravado_fim})


# ── o mapa da fonte ─────────────────────────────────────────────────────────

# Um vão só conta quando é grande o bastante para ele reparar. Abaixo de um
# minuto, o intervalo entre dois cortes é respiração normal da entrevista; a
# partir daí é um pedaço da fonte que não virou nada, e é sobre esse pedaço
# que ele pergunta.
VAO_MINIMO = 60.0

# Os motivos da máquina são etiquetas em inglês. Ele não lê inglês e não tem
# por que ler: quem escreve a etiqueta é o programa, e traduzir na hora de
# mostrar é obrigação de quem escreveu. Sem isto o mapa diria
# "touching_sibling_lost_to_better_candidate" para um editor de vídeo.
MOTIVOS = {
    "duplicate_overlap": "repetia material de um corte já escolhido",
    "duplicate_similarity": "dizia quase a mesma coisa que outro corte",
    "touching_sibling_lost_to_better_candidate": "encostava em outro trecho e perdeu",
    "touching_sibling_lost_to_existing_candidate": "encostava em outro trecho e perdeu",
    "already_exported_fingerprint": "já tinha sido exportado numa rodada anterior",
    "not_evaluated": "não chegou a ser avaliado",
}


def _numero(valor, padrao=0.0):
    """A folha guarda número às vezes como texto. Melhor tolerar aqui do que
    deixar uma faixa inteira sumir do mapa por causa de uma aspa."""
    try:
        return float(valor)
    except (TypeError, ValueError):
        return padrao


def _motivo_em_portugues(bruto):
    etiqueta = str(bruto or "").strip()
    return MOTIVOS.get(etiqueta, etiqueta.replace("_", " ") or "sem motivo registrado")


def _qual_corte(cortes, comeco):
    """De um segundo para um número de corte.

    O vencedor é comparado com a borda que a MÁQUINA propôs, não com a que ele
    ajustou depois: a disputa aconteceu antes de qualquer ajuste, e casar com a
    borda de agora faria a resposta mudar sozinha quando ele arrastasse uma
    alça no talho.
    """
    if comeco < 0:
        return None
    for i, bruto in enumerate(cortes):
        if abs(_numero(bruto.get("start_s")) - comeco) <= 1.0:
            return i + 1
    # Perdeu para um candidato que também acabou não sendo entregue. Acontece,
    # e dizer isso é mais honesto do que apontar para um corte que não existe.
    return None


def _juntar(intervalos):
    """Une o que se encosta ou se sobrepõe."""
    juntos = []
    for inicio, fim in sorted(intervalos):
        if juntos and inicio <= juntos[-1][1]:
            juntos[-1][1] = max(juntos[-1][1], fim)
        else:
            juntos.append([inicio, fim])
    return juntos


def _vaos(entregues, duracao):
    """Os pedaços da fonte que não viraram corte nenhum."""
    vazios = []
    ponteiro = 0.0
    for inicio, fim in _juntar([(c["inicio"], c["fim"]) for c in entregues]):
        if inicio - ponteiro >= VAO_MINIMO:
            vazios.append([ponteiro, inicio])
        ponteiro = max(ponteiro, fim)
    if duracao - ponteiro >= VAO_MINIMO:
        vazios.append([ponteiro, duracao])
    return vazios


@bancada.route("/api/mapa/onda")
def api_mapa_onda():
    """A onda da fonte INTEIRA, para servir de chão ao mapa.

    Lida em pedaços de dois minutos e guardada em disco. Ler meia hora de áudio
    de uma vez custa cento e treze megabytes de memória; uma entrevista de duas
    horas, quase meio giga — e o mapa é uma janela que ele abre e fecha o dia
    todo. Em pedaços, o pico de memória é o de um pedaço só, e da segunda vez
    em diante o arquivo guardado responde na hora.
    """
    import numpy as np

    from modules.speaker_id import read_pcm

    dados, fonte = _folha_da_rodada()
    if not dados or fonte is None:
        abort(404)
    duracao = _numero((dados.get("fonte") or {}).get("duracao_s"))
    if duracao <= 0:
        abort(404)
    fatias = max(120, min(2000, int(_numero(request.args.get("fatias"), 900))))

    CACHE.mkdir(parents=True, exist_ok=True)
    assinatura = f"{fonte}|{fonte.stat().st_mtime_ns}|{fatias}|mapa"
    guardado = CACHE / (uuid.uuid5(uuid.NAMESPACE_URL, assinatura).hex + ".json")
    if guardado.exists():
        try:
            return jsonify(json.loads(guardado.read_text(encoding="utf-8")))
        except (OSError, ValueError):
            pass   # arquivo estragado: refaz em vez de quebrar a tela

    PEDACO = 120.0
    largura_s = duracao / fatias
    picos = []
    inicio = 0.0
    try:
        while inicio < duracao:
            fim = min(duracao, inicio + PEDACO)
            amostras = read_pcm(str(fonte), inicio, fim)
            quantas = max(1, round((fim - inicio) / largura_s))
            passo = max(1, amostras.size // quantas)
            if amostras.size:
                bloco = amostras[: passo * quantas].reshape(quantas, passo)
                energia = np.sqrt((bloco.astype(np.float64) ** 2).mean(axis=1))
                picos.extend(float(v) for v in np.sqrt(energia))
            else:
                picos.extend([0.0] * quantas)
            inicio = fim
    except (OSError, ValueError, subprocess.SubprocessError) as erro:
        return jsonify({"ok": False, "erro": f"não deu para ler o áudio: {str(erro)[:120]}"}), 500

    teto = max(picos) or 1.0
    corpo = {
        "ok": True,
        "segundos": round(duracao, 2),
        "picos": [round(v / teto, 4) for v in picos],
    }
    try:
        guardado.write_text(json.dumps(corpo), encoding="utf-8")
    except OSError:
        pass   # sem poder guardar, ainda responde; só volta a calcular na próxima
    return jsonify(corpo)


@bancada.route("/api/mapa")
def api_mapa():
    """Onde a rodada cortou, onde recusou, e onde não achou nada.

    A pergunta que este mapa existe para responder não é "onde estão os
    cortes" — a parede já responde isso. É a outra: POR QUE aquele pedaço de
    quatro minutos não deu corte nenhum. A resposta mora nos recusados, que
    até agora só existiam como um número no fim do relatório.
    """
    dados, fonte = _folha_da_rodada()
    if not dados:
        return jsonify({"ok": True, "tem_rodada": False})

    duracao = _numero((dados.get("fonte") or {}).get("duracao_s"))
    cortes = dados.get("cortes_renderizados") or []

    entregues = []
    for i, bruto in enumerate(cortes):
        inicio, fim, ajustado = _bordas(dados, i + 1)
        entregues.append({
            "n": i + 1,
            "inicio": round(inicio, 2),
            "fim": round(fim, 2),
            "ajustado": ajustado,
            "fala": " ".join(str(bruto.get("texto") or "").split())[:220],
        })

    diagnostico = (dados.get("selecao") or {}).get("diagnostico") or {}
    recusados = []
    for bruto in diagnostico.get("hard_negatives") or []:
        inicio = _numero(bruto.get("start"))
        fim = _numero(bruto.get("end"))
        if fim <= inicio:
            continue
        vencedor = bruto.get("winner") if isinstance(bruto.get("winner"), dict) else {}
        detalhes = bruto.get("details") if isinstance(bruto.get("details"), dict) else {}
        recusados.append({
            "inicio": round(inicio, 2),
            "fim": round(fim, 2),
            "motivo": _motivo_em_portugues(bruto.get("reason")),
            "trecho": " ".join(str(bruto.get("text_preview") or "").split())[:160],
            # Contra QUEM perdeu, e por quanto. Saber que um trecho foi
            # recusado não resolve nada; saber que ele perdeu para o CORTE 03
            # por 23 pontos resolve, porque aí ele abre o corte 03 e julga.
            # A folha guarda o vencedor pelo segundo em que começa — número que
            # não quer dizer nada para ele —, então aqui vira número de corte.
            "perdeu_para": _qual_corte(cortes, _numero(vencedor.get("start"), -1)) if vencedor else None,
            "por_quanto": round(_numero(detalhes.get("score_gap"), 0), 1) if detalhes else 0,
        })

    adiados = []
    for bruto in dados.get("candidatos_adiados") or []:
        inicio = _numero(bruto.get("start_s"))
        fim = _numero(bruto.get("end_s"))
        if fim <= inicio:
            continue
        adiados.append({
            "inicio": round(inicio, 2),
            "fim": round(fim, 2),
            "motivo": " ".join(str(bruto.get("motivo_adiamento") or "").split())[:160],
            "trecho": " ".join(str(bruto.get("texto") or "").split())[:160],
        })

    # Marcar quem morreu DENTRO de um vão. É a discriminação que faz esta tela
    # valer: um recusado no meio de um trecho que já deu corte é rotina; um
    # recusado dentro de um buraco de três minutos é a explicação do buraco.
    faixas_vazias = _vaos(entregues, duracao)
    for lista in (recusados, adiados):
        for item in lista:
            centro = (item["inicio"] + item["fim"]) / 2
            item["num_vao"] = any(a <= centro <= b for a, b in faixas_vazias)

    vazios = []
    for inicio, fim in faixas_vazias:
        # Quantos candidatos morreram dentro deste vão. É a diferença entre
        # "aqui não tinha nada" e "aqui tinha três coisas e todas caíram".
        dentro = sum(1 for r in recusados if inicio <= (r["inicio"] + r["fim"]) / 2 <= fim)
        adiado_aqui = sum(1 for a in adiados if inicio <= (a["inicio"] + a["fim"]) / 2 <= fim)
        vazios.append({
            "inicio": round(inicio, 2),
            "fim": round(fim, 2),
            "recusados": dentro,
            "adiados": adiado_aqui,
        })

    aproveitado = sum(fim - inicio for inicio, fim in _juntar([(c["inicio"], c["fim"]) for c in entregues]))
    return jsonify({
        "ok": True,
        "tem_rodada": True,
        "fonte": {
            "nome": str((dados.get("fonte") or {}).get("arquivo") or ""),
            "segundos": round(duracao, 2),
            "tem_som": fonte is not None,
        },
        "entregues": entregues,
        "recusados": recusados,
        "adiados": adiados,
        "vazios": vazios,
        "aproveitado": round(aproveitado, 2),
    })


# ── a bancada ───────────────────────────────────────────────────────────────


@bancada.route("/2")
def pagina_da_bancada():
    return render_template("bancada.html")


def criar_app():
    """Um Flask só com a bancada, sem o motor.

    Serve para duas coisas: trabalhar no desenho sem esperar o programa inteiro
    subir, e rodar os testes das telas sem arrastar o motor para dentro deles.
    Quem serve o editor de verdade é o `app.py` da raiz, que registra o mesmo
    Blueprint ao lado de tudo o mais.
    """
    sozinho = Flask(__name__)
    sozinho.register_blueprint(bancada)
    return sozinho


app = criar_app()


if __name__ == "__main__":
    print(f"Furia 2 — bancada em http://127.0.0.1:{PORTA}/2")
    # 127.0.0.1 e não 0.0.0.0: o programa é da máquina dele e não tem por que
    # ficar escutando a rede da casa.
    app.run(host="127.0.0.1", port=PORTA, debug=False)
