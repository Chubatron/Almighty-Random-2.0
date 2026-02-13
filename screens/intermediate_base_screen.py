# screens/intermediate_base_screen.py
from kivy.uix.screenmanager import Screen
from kivy.uix.floatlayout import FloatLayout
from kivy.properties import StringProperty
from kivy.clock import Clock
from kivy.animation import Animation
from kivy.uix.behaviors import ButtonBehavior
from kivy.uix.image import Image as KivyImage
from sound_manager import SoundManager


class IntermediateScreen(Screen):
    """Базовый класс для промежуточных экранов (меню выбора)"""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.layout = FloatLayout()
        self.sound_manager = SoundManager()
        self.add_widget(self.layout)

    def on_enter(self):
        """При входе на промежуточный экран - возвращаем громкость"""
        self.sound_manager.fade_to(1.0, duration=0.5)

    def on_leave(self):
        """При выходе с промежуточного экрана"""
        pass

    def go_to_menu(self, instance=None):
        """Возврат в главное меню"""
        self.manager.current = 'menu'

    def go_to_game(self, game_name):
        """Переход к игре - будет убавлять громкость при входе в игру"""
        self.manager.current = game_name
        # Громкость убавится в BaseGameScreen.on_enter()