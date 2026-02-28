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
from kivy.graphics import Color, Ellipse, Rectangle, PushMatrix, PopMatrix, Rotate, Translate, Scale
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
    rotation_angle = NumericProperty(-90)  # ИЗМЕНЕНО: теперь -90 градусов (против часовой стрелки)

    # Флаг для зеркального отображения монеты
    coin_mirror = NumericProperty(1)

    # Диапазон кадров для текущей анимации [start, end]
    animation_range = ListProperty([0, 23])  # По умолчанию первые 24 кадра

    # Свойства для позиции на эллипсе
    ellipse_offset_x = NumericProperty(0)
    ellipse_offset_y = NumericProperty(0)

    # ФИКСИРОВАННЫЕ параметры тени
    shadow_offset_x = NumericProperty(0)
    shadow_offset_y = NumericProperty(0)
    shadow_scale_y = NumericProperty(0.9)
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

    def __init__(self, spritesheet_path, frame_width=64, frame_height=64,
                 cols=10, rows=10, total_frames=96, frames_per_block=24, start_frame=0,
                 shadow_offset_x=-13.2, shadow_offset_y=12.1,
                 shadow_scale_y=0.9, shadow_alpha=0.6, **kwargs):
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

        self.bind(texture=self._update_rotation)
        self.bind(pos=self._update_rotation, size=self._update_rotation)
        self.bind(rotation_angle=self._update_rotation)
        self.bind(ellipse_offset_x=self._update_position,
                  ellipse_offset_y=self._update_position)
        self.bind(coin_mirror=self._update_rotation)

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

    def set_animation_range(self, start_frame, end_frame, mirror_coin=False, block_num=1):
        """Устанавливает диапазон кадров для анимации"""
        self.animation_range = [start_frame, end_frame]
        self.coin_mirror = -1 if mirror_coin else 1
        self.current_block = block_num
        print(f"🎯 Установлен диапазон анимации: {start_frame}-{end_frame}, блок {block_num}")

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
            # ===== ОТЛАДОЧНЫЕ КВАДРАТЫ В ЦЕНТРЕ =====
            # (можно закомментировать или удалить в продакшене)
            # Color(1, 0, 0, 0.3)  # Красный полупрозрачный
            # Rectangle(pos=(center_x - self.width / 2, center_y - self.height / 2),
            #           size=(self.width, self.height))
            #
            # Color(1, 1, 0, 0.3)  # Желтый полупрозрачный
            # Rectangle(pos=(center_x - self.width / 2, center_y - self.height / 2),
            #           size=(self.width, self.height))

            # ===== ТЕНЬ =====
            PushMatrix()
            Translate(center_x, center_y)
            Scale(1, self.shadow_scale_y, 1)
            Rotate(angle=self.rotation_angle, origin=(0, 0))
            Translate(-center_x, -center_y)

            Color(0, 0, 0, self.shadow_alpha)
            Rectangle(texture=self.texture, pos=self.pos, size=self.size)
            PopMatrix()

            # ===== МОНЕТА =====
            # Сохраняем текущую матрицу для всех копий
            PushMatrix()
            Translate(center_x, center_y)
            Scale(self.coin_mirror, 1, 1)
            Rotate(angle=self.rotation_angle, origin=(0, 0))
            Translate(-center_x, -center_y)

            # Если включен режим множественных копий и есть история
            if self.multi_copy_mode and len(self.frame_history) > 0:
                # Рисуем ВСЕ копии из истории с одинаковой прозрачностью
                # ВСЕ копии используют ТЕКУЩИЙ поворот, так как матрица уже применена
                for i, frame_data in enumerate(self.frame_history):
                    frame_texture = frame_data['texture']

                    # Небольшое смещение для копий, чтобы создать эффект множественности
                    # (опционально, можно убрать если не нужно)
                    offset_x = (i - len(self.frame_history) / 2) * 2
                    offset_y = (i - len(self.frame_history) / 2) * 2

                    Color(1.3, 1.3, 1.3, self.copy_opacity)
                    Rectangle(
                        texture=frame_texture,
                        pos=(self.x + offset_x, self.y + offset_y),
                        size=self.size
                    )

                # Рисуем текущий кадр поверх с той же прозрачностью
                Color(1.3, 1.3, 1.3, self.copy_opacity)
                Rectangle(texture=self.texture, pos=self.pos, size=self.size)
            else:
                # Обычный режим - одна монета с полной непрозрачностью
                Color(1.3, 1.3, 1.3, 1)
                Rectangle(texture=self.texture, pos=self.pos, size=self.size)

            PopMatrix()

    def _update_position(self, *args):
        """Обновляет позицию монеты на эллипсе"""
        center_x = 0.35
        center_y = 0.5

        self.pos_hint = {
            'center_x': center_x + self.ellipse_offset_x,
            'center_y': center_y + self.ellipse_offset_y
        }

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

    def stop_animation(self):
        """Останавливает анимацию"""
        self.is_animating = False
        self.multi_copy_mode = False
        self.frame_history = []
        if self.anim_clock:
            self.anim_clock.cancel()
            self.anim_clock = None

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

    def reset_to_first_animation(self, start_frame=0):
        """Сбрасывает монету к первому блоку (первые 24 кадра) с указанным начальным кадром"""
        self.stop_animation()
        self.set_animation_range(0, 23, block_num=1)
        if 0 <= start_frame < len(self.frames):
            self.texture = self.frames[start_frame]
            print(f"🎬 Сброс к первому блоку, кадр: {start_frame + 1}")


