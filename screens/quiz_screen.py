from kivy.clock import Clock
from kivy.core.window import Window
from kivy.utils import platform
from kivy.uix.image import Image
from kivy.uix.button import Button
from kivy.uix.floatlayout import FloatLayout
from kivy.graphics import Color, Rectangle, Line, PushMatrix, PopMatrix, Rotate, Translate, Ellipse, Triangle
from kivy.animation import Animation
from kivy.uix.widget import Widget
from kivy.core.text import Label as CoreLabel
from kivy.properties import NumericProperty, BooleanProperty, ColorProperty, ListProperty
from kivy.uix.behaviors import ButtonBehavior
import datetime
import math
import random

from screens.base_game_screen import BaseGameScreen
from screens.quiz.template_popup import TemplatePopup
from screens.quiz.template_manager import TemplateManager
from sound_manager import SoundManager


class ImageButton(ButtonBehavior, Image):
    """Кнопка с изображением"""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.allow_stretch = True
        self.keep_ratio = True


class DustParticle(Widget):
    """Частица пыли/искры с анимацией"""
    velocity_x = NumericProperty(0)
    velocity_y = NumericProperty(0)
    opacity = NumericProperty(1.0)
    size_factor = NumericProperty(1.0)
    color = ColorProperty((1, 1, 0.5, 0.8))
    glow_intensity = NumericProperty(1.0)
    target_glow = NumericProperty(1.0)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.size = (random.uniform(2, 5), random.uniform(2, 5))
        self.velocity_x = random.uniform(-30, 30)
        self.velocity_y = random.uniform(-30, 30)
        self.opacity = random.uniform(0.3, 0.8)
        self.color = (
            random.uniform(0.2, 0.5),  # R - красный (20-50%)
            random.uniform(0.7, 1.0),  # G - зеленый (70-100%)
            random.uniform(0.9, 1.0),  # B - синий (90-100%) - высокий
            self.opacity  # A - прозрачность
        )

        self.glow_intensity = 1.0
        self.target_glow = 1.0
        self.x = random.uniform(0, Window.width)
        self.y = random.uniform(0, Window.height)
        self.bind(pos=self._update_rect, size=self._update_rect)

    def _update_rect(self, *args):
        self.canvas.clear()
        with self.canvas:
            Color(*self.color[:3], self.color[3] * self.glow_intensity)
            Ellipse(pos=self.pos, size=self.size)
            if self.glow_intensity > 0.3:
                glow_size = (self.size[0] * 3, self.size[1] * 3)
                glow_pos = (self.x - self.size[0], self.y - self.size[1])
                Color(*self.color[:3], self.color[3] * self.glow_intensity * 0.3)
                Ellipse(pos=glow_pos, size=glow_size)

    def update(self, dt):
        self.x += self.velocity_x * dt
        self.y += self.velocity_y * dt
        if random.random() < 0.05:
            self.velocity_x += random.uniform(-10, 10)
            self.velocity_y += random.uniform(-10, 10)
        max_speed = 50
        self.velocity_x = max(-max_speed, min(max_speed, self.velocity_x))
        self.velocity_y = max(-max_speed, min(max_speed, self.velocity_y))
        if self.x < -self.width:
            self.x = Window.width
        elif self.x > Window.width:
            self.x = -self.width
        if self.y < -self.height:
            self.y = Window.height
        elif self.y > Window.height:
            self.y = -self.height
        if abs(self.glow_intensity - self.target_glow) > 0.01:
            self.glow_intensity += (self.target_glow - self.glow_intensity) * 0.1


class ParticleSystem(Widget):
    """Система частиц для создания эффекта пыли/искр"""
    particles = ListProperty([])
    is_active = BooleanProperty(False)
    glow_mode = BooleanProperty(False)
    base_glow = NumericProperty(0.5)
    active_glow = NumericProperty(1.2)

    def __init__(self, num_particles=20, **kwargs):
        super().__init__(**kwargs)
        self.num_particles = num_particles
        self.update_clock = None
        self.bind(pos=self._update_all, size=self._update_all)
        self.create_particles()
        self.start_perpetual_motion()

    def create_particles(self):
        self.particles = []
        for _ in range(self.num_particles):
            particle = DustParticle()
            self.particles.append(particle)
            self.add_widget(particle)

    def start_perpetual_motion(self):
        self.is_active = True
        if not self.update_clock:
            self.update_clock = Clock.schedule_interval(self.update_particles, 1 / 60)

    def set_glow_mode(self, active=True):
        self.glow_mode = active
        target_glow = self.active_glow if active else self.base_glow
        for particle in self.particles:
            particle.target_glow = target_glow

    def update_particles(self, dt):
        if not self.is_active:
            return
        for particle in self.particles:
            particle.update(dt)
        if self.glow_mode and random.random() < 0.02:
            for particle in self.particles:
                particle.glow_intensity = min(particle.target_glow * 1.3, 2.0)

    def _update_all(self, *args):
        for particle in self.particles:
            particle._update_rect()

    def cleanup(self):
        self.is_active = False
        if self.update_clock:
            self.update_clock.cancel()
            self.update_clock = None
        self.particles = []
        self.clear_widgets()


