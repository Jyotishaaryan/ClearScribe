"""ClearScribe Batch window.

A small, plain desktop window that drives the ClearScribe batch
pipeline: pick a folder of recordings, choose a model and formats,
run, and watch progress. Deliberately understated native Qt - no
chatbot panels, no gradients.

Written for ClearScribe by Jyotish Aaryan; project is a fork of Buzz
by Chidi Williams (MIT License).

Run with:  python -m clearscribe.gui
"""

from __future__ import annotations

import sys
import traceback
from pathlib import Path

from PyQt6.QtCore import QThread, pyqtSignal
from PyQt6.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QPlainTextEdit,
    QProgressBar,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from .batch import DEFAULT_FORMATS, find_media_files, render_summary_md, run_batch, summarize
import time

MODEL_SIZES = ("tiny", "base", "small", "medium", "large-v3")


class BatchWorker(QThread):
    progressed = pyqtSignal(str)
    finished_ok = pyqtSignal(str)
    failed = pyqtSignal(str)

    def __init__(self, files, out_dir, formats, model_size, language, parent=None):
        super().__init__(parent)
        self.files = files
        self.out_dir = out_dir
        self.formats = formats
        self.model_size = model_size
        self.language = language or None

    def run(self):
        try:
            from faster_whisper import WhisperModel

            model_name = f"faster-whisper/{self.model_size}"
            model = WhisperModel(self.model_size, device="cpu", compute_type="int8")
            started = time.time()
            results, errors = run_batch(
                self.files, self.out_dir, self.formats, model, model_name,
                language=self.language, progress=self.progressed.emit,
            )
            summary = summarize(results, started)
            summary["errors"] = errors
            import json

            (self.out_dir / "summary.json").write_text(
                json.dumps(summary, indent=2), encoding="utf-8")
            (self.out_dir / "SUMMARY.md").write_text(
                render_summary_md(summary, model_name, errors), encoding="utf-8")
            self.finished_ok.emit(render_summary_md(summary, model_name, errors))
        except Exception:
            self.failed.emit(traceback.format_exc())


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("ClearScribe Batch")
        self.setMinimumWidth(560)
        self.worker = None

        root = QWidget()
        layout = QVBoxLayout(root)

        form = QFormLayout()
        folder_row = QHBoxLayout()
        self.folder_edit = QLineEdit()
        self.folder_edit.setPlaceholderText("Folder with audio or video files")
        browse = QPushButton("Browse...")
        browse.clicked.connect(self.pick_folder)
        folder_row.addWidget(self.folder_edit, 1)
        folder_row.addWidget(browse)
        form.addRow("Folder", folder_row)

        options_row = QHBoxLayout()
        self.model_combo = QComboBox()
        self.model_combo.addItems(MODEL_SIZES)
        self.language_edit = QLineEdit("en")
        self.language_edit.setMaximumWidth(70)
        options_row.addWidget(QLabel("Model"))
        options_row.addWidget(self.model_combo)
        options_row.addWidget(QLabel("Language"))
        options_row.addWidget(self.language_edit)
        options_row.addStretch(1)
        form.addRow(options_row)

        formats_row = QHBoxLayout()
        self.format_checks = {}
        for fmt in DEFAULT_FORMATS:
            cb = QCheckBox(fmt.upper() if fmt != "md" else "Markdown")
            cb.setChecked(True)
            self.format_checks[fmt] = cb
            formats_row.addWidget(cb)
        formats_row.addStretch(1)
        form.addRow("Formats", formats_row)
        layout.addLayout(form)

        self.run_button = QPushButton("Transcribe folder")
        self.run_button.clicked.connect(self.start_batch)
        layout.addWidget(self.run_button)

        self.progress = QProgressBar()
        self.progress.setRange(0, 100)
        self.progress.setValue(0)
        layout.addWidget(self.progress)

        self.log = QPlainTextEdit()
        self.log.setReadOnly(True)
        layout.addWidget(self.log, 1)

        credit = QLabel(
            "Based on Buzz by Chidi Williams (MIT License). "
            "ClearScribe additions by Jyotish Aaryan."
        )
        credit.setStyleSheet("color: #666;")
        layout.addWidget(credit)

        self.setCentralWidget(root)

    def pick_folder(self):
        chosen = QFileDialog.getExistingDirectory(self, "Choose folder")
        if chosen:
            self.folder_edit.setText(chosen)

    def selected_formats(self):
        return tuple(f for f, cb in self.format_checks.items() if cb.isChecked())

    def start_batch(self):
        text = self.folder_edit.text().strip()
        if not text:
            self.log.appendPlainText("Choose a real folder first.")
            return
        folder = Path(text)
        if not folder.is_dir():
            self.log.appendPlainText("Choose a real folder first.")
            return
        files = find_media_files(folder)
        if not files:
            self.log.appendPlainText("No audio or video files found in that folder.")
            return
        formats = self.selected_formats()
        if not formats:
            self.log.appendPlainText("Pick at least one output format.")
            return
        out_dir = folder / "clearscribe-out"
        out_dir.mkdir(parents=True, exist_ok=True)
        self.run_button.setEnabled(False)
        self.progress.setRange(0, len(files))
        self.progress.setValue(0)
        self.log.appendPlainText(
            f"Starting: {len(files)} file(s), model {self.model_combo.currentText()}")
        self._seen = 0
        self.worker = BatchWorker(
            files, out_dir, formats,
            self.model_combo.currentText(), self.language_edit.text().strip(),
        )
        self.worker.progressed.connect(self.on_progress)
        self.worker.finished_ok.connect(self.on_finished)
        self.worker.failed.connect(self.on_failed)
        self.worker.start()

    def on_progress(self, line: str):
        self.log.appendPlainText(line)
        if line.startswith("[") and "done" not in line and "FAILED" not in line:
            pass
        if "done:" in line or "FAILED" in line:
            self._seen += 1
            self.progress.setValue(self._seen)

    def on_finished(self, summary_md: str):
        self.log.appendPlainText("")
        self.log.appendPlainText(summary_md)
        self.log.appendPlainText("Outputs are in the clearscribe-out folder.")
        self.run_button.setEnabled(True)

    def on_failed(self, tb: str):
        self.log.appendPlainText("Run failed:\n" + tb)
        self.run_button.setEnabled(True)


def main():
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
