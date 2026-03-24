from kivy.uix.screenmanager import Screen
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.button import Button
from kivy.uix.image import Image
from kivy.properties import StringProperty
from kivy.clock import Clock
from kivy.animation import Animation
from kivy.uix.behaviors import ButtonBehavior
from kivy.core.audio import SoundLoader
from sound_manager import SoundManager
import os


class IntermediateScreen(Screen):
    """Базовый класс для промежуточных экранов (меню выбора)"""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.layout = FloatLayout()
        self.sound_manager = SoundManager()

        # Создаем стандартную кнопку назад (как в BaseGameScreen)
        self.back_button = Button(
            text='← Назад',
            font_size='16sp',
            size_hint=(None, None),
            size=(100, 40),
            pos_hint={'x': 0.02, 'top': 0.98},  # ← Левый верхний угол
            background_color=(0.2, 0.2, 0.2, 0.9),
            color=(1, 1, 1, 1)
        )
        self.back_button.bind(on_press=self.go_to_menu)
        self.layout.add_widget(self.back_button)

        # Загружаем звук для кнопки
        self.load_back_sound()

        self.add_widget(self.layout)

    def load_back_sound(self):
        """Загружает звук для кнопки назад"""
        sound_path = 'assets/sounds/Schpun.ogg'
        if os.path.exists(sound_path):
            self.back_sound = SoundLoader.load(sound_path)
            if self.back_sound:
                self.back_sound.volume = 0.8
                print(f"✅ Loaded back button sound: {sound_path}")
        else:
            print(f"⚠️ Back button sound file not found: {sound_path}")

    def play_back_sound(self):
        """Воспроизводит звук при нажатии на кнопку назад"""
        if hasattr(self, 'back_sound') and self.back_sound:
            try:
                self.back_sound.play()
                print("🔊 Playing back button sound")
            except:
                pass

    def on_enter(self):
        """При входе на промежуточный экран - возвращаем громкость"""
        self.sound_manager.fade_to(1.0, duration=0.5)

    def on_leave(self):
        """При выходе с промежуточного экрана"""
        pass

    def go_to_menu(self, instance=None):
        """Возврат в главное меню с звуком"""
        self.play_back_sound()
        Clock.schedule_once(lambda dt: self._go_to_menu(), 0.1)

    def _go_to_menu(self):
        """Реальный переход в меню"""
        self.manager.current = 'menu'

    def go_to_game(self, game_name):
        """Переход к игре - будет убавлять громкость при входе в игру"""
        self.manager.current = game_name