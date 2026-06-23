"""
Главное окно приложения — единственный экран UI.
Светлая, минималистичная тема, без анимаций.
"""
import os
import sys

from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap, QIcon  # Добавили импорт QIcon
from PySide6.QtNetwork import QNetworkAccessManager, QNetworkRequest
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton,
    QComboBox, QProgressBar, QFileDialog, QMessageBox, QGroupBox
)

from core.settings import AppSettings
from core.workers import AnalyzeWorker, DownloadWorker
from core.downloader import DownloadTask

LIGHT_STYLE = """
QWidget { background-color: #fafafa; color: #222; font-family: 'Segoe UI', sans-serif; font-size: 13px; }
QLineEdit, QComboBox { padding: 6px; border: 1px solid #ccc; border-radius: 4px; background: #fff; }
QPushButton { padding: 8px 14px; border-radius: 4px; background-color: #e53935; color: white; border: none; }
QPushButton:hover { background-color: #c62828; }
QPushButton:disabled { background-color: #ccc; color: #777; }
QPushButton#secondary { background-color: #eee; color: #333; }
QPushButton#secondary:hover { background-color: #ddd; }
QProgressBar { border: 1px solid #ccc; border-radius: 4px; text-align: center; background: #fff; }
QProgressBar::chunk { background-color: #e53935; border-radius: 4px; }
QGroupBox { border: 1px solid #ddd; border-radius: 6px; margin-top: 10px; padding-top: 12px; }
QGroupBox::title { subcontrol-origin: margin; left: 10px; padding: 0 4px; }
"""


class MainWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("YouTube Downloader")
        self.setMinimumWidth(560)
        self.setStyleSheet(LIGHT_STYLE)

        # --- НАСТРОЙКА ИКОНКИ ДЛЯ ОКНА И ПАНЕЛИ ЗАДАЧ ---
        # Определяем путь к иконке в зависимости от режима запуска
        if getattr(sys, 'frozen', False):
            # Режим скомпилированного .exe (PyInstaller создает папку во временном хранилище)
            icon_path = os.path.join(sys._MEIPASS, 'resources', 'app.ico')
        else:
            # Режим разработки: берем абсолютный путь от корня проекта
            project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            icon_path = os.path.join(project_root, 'resources', 'app.ico')

        if os.path.exists(icon_path):
            self.setWindowIcon(QIcon(icon_path))
        # ------------------------------------------------

        self.settings = AppSettings()
        self.video_info = None
        self.thumbnail_pixmap = None
        self.analyze_worker = None
        self.download_worker = None
        self.net_manager = QNetworkAccessManager(self)

        self._build_ui()

    # ---------- UI構築 ----------
    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setSpacing(12)
        root.setContentsMargins(16, 16, 16, 16)

        # --- Ссылка ---
        url_row = QHBoxLayout()
        self.url_input = QLineEdit()
        self.url_input.setPlaceholderText("Вставьте ссылку на видео YouTube...")
        self.analyze_btn = QPushButton("Анализировать")
        self.analyze_btn.clicked.connect(self.on_analyze)
        url_row.addWidget(self.url_input)
        url_row.addWidget(self.analyze_btn)
        root.addLayout(url_row)

        # --- Превью / инфо ---
        self.info_box = QGroupBox("Информация о видео")
        info_layout = QHBoxLayout()
        self.thumb_label = QLabel()
        self.thumb_label.setFixedSize(160, 90)
        self.thumb_label.setStyleSheet("background:#eee; border-radius:4px;")
        self.thumb_label.setAlignment(Qt.AlignCenter)
        self.thumb_label.setText("Превью")

        text_col = QVBoxLayout()
        self.title_label = QLabel("—")
        self.title_label.setWordWrap(True)
        self.title_label.setStyleSheet("font-weight: 600;")
        self.duration_label = QLabel("Длительность: —")
        text_col.addWidget(self.title_label)
        text_col.addWidget(self.duration_label)
        text_col.addStretch()

        self.close_video_btn = QPushButton("Закрыть видео")
        self.close_video_btn.setObjectName("secondary")
        self.close_video_btn.setEnabled(False)
        self.close_video_btn.clicked.connect(self.on_close_video)

        info_layout.addWidget(self.thumb_label)
        info_layout.addLayout(text_col)
        info_layout.addWidget(self.close_video_btn, alignment=Qt.AlignTop)
        self.info_box.setLayout(info_layout)
        root.addWidget(self.info_box)

        # --- Параметры скачивания ---
        params_box = QGroupBox("Параметры скачивания")
        params_layout = QVBoxLayout()

        fmt_row = QHBoxLayout()
        fmt_row.addWidget(QLabel("Формат:"))
        self.format_combo = QComboBox()
        self.format_combo.addItems(["mp4 (видео)", "mp3 (только аудио)"])
        self.format_combo.currentIndexChanged.connect(self.on_format_changed)
        fmt_row.addWidget(self.format_combo)

        fmt_row.addSpacing(20)
        fmt_row.addWidget(QLabel("Качество:"))
        self.quality_combo = QComboBox()
        self.quality_combo.addItem("Сначала нажмите «Анализировать»")
        self.quality_combo.setEnabled(False)
        fmt_row.addWidget(self.quality_combo)
        params_layout.addLayout(fmt_row)

        folder_row = QHBoxLayout()
        self.folder_input = QLineEdit(self.settings.save_folder or os.path.expanduser("~/Downloads"))
        self.folder_btn = QPushButton("Выбрать папку")
        self.folder_btn.clicked.connect(self.on_choose_folder)
        folder_row.addWidget(self.folder_input)
        folder_row.addWidget(self.folder_btn)
        params_layout.addLayout(folder_row)

        params_box.setLayout(params_layout)
        root.addWidget(params_box)

        # --- Скачивание ---
        download_row = QHBoxLayout()
        self.download_btn = QPushButton("Скачать")
        self.download_btn.setEnabled(False)
        self.download_btn.clicked.connect(self.on_download)
        self.cancel_btn = QPushButton("Отменить скачивание")
        self.cancel_btn.setObjectName("secondary")
        self.cancel_btn.setVisible(False)
        self.cancel_btn.clicked.connect(self.on_cancel_download)
        download_row.addWidget(self.download_btn)
        download_row.addWidget(self.cancel_btn)
        root.addLayout(download_row)

        self.progress_bar = QProgressBar()
        self.progress_bar.setValue(0)
        root.addWidget(self.progress_bar)

        self.status_label = QLabel("")
        self.status_label.setStyleSheet("color: #666;")
        root.addWidget(self.status_label)

        root.addStretch()

    # ---------- Обработчики ----------
    def on_format_changed(self, _idx):
        is_mp3 = self.format_combo.currentIndex() == 1
        self.quality_combo.setEnabled(not is_mp3 and self.quality_combo.count() > 1 and self.video_info is not None)

    def on_choose_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Выберите папку для сохранения", self.folder_input.text())
        if folder:
            self.folder_input.setText(folder)
            self.settings.save_folder = folder
            self.settings.sync()

    def on_analyze(self):
        url = self.url_input.text().strip()
        if not url:
            QMessageBox.warning(self, "Ошибка", "Вставьте ссылку на видео.")
            return

        self.analyze_btn.setEnabled(False)
        self.status_label.setText("Получение информации о видео...")
        self.download_btn.setEnabled(False)

        self.analyze_worker = AnalyzeWorker(url)
        self.analyze_worker.finished_ok.connect(self.on_analyze_ok)
        self.analyze_worker.finished_error.connect(self.on_analyze_error)
        self.analyze_worker.start()

    def on_analyze_ok(self, info):
        self.video_info = info
        self.analyze_btn.setEnabled(True)
        self.status_label.setText("Готово к скачиванию.")

        self.title_label.setText(info.title)
        self.duration_label.setText(f"Длительность: {info.duration_str}")

        self.quality_combo.clear()
        self.quality_combo.setEnabled(True)
        if info.formats:
            self.quality_combo.addItems(list(reversed(info.formats)))
        else:
            self.quality_combo.addItem("best")

        self.download_btn.setEnabled(True)
        self.close_video_btn.setEnabled(True)
        self.thumbnail_pixmap = None
        self._load_thumbnail(info.thumbnail)

    def on_analyze_error(self, message: str):
        self.analyze_btn.setEnabled(True)
        self.status_label.setText("")
        QMessageBox.critical(self, "Не удалось получить данные", message)

    def _load_thumbnail(self, url: str):
        if not url:
            return
        request = QNetworkRequest(url)
        reply = self.net_manager.get(request)
        reply.finished.connect(lambda: self._on_thumb_loaded(reply))

    def _on_thumb_loaded(self, reply):
        data = reply.readAll()
        pixmap = QPixmap()
        if pixmap.loadFromData(data):
            self.thumbnail_pixmap = pixmap
            scaled = pixmap.scaled(160, 90, Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation)
            self.thumb_label.setPixmap(scaled)
        reply.deleteLater()

    def on_close_video(self):
        """Сбрасывает текущий анализ видео и возвращает экран в исходное состояние."""
        self.video_info = None
        self.thumbnail_pixmap = None

        self.url_input.clear()
        self.title_label.setText("—")
        self.duration_label.setText("Длительность: —")
        self.thumb_label.clear()
        self.thumb_label.setText("Превью")

        self.quality_combo.clear()
        self.quality_combo.addItem("Сначала нажмите «Анализировать»")
        self.quality_combo.setEnabled(False)

        self.download_btn.setEnabled(False)
        self.close_video_btn.setEnabled(False)
        self.progress_bar.setValue(0)
        self.status_label.setText("")

    def on_download(self):
        if not self.video_info:
            return

        fmt = "mp3" if self.format_combo.currentIndex() == 1 else "mp4"
        quality = self.quality_combo.currentText() if self.quality_combo.isEnabled() else "best"
        folder = self.folder_input.text().strip() or os.path.expanduser("~/Downloads")

        task = DownloadTask(
            url=self.video_info.webpage_url or self.url_input.text().strip(),
            quality=quality,
            fmt=fmt,
            save_folder=folder,
        )

        self.settings.save_folder = folder
        self.settings.last_format = fmt
        self.settings.sync()

        self.download_btn.setEnabled(False)
        self.analyze_btn.setEnabled(False)
        self.cancel_btn.setVisible(True)
        self.progress_bar.setValue(0)
        self.status_label.setText("Скачивание начато...")

        self.download_worker = DownloadWorker(task)
        self.download_worker.progress.connect(self.on_progress)
        self.download_worker.log.connect(lambda m: self.status_label.setText(m))
        self.download_worker.finished_ok.connect(self.on_download_ok)
        self.download_worker.finished_error.connect(self.on_download_error)
        self.download_worker.cancelled.connect(self.on_download_cancelled)
        self.download_worker.start()

    def on_cancel_download(self):
        if self.download_worker:
            self.download_worker.cancel()
            self.status_label.setText("Отмена скачивания...")
            self.cancel_btn.setEnabled(False)

    def on_progress(self, percent: float, speed: str):
        self.progress_bar.setValue(int(percent))
        self.status_label.setText(f"Скачивание... {percent:.1f}% — {speed}")

    def _reset_after_download(self):
        self.download_btn.setEnabled(True)
        self.analyze_btn.setEnabled(True)
        self.cancel_btn.setVisible(False)
        self.cancel_btn.setEnabled(True)

    def on_download_ok(self, filepath: str):
        self._reset_after_download()
        self.progress_bar.setValue(100)
        self.status_label.setText(f"Готово: {filepath}")
        QMessageBox.information(self, "Скачивание завершено", f"Файл сохранён:\n{filepath}")

    def on_download_error(self, message: str):
        self._reset_after_download()
        self.status_label.setText("Ошибка скачивания.")
        QMessageBox.critical(self, "Ошибка скачивания", message)

    def on_download_cancelled(self):
        self._reset_after_download()
        self.progress_bar.setValue(0)
        self.status_label.setText("Скачивание отменено.")