import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import app as furia_app
from modules import transcript_archive


class TranscriptArchiveTests(unittest.TestCase):
    def test_quality_report_flags_overlap_and_short_coverage(self):
        report = transcript_archive.validate_transcription(
            {
                "segments": [
                    {"start": 0, "end": 4, "text": "Primeira frase."},
                    {"start": 3, "end": 5, "text": "Sobreposição."},
                ]
            },
            duration=30,
        )
        self.assertEqual(report["quality"], "review_recommended")
        self.assertTrue(report["warnings"])
        self.assertFalse(report["semantic_accuracy_verified"])

    def test_quality_report_flags_timestamps_beyond_source_duration(self):
        report = transcript_archive.validate_transcription(
            {
                "segments": [
                    {"start": 0.0, "end": 12.0, "text": "Trecho que pertence a outra fonte."},
                ],
            },
            duration=10.0,
        )
        self.assertEqual(report["quality"], "needs_attention")
        self.assertIn("excedem a duração", report["issues"][0])
        self.assertFalse(report["semantic_accuracy_verified"])

    def test_quality_report_rejects_non_finite_timestamps(self):
        report = transcript_archive.validate_transcription(
            {
                "segments": [
                    {"start": "nan", "end": 2, "text": "Abertura inválida."},
                    {"start": 3, "end": "inf", "text": "Fechamento inválido."},
                    {"start": 4, "end": 6, "text": "Segmento válido com contexto suficiente."},
                ]
            }
        )
        self.assertEqual(report["valid_segment_count"], 1)
        self.assertEqual(report["quality"], "needs_attention")
        self.assertIn("intervalo inválido", report["issues"][0])

    def test_empty_transcription_has_zero_quality_score(self):
        report = transcript_archive.validate_transcription({"segments": []})
        self.assertEqual(report["quality"], "needs_attention")
        self.assertEqual(report["valid_segment_count"], 0)
        self.assertEqual(report["score"], 0.0)

    def test_archive_listing_revalidates_legacy_json_quality(self):
        with tempfile.TemporaryDirectory() as tempdir:
            directory = Path(tempdir) / "legacy_hash"
            directory.mkdir()
            (directory / "metadata.json").write_text(
                json.dumps({"source": "user_uploaded_transcript", "quality": {"quality": "structurally_ok", "score": 100.0}}),
                encoding="utf-8",
            )
            (directory / "transcript.json").write_text(json.dumps({"segments": []}), encoding="utf-8")
            with patch.object(transcript_archive, "PERSISTENT_TRANSCRIPTS_DIR", tempdir):
                entries = transcript_archive.list_archived_transcriptions()
            self.assertEqual(entries[0]["quality"]["quality"], "needs_attention")
            self.assertEqual(entries[0]["quality"]["score"], 0.0)
            self.assertTrue(entries[0]["quality_revalidated"])

    def test_archive_writes_machine_readable_and_timestamped_files(self):
        with tempfile.TemporaryDirectory() as tempdir:
            transcription = {
                "language": "pt",
                "source": "public_subtitle",
                "segments": [
                    {"start": 0, "end": 2.5, "text": "Olá, Brasil."},
                    {"start": 3, "end": 5, "text": "Esta é uma tese completa."},
                ],
            }
            with patch.object(transcript_archive, "PERSISTENT_TRANSCRIPTS_DIR", tempdir):
                result = transcript_archive.archive_transcription(
                    transcription,
                    source_video="C:/Videos/live.mp4",
                    source="public_subtitle",
                    source_artifact="C:/Videos/live.pt.vtt",
                    project_id=9,
                    duration=5,
                    archive_name="live",
                )
            self.assertTrue(Path(result["json"]).is_file())
            self.assertTrue(Path(result["text"]).is_file())
            self.assertTrue(Path(result["metadata"]).is_file())
            payload = json.loads(Path(result["json"]).read_text(encoding="utf-8"))
            self.assertEqual(payload["archive_metadata"]["project_id"], 9)
            self.assertIn("00:00:00.000", Path(result["text"]).read_text(encoding="utf-8"))

    def test_archive_listing_exposes_only_metadata_and_file_presence(self):
        with tempfile.TemporaryDirectory() as tempdir:
            directory = Path(tempdir) / "sample_hash"
            directory.mkdir()
            (directory / "metadata.json").write_text(
                json.dumps({"source": "whisper", "project_id": 4}), encoding="utf-8"
            )
            (directory / "transcript.txt").write_text("00:00:00.000 frase\n", encoding="utf-8")
            with patch.object(transcript_archive, "PERSISTENT_TRANSCRIPTS_DIR", tempdir):
                entries = transcript_archive.list_archived_transcriptions()
            self.assertEqual(entries[0]["source"], "whisper")
            self.assertTrue(entries[0]["has_text"])
            self.assertFalse(entries[0]["has_json"])


class TranscriptArchiveEndpointTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = furia_app.app.test_client()

    def test_transcript_file_endpoint_blocks_traversal(self):
        response = self.client.get("/api/editorial/transcripts/../metadata.json")
        self.assertIn(response.status_code, {400, 404})

    def test_transcript_list_endpoint_is_available(self):
        with patch.object(furia_app, "list_archived_transcriptions", return_value=[]):
            response = self.client.get("/api/editorial/transcripts")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json()["transcripts"], [])


if __name__ == "__main__":
    unittest.main()
