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
