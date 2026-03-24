from kivy.uix.screenmanager import Screen
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.image import Image
from kivy.uix.label import Label
from animated_background import AnimatedBackground
from components.control_panel import ControlPanel
from components.icon_button import IconButton
from sound_manager import SoundManager


class MainMenuScreen(Screen):
    """Главное меню с кнопками"""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        layout = FloatLayout()

        # Анимированный фон
        self.background = AnimatedBackground()
        layout.add_widget(self.background)

        # Статический фон (полупрозрачный)
        bg = Image(
            source='assets/backgrounds/indigo_bg.png',
            allow_stretch=True,
            keep_ratio=True,
            size_hint=(1, 1),
            fit_mode='fill',
            opacity=0.7
        )
        layout.add_widget(bg)

        # Заголовок
        title = Label(
            text='SELECT AN ITEM',
            font_name='assets/fonts/JockeyOne-Regular.ttf',
            font_size='32sp',
            bold=True,
            color=(1, 1, 1, 1),
            outline_color=(0, 0, 0, 1),
            outline_width=2,
            size_hint=(None, None),
            size=(400, 50),
            pos_hint={'center_x': 0.5, 'top': 0.95}
        )
        layout.add_widget(title)

        # Создаем кнопки
        self.create_buttons(layout)

        # Панель управления
        self.control_panel = ControlPanel()
        layout.add_widget(self.control_panel)

        self.add_widget(layout)

    def on_pre_enter(self, *args):
        """Вызывается перед показом экрана"""
        SoundManager().play()  # Музыка играет

    def on_leave(self, *args):
        """Вызывается при уходе с экрана - НЕ ОСТАНАВЛИВАЕМ музыку"""
        pass

    def create_buttons(self, layout):
        """Создает кнопки видов спорта"""
        sports = [
            ('MagicBall', 'assets/images/buttons/Football_ball_button.png', 'magic_ball', self.change_to_game),
            ('Dice', 'assets/images/buttons/Dice_button.png', 'dice', self.change_to_game),
            ('Roulette', 'assets/images/buttons/Blue_roulette_button.png', 'intermediate_roulette', self.change_to_intermediate_roulette),  # ← Изменено
            ('Random', 'assets/images/buttons/Green_random_button.png', 'random', self.change_to_game),
            ('Coin', 'assets/images/buttons/Grey_cent_button.png', 'coin', self.change_to_game),
            ('Quiz', 'assets/images/buttons/Green_quiz_button.png', 'quiz', self.change_to_game),
            ('RSP', 'assets/images/buttons/rsp_button.png', 'rsp', self.change_to_game),
        ]

        # Сетка 4x2 (8 позиций, 7 кнопок + 1 пустая)
        rows, cols = 4, 2
        button_width, button_height = 0.4, 0.12
        horizontal_spacing, vertical_spacing = 0.1, 0.03
        start_x, start_y = 0.05, 0.7

        for i, (text, icon_path, screen_name, callback) in enumerate(sports):
            row, col = i // cols, i % cols
            x_pos = start_x + col * (button_width + horizontal_spacing)
            y_pos = start_y - row * (button_height + vertical_spacing)

            btn = IconButton(
                text=text,
                icon_path=icon_path,
                sport=screen_name,
                size_hint=(button_width, button_height),
                pos_hint={'x': x_pos, 'y': y_pos},
                callback=callback
            )
            layout.add_widget(btn)

    def change_to_game(self, instance):
        """Переход к игровому экрану"""
        # Проверяем, существует ли метод start_game у экрана
        if hasattr(self.manager.get_screen(instance.sport), 'start_game'):
            self.manager.get_screen(instance.sport).start_game()
        self.manager.current = instance.sport

    def change_to_intermediate_roulette(self, instance):
        """Переход к промежуточному экрану рулетки"""
        print("🎲 Переход на промежуточный экран рулетки")
        self.manager.current = 'intermediate_roulette'