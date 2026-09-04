from __future__ import annotations

import io
import os
import sys
import time
from pathlib import Path

from PIL import Image
from PySide6.QtCore import QRect, QSize, Qt, Signal
from PySide6.QtGui import QColor, QDragEnterEvent, QDropEvent, QIcon, QMouseEvent, QPixmap
from PySide6.QtWidgets import (
    QApplication,
    QColorDialog,
    QComboBox,
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QStatusBar,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from wallpane.compose import Assignment, FitMode, Monitor, compose, parse_fit_mode
from wallpane.hostcmd import log_apply
from wallpane.config import AppConfig, load_config, save_config
from wallpane.displays import DisplayError, list_monitors
from wallpane.i18n import t
from wallpane.wallpaper import WallpaperError, apply_composed_image, output_dir

IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".webp", ".bmp", ".tif", ".tiff"}
IMAGE_FILTER = "Images (*.png *.jpg *.jpeg *.webp *.bmp *.tif *.tiff);;All files (*)"
MINT_GREEN = "#6AA84F"
ICON_PNG = Path(__file__).resolve().parent / "resources" / "wallpane.png"


def hex_to_rgb(value: str) -> tuple[int, int, int]:
    text = value.strip().lstrip("#")
    if len(text) != 6:
        return (0, 0, 0)
    return int(text[0:2], 16), int(text[2:4], 16), int(text[4:6], 16)


def pil_to_pixmap(image: Image.Image) -> QPixmap:
    buf = io.BytesIO()
    image.save(buf, format="PNG")
    pixmap = QPixmap()
    pixmap.loadFromData(buf.getvalue())
    return pixmap


def paths_from_drop(event: QDropEvent) -> list[Path]:
    paths: list[Path] = []
    mime = event.mimeData()
    if mime is None:
        return paths
    for url in mime.urls():
        local = url.toLocalFile()
        if not local:
            continue
        path = Path(local)
        if path.suffix.lower() in IMAGE_EXTS and path.is_file():
            paths.append(path)
    return paths


