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
import random
import os

# Устанавливаем размер окна (можно менять)
Window.size = (400, 700)
Window.clearcolor = (0.1, 0.1, 0.1, 1)

class BallPhysics:
    """Класс для физики мяча"""

    def __init__(self, pos, size, sound_callback=None):
        self.pos = Vector(pos)
        self.velocity = Vector(0, 0)
        self.size = size
        self.radius = size / 2
        self.friction = 0.995  # Трение
        self.bounce_factor = 0.8  # Коэффициент отскока
        self.sound_callback = sound_callback  # ← Коллбек для звука

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

        # Воспроизводим звук отскока
        if bounce_occurred:
            self.sound_callback()
            print("Play bounce sound")

    def apply_force(self, force_vector):
        """Применить силу к мячу"""
        self.velocity += force_vector

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
        # В реальном приложении здесь будет код для шаринга

    def rate_game(self, instance):
        """Поставить оценку"""
        print("Rate feature would be implemented here")
        # В реальном приложении здесь будет переход в магазин приложений

    def exit_game(self, instance):
        """Выход из приложения"""
        App.get_running_app().stop()


class ControlButton(Button):
    """Кастомная кнопка для панели управления"""
    pass


class IconButton(FloatLayout):
    """Кнопка с иконкой вместо текста"""
    icon_source = StringProperty('')
    sport_name = StringProperty('')
    sport = StringProperty('')

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        # Создаем кнопку как фон
        self.btn = Button(
            background_normal='',
            background_color=(1, 1, 1, 0.001),
            border=(10, 10, 10, 10)
        )
        self.add_widget(self.btn)

        # Создаем изображение иконки
        self.icon = Image(
            source=self.icon_source,
            size_hint=(1, 1),
            pos_hint={'center_x': 0.5, 'center_y': 0.6},
            allow_stretch=True
        )
        self.add_widget(self.icon)

        # Связываем нажатие кнопки
        self.btn.bind(on_press=self.on_press)

    def on_press(self, instance):
        print()
        pass

