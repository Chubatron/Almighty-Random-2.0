# screens/draw/draw_board.py
"""
Виджет доски Гальтона:
- GaltonBoardWithHopper — лейка + доска + физика шаров + свайпы + барьер + волны

Виджет корзин удалён — данные корзин создаются в GaltonTable (draw_main.py).

Отладочная рамка (debug_widget) рисуется прямо в canvas доски,
как лейка, спрайты, барьер и шары. Координаты задаются коэффициентами
от границ доски. При скролле рамка едет вместе с доской автоматически.

Вместо рамки отображается кадр из 10_tubes.png (сетка 3x4).
При переходе между экранами проигрывается анимация кадров 0..11.
"""

import math
import random

from kivy.clock import Clock
from kivy.core.window import Window
from kivy.graphics import Color, Ellipse, Line, Rectangle
from kivy.metrics import sp
from kivy.properties import ObjectProperty
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.label import Label

from screens.draw.draw_widgets import (
    SpriteSheet, BallSprite, SpriteObject, CollisionCircle,
    BarrierRenderer, WaveEffect, Bucket,
)


class GaltonBoardWithHopper(FloatLayout):
    """Объединенный виджет: лейка + доска Гальтона с общей физикой"""

    on_ball_in_bucket = ObjectProperty(None)
    on_all_balls_in_buckets = ObjectProperty(None)

    SWIPE_RESET_DELAY = 0.2

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self.hopper_height_ratio = 0.9
        self.top_width_factor = 0.6
        self.bottom_width_factor = 0.1
        self.hopper_bottom_visible = True

        self.rows = 16
        self.cols = 11

        self.balls = []
        self.balls_in_hopper = []
        self.falling_balls = []
        self.balls_in_buckets_list = []

        self.sprites = []
        self.collision_circles = []
        self._generated = False

        self.gravity = 0.6
        self.damping = 0.3
        self.friction = 0.92
        self.resting_threshold = 0.05
        self.physics_running = False
        self.physics_update_timer = None

        self.is_dropping = False
        self.total_balls = 0
        self.balls_in_buckets_count = 0
        self._all_balls_in_buckets_called = False

        self.ball_radius = int(Window.width * 0.015)
        self.ball_radius = max(8, min(30, self.ball_radius))

        self.show_all_debug = False
        self.show_debug = False
        self.debug_color = (1, 0, 0, 0.15)
        self.debug_border_color = (1, 0, 0, 0.8)
        self.show_hopper_debug = False
        self.hopper_debug_color = (0, 1, 0, 0.15)
        self.hopper_debug_border_color = (0, 1, 0, 0.6)

        # === ОТЛАДОЧНЫЙ СПРАЙТ (часть canvas доски) ===
        self.show_debug_widget = True

        self.debug_widget_x_ratio = 0.0
        self.debug_widget_y_ratio = -0.3
        self.debug_widget_w_ratio = 1.0
        self.debug_widget_h_ratio = 0.3

        self.debug_widget_border_color = (0, 1, 0, 1)

        # Текстура текущего кадра из 10_tubes.png
        self.debug_sprite_texture = None

        # Спрайт-лист труб и состояние анимации кадров
        self._tubes_sheet = None
        self._tubes_rows = 4
        self._tubes_cols = 3
        self._debug_frame_index = 0
        self._debug_frame_timer = None
        self._debug_frame_sequence = []

        self.barrier_height = 0
        self.barrier_width = 0
        self.barrier_visible = True
        self.barrier_pos = (0, 0)
        self.barrier_size = (0, 0)
        self._barrier_opening_complete = False

        self.barrier_open_indices = set()

        self.active_waves = []
        self._wave_timer = None

        self._swipe_active = False
        self._swipe_start_x = 0
        self._swipe_start_y = 0
        self._swipe_frame_offset = 0
        self._swipe_animating = False
        self._swipe_reset_timer = None
        self._swipe_affected_sprites = set()
        self._swipe_current_sprite = None
        self._swipe_log_counter = 0
        self._swipe_log_interval = 3

        self.load_ball_sprites()
        self.load_sprite_sheets()
        self._load_debug_sprite()

        self.barrier_renderer = BarrierRenderer(board_ref=self)

        self.bind(size=self._update_layout, pos=self._update_layout)
        Clock.schedule_once(lambda dt: self._update_layout(), 0.1)

        self.bind(on_touch_down=self._on_swipe_touch_down)
        self.bind(on_touch_move=self._on_swipe_touch_move)
        self.bind(on_touch_up=self._on_swipe_touch_up)

    def load_ball_sprites(self):
        try:
            BallSprite.sprite_sheet = SpriteSheet(
                'assets/sprites/glass_ball_spritesheet_transparent.png',
                6, 12, 128, 128, "Шары"
            )
            if BallSprite.sprite_sheet:
                print(f"✅ Загружено {len(BallSprite.sprite_sheet.textures)} кадров для шаров")
        except Exception as e:
            print(f"⚠️ Ошибка загрузки спрайтлиста шаров: {e}")

    def load_sprite_sheets(self):
        try:
            SpriteObject.sprite_sheet = SpriteSheet(
                'assets/sprites/stick_b_a_transparent.png', 15, 12, 128, 128, "Основной"
            )
            SpriteObject.shadow_sheet = SpriteSheet(
                'assets/sprites/stick_shadow_spritesheet_transparent.png', 15, 12, 128, 128, "Тени"
            )
            if SpriteObject.sprite_sheet:
                print(f"✅ Основной: {len(SpriteObject.sprite_sheet.textures)} кадров")
            if SpriteObject.shadow_sheet:
                print(f"✅ Тени: {len(SpriteObject.shadow_sheet.textures)} кадров")
        except Exception as e:
            print(f"⚠️ Ошибка загрузки: {e}")

    def _load_debug_sprite(self):
        """Загружает спрайт-лист 10_tubes.png (сетка 3 колонки × 4 строки)."""
        print("🔍 [_load_debug_sprite] Начало загрузки 10_tubes.png")
        try:
            from PIL import Image as PILImage

            path = 'assets/sprites/10_tubes.png'
            print(f"🔍 [_load_debug_sprite] Путь: {path}")

            pil = PILImage.open(path)
            img_w, img_h = pil.size
            print(f"🔍 [_load_debug_sprite] Размер файла: {img_w}x{img_h}")

            cols, rows = 3, 4
            frame_w = img_w // cols
            frame_h = img_h // rows
            print(f"🔍 [_load_debug_sprite] Кадр: {frame_w}x{frame_h}, сетка {cols}x{rows}")

            sheet = SpriteSheet(path, rows, cols, frame_w, frame_h, "Tubes")
            self._tubes_sheet = sheet
            self._tubes_rows = rows
            self._tubes_cols = cols

            self._debug_frame_index = 0
            self.debug_sprite_texture = sheet.get_frame_texture(0, 0)

            if self.debug_sprite_texture:
                print(f"✅ [_load_debug_sprite] Загружено кадров: {len(sheet.textures)}")
                print(f"✅ [_load_debug_sprite] Первый кадр получен: {self.debug_sprite_texture}")
            else:
                print("⚠️ [_load_debug_sprite] Первый кадр НЕ получен")
        except Exception as e:
            print(f"⚠️ [_load_debug_sprite] Ошибка: {e}")
            import traceback
            traceback.print_exc()
            self._tubes_sheet = None
            self.debug_sprite_texture = None
        print("🔍 [_load_debug_sprite] Конец")

    def _get_tube_frame_texture(self, index):
        """Текстура кадра по индексу 0..11 (слева направо, сверху вниз)."""
        if not self._tubes_sheet:
            print(f"⚠️ [_get_tube_frame_texture] _tubes_sheet = None (index={index})")
            return None
        total = self._tubes_rows * self._tubes_cols
        if total <= 0:
            print(f"⚠️ [_get_tube_frame_texture] total <= 0 (rows={self._tubes_rows}, cols={self._tubes_cols})")
            return None
        index = index % total
        row = index // self._tubes_cols
        col = index % self._tubes_cols
        tex = self._tubes_sheet.get_frame_texture(row, col)
        if tex is None:
            print(f"⚠️ [_get_tube_frame_texture] Нет текстуры для index={index} (row={row}, col={col})")
        return tex

    def set_debug_frame(self, index):
        """Устанавливает отладочный кадр по индексу и перерисовывает canvas."""
        tex = self._get_tube_frame_texture(index)
        if tex is None:
            print(f"⚠️ [set_debug_frame] tex = None для index={index}, пропускаем")
            return
        total = self._tubes_rows * self._tubes_cols
        self._debug_frame_index = index % total
        self.debug_sprite_texture = tex
        print(f"🎞️ [set_debug_frame] Показан кадр {self._debug_frame_index} (из {total})")
        self.update_canvas()

    def stop_debug_sprite_animation(self):
        """Останавливает анимацию кадров, НЕ сбрасывая текущий кадр."""
        if self._debug_frame_timer:
            print("🛑 [stop_debug_sprite_animation] Отменяю таймер")
            self._debug_frame_timer.cancel()
            self._debug_frame_timer = None
        else:
            print("🛑 [stop_debug_sprite_animation] Таймера не было")
        self._debug_frame_sequence = []

    def play_transition_debug_animation(self, step_time=0.05):
        """Проигрывает кадры 0..11 во время перехода между экранами."""
        print("=" * 50)
        print("▶️ [play_transition_debug_animation] ВЫЗВАН")

        if not self._tubes_sheet:
            print("⚠️ [play_transition_debug_animation] _tubes_sheet = None — выход")
            return

        total = self._tubes_rows * self._tubes_cols
        print(f"▶️ [play_transition_debug_animation] total кадров = {total}")
        if total <= 0:
            print("⚠️ [play_transition_debug_animation] total <= 0 — выход")
            return

        self.stop_debug_sprite_animation()

        self._debug_frame_sequence = list(range(total))
        print(f"▶️ [play_transition_debug_animation] Очередь: {self._debug_frame_sequence}")

        first = self._debug_frame_sequence.pop(0)
        self.set_debug_frame(first)
        print(f"▶️ [play_transition_debug_animation] Первый кадр {first} показан, "
              f"в очереди осталось {len(self._debug_frame_sequence)}")

        def _next(dt):
            print(f"⏱️ [play_transition_debug_animation._next] dt={dt}, "
                  f"очередь={self._debug_frame_sequence}")
            if not self._debug_frame_sequence:
                print("✅ [play_transition_debug_animation] Анимация завершена")
                self._debug_frame_timer = None
                return
            idx = self._debug_frame_sequence.pop(0)
            self.set_debug_frame(idx)
            if self._debug_frame_sequence:
                self._debug_frame_timer = Clock.schedule_once(_next, step_time)
            else:
                print("✅ [play_transition_debug_animation] Последний кадр показан")
                self._debug_frame_timer = None

        if self._debug_frame_sequence:
            print(f"⏱️ [play_transition_debug_animation] Ставлю таймер на {step_time} с")
            self._debug_frame_timer = Clock.schedule_once(_next, step_time)
        else:
            print("✅ [play_transition_debug_animation] Всего 1 кадр, анимация не нужна")
        print("=" * 50)

    def _update_layout(self, *args):
        if self.width == 0 or self.height == 0:
            return

        self._generate_board()
        self._update_barrier_position()
        self.update_canvas()

    def _update_barrier_position(self):
        screen_width = Window.width
        screen_height = Window.height

        self.barrier_height = screen_height * 0.03
        self.barrier_width = screen_width
        bar_y = self.y - self.barrier_height / 2

        self.barrier_pos = (0, bar_y)
        self.barrier_size = (self.barrier_width, self.barrier_height)

    def _get_hopper_bottom_y(self):
        return self.y + self.height * self.hopper_height_ratio

    def _get_hopper_top_y(self):
        return self.y + self.height

    def _get_hopper_width_at_y(self, y):
        top_y = self._get_hopper_top_y()
        bottom_y = self._get_hopper_bottom_y()

        top_width = self.width * self.top_width_factor
        bottom_width = self.width * self.bottom_width_factor

        if y >= top_y:
            return top_width
        if y <= bottom_y:
            return bottom_width

        t = (top_y - y) / (top_y - bottom_y)
        return top_width - (top_width - bottom_width) * t

    def _get_hopper_left_wall(self, y):
        return self.x + (self.width - self._get_hopper_width_at_y(y)) / 2

    def _get_hopper_right_wall(self, y):
        return self.x + (self.width + self._get_hopper_width_at_y(y)) / 2

    def _generate_board(self, *args):
        self.sprites.clear()
        self.collision_circles.clear()
        self._generated = False

        if self.width == 0 or self.height == 0:
            return

        board_top = self._get_hopper_bottom_y()
        board_bottom = self.y

        board_height = board_top - board_bottom
        if board_height <= 0:
            return

        spacing_x = self.width / (self.cols - 1)
        sprite_radius = max(35, min(100, spacing_x * 0.7))
        spacing_y = max(35, min(120, board_height / self.rows))
        sprite_radius = min(sprite_radius, spacing_y * 0.7)
        circle_radius = sprite_radius * 0.2

        start_x = self.x
        start_y = board_top - sprite_radius

        for row in range(self.rows):
            if row == self.rows - 1:
                continue

            count = self.cols if row % 2 == 0 else self.cols - 1
            row_start_x = start_x if row % 2 == 0 else start_x + spacing_x / 2

            for col in range(count):
                x = row_start_x + col * spacing_x
                y = start_y - row * spacing_y

                if y < board_bottom:
                    break

                sprite = SpriteObject(row, col, x, y, sprite_radius)
                self.sprites.append(sprite)
                self.collision_circles.append(CollisionCircle(x, y, circle_radius, sprite))

        self._generated = True

    def update_canvas(self, *args):
        self.canvas.clear()
        if self.width == 0 or self.height == 0:
            return

        if self.show_all_debug and self.show_debug:
            with self.canvas:
                Color(*self.debug_color)
                Rectangle(pos=self.pos, size=self.size)
                Color(*self.debug_border_color)
                Line(rectangle=(self.x, self.y, self.width, self.height), width=2)

        with self.canvas:
            Color(0.2, 0.2, 0.4, 0.05)
            Rectangle(pos=self.pos, size=self.size)

        self._draw_hopper()
        self._draw_sprites()
        self._draw_shadows()
        self._draw_barrier()
        self._draw_balls()
        self._draw_waves()

        if self.show_all_debug and self.show_debug:
            self._draw_debug_info()

        self._draw_debug_widget()

    def _draw_waves(self):
        for wave in self.active_waves:
            wave.draw(self.canvas)

    def _draw_barrier(self):
        if not self.barrier_renderer:
            return

        left_tex = self.barrier_renderer.get_left_texture()
        right_tex = self.barrier_renderer.get_right_texture()

        if not left_tex and not right_tex:
            return

        full_w = self.barrier_width
        full_h = self.barrier_height
        full_y = self.barrier_pos[1]
        half_w = full_w / 2

        with self.canvas:
            Color(1, 1, 1, 1)

            if left_tex:
                Rectangle(
                    pos=(0, full_y),
                    size=(half_w, full_h),
                    texture=left_tex,
                    tex_coords=(0.0, 0.0, 0.5, 0.0, 0.5, 1.0, 0.0, 1.0)
                )

            if right_tex:
                Rectangle(
                    pos=(half_w, full_y),
                    size=(half_w, full_h),
                    texture=right_tex,
                    tex_coords=(0.5, 0.0, 1.0, 0.0, 1.0, 1.0, 0.5, 1.0)
                )

            if self.show_all_debug and self.show_debug:
                Color(1, 0.8, 0, 0.5)
                Line(rectangle=(0, full_y, half_w, full_h), width=1, dash_length=5, dash_offset=2)
                Line(rectangle=(half_w, full_y, half_w, full_h), width=1, dash_length=5, dash_offset=2)

    def _draw_hopper(self):
        top_y = self._get_hopper_top_y()
        bottom_y = self._get_hopper_bottom_y()

        center_x = self.x + self.width / 2
        top_width = self.width * self.top_width_factor
        bottom_width = self.width * self.bottom_width_factor

        points = [
            center_x - top_width / 2, top_y,
            center_x + top_width / 2, top_y,
            center_x + bottom_width / 2, bottom_y,
            center_x - bottom_width / 2, bottom_y,
        ]

        with self.canvas:
            if self.show_all_debug and self.show_hopper_debug:
                Color(*self.hopper_debug_color)
                from kivy.graphics import Triangle
                vertices1 = [points[0], points[1], points[2], points[3], points[6], points[7]]
                vertices2 = [points[2], points[3], points[4], points[5], points[6], points[7]]
                Triangle(points=vertices1)
                Triangle(points=vertices2)
                Color(*self.hopper_debug_border_color)
                Line(points=[points[0], points[1], points[2], points[3]], width=2)
                Line(points=[points[2], points[3], points[4], points[5]], width=2)
                Line(points=[points[6], points[7], points[0], points[1]], width=2)
                if self.hopper_bottom_visible:
                    Line(points=[points[4], points[5], points[6], points[7]], width=3)

            Color(0.0, 0.8, 1.0, 0.1)
            from kivy.graphics import Triangle
            vertices1 = [points[0], points[1], points[2], points[3], points[6], points[7]]
            vertices2 = [points[2], points[3], points[4], points[5], points[6], points[7]]
            Triangle(points=vertices1)
            Triangle(points=vertices2)

            Color(0.0, 0.8, 1.0, 0.8)
            Line(points=[points[0], points[1], points[2], points[3]], width=2)
            Line(points=[points[2], points[3], points[4], points[5]], width=2)
            Line(points=[points[6], points[7], points[0], points[1]], width=2)

            if self.hopper_bottom_visible:
                Color(0.0, 0.8, 1.0, 0.8)
                Line(points=[points[4], points[5], points[6], points[7]], width=3)

    def _draw_sprites(self):
        if not SpriteObject.sprite_sheet:
            return
        for sprite in self.sprites:
            texture = sprite.get_frame_texture()
            if texture:
                size = sprite.radius * 2
                with self.canvas:
                    Color(1, 1, 1, 1)
                    Rectangle(pos=(sprite.x - size / 2, sprite.y - size / 2),
                              size=(size, size), texture=texture)

    def _draw_shadows(self):
        if not SpriteObject.shadow_sheet:
            return
        for sprite in self.sprites:
            texture = sprite.get_shadow_texture()
            if texture:
                size = sprite.radius * 2
                with self.canvas:
                    Color(1, 1, 1, 0.5)
                    Rectangle(pos=(sprite.x - size / 2, sprite.y - size / 2),
                              size=(size, size), texture=texture)

    def _draw_balls(self):
        sorted_balls = sorted(self.balls_in_hopper, key=lambda b: b.y, reverse=True)
        for ball in sorted_balls:
            self._draw_single_ball(ball)

        for ball in self.falling_balls:
            if not ball.is_in_bucket:
                self._draw_single_ball(ball)

    def _draw_single_ball(self, ball):
        if ball.y < self.y:
            alpha = max(0, (ball.y - self.y + ball.radius * 2) / (ball.radius * 2))
        else:
            alpha = 1.0

        if BallSprite.sprite_sheet:
            texture = ball.get_texture()
            if texture:
                size = ball.radius * 8
                with self.canvas:
                    Color(0, 0, 0, 0.2 * alpha)
                    Ellipse(pos=(ball.x - ball.radius - 2, ball.y - ball.radius - 2),
                            size=(ball.radius * 2 + 4, ball.radius * 2 + 4))
                    Color(1, 1, 1, alpha)
                    Rectangle(pos=(ball.x - size / 2, ball.y - size / 2),
                              size=(size, size), texture=texture)
        else:
            with self.canvas:
                Color(0, 0, 0, 0.2 * alpha)
                Ellipse(pos=(ball.x - ball.radius - 1, ball.y - ball.radius - 1),
                        size=(ball.radius * 2 + 2, ball.radius * 2 + 2))
                Color(*ball.color[0:3], alpha)
                Ellipse(pos=(ball.x - ball.radius, ball.y - ball.radius),
                        size=(ball.radius * 2, ball.radius * 2))

    def _draw_debug_info(self):
        with self.canvas:
            Color(1, 1, 0, 0.5)
            bottom_y = self._get_hopper_bottom_y()
            Line(points=[self.x, bottom_y, self.x + self.width, bottom_y], width=1, dash_length=5)

            Color(1, 1, 1, 0.8)
            info_text = [
                f"Hopper: {len(self.balls_in_hopper)}",
                f"Falling: {len(self.falling_balls)}",
                f"Total: {self.total_balls}",
                f"In buckets: {self.balls_in_buckets_count}",
                f"Barrier L={self.barrier_renderer.frame_L} R={self.barrier_renderer.frame_R}",
                f"Open idx: {sorted(self.barrier_open_indices)}",
                f"Waves: {len(self.active_waves)}"
            ]

            y_pos = self.y + self.height - 15
            for line in info_text:
                Color(0, 0, 0, 0.7)
                Rectangle(pos=(self.x + 5, y_pos - 10), size=(len(line) * 6, 12))
                Color(1, 1, 1, 0.9)
                y_pos -= 14

    def _draw_debug_widget(self):
        """Рисует текущий кадр из 10_tubes.png с рамкой вокруг него."""
        if not self.show_debug_widget:
            return
        if self.width == 0 or self.height == 0:
            return
        if not self.debug_sprite_texture:
            return

        x = self.x + self.debug_widget_x_ratio * self.width
        y = self.y + self.debug_widget_y_ratio * self.height
        w = self.debug_widget_w_ratio * self.width
        h = self.debug_widget_h_ratio * self.height

        with self.canvas:
            Color(1, 1, 1, 1)
            Rectangle(
                pos=(x, y),
                size=(w, h),
                texture=self.debug_sprite_texture
            )
            Color(*self.debug_widget_border_color)
            Line(rectangle=(x, y, w, h), width=2)

    # ==================== ВОЛНЫ ====================

    def spawn_wave(self, x, y):
        wave = WaveEffect(x, y, self)
        self.active_waves.append(wave)

        if self._wave_timer is None:
            self._wave_timer = Clock.schedule_interval(self._tick_waves, 1 / 60.0)

        print(f"🌊 Волна из ({x:.0f}, {y:.0f})")

    def _tick_waves(self, dt):
        if not self.active_waves:
            if self._wave_timer:
                self._wave_timer.cancel()
                self._wave_timer = None
            return

        for wave in list(self.active_waves):
            wave.update(dt)

    # ==================== БАРЬЕР ====================

    def animate_barrier_for_buckets(self, teams_count, callback=None):
        if not self.barrier_renderer:
            if callback:
                callback()
            return

        total = 10
        teams_count = max(0, min(total, teams_count))

        start = (total - teams_count + 1) // 2
        end = start + teams_count
        self.barrier_open_indices = set(range(start, end))

        print(f"🔓 Открытые корзины: {sorted(self.barrier_open_indices)} (teams={teams_count})")

        self.barrier_renderer.stop_animation()
        self.barrier_renderer.start_opening_animation(teams_count, callback)
        self._barrier_opening_complete = False

    def animate_barrier_close(self, callback=None):
        if not self.barrier_renderer:
            if callback:
                callback()
            return

        self.barrier_open_indices = set()
        self.barrier_renderer.stop_animation()
        self.barrier_renderer.start_closing_animation(callback)

    # ==================== ШАРЫ И ФИЗИКА ====================

    def add_ball(self, color, player_name="", sprite_row=None):
        ball = BallSprite(color, self.ball_radius, player_name, sprite_row)
        ball.is_in_hopper = True
        ball.is_settled = False

        center_x = self.x + self.width / 2
        top_y = self._get_hopper_top_y()

        ball_count = len(self.balls_in_hopper)
        offset_x = (ball_count % 5) * 20 - 40
        offset_y = (ball_count // 5) * 25

        ball.x = center_x + offset_x + random.uniform(-10, 10)
        ball.y = top_y - 20 - offset_y + random.uniform(-5, 5)

        ball.vx = random.uniform(-0.3, 0.3)
        ball.vy = random.uniform(-0.3, 0.3)

        self.balls.append(ball)
        self.balls_in_hopper.append(ball)
        self.total_balls += 1

        self._start_physics()
        self.update_canvas()
        return ball

    def reset_balls_positions(self):
        if not self.balls_in_hopper:
            return

        center_x = self.x + self.width / 2
        top_y = self._get_hopper_top_y()

        for i, ball in enumerate(self.balls_in_hopper):
            cols = 5
            row = i // cols
            col = i % cols

            ball.x = center_x + (col - cols / 2) * 25 + random.uniform(-5, 5)
            ball.y = top_y - 20 - row * 28 + random.uniform(-5, 5)
            ball.vx = 0
            ball.vy = 0
            ball.is_settled = False
            ball.is_falling = False
            ball.is_rolling_on_barrier = False

        self.update_canvas()

    def add_balls_batch(self, balls):
        for ball in balls:
            self.add_ball(ball.color, ball.player_name, ball.sprite_row)

    def start_dropping(self):
        if self.is_dropping:
            return

        if not self.balls_in_hopper:
            print("⚠️ Нет шаров в лейке!")
            return

        self.is_dropping = True
        self.hopper_bottom_visible = False

        for ball in self.balls_in_hopper[:]:
            ball.is_in_hopper = False
            ball.is_falling = True
            ball.is_settled = False
            ball.is_rolling_on_barrier = False

            ball.vx = random.uniform(-0.5, 0.5)
            ball.vy = 0.5

            self.balls_in_hopper.remove(ball)
            self.falling_balls.append(ball)

        self.update_canvas()
        self._start_physics()

    def _update_physics(self, dt):
        self._update_hopper_physics()
        self._update_falling_physics()

    def _update_hopper_physics(self):
        if not self.balls_in_hopper:
            return

        bottom_y = self._get_hopper_bottom_y()
        top_y = self._get_hopper_top_y()

        for ball in self.balls_in_hopper:
            if ball.is_settled:
                continue

            ball.vy += self.gravity * 0.15
            ball.vx *= self.friction
            ball.x += ball.vx
            ball.y -= ball.vy

            if ball.y + ball.radius > top_y:
                ball.y = top_y - ball.radius
                ball.vy = abs(ball.vy) * 0.3

            left_wall = self._get_hopper_left_wall(ball.y)
            right_wall = self._get_hopper_right_wall(ball.y)

            if ball.x - ball.radius < left_wall:
                ball.x = left_wall + ball.radius
                ball.vx = abs(ball.vx) * self.damping * 0.5
            if ball.x + ball.radius > right_wall:
                ball.x = right_wall - ball.radius
                ball.vx = -abs(ball.vx) * self.damping * 0.5

            if self.hopper_bottom_visible:
                if ball.y - ball.radius < bottom_y:
                    ball.y = bottom_y + ball.radius
                    ball.vy *= -0.1
                    ball.vx *= 0.5
                    if abs(ball.vy) < 0.8 and abs(ball.vx) < 0.8:
                        ball.vy = 0
                        ball.vx = 0
                        ball.is_settled = True

        for i in range(len(self.balls_in_hopper)):
            for j in range(i + 1, len(self.balls_in_hopper)):
                ball1 = self.balls_in_hopper[i]
                ball2 = self.balls_in_hopper[j]

                speed1 = math.hypot(ball1.vx, ball1.vy)
                speed2 = math.hypot(ball2.vx, ball2.vy)
                if speed1 < 0.3 and speed2 < 0.3:
                    continue

                dx = ball1.x - ball2.x
                dy = ball1.y - ball2.y
                dist = math.hypot(dx, dy)
                min_dist = ball1.radius + ball2.radius

                if dist < min_dist and dist > 0:
                    nx = dx / dist
                    ny = dy / dist

                    overlap = min_dist - dist
                    overlap_half = overlap * 0.5

                    ball1.x += nx * overlap_half
                    ball1.y += ny * overlap_half
                    ball2.x -= nx * overlap_half
                    ball2.y -= ny * overlap_half

                    if abs(ny) > 0.5:
                        if ball1.y > ball2.y:
                            ball1.y = ball2.y + ball1.radius + ball2.radius
                        else:
                            ball2.y = ball1.y + ball1.radius + ball2.radius

                        ball1.vy *= 0.1
                        ball1.vx *= 0.8
                        ball2.vy *= 0.1
                        ball2.vx *= 0.8

                    for ball in [ball1, ball2]:
                        left_wall = self._get_hopper_left_wall(ball.y)
                        right_wall = self._get_hopper_right_wall(ball.y)

                        if ball.x - ball.radius < left_wall:
                            ball.x = left_wall + ball.radius
                            ball.vx = abs(ball.vx) * self.damping * 0.5
                        if ball.x + ball.radius > right_wall:
                            ball.x = right_wall - ball.radius
                            ball.vx = -abs(ball.vx) * self.damping * 0.5

                        if self.hopper_bottom_visible:
                            if ball.y - ball.radius < bottom_y:
                                ball.y = bottom_y + ball.radius
                                ball.vy *= -0.1
                                ball.vx *= 0.5
                                if abs(ball.vy) < 0.8 and abs(ball.vx) < 0.8:
                                    ball.vy = 0
                                    ball.vx = 0
                                    ball.is_settled = True

                    dvx = ball1.vx - ball2.vx
                    dvy = ball1.vy - ball2.vy
                    dvn = dvx * nx + dvy * ny

                    if dvn < 0:
                        restitution = 0.05
                        impulse = -(1 + restitution) * dvn / 2

                        ball1.vx += impulse * nx
                        ball1.vy += impulse * ny
                        ball2.vx -= impulse * nx
                        ball2.vy -= impulse * ny

                        ball1.vx *= 0.5
                        ball1.vy *= 0.5
                        ball2.vx *= 0.5
                        ball2.vy *= 0.5

                        if abs(ball1.vx) < 0.3 and abs(ball1.vy) < 0.3:
                            ball1.vx = 0
                            ball1.vy = 0
                            if self.hopper_bottom_visible and ball1.y - ball1.radius <= bottom_y + 2:
                                ball1.is_settled = True

                        if abs(ball2.vx) < 0.3 and abs(ball2.vy) < 0.3:
                            ball2.vx = 0
                            ball2.vy = 0
                            if self.hopper_bottom_visible and ball2.y - ball2.radius <= bottom_y + 2:
                                ball2.is_settled = True

        if self.hopper_bottom_visible:
            for ball in self.balls_in_hopper:
                if not ball.is_settled:
                    speed = math.hypot(ball.vx, ball.vy)
                    if speed < 0.5 and ball.y - ball.radius <= bottom_y + 2:
                        ball.vx = 0
                        ball.vy = 0
                        ball.is_settled = True

        self.update_canvas()

    def _is_ball_over_open_bucket(self, ball_x):
        if not (hasattr(self, 'buckets_ref') and self.buckets_ref):
            return True

        buckets = self.buckets_ref
        if not buckets:
            return True

        nearest = min(range(len(buckets)), key=lambda i: abs(ball_x - buckets[i].x))
        return nearest in self.barrier_open_indices

    def _apply_barrier_collision(self, ball):
        if not self.barrier_renderer or not self.barrier_renderer.is_open:
            return False

        barrier_center_y = self.barrier_pos[1] + self.barrier_height / 2

        ball_bottom = ball.y - ball.radius
        if ball_bottom > barrier_center_y + ball.radius:
            return False

        if ball.y < barrier_center_y - ball.radius:
            return False

        if self._is_ball_over_open_bucket(ball.x):
            ball.is_rolling_on_barrier = False
            return False

        ball.is_rolling_on_barrier = True
        ball.y = barrier_center_y + ball.radius

        if ball.vy < 0:
            ball.vy = 0

        if ball.vx > 0.1:
            ball.vx = max(ball.vx, 2.0)
        elif ball.vx < -0.1:
            ball.vx = min(ball.vx, -2.0)
        else:
            buckets = self.buckets_ref
            if not buckets:
                ball.vx = 0
                return True

            nearest = min(range(len(buckets)),
                          key=lambda i: abs(ball.x - buckets[i].x))

            left_open = None
            right_open = None
            for i in range(nearest, -1, -1):
                if i in self.barrier_open_indices:
                    left_open = i
                    break
            for i in range(nearest, len(buckets)):
                if i in self.barrier_open_indices:
                    right_open = i
                    break

            target_x = None
            if left_open is not None and right_open is not None:
                d_left = abs(ball.x - buckets[left_open].x)
                d_right = abs(ball.x - buckets[right_open].x)
                target_x = buckets[left_open].x if d_left < d_right else buckets[right_open].x
            elif left_open is not None:
                target_x = buckets[left_open].x
            elif right_open is not None:
                target_x = buckets[right_open].x

            if target_x is not None:
                ball.vx = 2.0 if target_x > ball.x else -2.0
            else:
                ball.vx = 0

        max_roll = 4.0
        if abs(ball.vx) > max_roll:
            ball.vx = max_roll * (1 if ball.vx > 0 else -1)

        if ball.x - ball.radius < 0:
            ball.x = ball.radius
            ball.vx = abs(ball.vx)
        if ball.x + ball.radius > Window.width:
            ball.x = Window.width - ball.radius
            ball.vx = -abs(ball.vx)

        return True

    def _update_falling_physics(self):
        for ball in self.falling_balls[:]:
            if ball.is_in_bucket:
                continue

            ball._fall_time += 1
            if ball._fall_time > 500:
                print(f"⚠️ Шар {ball.player_name} завис")
                self._on_ball_reached_bottom(ball)
                continue

            if ball.is_rolling_on_barrier:
                ball.x += ball.vx
                ball.update_frame()

                if self._is_ball_over_open_bucket(ball.x):
                    ball.is_rolling_on_barrier = False
                    ball.vy = -1.0
                else:
                    barrier_center_y = self.barrier_pos[1] + self.barrier_height / 2
                    ball.y = barrier_center_y + ball.radius

                    if ball.x - ball.radius < 0:
                        ball.x = ball.radius
                        ball.vx = abs(ball.vx)
                    if ball.x + ball.radius > Window.width:
                        ball.x = Window.width - ball.radius
                        ball.vx = -abs(ball.vx)

                    self.update_canvas()
                    continue

            ball.vy -= 1.2
            ball.x += ball.vx
            ball.y += ball.vy
            ball.update_frame()

            for circle in self.collision_circles:
                if circle.is_active and circle.check_collision(ball):
                    direction = circle.get_bounce_direction(ball)
                    ball.vx = direction.x * random.uniform(3, 7)
                    ball.vy = direction.y * random.uniform(3, 7)
                    circle.hit()
                    ball.x += random.uniform(-3, 3)
                    ball.y += random.uniform(-3, 3)
                    break

            self._apply_barrier_collision(ball)

            if ball.x - ball.radius < self.x:
                ball.x = self.x + ball.radius
                ball.vx = abs(ball.vx)
            if ball.x + ball.radius > self.x + self.width:
                ball.x = self.x + self.width - ball.radius
                ball.vx = -abs(ball.vx)

            if ball.y < self.y - ball.radius * 2:
                self._on_ball_reached_bottom(ball)

        self.update_canvas()

    def _on_ball_reached_bottom(self, ball):
        if ball in self.falling_balls:
            self.falling_balls.remove(ball)

        if ball in self.balls_in_hopper:
            self.balls_in_hopper.remove(ball)

        ball.is_falling = False
        ball.is_in_hopper = False
        ball.is_rolling_on_barrier = False

        bucket_id = self._get_bucket_by_position(ball.x)

        if bucket_id >= 0 and self.on_ball_in_bucket:
            ball.is_in_bucket = True
            self.on_ball_in_bucket(bucket_id, ball)
            self.balls_in_buckets_count += 1

            if self.balls_in_buckets_count >= self.total_balls and not self._all_balls_in_buckets_called:
                self._all_balls_in_buckets_called = True
                if self.on_all_balls_in_buckets:
                    self.on_all_balls_in_buckets()
        else:
            ball.is_in_bucket = True
            self.balls_in_buckets_count += 1
            if self.balls_in_buckets_count >= self.total_balls and not self._all_balls_in_buckets_called:
                self._all_balls_in_buckets_called = True
                if self.on_all_balls_in_buckets:
                    self.on_all_balls_in_buckets()

    def _get_bucket_by_position(self, x):
        if hasattr(self, 'buckets_ref') and self.buckets_ref:
            buckets = self.buckets_ref
            if not buckets:
                return -1

            nearest = min(range(len(buckets)), key=lambda i: abs(x - buckets[i].x))
            bucket = buckets[nearest]
            if abs(x - bucket.x) <= bucket.width * 0.9:
                return nearest
            else:
                for i, b in enumerate(buckets):
                    if len(b.balls) < b.max_capacity:
                        return i
                return nearest
        return -1

    def _physics_loop(self, dt):
        if not self.balls_in_hopper and not self.falling_balls:
            self.physics_running = False
            if self.physics_update_timer:
                self.physics_update_timer.cancel()
                self.physics_update_timer = None
            return

        self._update_physics(dt)

    def _start_physics(self):
        if self.physics_running:
            return

        self.physics_running = True
        if self.physics_update_timer:
            self.physics_update_timer.cancel()

        self._physics_loop(0.02)
        self.physics_update_timer = Clock.schedule_interval(self._physics_loop, 0.02)

    def get_ball_count(self):
        return len(self.balls_in_hopper)

    def clear_balls(self):
        self.balls.clear()
        self.balls_in_hopper.clear()
        self.falling_balls.clear()
        self.balls_in_buckets_list.clear()
        self.is_dropping = False
        self.hopper_bottom_visible = True
        self.physics_running = False
        self.total_balls = 0
        self.balls_in_buckets_count = 0
        self._all_balls_in_buckets_called = False

        if self.physics_update_timer:
            self.physics_update_timer.cancel()
            self.physics_update_timer = None

        self.active_waves.clear()
        if self._wave_timer:
            self._wave_timer.cancel()
            self._wave_timer = None

        self.update_canvas()

    # ==================== ОБРАБОТЧИКИ СВАЙПА ====================

    def _get_nearest_sprite(self, x, y):
        if not self.sprites:
            return None

        nearest = None
        min_dist = float('inf')

        for sprite in self.sprites:
            dist = math.hypot(sprite.x - x, sprite.y - y)
            if dist < min_dist:
                min_dist = dist
                nearest = sprite

        if nearest and min_dist < nearest.radius * 3:
            return nearest
        return None

    def _apply_swipe_to_sprite(self, sprite, offset):
        if sprite:
            sprite.set_swipe_frame(offset)

    def _reset_sprite_swipe(self, sprite):
        if sprite:
            sprite.reset_swipe_frame()

    def _schedule_sprite_reset(self, sprite):
        if sprite:
            sprite.schedule_swipe_reset(self.SWIPE_RESET_DELAY)

    def _animate_sprite_swipe(self, sprite):
        if not sprite:
            return

        if hasattr(sprite, '_swipe_animation_timer') and sprite._swipe_animation_timer:
            sprite._swipe_animation_timer.cancel()
            sprite._swipe_animation_timer = None

        frames = [0, 1, 0, -1, 0]
        current_step = 0

        def step():
            nonlocal current_step
            if current_step >= len(frames):
                sprite._swipe_animation_timer = None
                return

            offset = frames[current_step]
            if offset == 0:
                sprite.reset_swipe_frame()
            else:
                sprite.set_swipe_frame(offset)

            current_step += 1
            self.update_canvas()

            sprite._swipe_animation_timer = Clock.schedule_once(
                lambda dt: step(), 0.05
            )

        step()

    def _cancel_sprite_animation(self, sprite):
        if sprite and hasattr(sprite, '_swipe_animation_timer') and sprite._swipe_animation_timer:
            sprite._swipe_animation_timer.cancel()
            sprite._swipe_animation_timer = None

    def _on_swipe_touch_down(self, instance, touch):
        board_top = self._get_hopper_bottom_y()
        if touch.y > board_top or touch.y < self.y:
            return False

        if touch.x < self.x or touch.x > self.x + self.width:
            return False

        sprite = self._get_nearest_sprite(touch.x, touch.y)
        if sprite is None:
            return False

        self._swipe_active = True
        self._swipe_start_x = touch.x
        self._swipe_start_y = touch.y
        self._swipe_frame_offset = 0
        self._swipe_current_sprite = sprite
        self._swipe_affected_sprites = set()
        self._swipe_log_counter = 0

        if self._swipe_reset_timer:
            self._swipe_reset_timer.cancel()
            self._swipe_reset_timer = None

        self.update_canvas()
        return False

    def _on_swipe_touch_move(self, instance, touch):
        if not self._swipe_active:
            return False

        board_top = self._get_hopper_bottom_y()
        if touch.y > board_top or touch.y < self.y:
            return False

        current_sprite = self._get_nearest_sprite(touch.x, touch.y)

        if current_sprite != self._swipe_current_sprite:
            if self._swipe_current_sprite is not None:
                self._animate_sprite_swipe(self._swipe_current_sprite)
                if self._swipe_current_sprite in self._swipe_affected_sprites:
                    self._swipe_affected_sprites.remove(self._swipe_current_sprite)
                self._swipe_current_sprite = None

            self._swipe_current_sprite = current_sprite
            self._swipe_frame_offset = 0

            if current_sprite is not None:
                self._swipe_affected_sprites.add(current_sprite)
                if current_sprite._swipe_reset_timer:
                    current_sprite._swipe_reset_timer.cancel()
                    current_sprite._swipe_reset_timer = None
                self._cancel_sprite_animation(current_sprite)

                delta_x = touch.x - self._swipe_start_x
                frame_offset = int(delta_x / 30)
                max_offset = 3
                frame_offset = max(-max_offset, min(max_offset, frame_offset))
                self._swipe_frame_offset = frame_offset
                if frame_offset != 0:
                    self._apply_swipe_to_sprite(current_sprite, frame_offset)
            else:
                for sprite in list(self._swipe_affected_sprites):
                    self._reset_sprite_swipe(sprite)
                self._swipe_affected_sprites.clear()
                self._swipe_frame_offset = 0

            self.update_canvas()
            return False

        if self._swipe_current_sprite is not None:
            delta_x = touch.x - self._swipe_start_x

            frame_offset = int(delta_x / 30)
            max_offset = 3
            frame_offset = max(-max_offset, min(max_offset, frame_offset))

            if frame_offset != self._swipe_frame_offset:
                self._reset_sprite_swipe(self._swipe_current_sprite)

                self._swipe_frame_offset = frame_offset

                if frame_offset != 0:
                    self._apply_swipe_to_sprite(self._swipe_current_sprite, frame_offset)
                    if self._swipe_current_sprite not in self._swipe_affected_sprites:
                        self._swipe_affected_sprites.add(self._swipe_current_sprite)
                    if self._swipe_current_sprite._swipe_reset_timer:
                        self._swipe_current_sprite._swipe_reset_timer.cancel()
                        self._swipe_current_sprite._swipe_reset_timer = None
                    self._cancel_sprite_animation(self._swipe_current_sprite)
                else:
                    if self._swipe_current_sprite in self._swipe_affected_sprites:
                        self._swipe_affected_sprites.remove(self._swipe_current_sprite)
                    self._animate_sprite_swipe(self._swipe_current_sprite)

                self.update_canvas()

        return False

    def _on_swipe_touch_up(self, instance, touch):
        if not self._swipe_active:
            return False

        self._swipe_active = False

        for sprite in list(self._swipe_affected_sprites):
            self._animate_sprite_swipe(sprite)
        self._swipe_affected_sprites.clear()

        if self._swipe_current_sprite is not None:
            self._animate_sprite_swipe(self._swipe_current_sprite)
            self._swipe_current_sprite = None

        self._swipe_frame_offset = 0

        self.update_canvas()
        return False

    def reset_swipe_state(self):
        self._swipe_active = False
        self._swipe_frame_offset = 0
        self._swipe_animating = False
        self._swipe_current_sprite = None

        if self._swipe_reset_timer:
            self._swipe_reset_timer.cancel()
            self._swipe_reset_timer = None

        for sprite in list(self._swipe_affected_sprites):
            self._reset_sprite_swipe(sprite)
        self._swipe_affected_sprites.clear()

        self.active_waves.clear()
        if self._wave_timer:
            self._wave_timer.cancel()
            self._wave_timer = None

        self.update_canvas()