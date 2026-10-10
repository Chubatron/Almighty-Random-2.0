from kivy.uix.screenmanager import Screen
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.image import Image
from kivy.uix.label import Label
from kivy.clock import Clock
from kivy.properties import StringProperty
from kivy.graphics import Color, Rectangle
from components.control_panel import ControlPanel
from components.icon_button import IconButton
from sound_manager import SoundManager
from lucky_token import LuckyToken
from components.token_widget import TokenWidget

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from animated_background import AnimatedBackground


class MainMenuScreen(Screen):
    """Главное меню с кнопками"""

    coin_text = StringProperty('0')

    def __init__(self, **kwargs):
        self.screen_params = kwargs.pop('screen_params', None)
        super().__init__(**kwargs)

        self.sound_manager = SoundManager()
        self.tokens = LuckyToken()

        layout = FloatLayout()

        # Анимированный фон
        self.background = AnimatedBackground()
        layout.add_widget(self.background)

        # Статический фон
        bg = Image(
            source='assets/backgrounds/indigo_bg.png',
            fit_mode='fill',
            size_hint=(1, 1),
            opacity=0.7
        )
        layout.add_widget(bg)

        # =====================================================================
        # ЗАГОЛОВОК — размер и позиция теперь в долях экрана
        # =====================================================================
        title = Label(
            text='TEST YOUR LUCK',
            font_name='assets/fonts/JockeyOne-Regular.ttf',
            font_size='32sp',
            bold=True,
            color=(1, 1, 1, 1),
            outline_color=(0, 0, 0, 1),
            outline_width=2,
            size_hint=(0.70, 0.07),
            pos_hint={'center_x': 0.5, 'top': 0.93},
        )
        with title.canvas.before:
            Color(1, 0, 0, 0)
            title._red_bg = Rectangle(pos=title.pos, size=title.size)
        title.bind(
            pos=lambda *a: setattr(title._red_bg, 'pos', title.pos),
            size=lambda *a: setattr(title._red_bg, 'size', title.size),
        )
        layout.add_widget(title)

        # ==================== LUCKY_TOKEN: ВИДЖЕТ ====================
        # size_hint и pos_hint берутся из TokenWidget.DEFAULT_*
        self.token_widget = TokenWidget()
        self.token_widget.set_value(self.tokens.get_balance())
        self.token_widget.set_state(True)
        layout.add_widget(self.token_widget)

        self.tokens.bind(on_balance_changed=self._on_balance_changed)
        # ===========================================================

        # =====================================================================
        # КОНТЕЙНЕР С КНОПКАМИ (красная заливка) — в долях экрана.
        # Формула использует те же константы, что и create_buttons,
        # поэтому границы совпадают с кнопками.
        # =====================================================================
        bw, bh = 0.4, 0.12
        hs, vs = 0.1, 0.03
        sx, sy = 0.05, 0.7

        grid_w = 2 * bw + hs               # 0.9
        grid_h = 4 * bh + 3 * vs           # 0.57

        grid_y = sy - (grid_h - bh)        # 0.25

        games_bg = FloatLayout(
            size_hint=(grid_w, grid_h),
            pos_hint={'x': sx, 'y': grid_y},
        )
        with games_bg.canvas.before:
            Color(1, 0, 0, 0)
            games_bg._red_bg = Rectangle(pos=games_bg.pos, size=games_bg.size)
        games_bg.bind(
            pos=lambda *a: setattr(games_bg._red_bg, 'pos', games_bg.pos),
            size=lambda *a: setattr(games_bg._red_bg, 'size', games_bg.size),
        )
        layout.add_widget(games_bg)
        # =====================================================================

        # Создаем кнопки — НЕ ТРОГАЕМ
        self.create_buttons(layout)

        # Панель управления
        self.control_panel = ControlPanel()
        layout.add_widget(self.control_panel)

        self.add_widget(layout)

    def on_pre_enter(self, *args):
        self._refresh_balance()

        if not self.sound_manager.is_muted():
            self.sound_manager.play()
        else:
            print(f"🔇 [MainMenuScreen] Звук выключен, не запускаем")

    def _refresh_balance(self):
        if hasattr(self, 'token_widget') and self.token_widget:
            self.token_widget.set_value(self.tokens.get_balance())
            self.token_widget.set_state(self.tokens.get_balance() > 0)

    def _on_balance_changed(self, instance, new_balance):
        if hasattr(self, 'token_widget') and self.token_widget:
            self.token_widget.set_value(int(new_balance))
            self.token_widget.set_state(int(new_balance) > 0)

    def on_leave(self, *args):
        try:
            self.tokens.unbind(on_balance_changed=self._on_balance_changed)
        except Exception:
            pass

    # create_buttons НЕ ТРОГАЕМ — как было
    def create_buttons(self, layout):
        sports = [
            ('MagicBall', 'assets/images/buttons/Football_ball_button.png', 'magic_ball', self.change_to_game),
            ('Dice', 'assets/images/buttons/Dice_button.png', 'dice', self.change_to_game),
            ('Roulette', 'assets/images/buttons/Blue_roulette_button.png', 'intermediate_roulette',
             self.change_to_intermediate_roulette),
            ('RandNum', 'assets/images/buttons/Green_random_button.png', 'random', self.change_to_game),
            ('Heads or Tails?', 'assets/images/buttons/Grey_cent_button.png', 'coin', self.change_to_game),
            ('Quiz', 'assets/images/buttons/Green_quiz_button.png', 'quiz', self.change_to_game),
            ('Rock, Paper, Scissors', 'assets/images/buttons/rsp_button.png', 'rsp', self.change_to_game),
            ('Team Draw', 'assets/images/buttons/team_draw_button.png', 'team_draw', self.change_to_game),
        ]

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
                callback=callback,
                sound_manager=self.sound_manager
            )
            layout.add_widget(btn)

    def change_to_game(self, instance):
        print(f"🎮 Переход на {instance.sport}")
        from main import switch_screen
        switch_screen(instance.sport)

        def call_start_game(dt):
            try:
                screen = self.manager.get_screen(instance.sport)
                if hasattr(screen, 'start_game'):
                    screen.start_game()
                    print(f"✅ Вызван start_game для {instance.sport}")
            except Exception as e:
                print(f"⚠️ Ошибка вызова start_game для {instance.sport}: {e}")

        Clock.schedule_once(call_start_game, 0.2)

    def change_to_intermediate_roulette(self, instance):
        print(f"🎲 Переход на промежуточный экран рулетки")
        from main import switch_screen
        switch_screen('intermediate_roulette')