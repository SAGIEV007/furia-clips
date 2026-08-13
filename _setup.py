"""
Furia Clips - Setup Script
Handles dependency installation and environment setup.
Called by run.bat to avoid Windows CMD parsing issues.
"""
import subprocess
import sys
import os
import shutil


def run_cmd(cmd, check=False, quiet=False):
    """Run a command and return success status."""
    try:
        kw = {"capture_output": quiet, "text": True}
        result = subprocess.run(cmd, **kw)
        return result.returncode == 0
    except Exception:
        return False


def check_ffmpeg():
    """Check if FFmpeg is available."""
    if shutil.which("ffmpeg") and shutil.which("ffprobe"):
        print("[OK] FFmpeg e ffprobe encontrados")
        return True
    else:
        print("[ERRO] FFmpeg/ffprobe nao encontrado no PATH.")
        print("  O launcher tenta instalar automaticamente antes deste setup.")
        return False


def check_gemini_key():
    """Check for Gemini API key in env or .env file."""
    # Check env var first
    api_key = os.environ.get("GEMINI_API_KEY", "")
    if api_key:
        print("[OK] Gemini API key encontrada (variavel de ambiente)")
        _save_gemini_key_to_env(api_key)
        return True

    # Check .env file
    env_file = os.path.join(os.path.dirname(__file__), ".env")
    if os.path.exists(env_file):
        with open(env_file, "r") as f:
            for line in f:
                line = line.strip()
                if line.startswith("GEMINI_API_KEY=") and len(line) > 15:
                    print("[OK] Gemini API key encontrada (.env)")
                    return True

    return False


def prompt_gemini_key():
    """Ask user for Gemini API key on first run."""
    print()
    print("--------------------------------------------------")
    print("   Configuracao do Google Gemini (IA Online)")
    print("--------------------------------------------------")
    print()
    print("  O Gemini Flash e a IA mais inteligente do Furia Clips.")
    print("  E GRATIS - crie sua API key em 30 segundos:")
    print()
    print("  -> https://aistudio.google.com/apikeys")
    print()
    print("  Cole a API key abaixo, ou pressione Enter para pular")
    print("  (voce pode configurar depois na interface do app).")
    print()

    try:
        key = input("  Gemini API Key: ").strip()
    except (EOFError, KeyboardInterrupt):
        key = ""

    if key and len(key) > 10:
        _save_gemini_key_to_env(key)
        print()
        print("[OK] Gemini API key salva! O app usara Gemini como padrao.")
        return True
    else:
        print()
        print("[INFO] Sem Gemini. O app usara Ollama (offline) ou NLP basico.")
        print("  Voce pode configurar o Gemini depois na interface do app.")
        return False


def _save_gemini_key_to_env(api_key):
    """Save Gemini API key to .env file."""
    env_file = os.path.join(os.path.dirname(__file__), ".env")
    lines = []
    found = False

    if os.path.exists(env_file):
        with open(env_file, "r") as f:
            for line in f:
                if line.strip().startswith("GEMINI_API_KEY="):
                    lines.append(f"GEMINI_API_KEY={api_key}\n")
                    found = True
                else:
                    lines.append(line)

    if not found:
        lines.append(f"GEMINI_API_KEY={api_key}\n")

    with open(env_file, "w") as f:
        f.writelines(lines)


def check_ollama():
    """Check if Ollama is available and has the model."""
    print()
    print("--------------------------------------------------")
    print("   Verificando Ollama (IA local/offline)...")
    print("--------------------------------------------------")

    if not shutil.which("ollama"):
        print("[INFO] Ollama nao encontrado; isso e opcional.")
        print("  O programa usara Gemini se configurado ou o ranking NLP local.")
        print("  Se quiser IA local mais avancada depois, instale Ollama em https://ollama.com")
        print("  Apos instalar, rode: ollama pull llama3.2:3b")
        return False

    # Check if ollama is running
    if not run_cmd(["ollama", "list"], quiet=True):
        print("[INFO] Ollama instalado, mas nao esta rodando; isso e opcional.")
        print("  O programa continuara funcionando com Gemini configurado ou NLP local.")
        return False

    print("[OK] Ollama detectado")

    # Check if model exists
    try:
        result = subprocess.run(["ollama", "list"], capture_output=True, text=True)
        if "llama3.2" in result.stdout:
            print("[OK] Modelo llama3.2:3b disponivel")
            return True
    except Exception:
        pass

    print("[Setup] Modelo llama3.2:3b nao encontrado. Baixando...")
    print("  Isso pode demorar alguns minutos - modelo de ~2GB")
    if run_cmd(["ollama", "pull", "llama3.2:3b"]):
        print("[OK] Modelo llama3.2:3b instalado com sucesso!")
        return True
    else:
        print("[INFO] Nao foi possivel baixar o modelo Ollama; continuando com o fallback local.")
        return False


