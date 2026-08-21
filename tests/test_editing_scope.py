import inspect

import app as app_module
import config


def test_word_timestamps_are_enabled_by_default_for_editorial_precision():
    assert config.DEFAULT_SETTINGS["whisper_word_timestamps"] is True


def test_editing_pipeline_disables_non_editing_metadata_by_default():
    assert config.DEFAULT_SETTINGS["generate_seo_metadata"] is False
    source = inspect.getsource(app_module.api_process_complete)
    assert 'settings.get("generate_seo_metadata", False)' in source
    assert "Metadados de publicação desativados" in source
