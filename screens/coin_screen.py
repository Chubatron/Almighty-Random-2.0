from kivy.uix.image import Image
from kivy.uix.widget import Widget
from kivy.animation import Animation
from kivy.clock import Clock
from kivy.properties import NumericProperty, BooleanProperty, ColorProperty, ListProperty, StringProperty, \
    ObjectProperty
from kivy.core.window import Window
from kivy.core.image import Image as CoreImage
from kivy.core.audio import SoundLoader
from kivy.graphics import Color, Ellipse, Rectangle, Line, PushMatrix, PopMatrix, Rotate, Translate, \
    Scale
import random
import os
import math
from functools import partial

from screens.base_game_screen import BaseGameScreen


class DustParticle(Widget):
    """Частица пыли/искры с анимацией"""
    velocity_x = NumericProperty(0)
    velocity_y = NumericProperty(0)
    opacity = NumericProperty(1.0)
    size_factor = NumericProperty(1.0)
    color = ColorProperty((1, 1, 0.5, 0.8))  # Желтовато-оранжевый цвет
    glow_intensity = NumericProperty(1.0)  # Интенсивность свечения
    target_glow = NumericProperty(1.0)  # Целевая интенсивность для плавных переходов

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.size = (random.uniform(2, 5), random.uniform(2, 5))
        self.velocity_x = random.uniform(-30, 30)
        self.velocity_y = random.uniform(-30, 30)
        self.opacity = random.uniform(0.3, 0.8)
        self.color = (
            random.uniform(0.8, 1.0),  # R - оранжево-желтый
            random.uniform(0.5, 0.8),  # G
            random.uniform(0.2, 0.4),  # B - мало синего
            self.opacity
        )
        self.glow_intensity = 1.0
        self.target_glow = 1.0

        # Случайное начальное положение
        self.x = random.uniform(0, Window.width)
        self.y = random.uniform(0, Window.height)

        self.bind(pos=self._update_rect, size=self._update_rect)

    def _update_rect(self, *args):
        self.canvas.clear()
        with self.canvas:
            # Рисуем частицу с эффектом свечения
            Color(*self.color[:3], self.color[3] * self.glow_intensity)

            # Основная частица
            Ellipse(pos=self.pos, size=self.size)

            # Эффект свечения (больший круг с низкой прозрачностью)
            if self.glow_intensity > 0.3:
                glow_size = (self.size[0] * 3, self.size[1] * 3)
                glow_pos = (self.x - self.size[0], self.y - self.size[1])
                Color(*self.color[:3], self.color[3] * self.glow_intensity * 0.3)
                Ellipse(pos=glow_pos, size=glow_size)

    def update(self, dt):
        """Обновление позиции частицы"""
        self.x += self.velocity_x * dt
        self.y += self.velocity_y * dt

        # Плавное изменение скорости для хаотичности
        if random.random() < 0.05:
            self.velocity_x += random.uniform(-10, 10)
            self.velocity_y += random.uniform(-10, 10)

        # Ограничение скорости
        max_speed = 50
        self.velocity_x = max(-max_speed, min(max_speed, self.velocity_x))
        self.velocity_y = max(-max_speed, min(max_speed, self.velocity_y))

        # Зацикливание по краям экрана
        if self.x < -self.width:
            self.x = Window.width
        elif self.x > Window.width:
            self.x = -self.width

        if self.y < -self.height:
            self.y = Window.height
        elif self.y > Window.height:
            self.y = -self.height

        # Плавное изменение интенсивности свечения
        if abs(self.glow_intensity - self.target_glow) > 0.01:
            self.glow_intensity += (self.target_glow - self.glow_intensity) * 0.1


class ParticleSystem(Widget):
    """Система частиц для создания эффекта пыли/искр"""
    particles = ListProperty([])
    is_active = BooleanProperty(False)
    glow_mode = BooleanProperty(False)  # Режим интенсивного свечения
    base_glow = NumericProperty(0.5)  # Базовая яркость
    active_glow = NumericProperty(1.2)  # Яркость при активном режиме

    def __init__(self, num_particles=20, **kwargs):
        super().__init__(**kwargs)
        self.num_particles = num_particles
        self.update_clock = None
        self.bind(pos=self._update_all, size=self._update_all)

        # Создаем частицы
        self.create_particles()

        # Сразу запускаем анимацию частиц (они всегда движутся)
        self.start_perpetual_motion()

    def create_particles(self):
        """Создает частицы"""
        self.particles = []
        for _ in range(self.num_particles):
            particle = DustParticle()
            self.particles.append(particle)
            self.add_widget(particle)

    def start_perpetual_motion(self):
        """Запускает вечное движение частиц"""
        self.is_active = True

        if not self.update_clock:
            self.update_clock = Clock.schedule_interval(self.update_particles, 1 / 60)

    def set_glow_mode(self, active=True):
        """Устанавливает режим свечения (яркий или обычный)"""
        self.glow_mode = active
        target_glow = self.active_glow if active else self.base_glow

        for particle in self.particles:
            particle.target_glow = target_glow

    def update_particles(self, dt):
        """Обновляет все частицы"""
        if not self.is_active:
            return

        for particle in self.particles:
            particle.update(dt)

        # Периодически меняем интенсивность свечения для эффекта мерцания
        # только если в активном режиме
        if self.glow_mode and random.random() < 0.02:
            for particle in self.particles:
                # Временное усиление свечения для мерцания
                particle.glow_intensity = min(particle.target_glow * 1.3, 2.0)

    def _update_all(self, *args):
        """Обновляет все частицы при изменении размера/позиции"""
        for particle in self.particles:
            particle._update_rect()

    def cleanup(self):
        """Очищает все частицы и останавливает анимацию"""
        self.is_active = False
        if self.update_clock:
            self.update_clock.cancel()
            self.update_clock = None
        self.particles = []
        self.clear_widgets()


class FullScreenTouchArea(Widget):
    """Область на весь экран для возврата монеты"""
    is_enabled = BooleanProperty(False)  # По умолчанию выключена

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.size_hint = (1, 1)  # На весь экран
        self.pos_hint = {'x': 0, 'y': 0}

    def on_touch_down(self, touch):
        if self.is_enabled and self.collide_point(*touch.pos):
            return True
        return super().on_touch_down(touch)


