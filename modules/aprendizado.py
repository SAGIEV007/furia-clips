"""O que o programa aprendeu com o editor.

O PROBLEMA, NAS PALAVRAS DELE
-----------------------------
    "quando eu mandar links de lives recentes, essas lives não vão estar no
     chub, então precisam ter aprendido padrões de cortes anteriores para
     funcionarem corretamente"

Ele está certo, e o diagnóstico dele é preciso. Hoje o motor tem duas fontes de
número, e nenhuma das duas serve para uma live de ontem:

    o espelho do CHUB   mede 5.339 cortes JÁ PUBLICADOS — três pesos, e só
    os blocos do Acervo  são a régua, mas só existem para vídeo catalogado

Numa live recente não há bloco do Acervo, e o motor cai nas regras fixas — que
são palpites meus com cara de ciência. É exatamente onde ele mais precisa de
ajuda e onde tem menos.

O QUE ESTE ARQUIVO FAZ
----------------------
Transforma o julgamento dele em número, e o número entra no motor pela mesma
porta por onde entram os pesos do CHUB (`espelho_chub.portoes`). Duas fontes:

    o caderno de vereditos    "3 ok", "4 ok mas final cortado"
    os cortes que ele fez     começo e fim que ELE escolheu, no vídeo dele

A segunda é a mais valiosa e é a que resolve o problema da live recente: um
corte que ele fez à mão é um gabarito que não depende do CHUB. Ele é a resposta
certa, para aquele vídeo, escrita por quem decide.

O QUE ISTO NÃO É
----------------
Não é rede neural, não é "treinar um modelo". É calibração medida, e a
diferença importa: cada número daqui tem uma conta de uma linha que dá para
conferir na mão, e um motivo em português na tela. Um sistema que ele não possa
auditar seria pior que os palpites, porque erraria sem deixar rastro.

A REGRA QUE NÃO SE QUEBRA (NORTE §15)
-------------------------------------
Só entra aqui o que veio de fora do programa: o veredito dele e o corte dele.
Nada que o Furia disse sobre o próprio trabalho vira peso. Um motor que aprende
com a própria opinião só aprende a concordar consigo mesmo.
"""

from __future__ import annotations

import json
import os
from collections import defaultdict
from pathlib import Path
from typing import Any

# Quantos casos são precisos antes de um número do editor mexer no motor.
# Abaixo disto, uma etiqueta a mais vira uma mudança de rumo, e o motor passa a
# perseguir o último clipe que ele reprovou em vez do padrão dele.
MINIMO_DE_CASOS = 8

# Teto do ajuste, em POR CENTO do peso atual — não em pontos de nota. Trinta
# por cento move o número o bastante para a régua enxergar e pouco o bastante
# para um sinal só não decidir sozinho o que é corte e o que não é.
TETO = 30.0

# A ponte entre o que ele escreve no WhatsApp e o número que o motor usa.
# Cada linha é: etiqueta do editor -> (peso do motor, sinal que o motor grava).
#
# A segunda coluna é o que permite achar o ERRO DE CALIBRAÇÃO. Se ele marcou
# "final cortado" num corte em que o motor tinha gravado `payoff_complete:
# True`, o motor não errou o peso — errou o diagnóstico. Isso é mais grave, e
# aparece separado.
O_QUE_CADA_ETIQUETA_CORRIGE: dict[str, tuple[str, str]] = {
    "fim": ("termina_sem_fechar", "payoff_complete"),
    "abertura": ("comeca_no_meio_da_frase", "starts_mid_sentence"),
    "locutor": ("abre_sem_afirmar", "opens_without_a_claim"),
    "contexto": ("contexto_incompleto", "context_complete"),
    "repetido": ("repeticao", "overlap_suspected"),
}

# Quando o sinal do motor está LIGADO, ele já acusou o defeito. Para
# `payoff_complete` e `context_complete` é o contrário: ligado quer dizer "está
# tudo bem". Estas duas leem ao contrário na hora de contar acerto e erro.
SINAL_LIGADO_E_BOM = {"payoff_complete", "context_complete"}


def _pasta(nome: str, data_dir=None) -> Path:
    raiz = Path(
        data_dir or os.environ.get("FURIA_CLIPS_DATA_DIR") or (Path.home() / "FuriaClipsData")
    )
    return raiz / nome