class MonitorCard(QFrame):
    image_changed = Signal(str, object)
    mode_changed = Signal(str, object)
    request_apply_all = Signal(str)

    def __init__(self, monitor: Monitor, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.monitor = monitor
        self.assignment: Assignment | None = None
        self.setAcceptDrops(True)
        self.setObjectName("monitorCard")
        self.setFrameShape(QFrame.Shape.StyledPanel)
        self.setMinimumSize(220, 170)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(8)

        title = t("display_size", name=monitor.display_name, width=monitor.width, height=monitor.height)
        if monitor.primary:
            title = f"{title}  ·  {t('primary')}"
        self.title_label = QLabel(title)
        self.title_label.setObjectName("cardTitle")

        self.preview = QLabel(t("drop_hint"))
        self.preview.setObjectName("dropTarget")
        self.preview.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.preview.setWordWrap(True)
        self.preview.setMinimumHeight(90)
        self.preview.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.title_label.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        self.preview.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)

        self.mode = QComboBox()
        self.mode.addItem(t("mode_cover"), FitMode.COVER.value)
        self.mode.addItem(t("mode_contain"), FitMode.CONTAIN.value)
        self.mode.addItem(t("mode_stretch"), FitMode.STRETCH.value)
        self.mode.addItem(t("mode_center"), FitMode.CENTER.value)
        self.mode.currentIndexChanged.connect(self._on_mode_changed)

        buttons = QHBoxLayout()
        browse = QToolButton()
        browse.setText(t("browse"))
        browse.clicked.connect(self.choose_image)
        clear = QToolButton()
        clear.setText(t("clear"))
        clear.clicked.connect(self.clear_image)
        apply_all = QToolButton()
        apply_all.setText(t("same_all"))
        apply_all.clicked.connect(lambda: self.request_apply_all.emit(self.monitor.key))
        buttons.addWidget(browse)
        buttons.addWidget(clear)
        buttons.addStretch(1)
        buttons.addWidget(apply_all)

        layout.addWidget(self.title_label)
        layout.addWidget(self.preview, 1)
        layout.addWidget(self.mode)
        layout.addLayout(buttons)

    def current_mode(self) -> FitMode:
        try:
            return parse_fit_mode(self.mode.currentData() or FitMode.COVER.value)
        except ValueError:
            return FitMode.COVER

    def set_assignment(self, assignment: Assignment | None) -> None:
        self.assignment = assignment
        if assignment is None:
            self.preview.setPixmap(QPixmap())
            self.preview.setText(t("drop_hint"))
            self.setProperty("filled", False)
        else:
            self.preview.setText("")
            pixmap = QPixmap(str(assignment.path))
            if not pixmap.isNull():
                self.preview.setPixmap(
                    pixmap.scaled(
                        self.preview.size(),
                        Qt.AspectRatioMode.KeepAspectRatio,
                        Qt.TransformationMode.SmoothTransformation,
                    )
                )
            else:
                self.preview.setText(assignment.path.name)
            index = self.mode.findData(parse_fit_mode(assignment.mode).value)
            if index >= 0:
                self.mode.blockSignals(True)
                self.mode.setCurrentIndex(index)
                self.mode.blockSignals(False)
            self.setProperty("filled", True)
        self.style().unpolish(self)
        self.style().polish(self)

    def choose_image(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, t("browse"), str(Path.home()), IMAGE_FILTER)
        if path:
            self._assign_path(Path(path))

    def clear_image(self) -> None:
        self.set_assignment(None)
        self.image_changed.emit(self.monitor.key, None)

    def dragEnterEvent(self, event: QDragEnterEvent) -> None:
        if paths_from_drop(event):
            event.acceptProposedAction()
            self.setProperty("dropHover", True)
            self.style().polish(self)
        else:
            event.ignore()

    def dragLeaveEvent(self, event) -> None:  # type: ignore[no-untyped-def]
        self.setProperty("dropHover", False)
        self.style().polish(self)
        super().dragLeaveEvent(event)

    def dropEvent(self, event: QDropEvent) -> None:
        self.setProperty("dropHover", False)
        self.style().polish(self)
        paths = paths_from_drop(event)
        if not paths:
            event.ignore()
            return
        self._assign_path(paths[0])
        event.acceptProposedAction()

    def mousePressEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.MouseButton.LeftButton and self.assignment is None:
            self.choose_image()
        super().mousePressEvent(event)

    def resizeEvent(self, event) -> None:  # type: ignore[no-untyped-def]
        super().resizeEvent(event)
        if self.assignment is not None:
            self.set_assignment(self.assignment)

    def _assign_path(self, path: Path) -> None:
        assignment = Assignment(path=path, mode=self.current_mode())
        self.set_assignment(assignment)
        self.image_changed.emit(self.monitor.key, assignment)

    def _on_mode_changed(self) -> None:
        if self.assignment is not None:
            self.assignment.mode = self.current_mode()
        self.mode_changed.emit(self.monitor.key, self.current_mode())


