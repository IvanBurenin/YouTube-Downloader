"""
Пользовательские исключения для понятной обработки ошибок в UI.
"""


class AppError(Exception):
    """Базовая ошибка приложения с человекочитаемым сообщением."""

    def __init__(self, message: str):
        super().__init__(message)
        self.message = message


class InvalidUrlError(AppError):
    """Ссылка не похожа на ссылку YouTube или имеет неверный формат."""
    pass


class NetworkError(AppError):
    """Проблемы с подключением к интернету / YouTube."""
    pass


class VideoUnavailableError(AppError):
    """Видео удалено, приватное, недоступно в регионе и т.д."""
    pass


class DownloadError(AppError):
    """Ошибка в процессе скачивания/обработки файла."""
    pass


class DownloadCancelledError(AppError):
    """Пользователь отменил скачивание."""
    pass
