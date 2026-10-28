# ClearScribe

ClearScribe turns a folder of audio or video recordings into text transcripts,
subtitles and timestamped Markdown files. Use the desktop window for a guided
batch run, or the command line to choose an output folder.

## Features

- Find supported recordings in a folder and its subfolders.
- Transcribe with faster-whisper on the CPU using int8 computation.
- Choose a model: `tiny`, `base`, `small`, `medium` or `large-v3`.
- Set a language code, or leave it blank in the window for automatic detection.
- Export TXT, SRT, VTT and Markdown, together or separately.
- View per-file progress in the desktop window.
- Record per-file failures and continue with the remaining recordings.
- Write `SUMMARY.md` and `summary.json` with successful files, durations,
  word counts, output names and errors.

The Markdown export is a timestamped transcript, not an AI-generated summary of
what was said. The batch summary reports processing results, not lecture notes.

## Requirements

- Python 3.13 for the supplied project.
- ffmpeg installed and available on your system PATH.
- Python packages: `faster-whisper`, `numpy` and `PyQt6` for the desktop window.
- Space for model files and generated transcripts. Larger models need more
  memory and take longer on a CPU. Start with `tiny` to check your setup.

The first use of a model may need an internet connection to download it. The
ClearScribe batch code runs transcription locally; it does not contain a
cloud transcription upload step. A GPU is not required by this pipeline.

## Setup

Extract `clearscribe-source.zip`, open a terminal, and change into the project
folder containing this file and the `clearscribe/` Python package.

### Linux or macOS

```bash
python3.13 -m venv .venv
source .venv/bin/activate
python -m pip install faster-whisper numpy PyQt6
```

Install ffmpeg separately if needed: `sudo apt install ffmpeg` on Ubuntu, or
`brew install ffmpeg` on macOS when Homebrew is installed.

### Windows PowerShell

```powershell
py -3.13 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install faster-whisper numpy PyQt6
```

Install ffmpeg separately and add its executable folder to PATH. If activation
is restricted, use `.\.venv\Scripts\python.exe` instead of `python` in the
remaining commands; activation is not required when using that full path.

Check that ffmpeg is reachable:

```bash
ffmpeg -version
```

These commands install the packages needed for the ClearScribe batch window,
not every dependency listed in the full project's `pyproject.toml`.

## Desktop window

From the project folder, with the environment active:

```bash
python -m clearscribe.gui
```

1. Click **Browse...** and choose a folder of recordings.
2. Choose a model. The default is `tiny`.
3. Set the language, for example `en` for English. The window starts with `en`;
   clear the field to request automatic language detection.
4. Select at least one output format.
5. Click **Transcribe folder**.
6. Review the progress log and summary, including any failed files.

Outputs are saved in a `clearscribe-out` subfolder inside the selected folder.
The window runs transcription on a worker thread so the interface can remain
responsive. There is no pause or cancel control in this version.

## Command line

Transcribe a folder with all four output formats:

```bash
python -m clearscribe.batch "demo-input" --model tiny --language en
```

Choose an input folder, a separate output folder and selected formats:

```bash
python -m clearscribe.batch "recordings" --output "transcripts" --model small --language en --formats txt,md
```

Omit `--language` for automatic detection. Omit `--output` to save results in
`<input-folder>/clearscribe-out`. Valid format names are `txt,srt,vtt,md`.
Use `python -m clearscribe.batch --help` to see the available arguments.

## Output files

For an input named `lecture-01.mp3`, the default exports are:

```text
clearscribe-out/
  lecture-01.txt
  lecture-01.srt
  lecture-01.vtt
  lecture-01.md
  SUMMARY.md
  summary.json
```

- **TXT:** plain transcript text.
- **SRT / VTT:** timed subtitle segments.
- **Markdown:** source, model, language and creation metadata, followed by
  timestamped transcript segments.
- **Summary files:** batch totals, successful outputs and per-file errors.

## Supported input extensions

Audio: `.mp3`, `.wav`, `.m4a`, `.m4b`, `.aac`, `.ogg`, `.opus`, `.flac`.

Video: `.mp4`, `.m4v`, `.webm`, `.ogm`, `.mov`, `.mkv`, `.avi`, `.wmv`.

An extension being listed does not guarantee that every file will decode.
ffmpeg must be able to read its actual media content and codec.

## Important limits

- Review transcripts before using them. Noise, accents, mixed languages and
  technical vocabulary can affect accuracy.
- Outputs go into one folder, even when recordings come from subfolders.
  Use unique, simple input names such as `lecture-01.mp3`. Avoid repeated names
  and extra dots before the final extension: output naming can cause collisions.
- Existing files with the same output name are overwritten without a prompt.
  Back up results or choose a new output folder before rerunning.
- A batch can finish with some files failed. Check the summary, not only the
  process exit status. The CLI returns a failure status when all files fail,
  but a mixed-success run can return success.
- This version focuses on recorded-file batch transcription. The ClearScribe
  window does not provide live microphone recording, speaker labels,
  transcript editing or automatic content summarization.

## Checks and test status

The delivered version was previously checked with a short English recording
in MP3 and FLAC form, plus corrupt-file cases. Ten focused tests were reported
passing for exports, batch handling and window validation. This is not an
accuracy benchmark or a claim that every listed media type has been tested.

The window was tested using offscreen rendering on Linux. Your laptop setup
and normal on-screen behavior still need to be checked. Windows and macOS
setup commands above have not been validated on your device.

To rerun the focused tests, with ffmpeg available:

```bash
python -m pip install pytest
python -m pytest tests/test_clearscribe.py tests/test_batch_hardening.py tests/test_gui.py --noconftest -q
```

These tests include a fake transcription model for batch checks; they do not
measure real-model transcription accuracy.

## Troubleshooting

- **No module named clearscribe:** run from the extracted project folder,
  not from inside its inner `clearscribe/` package directory.
- **ffmpeg not found:** install ffmpeg, check PATH and reopen the terminal.
- **A file fails to decode:** try playing it, check that it is not corrupt,
  and review the error in the summary. Other files can still be processed.
- **The window will not open:** confirm `PyQt6` is installed in the same
  environment and that your operating system has the required Qt display
  libraries. Headless servers need a display or an offscreen test setup.
- **The model is slow or runs out of memory:** try `tiny` and a short clip
  before increasing model size or processing a long folder.
