import json
import os
import time

import pytest

from modules.transcriber_cache_utils import prune_cache, get_cache_stats, CACHE_DIR
from modules.transcriber import Transcriber


@pytest.fixture()
def transcriber(tmp_path, monkeypatch):
    monkeypatch.setattr('modules.transcriber.CACHE_DIR', str(tmp_path))
    monkeypatch.setattr('modules.transcriber_cache_utils.CACHE_DIR', str(tmp_path))
    return Transcriber(model_name="tiny", device="cpu")


def _write_cache(transcriber, audio_path, age_seconds=0):
    cache_key = transcriber._get_cache_key(audio_path)
    path = transcriber._get_cache_path(cache_key)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    payload = {"segments": [], "full_text": "", "language": "pt"}
    with open(path, "w", encoding="utf-8") as f:
        json.dump(payload, f)
    past = time.time() - age_seconds
    os.utime(path, (past, past))
    return path


def test_stats_empty_dir(transcriber, tmp_path):
    stats = transcriber.get_cache_stats()
    assert stats["entries"] == 0
    assert stats["session_hits"] == 0
    assert stats["session_misses"] == 0


def test_hits_and_misses_counted(transcriber, tmp_path):
    audio = os.path.join(str(tmp_path), "audio.mp3")
    open(audio, "w").close()
    _write_cache(transcriber, audio)

    transcriber._load_from_cache(audio)
    transcriber._load_from_cache(audio)
    transcriber._load_from_cache(audio)

    stats = transcriber.get_cache_stats()
    assert stats["session_hits"] == 3
    assert stats["session_misses"] == 0


def test_misses_counted_when_no_cache(transcriber, tmp_path):
    audio = os.path.join(str(tmp_path), "audio.mp3")
    open(audio, "w").close()

    transcriber._load_from_cache(audio)
    transcriber._load_from_cache(audio)

    stats = transcriber.get_cache_stats()
    assert stats["session_hits"] == 0
    assert stats["session_misses"] == 2


def test_prune_removes_old_entries(transcriber, tmp_path):
    old_audio = os.path.join(str(tmp_path), "old.mp3")
    fresh_audio = os.path.join(str(tmp_path), "fresh.mp3")
    open(old_audio, "w").close()
    open(fresh_audio, "w").close()
    old = _write_cache(transcriber, old_audio, age_seconds=60 * 60 * 24 * 10)
    fresh = _write_cache(transcriber, fresh_audio, age_seconds=60)

    result = transcriber.prune_cache(max_age_days=7, max_entries=200)
    assert result["removed"] == 1
    assert result["remaining"] == 1
    assert os.path.exists(fresh)
    assert not os.path.exists(old)


def test_prune_respects_max_entries(transcriber, tmp_path):
    audios = [os.path.join(str(tmp_path), f"audio_{i}.mp3") for i in range(5)]
    for p in audios:
        open(p, "w").close()
    paths = []
    for i, audio in enumerate(audios):
        paths.append(_write_cache(transcriber, audio, age_seconds=i))

    result = transcriber.prune_cache(max_age_days=7, max_entries=3)
    assert result["remaining"] == 3
    assert result["removed"] == 2
