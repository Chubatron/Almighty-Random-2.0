from kivy.app import App
from kivy.uix.screenmanager import ScreenManager, Screen, FadeTransition
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.image import Image
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.core.audio import SoundLoader
from kivy.core.window import Window
from kivy.clock import Clock
from kivy.animation import Animation
from kivy.properties import StringProperty, NumericProperty
from kivy.vector import Vector
import os

# Устанавливаем размер окна (можно менять)
Window.size = (400, 700)
Window.clearcolor = (0.1, 0.1, 0.1, 1)

class BallPhysics:
    """Класс для физики мяча"""

    def __init__(self, pos, size, sound_callback=None):  # ← Добавить sound_callback как параметр
        self.pos = Vector(pos)
        self.velocity = Vector(0, 0)
        self.size = size
        self.radius = size / 2
        self.friction = 0.995  # Трение
        self.bounce_factor = 0.8  # Коэффициент отскока
        self.sound_callback = sound_callback  # ← Сохраняем коллбек
        self.can_play_sound = True  # Для предотвращения множественных срабатываний

    def update(self, dt, screen_width, screen_height):
        """Обновление физики мяча"""
        # Применяем трение
        self.velocity *= self.friction

        # Обновляем позицию
        new_pos = self.pos + self.velocity * dt * 60

        # Проверяем столкновение с границами
        self.check_boundaries(new_pos, screen_width, screen_height)

        # Обновляем позицию
        self.pos = new_pos

        # Если скорость очень мала - останавливаем
        if self.velocity.length() < 0.6:
            self.velocity = Vector(0, 0)
            self.can_play_sound = True  # Разрешаем звук снова, когда мяч остановился

    def check_boundaries(self, new_pos, screen_width, screen_height):
        """Проверка столкновений с границами"""
        bounce_occurred = False

        # Столкновение с правой границей
        if new_pos.x + self.radius > screen_width:
            self.velocity.x = -abs(self.velocity.x) * self.bounce_factor
            new_pos.x = screen_width - self.radius
            bounce_occurred = True

        # Столкновение с левой границей
        if new_pos.x - self.radius < 0:
            self.velocity.x = abs(self.velocity.x) * self.bounce_factor
            new_pos.x = self.radius
            bounce_occurred = True

        # Столкновение с верхней границей
        if new_pos.y + self.radius > screen_height:
            self.velocity.y = -abs(self.velocity.y) * self.bounce_factor
            new_pos.y = screen_height - self.radius
            bounce_occurred = True

        # Столкновение с нижней границей
        if new_pos.y - self.radius < 0:
            self.velocity.y = abs(self.velocity.y) * self.bounce_factor
            new_pos.y = self.radius
            bounce_occurred = True

        # Воспроизводим звук отскока, если скорость достаточно высокая
        if bounce_occurred:
            self.sound_callback()

    def apply_force(self, force_vector):
        """Применить силу к мячу"""
        self.velocity += force_vector
        self.can_play_sound = True  # Разрешаем звук при новом броске

    def set_velocity_from_swipe(self, start_pos, end_pos, multiplier=0.1):
        """Установить скорость на основе свайпа"""
        dx = end_pos[0] - start_pos[0]
        dy = end_pos[1] - start_pos[1]
        self.velocity = Vector(dx, dy) * multiplier