class RotatingImage(Image):
    """
    Вращающееся изображение с правильным вращением вокруг своего центра
    Наследуется от Image для правильной работы с текстурами
    """

    rotation_angle = NumericProperty(0)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.allow_stretch = True
        self.keep_ratio = True
        self._rotation_instruction = None

        # Привязываем свойства для обновления
        self.bind(rotation_angle=self._update_rotation)
        self.bind(center=self._update_origin)
        self.bind(size=self._update_origin)
        self.bind(pos=self._update_origin)

        # Настраиваем графику после инициализации
        Clock.schedule_once(self._setup_graphics, 0)

    def _setup_graphics(self, dt=None):
        """Настраивает графические инструкции для вращения"""
        # Очищаем старые инструкции
        self.canvas.before.clear()
        self.canvas.after.clear()

        # Создаем новые инструкции
        with self.canvas.before:
            PushMatrix()
            self._rotation_instruction = Rotate(
                angle=self.rotation_angle,
                origin=self.center
            )
        with self.canvas.after:
            PopMatrix()

    def _update_rotation(self, instance, value):
        """Обновляет угол вращения"""
        if self._rotation_instruction:
            self._rotation_instruction.angle = value

    def _update_origin(self, *args):
        """Обновляет центр вращения при изменении позиции или размера"""
        if self._rotation_instruction:
            self._rotation_instruction.origin = (self.center_x, self.center_y)

    def rotate_to(self, angle, duration=3.0, transition='linear'):
        """
        Анимирует вращение к указанному углу

        Args:
            angle: целевой угол в градусах
            duration: длительность анимации в секундах
            transition: тип анимации ('linear', 'in_quad', 'out_quad', и т.д.)
        """
        anim = Animation(rotation_angle=angle, duration=duration, transition=transition)
        anim.start(self)
        return anim


