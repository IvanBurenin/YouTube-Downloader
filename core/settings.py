"""
Хранение и загрузка локальных настроек приложения.
Используется QSettings (реестр Windows / ini-файл на других ОС).
"""
from PySide6.QtCore import QSettings

ORG_NAME = "MyTools"
APP_NAME = "YouTubeDownloader"


class AppSettings:
    """Обёртка над QSettings для удобного доступа к настройкам приложения."""

    def __init__(self):
        self._settings = QSettings(ORG_NAME, APP_NAME)

    @property
    def save_folder(self) -> str:
        return self._settings.value("save_folder", "", type=str)

    @save_folder.setter
    def save_folder(self, value: str):
        self._settings.setValue("save_folder", value)

    @property
    def theme(self) -> str:
        return self._settings.value("theme", "light", type=str)

    @theme.setter
    def theme(self, value: str):
        self._settings.setValue("theme", value)

    @property
    def last_format(self) -> str:
        return self._settings.value("last_format", "mp4", type=str)

    @last_format.setter
    def last_format(self, value: str):
        self._settings.setValue("last_format", value)

    def sync(self):
        self._settings.sync()
