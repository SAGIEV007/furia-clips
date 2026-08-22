import json

from modules.approved_clip_priors import load_feature_records
from modules.learning_importer import import_review_dataset


def test_import_review_dataset_accepts_csv_and_emits_sanitized_features(tmp_path):
    source = tmp_path / "review.csv"
    source.write_text(
        "decision,duration,format_id,hook_family,topic,headline,transcript,file_path\n"
        "approved,34,square_alfinetei,tese,seguranca,ALERTA: A VERDADE,transcricao privada,/private/video.mp4\n"
        "rejected,120,vertical_916,conversa,seguranca,Uma fala,transcricao privada,/private/video2.mp4\n"
        "pending,40,square_alfinetei,tese,seguranca,ignorar,raw,/private/video3.mp4\n",
        encoding="utf-8",
    )
    manifest = import_review_dataset(source, output_dir=tmp_path / "learning")
    assert manifest["input_rows"] == 3
    assert manifest["accepted_rows"] == 2
    assert manifest["rejected_rows"] == 1
    assert manifest["raw_transcript_or_media_stored"] is False
    output = (tmp_path / "learning" / "approved_clip_features.jsonl").read_text(encoding="utf-8")
    assert "transcricao privada" not in output
    assert "/private/video" not in output
    assert "ALERTA" not in output
    rows = load_feature_records(tmp_path / "learning" / "approved_clip_features.jsonl")
    assert len(rows) == 2
    assert rows[0]["headline_shape"]["attention_word"] is True


def test_import_review_dataset_rejects_unknown_extension(tmp_path):
    source = tmp_path / "review.txt"
    source.write_text("not a supported dataset", encoding="utf-8")
    try:
        import_review_dataset(source, output_dir=tmp_path / "learning")
    except ValueError as exc:
        assert "Formato não suportado" in str(exc)
    else:
        raise AssertionError("formato inválido foi aceito")



def test_import_review_dataset_strict_schema_reports_errors_and_sample_sizes(tmp_path):
    source = tmp_path / "layer3.jsonl"
    source.write_text("\n".join([
        '{"clip_id":"c1","label":"approved","duration_sec":38.2,"editorial_family":"politico","format_id":"vertical_916","headline_sanitized":"ALERTA SOBRE A PROPOSTA","transcript":"texto privado"}',
        '{"clip_id":"c2","label":"rejected","duration_sec":12,"rejection_reason":"mid_sentence","path":"/private/video.mp4"}',
        '{"clip_id":"c3","label":"maybe","duration_sec":20}',
        '{"clip_id":"c4","label":"approved","duration_sec":700}',
    ]) + "\n", encoding="utf-8")
    manifest = import_review_dataset(source, output_dir=tmp_path / "learning", strict=True)
    assert manifest["accepted"] == 2
    assert manifest["rejected_rows"] == 2
    assert manifest["sample_size_approved"] == 1
    assert manifest["sample_size_rejected"] == 1
    assert manifest["priors_updated"] is True
    assert {error["reason"] for error in manifest["errors"]} == {"invalid_label", "invalid_duration_or_schema"}
    output = (tmp_path / "learning" / "approved_clip_features.jsonl").read_text(encoding="utf-8")
    assert "texto privado" not in output
    assert "/private/video" not in output
    assert "ALERTA SOBRE" not in output


def test_import_review_rows_deduplicates_last_write_and_keeps_only_features(tmp_path):
    from modules.learning_importer import import_review_rows

    manifest = import_review_rows([
        {"clip_id": "same", "label": "approved", "duration_sec": 30, "format_id": "vertical_916"},
        {"clip_id": "same", "label": "rejected", "duration_sec": 40, "format_id": "square_alfinetei", "raw_text": "private"},
        {"clip_id": "other", "label": "approved", "duration_sec": 35, "format_id": "unknown"},
    ], output_dir=tmp_path / "learning", strict=True)
    assert manifest["accepted"] == 2
    assert manifest["deduplicated_rows"] == 1
    assert manifest["sample_size_approved"] == 1
    assert manifest["sample_size_rejected"] == 1
    rows = load_feature_records(tmp_path / "learning" / "approved_clip_features.jsonl")
    assert {row["clip_id"] for row in rows} == {"same", "other"}
    assert next(row for row in rows if row["clip_id"] == "same")["decision"] == "rejected"
