"""
Фоновые потоки/процессы, чтобы сетевые операции не блокировали интерфейс.
"""
import multiprocessing
import os
import subprocess
import glob
import time

from PySide6.QtCore import QThread, Signal

from core.analyzer import fetch_video_info
from core.downloader import DownloadTask, _process_entry
from core.exceptions import AppError


class AnalyzeWorker(QThread):
    finished_ok = Signal(object)   # VideoInfo
    finished_error = Signal(str)

    def __init__(self, url: str):
        super().__init__()
        self.url = url

    def run(self):
        try:
            info = fetch_video_info(self.url)
            self.finished_ok.emit(info)
        except AppError as e:
            self.finished_error.emit(e.message)
        except Exception as e:
            self.finished_error.emit(f"Непредвиденная ошибка: {e}")


def _kill_ffmpeg_processes():
    """Принудительно завершает зависшие процессы ffmpeg.exe (Windows)."""
    if os.name == "nt":
        try:
            subprocess.run(
                ["taskkill", "/F", "/IM", "ffmpeg.exe", "/T"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
        except Exception:
            pass


class DownloadWorker(QThread):
    progress = Signal(float, str)   # percent, speed_str
    log = Signal(str)
    finished_ok = Signal(str)       # путь к файлу
    finished_error = Signal(str)
    cancelled = Signal()

    def __init__(self, task: DownloadTask):
        super().__init__()
        self.task = task
        self._process = None
        self._cancel_requested = False

    def cancel(self):
        """Запрашивает немедленную остановку скачивания (вызывается из UI-потока)."""
        self._cancel_requested = True

    def run(self):
        queue = multiprocessing.Queue()
        self._process = multiprocessing.Process(
            target=_process_entry, args=(self.task, queue), daemon=True
        )
        self._process.start()

        try:
            while True:
                if self._cancel_requested:
                    self._terminate_process()
                    self._clean_part_files() # Удаляем мусор ПОСЛЕ закрытия процесса
                    self.cancelled.emit()
                    return

                try:
                    kind, *payload = queue.get(timeout=0.2)
                except Exception:
                    if not self._process.is_alive():
                        self.finished_error.emit(
                            "Процесс скачивания неожиданно завершился."
                        )
                        return
                    continue

                if kind == "progress":
                    percent, speed = payload
                    self.progress.emit(percent, speed)
                elif kind == "log":
                    (message,) = payload
                    self.log.emit(message)
                elif kind == "ok":
                    (filepath,) = payload
                    self.finished_ok.emit(filepath)
                    return
                elif kind == "error":
                    (message,) = payload
                    self.finished_error.emit(message)
                    return
                elif kind == "cancelled":
                    self._clean_part_files()
                    self.cancelled.emit()
                    return
        finally:
            if self._process and self._process.is_alive():
                self._terminate_process()

    def _terminate_process(self):
        """Гарантированно и жестко завершает процесс скачивания."""
        if self._process and self._process.is_alive():
            self._process.terminate()
            self._process.join(timeout=2)
            if self._process.is_alive():
                self._process.kill()
        _kill_ffmpeg_processes()
        # Небольшая пауза, чтобы ОС успела разблокировать дескрипторы файлов
        time.sleep(0.3)

    def _clean_part_files(self):
        """Сканирует папку сохранения и удаляет любые недокачанные фрагменты."""
        try:
            extensions = ["*.part", "*.ytdl", "*.part.mp4", "*.part.m4a", "*.part.webm"]
            for ext in extensions:
                for part_file in glob.glob(os.path.join(self.task.save_folder, ext)):
                    if os.path.exists(part_file):
                        os.remove(part_file)
        except Exception:
            pass