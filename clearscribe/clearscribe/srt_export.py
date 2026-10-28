"""Plain-Python SRT/VTT/TXT writers for the ClearScribe batch pipeline.

The upstream Buzz writers live inside the Qt application stack; these
standalone writers keep the batch tool free of GUI dependencies.

Written for ClearScribe by Jyotish Aaryan; project is a fork of Buzz
by Chidi Williams (MIT License).
"""

from __future__ import annotations


def _srt_time(seconds: float) -> str:
    if seconds < 0:
        seconds = 0
    ms = int(round(seconds * 1000))
    hours, rem = divmod(ms, 3600_000)
    minutes, rem = divmod(rem, 60_000)
    secs, millis = divmod(rem, 1000)
    return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"


def _vtt_time(seconds: float) -> str:
    return _srt_time(seconds).replace(",", ".")


def render_txt(segments) -> str:
    return "".join(seg["text"].strip() + "\n" for seg in segments if seg["text"].strip())


def render_srt(segments) -> str:
    blocks = []
    index = 1
    for seg in segments:
        text = seg["text"].strip()
        if not text:
            continue
        blocks.append(
            f"{index}\n{_srt_time(seg['start'])} --> {_srt_time(seg['end'])}\n{text}\n"
        )
        index += 1
    return "\n".join(blocks)


def render_vtt(segments) -> str:
    body = []
    for seg in segments:
        text = seg["text"].strip()
        if not text:
            continue
        body.append(f"{_vtt_time(seg['start'])} --> {_vtt_time(seg['end'])}\n{text}\n")
    return "WEBVTT\n\n" + "\n".join(body)
