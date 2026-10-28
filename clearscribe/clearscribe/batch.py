"""ClearScribe batch transcription pipeline.

Transcribes every audio/video file in a folder in one run and writes a
summary report alongside the transcripts. Designed for students dumping
a folder of lecture recordings and getting notes back.

Written for ClearScribe by Jyotish Aaryan; project is a fork of Buzz
by Chidi Williams (MIT License). Uses faster-whisper, one of the same
local Whisper engines Buzz offers.

Usage:
    python -m clearscribe.batch INPUT_DIR [--output DIR] [--model tiny]
        [--language en] [--formats txt,srt,vtt,md]
"""

from __future__ import annotations

import argparse
import datetime
import json
import sys
import time
from pathlib import Path

from .markdown_export import write_markdown
from .srt_export import render_srt, render_txt, render_vtt

# Mirrors the extension sets in buzz/transcriber/transcriber.py so the
# batch tool stays free of the Qt stack.
AUDIO_EXTENSIONS = (".mp3", ".wav", ".m4a", ".m4b", ".aac", ".ogg", ".opus", ".flac")
VIDEO_EXTENSIONS = (".mp4", ".m4v", ".webm", ".ogm", ".mov", ".mkv", ".avi", ".wmv")
SUPPORTED_EXTENSIONS = AUDIO_EXTENSIONS + VIDEO_EXTENSIONS

DEFAULT_FORMATS = ("txt", "srt", "vtt", "md")


def find_media_files(input_dir: Path):
    return sorted(
        p for p in input_dir.rglob("*")
        if p.is_file() and p.suffix.lower() in SUPPORTED_EXTENSIONS
    )


def word_count(segments) -> int:
    return sum(len(seg["text"].split()) for seg in segments)


def decode_audio(path: Path):
    """Decode any audio/video file to 16 kHz mono float32 via ffmpeg.

    faster-whisper accepts a NumPy array, which keeps this pipeline
    independent of the PyAV version (its API changes between releases).
    """
    import subprocess

    import numpy as np

    cmd = [
        "ffmpeg", "-nostdin", "-i", str(path),
        "-f", "f32le", "-acodec", "pcm_f32le",
        "-ac", "1", "-ar", "16000", "-",
    ]
    try:
        proc = subprocess.run(cmd, capture_output=True, check=True)
    except subprocess.CalledProcessError as exc:
        raise RuntimeError(
            f"ffmpeg could not decode {path.name} (unsupported or corrupt media)"
        ) from exc
    return np.frombuffer(proc.stdout, dtype=np.float32)


def transcribe_file(model, path: Path, language: str | None):
    audio = decode_audio(path)
    raw_segments, info = model.transcribe(audio, language=language)
    segments = [
        {"start": s.start, "end": s.end, "text": s.text} for s in raw_segments
    ]
    return segments, info


def write_outputs(segments, info, out_base: Path, formats, model_name: str, source: Path):
    written = []
    if "txt" in formats:
        p = out_base.with_suffix(".txt")
        p.write_text(render_txt(segments), encoding="utf-8")
        written.append(p)
    if "srt" in formats:
        p = out_base.with_suffix(".srt")
        p.write_text(render_srt(segments), encoding="utf-8")
        written.append(p)
    if "vtt" in formats:
        p = out_base.with_suffix(".vtt")
        p.write_text(render_vtt(segments), encoding="utf-8")
        written.append(p)
    if "md" in formats:
        p = out_base.with_suffix(".md")
        write_markdown(
            segments,
            p,
            title=source.stem,
            source_file=source.name,
            model=model_name,
            language=getattr(info, "language", "auto"),
        )
        written.append(p)
    return written


def summarize(results, started_at: float):
    total_words = sum(r["words"] for r in results)
    total_audio = sum(r["duration_s"] for r in results)
    return {
        "files_processed": len(results),
        "total_words": total_words,
        "total_audio_seconds": round(total_audio, 1),
        "wall_time_seconds": round(time.time() - started_at, 1),
        "files": results,
    }


def render_summary_md(summary, model_name: str, errors=None) -> str:
    lines = [
        "# ClearScribe batch summary",
        "",
        f"- Model: {model_name}",
        f"- Files processed: {summary['files_processed']}",
        f"- Total audio: {summary['total_audio_seconds']}s",
        f"- Total words: {summary['total_words']}",
        f"- Wall time: {summary['wall_time_seconds']}s",
        "",
        "| File | Audio (s) | Words | Outputs |",
        "| --- | --- | --- | --- |",
    ]
    for r in summary["files"]:
        outs = ", ".join(r["outputs"])
        lines.append(f"| {r['file']} | {r['duration_s']} | {r['words']} | {outs} |")
    for e in (errors or []):
        lines.append("")
        lines.append(f"**Failed:** `{e['file']}` - {e['error']}")
    return "\n".join(lines) + "\n"


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(prog="clearscribe-batch", description=__doc__)
    parser.add_argument("input_dir", type=Path)
    parser.add_argument("--output", type=Path, default=None)
    parser.add_argument("--model", default="tiny")
    parser.add_argument("--language", default=None)
    parser.add_argument("--formats", default=",".join(DEFAULT_FORMATS))
    args = parser.parse_args(argv)

    if not args.input_dir.is_dir():
        print(f"Error: {args.input_dir} is not a directory", file=sys.stderr)
        return 1

    files = find_media_files(args.input_dir)
    if not files:
        print(f"No audio or video files found under {args.input_dir}", file=sys.stderr)
        return 1

    out_dir = args.output or (args.input_dir / "clearscribe-out")
    out_dir.mkdir(parents=True, exist_ok=True)
    formats = tuple(f.strip() for f in args.formats.split(",") if f.strip())

    print(f"ClearScribe batch: {len(files)} file(s), model={args.model}, output={out_dir}")

    from faster_whisper import WhisperModel  # deferred: heavy import

    started = time.time()
    model = WhisperModel(args.model, device="cpu", compute_type="int8")
    model_name = f"faster-whisper/{args.model}"


    results, errors = run_batch(
        files, out_dir, formats, model, model_name, language=args.language
    )

    summary = summarize(results, started)
    summary["errors"] = errors
    (out_dir / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    (out_dir / "SUMMARY.md").write_text(
        render_summary_md(summary, model_name, errors), encoding="utf-8")
    print(render_summary_md(summary, model_name, errors))
    print(f"Summary written to {out_dir / 'SUMMARY.md'}")
    if not results and errors:
        return 1
    return 0


def run_batch(files, out_dir, formats, model, model_name, language=None, progress=print):
    """Transcribe every file, capturing per-file errors instead of stopping."""
    results = []
    errors = []
    for i, path in enumerate(files, start=1):
        progress(f"[{i}/{len(files)}] {path.name} ...")
        try:
            segments, info = transcribe_file(model, path, language)
            out_base = out_dir / path.stem
            written = write_outputs(segments, info, out_base, formats, model_name, path)
        except Exception as exc:  # corrupt media, ffmpeg failure, decode issues
            errors.append({"file": path.name, "error": str(exc)[:200]})
            progress(f"    FAILED: {exc}")
            continue
        duration = getattr(info, "duration", 0.0)
        results.append({
            "file": path.name,
            "duration_s": round(duration, 1),
            "words": word_count(segments),
            "outputs": [p.name for p in written],
        })
        progress(f"    done: {len(segments)} segments, {results[-1]['words']} words")
    return results, errors


if __name__ == "__main__":
    raise SystemExit(main())
