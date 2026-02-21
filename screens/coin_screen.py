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
    """Монета из спрайт-листа с поворотом на 90 градусов вокруг центра и тенью"""
    current_frame = NumericProperty(0)
    is_animating = BooleanProperty(False)
    frames = ListProperty([])
    rotation_angle = NumericProperty(-90)

    # Свойства для позиции на эллипсе
    ellipse_offset_x = NumericProperty(0)
    ellipse_offset_y = NumericProperty(0)

    # Свойства для тени
    shadow_offset = NumericProperty(65)  # Смещение тени в пикселях
    shadow_alpha = NumericProperty(0.6)  # Прозрачность тени

    def __init__(self, spritesheet_path, frame_width=64, frame_height=64,
                 cols=5, rows=4, total_frames=20, **kwargs):
        super().__init__(**kwargs)

        self.frame_width = frame_width
        self.frame_height = frame_height
        self.cols = cols
        self.rows = rows
        self.total_frames = min(total_frames, cols * rows)
        self.anim_clock = None

        self.load_spritesheet(spritesheet_path)

        self.bind(texture=self._update_rotation)
        self.bind(pos=self._update_rotation, size=self._update_rotation)
        self.bind(rotation_angle=self._update_rotation)
        self.bind(ellipse_offset_x=self._update_position,
                  ellipse_offset_y=self._update_position)
        self.bind(shadow_offset=self._update_rotation,
                  shadow_alpha=self._update_rotation)

    def load_spritesheet(self, spritesheet_path):
        if not os.path.exists(spritesheet_path):
            print(f"❌ Файл не найден: {spritesheet_path}")
            return

        try:
            img = CoreImage(spritesheet_path)
            texture = img.texture
            if not texture:
                print("❌ Не удалось загрузить текстуру")
                return

            tex_width, tex_height = texture.size
            print(f"📐 Размер спрайт-листа: {tex_width}x{tex_height}")

            frame_w = min(self.frame_width, tex_width // self.cols)
            frame_h = min(self.frame_height, tex_height // self.rows)
            print(f"🖼️ Размер кадра: {frame_w}x{frame_h}")

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

            print(f"✅ Загружено кадров: {len(self.frames)}")

            if self.frames:
                # Устанавливаем 5-й кадр (индекс 4) как начальный
                start_frame = 4  # 👈 5-Й КАДР (ИНДЕКС 4)
                self.texture = self.frames[start_frame]
                print(f"🎬 Стартовый кадр: {start_frame + 1}")
                Clock.schedule_once(lambda dt: self._update_rotation(), 0)

        except Exception as e:
            print(f"❌ Ошибка загрузки спрайт-листа: {e}")

    def _update_rotation(self, *args):
        """Обновляет поворот изображения: тень с смещением в % от ширины монеты"""
        if not self.texture:
            return

        self.canvas.clear()

        # Параметры тени в процентах от размера монеты
        shadow_offset_x_percent = -0.24  # 👈 СМЕЩЕНИЕ ПО X (0 = 0%, 0.5 = 50%, 1.0 = 100%)
        shadow_offset_y_percent = 0.22  # 👈 СМЕЩЕНИЕ ПО Y (0 = 0%, 0.5 = 50%, 1.0 = 100%)
        shadow_scale_y = 0.9  # 👈 СПЛЮЩИВАНИЕ ПО Y
        shadow_alpha = 0.6  # 👈 ПРОЗРАЧНОСТЬ ТЕНИ

        # Преобразуем проценты в пиксели на основе ширины монеты
        shadow_offset_x = self.width * shadow_offset_x_percent
        shadow_offset_y = self.height * shadow_offset_y_percent

        with self.canvas:
            # 👇 ТЕНЬ
            PushMatrix()
            Translate(self.center_x + shadow_offset_x,
                      self.center_y + shadow_offset_y)

            Scale(1, shadow_scale_y, 1)

            Rotate(angle=self.rotation_angle, origin=(0, 0))
            Translate(-(self.center_x + shadow_offset_x),
                      -(self.center_y + shadow_offset_y))

            Color(0, 0, 0, shadow_alpha)
            Rectangle(texture=self.texture, pos=self.pos, size=self.size)
            PopMatrix()

            # 👇 МОНЕТА
            PushMatrix()
            Translate(self.center_x, self.center_y)
            Rotate(angle=self.rotation_angle, origin=(0, 0))
            Translate(-self.center_x, -self.center_y)
            Color(1.3, 1.3, 1.3, 1)
            Rectangle(texture=self.texture, pos=self.pos, size=self.size)
            PopMatrix()

    def _update_position(self, *args):
        """Обновляет позицию монеты на эллипсе"""
        # Центр эллипса
        center_x = 0.35
        center_y = 0.5

        self.pos_hint = {
            'center_x': center_x + self.ellipse_offset_x,
            'center_y': center_y + self.ellipse_offset_y
        }

    def start_animation(self, fps=60):
        """Запускает бесконечную анимацию вращения

        Args:
            fps: частота кадров
        """
        if not self.frames or self.is_animating:
            return
        self.is_animating = True
        self.current_frame = 0
        self.frame_duration = 1.0 / fps
        if self.anim_clock:
            self.anim_clock.cancel()
        self.anim_clock = Clock.schedule_interval(self.next_frame, self.frame_duration)

    def next_frame(self, dt):
        if not self.is_animating or not self.frames:
            return
        self.current_frame += 1
        if self.current_frame >= len(self.frames):
            self.current_frame = 0
            # НИКОГДА НЕ ОСТАНАВЛИВАЕМ АНИМАЦИЮ - ПРОСТО ПРОДОЛЖАЕМ ЦИКЛ
        self.texture = self.frames[self.current_frame]
        self._update_rotation()

    def stop_animation(self):
        """Останавливает анимацию принудительно"""
        self.is_animating = False
        if self.anim_clock:
            self.anim_clock.cancel()
            self.anim_clock = None
        # НЕ меняем текстуру здесь - это будет сделано в set_result

    def set_result(self, result):
        """Устанавливает финальный кадр (0 - орел, 1 - решка) на случайный кадр из соответствующей половины"""
        if not self.frames:
            return

        # Определяем диапазон кадров для орла и решки
        total_frames = len(self.frames)
        half_frames = total_frames // 2

        if result == 0:  # Орел - первая половина кадров
            # Выбираем случайный кадр из первой половины (0 до half_frames-1)
            random_frame = random.randint(0, half_frames - 1)
            self.texture = self.frames[random_frame]
            print(f"🎲 Орел: выбран кадр {random_frame + 1} из {half_frames}")
        else:  # Решка - вторая половина кадров
            # Выбираем случайный кадр из второй половины (half_frames до total_frames-1)
            random_frame = random.randint(half_frames, total_frames - 1)
            self.texture = self.frames[random_frame]
            print(f"🎲 Решка: выбран кадр {random_frame + 1} из {total_frames}")

        self._update_rotation()

class CoinScreen(BaseGameScreen):
    """Игровой экран с монетой из спрайт-листа"""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self.background_image = 'assets/backgrounds/coin_bg.png'
        self.spritesheet_path = 'assets/images/coin/spritesheet_1.png'

        self.coin = None
        self.touch_area = None
        self.info_label = None
        self.stats_label = None

        self.total_flips = 0
        self.heads_count = 0
        self.tails_count = 0

    def on_enter(self):
        super().on_enter()
        self.setup_game_ui()
        Window.bind(on_resize=self.on_window_resize)

    def on_leave(self):
        super().on_leave()
        Window.unbind(on_resize=self.on_window_resize)

    def on_window_resize(self, instance, width, height):
        pass

    def check_file(self, path):
        if os.path.exists(path):
            print(f"✅ Файл найден: {path}")
            return True
        else:
            print(f"❌ Файл НЕ найден: {path}")
            return False

    def setup_game_ui(self):
        self.check_file(self.spritesheet_path)

        # Параметры эллипса (для анимации)
        a = 0.15  # Полуось по X (оставляем без изменений)
        center_x = 0.35  # Центр эллипса (оставляем без изменений)

        # Смещение изображения монеты влево на 0.02
        image_shift = 0.02  # 👈 СМЕЩЕНИЕ ИЗОБРАЖЕНИЯ ВЛЕВО

        # СОЗДАЕМ МОНЕТУ - СРАЗУ В ЛЕВОЙ ТОЧКЕ ЭЛЛИПСА + ДОПОЛНИТЕЛЬНОЕ СМЕЩЕНИЕ
        self.coin = SpritesheetCoin(
            spritesheet_path=self.spritesheet_path,
            frame_width=64,
            frame_height=64,
            cols=5,
            rows=4,
            total_frames=19,
            rotation_angle=-90,
            size_hint=(None, None),
            size=(110, 110),
            # Начальная позиция: (центр эллипса - a) - image_shift (смещение влево)
            pos_hint={'center_x': center_x - a - image_shift, 'center_y': 0.5},
            allow_stretch=True
        )
        self.layout.add_widget(self.coin)

        # ОБЛАСТЬ НАЖАТИЯ (должна остаться там же, где монета)
        self.touch_area = TouchArea(
            size_hint=(0.4, 0.4),
            # Область нажатия тоже смещаем, чтобы она была над монетой
            pos_hint={'center_x': center_x - a - image_shift, 'center_y': 0.5},
        )
        self.layout.add_widget(self.touch_area)

        # Привязываем обработчик касания
        self.touch_area.bind(on_touch_down=self.on_area_touch)

        # ИНФОРМАЦИЯ
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

        # СТАТИСТИКА
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

        # ВЫСОКАЯ СКОРОСТЬ ВРАЩЕНИЯ (60 FPS)
        fps = 60

        print(f"⏱️ Длительность движения: 7 сек, Вращение: постоянное 60 FPS (бесконечное)")

        # СОЗДАЕМ АНИМАЦИЮ ДВИЖЕНИЯ ПО ВЕРТИКАЛЬНОЙ СПИРАЛИ (ЭЛЛИПС)
        spiral_anim = self.create_vertical_spiral_animation(duration=7.0)

        # ЗАПУСКАЕМ АНИМАЦИЮ ДВИЖЕНИЯ
        spiral_anim.start(self.coin)

        # ЗАПУСКАЕМ БЕСКОНЕЧНОЕ ВРАЩЕНИЕ (БЕЗ ПАРАМЕТРА infinite)
        self.coin.start_animation(fps=fps)

        def finish_animation(dt):
            # ПРИНУДИТЕЛЬНО ОСТАНАВЛИВАЕМ АНИМАЦИЮ ВРАЩЕНИЯ
            self.coin.stop_animation()
            self.coin.set_result(result)
            self.coin.ellipse_offset_x = 0
            self.coin.ellipse_offset_y = 0

        Clock.schedule_once(finish_animation, 7.0)

    def create_vertical_spiral_animation(self, duration=7.0):
        """Создает анимацию движения по вертикальной спирали (эллипс)"""
        steps = 140  # Больше шагов для плавности

        anim = Animation(duration=0)

        # Параметры вертикального эллипса
        a = 0.15  # Полуось по X (горизонтальная)
        b = 0.4  # Полуось по Y (вертикальная) - эллипс вытянут вертикально

        for i in range(steps):
            t = i / steps  # Время от 0 до 1

            # Радиус уменьшается от 1 до 0 (спираль сжимается к центру)
            radius_factor = 1 - t

            # 👇 ИЗМЕНЕНО: добавляем Pi к углу, чтобы начать с левой точки (cos(pi) = -1)
            angle = math.pi + t * 8 * math.pi  # 4 полных оборота, начиная с левой точки

            # Координаты на вертикальном эллипсе
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
        super().go_to_menu()