class CoinScreen(BaseGameScreen):
    """Игровой экран с монетой из единого спрайт-листа 10x10 (96 кадров, 4 блока по 24 кадра)"""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self.background_image = 'assets/backgrounds/coin_bg.png'

        # Единый спрайт-лист 10x10 с 96 кадрами (4 блока по 24 кадра)
        self.spritesheet_path = 'assets/sprites/spritesheet_10x10.png'

        self.coin = None
        self.touch_area = None
        self.info_label = None
        self.stats_label = None
        self.flip_sound = None

        self.total_flips = 0
        self.heads_count = 0
        self.tails_count = 0
        self.coin_start_frame = 0
        self.coin_start_side = 0

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
        # Проверяем наличие спрайт-листа
        self.check_file(self.spritesheet_path)

        a = 0.15
        b = 0.4
        center_x = 0.35
        image_shift = 0.02

        # Размер монеты
        coin_size = 55
        shadow_offset_x = coin_size * 1
        shadow_offset_y = coin_size * 1

        # Случайно выбираем начальную сторону монеты (0 - орел/кадр 0, 1 - решка/кадр 11)
        self.coin_start_side = random.randint(0, 1)
        self.coin_start_frame = 0 if self.coin_start_side == 0 else 11

        print(
            f"🎲 Начальная сторона: {'ОРЕЛ' if self.coin_start_side == 0 else 'РЕШКА'}, кадр: {self.coin_start_frame + 1}")

        # СОЗДАЕМ МОНЕТУ
        self.coin = SpritesheetCoin(
            spritesheet_path=self.spritesheet_path,
            frame_width=64,
            frame_height=64,
            cols=10,
            rows=10,
            total_frames=96,
            frames_per_block=24,
            start_frame=self.coin_start_frame,
            rotation_angle=-90,  # ИЗМЕНЕНО: теперь -90 градусов (против часовой стрелки)
            size_hint=(None, None),
            size=(coin_size, coin_size),
            pos_hint={'center_x': center_x - a - image_shift, 'center_y': 0.5},
            allow_stretch=True,
            shadow_offset_x=shadow_offset_x,
            shadow_offset_y=shadow_offset_y,
            shadow_scale_y=0.9,
            shadow_alpha=0.6
        )

        self.coin.ellipse_offset_x = -a
        self.coin.ellipse_offset_y = 0

        self.layout.add_widget(self.coin)

        self.touch_area = TouchArea(
            size_hint=(0.4, 0.4),
            pos_hint={'center_x': center_x - a - image_shift, 'center_y': 0.5},
        )
        self.layout.add_widget(self.touch_area)

        self.touch_area.bind(on_touch_down=self.on_area_touch)

        self.info_label = Label(
            text='👆 Нажмите на монету',
            color=(1, 1, 0.9, 0.9),
            size_hint=(None, None),
            size=(400, 50),
            pos_hint={'center_x': 0.5, 'center_y': 0.15},
            font_size=20,
            bold=True
        )
        self.layout.add_widget(self.info_label)

        self.stats_label = Label(
            text='Бросков: 0',
            color=(1, 1, 0.9, 0.7),
            size_hint=(None, None),
            size=(300, 40),
            pos_hint={'center_x': 0.5, 'center_y': 0.08},
            font_size=18
        )
        self.layout.add_widget(self.stats_label)

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

        # Сбрасываем к первому блоку с текущим начальным кадром
        self.coin.reset_to_first_animation(self.coin_start_frame)

        result = random.randint(0, 1)

        self.total_flips += 1
        if result == 0:
            self.heads_count += 1
            result_text = 'ОРЕЛ'
        else:
            self.tails_count += 1
            result_text = 'РЕШКА'

        self.stats_label.text = f'Бросков: {self.total_flips} | Орел: {self.heads_count} | Решка: {self.tails_count}'
        print(f"🎲 Результат: {result_text}")

        # НАСТРОЙКИ АНИМАЦИИ
        # =================

        # Параметры для этапов с копиями
        base_fps = 30
        base_frame_step = 2

        # Количество копий для разных этапов
        stage1_copy_count = 4  # 4 копии для первого этапа (в движении)
        stage1_copy_opacity = 0.4

        stage2_copy_count = 2  # 2 копии для второго этапа (на месте)
        stage2_copy_opacity = 0.4

        stage3_copy_count = 2  # 2 копии для блока 2
        stage3_copy_opacity = 0.4

        stage4_copy_count = 2  # 2 копии для блока 3
        stage4_copy_opacity = 0.4

        stage5_copy_count = 2  # 2 копии для блока 4
        stage5_copy_opacity = 0.4

        # Длительности этапов
        move_duration = 12.0  # УВЕЛИЧЕНО: Вращение с копиями в движении (было 5.0, стало 12.0)
        center_duration = 2.0  # Вращение с копиями на месте
        block_duration = 1.5  # Длительность каждого блока (2, 3, 4)

        print(f"\n=== ПОРЯДОК АНИМАЦИИ ===")
        print(f"1. Вращение с {stage1_copy_count} копиями В ДВИЖЕНИИ: {move_duration} сек (ЗАМЕДЛЕНО)")
        print(f"2. Вращение с {stage2_copy_count} копиями НА МЕСТЕ: {center_duration} сек")
        print(f"3. Блок 2 (кадры 24-47) с {stage3_copy_count} копиями: {block_duration} сек")
        print(f"4. Блок 3 (кадры 48-71) с {stage4_copy_count} копиями: {block_duration} сек")
        print(f"5. Блок 4 (кадры 72-95) с {stage5_copy_count} копиями: {block_duration} сек")
        print(f"6. Показ результата\n")

        # СОЗДАЕМ АНИМАЦИЮ ДВИЖЕНИЯ ПО СПИРАЛИ (с увеличенной длительностью)
        spiral_anim = self.create_vertical_spiral_animation(duration=move_duration)

        def on_move_complete(animation, widget):
            print("⏱️ Этап 1 завершен - движение окончено")
            print("⏱️ Этап 2 - вращение с копиями на месте")
            self.start_center_rotation(
                result,
                base_fps,
                base_frame_step,
                stage2_copy_count,
                stage2_copy_opacity,
                center_duration,
                base_fps, base_frame_step,
                stage3_copy_count, stage3_copy_opacity,
                stage4_copy_count, stage4_copy_opacity,
                stage5_copy_count, stage5_copy_opacity,
                block_duration
            )

        spiral_anim.bind(on_complete=on_move_complete)

        # ЭТАП 1: Запускаем анимацию первого блока (кадры 0-23)
        # с копиями ВО ВРЕМЯ ДВИЖЕНИЯ
        print("🎬 ЭТАП 1: Вращение с копиями в движении (ЗАМЕДЛЕНО)")
        self.coin.set_animation_range(0, 23, block_num=1)
        spiral_anim.start(self.coin)
        self.coin.start_animation(
            fps=base_fps,
            frame_step=base_frame_step,
            multi_copy_mode=True,
            copy_count=stage1_copy_count,
            copy_opacity=stage1_copy_opacity
        )

    def start_center_rotation(self, result,
                              fps1=30, frame_step1=2,
                              copy_count1=2, copy_opacity1=0.4, duration1=2.0,
                              fps2=30, frame_step2=2,
                              copy_count2=2, copy_opacity2=0.4,
                              copy_count3=2, copy_opacity3=0.4,
                              copy_count4=2, copy_opacity4=0.4,
                              block_duration=1.5):
        """ЭТАП 2: Вращение с копиями на месте"""
        print(f"⏱️ ЭТАП 2: Вращение с {copy_count1} копиями на месте {duration1} сек")

        # Останавливаем текущую анимацию
        self.coin.stop_animation()

        # Возвращаемся к первому блоку (кадры 0-23) для вращения на месте
        self.coin.set_animation_range(0, 23, block_num=1)

        # Запускаем анимацию с копиями НА МЕСТЕ (без движения)
        self.coin.start_animation(
            fps=fps1,
            frame_step=frame_step1,
            multi_copy_mode=True,
            copy_count=copy_count1,
            copy_opacity=copy_opacity1
        )

        # Через указанное время переходим к блоку 2
        Clock.schedule_once(lambda dt: self.switch_to_block_2(
            result,
            fps2, frame_step2,
            copy_count2, copy_opacity2,
            copy_count3, copy_opacity3,
            copy_count4, copy_opacity4,
            block_duration
        ), duration1)

    def switch_to_block_2(self, result,
                          fps=30, frame_step=2,
                          copy_count2=2, copy_opacity2=0.4,
                          copy_count3=2, copy_opacity3=0.4,
                          copy_count4=2, copy_opacity4=0.4,
                          block_duration=1.5):
        """ЭТАП 3: Блок 2 (кадры 24-47) с 2 копиями"""
        print(f"⏱️ ЭТАП 3: Переключение на блок 2 (кадры 24-47) с {copy_count2} копиями")
        self.coin.stop_animation()
        self.coin.set_animation_range(24, 47, block_num=2)
        self.coin.start_animation(
            fps=fps,
            frame_step=frame_step,
            multi_copy_mode=True,
            copy_count=copy_count2,
            copy_opacity=copy_opacity2
        )

        # Через block_duration секунды переключаемся на блок 3
        Clock.schedule_once(lambda dt: self.switch_to_block_3(
            result,
            fps, frame_step,
            copy_count3, copy_opacity3,
            copy_count4, copy_opacity4,
            block_duration
        ), block_duration)

    def switch_to_block_3(self, result,
                          fps=30, frame_step=2,
                          copy_count3=2, copy_opacity3=0.4,
                          copy_count4=2, copy_opacity4=0.4,
                          block_duration=1.5):
        """ЭТАП 4: Блок 3 (кадры 48-71) с 2 копиями"""
        print(f"⏱️ ЭТАП 4: Переключение на блок 3 (кадры 48-71) с {copy_count3} копиями")
        self.coin.stop_animation()
        self.coin.set_animation_range(48, 71, block_num=3)
        self.coin.start_animation(
            fps=fps,
            frame_step=frame_step,
            multi_copy_mode=True,
            copy_count=copy_count3,
            copy_opacity=copy_opacity3
        )

        # Через block_duration секунды переключаемся на блок 4
        Clock.schedule_once(lambda dt: self.switch_to_block_4(
            result,
            fps, frame_step,
            copy_count4, copy_opacity4,
            block_duration
        ), block_duration)

    def switch_to_block_4(self, result,
                          fps=30, frame_step=2,
                          copy_count4=2, copy_opacity4=0.4,
                          block_duration=1.5):
        """ЭТАП 5: Блок 4 (кадры 72-95) с 2 копиями - используем только половину кадров в зависимости от результата"""

        # Определяем диапазон кадров в зависимости от результата
        if result == 0:  # Орёл - первые 12 кадров блока 4
            start_frame = 72
            end_frame = 83
            side_name = "ОРЁЛ"
        else:  # Решка - вторые 12 кадров блока 4
            start_frame = 84
            end_frame = 95
            side_name = "РЕШКА"

        print(f"⏱️ ЭТАП 5: Блок 4 (кадры {start_frame}-{end_frame}) для {side_name} с {copy_count4} копиями")

        self.coin.stop_animation()
        self.coin.set_animation_range(start_frame, end_frame, block_num=4)
        self.coin.start_animation(
            fps=fps,
            frame_step=frame_step,
            multi_copy_mode=True,
            copy_count=copy_count4,
            copy_opacity=copy_opacity4
        )

        # Через block_duration секунды показываем результат
        Clock.schedule_once(lambda dt: self.finish_rotation(result), block_duration)

    def finish_rotation(self, result):
        """ЭТАП 6: Показ результата - останавливаем на конкретном кадре из 4-го блока"""
        print("⏱️ ЭТАП 6: Показ результата")

        # Останавливаем анимацию
        self.coin.stop_animation()

        # Выбираем конкретный кадр из 4-го блока в зависимости от результата
        if result == 0:  # Орёл - кадр из первой половины 4-го блока
            # Можно выбрать конкретный кадр, например 72 (первый кадр орла в 4-м блоке)
            final_frame = 72
            side_name = "ОРЁЛ"
        else:  # Решка - кадр из второй половины 4-го блока
            # Можно выбрать конкретный кадр, например 84 (первый кадр решки в 4-м блоке)
            final_frame = 84
            side_name = "РЕШКА"

        # Устанавливаем финальный кадр
        if 0 <= final_frame < len(self.coin.frames):
            self.coin.texture = self.coin.frames[final_frame]
            print(f"🎯 Финальный кадр: {final_frame + 1} ({side_name})")
            self.coin._update_rotation()

        self.stop_flip_sound()

    def create_vertical_spiral_animation(self, duration=12.0):
        """Создает анимацию движения по спирали (замедленную)"""
        steps = 200  # Увеличено количество шагов для более плавного движения
        anim = Animation(duration=0)

        a = 0.15
        b = 0.4

        for i in range(steps):
            t = i / steps
            radius_factor = 1 - t
            angle = math.pi + t * 8 * math.pi
            x_offset = a * radius_factor * math.cos(angle)
            y_offset = b * radius_factor * math.sin(angle)

            step_anim = Animation(
                ellipse_offset_x=x_offset,
                ellipse_offset_y=y_offset,
                duration=duration / steps,
                t='linear'
            )
            anim += step_anim

        return anim

    def go_to_menu(self):
        if self.coin:
            self.coin.stop_animation()
        self.stop_flip_sound()
        super().go_to_menu()