class ControlPanel(FloatLayout):
    """Панель служебных кнопок внизу экрана"""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.size_hint = (1, 0.15)
        self.pos_hint = {'x': 0, 'y': 0}

        # Фон панели
        bg = Image(
            source='',
            color=(0.1, 0.1, 0.1, 0.0),
            allow_stretch=True,
            keep_ratio=False,
            size_hint=(1, 1)
        )
        self.add_widget(bg)

        # Создаем служебные кнопки
        self.create_buttons()

    def create_buttons(self):
        """Создает кнопки на панели управления"""
        buttons = [
            ('SOUND ON', 'assets/icons/sound_on.png', self.toggle_sound, (0.2, 0.8, 0.2, 1)),
            ('SHARE', 'assets/icons/share.png', self.share_game, (0.1, 0.6, 0.9, 1)),
            ('RATE', 'assets/icons/star.png', self.rate_game, (1, 0.8, 0.1, 1)),
            ('EXIT', 'assets/icons/exit.png', self.exit_game, (0.8, 0.1, 0.1, 1)),

        ]

        # Распределяем кнопки равномерно по ширине
        for i, (text, icon, callback, color) in enumerate(buttons):
            btn = ControlButton(
                text=text,
                size_hint=(0.2, 0.8),
                pos_hint={'x': 0.05 + i * 0.23, 'y': 0.1},
                background_color=color,
                background_normal='',
                font_size='12sp'
            )
            btn.bind(on_press=callback)
            self.add_widget(btn)

    def toggle_sound(self, instance):
        """Включить/выключить звук"""
        app = App.get_running_app()
        if app.background_music:
            if app.background_music.volume > 0:
                app.background_music.volume = 0
                instance.text = 'SOUND OFF'
                instance.background_color = (0.5, 0.5, 0.5, 1)
            else:
                app.background_music.volume = 0.1
                instance.text = 'SOUND ON'
                instance.background_color = (0.2, 0.8, 0.2, 1)

    def share_game(self, instance):
        """Поделиться игрой"""
        print("Share feature would be implemented here")

    def rate_game(self, instance):
        """Поставить оценку"""
        print("Rate feature would be implemented here")

    def exit_game(self, instance):
        """Выход из приложения"""
        App.get_running_app().stop()


class ControlButton(Button):
    """Кастомная кнопка для панели управления"""
    pass


class MainMenuScreen(Screen):
    """Главное меню с фоном и кнопками"""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        layout = FloatLayout()

        # Фон меню
        bg = Image(
            source='assets/backgrounds/main_menu_bg.jpg',
            allow_stretch=True,
            keep_ratio=True,
            size_hint=(1, 1),
            fit_mode='fill'
        )
        layout.add_widget(bg)

        # Заголовок
        title = Label(
            text='SELECT  AN  ITEM',
            font_name='assets/fonts/JockeyOne-Regular.ttf',
            font_size='32sp',
            bold=True,
            color=(1, 1, 1, 1),
            outline_color=(0, 0, 0, 1),
            outline_width=2,
            size_hint=(None, None),
            size=(400, 50),
            pos_hint={'center_x': 0.5, 'top': 0.9}
        )
        layout.add_widget(title)

        # Кнопки выбора спорта
        sports = [
            ('FOOTBALL', 'football', (0.2, 0.8, 0.2, 1)),
            ('BASKETBALL', 'basketball', (0.9, 0.3, 0.2, 1)),
            ('BOWLING', 'bowling', (0.1, 0.5, 0.9, 1)),
            ('DICE', 'dice', (0.1, 0.1, 0.1, 1)),
        ]

        for i, (text, sport, color) in enumerate(sports):
            btn = SportButton(
                text=text,
                sport=sport,
                size_hint=(0.7, 0.12),
                pos_hint={'center_x': 0.5, 'center_y': 0.7 - i * 0.15},
                background_color=color,
                background_normal='',
                font_size='20sp',
                bold=True
            )
            btn.bind(on_press=self.change_to_game)
            layout.add_widget(btn)

        # Добавляем панель управления
        self.control_panel = ControlPanel()
        layout.add_widget(self.control_panel)

        self.add_widget(layout)

    def change_to_game(self, instance):
        """Переход к игровому экрану"""
        self.manager.current = instance.sport
        self.manager.get_screen(instance.sport).start_game()


class SportButton(Button):
    """Кастомная кнопка для выбора спорта"""
    sport = StringProperty('')


