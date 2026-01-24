import os
from kivy.core.audio import SoundLoader
from kivy.clock import Clock


class SoundManager:
    """Глобальный менеджер звука для всего приложения"""
    _instance = None
    _sound = None
    _current_volume = 1.0
    _is_muted = False

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        # Инициализация только один раз
        if not hasattr(self, '_initialized'):
            self._initialized = True

    def initialize(self, sound_file="assets/sounds/background.wav"):
        """Инициализация звука при старте приложения"""
        if self._sound:
            return  # Уже инициализирован

        if os.path.exists(sound_file):
            self._sound = SoundLoader.load(sound_file)
            if self._sound:
                self._sound.volume = self._current_volume
                self._sound.loop = True  # Зациклить
                print(f"Фоновая музыка загружена: {sound_file}")
            else:
                print(f"Не удалось загрузить звук: {sound_file}")
        else:
            print(f"Файл не найден: {sound_file}")

    def play(self):
        """Начать воспроизведение"""
        if self._sound and not self._is_muted:
            if self._sound.state != 'play':
                self._sound.play()

    def pause(self):
        """Пауза"""
        if self._sound and self._sound.state == 'play':
            self._sound.stop()  # или .pause() если поддерживается

    def resume(self):
        """Продолжить"""
        self.play()

    def stop(self):
        """Остановить"""
        if self._sound:
            self._sound.stop()


    def get_volume(self):
        """Получить текущую громкость"""
        return self._current_volume


    def set_volume(self, volume):
        """Установить громкость (0.0 - 1.0)"""
        self._current_volume = max(0.0, min(1.0, volume))
        if self._sound:
            self._sound.volume = self._current_volume

    def mute(self):
        """Выключить звук"""
        self._is_muted = True
        if self._sound and self._sound.state == 'play':
            self._sound.volume = 0.0

    def unmute(self):
        """Включить звук"""
        self._is_muted = False
        if self._sound:
            self._sound.volume = self._current_volume

    def is_muted(self):
        """Проверка, выключен ли звук"""
        return self._is_muted

    @property
    def is_playing(self):
        return self._sound and self._sound.state == 'play'