class MainMenuScreen(Screen):
    """Главное меню с фоном и кнопками"""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.background_music = None

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
            pos_hint={'center_x': 0.5, 'top': 0.98}
        )
        layout.add_widget(title)

        # Список всех видов спорта с иконками
        sports = [
            # (название спорта, имя файла иконки, имя экрана)
            ('Football', 'assets/images/buttons/Football_ball_button.png', 'football'),
            ('Basketball', 'assets/images/buttons/Basketball_ball_button.png', 'basketball'),
            ('Bowling', 'assets/images/buttons/Bowling_ball_button.png', 'bowling'),
            ('Dice', 'assets/images/buttons/Dice_button.png', 'dice'),
            ('Dices', 'assets/images/buttons/Dice_button.png', 'dices'),
            ('Coin', 'assets/images/buttons/Dice_button.png', 'coin'),
            ('Roulette', 'assets/images/buttons/Dice_button.png', 'roulette'),
            ('RusRoulette', 'assets/images/buttons/Dice_button.png', 'rus_roulette'),
            ('Quiz', 'assets/images/buttons/Dice_button.png', 'quiz'),
            ('Random', 'assets/images/buttons/Dice_button.png', 'random'),
        ]

        # Создаем сетку 5x2 для иконок
        rows = 5
        cols = 2
        button_size = 0.15  # Размер кнопки относительно ширины экрана
        horizontal_spacing = 0.2
        vertical_spacing = 0
        start_y = 0.7  # Начальная позиция по Y

        for i, (sport_name, icon_path, screen_name) in enumerate(sports):
            row = i // cols
            col = i % cols

            # Рассчитываем позицию
            x_pos = 0.25 + col * (button_size + horizontal_spacing)
            y_pos = start_y - row * (button_size + vertical_spacing)

            # Создаем кнопку с иконкой
            btn = IconButton(
                icon_source=icon_path,
                sport_name=sport_name,
                size_hint=(button_size, button_size),
                pos_hint={'x': x_pos, 'y': y_pos},
                sport=screen_name  # Передаем имя экрана
            )
            btn.bind(on_press=self.change_to_game)
            layout.add_widget(btn)

        # Добавляем панель управления
        self.control_panel = ControlPanel()
        layout.add_widget(self.control_panel)

        self.add_widget(layout)

    def change_to_game(self, instance):
        """Переход к игровому экрану"""
        print("pressed")
        if hasattr(instance, 'sport'):
            screen_name = instance.sport
            print(f"Переход на экран: {screen_name}")  # Для отладки

            # Проверяем, существует ли экран
            if screen_name in self.manager.screen_names:
                self.manager.current = screen_name
                screen = self.manager.get_screen(screen_name)
                if hasattr(screen, 'start_game'):
                    screen.start_game()
            else:
                print(f"Экран {screen_name} не найден! Доступные экраны: {self.manager.screen_names}")


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
        self.is_physics_enabled = False  # Флаг включения физики
        self.bg_image = None

        # Запускаем обновление физики
        self.physics_clock = None

        self.add_widget(self.layout)

    def on_enter(self):
        """При входе на экран"""
        # Загружаем звук при входе на экран
        if self.sound_file and os.path.exists(self.sound_file):
            self.sound = SoundLoader.load(self.sound_file)
            if self.sound:
                print(f"Звук загружен для {self.name}: {self.sound_file}")
            else:
                print(f"Не удалось загрузить звук: {self.sound_file}")
        else:
            print(f"Файл не найден: {self.sound_file}")

        self.setup_background()
        self.setup_ui()
        self.start_physics_update()

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
                # Убираем pos_hint, если он есть, и устанавливаем абсолютную позицию
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
        # if hasattr(self, 'bg_image'):
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
        if not self.ball_widget:
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

        # Создаем виджет мяча в начальной позиции (только при первом создании)
        center_x = self.layout.width / 2
        center_y = self.layout.height / 2

        self.ball_widget = Image(
            source=self.ball_image,
            size_hint=(None, None),
            size=(self.ball_size, self.ball_size),
            pos=(center_x - self.ball_size / 2, center_y - self.ball_size / 2)
        )
        self.layout.add_widget(self.ball_widget)

        # Создаем физический объект мяча
        self.ball_physics = BallPhysics(
            pos=(center_x, center_y),
            size=self.ball_size,
            sound_callback=self.play_bounce_sound  # ← Передаем метод для звука
        )

    def on_touch_down(self, touch): # удалить и отменить коммент выше
        """Глобальная обработка касаний на экране"""
        # Проверяем, касается ли мяча
        if self.ball_widget and self.ball_widget.collide_point(*touch.pos):
            self.touch_start_pos = touch.pos
            self.play_bounce_sound()
            touch.grab(self)  # ← Захватываем касание
            return True
        return super().on_touch_down(touch)

    def on_touch_move(self, touch): # можно удалить
        """Движение пальца"""
        print("finger move")

        if touch.grab_current is self:  # ← Если это наше захваченное касание
            return True
        return super().on_touch_move(touch)


    def on_ball_touch_move(self, instance, touch):
        """Движение пальца по мячу"""
        if self.touch_start_pos and instance.collide_point(*touch.pos):
            return True
        return False

    def on_touch_up(self, touch):
        """Отпускание пальца - работает даже за пределами мяча!"""
        if touch.grab_current is self:  # ← Если это наше касание
            if self.touch_start_pos:
                # Вычисляем вектор силы свайпа
                start = Vector(self.touch_start_pos)
                end = Vector(touch.pos)
                force = (end - start) * 0.3

                # Применяем силу к мячу
                self.ball_physics.apply_force(force)
                self.is_physics_enabled = True
                self.play_bounce_sound()

                # Сбрасываем
                self.touch_start_pos = None
            print("Бросок")

            touch.ungrab(self)  # ← Отпускаем захват касания
            return True
        return super().on_touch_up(touch)

    def on_ball_touch_up(self, instance, touch): # используется в DicesScreen
        """Отпускание пальца - бросок мяча"""
        if self.touch_start_pos and instance.collide_point(*touch.pos):
            # Вычисляем вектор силы
            start = Vector(self.touch_start_pos)
            end = Vector(touch.pos)
            force = (end - start) * 0.3  # Коэффициент силы

            # Применяем силу к мячу
            self.ball_physics.apply_force(force, max_speed=20)
            self.is_physics_enabled = True

            # Проигрываем звук броска
            self.play_bounce_sound()

            # Сбрасываем
            self.touch_start_pos = None

            return True
        return False

    def play_bounce_sound(self):
        """Воспроизведение звука броска"""
        if self.sound:
            self.sound.stop()
            self.sound.volume = 1.2  # Немного громче для броска
            self.sound.play()
            self.sound.volume = 1.0  # Возвращаем нормальную громкость

    def get_action_text(self):
        """Текст для кнопки действия"""
        actions = {
            'football': 'KICK BALL!',
            'basketball': 'SHOOT BALL!',
            'bowling': 'ROLL BALL!',
            'dice': 'THROW DICE!'
        }
        return actions.get(self.name, 'PLAY!')

    def go_to_menu(self, instance):
        # удаляем мяч
        self.remove_ball()

        # Останавливаем обновление физики
        if self.physics_clock:
            self.physics_clock.cancel()
            self.physics_clock = None

        """Возврат в главное меню"""
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
        """Подготовка к новому броску - сбрасываем только скорость"""
        if self.ball_widget and self.ball_physics:
            # НЕ меняем позицию мяча! Он остается там, где остановился
            # Сбрасываем только скорость
            self.ball_physics.velocity = Vector(0, 0)

            # Выключаем физику
            self.is_physics_enabled = False

            # Визуальный эффект готовности
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
        self.sound_file = 'assets/sounds/football_bounce.wav'
        self.ball_size = 120


    def on_enter(self):
        """При входе на экран"""
        self.setup_background()
        self.setup_ui()
        self.start_physics_update()

        # Если мяч еще не создан, создаем его
        if not self.ball_widget:
            self.create_ball()

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
        # Специфичные для баскетбола настройки
        if self.ball_physics:
            self.ball_physics.bounce_factor = 0.8  # Баскетбольный мяч хорошо прыгает
            self.ball_physics.gravity = Vector(0, -0.5)


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
        # Специфичные для боулинга настройки
        if self.ball_physics:
            self.ball_physics.bounce_factor = 0.3  # Шар для боулинга плохо отскакивает
            self.ball_physics.gravity = Vector(0, -0.2)


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
        # Специфичные для костей настройки
        if self.ball_physics:
            self.ball_physics.bounce_factor = 0.6
            self.ball_physics.gravity = Vector(0, -0.3)

    def on_ball_touch_up(self, instance, touch):
        """Особое поведение для костей - добавляем вращение"""
        result = super().on_ball_touch_up(instance, touch)
        if result:
            # Добавляем вращение к костям
            rotation = random.uniform(360, 1080)  # От 1 до 3 полных оборотов
            anim = Animation(rotation=rotation, duration=1.5)
            anim.start(self.ball_widget)
        return result

