from kivy.uix.screenmanager import Screen
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.image import Image
from kivy.uix.label import Label
from kivy.uix.widget import Widget
from kivy.animation import Animation
from kivy.clock import Clock
from kivy.properties import NumericProperty, BooleanProperty, ColorProperty, ListProperty
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
    """Монета из единого спрайт-листа 10x10 (96 кадров, 4 блока по 24 кадра)"""
    current_frame = NumericProperty(0)
    is_animating = BooleanProperty(False)
    frames = ListProperty([])
    rotation_angle = NumericProperty(-90)  # Поворот против часовой стрелки

    # Флаг для зеркального отображения монеты
    coin_mirror = NumericProperty(1)

    # Диапазон кадров для текущей анимации [start, end]
    animation_range = ListProperty([0, 23])  # По умолчанию первые 24 кадра

    # Свойства для позиции на эллипсе
    ellipse_offset_x = NumericProperty(0)
    ellipse_offset_y = NumericProperty(0)

    # Дополнительное смещение для позиционирования монеты (в пикселях)
    extra_offset_x = NumericProperty(0)
    extra_offset_y = NumericProperty(0)

    # Параметры тени - теперь они будут использоваться в отрисовке!
    shadow_offset_x = NumericProperty(0)
    shadow_offset_y = NumericProperty(0)
    shadow_scale_y = NumericProperty(1)
    shadow_alpha = NumericProperty(0.6)

    # Номер текущего блока спрайт-листа (1-4)
    current_block = NumericProperty(1)

    # Шаг пропуска кадров (1 - все кадры, 2 - каждый второй, 3 - каждый третий и т.д.)
    frame_step = NumericProperty(1)

    # Флаг для режима множественных копий (несколько кадров в одном месте)
    multi_copy_mode = BooleanProperty(False)
    copy_count = NumericProperty(4)  # Количество копий (4)
    copy_opacity = NumericProperty(0.4)  # Прозрачность ВСЕХ копий
    frame_history = ListProperty([])  # История кадров для множественных копий

    # Спиральный фактор (уменьшение радиуса)
    spiral_factor = NumericProperty(1.0)

    # Параметры смещения для разных блоков
    block_offset = NumericProperty(0)  # Текущее смещение для блока
    target_offset = NumericProperty(0)  # Целевое смещение для блока
    previous_offset = NumericProperty(0)  # Предыдущее смещение

    # Ссылка на вторую монету (для синхронизации)
    secondary_coin = None

    # Прозрачность монеты
    coin_opacity = NumericProperty(1.0)

    def __init__(self, spritesheet_path, frame_width=64, frame_height=64,
                 cols=10, rows=10, total_frames=96, frames_per_block=24, start_frame=0,
                 shadow_offset_x=0, shadow_offset_y=0,
                 shadow_scale_y=1.0, shadow_alpha=0.6, coin_opacity=1.0, **kwargs):
        super().__init__(**kwargs)

        self.frame_width = frame_width
        self.frame_height = frame_height
        self.cols = cols
        self.rows = rows
        self.total_frames = total_frames
        self.frames_per_block = frames_per_block
        self.start_frame = start_frame
        self.anim_clock = None
        self.current_fps = 60
        self.spritesheet_path = spritesheet_path
        self.frame_step = 1
        self.multi_copy_mode = False
        self.copy_count = 4
        self.copy_opacity = 0.4
        self.frame_history = []
        self.spiral_factor = 1.0
        self.block_offset = 0
        self.target_offset = 0
        self.previous_offset = 0
        self.coin_opacity = coin_opacity

        # Устанавливаем параметры тени
        self.shadow_offset_x = shadow_offset_x
        self.shadow_offset_y = shadow_offset_y
        self.shadow_scale_y = shadow_scale_y
        self.shadow_alpha = shadow_alpha

        print(f"🔧 SpritesheetCoin __init__: загрузка спрайт-листа {spritesheet_path}")

        # Загружаем спрайт-лист
        self.load_spritesheet()

        # Устанавливаем начальный диапазон (первые 24 кадра - блок 1)
        self.set_animation_range(0, 23, block_num=1)

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
        self.bind(current_frame=self._update_block_offset)  # Добавляем привязку для обновления смещения
        self.bind(coin_opacity=self._update_rotation)

        # ВАЖНО: Привязываем свойства тени к обновлению отрисовки
        self.bind(shadow_offset_x=self._update_rotation,
                  shadow_offset_y=self._update_rotation,
                  shadow_scale_y=self._update_rotation,
                  shadow_alpha=self._update_rotation)

    def load_spritesheet(self):
        """Загружает единый спрайт-лист 10x10 (96 кадров)"""
        if not os.path.exists(self.spritesheet_path):
            print(f"❌ Файл не найден: {self.spritesheet_path}")
            return

        try:
            img = CoreImage(self.spritesheet_path)
            texture = img.texture
            if not texture:
                print("❌ Не удалось загрузить текстуру")
                return

            tex_width, tex_height = texture.size
            print(f"📐 Размер спрайт-листа: {tex_width}x{tex_height}")

            frame_w = min(self.frame_width, tex_width // self.cols)
            frame_h = min(self.frame_height, tex_height // self.rows)
            print(f"🖼️ Размер кадра: {frame_w}x{frame_h} (сетка {self.cols}x{self.rows})")

            self.frames = []
            for i in range(self.total_frames):
                row = i // self.cols
                col = i % self.cols
                x = col * frame_w
                y = (self.rows - 1 - row) * frame_h
                try:
                    frame = texture.get_region(x, y, frame_w, frame_h)
                    self.frames.append(frame)
                except Exception as e:
                    print(f"❌ Ошибка кадра {i}: {e}")

            print(f"✅ Загружено кадров: {len(self.frames)} из {self.total_frames}")
            print(f"📊 Блоки: 1: 0-23, 2: 24-47, 3: 48-71, 4: 72-95")

            if self.frames:
                if 0 <= self.start_frame < len(self.frames):
                    self.texture = self.frames[self.start_frame]
                    print(f"🎬 Начальный кадр: {self.start_frame + 1}")
                else:
                    self.texture = self.frames[0]
                    print(f"🎬 Начальный кадр (по умолчанию): 1")

                Clock.schedule_once(lambda dt: self._update_rotation(), 0.1)
                Clock.schedule_once(lambda dt: self._update_position(), 0.1)

        except Exception as e:
            print(f"❌ Ошибка загрузки спрайт-листа: {e}")

    def set_secondary_coin(self, coin):
        """Устанавливает ссылку на вторую монету для синхронизации"""
        self.secondary_coin = coin

    def set_animation_range(self, start_frame, end_frame, mirror_coin=False, block_num=1):
        """Устанавливает диапазон кадров для анимации"""
        self.animation_range = [start_frame, end_frame]
        self.coin_mirror = -1 if mirror_coin else 1
        self.current_block = block_num
        print(f"🎯 Установлен диапазон анимации: {start_frame}-{end_frame}, блок {block_num}")

        # Если есть вторая монета, синхронизируем её диапазон
        if self.secondary_coin:
            self.secondary_coin.animation_range = [start_frame, end_frame]
            self.secondary_coin.current_block = block_num

    def _update_block_offset(self, *args):
        """Обновляет смещение монеты в зависимости от текущего кадра"""
        if not hasattr(self, 'parent_screen') or not self.parent_screen:
            return

        block = self.current_block
        frame_in_block = self.current_frame - self.animation_range[0]
        total_frames = self.animation_range[1] - self.animation_range[0] + 1
        mid_frame = total_frames // 2  # 12-й кадр (индекс 11 или 12)

        if block == 1:
            # Для первого блока смещение всегда 0
            self.block_offset = 0
        else:
            # Получаем целевое смещение для текущего блока
            if block == 2:
                target = self.parent_screen.block2_offset
            elif block == 3:
                target = self.parent_screen.block3_offset
            elif block == 4:
                target = self.parent_screen.block4_offset
            else:
                target = 0

            # Получаем предыдущее смещение
            if block == 2:
                previous = 0  # Предыдущий блок 1 имел смещение 0
            elif block == 3:
                previous = self.parent_screen.block2_offset
            elif block == 4:
                previous = self.parent_screen.block3_offset
            else:
                previous = 0

            # Вычисляем коэффициент в зависимости от положения кадра
            # На 1-м кадре: 0, на 12-м кадре: 1, на 24-м кадре: 0
            if frame_in_block <= mid_frame:
                # От 1 до 12 кадра - линейный рост от 0 до 1
                factor = frame_in_block / mid_frame
            else:
                # От 12 до 24 кадра - линейное падение от 1 до 0
                factor = (total_frames - 1 - frame_in_block) / mid_frame

            # Вычисляем текущее смещение как интерполяцию между предыдущим и целевым
            self.block_offset = previous + (target - previous) * factor

        # Применяем смещение к extra_offset_x
        self.extra_offset_x = self.block_offset

    def _update_rotation(self, *args):
        """Обновляет поворот изображения и тени"""
        if not self.texture:
            return

        if self.width <= 0 or self.height <= 0 or (self.x == 0 and self.y == 0):
            Clock.schedule_once(lambda dt: self._update_rotation(), 0.1)
            return

        self.canvas.clear()

        center_x = self.x + self.width / 2
        center_y = self.y + self.height / 2

        with self.canvas:
            # ===== ТЕНЬ =====
            PushMatrix()
            Translate(center_x, center_y)
            Rotate(angle=self.rotation_angle, origin=(0, 0))

            # Используем свойства shadow_offset_x и shadow_offset_y
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

            if self.multi_copy_mode and len(self.frame_history) > 0:
                # Рисуем историю кадров (копии)
                for i, frame_data in enumerate(self.frame_history):
                    frame_texture = frame_data['texture']
                    # Небольшое случайное смещение для копий
                    offset_x = (i - len(self.frame_history) / 2) * 2
                    offset_y = (i - len(self.frame_history) / 2) * 2

                    Color(1.3, 1.3, 1.3, self.copy_opacity * self.coin_opacity)
                    Rectangle(
                        texture=frame_texture,
                        pos=(self.x + offset_x, self.y + offset_y),
                        size=self.size
                    )

                # Рисуем текущий кадр
                Color(1.3, 1.3, 1.3, self.coin_opacity)
                Rectangle(texture=self.texture, pos=self.pos, size=self.size)
            else:
                # Обычный режим - только текущий кадр
                Color(1.3, 1.3, 1.3, self.coin_opacity)
                Rectangle(texture=self.texture, pos=self.pos, size=self.size)

            PopMatrix()

    def _update_position(self, *args):
        """Обновляет позицию монеты на эллипсе с учетом спирального фактора и дополнительного смещения"""
        base_center_x = 0.35
        base_center_y = 0.5

        # Применяем спиральный фактор к смещению эллипса
        # Когда spiral_factor = 1, монета на краю эллипса
        # Когда spiral_factor = 0, монета в центре
        current_offset_x = self.ellipse_offset_x * self.spiral_factor
        current_offset_y = self.ellipse_offset_y * self.spiral_factor

        # Применяем базовое смещение по эллипсу с учетом спирали
        # Дополнительное смещение в пикселях преобразуем в относительные координаты
        self.pos_hint = {
            'center_x': base_center_x + current_offset_x + (self.extra_offset_x / Window.width),
            'center_y': base_center_y + current_offset_y + (self.extra_offset_y / Window.height)
        }

        # После изменения позиции обновляем отрисовку
        Clock.schedule_once(lambda dt: self._update_rotation(), 0.05)

    def start_animation(self, fps=60, frame_step=1, multi_copy_mode=False, copy_count=4, copy_opacity=0.4):
        """
        Запускает анимацию вращения
        fps: кадров в секунду
        frame_step: шаг пропуска кадров
        multi_copy_mode: режим множественных копий
        copy_count: количество копий
        copy_opacity: прозрачность ВСЕХ копий
        """
        if not self.frames or self.is_animating:
            return

        self.is_animating = True
        self.current_fps = fps
        self.frame_step = frame_step
        self.multi_copy_mode = multi_copy_mode
        self.copy_count = copy_count
        self.copy_opacity = copy_opacity
        self.current_frame = self.animation_range[0]
        self.frame_duration = 1.0 / fps
        self.frame_history = []  # Очищаем историю при новом запуске

        if self.anim_clock:
            self.anim_clock.cancel()

        self.anim_clock = Clock.schedule_interval(self.next_frame, self.frame_duration)

        # Рассчитываем эффективную скорость с учетом пропуска кадров
        effective_speed = fps * frame_step
        copy_info = f", режим копий: {copy_count} копий, прозрачность {copy_opacity}" if multi_copy_mode else ""
        print(
            f"🎬 Анимация запущена с FPS: {fps}, шаг пропуска: {frame_step}, эффективная скорость: {effective_speed} кадров/сек{copy_info}, диапазон: {self.animation_range[0]}-{self.animation_range[1]}")

    def next_frame(self, dt):
        if not self.is_animating or not self.frames:
            return

        # Если включен режим множественных копий, сохраняем текущий кадр в историю
        if self.multi_copy_mode:
            # Добавляем текущий кадр в историю
            self.frame_history.append({
                'texture': self.texture,
                'frame': self.current_frame
            })

            # Ограничиваем длину истории
            if len(self.frame_history) > self.copy_count:
                self.frame_history.pop(0)

        # Увеличиваем текущий кадр с учетом шага пропуска
        self.current_frame += self.frame_step

        # Проверяем выход за пределы диапазона
        if self.current_frame > self.animation_range[1]:
            # Вычисляем, на сколько мы вышли за пределы
            overflow = self.current_frame - self.animation_range[1] - 1
            # Возвращаемся к началу с учетом переполнения
            self.current_frame = self.animation_range[0] + overflow

            # При зацикливании очищаем историю, чтобы не было скачка
            if self.multi_copy_mode:
                self.frame_history = []

        self.texture = self.frames[self.current_frame]
        self._update_rotation()

        # Синхронизируем вторую монету со смещением на 8 кадров
        if self.secondary_coin and self.secondary_coin.is_animating:
            # Вычисляем кадр для второй монеты (текущий кадр + 8, с учетом диапазона)
            secondary_frame = self.current_frame + 8

            # Проверяем выход за пределы диапазона
            if secondary_frame > self.animation_range[1]:
                overflow = secondary_frame - self.animation_range[1] - 1
                secondary_frame = self.animation_range[0] + overflow

            self.secondary_coin.texture = self.frames[secondary_frame]
            self.secondary_coin.current_frame = secondary_frame
            self.secondary_coin._update_rotation()

    def stop_animation(self):
        """Останавливает анимацию"""
        self.is_animating = False
        self.multi_copy_mode = False
        self.frame_history = []
        if self.anim_clock:
            self.anim_clock.cancel()
            self.anim_clock = None

        # Останавливаем и вторую монету
        if self.secondary_coin:
            self.secondary_coin.is_animating = False
            if self.secondary_coin.anim_clock:
                self.secondary_coin.anim_clock.cancel()
                self.secondary_coin.anim_clock = None

    def set_result(self, result):
        """Устанавливает финальный кадр (0 - орел, 1 - решка) - используется только если анимация не показала результат"""
        if not self.frames:
            return

        # Для 96 кадров (4 блока по 24 кадра):
        # Блок 1 (0-23): первые 12 кадров - орел, вторые 12 - решка
        # Блок 2 (24-47): первые 12 кадров - орел, вторые 12 - решка
        # Блок 3 (48-71): первые 12 кадров - орел, вторые 12 - решка
        # Блок 4 (72-95): первые 12 кадров - орел, вторые 12 - решка

        # Выбираем случайный блок (1-4)
        block = random.randint(0, 3)
        block_start = block * 24

        if result == 0:  # Орел - первая половина блока
            frame_index = block_start + random.randint(0, 11)
            print(f"🎲 Орел: выбран кадр {frame_index + 1} из блока {block + 1}")
        else:  # Решка - вторая половина блока
            frame_index = block_start + random.randint(12, 23)
            print(f"🎲 Решка: выбран кадр {frame_index + 1} из блока {block + 1}")

        self.texture = self.frames[frame_index]
        self._update_rotation()

        # Синхронизируем вторую монету
        if self.secondary_coin:
            self.secondary_coin.texture = self.frames[frame_index]
            self.secondary_coin._update_rotation()

    def reset_to_first_animation(self, start_frame=0):
        """Сбрасывает монету к первому блоку (первые 24 кадра) с указанным начальным кадром и обнуляет смещение"""
        self.stop_animation()
        self.set_animation_range(0, 23, block_num=1)
        self.extra_offset_x = 0  # Сбрасываем дополнительное смещение в пикселях
        self.extra_offset_y = 0
        self.ellipse_offset_x = 0  # Сбрасываем смещение на эллипсе
        self.ellipse_offset_y = 0
        self.spiral_factor = 1.0  # Сбрасываем спиральный фактор
        self.block_offset = 0
        self.target_offset = 0
        self.previous_offset = 0
        self.coin_opacity = 1.0  # На старте монета полностью видна
        if 0 <= start_frame < len(self.frames):
            self.texture = self.frames[start_frame]
            print(f"🎬 Сброс к первому блоку, кадр: {start_frame + 1}, смещение обнулено")

        # Сбрасываем и вторую монету, но делаем её невидимой (прозрачность 0)
        if self.secondary_coin:
            secondary_start = (start_frame + 8) % 24
            self.secondary_coin.stop_animation()
            self.secondary_coin.set_animation_range(0, 23, block_num=1)
            self.secondary_coin.extra_offset_x = 0
            self.secondary_coin.extra_offset_y = 0
            self.secondary_coin.ellipse_offset_x = 0
            self.secondary_coin.ellipse_offset_y = 0
            self.secondary_coin.spiral_factor = 1.0
            self.secondary_coin.block_offset = 0
            self.secondary_coin.coin_opacity = 0  # Невидимая на старте
            if 0 <= secondary_start < len(self.secondary_coin.frames):
                self.secondary_coin.texture = self.secondary_coin.frames[secondary_start]


class CoinScreen(BaseGameScreen):
    """Игровой экран с монетой из единого спрайт-листа 10x10 (96 кадров, 4 блока по 24 кадра)
       Движение по спирали от края эллипса к центру, затем вращение на месте, затем переход по блокам
    """

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self.background_image = 'assets/backgrounds/coin_bg.png'

        # Единый спрайт-лист 10x10 с 96 кадрами (4 блока по 24 кадра)
        self.spritesheet_path = 'assets/sprites/spritesheet_10x10.png'

        self.coin = None
        self.secondary_coin = None  # Вторая полупрозрачная монета
        self.touch_area = None
        self.info_label = None
        self.stats_label = None
        self.flip_sound = None

        self.total_flips = 0
        self.heads_count = 0
        self.tails_count = 0
        self.coin_start_frame = 0
        self.coin_start_side = 0

        # Высота монеты для расчета смещения (в пикселях)
        self.coin_height = 55
        # Шаг смещения монеты - 1/12 высоты монеты, отрицательное значение для смещения влево
        self.shift_step = -self.coin_height / 24  # 1/12 от высоты, отрицательное = смещение влево

        # Начальное смещение тени (полная высота вниз)
        self.initial_shadow_offset = -self.coin_height * 0.97  # чтобы тень была ПОД монетой
        # Текущее смещение тени
        self.current_shadow_offset = self.initial_shadow_offset

        # Параметры для движения по эллипсу (горизонтальный эллипс)
        self.ellipse_radius_x = 0.15  # Радиус эллипса по X (горизонтальный)
        self.ellipse_radius_y = 0.4  # Радиус эллипса по Y (вертикальный)
        self.start_offset_x = -0.15  # Стартовое смещение X (левая точка эллипса)
        self.start_offset_y = 0  # Стартовое смещение Y (центр по вертикали)

        # Целевые смещения для каждого блока
        self.block2_offset = self.shift_step  # Смещение для блока 2 на 12-м кадре
        self.block3_offset = self.shift_step * 2  # Смещение для блока 3 на 12-м кадре
        self.block4_offset = self.shift_step * 3  # Смещение для блока 4 на 12-м кадре

    def on_enter(self):
        super().on_enter()
        self.setup_game_ui()
        self.load_flip_sound()
        Window.bind(on_resize=self.on_window_resize)

    def on_leave(self):
        super().on_leave()
        if self.coin:
            self.coin.stop_animation()
        if self.secondary_coin:
            self.secondary_coin.stop_animation()
        if self.flip_sound and self.flip_sound.state == 'play':
            self.flip_sound.stop()
        Window.unbind(on_resize=self.on_window_resize)

    def on_window_resize(self, instance, width, height):
        if self.coin:
            Clock.schedule_once(lambda dt: self.coin._update_rotation(), 0.1)
        if self.secondary_coin:
            Clock.schedule_once(lambda dt: self.secondary_coin._update_rotation(), 0.1)

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
        # Проверяем наличие спрайт-листа
        self.check_file(self.spritesheet_path)

        a = 0.15
        b = 0.4
        center_x = 0.35
        image_shift = 0.02

        # Размер монеты
        coin_size = 55
        self.coin_height = coin_size  # Сохраняем высоту для расчетов
        self.shift_step = -self.coin_height / 24  # Обновляем шаг смещения (1/12 высоты)
        self.initial_shadow_offset = -self.coin_height * 0.97  # чтобы тень была ПОД монетой
        self.current_shadow_offset = self.initial_shadow_offset

        # Обновляем целевые смещения
        self.block2_offset = self.shift_step
        self.block3_offset = self.shift_step * 2
        self.block4_offset = self.shift_step * 3

        # Случайно выбираем начальную сторону монеты (0 - орел/кадр 0, 1 - решка/кадр 11)
        self.coin_start_side = random.randint(0, 1)
        self.coin_start_frame = 0 if self.coin_start_side == 0 else 11

        print(
            f"🎲 Начальная сторона: {'ОРЕЛ' if self.coin_start_side == 0 else 'РЕШКА'}, кадр: {self.coin_start_frame + 1}")

        # СОЗДАЕМ ОСНОВНУЮ МОНЕТУ (полностью видимая на старте)
        self.coin = SpritesheetCoin(
            spritesheet_path=self.spritesheet_path,
            frame_width=64,
            frame_height=64,
            cols=10,
            rows=10,
            total_frames=96,
            frames_per_block=24,
            start_frame=self.coin_start_frame,
            rotation_angle=-90,  # Поворот против часовой стрелки
            size_hint=(None, None),
            size=(coin_size, coin_size),
            pos_hint={'center_x': center_x - a - image_shift, 'center_y': 0.5},
            allow_stretch=True,
            shadow_offset_x=0,
            shadow_offset_y=self.initial_shadow_offset,  # Начальное смещение тени
            shadow_scale_y=1.0,
            shadow_alpha=0.5,
            coin_opacity=1.0  # Полностью видимая на старте
        )

        # Устанавливаем ссылку на родительский экран для доступа к смещениям
        self.coin.parent_screen = self

        # Устанавливаем начальное смещение эллипса (левая точка эллипса)
        self.coin.ellipse_offset_x = -self.ellipse_radius_x  # Левая точка
        self.coin.ellipse_offset_y = 0  # Центр по вертикали
        self.coin.spiral_factor = 1.0  # Начинаем с края эллипса

        self.layout.add_widget(self.coin)

        # СОЗДАЕМ ВТОРУЮ ПОЛУПРОЗРАЧНУЮ МОНЕТУ (прозрачность 0, невидимая на старте)
        secondary_start_frame = (self.coin_start_frame + 8) % 24  # Смещение на 8 кадров в пределах блока 1

        self.secondary_coin = SpritesheetCoin(
            spritesheet_path=self.spritesheet_path,
            frame_width=64,
            frame_height=64,
            cols=10,
            rows=10,
            total_frames=96,
            frames_per_block=24,
            start_frame=secondary_start_frame,
            rotation_angle=-90,  # Такой же поворот
            size_hint=(None, None),
            size=(coin_size, coin_size),
            pos_hint={'center_x': center_x - a - image_shift, 'center_y': 0.5},  # Та же позиция
            allow_stretch=True,
            shadow_offset_x=0,
            shadow_offset_y=self.initial_shadow_offset,  # Такая же тень
            shadow_scale_y=1.0,
            shadow_alpha=0.5,
            coin_opacity=0  # Невидимая на старте
        )

        # Устанавливаем ссылку на родительский экран
        self.secondary_coin.parent_screen = self

        # Устанавливаем такое же начальное смещение эллипса
        self.secondary_coin.ellipse_offset_x = -self.ellipse_radius_x
        self.secondary_coin.ellipse_offset_y = 0
        self.secondary_coin.spiral_factor = 1.0

        # Устанавливаем связь между монетами (основная монета будет управлять второй)
        self.coin.set_secondary_coin(self.secondary_coin)

        self.layout.add_widget(self.secondary_coin)

        self.touch_area = TouchArea(
            size_hint=(0.4, 0.4),
            pos_hint={'center_x': center_x - a - image_shift, 'center_y': 0.5},
        )
        self.layout.add_widget(self.touch_area)

        self.touch_area.bind(on_touch_down=self.on_area_touch)

    def update_ellipse_position(self, angle):
        """
        Обновляет позицию монеты на эллипсе по заданному углу
        """
        # Для горизонтального эллипса: x = a*cos(angle), y = b*sin(angle)
        x_offset = self.ellipse_radius_x * math.cos(angle)
        y_offset = self.ellipse_radius_y * math.sin(angle)

        self.coin.ellipse_offset_x = x_offset
        self.coin.ellipse_offset_y = y_offset

        # Обновляем и вторую монету
        if self.secondary_coin:
            self.secondary_coin.ellipse_offset_x = x_offset
            self.secondary_coin.ellipse_offset_y = y_offset

    def create_spiral_animation(self, duration=8.0, rotations=3):
        """
        Создает анимацию движения по спирали от края эллипса к центру
        с РАВНОМЕРНОЙ скоростью (БЕЗ ЗАТУХАНИЯ)
        duration: длительность анимации
        rotations: количество полных оборотов
        """
        anim = Animation(duration=0)

        # Количество шагов анимации
        steps = 60
        step_duration = duration / steps  # Одинаковая длительность для каждого шага

        # Стартовый угол для левой точки эллипса
        start_angle = math.pi

        # Конечный угол: стартовый угол + 2π * rotations
        end_angle = start_angle + (2 * math.pi * rotations)

        for i in range(1, steps + 1):  # Начинаем с i=1, чтобы не создавать пустой первый шаг
            t = i / steps  # Прогресс от 1/steps до 1

            # Текущий угол (линейно увеличивается)
            current_angle = start_angle + (end_angle - start_angle) * t

            # Вычисляем позицию на эллипсе
            x_offset = self.ellipse_radius_x * math.cos(current_angle)
            y_offset = self.ellipse_radius_y * math.sin(current_angle)

            # СПИРАЛЬНЫЙ ФАКТОР - РАВНОМЕРНОЕ УМЕНЬШЕНИЕ
            spiral_factor = 1.0 - t  # Линейное изменение

            # Добавляем ключевой кадр анимации с одинаковой длительностью
            step_anim = Animation(
                ellipse_offset_x=x_offset,
                ellipse_offset_y=y_offset,
                spiral_factor=spiral_factor,
                duration=step_duration,  # Одинаковая длительность для всех шагов
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

        # Сбрасываем к первому блоку и начальной позиции
        self.coin.reset_to_first_animation(self.coin_start_frame)
        self.coin.shadow_offset_y = self.initial_shadow_offset
        self.current_shadow_offset = self.initial_shadow_offset

        # Вторая монета уже синхронизируется через reset_to_first_animation

        # Устанавливаем начальную позицию на эллипсе (левая точка)
        self.coin.ellipse_offset_x = -self.ellipse_radius_x
        self.coin.ellipse_offset_y = 0
        self.coin.spiral_factor = 1.0  # Начинаем с края

        if self.secondary_coin:
            self.secondary_coin.ellipse_offset_x = -self.ellipse_radius_x
            self.secondary_coin.ellipse_offset_y = 0
            self.secondary_coin.spiral_factor = 1.0

        result = random.randint(0, 1)

        self.total_flips += 1
        if result == 0:
            self.heads_count += 1
            result_text = 'ОРЕЛ'
        else:
            self.tails_count += 1
            result_text = 'РЕШКА'

        # НАСТРОЙКИ АНИМАЦИИ
        # =================

        # Параметры для этапов с копиями
        base_fps = 60  # FPS для анимации
        base_frame_step = 2  # Шаг пропуска кадров

        # Количество копий для разных этапов
        stage2_copy_count = 2  # 2 копии для второго этапа
        stage2_copy_opacity = 0.4

        stage3_copy_count = 2  # 2 копии для блока 2
        stage3_copy_opacity = 0.4

        stage4_copy_count = 2  # 2 копии для блока 3
        stage4_copy_opacity = 0.4

        stage5_copy_count = 2  # 2 копии для блока 4
        stage5_copy_opacity = 0.4

        # Длительности этапов
        block_duration = 3.0  # Длительность каждого блока (2, 3, 4)
        spiral_duration = 8.0  # Длительность движения по спирали
        center_rotation_duration = 5.0  # Длительность вращения в центре
        rotations = 4  # Количество полных оборотов во время движения по спирали
        fade_duration = 1.0  # Длительность плавного появления/исчезновения

        # Шаг смещения монеты в пикселях
        step_x = self.shift_step

        # Коэффициент уменьшения смещения тени
        shadow_reduction_factor = 11

        print(f"\n=== ПОРЯДОК АНИМАЦИИ ===")
        print(f"1. Движение по спирали к центру: {spiral_duration} сек")
        print(f"   Старт: левая точка эллипса")
        print(f"   {rotations} полных оборотов")
        print(f"   Эллипс: ширина={self.ellipse_radius_x}, высота={self.ellipse_radius_y}")
        print(f"2. Вращение в центре: {center_rotation_duration} сек")
        print(f"   Плавный переход: первая анимация исчезает, вторая появляется за {fade_duration} сек")
        print(f"3. Блок 2: {block_duration} сек (старт с кадра 35, цикл 24-47)")
        print(f"   Смещение: 0 на 24 кадре -> {step_x:.2f}px на 35 кадре -> 0 на 47 кадре")
        print(f"4. Блок 3: {block_duration} сек (старт с кадра 59, цикл 48-71)")
        print(f"   Смещение: {step_x * 2:.2f}px (постоянное)")
        print(f"5. Блок 4: {block_duration} сек (старт с 77/89, цикл 72-83/84-95)")
        print(f"   Смещение: 0 на 72/84 кадре -> {step_x * 3:.2f}px на 77/89 кадре -> 0 на 83/95 кадре")
        print(
            f"   Плавный переход: вторая монета исчезает, основная становится полностью видимой за {fade_duration} сек")
        print(f"   Скорость вращения: {base_fps * base_frame_step} кадров/сек")
        print(f"   На блоке 4 монета становится полностью видимой и остается одна")

        # ЭТАП 1: Запускаем анимацию движения по спирали
        print("🎬 ЭТАП 1: Движение по спирали к центру")
        self.coin.set_animation_range(0, 23, block_num=1)
        self.coin.extra_offset_x = 0
        self.coin.shadow_offset_y = self.current_shadow_offset
        self.coin.start_animation(
            fps=base_fps,
            frame_step=base_frame_step,
            multi_copy_mode=True,
            copy_count=stage2_copy_count,
            copy_opacity=stage2_copy_opacity
        )

        # Запускаем анимацию для второй монеты (она будет синхронизироваться через основную)
        if self.secondary_coin:
            self.secondary_coin.set_animation_range(0, 23, block_num=1)
            self.secondary_coin.extra_offset_x = 0
            self.secondary_coin.shadow_offset_y = self.current_shadow_offset
            self.secondary_coin.start_animation(
                fps=base_fps,
                frame_step=base_frame_step,
                multi_copy_mode=True,
                copy_count=stage2_copy_count,
                copy_opacity=stage2_copy_opacity
            )

        # СОЗДАЕМ И ЗАПУСКАЕМ АНИМАЦИЮ ДВИЖЕНИЯ ПО СПИРАЛИ
        spiral_anim = self.create_spiral_animation(spiral_duration, rotations)

        # Привязываем функцию, которая запустит вращение в центре после окончания спирали
        def on_spiral_complete(animation, coin):
            print("✅ Спираль завершена, начинаем вращение в центре")
            self.start_center_rotation(result, base_fps, base_frame_step, center_rotation_duration, fade_duration)

        spiral_anim.bind(on_complete=on_spiral_complete)
        spiral_anim.start(self.coin)

        # Запускаем такую же анимацию для второй монеты
        if self.secondary_coin:
            spiral_anim_copy = self.create_spiral_animation(spiral_duration, rotations)
            spiral_anim_copy.start(self.secondary_coin)

    def start_center_rotation(self, result, fps, frame_step, duration, fade_duration=1.0):
        """
        Этап 2: Вращение монеты в центре эллипса с плавным переходом
        Первая анимация исчезает, вторая появляется одновременно
        """
        print(f"⏱️ ЭТАП 2: Вращение в центре - {duration} сек")
        print(f"   Плавный переход: основная монета 1.0 → 0.0, вторая монета 0.0 → 1.0 за {fade_duration} сек")

        # Убеждаемся, что монета в центре
        self.coin.spiral_factor = 0
        if self.secondary_coin:
            self.secondary_coin.spiral_factor = 0

        # Создаем параллельные анимации для плавного перехода
        if self.secondary_coin:
            # Анимация для основной монеты: исчезает (1.0 → 0.0)
            fade_out_anim = Animation(coin_opacity=0.0, duration=fade_duration, t='linear')

            # Анимация для второй монеты: появляется (0.0 → 1.0)
            fade_in_anim = Animation(coin_opacity=1.0, duration=fade_duration, t='linear')

            # Запускаем обе анимации одновременно
            fade_out_anim.start(self.coin)
            fade_in_anim.start(self.secondary_coin)
        else:
            # Если нет второй монеты, просто делаем основную полупрозрачной
            fade_anim = Animation(coin_opacity=0.7, duration=fade_duration, t='linear')
            fade_anim.start(self.coin)

        # Через указанное время переходим к блоку 2
        Clock.schedule_once(lambda dt: self.switch_to_block_2(
            result,
            fps, frame_step,
            2, 0.4,  # copy_count2, copy_opacity2
            2, 0.4,  # copy_count3, copy_opacity3
            2, 0.4,  # copy_count4, copy_opacity4
            1.5,  # block_duration
            self.shift_step,
            11,  # shadow_reduction_factor
            fade_duration
        ), duration)

    def switch_to_block_2(self, result,
                          fps=60, frame_step=2,
                          copy_count2=2, copy_opacity2=0.4,
                          copy_count3=2, copy_opacity3=0.4,
                          copy_count4=2, copy_opacity4=0.4,
                          block_duration=3.0,
                          step_x=-18,
                          shadow_reduction_factor=11,
                          fade_duration=1.0):
        """ЭТАП 3: Блок 2 со смещением монеты и уменьшенной тенью - старт с 35 кадра, цикл 24-47"""
        self.current_shadow_offset = self.initial_shadow_offset + (self.coin_height / shadow_reduction_factor)

        # Стартуем с 35 кадра, но анимируем весь диапазон 24-47
        start_frame = 35  # Стартовый кадр
        full_range_start = 24  # Начало полного диапазона
        full_range_end = 47  # Конец полного диапазона

        print(f"⏱️ ЭТАП 3: Блок 2 (кадры {full_range_start}-{full_range_end}) с {copy_count2} копиями")
        print(f"   Смещение монеты будет динамическим: 0 на кадре 24 -> {step_x:.2f}px на кадре 35 -> 0 на кадре 47")
        print(f"   Смещение тени: {self.current_shadow_offset:.2f}px (постоянное)")
        print(f"   Скорость вращения: {fps * frame_step} кадров/сек")

        self.coin.stop_animation()
        if self.secondary_coin:
            self.secondary_coin.stop_animation()

        # Устанавливаем начальный кадр на 35
        if 0 <= start_frame < len(self.coin.frames):
            self.coin.texture = self.coin.frames[start_frame]
            self.coin.current_frame = start_frame

            # Для второй монеты - кадр со смещением +8
            if self.secondary_coin:
                secondary_frame = start_frame + 8
                if secondary_frame > full_range_end:
                    secondary_frame = full_range_start + (secondary_frame - full_range_end - 1)
                self.secondary_coin.texture = self.secondary_coin.frames[secondary_frame]
                self.secondary_coin.current_frame = secondary_frame

        # Устанавливаем полный диапазон для циклической анимации
        self.coin.set_animation_range(full_range_start, full_range_end, block_num=2)
        self.coin.shadow_offset_y = self.current_shadow_offset
        self.coin.start_animation(
            fps=fps,
            frame_step=frame_step,
            multi_copy_mode=True,
            copy_count=copy_count2,
            copy_opacity=copy_opacity2
        )

        # Запускаем анимацию для второй монеты
        if self.secondary_coin:
            self.secondary_coin.set_animation_range(full_range_start, full_range_end, block_num=2)
            self.secondary_coin.shadow_offset_y = self.current_shadow_offset
            self.secondary_coin.start_animation(
                fps=fps,
                frame_step=frame_step,
                multi_copy_mode=True,
                copy_count=copy_count2,
                copy_opacity=copy_opacity2
            )

        Clock.schedule_once(lambda dt: self.switch_to_block_3(
            result,
            fps, frame_step,
            copy_count3, copy_opacity3,
            copy_count4, copy_opacity4,
            block_duration,
            step_x,
            shadow_reduction_factor,
            fade_duration
        ), block_duration)

    def switch_to_block_3(self, result,
                          fps=60, frame_step=2,
                          copy_count3=2, copy_opacity3=0.4,
                          copy_count4=2, copy_opacity4=0.4,
                          block_duration=3.0,
                          step_x=-18,
                          shadow_reduction_factor=11,
                          fade_duration=1.0):
        """ЭТАП 4: Блок 3 со смещением монеты и еще более уменьшенной тенью - старт с 59 кадра, цикл 48-71"""
        self.current_shadow_offset = self.initial_shadow_offset + (self.coin_height / shadow_reduction_factor) * 2

        # Стартуем с 59 кадра, но анимируем весь диапазон 48-71
        start_frame = 59  # Стартовый кадр
        full_range_start = 48  # Начало полного диапазона
        full_range_end = 71  # Конец полного диапазона

        print(f"⏱️ ЭТАП 4: Блок 3 (кадры {full_range_start}-{full_range_end}) с {copy_count3} копиями")
        print(f"   Смещение монеты: {step_x * 2:.2f}px (постоянное)")
        print(f"   Смещение тени: {self.current_shadow_offset:.2f}px (постоянное)")
        print(f"   Скорость вращения: {fps * frame_step} кадров/сек")

        self.coin.stop_animation()
        if self.secondary_coin:
            self.secondary_coin.stop_animation()

        # Устанавливаем начальный кадр на 59
        if 0 <= start_frame < len(self.coin.frames):
            self.coin.texture = self.coin.frames[start_frame]
            self.coin.current_frame = start_frame

            # Для второй монеты - кадр со смещением +8
            if self.secondary_coin:
                secondary_frame = start_frame + 8
                if secondary_frame > full_range_end:
                    secondary_frame = full_range_start + (secondary_frame - full_range_end - 1)
                self.secondary_coin.texture = self.secondary_coin.frames[secondary_frame]
                self.secondary_coin.current_frame = secondary_frame

        # Устанавливаем полный диапазон для циклической анимации
        self.coin.set_animation_range(full_range_start, full_range_end, block_num=3)
        self.coin.shadow_offset_y = self.current_shadow_offset

        # Устанавливаем постоянное смещение монеты
        self.coin.extra_offset_x = step_x * 2
        if self.secondary_coin:
            self.secondary_coin.extra_offset_x = step_x * 2

        self.coin.start_animation(
            fps=fps,
            frame_step=frame_step,
            multi_copy_mode=True,
            copy_count=copy_count3,
            copy_opacity=copy_opacity3
        )

        # Запускаем анимацию для второй монеты
        if self.secondary_coin:
            self.secondary_coin.start_animation(
                fps=fps,
                frame_step=frame_step,
                multi_copy_mode=True,
                copy_count=copy_count3,
                copy_opacity=copy_opacity3
            )

        Clock.schedule_once(lambda dt: self.switch_to_block_4(
            result,
            fps, frame_step,
            copy_count4, copy_opacity4,
            block_duration,
            step_x,
            shadow_reduction_factor,
            fade_duration
        ), block_duration)

    def switch_to_block_4(self, result,
                          fps=60, frame_step=2,
                          copy_count4=2, copy_opacity4=0.4,
                          block_duration=3.0,
                          step_x=-18,
                          shadow_reduction_factor=11,
                          fade_duration=1.0):
        """ЭТАП 5: Блок 4 со смещением монеты и минимальной тенью - старт с среднего кадра, цикл в своей половине"""
        self.current_shadow_offset = self.initial_shadow_offset + (self.coin_height / shadow_reduction_factor) * 3

        if result == 0:
            # Для орла: кадры 72-83 - старт с 77, цикл 72-83
            start_frame = 77
            full_range_start = 72
            full_range_end = 83
            side_name = "ОРЁЛ"
        else:
            # Для решки: кадры 84-95 - старт с 89, цикл 84-95
            start_frame = 89
            full_range_start = 84
            full_range_end = 95
            side_name = "РЕШКА"

        print(f"⏱️ ЭТАП 5: Блок 4 (кадры {full_range_start}-{full_range_end}) для {side_name} с {copy_count4} копиями")
        print(
            f"   Смещение монеты будет динамическим: 0 на кадре {full_range_start} -> {step_x * 3:.2f}px на кадре {start_frame} -> 0 на кадре {full_range_end}")
        print(f"   Смещение тени: {self.current_shadow_offset:.2f}px (постоянное)")
        print(f"   Скорость вращения: {fps * frame_step} кадров/сек")
        print(
            f"   Плавный переход: вторая монета исчезает, основная становится полностью видимой за {fade_duration} сек")

        self.coin.stop_animation()
        if self.secondary_coin:
            self.secondary_coin.stop_animation()

        # Создаем параллельные анимации для плавного перехода
        if self.secondary_coin:
            # Анимация для второй монеты: исчезает (1.0 → 0.0)
            fade_out_anim = Animation(coin_opacity=0.0, duration=fade_duration, t='linear')

            # Анимация для основной монеты: становится полностью видимой (0.0 → 1.0)
            fade_in_anim = Animation(coin_opacity=1.0, duration=fade_duration, t='linear')

            # Запускаем обе анимации одновременно
            fade_out_anim.start(self.secondary_coin)
            fade_in_anim.start(self.coin)
        else:
            # Если нет второй монеты, просто делаем основную полностью видимой
            fade_anim = Animation(coin_opacity=1.0, duration=fade_duration, t='linear')
            fade_anim.start(self.coin)

        # Устанавливаем начальный кадр на средний кадр блока
        if 0 <= start_frame < len(self.coin.frames):
            self.coin.texture = self.coin.frames[start_frame]
            self.coin.current_frame = start_frame

            # Для второй монеты - кадр со смещением +8 (но она будет исчезать)
            if self.secondary_coin:
                secondary_frame = start_frame + 8
                if secondary_frame > full_range_end:
                    secondary_frame = full_range_start + (secondary_frame - full_range_end - 1)
                self.secondary_coin.texture = self.secondary_coin.frames[secondary_frame]
                self.secondary_coin.current_frame = secondary_frame

        # Устанавливаем полный диапазон для циклической анимации
        self.coin.set_animation_range(full_range_start, full_range_end, block_num=4)
        self.coin.shadow_offset_y = self.current_shadow_offset
        self.coin.start_animation(
            fps=fps,
            frame_step=frame_step,
            multi_copy_mode=True,
            copy_count=copy_count4,
            copy_opacity=copy_opacity4
        )

        # Запускаем анимацию для второй монеты (она будет синхронизироваться, но исчезать)
        if self.secondary_coin:
            self.secondary_coin.set_animation_range(full_range_start, full_range_end, block_num=4)
            self.secondary_coin.shadow_offset_y = self.current_shadow_offset
            self.secondary_coin.start_animation(
                fps=fps,
                frame_step=frame_step,
                multi_copy_mode=True,
                copy_count=copy_count4,
                copy_opacity=copy_opacity4
            )

        Clock.schedule_once(lambda dt: self.finish_rotation(result), block_duration)

    def finish_rotation(self, result):
        """ЭТАП 6: Показ результата в центре"""
        print("⏱️ ЭТАП 6: Показ результата в центре")

        self.coin.stop_animation()
        if self.secondary_coin:
            self.secondary_coin.stop_animation()
            # Убеждаемся, что вторая монета невидима
            self.secondary_coin.coin_opacity = 0

        # Убеждаемся, что основная монета полностью видима
        self.coin.coin_opacity = 1.0

        # Устанавливаем монету в центр (spiral_factor = 0)
        self.coin.spiral_factor = 0
        if self.secondary_coin:
            self.secondary_coin.spiral_factor = 0

        if result == 0:
            final_frame = 72
            side_name = "ОРЁЛ"
        else:
            final_frame = 84
            side_name = "РЕШКА"

        if 0 <= final_frame < len(self.coin.frames):
            self.coin.texture = self.coin.frames[final_frame]
            print(f"🎯 Финальный кадр: {final_frame + 1} ({side_name}) в центре")
            self.coin._update_rotation()

            # Вторая монета тоже показывает результат (со смещением +8), но остаётся невидимой
            if self.secondary_coin:
                secondary_frame = final_frame + 8
                if secondary_frame > 95:
                    secondary_frame = 72 + (secondary_frame - 96)  # Зацикливание в пределах блока 4
                self.secondary_coin.texture = self.secondary_coin.frames[secondary_frame]
                self.secondary_coin._update_rotation()

        self.stop_flip_sound()

    def go_to_menu(self):
        if self.coin:
            self.coin.stop_animation()
        if self.secondary_coin:
            self.secondary_coin.stop_animation()
        self.stop_flip_sound()
        super().go_to_menu()