class TouchArea(Widget):
    """Область для нажатия с визуальной подсветкой"""
    highlight_color = ColorProperty((0, 1, 0, 0.3))
    is_pressed = BooleanProperty(False)
    is_enabled = BooleanProperty(True)  # Флаг для блокировки/разблокировки области

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.touch_pos = (0, 0)
        self.bind(pos=self._update_rect, size=self._update_rect)

    def on_touch_down(self, touch):
        # Проверяем, включена ли область и есть ли коллизия
        if self.is_enabled and self.collide_point(*touch.pos):
            self.is_pressed = True
            self.touch_pos = touch.pos
            self.show_touch_feedback()
            return True
        return super().on_touch_down(touch)

    def on_touch_up(self, touch):
        if self.is_enabled and self.collide_point(*touch.pos):
            self.is_pressed = False
            self.hide_touch_feedback()
            return True
        return super().on_touch_up(touch)

    def show_touch_feedback(self):
        self.canvas.clear()
        with self.canvas:
            Color(*self.highlight_color)
            Ellipse(pos=(self.touch_pos[0] - 40, self.touch_pos[1] - 40), size=(80, 80))
            Color(0, 1, 0, 0.8)
            Ellipse(pos=(self.touch_pos[0] - 40, self.touch_pos[1] - 40), size=(80, 80), width=2)
        Clock.schedule_once(lambda dt: self.hide_touch_feedback(), 0.3)

    def hide_touch_feedback(self):
        self.canvas.clear()

    def _update_rect(self, *args):
        self.canvas.before.clear()
        with self.canvas.before:
            Color(0.5, 0.5, 0.5, 0.1)
            Rectangle(pos=self.pos, size=self.size)


