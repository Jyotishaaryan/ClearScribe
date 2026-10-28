# ClearScribe: how the code works

A reading guide for presenting and defending this project. Fork of Buzz
by Chidi Williams (MIT). The ClearScribe additions are the parts you own
and should be ready to explain line by line.

## The big picture

Buzz is a desktop transcription app: a Qt6 GUI queues files, a transcriber
backend (OpenAI Whisper, whisper.cpp, faster-whisper, Hugging Face
transformers, or the OpenAI API) turns audio into timestamped segments,
and writers export TXT/SRT/VTT. ClearScribe keeps that app and adds a
headless batch pipeline on top of the same faster-whisper engine.

## The ClearScribe additions (clearscribe/)

### batch.py - the pipeline

Flow per run:

1. `find_media_files` walks the input folder for known audio/video
   extensions (mirrored from upstream so the tool never imports Qt).
2. `decode_audio` shells out to ffmpeg and reads raw 16 kHz mono float32
   PCM into a NumPy array. Design decision: faster-whisper accepts a NumPy
   array, and decoding through ffmpeg directly avoids PyAV, whose Python
   API changed between releases and broke version-pinned installs. ffmpeg
   is already a Buzz requirement, so this adds no new dependency.
3. `transcribe_file` runs faster-whisper on the array and normalizes
   segments to plain dicts `{start, end, text}`.
4. `write_outputs` emits TXT/SRT/VTT/Markdown per file.
5. `summarize` + `render_summary_md` produce `summary.json` and
   `SUMMARY.md` with per-file durations, word counts and wall time.

### srt_export.py - standalone writers

Upstream writers are entangled with the Qt stack. These pure-Python
renderers produce identical formats with zero GUI imports, which is why
the batch tool installs in seconds instead of gigabytes. SRT uses
`HH:MM:SS,mmm`, VTT uses `HH:MM:SS.mmm` with a `WEBVTT` header.

### gui.py - the Batch window

A small QMainWindow over the pipeline: folder picker, model combo,
language field, format checkboxes, a progress bar and a read-only log.
The transcription runs in a QThread (`BatchWorker`) so the window stays
responsive; progress lines travel back over Qt signals. The credit line
in the footer keeps the Buzz attribution visible in the UI itself.

### Error handling

Every file is transcribed inside a try/except in `run_batch`: a corrupt
or unsupported file is recorded under `errors` with a clean message
(ffmpeg decode failures are rewritten as "unsupported or corrupt media")
and the batch continues. The summary lists failures under a **Failed**
line, and the CLI exits non-zero only when nothing succeeded.

### markdown_export.py - the new format

A Markdown document with a metadata header (source, model, language,
date) and one bold `[HH:MM:SS]` timestamp per segment. Blank segments are
skipped. Designed for dropping lecture transcripts into a notes vault.

## Testing

Three files, ten tests: `test_clearscribe.py` covers timestamp formatting,
blank-segment skipping, SRT/VTT rendering, word counts, file discovery
and summary aggregation; `test_batch_hardening.py` drives `run_batch`
with a fake model over real ffmpeg decoding to cover corrupt media,
mixed folders, output overwrites, paths with spaces and exact export
regression; `test_gui.py` constructs the window offscreen and checks its
identity, defaults and folder validation. None of them downloads a model.
The end-to-end check was a real run through the window: two audio files
(FLAC and MP3 of the same 11-second JFK clip) transcribed correctly, and
a corrupt MP3 cleanly reported as failed without stopping the batch.

## Talking points for interviews

- Why fork instead of build from scratch: standing on a maintained,
  MIT-licensed codebase and owning a well-scoped addition is normal
  industry practice; the license and credit stay intact.
- The engineering decisions that are yours: ffmpeg-based decoding for
  dependency stability, Qt-free writers for a headless tool, the summary
  report, the Markdown format, and the test suite.
- Tradeoffs you can discuss: tiny vs larger models (speed vs accuracy),
  int8 CPU inference vs GPU, batch wall-clock scaling.

## Natural next features

- Speaker labels (upstream already ships diarization backends)
- A `--watch` mode that transcribes new files as they appear
- Parallel transcription across CPU cores
