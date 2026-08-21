from unittest.mock import patch

from modules.ai_backend import AIBackend
from modules.headline_studio import FORMAT_VERTICAL, generate_artwork_copy


TRANSCRIPT = """1
00:00:00,000 --> 00:00:04,000
Hoje o deputado precisa de cada vez mais emenda

2
00:00:04,000 --> 00:00:08,000
A emenda aumenta o custo do voto para ele

3
00:00:08,000 --> 00:00:12,000
A emenda deve ser vinculada às políticas públicas

4
00:00:12,000 --> 00:00:16,000
O parlamentar quer emenda para fazer a entrega da obra
"""


def test_auto_prefere_gemini_quando_a_chave_existe():
    backend = AIBackend("auto", {"gemini_api_key": "gemini-test-key", "ollama_url": "unused"})
    with patch.object(backend, "_generate_gemini", return_value='{"ok": true}') as gemini, patch.object(
        backend, "_generate_ollama", return_value='{"ollama": true}'
    ) as ollama:
        result = backend.generate("prompt", "system")
    assert result == '{"ok": true}'
    gemini.assert_called_once()
    ollama.assert_not_called()
    assert backend.last_provider == ""


def test_auto_faz_fallback_para_ollama_se_gemini_nao_responder():
    backend = AIBackend("auto", {"gemini_api_key": "gemini-test-key"})
    with patch.object(backend, "_generate_gemini", return_value=""), patch.object(
        backend, "_generate_ollama", return_value='{"ollama": true}'
    ):
        result = backend.generate("prompt", "system")
    assert result == '{"ollama": true}'


def test_legenda_sem_locutor_ainda_gera_headline_sem_atribuicao():
    result = generate_artwork_copy(TRANSCRIPT, preferred_format=FORMAT_VERTICAL, ai_backend=None)
    suggestions = result["formats"][FORMAT_VERTICAL]["suggestions"]
    assert suggestions
    assert all("RENAN" not in item["headline"].upper() for item in suggestions)
    assert all(item["eyebrow"] for item in suggestions)
    assert result["review_flags"]["speaker_unconfirmed"] is True
    assert result["review_flags"]["no_quote_found"] is False
