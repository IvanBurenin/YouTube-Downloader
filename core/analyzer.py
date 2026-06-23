"""
Получение информации о видео (название, превью, длительность, доступные качества)
без скачивания самого файла.
"""
import re
import socket

import yt_dlp

from core.exceptions import InvalidUrlError, NetworkError, VideoUnavailableError

YOUTUBE_URL_RE = re.compile(
    r"(https?://)?(www\.)?(youtube\.com/watch\?v=|youtu\.be/|youtube\.com/shorts/)[\w\-]+"
)


class VideoInfo:
    """Простой контейнер с информацией о видео, удобной для UI."""

    def __init__(self, raw: dict):
        self.id = raw.get("id")
        self.title = raw.get("title", "Без названия")
        self.thumbnail = raw.get("thumbnail")
        self.duration = raw.get("duration") or 0  # секунды
        self.webpage_url = raw.get("webpage_url")
        self.formats = self._extract_qualities(raw.get("formats", []))

    @staticmethod
    def _extract_qualities(formats: list) -> list:
        """Возвращает отсортированный список уникальных видео-качеств (например 1080p)."""
        qualities = {}
        for f in formats:
            height = f.get("height")
            if not height:
                continue
            label = f"{height}p"
            # Запоминаем лучший format_id для каждой высоты (приоритет mp4/avc)
            qualities[height] = label
        return [qualities[h] for h in sorted(qualities.keys())]

    @property
    def duration_str(self) -> str:
        h, rem = divmod(int(self.duration), 3600)
        m, s = divmod(rem, 60)
        if h:
            return f"{h:02d}:{m:02d}:{s:02d}"
        return f"{m:02d}:{s:02d}"


def validate_url(url: str) -> str:
    """Проверяет, что строка похожа на ссылку YouTube. Возвращает очищенный url."""
    url = url.strip()
    if not url or not YOUTUBE_URL_RE.search(url):
        raise InvalidUrlError(
            "Ссылка не похожа на ссылку YouTube. Проверьте и попробуйте снова."
        )
    return url


def fetch_video_info(url: str) -> VideoInfo:
    """
    Делает запрос к YouTube через yt-dlp (без скачивания) и возвращает VideoInfo.
    Бросает InvalidUrlError / NetworkError / VideoUnavailableError при проблемах.
    """
    url = validate_url(url)

    ydl_opts = {
        "quiet": True,
        "no_warnings": True,
        "skip_download": True,
        "noplaylist": True,
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            raw_info = ydl.extract_info(url, download=False)
    except yt_dlp.utils.DownloadError as e:
        msg = str(e).lower()
        if "private" in msg or "unavailable" in msg or "removed" in msg:
            raise VideoUnavailableError(
                "Видео недоступно: оно может быть приватным, удалённым "
                "или заблокированным в вашем регионе."
            )
        raise NetworkError(
            "Не удалось получить данные о видео. Проверьте ссылку и соединение."
        )
    except (socket.gaierror, ConnectionError, OSError):
        raise NetworkError("Нет соединения с интернетом. Проверьте сеть и повторите попытку.")

    if raw_info is None:
        raise VideoUnavailableError("Видео недоступно.")

    return VideoInfo(raw_info)