class WheelWithLines(Widget):
    """Виджет с вращающимися линиями и цифрами (без изображений)"""

    rotation_angle = NumericProperty(0)

    def __init__(self, sectors=None, **kwargs):
        super().__init__(**kwargs)
        self.sectors = sectors or ["1", "2", "3", "4", "5", "6", "7", "8"]
        self.is_spinning = False
        self.radius = 0
        self.on_complete_callback = None
        self.winner_index = None
        self.highlight_phase = 0
        self.highlight_timer = None
        self.bind(rotation_angle=self.update_wheel)
        self.bind(size=self.update_wheel)
        self.bind(pos=self.update_wheel)

    def highlight_winner(self, winner_index, duration=2.0, pulses=3):
        """Подсвечивает победивший сектор несколькими пульсациями"""
        self.winner_index = winner_index
        self.highlight_phase = 0

        # Отменяем предыдущий таймер
        if self.highlight_timer:
            self.highlight_timer.cancel()
            self.highlight_timer = None

        # Запускаем анимацию подсветки
        self.highlight_timer = Clock.schedule_interval(
            lambda dt: self._update_highlight(dt, pulses, duration),
            duration / (pulses * 2)
        )

        # Обновляем колесо для отображения подсветки
        self.update_wheel()

    def _update_highlight(self, dt, pulses, duration):
        """Обновляет фазу подсветки"""
        self.highlight_phase += 1
        self.update_wheel()

        # Завершаем подсветку
        if self.highlight_phase >= pulses * 2:
            if self.highlight_timer:
                self.highlight_timer.cancel()
                self.highlight_timer = None
            self.winner_index = None
            self.highlight_phase = 0
            self.update_wheel()

    def update_wheel(self, *args):
        self.canvas.clear()

        if not self.width or not self.height:
            return

        pos_x = self.x
        pos_y = self.y

        self.radius = min(self.width, self.height) / 2 - 10
        center_x = pos_x + self.width / 2
        center_y = pos_y + self.height / 2

        n = len(self.sectors)
        if n == 0:
            return

        angle_per_sector = 360.0 / n

        with self.canvas:
            PushMatrix()
            Translate(center_x, center_y)
            Rotate(angle=self.rotation_angle, origin=(0, 0))

            # Рисуем сектора с подсветкой
            for i in range(n):
                start_angle = math.radians(i * angle_per_sector)
                end_angle = math.radians((i + 1) * angle_per_sector)

                # Проверяем, нужно ли подсвечивать этот сектор
                is_highlighted = (self.winner_index is not None and
                                  i == self.winner_index and
                                  self.highlight_phase % 2 == 1)

                # Фон сектора (если подсвечен)
                if is_highlighted:
                    # Желтая подсветка
                    Color(1, 1, 0, 0.3)
                    # Рисуем залитый сектор
                    points = []
                    segments = 30
                    for s in range(segments + 1):
                        a = start_angle + (end_angle - start_angle) * s / segments
                        points.extend([
                            self.radius * 0.98 * math.cos(a),
                            self.radius * 0.98 * math.sin(a)
                        ])
                    # Добавляем центральную точку для замкнутой фигуры
                    points.extend([0, 0])
                    # Рисуем заливку
                    from kivy.graphics import Mesh
                    # Используем треугольники для заливки
                    Color(1, 1, 0, 0.3)
                    # Рисуем дугу с заливкой через Line с close=True
                    points = [0, 0]
                    for s in range(segments + 1):
                        a = start_angle + (end_angle - start_angle) * s / segments
                        points.extend([
                            self.radius * 0.98 * math.cos(a),
                            self.radius * 0.98 * math.sin(a)
                        ])
                    # Закрываем фигуру
                    points.extend([0, 0])
                    # Рисуем залитый сектор
                    from kivy.graphics import Line as KivyLine
                    KivyLine(points=points, close=True, width=0.5)

            # Перегородки (белые линии)
            for i in range(n):
                angle = math.radians(i * angle_per_sector)
                Color(1.0, 1.0, 1.0, 0.9)
                Line(
                    points=[
                        0, 0,
                        self.radius * math.cos(angle),
                        self.radius * math.sin(angle)
                    ],
                    width=1
                )

            # Внешняя граница
            Color(1.0, 1.0, 1.0, 0.8)
            Line(circle=(0, 0, self.radius), width=2)

            # Текст секторов
            for i in range(n):
                start_angle = math.radians(i * angle_per_sector)
                end_angle = math.radians((i + 1) * angle_per_sector)

                mid_angle = start_angle + (end_angle - start_angle) / 2
                text_radius = self.radius * 0.65
                text_x = text_radius * math.cos(mid_angle)
                text_y = text_radius * math.sin(mid_angle)
                rotate_angle = math.degrees(mid_angle)

                # Проверяем, нужно ли подсвечивать текст
                is_highlighted = (self.winner_index is not None and
                                  i == self.winner_index and
                                  self.highlight_phase % 2 == 1)

                # Размер шрифта для подсвеченного сектора
                font_size = max(18, self.radius * 0.22) if is_highlighted else max(14, self.radius * 0.15)

                label = CoreLabel(
                    text=self.sectors[i],
                    font_size=font_size,
                    color=(1, 1, 0, 1) if is_highlighted else (1, 1, 1, 0.95)
                )
                label.refresh()
                texture = label.texture

                if texture:
                    PushMatrix()
                    Translate(text_x, text_y)
                    Rotate(angle=rotate_angle, origin=(0, 0))
                    text_width = texture.width
                    text_height = texture.height

                    # Тень для читаемости
                    Color(0, 0, 0, 0.2 if is_highlighted else 0.1)
                    Rectangle(
                        pos=(-text_width / 2 - 3, -text_height / 2 - 3),
                        size=(text_width + 6, text_height + 6)
                    )
                    Color(1, 1, 0, 1) if is_highlighted else Color(1, 1, 1, 0.95)
                    Rectangle(
                        texture=texture,
                        pos=(-text_width / 2, -text_height / 2),
                        size=(text_width, text_height)
                    )
                    PopMatrix()

            # Центр
            Color(0.9, 0.9, 0.9, 0.8)
            Ellipse(pos=(-15, -15), size=(30, 30))
            Color(0.3, 0.3, 0.3, 0.8)
            Ellipse(pos=(-8, -8), size=(16, 16))

            PopMatrix()

            # Стрелка-указатель (сверху)
            arrow_size = self.radius * 0.08
            arrow_y = self.radius + 5

            with self.canvas:
                Color(1, 0, 0, 1)
                Triangle(
                    points=[
                        center_x - arrow_size, center_y + arrow_y - arrow_size * 0.5,
                        center_x + arrow_size, center_y + arrow_y - arrow_size * 0.5,
                        center_x, center_y + arrow_y + arrow_size * 0.5
                    ]
                )
                Color(0, 0, 0, 0.5)
                Line(
                    points=[
                        center_x - arrow_size, center_y + arrow_y - arrow_size * 0.5,
                        center_x + arrow_size, center_y + arrow_y - arrow_size * 0.5,
                        center_x, center_y + arrow_y + arrow_size * 0.5,
                        center_x - arrow_size, center_y + arrow_y - arrow_size * 0.5
                    ],
                    width=1
                )

    def spin(self, duration=3.0, slowdown_factor=0.7):
        """
        Запускает вращение с плавным замедлением с самого начала

        Args:
            duration: общая длительность вращения в секундах
            slowdown_factor: не используется (оставлен для совместимости)
        """
        if self.is_spinning:
            return

        self.is_spinning = True

        # Случайный угол (5-10 оборотов)
        extra_rotation = random.randint(0, 360)
        target_angle = self.rotation_angle + (random.randint(5, 10) * 360) + extra_rotation

        # out_quad - плавное замедление с самого начала
        anim = Animation(
            rotation_angle=target_angle,
            duration=duration,
            transition='out_quad'
        )
        anim.bind(on_complete=self.on_spin_complete)
        anim.start(self)

    def on_spin_complete(self, *args):
        self.is_spinning = False
        if self.on_complete_callback:
            self.on_complete_callback()

    def get_winner(self):
        if not self.sectors:
            return None, None
        n = len(self.sectors)
        angle_per_sector = 360.0 / n

        # Отнимаем 45 градусов для коррекции указателя
        pointer_angle = (0 - self.rotation_angle + 89) % 360
        index = int(pointer_angle / angle_per_sector) % n
        return index, self.sectors[index]


