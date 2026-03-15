from kivy.uix.screenmanager import Screen
from kivy.uix.floatlayout import FloatLayout
from kivy.properties import StringProperty
from kivy.clock import Clock
from kivy.animation import Animation
from kivy.uix.behaviors import ButtonBehavior
from kivy.uix.image import Image as KivyImage
from kivy.graphics import Rotate, PushMatrix, PopMatrix
from sound_manager import SoundManager  # Импортируем SoundManager
import os


class BaseGameScreen(Screen):
    """Базовый класс ТОЛЬКО с музыкой и кнопкой назад"""

    background_image = StringProperty('')
    sound_file = StringProperty('')

    # Флаг для определения, является ли экран игровым (нужно для регулировки громкости)
    is_game_screen = True  # По умолчанию True для игровых экранов

    # Флаг для специальной настройки кнопки назад (для CoinScreen)
    custom_back_button = False  # По умолчанию False для всех экранов

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.layout = FloatLayout()

        # Музыка/звук
        self.sound = None

        # Звук для кнопки назад
        self.back_sound = None

        # Фон
        self.bg_image = None

        # Кнопка назад
        self.back_button = None

        # Ссылка на глобальный SoundManager
        self.sound_manager = SoundManager()

        self.add_widget(self.layout)
        self.bind(size=self._on_size_change)

        # Загружаем звук для кнопки назад
        self.load_back_sound()

    def load_back_sound(self):
        """Загружает звук для кнопки назад"""
        from kivy.core.audio import SoundLoader

        sound_path = 'assets/sounds/Schpun.ogg'

        if os.path.exists(sound_path):
            self.back_sound = SoundLoader.load(sound_path)
            if self.back_sound:
                self.back_sound.volume = 0.8  # Громкость для звука кнопки
                print(f"✅ Loaded back button sound: {sound_path}")
            else:
                print(f"⚠️ Failed to load back button sound: {sound_path}")
        else:
            print(f"⚠️ Back button sound file not found: {sound_path}")

    def play_back_sound(self):
        """Воспроизводит звук при нажатии на кнопку назад"""
        if self.back_sound:
            try:
                self.back_sound.play()
                print("🔊 Playing back button sound")
            except:
                pass  # Игнорируем ошибки при воспроизведении

    def _on_size_change(self, instance, value):
        """Обновление позиций при изменении размера"""
        pass

    def on_enter(self):
        """При входе на экран"""
        self.setup_background()
        self.setup_sound()
        self.create_back_button()  # Создает кнопку с учетом флага custom_back_button

        # Если это игровой экран, плавно убавляем фоновую музыку
        if self.is_game_screen:
            self.sound_manager.fade_to(0.05, duration=1.0)  # Убавляем до 5% за 1 секунду

    def on_leave(self):
        """При выходе с экрана"""
        self.stop_sound()

        # Если это игровой экран, возвращаем громкость при выходе
        if self.is_game_screen:
            self.sound_manager.fade_to(1.0, duration=1.0)  # Возвращаем до 100% за 1 секунду

    def go_to_menu(self):
        """Возврат в меню"""
        # Воспроизводим звук кнопки назад
        self.play_back_sound()

        self.stop_sound()
        # Возвращаем громкость перед переходом в меню
        self.sound_manager.fade_to(1.0, duration=0.5)
        self.manager.current = 'menu'

    def setup_background(self):
        """Настраивает фон"""
        if self.bg_image:
            self.layout.remove_widget(self.bg_image)

        from kivy.uix.image import Image
        self.bg_image = Image(
            source=self.background_image,
            allow_stretch=True,
            keep_ratio=False
        )
        self.layout.add_widget(self.bg_image)

    def setup_sound(self):
        """Настройка музыки/звуков"""
        if self.sound_file:
            from kivy.core.audio import SoundLoader
            self.sound = SoundLoader.load(self.sound_file)
            if self.sound:
                self.sound.loop = True
                self.sound.volume = 0.5
                self.sound.play()

    def stop_sound(self):
        """Остановка музыки"""
        if self.sound:
            self.sound.stop()
            self.sound = None

    def create_back_button(self):
        """Создает кнопку возврата в меню с учетом флага custom_back_button"""
        if self.custom_back_button:
            # Для CoinScreen - специальная кнопка
            self._create_custom_back_button()
        else:
            # Для всех остальных экранов - обычная кнопка
            self._create_standard_back_button()

    def _create_standard_back_button(self):
        """Создает стандартную кнопку возврата в меню (оригинальная позиция)"""

        class ImageButton(ButtonBehavior, KivyImage):
            pass

        back_btn = ImageButton(
            source='assets/images/buttons/Orange_back_to_menu_button.png',
            size_hint=(None, None),
            size=(60, 60),
            pos_hint={'x': 0.09, 'y': 0.055},  # Оригинальная позиция
            allow_stretch=True
        )

        # Анимация при нажатии
        def on_press(instance):
            Animation(opacity=0.7, duration=0.1).start(instance)

        def on_release(instance):
            Animation(opacity=1.0, duration=0.1).start(instance)
            Clock.schedule_once(lambda dt: self.go_to_menu(), 0.1)
        back_btn.bind(on_press=on_press)
        back_btn.bind(on_release=on_release)

        self.back_button = back_btn
        self.layout.add_widget(back_btn)

    def _create_custom_back_button(self):
        """Создает кастомную кнопку возврата в меню (левый верхний угол, повернутая на 90°)"""

        class ImageButton(ButtonBehavior, KivyImage):
            pass

        back_btn = ImageButton(
            source='assets/images/buttons/bronze_button.png',
            size_hint=(None, None),
            size=(60, 60),
            pos_hint={'x': 0.02, 'y': 0.88},  # Левый верхний угол
            allow_stretch=True
        )

        # Поворачиваем кнопку на 90 градусов
        def apply_rotation(btn):
            """Применяет поворот к кнопке"""
            btn.canvas.before.clear()
            btn.canvas.after.clear()
            with btn.canvas.before:
                PushMatrix()
                Rotate(angle=90, origin=(btn.width / 2, btn.height / 2))
            with btn.canvas.after:
                PopMatrix()

        # Применяем поворот сразу
        apply_rotation(back_btn)

        # Обновляем поворот при изменении размера
        back_btn.bind(size=lambda instance, value: apply_rotation(instance))

        # Анимация при нажатии
        def on_press(instance):
            Animation(opacity=0.7, duration=0.1).start(instance)

        def on_release(instance):
            Animation(opacity=1.0, duration=0.1).start(instance)
            # Воспроизводим звук перед переходом
            self.play_back_sound()
            Clock.schedule_once(lambda dt: self.go_to_menu(), 0.1)

        back_btn.bind(on_press=on_press)
        back_btn.bind(on_release=on_release)

        self.back_button = back_btn
        self.layout.add_widget(back_btn)

    def start_game(self):
        """Метод для запуска игры (может быть переопределен в дочерних классах)"""
        pass