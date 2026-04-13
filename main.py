import json
import os
import random
import sys
import threading
import time

import vlc
from PySide6.QtCore import QDir, QFileInfo, QSize, Qt, QTimer, Signal
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import (
    QAbstractItemView,
    QApplication,
    QCheckBox,
    QComboBox,
    QFileDialog,
    QFileIconProvider,
    QFileSystemModel,
    QFrame,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QProgressBar,
    QPushButton,
    QSlider,
    QSplitter,
    QStyle,
    QToolButton,
    QTreeView,
    QVBoxLayout,
    QWidget,
)
from screeninfo import get_monitors


def resource_path(*parts):
    base_path = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base_path, *parts)


def app_base_path():
    if getattr(sys, "frozen", False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))


def config_path():
    base_dir = app_base_path()
    if os.access(base_dir, os.W_OK):
        return os.path.join(base_dir, "playonthere_config.json")

    appdata_dir = os.path.join(os.environ.get("LOCALAPPDATA", base_dir), "PlayOnThere")
    os.makedirs(appdata_dir, exist_ok=True)
    return os.path.join(appdata_dir, "playonthere_config.json")


def configure_vlc_runtime():
    base_dir = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))
    search_dirs = [
        base_dir,
        os.path.join(base_dir, "_internal"),
    ]

    for directory in search_dirs:
        if os.path.isdir(directory) and hasattr(os, "add_dll_directory"):
            try:
                os.add_dll_directory(directory)
            except OSError:
                pass

    plugin_candidates = [
        os.path.join(base_dir, "plugins"),
        os.path.join(base_dir, "_internal", "plugins"),
    ]
    for plugins_dir in plugin_candidates:
        if os.path.isdir(plugins_dir):
            os.environ.setdefault("VLC_PLUGIN_PATH", plugins_dir)
            break


class PlaylistWidget(QListWidget):
    playlistChanged = Signal()

    def __init__(self):
        super().__init__()
        self.setSelectionMode(QAbstractItemView.SingleSelection)
        self.setDragDropMode(QAbstractItemView.InternalMove)
        self.setDefaultDropAction(Qt.MoveAction)
        self.setDragEnabled(True)
        self.setAcceptDrops(True)
        self.setDropIndicatorShown(True)

    def dropEvent(self, event):
        super().dropEvent(event)
        self.playlistChanged.emit()

    def keyPressEvent(self, event):
        if event.key() in (Qt.Key_Delete, Qt.Key_Backspace):
            current_item = self.currentItem()
            if current_item is not None:
                row = self.row(current_item)
                self.takeItem(row)
                self.playlistChanged.emit()
            return
        super().keyPressEvent(event)


class DualPlayer:
    def __init__(self):
        configure_vlc_runtime()
        self.instance = vlc.Instance()
        self.player_a = self.instance.media_player_new()
        self.player_b = self.instance.media_player_new()
        self.active = self.player_a
        self.inactive = self.player_b
        self.crossfade_time = 3.0
        self.volume = 100

    def set_media(self, player, path):
        media = self.instance.media_new(path)
        player.set_media(media)

    def play_first(self, path):
        self.set_media(self.active, path)
        self.active.audio_set_volume(self.volume)
        self.active.play()

    def prepare_next(self, path):
        self.set_media(self.inactive, path)
        self.inactive.audio_set_volume(0)

    def crossfade(self):
        self.inactive.audio_set_volume(0)
        self.inactive.play()

        steps = 30
        delay = self.crossfade_time / steps
        target_volume = self.volume

        def fade():
            for step in range(steps):
                active_volume = int(target_volume * (1 - step / steps))
                inactive_volume = int(target_volume * (step / steps))
                self.active.audio_set_volume(active_volume)
                self.inactive.audio_set_volume(inactive_volume)
                time.sleep(delay)

            self.active.stop()
            self.active, self.inactive = self.inactive, self.active
            self.active.audio_set_volume(target_volume)

        threading.Thread(target=fade, daemon=True).start()

    def stop(self):
        self.player_a.stop()
        self.player_b.stop()

    def pause(self):
        self.active.pause()

    def set_volume(self, volume):
        self.volume = max(0, min(100, int(volume)))
        self.player_a.audio_set_volume(self.volume)
        self.player_b.audio_set_volume(self.volume)

    def get_time(self):
        return max(0, self.active.get_time())

    def set_time(self, value):
        self.active.set_time(max(0, int(value)))

    def get_length(self):
        return max(0, self.active.get_length())

    def get_state(self):
        try:
            return str(self.active.get_state()).split(".")[-1]
        except Exception:
            return "Unknown"

    def set_audio_device(self, device_id):
        if not device_id:
            return

        try:
            self.player_a.audio_output_device_set(None, device_id)
            self.player_b.audio_output_device_set(None, device_id)
        except Exception:
            pass

    def get_audio_devices(self):
        devices = []

        try:
            mods = self.player_a.audio_output_device_enum()
            current = mods
            while current:
                device = current.contents
                dev_id = device.device.decode() if device.device else ""
                desc = device.description.decode() if device.description else "Unknown"
                devices.append((dev_id, desc))
                current = device.next

            if mods:
                vlc.libvlc_audio_output_device_list_release(mods)

        except Exception as error:
            print("Error obteniendo dispositivos:", error)

        return devices


