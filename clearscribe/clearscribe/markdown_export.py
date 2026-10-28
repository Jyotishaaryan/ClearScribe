"""Markdown transcript export for ClearScribe.

Buzz upstream exports TXT, SRT and VTT. This module adds a Markdown
export with a metadata header and timestamped paragraphs, useful for
lecture notes and Obsidian-style vaults.

Written for ClearScribe by Jyotish Aaryan; project is a fork of Buzz
by Chidi Williams (MIT License).
"""

from __future__ import annotations

import datetime


def format_timestamp(seconds: float) -> str:
    """Render seconds as [HH:MM:SS]."""
    if seconds < 0:
        seconds = 0
    total = int(seconds)
    hours, rem = divmod(total, 3600)
    minutes, secs = divmod(rem, 60)
    return f"{hours:02d}:{minutes:02d}:{secs:02d}"


def render_markdown(
    segments,
    *,
    title: str,
    source_file: str,
    model: str,
    language: str,
    created: datetime.datetime | None = None,
) -> str:
    """Render timestamped transcript segments as a Markdown document."""
    created = created or datetime.datetime.now()
    lines = [
        f"# Transcript: {title}",
        "",
        f"- Source: `{source_file}`",
        f"- Model: {model}",
        f"- Language: {language}",
        f"- Created: {created.strftime('%Y-%m-%d %H:%M')}",
        "",
        "---",
        "",
    ]
    for seg in segments:
        start = format_timestamp(seg["start"])
        text = seg["text"].strip()
        if text:
            lines.append(f"**[{start}]** {text}")
            lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def write_markdown(segments, path, **metadata) -> None:
    with open(path, "w", encoding="utf-8") as f:
        f.write(render_markdown(segments, **metadata))
