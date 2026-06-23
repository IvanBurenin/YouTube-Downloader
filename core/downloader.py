"""
Логика скачивания видео/аудио через yt-dlp с поддержкой:
- выбора качества,
- выбора формата (mp4/mp3),
- передачи прогресса (% и скорость) в UI через callback.
"""
import os
import sys
import yt_dlp

from core.exceptions import DownloadError, NetworkError, VideoUnavailableError, DownloadCancelledError


def _ffmpeg_location() -> str | None:
    """
    Возвращает путь к ffmpeg.exe рядом с программой — либо встроенный
    в собранный exe (PyInstaller), либо лежащий в папке проекта при
    запуске через 'python main.py'. Если не найден — None, тогда
    yt-dlp ищет ffmpeg в системном PATH самостоятельно.
    """
    if getattr(sys, "frozen", False):
        bundled = os.path.join(sys._MEIPASS, "ffmpeg.exe")
        if os.path.exists(bundled):
            return bundled
    else:
        project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        local_ffmpeg = os.path.join(project_root, "ffmpeg.exe")
        if os.path.exists(local_ffmpeg):
            return local_ffmpeg
    return None


class DownloadTask:
    """Параметры одной задачи скачивания."""
    def __init__(self, url, quality, fmt, save_folder):
        self.url = url
        self.quality = quality
        self.fmt = fmt
        self.save_folder = save_folder


def _format_selector(quality: str, fmt: str) -> str:
    """Строит строку выбора формата для yt-dlp."""
    if fmt == "mp3":
        return "bestaudio/best"
    if quality in ("", "best", "Лучшее"):
        return "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best"
    height = quality.rstrip("p")
    return (
        f"bestvideo[height<={height}][ext=mp4]+bestaudio[ext=m4a]/"
        f"best[height<={height}][ext=mp4]/best[height<={height}]"
    )


def _process_entry(task: DownloadTask, progress_queue):
    """Точка входа для запуска скачивания в отдельном системном процессе."""
    def progress_cb(p, s):
        progress_queue.put(("progress", p, s))

    def log_cb(m):
        progress_queue.put(("log", m))

    try:
        path = run_download(task, progress_callback=progress_cb, log_callback=log_cb)
        progress_queue.put(("ok", path))
    except DownloadCancelledError:
        progress_queue.put(("cancelled", ""))
    except (NetworkError, VideoUnavailableError, DownloadError) as e:
        progress_queue.put(("error", e.message))
    except Exception as e:
        progress_queue.put(("error", f"Непредвиденная ошибка: {e}"))


def run_download(task: DownloadTask, progress_callback=None, log_callback=None, cancel_event=None) -> str:
    """Выполняет скачивание согласно task. Возвращает путь к итоговому файлу."""
    os.makedirs(task.save_folder, exist_ok=True)
    outtmpl = os.path.join(task.save_folder, "%(title).100s.%(ext)s")

    def hook(d):
        if cancel_event is not None and cancel_event.is_set():
            raise DownloadCancelledError("Скачивание отменено пользователем.")

        if d.get("status") == "downloading":
            total = d.get("total_bytes") or d.get("total_bytes_estimate")
            downloaded = d.get("downloaded_bytes", 0)
            speed = d.get("speed")
            speed_str = f"{speed / 1024 / 1024:.2f} МБ/с" if speed else "—"

            if total:
                percent = downloaded / total * 100
            else:
                frag_idx = d.get("fragment_index")
                frag_count = d.get("fragment_count")
                if frag_idx and frag_count:
                    percent = frag_idx / frag_count * 100
                else:
                    percent = 0.0
                    speed_str = f"{speed_str} (размер неизвестен)" if speed else "идёт загрузка..."

            if progress_callback:
                progress_callback(percent, speed_str)
        elif d.get("status") == "finished":
            if log_callback:
                log_callback("Загрузка завершена, выполняется обработка файла...")

    ydl_opts = {
        "outtmpl": outtmpl,
        "format": _format_selector(task.quality, task.fmt),
        "progress_hooks": [hook],
        "quiet": True,
        "no_warnings": True,
        "noplaylist": True,
        "merge_output_format": "mp4" if task.fmt == "mp4" else None,
    }

    ffmpeg_path = _ffmpeg_location()
    if ffmpeg_path:
        ydl_opts["ffmpeg_location"] = ffmpeg_path

    if task.fmt == "mp3":
        ydl_opts["postprocessors"] = [
            {
                "key": "FFmpegExtractAudio",
                "preferredcodec": "mp3",
                "preferredquality": "192",
            }
        ]

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(task.url, download=True)
            filepath = ydl.prepare_filename(info)
            if task.fmt == "mp3":
                base, _ = os.path.splitext(filepath)
                filepath = base + ".mp3"
            return filepath
            
    except yt_dlp.utils.DownloadError as e:
        msg = str(e).lower()
        
        # --- НОВАЯ КРАСИВАЯ ОБРАБОТКА UI ОШИБОК АВТОРИЗАЦИИ / БОТОВ ---
        oauth_triggers = ["oauth", "cookie", "sign in", "not a bot", "captcha", "confirm you're"]
        if any(trigger in msg for trigger in oauth_triggers):
            raise DownloadError("Ошибка OAuth2 (Cookies). Пожалуйста, попробуйте снова через несколько секунд.")
            
        if "private" in msg or "unavailable" in msg or "removed" in msg:
            raise VideoUnavailableError("Видео недоступно для скачивания.")
            
        raise NetworkError("Ошибка сети при скачивании. Проверьте соединение и повторите попытку.")
    except OSError as e:
        raise DownloadError(f"Ошибка файловой системы: {e}")
    except Exception as e:
        raise DownloadError(f"Непредвиденная ошибка при скачивании: {e}")