from kivy.uix.screenmanager import Screen
from kivy.uix.floatlayout import FloatLayout
from kivy.properties import StringProperty
from kivy.clock import Clock
from kivy.animation import Animation
from kivy.uix.behaviors import ButtonBehavior
from kivy.uix.image import Image as KivyImage
from sound_manager import SoundManager  # Импортируем SoundManager


class BaseGameScreen(Screen):
    """Базовый класс ТОЛЬКО с музыкой и кнопкой назад"""

    background_image = StringProperty('')
    sound_file = StringProperty('')

    # Флаг для определения, является ли экран игровым (нужно для регулировки громкости)
    is_game_screen = True  # По умолчанию True для игровых экранов

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.layout = FloatLayout()

        # Музыка/звук
        self.sound = None

        # Фон
        self.bg_image = None

        # Кнопка назад
        self.back_button = None

        # Ссылка на глобальный SoundManager
        self.sound_manager = SoundManager()

        self.add_widget(self.layout)
        self.bind(size=self._on_size_change)

    def _on_size_change(self, instance, value):
        """Обновление позиций при изменении размера"""
        pass

    def on_enter(self):
        """При входе на экран"""
        self.setup_background()
        self.setup_sound()
        self.create_back_button()

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
        """Создает кнопку возврата в меню с картинкой"""

        class ImageButton(ButtonBehavior, KivyImage):
            pass

        back_btn = ImageButton(
            source='assets/images/buttons/Orange_back_to_menu_button.png',
            size_hint=(None, None),
            size=(60, 60),
            pos_hint={'x': 0.09, 'y': 0.055},
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

    def start_game(self):
        pass