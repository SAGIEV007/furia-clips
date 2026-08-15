import database


def test_existing_clip_fingerprints_match_source_basename_across_checkouts(monkeypatch, tmp_path):
    monkeypatch.setattr(database, "DB_PATH", str(tmp_path / "fingerprints.sqlite"))
    database.init_db()
    project_id = database.create_project("Deduplicação", "C:/NotebookA/Videos/live-renan.mp4")
    approved_id = database.save_clip(
        project_id,
        "exports/clip-aprovado.mp4",
        120.0,
        165.0,
        45.0,
        82,
        True,
        0,
        "Pergunta e resposta completas.",
    )
    database.save_clip_feedback(approved_id, "approved")
    rejected_id = database.save_clip(
        project_id,
        "exports/clip-rejeitado.mp4",
        300.0,
        330.0,
        30.0,
        45,
        False,
        0,
        "Trecho sem conclusão.",
    )
    database.save_clip_feedback(rejected_id, "rejected")

    fingerprints = database.get_existing_clip_fingerprints("D:/NotebookB/Downloads/live-renan.mp4")

    assert len(fingerprints) == 2
    assert {item["review_status"] for item in fingerprints} == {"approved", "rejected"}
    assert {item["start"] for item in fingerprints} == {120.0, 300.0}
    assert all(item["editorial_key"] for item in fingerprints)


def test_existing_clip_fingerprints_ignore_invalid_intervals(monkeypatch, tmp_path):
    monkeypatch.setattr(database, "DB_PATH", str(tmp_path / "invalid.sqlite"))
    database.init_db()
    project_id = database.create_project("Deduplicação inválida", "uploads/fonte.mp4")
    database.save_clip(project_id, "exports/ok.mp4", 10.0, 20.0, 10.0, 70, False, 0, "válido")
    database.save_clip(project_id, "exports/zero.mp4", 50.0, 50.0, 0.0, 20, False, 0, "inválido")

    fingerprints = database.get_existing_clip_fingerprints("/tmp/fonte.mp4")

    assert len(fingerprints) == 1
    assert fingerprints[0]["start"] == 10.0
    assert fingerprints[0]["end"] == 20.0


def test_source_signature_prevents_same_basename_collision(monkeypatch, tmp_path):
    monkeypatch.setattr(database, "DB_PATH", str(tmp_path / "signature.sqlite"))
    database.init_db()
    source_a = tmp_path / "notebook_a" / "live.mp4"
    source_b = tmp_path / "notebook_b" / "live.mp4"
    source_a.parent.mkdir()
    source_b.parent.mkdir()
    source_a.write_bytes(b"video-a" * 200000)
    source_b.write_bytes(b"video-b" * 200000)

    project_a = database.create_project("Fonte A", str(source_a))
    project_b = database.create_project("Fonte B", str(source_b))
    database.save_clip(project_a, "exports/a.mp4", 10.0, 20.0, 10.0, 70, False, 0, "A")
    database.save_clip(project_b, "exports/b.mp4", 10.0, 20.0, 10.0, 70, False, 0, "B")

    fingerprints = database.get_existing_clip_fingerprints(str(source_a))

    assert len(fingerprints) == 1
    assert fingerprints[0]["text"] == "A"
    assert fingerprints[0]["source_signature"]
