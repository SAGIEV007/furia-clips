from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]


class WindowsBootstrapTests(unittest.TestCase):
    def test_launcher_invokes_bootstrap_and_uses_runtime_paths(self):
        launcher = (ROOT / "run.bat").read_text(encoding="utf-8")
        self.assertIn("bootstrap_windows.ps1", launcher)
        self.assertIn("python_path.txt", launcher)
        self.assertIn("ffmpeg_path.txt", launcher)
        self.assertIn("venv\\Scripts\\python.exe", launcher)
        self.assertIn("validate_runtime", launcher)
        self.assertIn("show_log", launcher)
        self.assertIn("run-latest.log", launcher)

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

    def test_setup_explains_gemini_is_optional(self):
        setup = (ROOT / "_setup.py").read_text(encoding="utf-8")
        self.assertIn("continuara funcionando localmente", setup)
        self.assertIn('deps_version = "v7_auto_backend"', setup)


if __name__ == "__main__":
    unittest.main()
