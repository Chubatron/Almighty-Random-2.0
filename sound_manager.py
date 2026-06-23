import os
from kivy.core.audio import SoundLoader
from kivy.clock import Clock
from kivy.utils import platform


class SoundManager:
    """Глобальный менеджер звука и вибрации для всего приложения"""
    _instance = None
    _sound = None
    _current_volume = 0.5
    _is_muted = False
    _target_volume = 0.5
    _fade_clock = None
    _is_vibration_enabled = True  # Флаг для вибрации

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        # Инициализация только один раз
        if not hasattr(self, '_initialized'):
            self._initialized = True
            self._vibrator = None
            self._init_vibrator()
            print("🔊 [SoundManager] Инициализация")

    def _init_vibrator(self):
        """Инициализация вибратора для Android"""
        if platform == 'android':
            try:
                from jnius import autoclass
                PythonActivity = autoclass('org.kivy.android.PythonActivity')
                activity = PythonActivity.mActivity
                self._vibrator = activity.getSystemService('vibrator')
                if self._vibrator is not None:
                    print("✅ [SoundManager] Вибратор инициализирован")
                else:
                    print("⚠️ [SoundManager] Вибратор не доступен")
            except Exception as e:
                print(f"⚠️ [SoundManager] Ошибка инициализации вибратора: {e}")
                self._vibrator = None
        else:
            print("📱 [SoundManager] Вибрация доступна только на Android")

    def initialize(self, sound_file="assets/sounds/background.wav"):
        """Инициализация звука при старте приложения"""
        if self._sound:
            print("🔊 [SoundManager] Звук уже инициализирован")
            return

        if os.path.exists(sound_file):
            self._sound = SoundLoader.load(sound_file)
            if self._sound:
                self._sound.volume = self._current_volume
                self._sound.loop = True
                print(f"🔊 [SoundManager] Фоновая музыка загружена: {sound_file}")
            else:
                print(f"❌ [SoundManager] Не удалось загрузить звук: {sound_file}")
        else:
            print(f"❌ [SoundManager] Файл не найден: {sound_file}")

    def play(self):
        """Начать воспроизведение"""
        print(f"🔊 [SoundManager] play() - is_muted={self._is_muted}, sound_exists={self._sound is not None}")
        if self._sound and not self._is_muted:
            if self._sound.state != 'play':
                self._sound.play()
                print("🔊 [SoundManager] Воспроизведение запущено")
            else:
                print("🔊 [SoundManager] Звук уже играет")
        else:
            print(f"🔊 [SoundManager] Не могу запустить: is_muted={self._is_muted}, sound_exists={self._sound is not None}")

    def pause(self):
        """Пауза"""
        if self._sound and self._sound.state == 'play':
            self._sound.stop()
            print("🔊 [SoundManager] Воспроизведение остановлено")

    def resume(self):
        """Продолжить"""
        print("🔊 [SoundManager] resume()")
        self.play()

    def stop(self):
        """Остановить"""
        if self._sound:
            self._sound.stop()
            if self._fade_clock:
                self._fade_clock.cancel()
                self._fade_clock = None
            print("🔊 [SoundManager] Звук остановлен")

    def get_volume(self):
        """Получить текущую громкость"""
        return self._current_volume

    def set_volume(self, volume):
        """Установить громкость (0.0 - 1.0)"""
        self._current_volume = max(0.0, min(0.5, volume))
        if self._sound and not self._is_muted:
            self._sound.volume = self._current_volume
        print(f"🔊 [SoundManager] Установлена громкость: {self._current_volume}, is_muted={self._is_muted}")

    def mute(self):
        """Выключить звук и вибрацию"""
        self._is_muted = True
        self._is_vibration_enabled = False
        if self._sound:
            self._sound.volume = 0.0
            if self._sound.state == 'play':
                self._sound.stop()
                print("🔊 [SoundManager] Воспроизведение остановлено при mute")
        print(f"🔊 [SoundManager] Звук и вибрация ВЫКЛЮЧЕНЫ (mute), is_muted={self._is_muted}, vibration={self._is_vibration_enabled}")

    def unmute(self):
        """Включить звук и вибрацию"""
        self._is_muted = False
        self._is_vibration_enabled = True
        if self._sound:
            self._sound.volume = self._current_volume
            if self._sound.state != 'play':
                self._sound.play()
                print("🔊 [SoundManager] Воспроизведение запущено при unmute")
            else:
                print("🔊 [SoundManager] Звук уже играет")
        print(f"🔊 [SoundManager] Звук и вибрация ВКЛЮЧЕНЫ (unmute), громкость={self._current_volume}, is_muted={self._is_muted}, vibration={self._is_vibration_enabled}")

    def is_muted(self):
        """Проверка, выключен ли звук"""
        return self._is_muted

    @property
    def is_playing(self):
        return self._sound and self._sound.state == 'play'

    def fade_to(self, target_volume, duration=1.0, callback=None):
        """Плавно изменяет громкость до target_volume за duration секунд."""
        self._target_volume = target_volume
        print(f"🔊 [SoundManager] fade_to({target_volume}, {duration}) - is_muted={self._is_muted}")

        if self._is_muted:
            print(f"🔊 [SoundManager] fade_to пропущен - звук выключен")
            if callback:
                callback()
            return

        if not self._sound:
            print(f"🔊 [SoundManager] fade_to пропущен - звук не загружен")
            if callback:
                callback()
            return

        if self._fade_clock:
            self._fade_clock.cancel()
            self._fade_clock = None

        start_volume = self._sound.volume
        step_count = int(duration * 20)
        step_duration = duration / step_count if step_count > 0 else 0
        volume_step = (target_volume - start_volume) / step_count if step_count > 0 else 0

        print(f"🔊 [SoundManager] fade_to: start={start_volume:.3f}, target={target_volume:.3f}, steps={step_count}")

        def update_volume(step):
            if step <= step_count and self._sound and not self._is_muted:
                new_volume = start_volume + volume_step * step
                self._sound.volume = max(0.0, min(0.5, new_volume))
                self._fade_clock = Clock.schedule_once(lambda dt: update_volume(step + 1), step_duration)
            else:
                if self._sound and not self._is_muted:
                    self._sound.volume = target_volume
                self._fade_clock = None
                print(f"🔊 [SoundManager] fade_to завершен, финальная громкость={self._sound.volume if self._sound else 'None'}")
                if callback:
                    callback()

        update_volume(1)

    def get_current_volume(self):
        """Возвращает текущую громкость (целевую, не реальную)"""
        return self._target_volume if hasattr(self, '_target_volume') else self._current_volume

    # ==================== МЕТОДЫ ВИБРАЦИИ ====================

    def set_vibration_enabled(self, enabled):
        """Включить/выключить вибрацию"""
        self._is_vibration_enabled = enabled
        print(f"📳 [SoundManager] Вибрация {'ВКЛЮЧЕНА' if enabled else 'ВЫКЛЮЧЕНА'}")

    def is_vibration_enabled(self):
        """Проверка, включена ли вибрация"""
        return self._is_vibration_enabled

    def vibrate(self, duration=0.05):
        """Воспроизводит вибрацию на Android"""
        if self._is_muted or not self._is_vibration_enabled:
            return
        if platform == 'android' and self._vibrator is not None:
            try:
                self._vibrator.vibrate(int(duration * 1000))
                print(f"📳 [SoundManager] Вибрация {duration}с")
            except Exception as e:
                print(f"⚠️ [SoundManager] Ошибка вибрации: {e}")

    def vibrate_short(self):
        """Короткая вибрация (30 мс)"""
        self.vibrate(0.03)

    def vibrate_medium(self):
        """Средняя вибрация (60 мс)"""
        self.vibrate(0.06)

    def vibrate_long(self):
        """Длинная вибрация (120 мс)"""
        self.vibrate(0.12)

    def vibrate_pattern(self, pattern=None, repeat=-1):
        """Вибрация с паттерном"""
        if self._is_muted or not self._is_vibration_enabled:
            return
        if platform == 'android' and self._vibrator is not None:
            try:
                if pattern:
                    pattern_ms = [int(p * 1000) for p in pattern]
                    self._vibrator.vibrate(pattern_ms, repeat)
                    print(f"📳 [SoundManager] Вибрация с паттерном: {pattern}")
            except Exception as e:
                print(f"⚠️ [SoundManager] Ошибка вибрации с паттерном: {e}")

    # ==================== МЕТОДЫ ДЛЯ ИГРЫ ====================

    def vibrate_glass_raise(self):
        """Вибрация при поднятии стакана (короткая, однократная)"""
        if self._is_muted or not self._is_vibration_enabled:
            return
        # Однократная вибрация (repeat=0), а не бесконечная (repeat=-1)
        self.vibrate_pattern([0.03, 0.02, 0.03], 0)
        print("📳 [SoundManager] Вибрация при поднятии стакана")

    def vibrate_glass_lower(self):
        """Вибрация при опускании стакана"""
        if self._is_muted or not self._is_vibration_enabled:
            return
        self.vibrate_short()
        print("📳 [SoundManager] Вибрация при опускании стакана")

    def vibrate_full_charge(self):
        """Вибрация при достижении 100% заряда"""
        if self._is_muted or not self._is_vibration_enabled:
            return
        self.vibrate_pattern([0.05, 0.03, 0.08, 0.03, 0.1], 0)
        print("📳 [SoundManager] Вибрация при достижении 100% заряда")

    def vibrate_dice_switch(self):
        """Вибрация при анимации перехода кубиков (1<->2)"""
        if self._is_muted or not self._is_vibration_enabled:
            return
        self.vibrate_medium()
        print("📳 [SoundManager] Вибрация при переходе кубиков")

    def vibrate_dice_appear(self):
        """Вибрация при появлении кубиков"""
        if self._is_muted or not self._is_vibration_enabled:
            return
        self.vibrate_pattern([0.02, 0.02, 0.03], 0)
        print("📳 [SoundManager] Вибрация при появлении кубиков")

    def vibrate_dice_disappear(self):
        """Вибрация при исчезновении кубиков"""
        if self._is_muted or not self._is_vibration_enabled:
            return
        self.vibrate_short()
        print("📳 [SoundManager] Вибрация при исчезновении кубиков")

    def vibrate_dice_roll(self):
        """Вибрация при броске кубиков"""
        if self._is_muted or not self._is_vibration_enabled:
            return
        self.vibrate_pattern([0.02, 0.02, 0.02, 0.02, 0.02], 0)
        print("📳 [SoundManager] Вибрация при броске кубиков")

    def cancel_vibration(self):
        """Отменить текущую вибрацию"""
        if platform == 'android' and self._vibrator is not None:
            try:
                self._vibrator.cancel()
                print(f"📳 [SoundManager] Вибрация отменена")
            except Exception as e:
                print(f"⚠️ [SoundManager] Ошибка отмены вибрации: {e}")