class GameScreen(Screen):
    """Базовый класс для игровых экранов"""
    ball_image = StringProperty('')
    background_image = StringProperty('')
    sound_file = StringProperty('')
    ball_size = NumericProperty(100)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.layout = FloatLayout()
        self.ball_widget = None
        self.ball_physics = None
        self.sound = None
        self.touch_start_pos = None
        self.is_physics_enabled = False
        self.bg_image = None
        self.physics_clock = None
        self.add_widget(self.layout)

    def on_enter(self):
        """При входе на экран"""
        # Загружаем звук при входе на экран
        self.load_sound()
        self.setup_background()
        self.setup_ui()
        self.start_physics_update()

    def load_sound(self):
        """Загружает звук"""
        if self.sound_file and os.path.exists(self.sound_file):
            self.sound = SoundLoader.load(self.sound_file)
            if self.sound:
                print(f"Звук загружен для {self.name}: {self.sound_file}")
                self.sound.volume = 1.0
            else:
                print(f"Не удалось загрузить звук: {self.sound_file}")
                self.sound = None
        else:
            print(f"Файл не найден: {self.sound_file}")
            self.sound = None

    def start_physics_update(self):
        """Запускаем обновление физики"""
        if self.physics_clock:
            self.physics_clock.cancel()
        self.physics_clock = Clock.schedule_interval(self.update_physics, 1 / 60.0)

    def update_physics(self, dt):
        """Обновление физики мяча"""
        if self.ball_physics and self.is_physics_enabled:
            # Обновляем физику
            self.ball_physics.update(dt, self.layout.width, self.layout.height)

            # Обновляем позицию виджета мяча
            if self.ball_widget:
                if self.ball_widget.pos_hint:
                    self.ball_widget.pos_hint = {}
                self.ball_widget.pos = (
                    self.ball_physics.pos.x - self.ball_physics.radius,
                    self.ball_physics.pos.y - self.ball_physics.radius
                )

            # Если мяч остановился, выключаем физику
            if self.ball_physics.velocity.length() < 0.5:
                self.is_physics_enabled = False

    def setup_background(self):
        """Устанавливаем фон"""
        if self.bg_image:
            self.layout.remove_widget(self.bg_image)

        self.bg_image = Image(
            source=self.background_image,
            allow_stretch=True,
            keep_ratio=False
        )
        self.layout.add_widget(self.bg_image)

    def setup_ui(self):
        """Настраиваем интерфейс"""
        # Очищаем старые виджеты (кроме фона)
        for child in self.layout.children[:]:
            if child not in [self.bg_image, self.ball_widget]:
                self.layout.remove_widget(child)

        self.create_ball()

        # Кнопка назад
        back_btn = Button(
            text='← MENU',
            size_hint=(0.25, 0.08),
            pos_hint={'x': 0.02, 'y': 0.02},
            background_color=(1, 0.3, 0.3, 1),
            background_normal=''
        )
        back_btn.bind(on_press=self.go_to_menu)
        self.layout.add_widget(back_btn)

        # Инструкция
        instruction = Label(
            text='Проведите пальцем по мячу для броска',
            font_size='14sp',
            color=(1, 1, 1, 0.8),
            size_hint=(None, None),
            size=(300, 30),
            pos_hint={'center_x': 0.5, 'top': 0.85}
        )
        self.layout.add_widget(instruction)

    def create_ball(self):
        """Создает мяч на экране"""
        if self.ball_widget:
            self.layout.remove_widget(self.ball_widget)

        center_x = self.layout.width / 2
        center_y = self.layout.height / 2

        self.ball_widget = Image(
            source=self.ball_image,
            size_hint=(None, None),
            size=(self.ball_size, self.ball_size),
            pos=(center_x - self.ball_size / 2, center_y - self.ball_size / 2)
        )
        self.layout.add_widget(self.ball_widget)

        # Создаем физический объект мяча с коллбеком
        self.ball_physics = BallPhysics(
            pos=(center_x, center_y),
            size=self.ball_size,
            sound_callback=self.play_bounce_sound  # ← БЕЗ скобок!
        )

    def on_touch_down(self, touch):
        """Глобальная обработка касаний на экране"""
        if self.ball_widget and self.ball_widget.collide_point(*touch.pos):
            self.touch_start_pos = touch.pos
            self.play_bounce_sound()
            touch.grab(self)
            return True
        return super().on_touch_down(touch)

    def on_touch_move(self, touch):
        """Движение пальца"""
        if touch.grab_current is self:
            return True
        return super().on_touch_move(touch)

    def on_touch_up(self, touch):
        """Отпускание пальца"""
        if touch.grab_current is self:
            if self.touch_start_pos:
                start = Vector(self.touch_start_pos)
                end = Vector(touch.pos)
                force = (end - start) * 0.3

                self.ball_physics.apply_force(force)
                self.is_physics_enabled = True
                self.play_bounce_sound()
                self.touch_start_pos = None
            touch.ungrab(self)
            return True
        return super().on_touch_up(touch)

    def play_bounce_sound(self):
        """Воспроизведение звука броска"""
        if self.sound:
            self.sound.stop()
            self.sound.volume = 1.2
            self.sound.play()
            # Возвращаем громкость через небольшое время
            Clock.schedule_once(lambda dt: setattr(self.sound, 'volume', 1.0) if self.sound else None, 0.1)

    def go_to_menu(self, instance):
        self.remove_ball()
        if self.physics_clock:
            self.physics_clock.cancel()
            self.physics_clock = None
        self.manager.current = 'menu'

    def remove_ball(self):
        """Удаляет мяч с экрана"""
        if self.ball_widget:
            self.layout.remove_widget(self.ball_widget)
            self.ball_widget = None
            self.ball_physics = None
            self.is_physics_enabled = False
            self.touch_start_pos = None

    def start_game(self):
        """Подготовка к новому броску"""
        if self.ball_widget and self.ball_physics:
            self.ball_physics.velocity = Vector(0, 0)
            self.is_physics_enabled = False
            (Animation(
                size=(self.ball_size * 1.1, self.ball_size * 1.1),
                duration=0.1
            ) + Animation(
                size=(self.ball_size, self.ball_size),
                duration=0.1
            )).start(self.ball_widget)


