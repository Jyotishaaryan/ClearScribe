"""Tests for the ClearScribe additions (no model download required)."""

import datetime
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from clearscribe.markdown_export import format_timestamp, render_markdown
from clearscribe.srt_export import render_srt, render_txt, render_vtt
from clearscribe.batch import find_media_files, summarize, word_count, render_summary_md

SEGMENTS = [
    {"start": 0.0, "end": 2.5, "text": " Hello there. "},
    {"start": 2.5, "end": 65.0, "text": " This is a test of the batch pipeline. "},
    {"start": 65.0, "end": 66.0, "text": "   "},
]


def test_format_timestamp():
    assert format_timestamp(0) == "00:00:00"
    assert format_timestamp(65) == "00:01:05"
    assert format_timestamp(3725) == "01:02:05"
    assert format_timestamp(-3) == "00:00:00"


def test_render_markdown_skips_blank_segments_and_stamps():
    md = render_markdown(
        SEGMENTS,
        title="lecture-01",
        source_file="lecture-01.mp3",
        model="faster-whisper/tiny",
        language="en",
        created=datetime.datetime(2026, 10, 28, 17, 30),
    )
    assert md.startswith("# Transcript: lecture-01")
    assert "**[00:00:00]** Hello there." in md
    assert "**[00:00:02]** This is a test of the batch pipeline." in md
    assert md.count("**[") == 2  # blank segment skipped
    assert "- Created: 2026-10-28 17:30" in md


def test_srt_and_vtt():
    srt = render_srt(SEGMENTS)
    assert "1\n00:00:00,000 --> 00:00:02,500\nHello there." in srt
    assert "00:01:06,000" not in srt  # blank segment skipped
    vtt = render_vtt(SEGMENTS)
    assert vtt.startswith("WEBVTT")
    assert "00:00:02.500 --> 00:01:05.000" in vtt
    assert render_txt(SEGMENTS).splitlines()[0] == "Hello there."


def test_word_count_and_summary(tmp_path):
    assert word_count(SEGMENTS) == 2 + 8
    (tmp_path / "a.mp3").write_bytes(b"x")
    (tmp_path / "b.pdf").write_bytes(b"x")
    (tmp_path / "sub").mkdir()
    (tmp_path / "sub" / "c.flac").write_bytes(b"x")
    found = [p.name for p in find_media_files(tmp_path)]
    assert found == ["a.mp3", "c.flac"]
    results = [
        {"file": "a.mp3", "duration_s": 10.0, "words": 9, "outputs": ["a.txt"]},
        {"file": "c.flac", "duration_s": 5.5, "words": 3, "outputs": ["c.txt"]},
    ]
    s = summarize(results, started_at=__import__("time").time() - 2)
    assert s["files_processed"] == 2
    assert s["total_words"] == 12
    assert s["total_audio_seconds"] == 15.5
    md = render_summary_md(s, "faster-whisper/tiny")
    assert "| a.mp3 | 10.0 | 9 | a.txt |" in md
