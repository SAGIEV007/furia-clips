import modules.clip_selector as _clip_selector_module


def _fast_llm_fallback(*args, **kwargs):
    return []


# Avoid network timeouts when Ollama is not running.
# Tests that need real LLM behavior should patch this explicitly.
_clip_selector_module.ClipSelector._select_with_llm = _fast_llm_fallback
