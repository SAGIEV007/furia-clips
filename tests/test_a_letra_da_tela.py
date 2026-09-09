"""Nenhum texto que ele lê pode ficar abaixo de 12 pixels.

MEDIDO NA TELA DELE, 1366 × 768
--------------------------------
Antes:

     9px      8 pedaços de texto
    10px     91
    11px    127     <- 226 pedaços em 11 px ou menos
    12px    102
    13px     81

Duzentos e vinte e seis pedaços de texto em 11 px ou menos, num notebook, num
programa em que ele passa o dia. Depois: zero, fora do caso proposital abaixo.

A RAIZ ERA A ESCALA, NÃO AS DECLARAÇÕES SOLTAS
-----------------------------------------------
Havia 423 `font-size` escritos à mão abaixo de 12 px, e eles foram elevados. Mas
o que produzia a maior parte da letra miúda era a escala do projeto:

    --text-xs: 10px  ->  12px
    --text-sm: 11px  ->  13px
    --text-base: 13px -> 14px

Consertar a escala é consertar tudo que a usa DIREITO; elevar declaração solta
só alcança quem não a usava.

O CASO QUE NÃO É DEFEITO
------------------------
`.run-bar-step` tem `font-size: 0`. Isso não é letra miúda — é o jeito de
esconder o rótulo e mostrar só a marca da etapa. Zero não é "pequeno demais para
ler": é "não é para ler". Mexer nele quebraria a barra de progresso.
"""

import re
import unittest
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
PISO_PX = 12.0

# Tamanho zero é técnica de esconder texto, não legibilidade. Estas são as
# classes que o usam de propósito; qualquer outra que apareça precisa de
# justificativa escrita antes de entrar aqui.
ESCONDER_DE_PROPOSITO = {"run-bar-step"}


def _folhas():
    return sorted((RAIZ / "static" / "css").glob("*.css"))


def _em_pixels(valor: str, unidade: str) -> float | None:
    numero = float(valor)
    if unidade == "px":
        return numero
    if unidade == "rem":
        return numero * 16
    return None  # `em` depende do pai; não dá para julgar sem contexto


class NenhumTamanhoDeclaradoAbaixoDoPiso(unittest.TestCase):
    def test_as_folhas_nao_declaram_letra_miuda(self):
        miudas = []
        for folha in _folhas():
            texto = folha.read_text(encoding="utf-8")
            for linha, conteudo in enumerate(texto.splitlines(), start=1):
                for achado in re.finditer(r"font-size:\s*([0-9.]+)(px|rem|em)", conteudo):
                    px = _em_pixels(achado.group(1), achado.group(2))
                    # `font-size: 0` é esconder, não encolher — e é pego pelo
                    # teste seguinte, que cobra a justificativa.
                    if px is None or px == 0 or px >= PISO_PX:
                        continue
                    miudas.append(f"{folha.name}:{linha} -> {achado.group(0)}")

        self.assertEqual(miudas, [], "letra abaixo de 12px voltou:\n  " + "\n  ".join(miudas[:15]))

    def test_a_escala_do_projeto_comeca_em_doze(self):
        """Era daqui que vinha a maior parte: `--text-xs: 10px`."""
        for folha in _folhas():
            texto = folha.read_text(encoding="utf-8")
            for achado in re.finditer(r"(--text-[a-z]+):\s*([0-9.]+)px", texto):
                self.assertGreaterEqual(
                    float(achado.group(2)), PISO_PX,
                    f"{folha.name}: {achado.group(1)} está em {achado.group(2)}px",
                )


class OTamanhoZeroPrecisaDeJustificativa(unittest.TestCase):
    def test_so_as_classes_conhecidas_escondem_texto(self):
        """Zero é legítimo para esconder rótulo, e perigoso por engano."""
        suspeitas = []
        for folha in _folhas():
            texto = folha.read_text(encoding="utf-8")
            for achado in re.finditer(r"([^{}]+)\{[^{}]*font-size:\s*0(?:px|rem)?\s*[;}]",
                                      texto):
                seletor = achado.group(1).strip().splitlines()[-1].strip()
                if not any(classe in seletor for classe in ESCONDER_DE_PROPOSITO):
                    suspeitas.append(f"{folha.name}: {seletor[:60]}")

        self.assertEqual(suspeitas, [],
                         "font-size: 0 fora das classes que escondem de propósito:\n  "
                         + "\n  ".join(suspeitas[:10]))


class OSmallDoNavegadorNaoManda(unittest.TestCase):
    """Sem regra própria, `<small>` sai em 11,25 px — e o que está dentro dele é
    explicação que ele lê: "Útil para lives longas...", "Centraliza o locutor
    detectado em 9:16"."""

    def test_existe_regra_de_base_para_small(self):
        achou = any(
            re.search(r"(?m)^small\s*\{[^}]*font-size", folha.read_text(encoding="utf-8"))
            for folha in _folhas()
        )
        self.assertTrue(achou, "sem regra de base, o <small> volta a 11,25 px")


if __name__ == "__main__":
    unittest.main()