class SpritesheetCoin(Image):
    """Монета из спрайт-листа 12x9 (108 кадров)"""
    current_frame = NumericProperty(0)
    is_animating = BooleanProperty(False)
    frames = ListProperty([])
    rotation_angle = NumericProperty(-90)  # Поворот против часовой стрелки

    # Флаг для зеркального отображения монеты
    coin_mirror = NumericProperty(1)

    # Диапазон кадров для текущей анимации [start, end]
    animation_range = ListProperty([0, 11])  # По умолчанию первые 12 кадров

    # Свойства для позиции на эллипсе
    ellipse_offset_x = NumericProperty(0)
    ellipse_offset_y = NumericProperty(0)

    # Дополнительное смещение для позиционирования монеты (в пикселях)
    extra_offset_x = NumericProperty(0)
    extra_offset_y = NumericProperty(0)

    # Параметры тени
    shadow_offset_x = NumericProperty(0)
    shadow_offset_y = NumericProperty(0)
    shadow_scale_y = NumericProperty(1)
    shadow_alpha = NumericProperty(0.6)

    # Шаг пропуска кадров (1 - все кадры, 2 - каждый второй и т.д.)
    frame_step = NumericProperty(1)

    # Спиральный фактор (уменьшение радиуса)
    spiral_factor = NumericProperty(1.0)

    # Прозрачность монеты
    coin_opacity = NumericProperty(1.0)

    # Текущий спрайт-лист
    current_spritesheet = StringProperty('')

    # Флаг для предотвращения артефактов при смене кадров
    _updating = BooleanProperty(False)

    # Флаг для отладки (выводить каждый кадр)
    debug_mode = BooleanProperty(False)

    def __init__(self, spritesheet_paths=None, frame_width=64, frame_height=64,
                 cols=12, rows=9, total_frames=108, start_frame=0,
                 shadow_offset_x=0, shadow_offset_y=0,
                 shadow_scale_y=1.0, shadow_alpha=0.6, coin_opacity=1.0, debug=False, **kwargs):
        super().__init__(**kwargs)

        self.frame_width = frame_width
        self.frame_height = frame_height
        self.cols = cols
        self.rows = rows
        self.total_frames = total_frames
        self.start_frame = start_frame
        self.anim_clock = None
        self.current_fps = 60
        self.spritesheet_paths = spritesheet_paths or {}
        self.frame_step = 1
        self.spiral_factor = 1.0
        self.coin_opacity = coin_opacity
        self.debug_mode = debug

        # Устанавливаем параметры тени
        self.shadow_offset_x = shadow_offset_x
        self.shadow_offset_y = shadow_offset_y
        self.shadow_scale_y = shadow_scale_y
        self.shadow_alpha = shadow_alpha

        # Привязываем все свойства, влияющие на отрисовку
        self.bind(texture=self._update_rotation)
        self.bind(pos=self._update_rotation, size=self._update_rotation)
        self.bind(rotation_angle=self._update_rotation)
        self.bind(ellipse_offset_x=self._update_position,
                  ellipse_offset_y=self._update_position,
                  extra_offset_x=self._update_position,
                  extra_offset_y=self._update_position)
        self.bind(coin_mirror=self._update_rotation)
        self.bind(spiral_factor=self._update_position)
        self.bind(coin_opacity=self._update_rotation)
        self.bind(shadow_offset_x=self._update_rotation,
                  shadow_offset_y=self._update_rotation,
                  shadow_scale_y=self._update_rotation,
                  shadow_alpha=self._update_rotation)

    def load_spritesheet(self, spritesheet_path):
        """Загружает спрайт-лист 12x9 (108 кадров)"""
        if not os.path.exists(spritesheet_path):
            return False

        try:
            img = CoreImage(spritesheet_path)
            texture = img.texture
            if not texture:
                return False

            tex_width, tex_height = texture.size

            frame_w = min(self.frame_width, tex_width // self.cols)
            frame_h = min(self.frame_height, tex_height // self.rows)

            frames = []
            for i in range(self.total_frames):
                row = i // self.cols
                col = i % self.cols
                x = col * frame_w
                y = (self.rows - 1 - row) * frame_h
                try:
                    frame = texture.get_region(x, y, frame_w, frame_h)
                    frames.append(frame)
                except Exception as e:
                    pass

            self.frames = frames
            self.current_spritesheet = spritesheet_path

            if self.frames and 0 <= self.start_frame < len(self.frames):
                self.texture = self.frames[self.start_frame]

            return True

        except Exception as e:
            return False

    def set_animation_range(self, start_frame, end_frame):
        """Устанавливает диапазон кадров для анимации"""
        # Проверяем, что индексы в пределах допустимого
        if not self.frames:
            return

        start_frame = max(0, min(start_frame, len(self.frames) - 1))
        end_frame = max(0, min(end_frame, len(self.frames) - 1))

        # Убеждаемся, что start_frame <= end_frame
        if start_frame > end_frame:
            start_frame, end_frame = end_frame, start_frame

        self.animation_range = [start_frame, end_frame]

    def _update_rotation(self, *args):
        """Обновляет поворот изображения и тени"""
        if not self.texture:
            return

        if self.width <= 0 or self.height <= 0 or (self.x == 0 and self.y == 0):
            Clock.schedule_once(lambda dt: self._update_rotation(), 0.1)
            return

        # Предотвращаем множественные обновления
        if self._updating:
            return

        self._updating = True

        self.canvas.clear()

        center_x = self.x + self.width / 2
        center_y = self.y + self.height / 2

        with self.canvas:
            # ===== ТЕНЬ =====
            PushMatrix()
            Translate(center_x, center_y)
            Rotate(angle=self.rotation_angle, origin=(0, 0))
            Translate(self.shadow_offset_x, self.shadow_offset_y)
            # Применяем масштабирование тени (отрицательный Scale для отражения по Y)
            Scale(1, -abs(self.shadow_scale_y), 1)
            Translate(-center_x, -center_y)

            Color(0, 0, 0, self.shadow_alpha)
            Rectangle(texture=self.texture, pos=self.pos, size=self.size)
            PopMatrix()

            # ===== МОНЕТА =====
            PushMatrix()
            Translate(center_x, center_y)
            Scale(self.coin_mirror, 1, 1)
            Rotate(angle=self.rotation_angle, origin=(0, 0))
            Translate(-center_x, -center_y)

            # Только одна монета, без копий
            Color(1.3, 1.3, 1.3, self.coin_opacity)
            Rectangle(texture=self.texture, pos=self.pos, size=self.size)

            PopMatrix()

        self._updating = False

    def _update_position(self, *args):
        """Обновляет позицию монеты на эллипсе"""
        base_center_x = 0.35
        base_center_y = 0.5

        # Применяем спиральный фактор к смещению эллипса
        current_offset_x = self.ellipse_offset_x * self.spiral_factor
        current_offset_y = self.ellipse_offset_y * self.spiral_factor

        self.pos_hint = {
            'center_x': base_center_x + current_offset_x + (self.extra_offset_x / Window.width),
            'center_y': base_center_y + current_offset_y + (self.extra_offset_y / Window.height)
        }

        Clock.schedule_once(lambda dt: self._update_rotation(), 0.05)

    def start_animation(self, fps=60, frame_step=1):
        """
        Запускает анимацию вращения (без дополнительных эффектов)
        """
        if not self.frames or self.is_animating:
            return

        self.is_animating = True
        self.current_fps = fps
        self.frame_step = max(1, frame_step)  # Убеждаемся, что шаг >= 1
        self.current_frame = self.animation_range[0]
        self.frame_duration = 1.0 / fps

        if self.anim_clock:
            self.anim_clock.cancel()

        self.anim_clock = Clock.schedule_interval(self.next_frame, self.frame_duration)

    def next_frame(self, dt):
        if not self.is_animating or not self.frames:
            return

        # Вычисляем следующий кадр
        next_frame = self.current_frame + self.frame_step

        # Проверяем, не вышли ли мы за верхнюю границу
        if next_frame > self.animation_range[1]:
            # Циклически возвращаемся к началу диапазона
            range_size = self.animation_range[1] - self.animation_range[0] + 1
            next_frame = self.animation_range[0] + ((next_frame - self.animation_range[0]) % range_size)

        # Проверяем, не вышли ли мы за нижнюю границу (при отрицательном шаге)
        elif next_frame < self.animation_range[0]:
            range_size = self.animation_range[1] - self.animation_range[0] + 1
            next_frame = self.animation_range[1] - ((self.animation_range[1] - next_frame) % range_size)

        # Убеждаемся, что кадр в допустимом диапазоне
        next_frame = max(self.animation_range[0], min(next_frame, self.animation_range[1]))

        self.current_frame = next_frame
        self.texture = self.frames[self.current_frame]

        self._update_rotation()

    def stop_animation(self):
        """Останавливает анимацию"""
        self.is_animating = False

        if self.anim_clock:
            self.anim_clock.cancel()
            self.anim_clock = None

    def set_result(self, result):
        """Устанавливает финальный кадр - ВСЕГДА последний кадр (108-й) независимо от результата"""
        if not self.frames:
            return

        # Останавливаем анимацию
        self.stop_animation()

        # Всегда показываем последний кадр (индекс 107 - это 108-й кадр)
        frame_index = 107  # 108-й кадр

        # Устанавливаем текстуру
        self.texture = self.frames[frame_index]

        # Принудительно очищаем canvas и рисуем заново
        self.canvas.clear()
        Clock.schedule_once(lambda dt: self._force_redraw(), 0.01)

    def _force_redraw(self):
        """Принудительная перерисовка с полной очисткой"""
        self._updating = False
        self._update_rotation()

    def reset_to_first_animation(self, start_frame=0):
        """Сбрасывает монету к первым 12 кадрам"""
        self.stop_animation()
        self.set_animation_range(0, min(11, len(self.frames) - 1))
        self.extra_offset_x = 0
        self.extra_offset_y = 0
        self.ellipse_offset_x = 0
        self.ellipse_offset_y = 0
        self.spiral_factor = 1.0
        self.coin_opacity = 1.0
        if 0 <= start_frame < len(self.frames):
            self.texture = self.frames[start_frame]

        # Обновляем отображение с задержкой
        Clock.schedule_once(lambda dt: self._update_rotation(), 0.02)

    def cleanup(self):
        """Полная очистка монеты"""
        self.stop_animation()
        self.frames = []
        self.texture = None
        self.canvas.clear()


class FinalSpritesheetCoin(Image):
    """Монета для финальной анимации из спрайт-листа 6x6 (36 кадров)"""
    current_frame = NumericProperty(0)
    is_animating = BooleanProperty(False)
    frames = ListProperty([])
    rotation_angle = NumericProperty(270)  # Поворот на 270 градусов по часовой стрелке (90+180=270)

    # Флаг для отладки
    debug_mode = BooleanProperty(False)

    def __init__(self, spritesheet_path, frame_width=128, frame_height=128,
                 cols=6, rows=6, total_frames=36, start_frame=0, debug=False, **kwargs):
        super().__init__(**kwargs)

        self.frame_width = frame_width
        self.frame_height = frame_height
        self.cols = cols
        self.rows = rows
        self.total_frames = total_frames
        self.start_frame = start_frame
        self.anim_clock = None
        self.current_fps = 60
        self.debug_mode = debug

        # Загружаем спрайт-лист
        self.load_spritesheet(spritesheet_path)

        # Привязываем обновление
        self.bind(texture=self._update_display)
        self.bind(pos=self._update_display, size=self._update_display)

    def load_spritesheet(self, spritesheet_path):
        """Загружает спрайт-лист 6x6 (36 кадров)"""
        if not os.path.exists(spritesheet_path):
            return False

        try:
            img = CoreImage(spritesheet_path)
            texture = img.texture
            if not texture:
                return False

            tex_width, tex_height = texture.size

            frame_w = min(self.frame_width, tex_width // self.cols)
            frame_h = min(self.frame_height, tex_height // self.rows)

            frames = []
            for i in range(self.total_frames):
                row = i // self.cols
                col = i % self.cols
                x = col * frame_w
                y = (self.rows - 1 - row) * frame_h
                try:
                    frame = texture.get_region(x, y, frame_w, frame_h)
                    frames.append(frame)
                except Exception as e:
                    pass

            self.frames = frames

            if self.frames and 0 <= self.start_frame < len(self.frames):
                self.texture = self.frames[self.start_frame]

            return True

        except Exception as e:
            return False

    def start_animation(self, fps=30, loop=False):
        """Запускает анимацию финального спрайт-листа (один раз)"""
        if not self.frames or self.is_animating:
            return

        self.is_animating = True
        self.current_fps = fps
        self.current_frame = 0
        self.loop = loop
        self.frame_duration = 1.0 / fps

        if self.anim_clock:
            self.anim_clock.cancel()

        self.anim_clock = Clock.schedule_interval(self.next_frame, self.frame_duration)

    def next_frame(self, dt):
        if not self.is_animating or not self.frames:
            return

        # Переходим к следующему кадру
        next_frame = self.current_frame + 1

        # Проверяем, не вышли ли за пределы
        if next_frame >= len(self.frames):
            if self.loop:
                next_frame = 0
            else:
                # Останавливаем анимацию на последнем кадре
                self.stop_animation()
                return

        self.current_frame = next_frame
        self.texture = self.frames[self.current_frame]

        self._update_display()

    def stop_animation(self):
        """Останавливает анимацию"""
        self.is_animating = False

        if self.anim_clock:
            self.anim_clock.cancel()
            self.anim_clock = None

    def _update_display(self, *args):
        """Обновляет отображение с поворотом на 270 градусов"""
        if not self.texture:
            return

        if self.width <= 0 or self.height <= 0:
            return

        self.canvas.clear()

        center_x = self.x + self.width / 2
        center_y = self.y + self.height / 2

        with self.canvas:
            # Поворачиваем изображение на 270 градусов по часовой стрелке
            PushMatrix()
            Translate(center_x, center_y)
            Rotate(angle=self.rotation_angle, origin=(0, 0))
            Translate(-center_x, -center_y)

            Color(1, 1, 1, 1)
            Rectangle(texture=self.texture, pos=self.pos, size=self.size)

            PopMatrix()

    def cleanup(self):
        """Полная очистка финальной монеты"""
        self.stop_animation()
        self.frames = []
        self.texture = None
        self.canvas.clear()


class CoinScreen(BaseGameScreen):
    """Игровой экран с монетой из спрайт-листов 12x9 (108 кадров)
       Упрощенная анимация: движение по спирали + вращение в центре + прокрутка всех кадров
    """

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self.background_image = 'assets/backgrounds/coin_bg.png'

        # Два спрайт-листа для основной анимации (108 кадров)
        self.spritesheet_path_1 = 'assets/sprites/coin_spritesheet_1.png'
        self.spritesheet_path_2 = 'assets/sprites/coin_spritesheet_2.png'

        # Два спрайт-листа для финальной анимации (36 кадров)
        self.final_spritesheet_orel = 'assets/sprites/orel_spritesheet.png'
        self.final_spritesheet_reshka = 'assets/sprites/reshka_spritesheet.png'

        # Статические изображения для начального состояния
        self.orel_image = 'assets/sprites/orel.png'
        self.reshka_image = 'assets/sprites/reshka.png'

        self.coin = None
        self.final_coin = None  # Для финальной анимации
        self.touch_area = None
        self.fullscreen_touch_area = None  # Область на весь экран для возврата
        self.info_label = None
        self.stats_label = None
        self.flip_sound = None  # Звук вращения монеты
        self.crystal_sound = None  # Звук для финальной анимации
        self.particle_system = None  # Система частиц
        self.return_animation_active = False  # Флаг для анимации возврата
        self.is_animating = False  # Флаг, указывающий, идет ли какая-либо анимация

        # Текущая сторона монеты (0 - орел, 1 - решка)
        self.current_side = 0

        self.total_flips = 0
        self.heads_count = 0
        self.tails_count = 0
        self.coin_start_frame = 0
        self.coin_start_side = 0

        # Высота монеты для расчета смещения (в пикселях)
        self.coin_height = 55
        self.final_coin_size = self.coin_height * 4  # Увеличение в 4 раза от начального (220px)

        # Начальное смещение тени (как в том файле)
        self.initial_shadow_offset = -self.coin_height * 0.97
        self.current_shadow_offset = self.initial_shadow_offset

        # Коэффициент уменьшения смещения тени (как в том файле)
        self.shadow_reduction_factor = 11

        # Параметры для движения по эллипсу
        self.ellipse_radius_x = 0.15
        self.ellipse_radius_y = 0.4
        self.start_offset_x = -0.15
        self.start_offset_y = 0

        # Смещение для финального этапа (четверть высоты монеты) - в пикселях
        # Отрицательное значение для смещения влево
        self.final_offset_x_pixels = -self.coin_height * 0.33

        # Стартовая позиция монеты (левая часть экрана)
        self.start_pos_x = 0.18
        self.start_pos_y = 0.5

        # Центр эллипса
        self.center_pos_x = 0.35
        self.center_pos_y = 0.5

        # Флаг отладки
        self.debug_mode = True

    def on_enter(self):
        """При входе на экран восстанавливаем начальное состояние монеты"""
        super().on_enter()

        # ПРИНУДИТЕЛЬНО ОТМЕНЯЕМ ВСЕ АНИМАЦИИ
        # Вместо Clock.unschedule() используем отмену конкретных анимаций

        # Пересоздаем UI при каждом входе
        self.setup_game_ui()
        self.load_flip_sound()
        self.load_crystal_sound()
        Window.bind(on_resize=self.on_window_resize)

        # Сбрасываем монету на стартовую позицию с первым кадром
        if self.coin:
            # Останавливаем все анимации
            self.coin.stop_animation()

            # Останавливаем все анимации Kivy, связанные с монетой
            Animation.cancel_all(self.coin)

            # Устанавливаем правильный спрайт-лист в зависимости от текущей стороны
            if self.current_side == 0:
                self.coin.load_spritesheet(self.spritesheet_path_1)
            else:
                self.coin.load_spritesheet(self.spritesheet_path_2)

            # Устанавливаем первый кадр
            if self.coin.frames and len(self.coin.frames) > 0:
                self.coin.texture = self.coin.frames[0]

            # Сбрасываем позицию на стартовую
            self.coin.pos_hint = {'center_x': self.start_pos_x, 'center_y': self.start_pos_y}
            self.coin.size = (self.coin_height, self.coin_height)
            self.coin.opacity = 1

            # Сбрасываем параметры тени на исходные
            self.coin.shadow_offset_x = 0
            self.coin.shadow_offset_y = self.initial_shadow_offset + self.coin_height * 0.13
            self.coin.shadow_scale_y = 1.0
            self.coin.shadow_alpha = 0.5

            # Сбрасываем параметры эллипса
            self.coin.ellipse_offset_x = -self.ellipse_radius_x
            self.coin.ellipse_offset_y = 0
            self.coin.spiral_factor = 1.0
            self.coin.extra_offset_x = 0

            # Принудительно обновляем позицию
            self.coin._update_position()
            self.coin._update_rotation()

        # Скрываем финальную монету
        if self.final_coin:
            self.final_coin.stop_animation()
            Animation.cancel_all(self.final_coin)
            self.final_coin.opacity = 0

        # Сбрасываем флаги
        self.is_animating = False
        self.return_animation_active = False

        # Отключаем полноэкранную область
        if self.fullscreen_touch_area:
            self.fullscreen_touch_area.is_enabled = False

        # Включаем основную область нажатия
        if self.touch_area:
            self.touch_area.is_enabled = True

        # Частицы уже запущены в __init__, просто устанавливаем обычный режим свечения
        if self.particle_system:
            self.particle_system.set_glow_mode(False)

    def on_leave(self):
        """При выходе с экрана полностью очищаем все анимации и виджеты"""
        super().on_leave()

        # Полная очистка всех виджетов и анимаций
        self.cleanup_all()

        Window.unbind(on_resize=self.on_window_resize)

    def cleanup_all(self):
        """Полная очистка всех ресурсов экрана"""
        # Останавливаем все анимации Kivy для всех виджетов
        if self.coin:
            Animation.cancel_all(self.coin)
        if self.final_coin:
            Animation.cancel_all(self.final_coin)
        if self.particle_system:
            Animation.cancel_all(self.particle_system)

        # Отменяем все запланированные события Clock
        # Вместо Clock.unschedule() без аргументов, отменяем конкретные функции
        # Но так как мы не храним ссылки на все lambda функции, просто пропускаем это
        # Анимации будут остановлены через Animation.cancel_all()

        # Останавливаем звуки
        self.stop_flip_sound()
        self.stop_crystal_sound()

        if self.flip_sound:
            self.flip_sound.unload()
            self.flip_sound = None

        if self.crystal_sound:
            self.crystal_sound.unload()
            self.crystal_sound = None

        # Очищаем монету
        if self.coin:
            self.coin.cleanup()
            if self.coin in self.layout.children:
                self.layout.remove_widget(self.coin)
            self.coin = None

        # Очищаем финальную монету
        if self.final_coin:
            self.final_coin.cleanup()
            if self.final_coin in self.layout.children:
                self.layout.remove_widget(self.final_coin)
            self.final_coin = None

        # Очищаем систему частиц
        if self.particle_system:
            self.particle_system.cleanup()
            if self.particle_system in self.layout.children:
                self.layout.remove_widget(self.particle_system)
            self.particle_system = None

        # Очищаем области касания
        if self.touch_area:
            if self.touch_area in self.layout.children:
                self.layout.remove_widget(self.touch_area)
            self.touch_area = None

        if self.fullscreen_touch_area:
            if self.fullscreen_touch_area in self.layout.children:
                self.layout.remove_widget(self.fullscreen_touch_area)
            self.fullscreen_touch_area = None

        # Сбрасываем флаги
        self.is_animating = False
        self.return_animation_active = False

    def on_window_resize(self, instance, width, height):
        if self.coin:
            Clock.schedule_once(lambda dt: self.coin._update_rotation(), 0.1)

    def check_file(self, path):
        if os.path.exists(path):
            return True
        else:
            return False

    def load_flip_sound(self):
        """Загружает звук для вращения монеты"""
        sound_path = 'assets/sounds/coin/coin_13s.ogg'

        if os.path.exists(sound_path):
            self.flip_sound = SoundLoader.load(sound_path)
            if self.flip_sound:
                self.flip_sound.volume = 0.7
        else:
            pass

    def load_crystal_sound(self):
        """Загружает звук для финальной анимации"""
        sound_path = 'assets/sounds/coin/crystal.ogg'

        if os.path.exists(sound_path):
            self.crystal_sound = SoundLoader.load(sound_path)
            if self.crystal_sound:
                self.crystal_sound.volume = 1.0
                print("✅ Загружен звук crystal.ogg")
        else:
            print("⚠️ Файл crystal.ogg не найден")

    def play_flip_sound(self):
        """Воспроизводит звук вращения монеты"""
        if self.flip_sound:
            try:
                if self.flip_sound.state == 'play':
                    self.flip_sound.stop()
                self.flip_sound.play()
            except Exception as e:
                pass

    def stop_flip_sound(self):
        """Останавливает звук вращения монеты"""
        if self.flip_sound and self.flip_sound.state == 'play':
            self.flip_sound.stop()

    def play_crystal_sound(self):
        """Воспроизводит звук для финальной анимации"""
        if self.crystal_sound:
            try:
                if self.crystal_sound.state == 'play':
                    self.crystal_sound.stop()
                self.crystal_sound.play()
                print("🔊 Воспроизводится crystal.ogg")
            except Exception as e:
                print(f"⚠️ Ошибка воспроизведения crystal.ogg: {e}")

    def stop_crystal_sound(self):
        """Останавливает звук финальной анимации"""
        if self.crystal_sound and self.crystal_sound.state == 'play':
            self.crystal_sound.stop()

    def setup_game_ui(self):
        # Проверяем наличие файлов
        self.check_file(self.spritesheet_path_1)
        self.check_file(self.spritesheet_path_2)
        self.check_file(self.final_spritesheet_orel)
        self.check_file(self.final_spritesheet_reshka)
        self.check_file(self.orel_image)
        self.check_file(self.reshka_image)

        a = 0.15
        center_x = 0.35
        image_shift = 0.02

        # Вычисляем стартовую позицию (левая часть экрана)
        self.start_pos_x = center_x - a - image_shift  # = 0.18

        # Размер монеты
        coin_size = 55
        self.coin_height = coin_size
        self.initial_shadow_offset = -self.coin_height * 0.97
        self.current_shadow_offset = self.initial_shadow_offset
        self.final_coin_size = self.coin_height * 4  # Увеличение в 4 раза

        # Смещение для финального этапа (отрицательное для смещения влево)
        self.final_offset_x_pixels = -self.coin_height * 0.33

        # Случайно выбираем начальную сторону монеты
        self.current_side = random.randint(0, 1)

        # Определяем начальный спрайт-лист и кадр
        if self.current_side == 0:
            # Орел - используем первый спрайт-лист, кадр 0
            self.coin_start_side = 0
            self.coin_start_frame = 0
            initial_spritesheet = self.spritesheet_path_1
        else:
            # Решка - используем второй спрайт-лист, кадр 0
            self.coin_start_side = 1
            self.coin_start_frame = 0
            initial_spritesheet = self.spritesheet_path_2

        # Перемещаем существующую кнопку меню в левый верхний угол
        if hasattr(self, 'menu_button') and self.menu_button:
            self.menu_button.pos_hint = {'x': 0.02, 'top': 0.98}
            self.menu_button.size_hint = (None, None)
            self.menu_button.size = (100, 50)

        # СОЗДАЕМ МОНЕТУ для основной анимации
        spritesheet_paths = {
            'heads': self.spritesheet_path_1,
            'tails': self.spritesheet_path_2
        }

        self.coin = SpritesheetCoin(
            spritesheet_paths=spritesheet_paths,
            frame_width=128,
            frame_height=128,
            cols=12,
            rows=9,
            total_frames=108,
            start_frame=self.coin_start_frame,
            rotation_angle=-90,
            size_hint=(None, None),
            size=(coin_size, coin_size),
            pos_hint={'center_x': self.start_pos_x, 'center_y': self.start_pos_y},
            allow_stretch=True,
            shadow_offset_x=0,
            shadow_offset_y=self.initial_shadow_offset + self.coin_height * 0.13,
            shadow_scale_y=1.0,
            shadow_alpha=0.5,
            coin_opacity=1.0,
            debug=self.debug_mode
        )

        # Загружаем начальный спрайт-лист
        self.coin.load_spritesheet(initial_spritesheet)

        # Явно устанавливаем первый кадр
        if self.coin.frames and len(self.coin.frames) > 0:
            self.coin.texture = self.coin.frames[0]

        # Устанавливаем начальное смещение эллипса (левая точка)
        self.coin.ellipse_offset_x = -self.ellipse_radius_x
        self.coin.ellipse_offset_y = 0
        self.coin.spiral_factor = 1.0

        self.layout.add_widget(self.coin)

        # СОЗДАЕМ МОНЕТУ для финальной анимации (изначально скрыта)
        self.final_coin = FinalSpritesheetCoin(
            spritesheet_path=self.final_spritesheet_orel,  # Временный путь, будет заменен при показе
            frame_width=128,
            frame_height=128,
            cols=6,
            rows=6,
            total_frames=36,
            start_frame=0,
            size_hint=(None, None),
            size=(self.final_coin_size, self.final_coin_size),
            pos_hint={'center_x': 0.5, 'center_y': 0.5},
            allow_stretch=True,
            opacity=0,  # Изначально скрыта
            debug=self.debug_mode
        )
        self.layout.add_widget(self.final_coin)

        # СОЗДАЕМ СИСТЕМУ ЧАСТИЦ (всегда активна)
        self.particle_system = ParticleSystem(num_particles=30)
        self.layout.add_widget(self.particle_system)

        # СОЗДАЕМ ОБЛАСТЬ НА ВЕСЬ ЭКРАН для возврата монеты (изначально скрыта)
        self.fullscreen_touch_area = FullScreenTouchArea()
        self.fullscreen_touch_area.is_enabled = False
        self.layout.add_widget(self.fullscreen_touch_area)
        self.fullscreen_touch_area.bind(on_touch_down=self.on_fullscreen_touch)

        # Область для нажатия (основная)
        self.touch_area = TouchArea(
            size_hint=(0.4, 0.4),
            pos_hint={'center_x': self.start_pos_x, 'center_y': self.start_pos_y},
        )
        self.layout.add_widget(self.touch_area)

        self.touch_area.bind(on_touch_down=self.on_area_touch)

    def on_fullscreen_touch(self, instance, touch):
        """Обработка нажатия на область всего экрана"""
        if instance.is_enabled and instance.collide_point(*touch.pos):
            self.return_coin_to_start()
            return True
        return False

    def create_spiral_animation(self, duration=8.0, rotations=3):
        """
        Создает анимацию движения по спирали от края эллипса к центру
        duration: длительность анимации
        rotations: количество полных оборотов
        """
        anim = Animation(duration=0)

        steps = 60
        step_duration = duration / steps

        start_angle = math.pi
        end_angle = start_angle + (2 * math.pi * rotations)

        for i in range(1, steps + 1):
            t = i / steps
            current_angle = start_angle + (end_angle - start_angle) * t
            x_offset = self.ellipse_radius_x * math.cos(current_angle)
            y_offset = self.ellipse_radius_y * math.sin(current_angle)
            spiral_factor = 1.0 - t

            step_anim = Animation(
                ellipse_offset_x=x_offset,
                ellipse_offset_y=y_offset,
                spiral_factor=spiral_factor,
                duration=step_duration,
                t='linear'
            )
            anim += step_anim

        return anim

    def on_area_touch(self, instance, touch):
        if instance.collide_point(*touch.pos):
            # Если сейчас идет какая-либо анимация, блокируем действие
            if self.is_animating:
                return True

            # Если финальная монета видна и анимация завершена, запускаем возврат
            if self.final_coin and self.final_coin.opacity == 1 and not self.final_coin.is_animating:
                self.return_coin_to_start()
                return True
            # Иначе запускаем обычное вращение
            elif not self.coin.is_animating and not self.final_coin.is_animating:
                self.flip_coin()
                return True
        return False

    def set_animating_state(self, animating):
        """Устанавливает состояние анимации и блокирует/разблокирует touch_area"""
        self.is_animating = animating
        if self.touch_area:
            self.touch_area.is_enabled = not animating

    def flip_coin(self):
        if self.coin.is_animating:
            return

        # Блокируем нажатия во время анимации
        self.set_animating_state(True)
        # Отключаем полноэкранную область
        if self.fullscreen_touch_area:
            self.fullscreen_touch_area.is_enabled = False

        # Скрываем финальную монету если она была видна
        if self.final_coin:
            self.final_coin.stop_animation()
            self.final_coin.opacity = 0

        # Воспроизводим звук вращения
        self.play_flip_sound()

        # Включаем режим яркого свечения частиц (они уже движутся, просто становятся ярче)
        if self.particle_system:
            self.particle_system.set_glow_mode(True)

        # Определяем случайный результат
        result = random.randint(0, 1)

        # Выбираем спрайт-лист в зависимости от результата
        if result == 0:
            # Орел - используем первый спрайт-лист
            spritesheet_to_use = self.spritesheet_path_1
            self.heads_count += 1
        else:
            # Решка - используем второй спрайт-лист
            spritesheet_to_use = self.spritesheet_path_2
            self.tails_count += 1

        self.total_flips += 1

        # Загружаем нужный спрайт-лист
        self.coin.load_spritesheet(spritesheet_to_use)

        # Сбрасываем монету
        self.coin.reset_to_first_animation(0)  # Всегда начинаем с кадра 0
        self.coin.shadow_offset_y = self.initial_shadow_offset
        self.current_shadow_offset = self.initial_shadow_offset

        # Устанавливаем начальную позицию на эллипсе
        self.coin.ellipse_offset_x = -self.ellipse_radius_x
        self.coin.ellipse_offset_y = 0
        self.coin.spiral_factor = 1.0

        # Сбрасываем дополнительное смещение
        self.coin.extra_offset_x = 0

        # НАСТРОЙКИ АНИМАЦИИ
        base_fps = 40
        base_frame_step = 1  # Без пропуска кадров для плавности

        # Длительности этапов
        spiral_duration = 8.0  # Движение по спирали
        center_rotation_duration = 2.0  # Вращение в центре (первые 12 кадров)
        rotations = 3  # Количество оборотов во время движения

        # ЭТАП 1: Движение по спирали с анимацией первых 12 кадров
        self.coin.set_animation_range(0, 11)
        self.coin.start_animation(
            fps=base_fps,
            frame_step=base_frame_step
        )

        # Запускаем анимацию движения по спирали
        spiral_anim = self.create_spiral_animation(spiral_duration, rotations)

        def on_spiral_complete(animation, coin):
            # Проверяем, что монета все еще существует и экран активен
            if self.coin is not None and not self.return_animation_active:
                self.start_center_rotation(result, base_fps, base_frame_step,
                                           center_rotation_duration)

        spiral_anim.bind(on_complete=on_spiral_complete)
        spiral_anim.start(self.coin)

    def start_center_rotation(self, result, fps, frame_step, duration):
        """
        Этап 2: Вращение в центре (первые 12 кадров)
        """
        # Проверяем, что монета все еще существует
        if self.coin is None:
            return

        # Убеждаемся, что монета в центре
        self.coin.spiral_factor = 0

        # Продолжаем анимацию первых 12 кадров
        self.coin.set_animation_range(0, 11)
        self.coin.start_animation(
            fps=fps,
            frame_step=frame_step
        )

        # Через указанное время переходим к финальной прокрутке всех кадров со смещением
        Clock.schedule_once(lambda dt: self.start_final_rotation_with_offset(result, fps, frame_step)
        if self.coin is not None and not self.return_animation_active else None,
                            duration)

    def start_final_rotation_with_offset(self, result, fps, frame_step):
        """
        Этап 3: Финальная прокрутка всех кадров (12-107) с одновременным смещением влево
        """
        # Проверяем, что монета все еще существует
        if self.coin is None:
            return

        self.coin.stop_animation()

        # Устанавливаем диапазон от 12 до 107 (все оставшиеся кадры)
        self.coin.set_animation_range(12, 107)

        # Рассчитываем время на прокрутку всех кадров
        frames_to_play = 96  # 107 - 12 + 1 = 96 кадров
        frame_duration = 1.0 / fps
        total_duration = frames_to_play * frame_duration

        # Устанавливаем начальный кадр
        self.coin.current_frame = 12
        self.coin.texture = self.coin.frames[12]

        # Создаем анимацию смещения влево
        offset_anim = Animation(
            extra_offset_x=self.final_offset_x_pixels,
            duration=total_duration,
            t='linear'
        )

        # Создаем анимацию для тени (постепенно поднимаем тень вверх)
        # Рассчитываем конечное смещение тени (поднимем на 30% от начального смещения)
        target_shadow_offset = self.initial_shadow_offset * 0.1  # Тень поднимается на 30%

        shadow_anim = Animation(
            shadow_offset_y=target_shadow_offset,
            duration=total_duration,
            t='linear'
        )

        # Запускаем анимацию кадров через Clock.schedule_interval
        self.coin.is_animating = True

        def update_frame(dt):
            if not self.coin.is_animating or self.coin is None:
                return False

            # Переходим к следующему кадру
            next_frame = self.coin.current_frame + 1

            # Проверяем, не дошли ли до конца
            if next_frame > 107:  # Последний кадр для прокрутки
                self.coin.is_animating = False
                self.finish_rotation(result)
                return False

            # Устанавливаем следующий кадр
            self.coin.current_frame = next_frame
            self.coin.texture = self.coin.frames[next_frame]
            self.coin._update_rotation()

            return True  # Продолжаем анимацию

        # Запускаем периодическое обновление кадров
        frame_interval = 1.0 / fps
        Clock.schedule_interval(update_frame, frame_interval)

        def on_anim_complete(animation, coin):
            pass

        # Запускаем анимации
        offset_anim.bind(on_complete=on_anim_complete)
        offset_anim.start(self.coin)
        shadow_anim.start(self.coin)

        # Страховка - если кадры почему-то не закончились вовремя
        Clock.schedule_once(lambda dt: self.finish_rotation(result)
        if self.coin is not None and self.coin.is_animating else None,
                            total_duration + 0.1)

    def finish_rotation(self, result):
        """Этап 4: Показ результата с паузой 2 секунды и запуск финальной анимации"""
        # Проверяем, что монета все еще существует
        if self.coin is None:
            return

        # Полностью останавливаем анимацию основной монеты
        if self.coin:
            self.coin.stop_animation()
            # Оставляем монету видимой на время паузы
            self.coin.opacity = 1

        # Запускаем финальную анимацию с задержкой 2 секунды
        Clock.schedule_once(lambda dt: self.start_final_animation(result)
        if self.coin is not None and not self.return_animation_active else None,
                            2.0)

    def start_final_animation(self, result):
        """Запускает финальную анимацию с увеличением и выходом в центр"""
        # Проверяем, что финальная монета все еще существует
        if self.final_coin is None:
            return

        # Скрываем основную монету
        if self.coin:
            self.coin.opacity = 0

        # Запускаем звук crystal.ogg с задержкой 1 секунда
        Clock.schedule_once(lambda dt: self.play_crystal_sound(), 1.5)

        # Выбираем нужный спрайт-лист в зависимости от результата
        if result == 0:
            final_spritesheet = self.final_spritesheet_orel
        else:
            final_spritesheet = self.final_spritesheet_reshka

        # Загружаем спрайт-лист в финальную монету
        self.final_coin.load_spritesheet(final_spritesheet)

        # Убеждаемся, что final_coin_size правильно вычислен (в 4 раза больше)
        target_size = self.coin_height * 4  # Увеличение в 4 раза (55px -> 220px)

        # Устанавливаем начальные параметры - СТАРТ ИЗ ЦЕНТРА ЭЛЛИПСА!
        self.final_coin.opacity = 1
        self.final_coin.size = (self.coin_height, self.coin_height)  # Начинаем с размера основной монеты
        self.final_coin.pos_hint = {'center_x': self.center_pos_x,
                                    'center_y': self.center_pos_y}  # Старт из центра эллипса (0.35, 0.5)

        # Принудительно обновляем позицию и размер
        self.final_coin.pos = self.final_coin.pos
        self.final_coin.size = self.final_coin.size

        # Длительность анимации
        animation_duration = 1.5  # 1.5 секунды

        # Запускаем анимацию кадров с правильным FPS для синхронизации
        # 36 кадров за animation_duration секунд = 36 / animation_duration FPS
        frame_fps = 36 / animation_duration  # 36 / 1.5 = 24 FPS
        self.final_coin.start_animation(fps=frame_fps, loop=False)

        # Создаем анимацию увеличения и перемещения в центр экрана
        # Используем линейную интерполяцию для равномерного увеличения
        grow_anim = Animation(
            size=(target_size, target_size),  # Увеличение в 4 раза
            pos_hint={'center_x': 0.5, 'center_y': 0.5},  # Перемещение в центр экрана
            duration=animation_duration,
            t='linear'  # Линейная интерполяция для равномерного увеличения
        )

        def on_grow_complete(animation, coin):
            # Проверяем, что объекты все еще существуют
            if self.particle_system:
                self.particle_system.set_glow_mode(False)
            # Разблокируем нажатия после завершения всей анимации
            self.set_animating_state(False)
            # Включаем полноэкранную область для возврата монеты
            if self.fullscreen_touch_area:
                self.fullscreen_touch_area.is_enabled = True

        grow_anim.bind(on_complete=on_grow_complete)
        grow_anim.start(self.final_coin)

        # Останавливаем звук вращения, если он еще играет
        self.stop_flip_sound()

        # Обновляем текущую сторону для следующего раза
        self.current_side = result

    def return_coin_to_start(self):
        """Возвращает монету в исходное положение"""
        # Блокируем нажатия во время анимации возврата
        self.set_animating_state(True)
        # Отключаем полноэкранную область
        if self.fullscreen_touch_area:
            self.fullscreen_touch_area.is_enabled = False
        self.return_animation_active = True

        # Останавливаем звук crystal.ogg
        self.stop_crystal_sound()

        # Останавливаем анимацию финальной монеты
        if self.final_coin:
            self.final_coin.stop_animation()
            self.final_coin.opacity = 0  # Скрываем финальную монету

        # Показываем основную монету с правильной стороной
        if self.coin:
            self.coin.opacity = 1
            # Загружаем правильный спрайт-лист в зависимости от результата
            if self.current_side == 0:
                self.coin.load_spritesheet(self.spritesheet_path_1)
            else:
                self.coin.load_spritesheet(self.spritesheet_path_2)

            # Устанавливаем ПЕРВЫЙ КАДР (индекс 0) для показа результата
            if self.coin.frames and len(self.coin.frames) > 0:
                self.coin.texture = self.coin.frames[0]

            # Сбрасываем параметры тени на исходные значения
            self.coin.shadow_offset_x = 0
            self.coin.shadow_offset_y = self.initial_shadow_offset + self.coin_height * 0.13
            self.coin.shadow_scale_y = 1.0
            self.coin.shadow_alpha = 0.5

            # Устанавливаем начальную позицию для анимации возврата - ИЗ ЦЕНТРА ЭКРАНА
            self.coin.pos_hint = {'center_x': 0.5, 'center_y': 0.5}
            self.coin.size = (self.final_coin_size, self.final_coin_size)  # Начинаем с большого размера

        # Создаем анимацию уменьшения и возврата на стартовую позицию
        return_anim = Animation(
            size=(self.coin_height, self.coin_height),  # Уменьшаем до исходного размера
            pos_hint={'center_x': self.start_pos_x, 'center_y': self.start_pos_y},
            # Возвращаем на стартовую позицию (0.18, 0.5)
            duration=1.2,
            t='out_quad'  # Плавная анимация
        )

        def on_return_complete(animation, coin):
            self.return_animation_active = False
            # Разблокируем нажатия
            self.set_animating_state(False)

        return_anim.bind(on_complete=on_return_complete)
        return_anim.start(self.coin)

    def go_to_menu(self):
        """Возврат в меню с полной остановкой всех анимаций"""
        # Полная очистка всех ресурсов
        self.cleanup_all()

        # Вызываем метод родительского класса для перехода в меню
        super().go_to_menu()