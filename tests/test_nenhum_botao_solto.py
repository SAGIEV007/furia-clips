"""Nenhum botão da tela pode ser enfeite.

O QUE O EDITOR PEDIU
--------------------
    "é para ser um ecossistema e não apenas um monte de botões que ou não
     funcionam ou não fazem parte do conjunto"

O QUE A AUDITORIA ACHOU
-----------------------
48 botões na tela. Todos ligados no `app.js`. Todos os endereços que a tela
chama existem no `app.py`. **Nenhum botão morto.**

Ou seja: a desconexão que ele sentiu era real, mas nunca esteve no botão. Ela
estava mais fundo, e foi essa a semana inteira:

    marcação de palavra ....  ligada na tela, desligada no banco desde agosto
    Acervo do CHUB .........  buscado, mas o arquivo não tinha id do vídeo
    vereditos ..............  111 dos 169 lidos no campo errado
    segunda moagem .........  um dos dois caminhos nunca consultava o Acervo

Botão ligado a uma função que existe, e a função ligada a nada. É por isso que
este arquivo confere a ponta da tela e os outros conferem a ponta do motor.

ESTE TESTE É BARATO E PERMANENTE
--------------------------------
Ele lê os três arquivos e falha no minuto em que alguém puser um botão sem
ligação ou chamar um endereço que não existe.
"""

import re
import unittest
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
TELA = (RAIZ / "templates" / "index.html").read_text(encoding="utf-8")
SCRIPT = (RAIZ / "static" / "js" / "app.js").read_text(encoding="utf-8")
SERVIDOR = (RAIZ / "app.py").read_text(encoding="utf-8")


def _rotas_do_servidor() -> set[str]:
    rotas = set()
    for achado in re.finditer(r'@app\.(?:route|get|post)\(\s*[\'"]([^\'"]+)', SERVIDOR):
        rotas.add(achado.group(1))
    return rotas


def _sem_interpolacao(texto: str) -> str:
    """`${...}` vira curinga, contando chaves.

    Um `${a ? 'x' : 'y'}` tem aspas e interrogação dentro, e uma expressão
    regular ingênua para no primeiro `}` — ou pior, para na aspa e leva metade
    da expressão para dentro da URL. Contar chave é a única forma que aguenta.
    """
    saida, posicao = [], 0
    while posicao < len(texto):
        if texto.startswith("${", posicao):
            profundidade, passo = 1, posicao + 2
            while passo < len(texto) and profundidade:
                profundidade += {"{": 1, "}": -1}.get(texto[passo], 0)
                passo += 1
            saida.append("\x00")
            posicao = passo
        else:
            saida.append(texto[posicao])
            posicao += 1
    return "".join(saida)


def _enderecos_chamados_pela_tela() -> set[str]:
    """As URLs que o `app.js` chama, com os pedaços variáveis normalizados."""
    chamadas = set()
    for achado in re.finditer(r"fetch\(\s*`([^`]*)`", SCRIPT):
        limpo = _sem_interpolacao(achado.group(1))
        if limpo.startswith("/"):
            chamadas.add(limpo)
    for achado in re.finditer(r"""fetch\(\s*(['"])((?:[^'"\\]|\\.)*)\1""", SCRIPT):
        if achado.group(2).startswith("/"):
            chamadas.add(achado.group(2))
    return chamadas


class TodoBotaoTemLigacao(unittest.TestCase):
    def test_todo_botao_com_id_e_procurado_pelo_javascript(self):
        botoes = sorted(set(re.findall(r'<button[^>]*\bid="([^"]+)"', TELA)))
        self.assertGreater(len(botoes), 30, "a tela deveria ter dezenas de botões")

        soltos = [
            identificador for identificador in botoes
            if f'getElementById("{identificador}")' not in SCRIPT
            and f"getElementById('{identificador}')" not in SCRIPT
            and f'"{identificador}"' not in SCRIPT
            and f"'{identificador}'" not in SCRIPT
        ]
        self.assertEqual(soltos, [], f"botão na tela que o programa nunca procura: {soltos}")


class TodoEnderecoChamadoExiste(unittest.TestCase):
    def test_a_tela_nao_chama_endereco_que_o_servidor_nao_tem(self):
        rotas = _rotas_do_servidor()
        self.assertGreater(len(rotas), 50)

        # O caminho de cada rota, com `<int:clip_id>` virando um segmento
        # qualquer — é assim que a tela o preenche.
        caminhos = [re.sub(r"<[^>]+>", "\x01", rota.rstrip("/")) for rota in rotas]

        orfaos = []
        for endereco in sorted(_enderecos_chamados_pela_tela()):
            alvo = endereco.split("?")[0].rstrip("/")
            # O curinga da tela casa com qualquer coisa sem barra — inclusive
            # com nada, porque um `${params}` no fim é a query string, que já
            # foi cortada acima.
            padrao = re.compile(
                "^" + "[^/]*".join(re.escape(parte) for parte in alvo.split("\x00")) + "$"
            )
            if not any(padrao.match(caminho.replace("\x01", "1")) for caminho in caminhos):
                orfaos.append(endereco.replace("\x00", "${...}"))

        self.assertEqual(orfaos, [], f"a tela chama endereço que não existe: {orfaos}")


class OsBotoesQueEuLiguEiNestaSemana(unittest.TestCase):
    """Os que nasceram de um defeito medido. Se sumirem, o defeito volta."""

    def test_continuam_todos_na_tela(self):
        for identificador, porque in [
            ("btnVincularAoLink", "sem ele seis dos sete arquivos dele não acham o CHUB"),
            ("btnJuntarVereditos", "sem ele o veredito do outro notebook fica parado em pasta"),
            ("btnDesfazerJuncao", "operação que escreve no julgamento dele precisa de volta"),
            ("btnPrepararParaOClaude", "ele perguntou onde ficava o arquivo; a resposta é um botão"),
        ]:
            self.assertIn(f'id="{identificador}"', TELA, porque)


if __name__ == "__main__":
    unittest.main()
