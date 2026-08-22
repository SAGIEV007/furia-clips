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


def test_existing_clip_fingerprints_normalize_windows_backslashes(monkeypatch, tmp_path):
    monkeypatch.setattr(database, "DB_PATH", str(tmp_path / "windows-path.sqlite"))
    database.init_db()
    project_id = database.create_project("Windows", r"C:\\NotebookA\\Videos\\live-renan.mp4")
    clip_id = database.save_clip(
        project_id, "exports/clip.mp4", 12.0, 30.0, 18.0, 80, True, 0, "Trecho com contexto completo."
    )
    database.save_clip_feedback(clip_id, "approved")

    fingerprints = database.get_existing_clip_fingerprints(r"D:\\NotebookB\\Downloads\\live-renan.mp4")

    assert len(fingerprints) == 1
    assert fingerprints[0]["start"] == 12.0
    assert fingerprints[0]["review_status"] == "approved"


def test_existing_clip_fingerprints_match_bare_source_basename(monkeypatch, tmp_path):
    monkeypatch.setattr(database, "DB_PATH", str(tmp_path / "basename.sqlite"))
    database.init_db()
    project_id = database.create_project("Basename", "live-renan.mp4")
    clip_id = database.save_clip(
        project_id, "exports/clip.mp4", 45.0, 75.0, 30.0, 78, True, 0, "Trecho completo."
    )
    database.save_clip_feedback(clip_id, "approved")

    fingerprints = database.get_existing_clip_fingerprints("D:/NotebookB/Videos/live-renan.mp4")

    assert len(fingerprints) == 1
    assert fingerprints[0]["start"] == 45.0
    assert fingerprints[0]["review_status"] == "approved"


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


def test_source_signature_changes_when_same_path_content_changes(tmp_path):
    source = tmp_path / "replaceable.mp4"
    source.write_bytes(b"video-original" * 200000)
    original = database.get_source_signature(str(source))

    source.write_bytes(b"video-substituido" * 200000)
    replaced = database.get_source_signature(str(source))

    assert original
    assert replaced
    assert replaced != original


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
