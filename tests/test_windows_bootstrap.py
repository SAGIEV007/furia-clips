from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]


class WindowsBootstrapTests(unittest.TestCase):
    def test_launcher_invokes_bootstrap_and_uses_runtime_paths(self):
        launcher = (ROOT / "run.bat").read_text(encoding="utf-8")
        self.assertIn("bootstrap_windows.ps1", launcher)
        self.assertIn("python_path.txt", launcher)
        self.assertIn("ffmpeg_path.txt", launcher)
        self.assertIn("ffprobe_path.txt", launcher)
        self.assertIn("FFPROBE_EXE", launcher)
        self.assertIn("venv\\Scripts\\python.exe", launcher)
        self.assertIn("validate_runtime", launcher)
        self.assertIn('show_log', launcher)
        self.assertIn('run-latest.log', launcher)
        self.assertIn('open_browser_windows.ps1', launcher)
        self.assertIn('127.0.0.1:3001', launcher)
        self.assertIn('-TimeoutSeconds 120', launcher)

    def test_bootstrap_has_python_and_ffmpeg_routes(self):
        bootstrap = (ROOT / "bootstrap_windows.ps1").read_text(encoding="utf-8")
        self.assertIn('Python.Python.3.12', bootstrap)
        self.assertIn('Gyan.FFmpeg', bootstrap)
        self.assertIn('ffprobe.exe', bootstrap)
        self.assertIn('PrependPath=1', bootstrap)
        self.assertIn('Start-Transcript', bootstrap)
        self.assertIn('bootstrap-latest.log', bootstrap)
        self.assertIn('System.IO.File]::WriteAllText', bootstrap)
        self.assertIn('UTF8Encoding($false)', bootstrap)
        self.assertGreaterEqual(bootstrap.count('Split-Path -Parent $ffmpeg'), 2)

    def test_browser_helper_waits_and_prefers_opera(self):
        helper = (ROOT / "scripts" / "open_browser_windows.ps1").read_text(encoding="utf-8")
        self.assertIn("Invoke-WebRequest", helper)
        self.assertIn("opera.exe", helper)
        self.assertIn("TimeoutSeconds", helper)
        self.assertIn("Get-RegistryExecutable", helper)
        self.assertIn("Start-Process", helper)

    def test_requirements_include_public_source_downloader(self):
        requirements = (ROOT / "requirements.txt").read_text(encoding="utf-8")
        self.assertIn("yt-dlp", requirements)

    def test_setup_explains_gemini_is_optional(self):
        setup = (ROOT / "_setup.py").read_text(encoding="utf-8")
        self.assertIn("Gemini Online e a prioridade", setup)
        self.assertIn("legenda publica", setup)
        self.assertIn("fallback local", setup)
        self.assertIn('deps_version = "v9_sources_gemini_fast_transcription"', setup)
        self.assertIn('python_exe, "-m", "pip"', setup)
        main_start = setup.find('def main():')
        main_block = setup[main_start:]
        self.assertNotIn('prompt_gemini_key()', main_block)


if __name__ == "__main__":
    unittest.main()
