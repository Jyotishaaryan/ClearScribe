# ClearScribe setup guide

Tested 28 Oct 2026 on Linux (Ubuntu) with Python 3.13 and ffmpeg.

## What you need

- Python 3.13 (the upstream Buzz codebase pins `>=3.13,<3.14`)
- ffmpeg (`sudo apt install ffmpeg` on Ubuntu; `brew install ffmpeg` on macOS)
- About 1 GB free disk for the tiny Whisper model; more for larger models
- No GPU required. The tiny model runs on a normal CPU.

## Fast path: the ClearScribe batch pipeline only

This is the new feature built for this fork. It needs only a few packages:

```bash
cd clearscribe
python3.13 -m venv .venv
source .venv/bin/activate
pip install faster-whisper soundfile pytest PyQt6
python -m clearscribe.batch /path/to/lectures --model tiny --language en
```

Outputs land in `<folder>/clearscribe-out/`: one `.txt`, `.srt`, `.vtt` and
`.md` per input file, plus `SUMMARY.md` and `summary.json`.

Model sizes: `tiny` (fastest, rough), `base`, `small`, `medium`,
`large-v3` (best, needs several GB RAM). Start with `tiny` to check the
pipeline, then rerun with `small` or `medium` for real notes.

Run the tests:

```bash
pip install PyQt6   # only needed for tests/test_gui.py
python -m pytest tests/test_clearscribe.py tests/test_batch_hardening.py tests/test_gui.py --noconftest -q
```

(`--noconftest` skips the upstream test setup, which needs the full app
dependencies.)

## The ClearScribe Batch window

```bash
pip install PyQt6
python -m clearscribe.gui
```

Pick a folder, choose the model and formats, and press "Transcribe folder".
Progress and the summary appear in the window; outputs land in the folder's
`clearscribe-out` subfolder. On a headless Linux server you can run it with
`QT_QPA_PLATFORM=offscreen` for scripted checks; on a laptop it opens as a
normal window.

## Full desktop app

The upstream Buzz GUI carries heavy dependencies (PyQt6, PyTorch,
transformers, NVIDIA libraries for diarization). Install it as upstream
documents:

```bash
pip install -e .
python -m buzz
```

Expect the install to download several GB. The GUI is optional for the
ClearScribe additions; the batch pipeline above works without it.