class QuizScreen(BaseGameScreen):
    """Экран Викторина с колесом"""

    DEBUG_MODE = True

    # === КОЭФФИЦИЕНТЫ ДЛЯ УПРАВЛЕНИЯ РАЗМЕРАМИ ===

    # Размер деревянного круга (fairy_disk) относительно экрана
    FAIRY_DISK_COEFF = 1

    # Размер белого колеса (линии и цифры) относительно fairy_disk
    WHEEL_TO_FAIRY_COEFF = 0.8

    # Размер fairy_drum относительно колеса (МЕНЯЙТЕ ЭТОТ КОЭФФИЦИЕНТ!)
    DRUM_TO_WHEEL_COEFF = 1

    # Настройки FPS для колеса
    WHEEL_FPS = 60

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.background_image = 'assets/backgrounds/quiz_bg.png'
        self.is_game_screen = True
        self.buttons_created = False
        self.fairy_size_coefficient = 1.1

        self.fairy_disk_widget = None
        self.fairy_drum_widget = None
        self.wheel_lines_widget = None
        self.wheel_container = None

        self.background_main = None
        self.background_dark = None
        self.is_night = False
        self.background_anim_main = None
        self.background_anim_dark = None
        self.background_is_forward = False
        self.background_return_timer = None

        self.original_sectors = []
        self.spin_start_time = 0
        self.current_template = None
        self.is_spinning = False

        # Скрытая кнопка для вращения
        self.hidden_spin_button = None

        # Система частиц
        self.particle_system = None

        # Кнопка со списками
        self.list_button = None

        # SoundManager
        self.sound_manager = SoundManager()

        # Звук вращения
        self.rotate_sound = None
        self.volume_anim = None

        # Звук кристалла (при остановке)
        self.crystal_sound = None

        # Инициализируем менеджер шаблонов
        self.template_manager = TemplateManager()

        Clock.schedule_once(self.set_landscape, 0.1)

    def _load_rotate_sound(self):
        """Загружает звук вращения"""
        try:
            from kivy.core.audio import SoundLoader
            self.rotate_sound = SoundLoader.load('assets/sounds/quiz_rotate.ogg')
            if self.rotate_sound:
                self.rotate_sound.volume = 0.0
                self._rotate_sound_volume = 0.0
                print("🔊 Звук вращения загружен")
            else:
                print("❌ Не удалось загрузить звук вращения")
        except Exception as e:
            print(f"❌ Ошибка загрузки звука: {e}")
            self.rotate_sound = None

    def _load_crystal_sound(self):
        """Загружает звук кристалла"""
        try:
            from kivy.core.audio import SoundLoader
            self.crystal_sound = SoundLoader.load('assets/sounds/coin/crystal.ogg')
            if self.crystal_sound:
                self.crystal_sound.volume = 1.0
                print("🔊 Звук кристалла загружен")
            else:
                print("❌ Не удалось загрузить звук кристалла")
        except Exception as e:
            print(f"❌ Ошибка загрузки звука кристалла: {e}")
            self.crystal_sound = None

    def _play_crystal_sound(self, dt):
        """Воспроизводит звук кристалла с задержкой"""
        if self.crystal_sound and not self.sound_manager.is_muted():
            self.crystal_sound.stop()
            self.crystal_sound.volume = 1.0
            self.crystal_sound.play()
            print("🔊 Звук кристалла воспроизведен (100% громкость)")

    def _fade_out_volume(self, duration):
        """Плавно уменьшает громкость звука до 0"""
        if not self.rotate_sound:
            return

        # Отменяем предыдущую анимацию громкости
        if self.volume_anim:
            self.volume_anim.cancel(self)
            self.volume_anim = None

        # Проверяем, играет ли звук
        if self.rotate_sound.state != 'play':
            print("🔊 Звук уже остановлен или не играет")
            return

        # Создаем анимацию уменьшения громкости
        self.volume_anim = Animation(
            rotate_sound_volume=0.0,
            duration=duration,
            transition='linear'
        )
        self.volume_anim.bind(on_complete=lambda *args: self._on_volume_fade_complete())
        self.volume_anim.start(self)

    def _on_volume_fade_complete(self):
        """Обработчик завершения уменьшения громкости"""
        if self.rotate_sound:
            self.rotate_sound.volume = 0.0
            self._rotate_sound_volume = 0.0
            self.rotate_sound.stop()
            print("🔊 Звук вращения остановлен (затухание завершено)")
        self.volume_anim = None

    @property
    def rotate_sound_volume(self):
        return getattr(self, '_rotate_sound_volume', 1.0)

    @rotate_sound_volume.setter
    def rotate_sound_volume(self, value):
        self._rotate_sound_volume = value
        if self.rotate_sound:
            self.rotate_sound.volume = value

    def log(self, message, *args):
        if self.DEBUG_MODE:
            if args:
                print(message.format(*args))
            else:
                print(message)

    def set_landscape(self, dt=None):
        if platform == 'android':
            try:
                from jnius import autoclass
                PythonActivity = autoclass('org.kivy.android.PythonActivity')
                activity = PythonActivity.mActivity
                activity.setRequestedOrientation(6)
            except:
                Window.orientation = 'landscape'
        else:
            Window.size = (700, 400)
        Clock.schedule_once(lambda dt: self.prepare_ui(), 0.3)

    def set_portrait(self, dt=None):
        if platform == 'android':
            try:
                from jnius import autoclass
                PythonActivity = autoclass('org.kivy.android.PythonActivity')
                activity = PythonActivity.mActivity
                activity.setRequestedOrientation(1)
            except:
                Window.orientation = 'portrait'
        else:
            Window.size = (400, 700)

    def prepare_ui(self):
        if not self.buttons_created:
            if platform != 'android':
                Window.size = (700, 400)
            Clock.schedule_once(self.create_ui_delayed, 0.1)

    def on_enter(self):
        self.set_landscape()
        super().on_enter()
        self.check_time_of_day()

        # Загружаем звук вращения при входе
        self._load_rotate_sound()

        # Загружаем звук кристалла при входе
        self._load_crystal_sound()

        # При входе на экран принудительно обновляем порядок и перерисовываем
        Clock.schedule_once(self._reorder_widgets_and_update, 0.2)

        # Запускаем систему частиц
        if self.particle_system:
            self.particle_system.start_perpetual_motion()

    def on_leave(self):
        """При выходе с экрана отменяем все таймеры и анимации"""
        if self.background_return_timer:
            self.background_return_timer.cancel()
            self.background_return_timer = None

        if self.background_anim_main:
            self.background_anim_main.cancel(self.background_main)
            self.background_anim_main = None
        if self.background_anim_dark:
            self.background_anim_dark.cancel(self.background_dark)
            self.background_anim_dark = None

        # Останавливаем звук вращения
        if self.rotate_sound:
            self.rotate_sound.stop()
            self.rotate_sound.volume = 0.0
            self._rotate_sound_volume = 0.0

        # Останавливаем звук кристалла
        if self.crystal_sound:
            self.crystal_sound.stop()

        # Отменяем анимацию громкости
        if self.volume_anim:
            self.volume_anim.cancel(self)
            self.volume_anim = None

        # Очищаем систему частиц
        if self.particle_system:
            self.particle_system.cleanup()
            if self.particle_system in self.layout.children:
                self.layout.remove_widget(self.particle_system)
            self.particle_system = None

        super().on_leave()

    def _reorder_widgets_and_update(self, dt):
        """Переупорядочивает виджеты и обновляет колесо"""
        if hasattr(self, 'layout') and self.layout:
            # Принудительно переупорядочиваем виджеты в правильном порядке
            widgets_to_keep = []
            widgets_to_reorder = []

            for child in self.layout.children[:]:
                if child == self.background_main or child == self.background_dark:
                    widgets_to_keep.append(child)
                elif child == self.back_button:
                    widgets_to_keep.append(child)
                elif child in [self.fairy_drum_widget, self.wheel_lines_widget,
                               self.fairy_disk_widget, self.list_button,
                               self.hidden_spin_button, self.particle_system]:
                    # Временно удаляем эти виджеты
                    self.layout.remove_widget(child)
                    widgets_to_reorder.append(child)

            # Добавляем виджеты в правильном порядке (снизу вверх)
            # 1. fairy_drum (самый нижний)
            if self.fairy_drum_widget in widgets_to_reorder:
                self.layout.add_widget(self.fairy_drum_widget)
            # 2. wheel_lines (средний)
            if self.wheel_lines_widget in widgets_to_reorder:
                self.layout.add_widget(self.wheel_lines_widget)
            # 3. fairy_disk (верхний)
            if self.fairy_disk_widget in widgets_to_reorder:
                self.layout.add_widget(self.fairy_disk_widget)
            # 4. hidden_spin_button (поверх fairy_disk)
            if self.hidden_spin_button in widgets_to_reorder:
                self.layout.add_widget(self.hidden_spin_button)
            # 5. list_button (поверх)
            if self.list_button in widgets_to_reorder:
                self.layout.add_widget(self.list_button)
            # 6. particle_system (поверх всего, но под кнопками)
            if self.particle_system in widgets_to_reorder:
                self.layout.add_widget(self.particle_system)

            # Принудительно обновляем размеры скрытой кнопки
            if self.hidden_spin_button and self.wheel_lines_widget:
                self.hidden_spin_button.size = self.wheel_lines_widget.size
                self.hidden_spin_button.pos = self.wheel_lines_widget.pos

            # Принудительно обновляем колесо
            if self.wheel_lines_widget:
                self.wheel_lines_widget.update_wheel()

            print("🔄 Виджеты переупорядочены и обновлены")

        # Загружаем сохраненный шаблон
        if hasattr(self, 'wheel_lines_widget') and self.wheel_lines_widget is not None:
            if hasattr(self, 'template_manager'):
                saved_template = self.template_manager.load_selected_template()
                if saved_template and saved_template.get('sectors'):
                    self.current_template = saved_template
                    sectors = saved_template.get('sectors', [])
                    if sectors:
                        self.original_sectors = sectors.copy()
                        display_sectors = self.truncate_sectors(sectors)
                        self.wheel_lines_widget.sectors = display_sectors
                        self.wheel_lines_widget.update_wheel()
                        print(f"📋 Загружен сохраненный шаблон: {saved_template.get('name')}")

    def check_time_of_day(self):
        current_hour = datetime.datetime.now().hour
        self.is_night = current_hour >= 18 or current_hour < 6
        if self.DEBUG_MODE:
            self.log(f"🌓 Время суток: {'Ночь' if self.is_night else 'День'} ({current_hour}:00)")

    def create_ui_delayed(self, dt):
        if not self.buttons_created:
            self.create_ui()
            self.buttons_created = True

    def set_list_button_enabled(self, enabled):
        """Включает/выключает кнопку списка шаблонов"""
        if self.list_button:
            self.list_button.disabled = not enabled
            # Делаем кнопку полупрозрачной, если отключена
            if enabled:
                self.list_button.opacity = 1.0
            else:
                self.list_button.opacity = 0.5

    def open_templates(self, instance):
        """Открывает попап со списком шаблонов (только если не вращается)"""
        if self.is_spinning:
            print("⛔ Вращение активно - кнопка списка заблокирована")
            return

        self.log("📋 Открытие шаблонов")
        popup = TemplatePopup(callback=self.on_template_loaded)
        popup.open()

    def on_template_loaded(self, template):
        self.log(f"📋 Шаблон загружен: {template.get('name')}")
        sectors = template.get('sectors', [])

        if sectors:
            self.original_sectors = sectors.copy()
            display_sectors = self.truncate_sectors(sectors)

            if self.wheel_lines_widget:
                self.wheel_lines_widget.sectors = display_sectors
                self.wheel_lines_widget.update_wheel()

            # Сохраняем выбранный шаблон
            if hasattr(self, 'template_manager'):
                template_id = template.get('id')
                if template_id:
                    self.template_manager.save_selected_template(template_id)
                    self.current_template = template
                    print(f"💾 Сохранен выбранный шаблон: {template.get('name')}")

            self.log(f"✅ Колесо обновлено: {len(sectors)} секторов")

    def truncate_sectors(self, sectors):
        truncated = []
        for sector in sectors:
            if len(sector) > 8:
                if len(sector) <= 10:
                    truncated_text = sector[:4] + '...' + sector[-2:]
                else:
                    truncated_text = sector[:5] + '...' + sector[-2:]
                truncated.append(truncated_text)
            else:
                truncated.append(sector)
        return truncated

    def create_ui(self):
        # Очищаем layout
        for child in self.layout.children[:]:
            if child != self.back_button:
                self.layout.remove_widget(child)

        screen_width = Window.width
        screen_height = Window.height

        self.log("=" * 60)
        self.log("📐 ИНФОРМАЦИЯ ОБ ЭКРАНЕ:")
        self.log(f"   screen_width:  {screen_width}")
        self.log(f"   screen_height: {screen_height}")
        self.log("=" * 60)

        # === 1. ФОН (САМЫЙ НИЖНИЙ СЛОЙ) ===
        time_suffix = 'night' if self.is_night else 'day'

        self.background_main = Image(
            source=f'assets/backgrounds/{time_suffix}_bg.png',
            allow_stretch=True,
            keep_ratio=False,
            size_hint=(1, 1),
            pos_hint={'x': 0, 'y': 0},
            opacity=0
        )
        self.layout.add_widget(self.background_main)

        self.background_dark = Image(
            source=f'assets/backgrounds/{time_suffix}_dark_bg.png',
            allow_stretch=True,
            keep_ratio=False,
            size_hint=(1, 1),
            pos_hint={'x': 0, 'y': 0},
            opacity=1
        )
        self.layout.add_widget(self.background_dark)

        # === 2. РАЗМЕРЫ ===
        min_side = min(screen_width, screen_height)

        # Размер fairy_disk
        fairy_size = int(min_side * self.FAIRY_DISK_COEFF)

        # Размер колеса с линиями
        wheel_size = int(fairy_size * self.WHEEL_TO_FAIRY_COEFF)

        # Размер fairy_drum (ИСПОЛЬЗУЕТ КОЭФФИЦИЕНТ!)
        drum_size = int(wheel_size * self.DRUM_TO_WHEEL_COEFF)

        self.log(f"📏 fairy_disk: {fairy_size}, wheel: {wheel_size}, drum: {drum_size}")
        self.log(f"📏 FAIRY_DISK_COEFF: {self.FAIRY_DISK_COEFF}")
        self.log(f"📏 DRUM_TO_WHEEL_COEFF: {self.DRUM_TO_WHEEL_COEFF}")

        # Позиции (центр экрана)
        fairy_x = (screen_width - fairy_size) / 2
        fairy_y = (screen_height - fairy_size) / 2

        wheel_x = (screen_width - wheel_size) / 2
        wheel_y = (screen_height - wheel_size) / 2

        drum_x = (screen_width - drum_size) / 2
        drum_y = (screen_height - drum_size) / 2

        # === 3. FAIRY_DRUM (САМЫЙ НИЖНИЙ СЛОЙ ИЗ ЭЛЕМЕНТОВ КОЛЕСА) ===
        self.fairy_drum_widget = RotatingImage(
            source='assets/images/fairy_drum.png',
            size_hint=(None, None),
            size=(drum_size, drum_size),
            pos=(drum_x, drum_y),
            rotation_angle=0
        )
        self.layout.add_widget(self.fairy_drum_widget)

        # === 4. WHEEL_WITH_LINES (СРЕДНИЙ СЛОЙ) ===
        # Проверяем, есть ли сохраненный шаблон
        saved_template = None
        if hasattr(self, 'template_manager'):
            saved_template = self.template_manager.load_selected_template()

        if saved_template and saved_template.get('sectors'):
            initial_sectors = saved_template.get('sectors')
            self.current_template = saved_template
            print(f"📋 Используем сохраненный шаблон: {saved_template.get('name')}")
        else:
            initial_sectors = ["1", "2", "3", "4", "5", "6", "7", "8"]
            print("📋 Используем шаблон по умолчанию")

        self.original_sectors = initial_sectors.copy()
        display_sectors = self.truncate_sectors(initial_sectors)

        self.wheel_lines_widget = WheelWithLines(
            sectors=display_sectors,
            size_hint=(None, None),
            size=(wheel_size, wheel_size),
            pos=(wheel_x, wheel_y)
        )
        self.layout.add_widget(self.wheel_lines_widget)
        self.wheel_container = self.wheel_lines_widget

        # === 5. FAIRY_DISK (САМЫЙ ВЕРХНИЙ СЛОЙ ИЗ ЭЛЕМЕНТОВ КОЛЕСА) ===
        self.fairy_disk_widget = Image(
            source='assets/images/fairy_disk.png',
            allow_stretch=True,
            keep_ratio=True,
            size_hint=(None, None),
            size=(fairy_size, fairy_size),
            pos=(fairy_x, fairy_y)
        )
        self.layout.add_widget(self.fairy_disk_widget)

        # === 6. СКРЫТАЯ КНОПКА ДЛЯ ВРАЩЕНИЯ (ПОВЕРХ КОЛЕСА) ===
        self.hidden_spin_button = Button(
            size_hint=(None, None),
            size=(wheel_size, wheel_size),
            pos=(wheel_x, wheel_y),
            background_color=(0, 0, 0, 0),
            background_normal='',
            color=(0, 0, 0, 0),
            text='',
            opacity=0
        )
        self.hidden_spin_button.bind(on_press=self.spin_wheel)
        self.layout.add_widget(self.hidden_spin_button)

        # === 7. КНОПКА СО СПИСКАМИ (ИЗОБРАЖЕНИЕ) ===
        btn_size = screen_width * 0.1
        self.list_button = ImageButton(
            source='assets/images/buttons/Fairy_list_button.png',
            size_hint=(None, None),
            size=(btn_size, btn_size),
            pos=(screen_width - btn_size - 20, screen_height - btn_size - 20),
            allow_stretch=True,
            keep_ratio=True
        )
        self.list_button.bind(on_press=self.open_templates)
        self.layout.add_widget(self.list_button)

        # === 8. СИСТЕМА ЧАСТИЦ (ПОВЕРХ ЭЛЕМЕНТОВ КОЛЕСА, НО ПОД КНОПКАМИ) ===
        self.particle_system = ParticleSystem(num_particles=25)
        self.layout.add_widget(self.particle_system)

        # === 9. КНОПКА НАЗАД (САМЫЙ ВЕРХНИЙ СЛОЙ) ===
        if self.back_button and self.back_button in self.layout.children:
            self.layout.remove_widget(self.back_button)
            self.layout.add_widget(self.back_button)

        # Добавляем callback для завершения вращения
        self.wheel_lines_widget.on_complete_callback = self.on_spin_complete

        self.log("✅ UI СОЗДАН")
        self.log("=" * 60)

    def spin_wheel(self, instance):
        """Запускает вращение"""
        if self.wheel_lines_widget and not self.wheel_lines_widget.is_spinning:
            self.is_spinning = True
            self.set_list_button_enabled(False)

            self.spin_start_time = datetime.datetime.now()
            spin_duration = 6.0

            # Отменяем предыдущий таймер возврата фона
            if self.background_return_timer:
                self.background_return_timer.cancel()
                self.background_return_timer = None

            # Включаем свечение частиц
            if self.particle_system:
                self.particle_system.set_glow_mode(True)

            # Воспроизводим звук вращения и сразу начинаем затухание
            if self.rotate_sound and not self.sound_manager.is_muted():
                # Отменяем предыдущую анимацию громкости
                if self.volume_anim:
                    self.volume_anim.cancel(self)
                    self.volume_anim = None

                # СБРАСЫВАЕМ ГРОМКОСТЬ НА 100% ПЕРЕД ВОСПРОИЗВЕДЕНИЕМ
                self.rotate_sound.volume = 1.0
                self._rotate_sound_volume = 1.0

                self.rotate_sound.stop()
                self.rotate_sound.play()
                print("🔊 Звук вращения запущен")
                # Начинаем затухание сразу с момента старта
                self._fade_out_volume(spin_duration)

            self.log("=" * 60)
            self.log("🎡 ЗАПУСК ВРАЩЕНИЯ")
            self.log(f"   Длительность: {spin_duration}с")

            # Анимация фона ВПЕРЕД (показываем светлый фон)
            self.animate_background_forward(duration=spin_duration)

            # Вращаем линии с замедлением (коэффициент 0.7 = 70% полной скорости, 30% замедление)
            self.wheel_lines_widget.spin(duration=spin_duration, slowdown_factor=0.7)

            # Вращаем fairy_drum синхронно с замедлением
            if self.fairy_drum_widget:
                extra_rotation = random.randint(0, 360)
                target_angle = self.fairy_drum_widget.rotation_angle + (random.randint(3, 8) * 360) + extra_rotation

                # Рассчитываем угол начала замедления для барабана
                total_rotation = target_angle - self.fairy_drum_widget.rotation_angle
                slowdown_start_angle = self.fairy_drum_widget.rotation_angle + total_rotation * 0.85

                # Сначала вращаем с постоянной скоростью
                anim1 = Animation(
                    rotation_angle=slowdown_start_angle,
                    duration=spin_duration * 0.7,
                    transition='linear'
                )

                # Затем замедляемся
                anim2 = Animation(
                    rotation_angle=target_angle,
                    duration=spin_duration * 0.3,
                    transition='out_quad'
                )

                anim1.bind(on_complete=lambda *args: anim2.start(self.fairy_drum_widget))
                anim1.start(self.fairy_drum_widget)

    def on_spin_complete(self):
        """Завершение вращения"""
        self.is_spinning = False
        self.set_list_button_enabled(True)

        # Останавливаем звук вращения
        if self.rotate_sound:
            self.rotate_sound.stop()
            self.rotate_sound.volume = 0.0
            self._rotate_sound_volume = 0.0

        if self.wheel_lines_widget:
            winner_index, winner_text = self.wheel_lines_widget.get_winner()
            if winner_text:
                if self.original_sectors and winner_index < len(self.original_sectors):
                    original_winner = self.original_sectors[winner_index]
                    self.log(f"🏆 ПОБЕДИТЕЛЬ: {original_winner} (сектор {winner_index + 1})")
                else:
                    self.log(f"🏆 ПОБЕДИТЕЛЬ: {winner_text} (сектор {winner_index + 1})")

                # Запускаем подсветку победившего сектора
                if self.wheel_lines_widget:
                    self.wheel_lines_widget.highlight_winner(winner_index, duration=2.0, pulses=3)

        # Выключаем свечение частиц
        if self.particle_system:
            self.particle_system.set_glow_mode(False)

        # Воспроизводим звук кристалла с задержкой 1 секунду
        Clock.schedule_once(self._play_crystal_sound, 0.5)

        # Пауза в 1 секунду перед возвратом фона
        if self.background_return_timer:
            self.background_return_timer.cancel()

        self.background_return_timer = Clock.schedule_once(
            self._return_background, 1.0
        )

    def _return_background(self, dt):
        """Возвращает фон обратно с плавной анимацией"""
        self.background_return_timer = None
        self.animate_background_backward(duration=2.5)

    def animate_background_forward(self, duration=3.0):
        """Анимация смены фона на светлый (main)"""
        if not self.background_main or not self.background_dark:
            return

        if self.background_anim_main:
            self.background_anim_main.cancel(self.background_main)
            self.background_anim_main = None
        if self.background_anim_dark:
            self.background_anim_dark.cancel(self.background_dark)
            self.background_anim_dark = None

        self.background_anim_main = Animation(opacity=1, duration=duration, transition='in_out_quad')
        self.background_anim_dark = Animation(opacity=0, duration=duration, transition='in_out_quad')

        self.background_anim_main.start(self.background_main)
        self.background_anim_dark.start(self.background_dark)

        self.background_is_forward = True
        self.log(f"🎬 АНИМАЦИЯ ФОНА ВПЕРЕД ({duration}с)")

    def animate_background_backward(self, duration=2.5):
        """Анимация возврата фона на темный (dark) с плавным замедлением"""
        if not self.background_main or not self.background_dark:
            return

        if self.background_anim_main:
            self.background_anim_main.cancel(self.background_main)
            self.background_anim_main = None
        if self.background_anim_dark:
            self.background_anim_dark.cancel(self.background_dark)
            self.background_anim_dark = None

        self.background_anim_main = Animation(opacity=0, duration=duration, transition='out_quad')
        self.background_anim_dark = Animation(opacity=1, duration=duration, transition='out_quad')

        self.background_anim_main.start(self.background_main)
        self.background_anim_dark.start(self.background_dark)

        self.background_is_forward = False
        self.log(f"🎬 АНИМАЦИЯ ФОНА НАЗАД ({duration}с)")

    def go_to_menu(self, instance=None):
        # Отменяем таймер перед выходом
        if self.background_return_timer:
            self.background_return_timer.cancel()
            self.background_return_timer = None

        # Останавливаем звук вращения
        if self.rotate_sound:
            self.rotate_sound.stop()
            self.rotate_sound.volume = 0.0
            self._rotate_sound_volume = 0.0

        # Останавливаем звук кристалла
        if self.crystal_sound:
            self.crystal_sound.stop()

        # Отменяем анимацию громкости
        if self.volume_anim:
            self.volume_anim.cancel(self)
            self.volume_anim = None

        # Очищаем систему частиц
        if self.particle_system:
            self.particle_system.cleanup()

        self.set_portrait()
        super().go_to_menu()