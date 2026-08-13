"""Local desktop dialogs used by the loopback-only UI.

On Windows the dialog runs in a dedicated PowerShell STA process so Flask's
worker thread never owns a GUI toolkit. On other platforms we use Tkinter when
available and return a descriptive error otherwise.
"""

from __future__ import annotations

import os
import platform
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
WINDOWS_DIALOG = ROOT / "scripts" / "native_dialog.ps1"


class DialogError(RuntimeError):
    """Raised when a native dialog cannot be opened."""


def _existing_dir(initial_path: str | None) -> str:
    if initial_path:
        candidate = Path(initial_path).expanduser()
        if candidate.exists() and candidate.is_dir():
            return str(candidate.resolve())
    return str(Path.home())


def choose_path(mode: str = "folder", initial_path: str | None = None, title: str = "Selecionar") -> str:
    if mode not in {"folder", "file"}:
        raise DialogError("Modo de diálogo inválido")

    if platform.system() == "Windows":
        if not WINDOWS_DIALOG.exists():
            raise DialogError("Script de diálogo nativo não encontrado")
        command = [
            "powershell.exe",
            "-NoProfile",
            "-STA",
            "-ExecutionPolicy",
            "Bypass",
            "-File",
            str(WINDOWS_DIALOG),
            "-Mode",
            mode,
            "-InitialPath",
            _existing_dir(initial_path),
            "-Title",
            title,
        ]
        result = subprocess.run(command, capture_output=True, text=True, timeout=120)
        if result.returncode != 0:
            raise DialogError(result.stderr.strip() or "Falha ao abrir diálogo nativo")
        return result.stdout.strip().splitlines()[-1] if result.stdout.strip() else ""

    try:
        import tkinter as tk
        from tkinter import filedialog
    except Exception as exc:
        raise DialogError("Tkinter não está disponível neste sistema") from exc

    root = tk.Tk()
    root.withdraw()
    root.attributes("-topmost", True)
    try:
        if mode == "folder":
            selected = filedialog.askdirectory(
                parent=root,
                initialdir=_existing_dir(initial_path),
                title=title,
                mustexist=False,
            )
        else:
            selected = filedialog.askopenfilename(
                parent=root,
                initialdir=_existing_dir(initial_path),
                title=title,
                filetypes=[
                    ("Vídeos e transcrições", "*.mp4 *.mkv *.avi *.mov *.webm *.flv *.wmv *.txt *.srt *.vtt"),
                    ("Todos os arquivos", "*.*"),
                ],
            )
    finally:
        root.destroy()
    return selected or ""


def open_local_path(path: str) -> None:
    target = str(Path(path).expanduser().resolve())
    if not os.path.exists(target):
        raise FileNotFoundError(target)
    system = platform.system()
    if system == "Windows":
        os.startfile(target)  # type: ignore[attr-defined]
    elif system == "Darwin":
        subprocess.Popen(["open", target])
    else:
        subprocess.Popen(["xdg-open", target])
