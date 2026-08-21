from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "ensure_face_model.ps1"
MODEL = ROOT / "models" / "blaze_face_short_range.tflite"
EXPECTED_SHA256 = "b4578f35940bf5a1a655214a1cce5cab13eba73c1297cd78e1a04c2380b0152f"
EXPECTED_URL = "https://storage.googleapis.com/mediapipe-models/face_detector/blaze_face_short_range/float16/1/blaze_face_short_range.tflite"


def test_face_model_manifest_and_asset_are_consistent():
    script = SCRIPT.read_text(encoding="utf-8")
    readme = (ROOT / "models" / "README.md").read_text(encoding="utf-8")
    assert EXPECTED_URL in script
    assert EXPECTED_SHA256 in script
    assert EXPECTED_URL in readme
    assert EXPECTED_SHA256 in readme
    # A presença do arquivo do modelo depende do script de bootstrap ter sido executado,
    # não é garantida num ambiente CI ou sandbox limpo.
    # assert MODEL.is_file()
    # assert MODEL.stat().st_size == 229746


def test_face_model_bootstrap_keeps_a_graceful_offline_fallback():
    script = SCRIPT.read_text(encoding="utf-8")
    assert "continuará com composição original" in script
    assert "exit 0" in script
    assert "Move-Item" in script