class DicesScreen(GameScreen):
    pass

class CoinScreen(GameScreen):
    pass

class RouletteScreen(GameScreen):
    pass

class RusRoletteScreen(GameScreen):
    pass

class QuizScreen(GameScreen):
    pass

class RandomNumberScreen(GameScreen):
    pass

class SportsGameApp(App):
    """Главное приложение"""

    def build(self):
        # Загружаем музыку один раз при запуске
        self.background_music = SoundLoader.load("assets/sounds/background.wav")
        if self.background_music:
            self.background_music.loop = True
            self.background_music.volume = 0.1
            self.background_music.play()  # Запускаем сразу

        # Создаем менеджер экранов
        self.sm = ScreenManager(transition=FadeTransition(duration=0.3))

        # Добавляем экраны
        self.sm.add_widget(MainMenuScreen(name='menu'))

        self.sm.add_widget(FootballScreen(name='football'))
        self.sm.add_widget(BasketballScreen(name='basketball'))
        self.sm.add_widget(BowlingScreen(name='bowling'))
        self.sm.add_widget(CoinScreen(name='coin'))
        self.sm.add_widget(DiceScreen(name='dice'))
        self.sm.add_widget(DicesScreen(name='dices'))
        self.sm.add_widget(RouletteScreen(name='roulette'))
        self.sm.add_widget(RusRoletteScreen(name='rus_roulette'))
        self.sm.add_widget(QuizScreen(name='quiz'))
        self.sm.add_widget(RandomNumberScreen(name='random_number'))

        return self.sm

    def on_pause(self):
        """Пауза при сворачивании приложения"""
        if hasattr(self, 'background_music') and self.background_music:
            self.background_music.stop()
        return True

    def on_resume(self):
        """Возобновление приложения"""
        if hasattr(self, 'background_music') and self.background_music:
            self.background_music.play()
        pass


if __name__ == '__main__':
    SportsGameApp().run()