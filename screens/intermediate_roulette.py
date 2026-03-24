# screens/intermediate_roulette.py
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.label import Label
from kivy.uix.image import Image
from kivy.animation import Animation
from kivy.clock import Clock
from kivy.core.audio import SoundLoader
from kivy.uix.behaviors import ButtonBehavior
from kivy.uix.button import Button
from animated_background import AnimatedBackground
from components.icon_button import IconButton
from screens.intermediate_base_screen import IntermediateScreen
import os


class IntermediateRoulette(IntermediateScreen):
    """Промежуточный экран для выбора типа рулетки"""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        # Удаляем стандартную кнопку из родителя
        if hasattr(self, 'back_button') and self.back_button:
            self.layout.remove_widget(self.back_button)
            self.back_button = None

        # Анимированный фон
        self.background = AnimatedBackground()
        self.layout.add_widget(self.background)

        # Статический фон (полупрозрачный)
        bg = Image(
            source='assets/backgrounds/indigo_bg.png',
            allow_stretch=True,
            keep_ratio=True,
            size_hint=(1, 1),
            fit_mode='fill',
            opacity=0.7
        )
        self.layout.add_widget(bg)

        # Заголовок
        title = Label(
            text='SELECT ROULETTE TYPE',
            font_name='assets/fonts/JockeyOne-Regular.ttf',
            font_size='32sp',
            bold=True,
            color=(1, 1, 1, 1),
            outline_color=(0, 0, 0, 1),
            outline_width=2,
            size_hint=(None, None),
            size=(500, 50),
            pos_hint={'center_x': 0.5, 'top': 0.95}
        )
        self.layout.add_widget(title)

        # Загружаем звук для кнопки назад
        self.load_back_sound()

        # Создаем кнопки выбора рулетки
        self.create_buttons()

        # Создаем кнопку назад с картинкой
        self.create_back_button()

    def load_back_sound(self):
        """Загружает звук для кнопки назад"""
        sound_path = 'assets/sounds/Schpun.ogg'

        if os.path.exists(sound_path):
            self.back_sound = SoundLoader.load(sound_path)
            if self.back_sound:
                self.back_sound.volume = 0.8
                print(f"✅ Loaded back button sound: {sound_path}")
            else:
                print(f"⚠️ Failed to load back button sound: {sound_path}")
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

    def create_buttons(self):
        """Создает кнопки выбора типа рулетки"""
        sports = [
            ('Classic Roulette', 'assets/images/buttons/Blue_roulette_button.png', 'roulette', self.change_to_game),
            ('Russian Roulette', 'assets/images/buttons/Red_rus_roulette_button.png', 'rus_roulette',
             self.change_to_game),
        ]

        # Располагаем кнопки по центру
        button_width, button_height = 0.3, 0.2
        start_x = 0.35
        start_y = 0.6
        vertical_spacing = 0.05

        for i, (text, icon_path, screen_name, callback) in enumerate(sports):
            y_pos = start_y - i * (button_height + vertical_spacing)

            btn = IconButton(
                text=text,
                icon_path=icon_path,
                sport=screen_name,
                size_hint=(button_width, button_height),
                pos_hint={'x': start_x, 'y': y_pos},
                callback=callback
            )

            self.layout.add_widget(btn)

    def create_back_button(self):
        """Создает кнопку назад с картинкой"""

        class BackImageButton(ButtonBehavior, Image):
            pass

        back_btn = BackImageButton(
            source='assets/images/buttons/Orange_back_to_menu_button.png',
            size_hint=(None, None),
            size=(60, 60),
            pos_hint={'x': 0.09, 'y': 0.055},
            allow_stretch=True
        )

        def on_press(instance):
            Animation(opacity=0.7, duration=0.1).start(instance)

        def on_release(instance):
            Animation(opacity=1.0, duration=0.1).start(instance)
            Clock.schedule_once(lambda dt: self.go_to_menu(), 0.1)

        back_btn.bind(on_press=on_press)
        back_btn.bind(on_release=on_release)

        self.layout.add_widget(back_btn)
        return back_btn

    def change_to_game(self, instance):
        """Переход к игровому экрану"""
        print(f"🎲 Переход на {instance.sport}")

        # Запускаем игру
        if hasattr(self.manager.get_screen(instance.sport), 'start_game'):
            self.manager.get_screen(instance.sport).start_game()

        # Переходим на экран игры
        self.manager.current = instance.sport

    def go_to_menu(self):
        """Переход в меню с воспроизведением звука"""
        self.play_back_sound()
        self.manager.current = 'menu'