def ler_vereditos(data_dir=None) -> list[dict]:
    """O caderno inteiro, o último veredito de cada corte.

    O caderno só acrescenta linha — ele nunca reescreve — então um corte pode
    ter mais de um veredito quando o editor muda de ideia. A última vale, e as
    anteriores continuam no arquivo porque apagar histórico de julgamento é
    apagar o motivo de tudo isto existir.
    """
    pasta = _pasta("vereditos", data_dir)
    if not pasta.is_dir():
        return []
    por_corte: dict[tuple[str, str], dict] = {}
    for arquivo in sorted(pasta.glob("*.txt")):
        for linha in arquivo.read_text(encoding="utf-8", errors="replace").splitlines():
            partes = [p.strip() for p in linha.split("|")]
            if len(partes) < 4 or not partes[3]:
                continue
            rodada, numero = partes[1], partes[2].lstrip("#")
            por_corte[(rodada, numero)] = {
                "rodada": rodada,
                "numero": numero,
                "veredito": partes[3].replace("-", " ").strip().lower(),
                "etiqueta": (partes[4] if len(partes) > 4 else "").strip().lower(),
                "motivo": partes[5] if len(partes) > 5 else "",
            }
    return list(por_corte.values())


def ler_manifestos(data_dir=None) -> dict[tuple[str, str], dict]:
    """O que foi enviado em cada rodada, com os sinais que o motor tinha gravado.

    Sem isto o caderno é uma lista de reclamações sem endereço: dá para saber
    que ele reprovou seis cortes por "final cortado", mas não se o motor tinha
    achado aqueles seis fechados. É a diferença entre "aperte este parafuso" e
    "o parafuso está solto em algum lugar da máquina".
    """
    pasta = _pasta("vereditos", data_dir)
    if not pasta.is_dir():
        return {}
    enviados: dict[tuple[str, str], dict] = {}
    for arquivo in sorted(pasta.glob("*.manifesto.json")):
        try:
            dados = json.loads(arquivo.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        rodada = str(dados.get("rodada") or arquivo.stem.split(".")[0])
        for corte in dados.get("cortes") or []:
            numero = str(corte.get("numero") or "").lstrip("#")
            if numero:
                enviados[(rodada, numero)] = corte
    return enviados


def ler_cortes_do_editor(data_dir=None) -> list[dict]:
    """Os cortes que ELE fez à mão. O gabarito que não depende do CHUB.

    Formato, uma linha por corte:

        2026-09-05 14:02 | dQw4w9WgXcQ | 754.0 | 812.5 | a headline que ele usou

    É pouca coisa de escrever e é a coisa mais valiosa do sistema inteiro: diz
    onde um assunto começa e termina numa live que o Acervo nunca viu.
    """
    pasta = _pasta("cortes_do_editor", data_dir)
    if not pasta.is_dir():
        return []
    cortes = []
    for arquivo in sorted(pasta.glob("*.txt")):
        for linha in arquivo.read_text(encoding="utf-8", errors="replace").splitlines():
            partes = [p.strip() for p in linha.split("|")]
            if len(partes) < 4:
                continue
            try:
                inicio, fim = float(partes[2]), float(partes[3])
            except ValueError:
                continue
            if fim <= inicio:
                continue
            cortes.append({
                "quando": partes[0],
                "video": partes[1],
                "start": inicio,
                "end": fim,
                "headline": partes[4] if len(partes) > 4 else "",
            })
    return cortes


# O que a lista de motivos da TELA quer dizer, na mesma língua das etiquetas do
# WhatsApp. Ele escolhe do menu ao aprovar ou rejeitar um corte, e o motivo já
# fica gravado no banco — não precisa digitar nada em lugar nenhum.
O_MENU_DA_TELA = {
    "no_payoff": "fim",            # "Não conclui o raciocínio"
    "starts_late": "abertura",     # "Começa no meio da fala"
    "wrong_speaker": "locutor",    # "Orador errado ou incerto"
    "missing_context": "contexto",  # "Sem contexto suficiente"
    "duplicate": "repetido",       # "Repetido ou parecido com outro"
    "audio_overlap": "repetido",   # "Áudio sobreposto ou confuso"
}

# Os nomes que a tela usava em versões anteriores. Aparecem nos bancos que ele
# guardou dos outros notebooks — dois dos trinta e sete vereditos recuperados em
# 08/09 vêm com `sem_contexto` e `sem_payoff`.
#
# Ficam SEPARADOS do menu de hoje de propósito. `O_MENU_DA_TELA` é a lista da
# tela, e existe um teste que exige que toda opção de lá chegue num peso — se
# esses nomes entrassem ali, o teste passaria a cobrar deles uma opção na tela
# que não existe mais, e a proteção viraria ruído.
#
# Um veredito que ele já deu não pode valer menos por ter sido dado numa versão
# antiga do programa.
MOTIVOS_DE_VERSOES_ANTIGAS = {
    "sem_payoff": "fim",
    "sem_contexto": "contexto",
    "comeca_tarde": "abertura",
    "locutor_errado": "locutor",
}


def etiqueta_do_motivo(codigo) -> str:
    """A etiqueta de um motivo, venha ele da tela de hoje ou de uma antiga."""
    chave = str(codigo or "").strip().lower()
    return O_MENU_DA_TELA.get(chave) or MOTIVOS_DE_VERSOES_ANTIGAS.get(chave, "")


def ler_do_programa() -> tuple[list[dict], dict]:
    """Os vereditos que ele deu na TELA, e o que o motor achava de cada corte.

    Esta é a fonte principal quando ele trabalha sozinho, sem o Hermes. E é a
    melhor das duas, porque não depende de ninguém transcrever nada: ele já
    aperta Aprovar ou Rejeitar e escolhe o motivo na lista, e o programa já
    guarda isso no banco junto com os sinais que o motor gravou naquele corte.

    O manifesto — que o Hermes precisa escrever à mão quando ele revisa pelo
    WhatsApp — aqui existe de graça: `score_factors` é o que o motor achava, e
    está na mesma linha do corte.
    """
    try:
        import sqlite3

        from config import DB_PATH
    except ImportError:
        return [], {}
    if not Path(DB_PATH).is_file():
        return [], {}

    vereditos: list[dict] = []
    enviados: dict[tuple[str, str], dict] = {}
    try:
        conn = sqlite3.connect(f"file:{DB_PATH}?mode=ro", uri=True)
        conn.row_factory = sqlite3.Row
        # A última decisão de cada corte, do mesmo jeito que o caderno de papel:
        # ele pode mudar de ideia, e a última é a que vale.
        linhas = conn.execute(
            """SELECT f.clip_id, f.action, f.reason_code, c.score_factors
                 FROM clip_feedback f
                 JOIN clips c ON c.id = f.clip_id
                WHERE f.id IN (SELECT MAX(id) FROM clip_feedback GROUP BY clip_id)
                  AND f.action IN ('approved', 'rejected', 'needs_review')"""
        ).fetchall()
        conn.close()
    except (sqlite3.Error, OSError):
        return [], {}

    for linha in linhas:
        numero = str(linha["clip_id"])
        try:
            sinais = json.loads(linha["score_factors"] or "{}")
        except ValueError:
            sinais = {}
        if not isinstance(sinais, dict):
            sinais = {}
        # O APRENDIZADO LIA A GAVETA ERRADA, E NÃO CORRIGIA NADA
        #
        # `score_factors` guarda duas coisas diferentes no mesmo lugar: as NOTAS
        # do ranqueamento (hook, flow, value, clarity...) na raiz, e as MARCAS
        # do corte (`payoff_complete`, `starts_mid_sentence`, ...) dentro de
        # `_review_flags`. Eu só olhava a raiz.
        #
        # Medido no banco do editor em 08/09, com 90 vereditos dados por ele:
        #
        #     manifestos lidos ....... 90
        #     casos contados ......... 0    <- nenhum sinal batia
        #     ajustes no motor ....... {}
        #
        # Quatro dos cinco sinais que este arquivo procura estão em
        # `_review_flags`, presentes em 279 cortes. Ou seja: ele apertou
        # Aprovar e Rejeitar noventa vezes e o motor **não mudou uma vírgula**,
        # sem nenhum erro aparecer na tela.
        marcas = sinais.get("_review_flags")
        if isinstance(marcas, dict):
            sinais = {**marcas, **{k: v for k, v in sinais.items() if not k.startswith("_")}}
        vereditos.append({
            "rodada": "programa",
            "numero": numero,
            "veredito": "ok" if linha["action"] == "approved" else "nao",
            "etiqueta": etiqueta_do_motivo(linha["reason_code"]),
            "motivo": str(linha["reason_code"] or ""),
        })
        enviados[("programa", numero)] = {"numero": numero, "sinais": sinais}
    return vereditos, enviados


def _acertos_e_erros(vereditos: list[dict], enviados: dict) -> dict[str, dict]:
    """Onde o motor acusou defeito que não havia, e onde não viu o que havia.

    Duas contas por sinal, e elas puxam para lados opostos:

        alarme falso  o motor marcou o defeito e o editor aprovou assim mesmo
        cegueira      o motor não marcou nada e o editor achou o defeito

    Cegueira faz o peso subir; alarme falso faz descer. Um sinal com muito dos
    dois não está mal calibrado — está medindo a coisa errada, e nenhum peso
    conserta isso. Por isso os dois números aparecem separados no relatório.
    """
    contas: dict[str, dict] = defaultdict(
        lambda: {"cegueira": 0, "alarme_falso": 0, "casos": 0}
    )
    for veredito in vereditos:
        corte = enviados.get((veredito["rodada"], veredito["numero"]))
        if not corte:
            continue
        sinais = corte.get("sinais") or {}
        aprovado = veredito["veredito"] == "ok"
        etiqueta = veredito["etiqueta"]

        for nome_etiqueta, (peso, sinal) in O_QUE_CADA_ETIQUETA_CORRIGE.items():
            if sinal not in sinais:
                continue
            bruto = bool(sinais.get(sinal))
            motor_acusou = (not bruto) if sinal in SINAL_LIGADO_E_BOM else bruto
            conta = contas[peso]
            conta["casos"] += 1
            if etiqueta == nome_etiqueta and not motor_acusou:
                conta["cegueira"] += 1
            elif aprovado and motor_acusou and etiqueta != nome_etiqueta:
                # APROVAR MARCANDO O DEFEITO NÃO É DIZER QUE O MOTOR EXAGEROU
                #
                # Perguntei a ele em 08/09 o que quer dizer aprovar um corte
                # marcando um defeito. A resposta: **"tem o defeito, mas dá para
                # usar"**. Ele concorda com o diagnóstico e publica assim mesmo.
                #
                # A regra antiga contava isso como alarme falso, e alarme falso
                # AFROUXA o desconto. Ou seja: ele confirmava que o defeito
                # existe e o motor passava a se importar menos com ele — o
                # oposto exato do que ele quis dizer.
                #
                # No banco dele são oito casos: aprovou marcando `starts_late`
                # três vezes, `no_payoff` uma, `too_long` quatro.
                #
                # Alarme falso agora só conta quando ele aprovou **sem** apontar
                # aquele defeito. Aí sim o motor viu problema onde ele não viu.
                conta["alarme_falso"] += 1
    return dict(contas)


def tudo_que_ele_julgou(data_dir=None) -> tuple[list[dict], dict]:
    """As duas fontes juntas: a tela do programa e o caderno do WhatsApp.

    Ele usa as duas conforme o dia — sozinho no computador aperta os botões;
    fora de casa responde ao Hermes pelo celular. As duas contam a mesma coisa
    e nenhuma delas é o programa se avaliando, que é o que importa.
    """
    da_tela, manifesto_da_tela = ler_do_programa()
    do_caderno = ler_vereditos(data_dir)
    manifesto_do_caderno = ler_manifestos(data_dir)
    return da_tela + do_caderno, {**manifesto_da_tela, **manifesto_do_caderno}


def ajustes(data_dir=None) -> dict[str, float]:
    """Quanto cada peso do motor deve mudar, segundo o julgamento do editor.

    A conta é de uma linha, de propósito:

        ajuste = (cegueira - alarme_falso) / casos  ->  fração do peso atual

    Um sinal em que ele achou seis defeitos que o motor não viu, e nenhum
    exagero, ganha peso. Um sinal que o motor acusa e ele aprova assim mesmo
    perde. Abaixo de `MINIMO_DE_CASOS`, nada se mexe — e nada se mexe em
    silêncio: `explicar()` diz por quê.
    """
    contas = _acertos_e_erros(*tudo_que_ele_julgou(data_dir))
    resultado: dict[str, float] = {}
    for peso, conta in contas.items():
        if conta["casos"] < MINIMO_DE_CASOS:
            continue
        fracao = (conta["cegueira"] - conta["alarme_falso"]) / conta["casos"]
        if abs(fracao) < 0.05:
            continue
        resultado[peso] = max(-TETO, min(TETO, round(fracao * 100, 1)))
    return resultado


def explicar(data_dir=None) -> list[dict]:
    """O mesmo cálculo, com o motivo por extenso — para a tela e para o Hermes."""
    contas = _acertos_e_erros(*tudo_que_ele_julgou(data_dir))
    linhas = []
    for peso, conta in sorted(contas.items()):
        casos = conta["casos"]
        if casos < MINIMO_DE_CASOS:
            motivo = f"só {casos} caso(s); preciso de {MINIMO_DE_CASOS} para mexer"
            ajuste = 0.0
        else:
            fracao = (conta["cegueira"] - conta["alarme_falso"]) / casos
            ajuste = max(-TETO, min(TETO, round(fracao * 100, 1)))
            if abs(fracao) < 0.05:
                motivo = "o motor e o editor concordam; nada a corrigir"
                ajuste = 0.0
            elif ajuste > 0:
                motivo = (
                    f"{conta['cegueira']} vez(es) ele viu o defeito e o motor não; "
                    f"o desconto sobe"
                )
            else:
                motivo = (
                    f"{conta['alarme_falso']} vez(es) o motor acusou e ele aprovou "
                    f"assim mesmo; o desconto desce"
                )
        linhas.append({
            "peso": peso, "ajuste": ajuste, "casos": casos,
            "cegueira": conta["cegueira"], "alarme_falso": conta["alarme_falso"],
            "motivo": motivo,
        })
    return linhas


def gabarito_do_editor(video: str, data_dir=None) -> list[dict[str, Any]]:
    """Os cortes dele num vídeo, no formato de bloco que a régua já lê.

    É isto que faz a régua funcionar numa live de ontem. O Acervo não tem
    aquele vídeo; ele tem — porque cortou. Cada corte dele vira um bloco de
    referência com um corte esperado, e todo o resto do sistema continua igual.
    """
    # As duas fontes do gabarito dele: o arquivo que ele digita e as bordas que
    # ele move na tela. A segunda é a que não dá trabalho, e foi a que ele
    # escolheu quando eu perguntei — por isso ela entra aqui, e não num caminho
    # separado que alguém teria que lembrar de chamar.
    do_arquivo = ler_cortes_do_editor(data_dir)
    da_tela = cortes_ajustados_no_programa()
    cortes = [
        c for c in (do_arquivo + da_tela)
        if video and (c.get("video") == video or video in str(c.get("arquivo") or ""))
    ]
    return [
        {
            "start": round(corte["start"], 2),
            "end": round(corte["end"], 2),
            "dur": round(corte["end"] - corte["start"], 2),
            "cortes": 1,
            "titulo": corte["headline"],
            "q": "",
            "fonte_do_gabarito": "editor",
        }
        for corte in sorted(cortes, key=lambda c: c["start"])
    ]


# ── juntar vereditos de outro computador ────────────────────────────────────


def _identidade(assinatura, inicio, fim, acao, motivo, quando) -> tuple:
    """O que faz um veredito ser o MESMO veredito, em qualquer computador.

    Não dá para usar o número do corte: ele é contado por banco, e o corte 12
    de um notebook é outro corte no outro. O que viaja é o conteúdo — que vídeo,
    que trecho, que decisão, quando foi tomada.
    """
    def numero(valor):
        try:
            return round(float(valor or 0), 2)
        except (TypeError, ValueError):
            return 0.0

    return (
        str(assinatura or ""), numero(inicio), numero(fim),
        str(acao or ""), str(motivo or ""), str(quando or "")[:19],
    )


def juntar_vereditos_de(caminho, destino=None) -> dict[str, Any]:
    """Trazer para cá os vereditos dados em outro computador. Sem apagar nada.

    POR QUE ISTO PRECISOU EXISTIR
    -----------------------------
    O botão que mandava feedback ao GitHub estava quebrado desde que o nome da
    branch entregue mudou — ou seja, **nunca funcionou na prática**. Enquanto
    isso ele revisava cortes nos dois notebooks. Medido nos bancos antigos que
    ele guardou:

        banco de hoje ............ 120 vereditos
        de um notebook antigo ..... 35 vereditos, NENHUM aqui dentro
        de outro ...................2 vereditos, NENHUM aqui dentro

    Trinta e sete julgamentos dele parados em pasta, sem efeito nenhum. Com eles
    juntos, os casos que a calibração conta vão de 79 para 102.

    O QUE ISTO NÃO FAZ, DE PROPÓSITO
    --------------------------------
    Não substitui o banco. `restore_editorial_backup` faz isso, e é a ferramenta
    errada aqui: substituir joga fora o que este computador julgou. Juntar
    preserva os dois lados.

    Também não repete: um veredito que já está aqui é reconhecido pelo conteúdo
    — que vídeo, que trecho, que decisão, quando — e ignorado. Importar duas
    vezes o mesmo arquivo dá o mesmo resultado que importar uma.

    Quando o corte julgado não existe neste computador, ele vem junto, com os
    sinais que o motor tinha gravado. Sem isso o veredito chegaria sem o que o
    motor achava, e a calibração não teria contra o que comparar.
    """
    import sqlite3

    from config import DB_PATH

    alvo = Path(destino or DB_PATH)
    origem = Path(caminho)
    resumo = {"lidos": 0, "novos": 0, "ja_tinha": 0, "ignorados": 0}
    if not origem.is_file():
        raise FileNotFoundError(f"Arquivo não encontrado: {origem}")
    if not alvo.is_file():
        raise FileNotFoundError("Este computador ainda não tem banco editorial.")

    # UMA CÓPIA ANTES DE ESCREVER, SEMPRE
    #
    # Eu entreguei este botão sem rede: ele escreve no banco de vereditos dele e
    # não havia como voltar atrás. Na primeira vez que ele usou, a tela disse
    # "115 vereditos novos; 0 já estavam aqui" — número que na minha bancada dá
    # 0 novos e 115 já presentes, ou seja, alguma coisa não bateu na máquina
    # dele e pode ter entrado repetido. Veredito repetido pesa em dobro na
    # calibração sem ninguém ver.
    #
    # Operação que escreve no julgamento dele não pode existir sem desfazer.
    copia = _guardar_copia_antes_de_juntar(alvo)
    resumo["copia_de_seguranca"] = str(copia) if copia else ""

    consulta = """SELECT f.action, COALESCE(f.reason_code,'') rc, f.created_at,
                         c.start_time s, c.end_time e, c.duration d, c.viral_score v,
                         c.score_factors sf, c.file_path fp, c.editorial_key ek,
                         p.source_signature sig, p.name pname
                    FROM clip_feedback f
                    JOIN clips c ON c.id = f.clip_id
                    JOIN projects p ON p.id = c.project_id
                   WHERE f.action IN ('approved','rejected','needs_review')"""

    de_fora = sqlite3.connect(f"file:{origem}?mode=ro", uri=True)
    de_fora.row_factory = sqlite3.Row
    try:
        linhas = de_fora.execute(consulta).fetchall()
    except sqlite3.Error as erro:
        de_fora.close()
        raise ValueError(f"Não parece um banco do Furia: {str(erro)[:120]}") from erro
    de_fora.close()
    resumo["lidos"] = len(linhas)
    if not linhas:
        return resumo

    aqui = sqlite3.connect(alvo)
    aqui.row_factory = sqlite3.Row
    try:
        conhecidos = {
            _identidade(r["sig"], r["s"], r["e"], r["action"], r["rc"], r["created_at"])
            for r in aqui.execute(consulta).fetchall()
        }
        # A ASSINATURA DO VÍDEO TEM QUE SOBREVIVER À IMPORTAÇÃO
        #
        # A primeira versão criava um projeto novo com assinatura
        # "importado-<hora>". Isso quebrava a identidade: no reimport, o mesmo
        # veredito chegava com a assinatura ORIGINAL e não batia com a que eu
        # tinha guardado. Medido — importar o mesmo arquivo duas vezes trazia os
        # 35 vereditos duas vezes, e um veredito contado em dobro pesa em dobro
        # na calibração, sem ninguém perceber.
        #
        # Guardando a assinatura original, o veredito é reconhecido de onde quer
        # que venha, e o corte ainda cai no projeto certo quando este computador
        # já conhece aquele vídeo.
        projetos: dict[str, int] = {}

        def projeto_para(assinatura: str) -> int:
            chave = str(assinatura or "")
            if chave in projetos:
                return projetos[chave]
            achado = aqui.execute(
                "SELECT id FROM projects WHERE source_signature = ? LIMIT 1", (chave,)
            ).fetchone()
            if achado:
                projetos[chave] = int(achado["id"])
            else:
                projetos[chave] = aqui.execute(
                    "INSERT INTO projects (name, source_video, source_signature)"
                    " VALUES (?,?,?)",
                    (f"Importado de outro computador ({chave[:16] or 'sem assinatura'})",
                     "importado", chave),
                ).lastrowid
            return projetos[chave]

        for linha in linhas:
            if _identidade(linha["sig"], linha["s"], linha["e"], linha["action"],
                           linha["rc"], linha["created_at"]) in conhecidos:
                resumo["ja_tinha"] += 1
                continue
            projeto_importado = projeto_para(linha["sig"])
            corte = aqui.execute(
                "INSERT INTO clips (project_id, file_path, editorial_key, start_time,"
                " end_time, duration, viral_score, score_factors) VALUES (?,?,?,?,?,?,?,?)",
                (projeto_importado, linha["fp"] or "importado", linha["ek"],
                 linha["s"], linha["e"], linha["d"], linha["v"], linha["sf"]),
            ).lastrowid
            aqui.execute(
                "INSERT INTO clip_feedback (clip_id, action, reason_code, created_at)"
                " VALUES (?,?,?,?)",
                (corte, linha["action"], linha["rc"], linha["created_at"]),
            )
            resumo["novos"] += 1
        aqui.commit()
    finally:
        aqui.close()
    return resumo


def datetime_agora() -> str:
    from datetime import datetime, timezone

    return datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")


def cortes_ajustados_no_programa() -> list[dict]:
    """As bordas que ELE moveu na tela. O gabarito que não precisa ser digitado.

    A ESCOLHA DELE, EM 08/09
    ------------------------
    Perguntei como ele preferia dizer "deveria acabar em 1:24". Ele escolheu
    **arrastar as bordas do corte na tela** — e estava certo: o programa já tem
    esse mecanismo, já grava o começo e o fim corrigidos, e ninguém lia.

    No banco dele há cinco linhas `adjusted`, todas com `start` igual a
    `original_start`: ele apertou e não moveu, ou a tela não deixou mover. O
    caminho existe e nunca carregou nada.

    POR QUE ISTO VALE MAIS QUE UMA ETIQUETA
    ---------------------------------------
    "Não conclui o raciocínio" diz que há um defeito. **Uma borda movida diz
    onde estava o certo** — e para uma live que o Acervo não catalogou, é a
    única resposta certa que existe no mundo. É a mesma coisa que
    `cortes_do_editor` guarda, sem ele precisar digitar nada em arquivo nenhum.

    Só entram bordas que ele REALMENTE moveu. Salvar sem mexer não é gabarito:
    seria o programa se elogiando com o próprio palpite, que é o que a regra do
    NORTE §15 proíbe.
    """
    try:
        import sqlite3

        from config import DB_PATH
    except ImportError:
        return []
    if not Path(DB_PATH).is_file():
        return []

    try:
        conn = sqlite3.connect(f"file:{DB_PATH}?mode=ro", uri=True)
        conn.row_factory = sqlite3.Row
        linhas = conn.execute(
            """SELECT f.adjustments, f.note, f.created_at,
                      c.start_time, c.end_time,
                      p.source_signature, p.source_video
                 FROM clip_feedback f
                 JOIN clips c ON c.id = f.clip_id
                 JOIN projects p ON p.id = c.project_id
                WHERE COALESCE(f.adjustments, '') NOT IN ('', '{}')"""
        ).fetchall()
        conn.close()
    except (sqlite3.Error, OSError):
        return []

    def numero(valor):
        try:
            return float(valor)
        except (TypeError, ValueError):
            return None

    cortes = []
    for linha in linhas:
        try:
            ajuste = json.loads(linha["adjustments"] or "{}")
        except ValueError:
            continue
        if not isinstance(ajuste, dict):
            continue
        inicio, fim = numero(ajuste.get("start")), numero(ajuste.get("end"))
        antes_inicio = numero(ajuste.get("original_start"))
        antes_fim = numero(ajuste.get("original_end"))
        if inicio is None or fim is None or fim <= inicio:
            continue
        # Salvar sem mexer não é correção. Meio segundo é a folga do arrasto.
        mexeu = (
            (antes_inicio is None or abs(inicio - antes_inicio) > 0.5)
            or (antes_fim is None or abs(fim - antes_fim) > 0.5)
        )
        if not mexeu:
            continue
        cortes.append({
            "quando": str(linha["created_at"] or "")[:16],
            "video": str(linha["source_signature"] or ""),
            "arquivo": str(linha["source_video"] or ""),
            "start": inicio,
            "end": fim,
            "headline": str(linha["note"] or "").strip(),
            "movido_no_comeco_s": round(inicio - antes_inicio, 2) if antes_inicio is not None else None,
            "movido_no_fim_s": round(fim - antes_fim, 2) if antes_fim is not None else None,
        })
    return cortes


def _guardar_copia_antes_de_juntar(banco: Path):
    """A cópia que permite desfazer a junção. Escrita antes de qualquer INSERT."""
    import sqlite3
    from datetime import datetime, timezone

    try:
        from config import PERSISTENT_BACKUPS_DIR

        pasta = Path(PERSISTENT_BACKUPS_DIR)
    except ImportError:
        pasta = Path(banco).parent
    try:
        pasta.mkdir(parents=True, exist_ok=True)
        # Milissegundos no nome, e nunca sobrescrever.
        #
        # Com carimbo só até o segundo, desfazer logo depois de juntar gerava o
        # MESMO nome de arquivo: a cópia de segurança do estado anterior era
        # sobrescrita pela do estado atual, e restaurá-la devolvia exatamente o
        # que se queria desfazer. Medido: 144 vereditos antes de desfazer, 144
        # depois. O desfazer não desfazia nada e dizia que sim.
        carimbo = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S-%f")
        destino = pasta / f"antes-de-juntar-{carimbo}.sqlite3"
        while destino.exists():
            carimbo += "x"
            destino = pasta / f"antes-de-juntar-{carimbo}.sqlite3"
        origem = sqlite3.connect(f"file:{banco}?mode=ro", uri=True)
        copia = sqlite3.connect(destino)
        with copia:
            origem.backup(copia)
        copia.close()
        origem.close()
        return destino
    except (OSError, ValueError, ImportError, sqlite3.Error):
        # A cópia é best-effort, mas a falta dela não pode passar em silêncio:
        # sem cópia não há como desfazer, e quem chama precisa saber disso.
        return None


def desfazer_ultima_juncao(destino=None) -> dict:
    """Voltar o banco para antes da última junção de vereditos.

    Sem isto, uma junção que trouxe repetido é irreversível — e o editor
    descobriria só quando o motor começasse a errar mais, sem ligar uma coisa à
    outra.
    """
    import shutil

    from config import DB_PATH, PERSISTENT_BACKUPS_DIR

    banco = Path(destino or DB_PATH)
    copias = sorted(
        Path(PERSISTENT_BACKUPS_DIR).glob("antes-de-juntar-*.sqlite3"),
        key=lambda p: p.stat().st_mtime, reverse=True,
    )
    if not copias:
        raise FileNotFoundError("Não há cópia de antes de nenhuma junção.")
    mais_recente = copias[0]
    # A cópia de agora, para o caso de ele querer voltar ao estado de depois.
    _guardar_copia_antes_de_juntar(banco)
    shutil.copy2(mais_recente, banco)
    return {"voltou_para": mais_recente.name, "quando": mais_recente.stat().st_mtime}
