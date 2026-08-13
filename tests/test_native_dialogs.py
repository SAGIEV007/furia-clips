from types import SimpleNamespace

import pytest

from modules import native_dialogs


def test_decode_process_output_accepts_none_and_utf8_bytes():
    assert native_dialogs._decode_process_output(None) == ""
    assert native_dialogs._decode_process_output("C:/Área") == "C:/Área"
    assert native_dialogs._decode_process_output("C:/Área".encode("utf-8")) == "C:/Área"


def test_windows_dialog_cancel_returns_empty_without_attribute_error(monkeypatch):
    monkeypatch.setattr(native_dialogs.platform, "system", lambda: "Windows")
    monkeypatch.setattr(
        native_dialogs.subprocess,
        "run",
        lambda *args, **kwargs: SimpleNamespace(returncode=0, stdout=None, stderr=None),
    )
    assert native_dialogs.choose_path(mode="folder") == ""


def test_windows_dialog_decodes_utf8_selected_path(monkeypatch):
    monkeypatch.setattr(native_dialogs.platform, "system", lambda: "Windows")
    monkeypatch.setattr(
        native_dialogs.subprocess,
        "run",
        lambda *args, **kwargs: SimpleNamespace(
            returncode=0,
            stdout="C:/Users/nandi/Área de Trabalho/Furia".encode("utf-8"),
            stderr=b"",
        ),
    )
    assert native_dialogs.choose_path(mode="folder") == "C:/Users/nandi/Área de Trabalho/Furia"


def test_windows_dialog_surfaces_real_process_error(monkeypatch):
    monkeypatch.setattr(native_dialogs.platform, "system", lambda: "Windows")
    monkeypatch.setattr(
        native_dialogs.subprocess,
        "run",
        lambda *args, **kwargs: SimpleNamespace(returncode=1, stdout=b"", stderr="falha".encode("utf-8")),
    )
    with pytest.raises(native_dialogs.DialogError, match="falha"):
        native_dialogs.choose_path(mode="folder")