class FootballScreen(GameScreen):
    """Экран футбола"""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.name = 'football'
        self.ball_image = 'assets/balls/football.png'
        self.background_image = 'assets/backgrounds/football_bg.jpg'
        self.sound_file = ('assets/sounds/football_bounc'
                           'e.wav')
        self.ball_size = 120


class BasketballScreen(GameScreen):
    """Экран баскетбола"""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.name = 'basketball'
        self.ball_image = 'assets/balls/basketball.png'
        self.background_image = 'assets/backgrounds/basketball_bg.jpg'
        self.sound_file = 'assets/sounds/basketball_bounce.mp3'
        self.ball_size = 110

    def on_enter(self):
        super().on_enter()
        if self.ball_physics:
            self.ball_physics.bounce_factor = 0.8


class BowlingScreen(GameScreen):
    """Экран боулинга"""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.name = 'bowling'
        self.ball_image = 'assets/balls/bowling_ball.png'
        self.background_image = 'assets/backgrounds/bowling_bg.jpg'
        self.sound_file = 'assets/sounds/bowling_strike.mp3'
        self.ball_size = 100

    def on_enter(self):
        super().on_enter()
        if self.ball_physics:
            self.ball_physics.bounce_factor = 0.3


class DiceScreen(GameScreen):
    """Экран игральных костей"""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.name = 'dice'
        self.ball_image = 'assets/balls/dice.png'
        self.background_image = 'assets/backgrounds/dice.jpg'
        self.sound_file = 'assets/sounds/dice_throw.mp3'
        self.ball_size = 120

    def on_enter(self):
        super().on_enter()
        if self.ball_physics:
            self.ball_physics.bounce_factor = 0.6


class SportsGameApp(App):
    """Главное приложение"""

    def build(self):
        self.background_music = SoundLoader.load("assets/sounds/background.wav")
        if self.background_music:
            self.background_music.loop = True
            self.background_music.volume = 0.1
            self.background_music.play()

        self.sm = ScreenManager(transition=FadeTransition(duration=0.3))
        self.sm.add_widget(MainMenuScreen(name='menu'))
        self.sm.add_widget(FootballScreen(name='football'))
        self.sm.add_widget(BasketballScreen(name='basketball'))
        self.sm.add_widget(BowlingScreen(name='bowling'))
        self.sm.add_widget(DiceScreen(name='dice'))

        return self.sm

    def on_pause(self):
        if hasattr(self, 'background_music') and self.background_music:
            self.background_music.stop()
        return True

    def on_resume(self):
        if hasattr(self, 'background_music') and self.background_music:
            self.background_music.play()


if __name__ == '__main__':
    SportsGameApp().run()