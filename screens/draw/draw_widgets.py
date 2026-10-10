# screens/draw/draw_widgets.py
"""
Вспомогательные классы для экрана жеребьёвки:
- SpriteSheet — нарезка спрайтлистов
- BallSprite — данные одного шара
- SpriteObject + CollisionCircle — колышек на доске и его хитбокс
- BarrierRenderer — анимация створок барьера
- WaveEffect — круговая волна от двойного клика
- Bucket — данные одной корзины (без рендера, только для физики и результатов)
- ResultsList — прокручиваемый список результатов
"""

import os
import math
import random

import numpy as np
from PIL import Image as PILImage

from kivy.clock import Clock
from kivy.core.image import Image as CoreImage
from kivy.core.window import Window
from kivy.graphics import Color, Ellipse, Line, Rectangle
from kivy.graphics.texture import Texture
from kivy.metrics import sp
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.scrollview import ScrollView
from kivy.uix.widget import Widget
from kivy.vector import Vector


class SpriteSheet:
    def __init__(self, sheet_path, rows, cols, frame_width, frame_height, name=""):
        self.sheet_path = sheet_path
        self.rows = rows
        self.cols = cols
        self.frame_width = frame_width
        self.frame_height = frame_height
        self.name = name
        self.textures = {}
        self.load_and_split()

    def load_and_split(self):
        try:
            if not os.path.exists(self.sheet_path):
                print(f"⚠️ [{self.name}] Файл не найден: {self.sheet_path}")
                return

            pil_image = PILImage.open(self.sheet_path).convert('RGBA')
            pixels = np.array(pil_image)

            img_height, img_width = pixels.shape[:2]
            expected_height = self.rows * self.frame_height
            expected_width = self.cols * self.frame_width

            print(f"📐 [{self.name}] Ожидаемый размер: {expected_width}x{expected_height}")
            print(f"📐 [{self.name}] Фактический размер: {img_width}x{img_height}")

            if img_height < expected_height or img_width < expected_width:
                print(f"⚠️ [{self.name}] Размеры меньше ожидаемых")
                actual_rows = min(self.rows, img_height // self.frame_height)
                actual_cols = min(self.cols, img_width // self.frame_width)
            else:
                actual_rows = self.rows
                actual_cols = self.cols

            print(f"📐 [{self.name}] Загружаем {actual_rows}x{actual_cols} кадров")

            for row in range(actual_rows):
                for col in range(actual_cols):
                    x1 = col * self.frame_width
                    y1 = row * self.frame_height
                    frame_pixels = pixels[y1:y1 + self.frame_height, x1:x1 + self.frame_width]
                    frame_pixels_flipped = np.flipud(frame_pixels)

                    texture = Texture.create(size=(self.frame_width, self.frame_height), colorfmt='rgba')
                    texture.blit_buffer(frame_pixels_flipped.tobytes(), colorfmt='rgba', bufferfmt='ubyte')
                    self.textures[(row, col)] = texture

            print(f"✅ [{self.name}] Загружено {len(self.textures)} кадров из {actual_rows * actual_cols}")
        except Exception as e:
            print(f"⚠️ [{self.name}] Ошибка: {e}")
            import traceback
            traceback.print_exc()

    def get_frame_texture(self, row, col):
        if not self.textures:
            return None
        if 0 <= row < self.rows and 0 <= col < self.cols:
            return self.textures.get((row, col))
        return None


class BarrierRenderer:
    """Рендерит барьер как ДВЕ створки.
    Каждая створка — половина кадра спрайтлиста.
    """

    sprite_sheet = None
    total_frames = 48

    FRAME_PAIRS = {
        0:  (0,  0),
        1:  (0,  8),
        2:  (8,  8),
        3:  (8,  16),
        4:  (16, 16),
        5:  (16, 24),
        6:  (24, 24),
        7:  (24, 32),
        8:  (32, 32),
        9:  (32, 40),
        10: (40, 40),
    }

    def __init__(self, board_ref=None):
        self.board_ref = board_ref

        self.frame_L = 0
        self.frame_R = 0
        self.target_frame_L = 0
        self.target_frame_R = 0

        self._is_opening = False
        self._is_closing = False
        self._animation_timer = None
        self._opening_callback = None
        self._closing_callback = None

        self.load_spritesheet()

    def load_spritesheet(self):
        try:
            sheet_path = 'assets/sprites/barrier_spritesheet.png'
            if os.path.exists(sheet_path):
                if BarrierRenderer.sprite_sheet is None:
                    test_img = PILImage.open(sheet_path)
                    img_width, img_height = test_img.size
                    frame_width = img_width // 1
                    frame_height = img_height // 48

                    BarrierRenderer.sprite_sheet = SpriteSheet(
                        sheet_path, 48, 1, frame_width, frame_height, "Затворы"
                    )
                    BarrierRenderer.total_frames = 48
                    print(f"✅ Загружен спрайтлист затворов: {BarrierRenderer.total_frames} кадров")
            else:
                print(f"⚠️ Файл спрайтлиста затворов не найден: {sheet_path}")
        except Exception as e:
            print(f"⚠️ Ошибка загрузки спрайтлиста затворов: {e}")

    def get_frame_pair_for_teams(self, teams_count):
        teams_count = max(0, min(10, teams_count))
        return BarrierRenderer.FRAME_PAIRS.get(teams_count, (0, 0))

    @property
    def is_open(self):
        return self.frame_L > 0 or self.frame_R > 0

    def start_opening_animation(self, teams_count, callback=None):
        left_frame, right_frame = self.get_frame_pair_for_teams(teams_count)

        self.target_frame_L = left_frame
        self.target_frame_R = right_frame

        print(f"🎬 Барьер: teams={teams_count}, left→кадр {left_frame}, right→кадр {right_frame}")

        if self.frame_L == self.target_frame_L and self.frame_R == self.target_frame_R:
            if callback:
                callback()
            return

        self._is_opening = True
        self._is_closing = False
        self._opening_callback = callback
        self.stop_animation()
        self._animate_opening()

    def _animate_opening(self):
        if not self._is_opening:
            return

        changed = False
        if self.frame_L < self.target_frame_L:
            self.frame_L += 1
            changed = True
        if self.frame_R < self.target_frame_R:
            self.frame_R += 1
            changed = True

        if changed:
            if self.board_ref:
                self.board_ref.update_canvas()
            self._animation_timer = Clock.schedule_once(
                lambda dt: self._animate_opening(), 0.01
            )
        else:
            self._is_opening = False
            if self._opening_callback:
                cb = self._opening_callback
                self._opening_callback = None
                cb()

    def start_closing_animation(self, callback=None):
        self.target_frame_L = 0
        self.target_frame_R = 0

        if self.frame_L == 0 and self.frame_R == 0:
            if callback:
                callback()
            return

        self._is_closing = True
        self._is_opening = False
        self._closing_callback = callback
        self.stop_animation()
        self._animate_closing()

    def _animate_closing(self):
        if not self._is_closing:
            return

        changed = False
        if self.frame_L > 0:
            self.frame_L -= 1
            changed = True
        if self.frame_R > 0:
            self.frame_R -= 1
            changed = True

        if changed:
            if self.board_ref:
                self.board_ref.update_canvas()
            self._animation_timer = Clock.schedule_once(
                lambda dt: self._animate_closing(), 0.01
            )
        else:
            self._is_closing = False
            if self._closing_callback:
                cb = self._closing_callback
                self._closing_callback = None
                cb()

    def stop_animation(self):
        if self._animation_timer:
            self._animation_timer.cancel()
            self._animation_timer = None

    def get_left_texture(self):
        if not BarrierRenderer.sprite_sheet:
            return None
        return BarrierRenderer.sprite_sheet.get_frame_texture(self.frame_L, 0)

    def get_right_texture(self):
        if not BarrierRenderer.sprite_sheet:
            return None
        return BarrierRenderer.sprite_sheet.get_frame_texture(self.frame_R, 0)


class BallSprite:
    sprite_sheet = None
    total_rows = 6

    def __init__(self, color=(1, 0, 0, 1), radius=15, player_name="", sprite_row=None):
        self.color = color
        self.radius = radius
        self.player_name = player_name
        self.x = 0
        self.y = 0
        self.vx = 0
        self.vy = 0
        self.is_falling = True
        self.is_in_bucket = False
        self.bucket_id = -1
        self.frame_index = 5
        self.is_in_hopper = False
        self.is_settled = False
        self.is_transitioning = False
        self._fall_time = 0
        self._settle_timer = 0
        self.is_rolling_on_barrier = False

        if sprite_row is None:
            self.sprite_row = random.randint(0, self.total_rows - 1)
        else:
            self.sprite_row = sprite_row % self.total_rows

    def reset(self):
        self.is_falling = True
        self.is_in_bucket = False
        self.bucket_id = -1
        self.vx = 0
        self.vy = 0
        self.frame_index = 5
        self.is_in_hopper = False
        self.is_settled = False
        self.is_transitioning = False
        self._fall_time = 0
        self._settle_timer = 0
        self.is_rolling_on_barrier = False

    def update_frame(self):
        if abs(self.vx) < 0.5:
            self.frame_index = 5
        elif self.vx > 0:
            self.frame_index = min(11, 5 + int(abs(self.vx) / 2))
        else:
            self.frame_index = max(0, 5 - int(abs(self.vx) / 2))

    def get_texture(self):
        if not BallSprite.sprite_sheet:
            return None
        return BallSprite.sprite_sheet.get_frame_texture(self.sprite_row, self.frame_index)


class SpriteObject:
    sprite_sheet = None
    shadow_sheet = None

    def __init__(self, row, col, x, y, radius=20):
        self.x = x
        self.y = y
        self.radius = radius
        self.hit_count = 0
        self.is_hit = False
        self.hit_anim_timer = 0
        self._saved_frame_col = None
        self._swipe_reset_timer = None
        self._swipe_animation_timer = None

        if row % 2 == 0:
            self.frame_row = row
            self.frame_col = col
        else:
            self.frame_row = row
            self.frame_col = col + 1

        self.base_frame_col = self.frame_col
        self.column_index = col
        self.row_index = row

    def get_frame_texture(self):
        if not SpriteObject.sprite_sheet:
            return None
        if self._saved_frame_col is not None:
            col = self._saved_frame_col
        elif self.is_hit:
            col = min(self.base_frame_col + 1, SpriteObject.sprite_sheet.cols - 1)
        else:
            col = self.base_frame_col
        return SpriteObject.sprite_sheet.get_frame_texture(self.frame_row, col)

    def get_shadow_texture(self):
        if not SpriteObject.shadow_sheet:
            return None
        if self._saved_frame_col is not None:
            col = self._saved_frame_col
        elif self.is_hit:
            col = min(self.base_frame_col + 1, SpriteObject.shadow_sheet.cols - 1)
        else:
            col = self.base_frame_col
        return SpriteObject.shadow_sheet.get_frame_texture(self.frame_row, col)

    def hit(self):
        self.hit_count += 1
        self.is_hit = True
        self.hit_anim_timer = 0.3
        Clock.schedule_once(lambda dt: setattr(self, 'is_hit', False), 0.3)

    def set_swipe_frame(self, col_offset):
        if col_offset == 0:
            self._saved_frame_col = None
        else:
            new_col = self.base_frame_col + col_offset
            max_col = SpriteObject.sprite_sheet.cols - 1 if SpriteObject.sprite_sheet else 0
            self._saved_frame_col = max(0, min(max_col, new_col))

    def reset_swipe_frame(self):
        self._saved_frame_col = None
        if self._swipe_reset_timer:
            self._swipe_reset_timer.cancel()
            self._swipe_reset_timer = None
        if self._swipe_animation_timer:
            self._swipe_animation_timer.cancel()
            self._swipe_animation_timer = None

    def schedule_swipe_reset(self, delay=0.15):
        if self._swipe_reset_timer:
            self._swipe_reset_timer.cancel()
            self._swipe_reset_timer = None

        self._swipe_reset_timer = Clock.schedule_once(
            lambda dt: self.reset_swipe_frame(), delay
        )


class CollisionCircle:
    def __init__(self, x, y, radius, sprite_ref):
        self.x = x
        self.y = y
        self.radius = radius
        self.sprite_ref = sprite_ref
        self.is_active = True
        self.show_debug = False

    def check_collision(self, ball):
        dist = math.hypot(ball.x - self.x, ball.y - self.y)
        return dist < (self.radius + ball.radius)

    def get_bounce_direction(self, ball):
        dx = ball.x - self.x
        dy = ball.y - self.y
        dist = math.hypot(dx, dy)
        if dist == 0:
            return Vector(random.uniform(-1, 1), random.uniform(-1, 1)).normalize()
        return Vector(dx / dist, dy / dist)

    def hit(self):
        self.sprite_ref.hit()


class Bucket:
    """Данные одной корзины. Без рендера — только для физики и результатов."""

    def __init__(self, bucket_id, team_name, color, x, y, width=50, height=120):
        self.id = bucket_id
        self.team_name = team_name
        self.color = color
        self.x = x
        self.y = y
        self.width = width
        self.height = height
        self.balls = []
        self.is_full = False
        self.max_capacity = 10

    def add_ball(self, ball):
        if not self.is_full and len(self.balls) < self.max_capacity:
            self.balls.append(ball)
            ball.is_in_bucket = True
            ball.bucket_id = self.id
            if len(self.balls) >= self.max_capacity:
                self.is_full = True

    def clear(self):
        self.balls.clear()
        self.is_full = False


class ResultsList(ScrollView):
    """Виджет с прокручиваемым списком результатов"""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.do_scroll_x = False
        self.do_scroll_y = True
        self.bar_width = 5
        self.bar_color = (1, 1, 1, 0.3)
        self.bar_inactive_color = (1, 1, 1, 0.1)

        self.container = BoxLayout(
            orientation='vertical',
            size_hint_y=None,
            spacing=5,
            padding=10
        )
        self.container.bind(minimum_height=self.container.setter('height'))
        self.add_widget(self.container)

        self.results = []
        self._is_visible = False

    def update_results(self, buckets):
        self.container.clear_widgets()
        self.results.clear()

        for bucket in buckets:
            if bucket.balls:
                team_label = Label(
                    text=f"[b]{bucket.team_name}[/b]",
                    font_size=sp(28),
                    color=(1, 1, 1, 1),
                    size_hint_y=None,
                    height=sp(40),
                    markup=True,
                    halign='left'
                )
                team_label.bind(size=team_label.setter('text_size'))
                self.container.add_widget(team_label)

                for ball in bucket.balls:
                    player_label = Label(
                        text=f"   • {ball.player_name}",
                        font_size=sp(24),
                        color=(0.8, 0.8, 0.8, 1),
                        size_hint_y=None,
                        height=sp(30),
                        halign='left'
                    )
                    player_label.bind(size=player_label.setter('text_size'))
                    self.container.add_widget(player_label)

                separator = Widget(size_hint_y=None, height=sp(10))
                self.container.add_widget(separator)

    def show(self):
        self.opacity = 1
        self._is_visible = True

    def hide(self):
        self.opacity = 0
        self._is_visible = False


class WaveEffect:
    """Круговая волна от точки двойного клика.

    Невидимый расходящийся круг: при пересечении со спрайтом —
    запускает ту же анимацию, что и свайп.
    """

    def __init__(self, x, y, board_ref, speed=18.0, thickness=40.0):
        self.x = x
        self.y = y
        self.board_ref = board_ref
        self.radius = 0.0
        self.speed = speed
        self.thickness = thickness
        self.max_radius = math.hypot(Window.width, Window.height) * 1.1
        self.hit_sprites = set()
        self.is_alive = True
        self._tick_timer = None
        self.show_ring = False

    def update(self, dt=0.016):
        if not self.is_alive:
            return

        self.radius += self.speed

        for sprite in self.board_ref.sprites:
            if sprite in self.hit_sprites:
                continue

            dist = math.hypot(sprite.x - self.x, sprite.y - self.y)
            if dist <= self.radius + self.thickness * 0.5 and \
               dist >= self.radius - self.thickness * 0.5:
                self.hit_sprites.add(sprite)
                self.board_ref._animate_sprite_swipe(sprite)

        if self.radius > self.max_radius:
            self.is_alive = False
            if self._tick_timer:
                self._tick_timer.cancel()
                self._tick_timer = None
            if self in self.board_ref.active_waves:
                self.board_ref.active_waves.remove(self)
            self.board_ref.update_canvas()
            return

        self.board_ref.update_canvas()

    def draw(self, canvas):
        if not self.show_ring:
            return
        with canvas:
            Color(0.4, 0.9, 1.0, 0.5)
            Line(circle=(self.x, self.y, self.radius), width=2)
            Color(0.4, 0.9, 1.0, 0.2)
            Line(circle=(self.x, self.y, self.radius - self.thickness * 0.5), width=1)
            Line(circle=(self.x, self.y, self.radius + self.thickness * 0.5), width=1)