class MonitorMap(QWidget):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.cards: dict[str, MonitorCard] = {}
        self._monitors: list[Monitor] = []
        self.setMinimumHeight(280)

    def set_monitors(self, monitors: list[Monitor]) -> None:
        for card in self.cards.values():
            card.setParent(None)
            card.deleteLater()
        self.cards.clear()
        self._monitors = list(monitors)
        for monitor in monitors:
            card = MonitorCard(monitor, self)
            self.cards[monitor.key] = card
            card.show()
        self._relayout()

    def resizeEvent(self, event) -> None:  # type: ignore[no-untyped-def]
        super().resizeEvent(event)
        self._relayout()

    def sizeHint(self) -> QSize:
        return QSize(880, 360)

    def _relayout(self) -> None:
        if not self._monitors:
            return
        min_x = min(m.x for m in self._monitors)
        min_y = min(m.y for m in self._monitors)
        span_w = max(m.x + m.width for m in self._monitors) - min_x
        span_h = max(m.y + m.height for m in self._monitors) - min_y
        pad = 12
        gap = 10
        avail_w = max(1, self.width() - pad * 2)
        avail_h = max(1, self.height() - pad * 2)
        scale = min(avail_w / span_w, avail_h / span_h)

        min_card_w, min_card_h = 220, 170
        for monitor in self._monitors:
            scale = max(scale, min_card_w / monitor.width, min_card_h / monitor.height)

        used_w = span_w * scale
        used_h = span_h * scale
        ox = pad + max(0, (avail_w - used_w) / 2)
        oy = pad + max(0, (avail_h - used_h) / 2)

        for monitor in self._monitors:
            card = self.cards[monitor.key]
            rect = QRect(
                int(ox + (monitor.x - min_x) * scale),
                int(oy + (monitor.y - min_y) * scale),
                max(min_card_w, int(monitor.width * scale) - gap),
                max(min_card_h, int(monitor.height * scale) - gap),
            )
            card.setGeometry(rect)


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle(t("window_title"))
        if ICON_PNG.is_file():
            self.setWindowIcon(QIcon(str(ICON_PNG)))
        self.resize(960, 620)
        self.assignments: dict[str, Assignment] = {}
        self.monitors: list[Monitor] = []
        self.config = load_config()
        self.fill_hex = self.config.fill or "#000000"

        root = QWidget()
        self.setCentralWidget(root)
        layout = QVBoxLayout(root)
        layout.setContentsMargins(16, 16, 16, 12)
        layout.setSpacing(12)

        toolbar = QHBoxLayout()
        self.apply_btn = QPushButton(t("apply"))
        self.apply_btn.setObjectName("applyButton")
        self.apply_btn.clicked.connect(self.apply_wallpaper)
        preview_btn = QPushButton(t("preview"))
        preview_btn.clicked.connect(self.show_preview)
        refresh_btn = QPushButton(t("refresh"))
        refresh_btn.clicked.connect(self.reload_monitors)

        self.color_btn = QPushButton(t("fill_color"))
        self.color_btn.clicked.connect(self.pick_fill_color)
        self._paint_color_button()

        toolbar.addWidget(self.apply_btn)
        toolbar.addWidget(preview_btn)
        toolbar.addWidget(refresh_btn)
        toolbar.addStretch(1)
        toolbar.addWidget(self.color_btn)

        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setFrameShape(QFrame.Shape.NoFrame)
        self.monitor_map = MonitorMap()
        self.scroll.setWidget(self.monitor_map)

        layout.addLayout(toolbar)
        layout.addWidget(self.scroll, 1)

        status = QStatusBar()
        self.setStatusBar(status)
        status.showMessage(t("status_ready"))

        self._preview_window: QMainWindow | None = None
        self.reload_monitors()

    def reload_monitors(self) -> None:
        previous = dict(self.assignments)
        try:
            self.monitors = list_monitors()
        except DisplayError as exc:
            self.monitors = []
            QMessageBox.warning(self, t("app_name"), f"{t('no_displays')}\n{exc}")
            return
        self.monitor_map.set_monitors(self.monitors)
        saved = self.config.assignments or {}
        self.assignments = {}
        for key, card in self.monitor_map.cards.items():
            card.image_changed.connect(self._on_image_changed)
            card.mode_changed.connect(self._on_mode_changed)
            card.request_apply_all.connect(self._apply_image_to_all)
            assignment = previous.get(key) or saved.get(key)
            if assignment is not None:
                card.set_assignment(assignment)
                self.assignments[key] = assignment
        self._relayout_map()

    def _relayout_map(self) -> None:
        if not self.monitors:
            return
        min_x = min(m.x for m in self.monitors)
        min_y = min(m.y for m in self.monitors)
        span_w = max(m.x + m.width for m in self.monitors) - min_x
        span_h = max(m.y + m.height for m in self.monitors) - min_y
        aspect = span_w / max(1, span_h)
        width = max(self.scroll.viewport().width(), 640)
        height = max(320, int(width / aspect) + 24)
        height = min(height, 720)
        self.monitor_map.setMinimumSize(width, height)

    def resizeEvent(self, event) -> None:  # type: ignore[no-untyped-def]
        super().resizeEvent(event)
        self._relayout_map()

    def _on_image_changed(self, key: str, assignment: Assignment | None) -> None:
        if assignment is None:
            self.assignments.pop(key, None)
        else:
            self.assignments[key] = assignment
        self._persist()

    def _on_mode_changed(self, key: str, mode: object) -> None:
        if key in self.assignments:
            try:
                self.assignments[key].mode = parse_fit_mode(mode)
            except ValueError:
                self.assignments[key].mode = FitMode.COVER
            self._persist()

    def _apply_image_to_all(self, key: str) -> None:
        source = self.assignments.get(key)
        if source is None:
            return
        for card_key, card in self.monitor_map.cards.items():
            assigned = Assignment(path=source.path, mode=card.current_mode())
            card.set_assignment(assigned)
            self.assignments[card_key] = assigned
        self._persist()

    def _persist(self) -> None:
        try:
            self.config = AppConfig(fill=self.fill_hex, assignments=dict(self.assignments))
            save_config(self.config)
        except Exception as exc:
            self.statusBar().showMessage(str(exc))

    def pick_fill_color(self) -> None:
        color = QColorDialog.getColor(QColor(self.fill_hex), self, t("fill_color"))
        if color.isValid():
            self.fill_hex = color.name().upper()
            self._paint_color_button()
            self._persist()

    def _paint_color_button(self) -> None:
        self.color_btn.setStyleSheet(
            f"QPushButton {{ padding: 6px 12px; border: 1px solid #888; "
            f"background: {self.fill_hex}; color: {'#111' if _is_light(self.fill_hex) else '#fff'}; }}"
        )

    def _compose(self) -> Image.Image | None:
        if not self.monitors:
            QMessageBox.warning(self, t("app_name"), t("no_displays"))
            return None
        if not self.assignments:
            QMessageBox.information(self, t("app_name"), t("need_image"))
            return None
        return compose(self.monitors, self.assignments, hex_to_rgb(self.fill_hex))

    def show_preview(self) -> None:
        image = self._compose()
        if image is None:
            return
        dialog = QMainWindow(self)
        dialog.setWindowTitle(t("preview_title"))
        label = QLabel()
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        pixmap = pil_to_pixmap(image)
        max_w, max_h = 1280, 720
        label.setPixmap(
            pixmap.scaled(
                max_w,
                max_h,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
        )
        dialog.setCentralWidget(label)
        dialog.resize(min(max_w, pixmap.width()), min(max_h, pixmap.height()))
        self._preview_window = dialog
        dialog.show()

    def apply_wallpaper(self) -> None:
        log_apply("gui apply clicked")
        image = self._compose()
        if image is None:
            return
        dest = output_dir() / f"composed-{int(time.time())}.png"
        image.save(dest, format="PNG")
        _prune_old_compositions(dest)
        try:
            apply_composed_image(dest, fill_hex=self.fill_hex)
        except WallpaperError as exc:
            if os.name == "nt":
                QMessageBox.information(self, t("app_name"), f"{t('not_linux')}\n\n{dest}")
            else:
                QMessageBox.critical(self, t("app_name"), f"{t('apply_failed')}\n{exc}")
            return
        except Exception as exc:
            QMessageBox.critical(self, t("app_name"), f"{t('apply_failed')}\n{exc}")
            return
        self.statusBar().showMessage(t("applied"))


def _is_light(hex_color: str) -> bool:
    r, g, b = hex_to_rgb(hex_color)
    return (r * 299 + g * 587 + b * 114) / 1000 > 140


def _prune_old_compositions(current: Path, keep: int = 4) -> None:
    files = sorted(output_dir().glob("composed-*.png"), key=lambda p: p.stat().st_mtime, reverse=True)
    for stale in files[keep:]:
        if stale != current:
            try:
                stale.unlink()
            except OSError:
                pass


def _stylesheet() -> str:
    return f"""
    QPushButton#applyButton {{
        background: {MINT_GREEN};
        color: white;
        font-weight: 600;
        padding: 8px 20px;
        border: none;
        border-radius: 6px;
    }}
    QPushButton#applyButton:hover {{
        background: #5A9842;
    }}
    QFrame#monitorCard {{
        background: palette(base);
        border: 1px solid palette(mid);
        border-radius: 10px;
    }}
    QFrame#monitorCard[filled="true"] {{
        border: 2px solid {MINT_GREEN};
    }}
    QFrame#monitorCard[dropHover="true"] {{
        border: 2px dashed {MINT_GREEN};
    }}
    QLabel#dropTarget {{
        background: palette(alternate-base);
        border: 1px dashed palette(mid);
        border-radius: 8px;
        padding: 8px;
        color: palette(mid);
    }}
    QLabel#cardTitle {{
        font-weight: 600;
    }}
    """


def run_gui() -> int:
    app = QApplication.instance() or QApplication(sys.argv)
    app.setApplicationName("Wallpane")
    app.setOrganizationName("wallpane")
    app.setStyle("Fusion")
    app.setStyleSheet(_stylesheet())
    window = MainWindow()
    window.show()
    return app.exec()
