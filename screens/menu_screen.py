from kivy.uix.screenmanager import Screen
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.image import Image
from kivy.uix.label import Label
from kivy.clock import Clock
from components.control_panel import ControlPanel
from components.icon_button import IconButton
from sound_manager import SoundManager

import sys
import os

# Добавляем корневую папку в путь
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from animated_background import AnimatedBackground


class MainMenuScreen(Screen):
    """Главное меню с кнопками"""

    def __init__(self, **kwargs):
        # Извлекаем screen_params из kwargs
        self.screen_params = kwargs.pop('screen_params', None)
        super().__init__(**kwargs)

        self.sound_manager = SoundManager()

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
            text='TEST YOUR LUCK',
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
        # Проверяем, не выключен ли звук
        if not self.sound_manager.is_muted():
            self.sound_manager.play()
        else:
            print(f"🔇 [MainMenuScreen] Звук выключен, не запускаем")

    def test_vibration(self):
        """Тестовая вибрация - для вашей версии Android"""
        print("🔨 [MainMenuScreen] Тестовая вибрация")

        from kivy.utils import platform
        if platform != 'android':
            print("📱 Не Android")
            return

        try:
            from jnius import autoclass
            PythonActivity = autoclass('org.kivy.android.PythonActivity')
            activity = PythonActivity.mActivity

            # Получаем vibrator сервис
            vibrator = activity.getSystemService('vibrator')

            if vibrator:
                print("✅ Vibrator получен")

                # Используем VibrationEffect (Android 8+)
                try:
                    VibrationEffect = autoclass('android.os.VibrationEffect')
                    # createOneShot(длительность_мс, амплитуда)
                    effect = VibrationEffect.createOneShot(200, 255)
                    vibrator.vibrate(effect)
                    print("✅ Вибрация 200ms через VibrationEffect")
                    return
                except Exception as e:
                    print(f"⚠️ VibrationEffect не сработал: {e}")

                # Если не сработало, пробуем старый метод
                try:
                    vibrator.vibrate(200)
                    print("✅ Вибрация 200ms через vibrate()")
                    return
                except Exception as e:
                    print(f"⚠️ vibrate() не сработал: {e}")
            else:
                print("❌ Vibrator не найден")

        except Exception as e:
            print(f"❌ Ошибка: {e}")

    def on_leave(self, *args):
        """Вызывается при уходе с экрана"""

    def create_buttons(self, layout):
        """Создает кнопки видов спорта"""
        sports = [
            ('MagicBall', 'assets/images/buttons/Football_ball_button.png', 'magic_ball', self.change_to_game),
            ('Dice', 'assets/images/buttons/Dice_button.png', 'dice', self.change_to_game),
            ('Roulette', 'assets/images/buttons/Blue_roulette_button.png', 'intermediate_roulette',
             self.change_to_intermediate_roulette),
            ('RandNum', 'assets/images/buttons/Green_random_button.png', 'random', self.change_to_game),
            ('Coin', 'assets/images/buttons/Grey_cent_button.png', 'coin', self.change_to_game),
            ('Quiz', 'assets/images/buttons/Green_quiz_button.png', 'quiz', self.change_to_game),
            ('RSP', 'assets/images/buttons/rsp_button.png', 'rsp', self.change_to_game),
            ('Team Draw', 'assets/images/buttons/team_draw_button.png', 'team_draw', self.change_to_game),  # Новая кнопка
        ]

        # Сетка 4x2
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
        """Переход к игровому экрану с пересозданием"""
        print(f"🎮 Переход на {instance.sport}")

        from main import switch_screen

        # Переключаем экран (он создастся заново)
        switch_screen(instance.sport)

        # Вызываем start_game после создания экрана
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
        """Переход к промежуточному экрану рулетки с пересозданием"""
        print(f"🎲 Переход на промежуточный экран рулетки")

        from main import switch_screen

        # Переключаем экран (он создастся заново)
        switch_screen('intermediate_roulette')