class PlayerUI(QWidget):
    AUDIO_EXTENSIONS = {".mp3", ".wav", ".flac", ".ogg", ".aac", ".m4a", ".wma"}
    VIDEO_EXTENSIONS = {".mp4", ".mkv", ".avi", ".mov", ".webm", ".mpeg", ".mpg"}

    def __init__(self):
        super().__init__()

        self.setWindowTitle("PlayOnThere")
        self.resize(1280, 760)

        self.player = DualPlayer()
        self.playlist = []
        self.current_index = -1
        self.current_folder = ""
        self.background_image = ""
        self.monitors = []
        self.icon_provider = QFileIconProvider()
        self.restoring_session = False

        self.init_ui()
        self.apply_styles()
        self.configure_runtime()

    def init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(14, 14, 14, 14)
        main_layout.setSpacing(12)

        top_layout = QHBoxLayout()
        top_layout.setSpacing(10)

        self.drive_select = QComboBox()
        self.monitor_select = QComboBox()
        self.audio_select = QComboBox()
        self.fullscreen_check = QCheckBox("Fullscreen")
        self.background_btn = QPushButton("Fondo audio/stop")
        self.background_status = QLabel("Sin imagen de fondo")

        top_layout.addWidget(QLabel("Unidad"))
        top_layout.addWidget(self.drive_select)
        top_layout.addWidget(QLabel("Monitor"))
        top_layout.addWidget(self.monitor_select)
        top_layout.addWidget(QLabel("Audio"))
        top_layout.addWidget(self.audio_select)
        top_layout.addWidget(self.fullscreen_check)
        top_layout.addWidget(self.background_btn)
        top_layout.addWidget(self.background_status, 1)

        self.model = QFileSystemModel()
        self.model.setFilter(QDir.AllDirs | QDir.NoDotAndDotDot | QDir.Drives)
        self.model.setRootPath("")

        self.tree = QTreeView()
        self.tree.setModel(self.model)
        self.tree.setHeaderHidden(True)
        self.tree.hideColumn(1)
        self.tree.hideColumn(2)
        self.tree.hideColumn(3)

        browser_box = QGroupBox("Carpetas")
        browser_layout = QVBoxLayout(browser_box)
        browser_layout.addWidget(self.tree)

        self.file_list = PlaylistWidget()

        self.folder_status = QLabel("Selecciona una carpeta para cargar archivos compatibles")
        self.now_playing = QLabel("Estado: detenido")

        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 1000)
        self.progress_bar.setValue(0)
        self.progress_label = QLabel("00:00 / 00:00")

        progress_layout = QHBoxLayout()
        progress_layout.setSpacing(10)
        progress_layout.addWidget(self.progress_bar, 1)
        progress_layout.addWidget(self.progress_label)

        library_box = QGroupBox("Lista de reproducción")
        library_layout = QVBoxLayout(library_box)
        library_layout.setSpacing(10)
        library_layout.addWidget(self.folder_status)
        library_layout.addWidget(self.now_playing)
        library_layout.addLayout(progress_layout)
        library_layout.addWidget(self.file_list)

        splitter = QSplitter(Qt.Horizontal)
        splitter.addWidget(browser_box)
        splitter.addWidget(library_box)
        splitter.setSizes([360, 700])

        controls_frame = QFrame()
        controls_layout = QHBoxLayout(controls_frame)
        controls_layout.setContentsMargins(12, 10, 12, 10)
        controls_layout.setSpacing(12)

        self.prev_btn = self.create_transport_button(QStyle.SP_MediaSkipBackward, "Pista anterior", self.prev_track)
        self.play_btn = self.create_transport_button(QStyle.SP_MediaPlay, "Reproducir selección", self.play, 34)
        self.pause_btn = self.create_transport_button(QStyle.SP_MediaPause, "Pausar", self.pause_track)
        self.stop_btn = self.create_transport_button(QStyle.SP_MediaStop, "Detener", self.stop)
        self.next_btn = self.create_transport_button(QStyle.SP_MediaSkipForward, "Siguiente pista", self.next_track)
        self.random_btn = self.create_transport_button(QStyle.SP_BrowserReload, "Reproducción aleatoria", self.random_track)

        self.volume_label = QLabel("Vol 80%")
        self.volume_slider = QSlider(Qt.Horizontal)
        self.volume_slider.setRange(0, 100)
        self.volume_slider.setFixedWidth(150)

        controls_layout.addWidget(self.prev_btn)
        controls_layout.addWidget(self.play_btn)
        controls_layout.addWidget(self.pause_btn)
        controls_layout.addWidget(self.stop_btn)
        controls_layout.addWidget(self.next_btn)
        controls_layout.addWidget(self.random_btn)
        controls_layout.addStretch(1)
        controls_layout.addWidget(self.volume_label)
        controls_layout.addWidget(self.volume_slider)

        status_frame = QFrame()
        status_layout = QHBoxLayout(status_frame)
        status_layout.setContentsMargins(10, 6, 10, 6)
        status_layout.setSpacing(12)

        self.status_bar = QLabel()
        self.status_bar.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)

        self.credit_label = QLabel(
            '<a href="https://github.com/YoeKimera">Yoe Kimera en GitHub</a>'
        )
        self.credit_label.setTextFormat(Qt.RichText)
        self.credit_label.setTextInteractionFlags(Qt.TextBrowserInteraction)
        self.credit_label.setOpenExternalLinks(True)
        self.credit_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)

        status_layout.addWidget(self.status_bar, 1)
        status_layout.addWidget(self.credit_label)

        main_layout.addLayout(top_layout)
        main_layout.addWidget(splitter, 1)
        main_layout.addWidget(controls_frame)
        main_layout.addWidget(status_frame)

    def configure_runtime(self):
        icon_path = resource_path("play_icon.png")
        if os.path.exists(icon_path):
            self.setWindowIcon(QIcon(icon_path))
        else:
            self.setWindowIcon(self.style().standardIcon(QStyle.SP_MediaPlay))

        self.load_drives()
        self.load_monitors()
        self.load_audio_devices()

        self.drive_select.currentIndexChanged.connect(self.change_drive)
        self.monitor_select.currentIndexChanged.connect(self.change_monitor)
        self.audio_select.currentIndexChanged.connect(self.change_audio)
        self.background_btn.clicked.connect(self.load_background_image)
        self.file_list.itemDoubleClicked.connect(self.play_selected_item)
        self.file_list.playlistChanged.connect(self.sync_playlist_from_view)
        self.tree.clicked.connect(self.on_tree_click)
        self.volume_slider.valueChanged.connect(self.change_volume)

        self.player.set_volume(80)
        self.volume_slider.setValue(80)

        self.progress_timer = QTimer(self)
        self.progress_timer.setInterval(500)
        self.progress_timer.timeout.connect(self.update_playback_ui)
        self.progress_timer.start()

        if not self.load_session() and self.drive_select.count() > 0:
            self.change_drive()
            self.update_status_bar("Listo")

    def apply_styles(self):
        self.setStyleSheet(
            """
            QWidget {
                background: #23262b;
                color: #f4f4f4;
                font-size: 13px;
            }
            QGroupBox {
                border: 1px solid #4f545c;
                border-radius: 8px;
                margin-top: 14px;
                padding-top: 12px;
                background: #2d3138;
                font-weight: 600;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 12px;
                padding: 0 4px;
            }
            QComboBox, QPushButton, QListWidget, QTreeView, QProgressBar, QSlider {
                border: 1px solid #59606a;
                border-radius: 6px;
                background: #181b20;
                padding: 6px;
            }
            QTreeView, QListWidget {
                alternate-background-color: #2b3038;
            }
            QListWidget::item:selected, QTreeView::item:selected {
                background: #415a77;
                color: #ffffff;
            }
            QToolButton {
                border: 1px solid #7f8791;
                border-radius: 10px;
                background: qlineargradient(
                    x1: 0, y1: 0, x2: 0, y2: 1,
                    stop: 0 #d8d8d8,
                    stop: 1 #989898
                );
                padding: 8px;
            }
            QToolButton:hover {
                background: qlineargradient(
                    x1: 0, y1: 0, x2: 0, y2: 1,
                    stop: 0 #eeeeee,
                    stop: 1 #b4b4b4
                );
            }
            QToolButton:pressed {
                background: #7b7b7b;
            }
            QProgressBar {
                min-height: 18px;
                text-align: center;
            }
            QProgressBar::chunk {
                background: #5c7c9d;
                border-radius: 4px;
            }
            QSlider::groove:horizontal {
                height: 6px;
                background: #3a4048;
                border-radius: 3px;
            }
            QSlider::handle:horizontal {
                width: 16px;
                margin: -6px 0;
                border-radius: 8px;
                background: #d4d4d4;
                border: 1px solid #8f8f8f;
            }
            QFrame {
                border-radius: 10px;
            }
            QLabel {
                padding: 1px 0;
            }
            QLabel[textFormat="2"] {
                color: #9ecbff;
            }
            """
        )

    def create_transport_button(self, icon_type, tooltip, slot, icon_size=28):
        button = QToolButton()
        button.setIcon(self.style().standardIcon(icon_type))
        button.setIconSize(QSize(icon_size, icon_size))
        button.setToolTip(tooltip)
        button.setFixedSize(56, 56)
        button.clicked.connect(slot)
        return button

    def supported_extensions(self):
        return self.AUDIO_EXTENSIONS | self.VIDEO_EXTENSIONS

    def is_supported_file(self, path):
        return os.path.splitext(path)[1].lower() in self.supported_extensions()

    def is_audio_file(self, path):
        return os.path.splitext(path)[1].lower() in self.AUDIO_EXTENSIONS

    def format_ms(self, value):
        total_seconds = max(0, int(value / 1000))
        minutes, seconds = divmod(total_seconds, 60)
        hours, minutes = divmod(minutes, 60)
        if hours:
            return f"{hours:02d}:{minutes:02d}:{seconds:02d}"
        return f"{minutes:02d}:{seconds:02d}"

    def update_status_bar(self, playback_text=None):
        drive_text = self.drive_select.currentText() or "Sin unidad"
        monitor_text = self.monitor_select.currentText() or "Sin monitor"
        audio_text = self.audio_select.currentText() or "Salida por defecto"
        if playback_text is None:
            playback_text = self.now_playing.text()
        self.status_bar.setText(
            f"Unidad: {drive_text} | Monitor: {monitor_text} | Audio: {audio_text} | {playback_text}"
        )

    def update_playback_ui(self):
        length_ms = self.player.get_length()
        current_ms = self.player.get_time()

        if length_ms > 0:
            progress_value = int((current_ms / length_ms) * 1000)
            self.progress_bar.setValue(max(0, min(1000, progress_value)))
            self.progress_label.setText(f"{self.format_ms(current_ms)} / {self.format_ms(length_ms)}")
        else:
            self.progress_bar.setValue(0)
            self.progress_label.setText("00:00 / 00:00")

        if self.current_index != -1 and self.playlist:
            current_name = os.path.basename(self.playlist[self.current_index])
            playback_text = f"Estado: {self.player.get_state()} | Archivo: {current_name}"
        else:
            playback_text = self.now_playing.text()

        self.update_status_bar(playback_text)

    def load_drives(self):
        self.drive_select.clear()
        for drive in QDir.drives():
            drive_path = drive.absolutePath()
            self.drive_select.addItem(QDir.toNativeSeparators(drive_path), drive_path)

    def set_combo_by_data(self, combo, value, require_enabled=False):
        for index in range(combo.count()):
            if combo.itemData(index) != value:
                continue
            if require_enabled:
                item = combo.model().item(index)
                if item is not None and not item.isEnabled():
                    continue
            combo.setCurrentIndex(index)
            return True
        return False

    def set_tree_root(self, root_path):
        root_index = self.model.setRootPath(root_path)
        self.tree.setRootIndex(root_index)

    def scan_supported_files(self, folder_path):
        entries = []
        for name in sorted(os.listdir(folder_path), key=str.casefold):
            full_path = os.path.join(folder_path, name)
            if os.path.isfile(full_path) and self.is_supported_file(full_path):
                entries.append(full_path)
        return entries

    def populate_playlist(self, entries, folder_path, restored=False):
        self.current_folder = folder_path
        self.playlist = list(entries)
        self.file_list.clear()
        self.current_index = -1
        self.progress_bar.setValue(0)
        self.progress_label.setText("00:00 / 00:00")

        for path in self.playlist:
            item = QListWidgetItem(self.icon_provider.icon(QFileInfo(path)), os.path.basename(path))
            item.setToolTip(path)
            item.setData(Qt.UserRole, path)
            self.file_list.addItem(item)

        suffix = " | Sesión restaurada" if restored else " | Arrastra para reordenar, Supr para quitar"
        self.folder_status.setText(
            f"Carpeta: {folder_path} | {len(self.playlist)} archivo(s) compatible(s){suffix}"
        )

        if self.playlist:
            self.file_list.setCurrentRow(0)
            self.now_playing.setText("Estado: listo para reproducir")
        else:
            self.now_playing.setText("Estado: sin archivos compatibles en esta carpeta")

        self.update_status_bar()

    def refresh_file_list(self, folder_path):
        if not os.path.isdir(folder_path):
            self.folder_status.setText("La selección actual no es una carpeta válida")
            self.now_playing.setText("Estado: detenido")
            self.update_status_bar()
            return

        self.populate_playlist(self.scan_supported_files(folder_path), folder_path)

    def sync_playlist_from_view(self):
        current_path = None
        if self.current_index != -1 and self.current_index < len(self.playlist):
            current_path = self.playlist[self.current_index]

        updated_playlist = []
        for row in range(self.file_list.count()):
            item = self.file_list.item(row)
            updated_playlist.append(item.data(Qt.UserRole))

        self.playlist = updated_playlist

        if not self.playlist:
            self.current_index = -1
            self.now_playing.setText("Estado: lista vacía")
            self.progress_bar.setValue(0)
            self.progress_label.setText("00:00 / 00:00")
            self.update_status_bar()
            return

        if current_path in self.playlist:
            self.current_index = self.playlist.index(current_path)
        else:
            self.current_index = min(self.file_list.currentRow(), len(self.playlist) - 1)

        if self.file_list.currentRow() == -1 and self.playlist:
            self.file_list.setCurrentRow(0)

        self.update_status_bar()

    def restore_playback_state(self, media_path, position_ms, playback_state):
        if not media_path or not os.path.exists(media_path):
            return

        self.player.play_first(media_path)

        def apply_resume_state(attempt=0):
            length_ms = self.player.get_length()
            if length_ms <= 0 and attempt < 10:
                QTimer.singleShot(300, lambda: apply_resume_state(attempt + 1))
                return

            if position_ms > 0:
                self.player.set_time(position_ms)

            if playback_state == "Paused":
                self.player.pause()

            self.now_playing.setText(f"Reproduciendo: {os.path.basename(media_path)}")
            self.update_playback_ui()

        QTimer.singleShot(300, apply_resume_state)

    def save_session(self):
        current_path = ""
        if self.current_index != -1 and self.current_index < len(self.playlist):
            current_path = self.playlist[self.current_index]

        session_data = {
            "drive_path": self.drive_select.currentData() or "",
            "current_folder": self.current_folder,
            "playlist": [path for path in self.playlist if os.path.exists(path)],
            "current_index": self.current_index,
            "current_path": current_path,
            "selected_index": self.current_selected_index(),
            "background_image": self.background_image,
            "audio_device": self.audio_select.currentData() or "",
            "monitor_index": self.monitor_select.currentData(),
            "fullscreen": self.fullscreen_check.isChecked(),
            "volume": self.volume_slider.value(),
            "playback_state": self.player.get_state(),
            "playback_position_ms": self.player.get_time(),
        }

        with open(config_path(), "w", encoding="utf-8") as config_file:
            json.dump(session_data, config_file, ensure_ascii=False, indent=2)

    def load_session(self):
        session_file = config_path()
        if not os.path.exists(session_file):
            return False

        try:
            with open(session_file, "r", encoding="utf-8") as config_file:
                session_data = json.load(config_file)
        except (OSError, json.JSONDecodeError):
            return False

        self.restoring_session = True
        try:
            saved_volume = int(session_data.get("volume", 80))
            self.volume_slider.setValue(max(0, min(100, saved_volume)))

            background_image = session_data.get("background_image", "")
            if background_image and os.path.exists(background_image):
                self.background_image = background_image
                self.background_status.setText(f"Fondo activo: {os.path.basename(background_image)}")

            drive_path = session_data.get("drive_path", "")
            if drive_path:
                self.set_combo_by_data(self.drive_select, drive_path)
                self.set_tree_root(drive_path)

            folder_path = session_data.get("current_folder", "")
            saved_playlist = [
                path for path in session_data.get("playlist", [])
                if os.path.exists(path) and self.is_supported_file(path)
            ]

            if saved_playlist:
                restored_folder = folder_path or os.path.dirname(saved_playlist[0])
                self.populate_playlist(saved_playlist, restored_folder, restored=True)
            elif folder_path and os.path.isdir(folder_path):
                self.populate_playlist(self.scan_supported_files(folder_path), folder_path, restored=True)
            elif self.drive_select.count() > 0:
                self.change_drive()

            selected_audio = session_data.get("audio_device", "")
            self.set_combo_by_data(self.audio_select, selected_audio)
            self.change_audio()

            saved_monitor = session_data.get("monitor_index")
            if saved_monitor is not None and self.set_combo_by_data(
                self.monitor_select, saved_monitor, require_enabled=True
            ):
                self.fullscreen_check.setChecked(bool(session_data.get("fullscreen", False)))
                self.change_monitor()
            else:
                self.fullscreen_check.setChecked(bool(session_data.get("fullscreen", False)))

            selected_index = int(session_data.get("selected_index", 0))
            current_path = session_data.get("current_path", "")
            if current_path and current_path in self.playlist:
                selected_index = self.playlist.index(current_path)

            if self.playlist and 0 <= selected_index < len(self.playlist):
                self.file_list.setCurrentRow(selected_index)
                self.current_index = selected_index
                self.now_playing.setText(f"Estado: listo para continuar | {os.path.basename(self.playlist[selected_index])}")

            playback_state = session_data.get("playback_state", "Stopped")
            playback_position = int(session_data.get("playback_position_ms", 0))
            if current_path and current_path in self.playlist and playback_state in {"Playing", "Paused"}:
                self.restore_playback_state(current_path, playback_position, playback_state)

            self.update_status_bar("Sesión restaurada")
            return True
        finally:
            self.restoring_session = False

    def current_selected_index(self):
        row = self.file_list.currentRow()
        if row < 0 and self.playlist:
            return 0
        return row

    def play_track_at(self, index, use_crossfade=False):
        if not self.playlist or index < 0 or index >= len(self.playlist):
            return

        path = self.playlist[index]
        if self.current_index == -1 or not use_crossfade:
            self.player.play_first(path)
        else:
            self.player.prepare_next(path)
            self.player.crossfade()

        self.current_index = index
        self.file_list.setCurrentRow(index)
        self.now_playing.setText(f"Reproduciendo: {os.path.basename(path)}")
        self.update_playback_ui()

    def load_monitors(self):
        self.monitors = get_monitors()
        self.monitor_select.clear()

        first_enabled_index = -1
        for index, monitor in enumerate(self.monitors):
            title = "Principal" if monitor.is_primary else f"Monitor {index}"
            self.monitor_select.addItem(f"{title} - {monitor.width}x{monitor.height}", index)
            combo_index = self.monitor_select.count() - 1
            item = self.monitor_select.model().item(combo_index)
            if item is not None and monitor.is_primary:
                item.setEnabled(False)
            elif first_enabled_index == -1:
                first_enabled_index = combo_index

        if first_enabled_index >= 0:
            self.monitor_select.setCurrentIndex(first_enabled_index)

    def change_monitor(self):
        monitor_index = self.monitor_select.currentData()
        if monitor_index is None:
            return

        monitor = self.monitors[monitor_index]
        if monitor.is_primary:
            self.update_status_bar("Monitor principal bloqueado")
            return

        self.move(monitor.x, monitor.y)
        self.resize(monitor.width, monitor.height)

        if self.fullscreen_check.isChecked():
            self.showFullScreen()
        else:
            self.showNormal()

        self.update_status_bar()

    def load_audio_devices(self):
        self.audio_select.clear()
        self.audio_select.addItem("Salida por defecto", "")
        for dev_id, description in self.player.get_audio_devices():
            self.audio_select.addItem(description, dev_id)

    def change_audio(self):
        self.player.set_audio_device(self.audio_select.currentData())
        self.update_status_bar()

    def change_volume(self, value):
        self.player.set_volume(value)
        self.volume_label.setText(f"Vol {value}%")
        self.update_status_bar()

    def change_drive(self):
        drive_path = self.drive_select.currentData()
        if not drive_path:
            return

        self.set_tree_root(drive_path)
        if not self.restoring_session:
            self.refresh_file_list(drive_path)

    def on_tree_click(self, index):
        path = self.model.filePath(index)
        if os.path.isdir(path):
            self.refresh_file_list(path)

    def play(self):
        if not self.playlist:
            return

        selected_index = self.current_selected_index()
        if selected_index == -1:
            return

        use_crossfade = self.current_index != -1 and self.current_index != selected_index
        self.play_track_at(selected_index, use_crossfade)

    def pause_track(self):
        self.player.pause()
        self.now_playing.setText("Estado: pausado")
        self.update_status_bar()

    def stop(self):
        self.player.stop()
        current_name = "sin selección"
        if self.current_index != -1 and self.current_index < len(self.playlist):
            current_name = os.path.basename(self.playlist[self.current_index])
        self.now_playing.setText(f"Estado: detenido | Última pista: {current_name}")
        self.progress_bar.setValue(0)
        self.progress_label.setText("00:00 / 00:00")
        self.update_status_bar()

    def next_track(self):
        if not self.playlist:
            return

        next_index = (self.current_selected_index() + 1) % len(self.playlist)
        self.play_track_at(next_index, self.current_index != -1)

    def prev_track(self):
        if not self.playlist:
            return

        prev_index = (self.current_selected_index() - 1) % len(self.playlist)
        self.play_track_at(prev_index, self.current_index != -1)

    def random_track(self):
        if not self.playlist:
            return

        random_index = random.randint(0, len(self.playlist) - 1)
        self.play_track_at(random_index, self.current_index != -1)

    def play_selected_item(self, item):
        path = item.data(Qt.UserRole)
        if path in self.playlist:
            self.play_track_at(self.playlist.index(path), self.current_index != -1)

    def load_background_image(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Seleccionar imagen de fondo",
            "",
            "Imágenes (*.png *.jpg *.jpeg *.bmp *.webp)",
        )
        if file_path:
            self.background_image = file_path
            self.background_status.setText(f"Fondo activo: {os.path.basename(file_path)}")

    def closeEvent(self, event):
        self.save_session()
        super().closeEvent(event)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setApplicationName("PlayOnThere")
    app.setApplicationDisplayName("PlayOnThere")
    window = PlayerUI()
    window.show()
    sys.exit(app.exec())