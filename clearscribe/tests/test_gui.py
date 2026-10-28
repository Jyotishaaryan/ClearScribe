"""GUI construction and validation tests (offscreen Qt, no display needed)."""

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt6.QtWidgets import QApplication

from clearscribe.gui import MainWindow

_APP = QApplication.instance() or QApplication([])
_WINDOWS = []


def make_window():
    w = MainWindow()
    _WINDOWS.append(w)  # keep the C++ widget alive for the test session
    return w


def test_window_identity_and_defaults():
    w = make_window()
    assert w.windowTitle() == "ClearScribe Batch"
    assert w.selected_formats() == ("txt", "srt", "vtt", "md")
    assert w.model_combo.currentText() == "tiny"
    from PyQt6.QtWidgets import QLabel
    texts = [l.text() for l in w.findChildren(QLabel)]
    assert any("Chidi Williams" in t and "Jyotish Aaryan" in t for t in texts)


def test_validation_blocks_empty_and_missing_folder():
    w = make_window()
    w.start_batch()
    assert "Choose a real folder first." in w.log.toPlainText()
    assert w.worker is None
    w.folder_edit.setText("/definitely/not/a/real/folder")
    w.start_batch()
    assert w.worker is None
