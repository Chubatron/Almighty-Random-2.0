from kivy.uix.image import Image
from kivy.uix.widget import Widget
from kivy.animation import Animation
from kivy.clock import Clock
from kivy.properties import NumericProperty, BooleanProperty, ColorProperty, ListProperty, StringProperty
from kivy.core.window import Window
from kivy.core.image import Image as CoreImage
from kivy.core.audio import SoundLoader
from kivy.graphics import Color, Ellipse, Rectangle, Line, PushMatrix, PopMatrix, Rotate, Translate, \
    Scale
import random
import os
import math

from screens.base_game_screen import BaseGameScreen


class TouchArea(Widget):
    """Область для нажатия с визуальной подсветкой"""
    highlight_color = ColorProperty((0, 1, 0, 0.3))
    is_pressed = BooleanProperty(False)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.touch_pos = (0, 0)
        self.bind(pos=self._update_rect, size=self._update_rect)

    def on_touch_down(self, touch):
        if self.collide_point(*touch.pos):
            self.is_pressed = True
            self.touch_pos = touch.pos
            self.show_touch_feedback()
            print(f"🟢 Нажатие в области: {touch.pos}")
            return True
        return super().on_touch_down(touch)

    def on_touch_up(self, touch):
        if self.collide_point(*touch.pos):
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

        print(f"🔧 SpritesheetCoin __init__: загрузка спрайт-листов")

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
            print(f"❌ Файл не найден: {spritesheet_path}")
            return False

        try:
            img = CoreImage(spritesheet_path)
            texture = img.texture
            if not texture:
                print("❌ Не удалось загрузить текстуру")
                return False

            tex_width, tex_height = texture.size
            print(f"📐 Размер спрайт-листа {spritesheet_path}: {tex_width}x{tex_height}")

            frame_w = min(self.frame_width, tex_width // self.cols)
            frame_h = min(self.frame_height, tex_height // self.rows)
            print(f"🖼️ Размер кадра: {frame_w}x{frame_h} (сетка {self.cols}x{self.rows})")

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
                    print(f"❌ Ошибка кадра {i}: {e}")

            print(f"✅ Загружено кадров: {len(frames)} из {self.total_frames}")

            self.frames = frames
            self.current_spritesheet = spritesheet_path

            if self.frames and 0 <= self.start_frame < len(self.frames):
                self.texture = self.frames[self.start_frame]

            return True

        except Exception as e:
            print(f"❌ Ошибка загрузки спрайт-листа: {e}")
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
        print(f"🎯 Установлен диапазон анимации: {start_frame}-{end_frame} (всего {end_frame - start_frame + 1} кадров)")

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

        effective_speed = fps * self.frame_step
        print(
            f"🎬 Анимация запущена с FPS: {fps}, шаг пропуска: {self.frame_step}, эффективная скорость: {effective_speed} кадров/сек, диапазон: {self.animation_range[0]}-{self.animation_range[1]}")

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
            if self.debug_mode:
                print(f"🔄 Цикл анимации: возврат к началу диапазона, новый кадр: {next_frame + 1}")

        # Проверяем, не вышли ли мы за нижнюю границу (при отрицательном шаге)
        elif next_frame < self.animation_range[0]:
            range_size = self.animation_range[1] - self.animation_range[0] + 1
            next_frame = self.animation_range[1] - ((self.animation_range[1] - next_frame) % range_size)
            if self.debug_mode:
                print(f"🔄 Цикл анимации: возврат к концу диапазона, новый кадр: {next_frame + 1}")

        # Убеждаемся, что кадр в допустимом диапазоне
        next_frame = max(self.animation_range[0], min(next_frame, self.animation_range[1]))

        self.current_frame = next_frame
        self.texture = self.frames[self.current_frame]

        # Выводим номер текущего кадра для отладки
        if self.debug_mode:
            print(
                f"🎞️ Кадр: {self.current_frame + 1}/{len(self.frames)} (диапазон: {self.animation_range[0] + 1}-{self.animation_range[1] + 1})")

        self._update_rotation()

    def stop_animation(self):
        """Останавливает анимацию"""
        self.is_animating = False

        if self.anim_clock:
            self.anim_clock.cancel()
            self.anim_clock = None

        if self.debug_mode:
            print("⏹️ Анимация остановлена")

    def set_result(self, result):
        """Устанавливает финальный кадр - ВСЕГДА последний кадр (108-й) независимо от результата"""
        if not self.frames:
            return

        # Останавливаем анимацию
        self.stop_animation()

        # Всегда показываем последний кадр (индекс 107 - это 108-й кадр)
        frame_index = 107  # 108-й кадр

        print(
            f"🎲 Результат: {'ОРЕЛ' if result == 0 else 'РЕШКА'}, финальный кадр: {frame_index + 1} (всегда последний)")

        # Устанавливаем текстуру
        self.texture = self.frames[frame_index]

        # Принудительно очищаем canvas и рисуем заново
        self.canvas.clear()
        Clock.schedule_once(lambda dt: self._force_redraw(), 0.01)

    def _force_redraw(self):
        """Принудительная перерисовка с полной очисткой"""
        self._updating = False
        self._update_rotation()
        if self.debug_mode:
            print("🔄 Принудительная перерисовка")

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
            print(f"🎬 Сброс к первым 12 кадрам, кадр: {start_frame + 1}")

        # Обновляем отображение с задержкой
        Clock.schedule_once(lambda dt: self._update_rotation(), 0.02)


class CoinScreen(BaseGameScreen):
    """Игровой экран с монетой из спрайт-листов 12x9 (108 кадров)
       Упрощенная анимация: движение по спирали + вращение в центре + прокрутка всех кадров
    """

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self.background_image = 'assets/backgrounds/coin_bg.png'

        # Два спрайт-листа
        self.spritesheet_path_1 = 'assets/sprites/coin_spritesheet_1.png'
        self.spritesheet_path_2 = 'assets/sprites/coin_spritesheet_2.png'

        # Статические изображения для начального состояния
        self.orel_image = 'assets/sprites/orel.png'
        self.reshka_image = 'assets/sprites/reshka.png'

        self.coin = None
        self.touch_area = None
        self.info_label = None
        self.stats_label = None
        self.flip_sound = None

        # Текущая сторона монеты (0 - орел, 1 - решка)
        self.current_side = 0

        self.total_flips = 0
        self.heads_count = 0
        self.tails_count = 0
        self.coin_start_frame = 0
        self.coin_start_side = 0

        # Высота монеты для расчета смещения (в пикселях)
        self.coin_height = 55

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

        # Флаг отладки
        self.debug_mode = True

    def on_enter(self):
        super().on_enter()
        self.setup_game_ui()
        self.load_flip_sound()
        Window.bind(on_resize=self.on_window_resize)

    def on_leave(self):
        super().on_leave()
        if self.coin:
            self.coin.stop_animation()
        if self.flip_sound and self.flip_sound.state == 'play':
            self.flip_sound.stop()
        Window.unbind(on_resize=self.on_window_resize)

    def on_window_resize(self, instance, width, height):
        if self.coin:
            Clock.schedule_once(lambda dt: self.coin._update_rotation(), 0.1)

    def check_file(self, path):
        if os.path.exists(path):
            print(f"✅ Файл найден: {path}")
            return True
        else:
            print(f"❌ Файл НЕ найден: {path}")
            return False

    def load_flip_sound(self):
        """Загружает звук для вращения монеты"""
        sound_path = 'assets/sounds/coin/coin_10s.ogg'

        if os.path.exists(sound_path):
            self.flip_sound = SoundLoader.load(sound_path)
            if self.flip_sound:
                self.flip_sound.volume = 0.7
                print(f"✅ Loaded flip sound: {sound_path}")
            else:
                print(f"⚠️ Failed to load flip sound: {sound_path}")
        else:
            print(f"⚠️ Flip sound file not found: {sound_path}")

    def play_flip_sound(self):
        """Воспроизводит звук вращения монеты"""
        if self.flip_sound:
            try:
                if self.flip_sound.state == 'play':
                    self.flip_sound.stop()
                self.flip_sound.play()
                print("🔊 Playing flip sound")
            except Exception as e:
                print(f"⚠️ Error playing flip sound: {e}")

    def stop_flip_sound(self):
        """Останавливает звук вращения монеты"""
        if self.flip_sound and self.flip_sound.state == 'play':
            self.flip_sound.stop()
            print("🔇 Flip sound stopped")

    def setup_game_ui(self):
        # Проверяем наличие файлов
        self.check_file(self.spritesheet_path_1)
        self.check_file(self.spritesheet_path_2)
        self.check_file(self.orel_image)
        self.check_file(self.reshka_image)

        a = 0.15
        center_x = 0.35
        image_shift = 0.02

        # Размер монеты
        coin_size = 55
        self.coin_height = coin_size
        self.initial_shadow_offset = -self.coin_height * 0.97
        self.current_shadow_offset = self.initial_shadow_offset

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
            print(f"🎲 Начальная сторона: ОРЕЛ, спрайт-лист: 1, кадр: 1")
        else:
            # Решка - используем второй спрайт-лист, кадр 0
            self.coin_start_side = 1
            self.coin_start_frame = 0
            initial_spritesheet = self.spritesheet_path_2
            print(f"🎲 Начальная сторона: РЕШКА, спрайт-лист: 2, кадр: 1")

        # СОЗДАЕМ МОНЕТУ - убираем дополнительное смещение тени
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
            pos_hint={'center_x': center_x - a - image_shift, 'center_y': 0.5},
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

        # Устанавливаем начальное смещение эллипса (левая точка)
        self.coin.ellipse_offset_x = -self.ellipse_radius_x
        self.coin.ellipse_offset_y = 0
        self.coin.spiral_factor = 1.0

        self.layout.add_widget(self.coin)

        # Область для нажатия
        self.touch_area = TouchArea(
            size_hint=(0.4, 0.4),
            pos_hint={'center_x': center_x - a - image_shift, 'center_y': 0.5},
        )
        self.layout.add_widget(self.touch_area)

        self.touch_area.bind(on_touch_down=self.on_area_touch)

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
            self.flip_coin()
            return True
        return False

    def flip_coin(self):
        if self.coin.is_animating:
            print("⏳ Монета уже вращается...")
            return

        # Воспроизводим звук вращения
        self.play_flip_sound()

        # Определяем случайный результат
        result = random.randint(0, 1)

        # Выбираем спрайт-лист в зависимости от результата
        if result == 0:
            # Орел - используем первый спрайт-лист
            spritesheet_to_use = self.spritesheet_path_1
            result_text = 'ОРЕЛ'
            self.heads_count += 1
        else:
            # Решка - используем второй спрайт-лист
            spritesheet_to_use = self.spritesheet_path_2
            result_text = 'РЕШКА'
            self.tails_count += 1

        self.total_flips += 1

        print(f"\n🎲 Результат: {result_text}, используем спрайт-лист: {spritesheet_to_use}")

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

        print(f"\n=== УПРОЩЕННАЯ АНИМАЦИЯ (спрайт-лист 12x9) ===")
        print(f"1. Движение по спирали к центру: {spiral_duration} сек")
        print(f"   Анимация: первые 12 кадров (0-11)")
        print(f"2. Вращение в центре: {center_rotation_duration} сек")
        print(f"   Анимация: первые 12 кадров (0-11)")
        print(f"3. Финальная прокрутка всех кадров со смещением (12-107)")
        print(f"   Всего кадров: 96 (12-107)")
        print(f"   Смещение влево: {abs(self.final_offset_x_pixels)} пикселей")
        print(f"   Начальное смещение тени: {self.current_shadow_offset:.2f}px")

        # ЭТАП 1: Движение по спирали с анимацией первых 12 кадров
        print("🎬 ЭТАП 1: Движение по спирали (первые 12 кадров)")
        self.coin.set_animation_range(0, 11)
        self.coin.start_animation(
            fps=base_fps,
            frame_step=base_frame_step
        )

        # Запускаем анимацию движения по спирали
        spiral_anim = self.create_spiral_animation(spiral_duration, rotations)

        def on_spiral_complete(animation, coin):
            print("✅ Спираль завершена, начинаем вращение в центре")
            self.start_center_rotation(result, base_fps, base_frame_step,
                                       center_rotation_duration)

        spiral_anim.bind(on_complete=on_spiral_complete)
        spiral_anim.start(self.coin)

    def start_center_rotation(self, result, fps, frame_step, duration):
        """
        Этап 2: Вращение в центре (первые 12 кадров)
        """
        print(f"⏱️ ЭТАП 2: Вращение в центре - {duration} сек (первые 12 кадров)")
        print(f"   Текущее смещение тени: {self.current_shadow_offset:.2f}px")

        # Убеждаемся, что монета в центре
        self.coin.spiral_factor = 0

        # Продолжаем анимацию первых 12 кадров
        self.coin.set_animation_range(0, 11)
        self.coin.start_animation(
            fps=fps,
            frame_step=frame_step
        )

        # Через указанное время переходим к финальной прокрутке всех кадров со смещением
        Clock.schedule_once(lambda dt: self.start_final_rotation_with_offset(result, fps, frame_step), duration)

    def start_final_rotation_with_offset(self, result, fps, frame_step):
        """
        Этап 3: Финальная прокрутка всех кадров (12-107) с одновременным смещением влево
        """
        print("⏱️ ЭТАП 3: Финальная прокрутка всех кадров со смещением влево (12-107)")

        self.coin.stop_animation()

        # Устанавливаем диапазон от 12 до 107 (все оставшиеся кадры)
        self.coin.set_animation_range(12, 107)

        # Рассчитываем время на прокрутку всех кадров
        frames_to_play = 96  # 107 - 12 + 1 = 96 кадров
        frame_duration = 1.0 / fps
        total_duration = frames_to_play * frame_duration

        print(f"   Кадров для прокрутки: {frames_to_play}")
        print(f"   Время прокрутки: {total_duration:.2f} сек")
        print(f"   Смещение влево: {abs(self.final_offset_x_pixels)} пикселей")
        print(f"   Начальное смещение тени: {self.current_shadow_offset:.2f}px")

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
            if not self.coin.is_animating:
                return False

            # Переходим к следующему кадру
            next_frame = self.coin.current_frame + 1

            # Проверяем, не дошли ли до конца
            if next_frame > 107:  # Последний кадр для прокрутки
                print(f"✅ Достигнут 108 кадр, останавливаем анимацию")
                self.coin.is_animating = False
                self.finish_rotation(result)
                return False

            # Устанавливаем следующий кадр
            self.coin.current_frame = next_frame
            self.coin.texture = self.coin.frames[next_frame]
            self.coin._update_rotation()

            if self.debug_mode:
                print(f"🎞️ Кадр: {next_frame + 1}/108, тень: {self.coin.shadow_offset_y:.2f}px")

            return True  # Продолжаем анимацию

        # Запускаем периодическое обновление кадров
        frame_interval = 1.0 / fps
        Clock.schedule_interval(update_frame, frame_interval)

        def on_anim_complete(animation, coin):
            print("✅ Анимации смещения и тени завершены")

        # Запускаем анимации
        offset_anim.bind(on_complete=on_anim_complete)
        offset_anim.start(self.coin)
        shadow_anim.start(self.coin)

        # Страховка - если кадры почему-то не закончились вовремя
        Clock.schedule_once(lambda dt: self.finish_rotation(result) if self.coin.is_animating else None,
                            total_duration + 0.1)

    def finish_rotation(self, result):
        """Этап 4: Показ результата"""
        print("⏱️ ЭТАП 4: Показ результата")

        # Полностью останавливаем анимацию
        if self.coin:
            self.coin.stop_animation()

            # Принудительно очищаем canvas
            self.coin.canvas.clear()

            # Сбрасываем флаг обновления
            self.coin._updating = False

        # Устанавливаем результат
        self._show_result(result)

    def _show_result(self, result):
        """Внутренний метод для показа результата без артефактов"""
        if self.coin:
            # Устанавливаем результат
            self.coin.set_result(result)

        self.stop_flip_sound()

        # Обновляем текущую сторону для следующего раза
        self.current_side = result

    def go_to_menu(self):
        if self.coin:
            self.coin.stop_animation()
        self.stop_flip_sound()
        super().go_to_menu()