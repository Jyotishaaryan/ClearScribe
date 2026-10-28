"""Hardening tests: errors, mixed input, overwrites, paths, export regression."""

import json
import subprocess
import sys
import time
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from clearscribe.batch import (
    find_media_files,
    render_summary_md,
    run_batch,
    summarize,
)

FORMATS = ("txt", "srt", "vtt", "md")


class FakeModel:
    """Stands in for faster-whisper so no model download is needed."""

    def transcribe(self, audio, language=None):
        assert hasattr(audio, "__len__") and len(audio) > 0
        segments = [
            SimpleNamespace(start=0.0, end=1.5, text=" First words."),
            SimpleNamespace(start=1.5, end=3.0, text=" Second words."),
        ]
        info = SimpleNamespace(duration=3.0, language=language or "en")
        return iter(segments), info


def make_wav(path: Path, seconds=1):
    subprocess.run(
        ["ffmpeg", "-y", "-f", "lavfi", "-i", f"sine=frequency=440:duration={seconds}",
         str(path)],
        capture_output=True, check=True,
    )


def test_mixed_folder_invalid_media_recorded_not_fatal(tmp_path):
    make_wav(tmp_path / "good.wav")
    (tmp_path / "broken.mp3").write_bytes(b"this is not really audio data")
    (tmp_path / "notes.pdf").write_bytes(b"ignored")
    files = find_media_files(tmp_path)
    assert [p.name for p in files] == ["broken.mp3", "good.wav"]
    out = tmp_path / "out"
    out.mkdir()
    results, errors = run_batch(files, out, FORMATS, FakeModel(), "fake/tiny", progress=lambda m: None)
    assert [r["file"] for r in results] == ["good.wav"]
    assert len(errors) == 1 and errors[0]["file"] == "broken.mp3"
    summary = summarize(results, time.time() - 1)
    md = render_summary_md(summary, "fake/tiny", errors)
    assert "**Failed:** `broken.mp3`" in md
    # valid file still produced every format
    for ext in FORMATS:
        assert (out / f"good.{ext}").exists()


def test_output_overwrite_is_clean(tmp_path):
    make_wav(tmp_path / "clip.wav")
    out = tmp_path / "out"
    out.mkdir()
    files = find_media_files(tmp_path)
    for _ in range(2):
        results, errors = run_batch(files, out, FORMATS, FakeModel(), "fake/tiny", progress=lambda m: None)
        assert not errors
    txt = (out / "clip.txt").read_text()
    assert txt == "First words.\nSecond words.\n"


def test_paths_with_spaces_and_unicode(tmp_path):
    sub = tmp_path / "my lectures"
    sub.mkdir()
    make_wav(sub / "week 1 (intro).wav")
    out = tmp_path / "out put"
    out.mkdir()
    results, errors = run_batch(find_media_files(sub), out, FORMATS, FakeModel(), "fake/tiny", progress=lambda m: None)
    assert not errors and results[0]["file"] == "week 1 (intro).wav"
    assert (out / "week 1 (intro).md").exists()


def test_export_regression_exact(tmp_path):
    make_wav(tmp_path / "clip.wav")
    out = tmp_path / "out"
    out.mkdir()
    run_batch(find_media_files(tmp_path), out, FORMATS, FakeModel(), "fake/tiny", progress=lambda m: None)
    assert (out / "clip.srt").read_text() == (
        "1\n00:00:00,000 --> 00:00:01,500\nFirst words.\n\n"
        "2\n00:00:01,500 --> 00:00:03,000\nSecond words.\n"
    )
    assert (out / "clip.vtt").read_text() == (
        "WEBVTT\n\n00:00:00.000 --> 00:00:01.500\nFirst words.\n\n"
        "00:00:01.500 --> 00:00:03.000\nSecond words.\n"
    )
    md = (out / "clip.md").read_text()
    assert "**[00:00:00]** First words." in md
    assert "**[00:00:01]** Second words." in md
    assert "- Model: fake/tiny" in md