def setup_venv():
    """Create virtual environment if needed."""
    venv_dir = os.path.join(os.path.dirname(__file__), "venv")
    activate = os.path.join(venv_dir, "Scripts", "activate.bat")

    if not os.path.exists(activate):
        print("[Setup] Criando ambiente virtual...")
        if not run_cmd([sys.executable, "-m", "venv", venv_dir]):
            print("[ERRO] Falha ao criar ambiente virtual.")
            return False
        print("[Setup] Ambiente criado!")

    return True


def install_deps():
    """Install dependencies if needed."""
    venv_dir = os.path.join(os.path.dirname(__file__), "venv")
    deps_version = "v7_auto_backend"
    marker = os.path.join(venv_dir, f".deps_{deps_version}")

    if os.path.exists(marker):
        return True  # Already installed

    pip_exe = os.path.join(venv_dir, "Scripts", "pip.exe")
    python_exe = os.path.join(venv_dir, "Scripts", "python.exe")

    if not os.path.exists(pip_exe):
        print("[ERRO] pip nao encontrado no venv.")
        return False

    print("==================================================")
    print("   Instalando/atualizando dependencias...")
    print("==================================================")
    print()

    print("[Setup] Atualizando pip...")
    run_cmd([pip_exe, "install", "--quiet", "--upgrade", "pip"])

    print("[Setup] Instalando faster-whisper...")
    if not run_cmd([pip_exe, "install", "--quiet", "faster-whisper"]):
        print("[AVISO] faster-whisper pode ter falhado")

    print("[Setup] Instalando demais dependencias...")
    req_file = os.path.join(os.path.dirname(__file__), "requirements.txt")
    if not run_cmd([pip_exe, "install", "--quiet", "-r", req_file]):
        print("[AVISO] Algumas dependencias falharam. Tentando individualmente...")
        run_cmd([pip_exe, "install", "flask", "flask-socketio", "gevent",
                 "gevent-websocket", "--quiet"])
        run_cmd([pip_exe, "install", "numpy", "scipy", "Pillow", "requests",
                 "pydub", "python-dotenv", "--quiet"])
        run_cmd([pip_exe, "install", "mediapipe", "--quiet"])
        run_cmd([pip_exe, "install", "ffmpeg-python", "--quiet"])

    print()
    print("[Setup] Baixando modelo Whisper (small)...")
    print("  Pode demorar na primeira vez.")
    print("  Depois disso tudo funciona OFFLINE!")
    run_cmd([python_exe, "-c",
             "from faster_whisper import WhisperModel; "
             "WhisperModel('small', device='cpu', compute_type='int8')"],
            quiet=True)
    print()
    print("[Setup] Instalacao completa!")

    # Mark deps installed (remove old markers)
    for f in os.listdir(venv_dir):
        if f.startswith(".deps_v"):
            try:
                os.remove(os.path.join(venv_dir, f))
            except Exception:
                pass

    # Create new marker
    with open(marker, "w") as f:
        f.write("ok")

    print()
    print("==================================================")
    print("   SETUP COMPLETO! Tudo pronto para uso offline.")
    print("==================================================")
    print()

    return True


def create_workspace():
    """Create workspace directories."""
    base = os.path.dirname(__file__)
    dirs = ["uploads", "processed", "exports", "thumbnails", "cache"]
    for d in dirs:
        path = os.path.join(base, "workspace", d)
        os.makedirs(path, exist_ok=True)


def main():
    """Run full setup."""
    print("==================================================")
    print("   FURIA CLIPS - Corte. Ranqueie. Domine.")
    print("==================================================")
    print()
    print(f"[OK] Python {sys.version.split()[0]} encontrado")

    if not check_ffmpeg():
        print("[ERRO] FFmpeg e ffprobe sao necessarios para cortar e validar videos.")
        return 1

    # Gemini e opcional. O modo automatico usa Gemini somente se uma chave ja existir;
    # caso contrario, tenta Ollama e depois cai para o ranking NLP local.
    if check_gemini_key():
        print("[IA] Gemini configurado; o modo automatico podera usa-lo.")
    else:
        print("[IA] Nenhuma chave Gemini configurada; o Furia Clips continuara funcionando localmente.")

    check_ollama()
    print()

    if not setup_venv():
        input("Pressione Enter para sair...")
        sys.exit(1)

    if not install_deps():
        input("Pressione Enter para sair...")
        sys.exit(1)

    create_workspace()

    # Signal success
    print("SETUP_OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
