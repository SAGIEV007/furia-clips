"""Garante que a fonte Montserrat usada nas legendas queimadas existe e é válida."""
from pathlib import Path

FONTS_DIR = Path(__file__).resolve().parent.parent / "fonts"
TTF_PATH = FONTS_DIR / "Montserrat-Bold.ttf"


def test_montserrat_bold_ttf_exists():
    assert TTF_PATH.exists(), f"Montserrat-Bold.ttf não encontrado em {TTF_PATH}"


def test_montserrat_bold_ttf_has_minimum_size():
    assert TTF_PATH.stat().st_size > 50_000, "TTF suspeito de estar vazio/corrompido"
