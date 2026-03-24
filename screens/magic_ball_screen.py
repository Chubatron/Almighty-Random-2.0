"""
Magic Ball Screen - экран с фоном и мячом из спрайт-листа с физикой
"""
import os
import math
from kivy.uix.image import Image
from kivy.uix.widget import Widget
from kivy.properties import StringProperty, NumericProperty, ListProperty, ObjectProperty
from kivy.clock import Clock
from kivy.animation import Animation
from kivy.vector import Vector
from kivy.graphics import Color, Rectangle, Ellipse
from kivy.graphics.texture import Texture
from PIL import Image as PILImage
import numpy as np
from screens.base_game_screen import BaseGameScreen


class SpriteSheetBall(Widget):
    """Виджет мяча с поддержкой спрайт-листа 8x8 и динамической тенью"""

    sprite_sheet_path = StringProperty('')
    ball_size = NumericProperty(100)
    rows = NumericProperty(8)
    cols = NumericProperty(8)
    frame_index = NumericProperty(0)
    velocity = ListProperty([0, 0])

    # Параметры тени
    show_shadow = NumericProperty(1)
    shadow_offset_x = NumericProperty(0)
    shadow_offset_y = NumericProperty(0)
    shadow_alpha = NumericProperty(0.5)
    shadow_extra_offset = NumericProperty(0)  # Дополнительное смещение для отдаления тени
    shadow_scale = NumericProperty(1.0)  # Масштаб тени

    _texture = ObjectProperty(None, allownone=True)
    _frame_width = NumericProperty(0)
    _frame_height = NumericProperty(0)
    _ball_bounds = ListProperty([0, 0, 0, 0])

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        # Загружаем спрайт-лист
        if self.sprite_sheet_path and os.path.exists(self.sprite_sheet_path):
            self._load_spritesheet(self.sprite_sheet_path)

        self.bind(
            frame_index=self._update_display,
            pos=self._update_display,
            size=self._update_display,
            velocity=self._update_display,
            show_shadow=self._update_display,
            shadow_offset_x=self._update_display,
            shadow_offset_y=self._update_display,
            shadow_alpha=self._update_display,
            shadow_extra_offset=self._update_display,
            shadow_scale=self._update_display
        )

    def _load_spritesheet(self, path):
        """Загружает спрайт-лист и обрезает фон вокруг мяча"""
        try:
            img = PILImage.open(path)
            self._frame_width = img.width // self.cols
            self._frame_height = img.height // self.rows
            self._ball_bounds = self._find_ball_bounds(img, 0, 0)

            print(f"✅ Спрайт-лист загружен: {self.rows}x{self.cols} кадров")
            print(f"   Размер кадра: {self._frame_width}x{self._frame_height}")
            print(f"   Границы мяча: {self._ball_bounds}")

            self._texture = Texture.create(size=img.size, colorfmt='rgba' if img.mode == 'RGBA' else 'rgb')
            if img.mode == 'RGBA':
                self._texture.blit_buffer(img.tobytes(), colorfmt='rgba', bufferfmt='ubyte')
            else:
                self._texture.blit_buffer(img.convert('RGB').tobytes(), colorfmt='rgb', bufferfmt='ubyte')

            self.size = (self.ball_size, self.ball_size)
            self._update_display()

        except Exception as e:
            print(f"❌ Ошибка загрузки спрайт-листа: {e}")

    def _find_ball_bounds(self, img, col, row):
        """Находит границы мяча в указанном кадре (обрезает фон)"""
        frame_x = col * self._frame_width
        frame_y = row * self._frame_height
        frame = img.crop((frame_x, frame_y, frame_x + self._frame_width, frame_y + self._frame_height))

        if frame.mode == 'RGBA':
            alpha = np.array(frame)[:, :, 3]
            non_transparent = alpha > 0
        else:
            gray = np.array(frame.convert('L'))
            non_transparent = gray > 50

        if not np.any(non_transparent):
            return [0, 0, self._frame_width, self._frame_height]

        rows = np.any(non_transparent, axis=1)
        cols = np.any(non_transparent, axis=0)
        y_min = np.argmax(rows)
        y_max = len(rows) - np.argmax(rows[::-1]) - 1
        x_min = np.argmax(cols)
        x_max = len(cols) - np.argmax(cols[::-1]) - 1

        margin = 2
        x_min = max(0, x_min - margin)
        y_min = max(0, y_min - margin)
        x_max = min(self._frame_width - 1, x_max + margin)
        y_max = min(self._frame_height - 1, y_max + margin)

        return [int(x_min), int(y_min), int(x_max - x_min + 1), int(y_max - y_min + 1)]

    def _update_display(self, *args):
        """Обновляет отображение текущего кадра с динамической тенью"""
        if not self._texture or self.width == 0:
            return

        total_frames = self.rows * self.cols
        if total_frames == 0:
            return

        frame_idx = self.frame_index % total_frames
        row = frame_idx // self.cols
        col = frame_idx % self.cols

        frame_left = col / self.cols
        frame_right = (col + 1) / self.cols
        frame_top = row / self.rows
        frame_bottom = (row + 1) / self.rows

        bx, by, bw, bh = self._ball_bounds
        ball_left = bx / self._frame_width
        ball_right = (bx + bw) / self._frame_width
        ball_top = by / self._frame_height
        ball_bottom = (by + bh) / self._frame_height

        tex_left = frame_left + ball_left * (frame_right - frame_left)
        tex_right = frame_left + ball_right * (frame_right - frame_left)
        tex_top = frame_top + ball_top * (frame_bottom - frame_top)
        tex_bottom = frame_top + ball_bottom * (frame_bottom - frame_top)

        tex_coords = (tex_left, 1 - tex_bottom, tex_right, 1 - tex_bottom,
                     tex_right, 1 - tex_top, tex_left, 1 - tex_top)

        self.canvas.clear()

        with self.canvas:
            # Тень (отдаляется от мяча при движении)
            if self.show_shadow:
                # Смещение тени = базовое + дополнительное (отдаление)
                shadow_x = self.x + self.shadow_offset_x
                shadow_y = self.y + self.shadow_offset_y + self.shadow_extra_offset

                # Масштаб тени (увеличивается при отдалении)
                shadow_size = (self.size[0] * self.shadow_scale,
                              self.size[1] * self.shadow_scale)
                shadow_x = self.x + (self.size[0] - shadow_size[0]) / 2 + self.shadow_offset_x
                shadow_y = self.y + (self.size[1] - shadow_size[1]) / 2 + self.shadow_offset_y + self.shadow_extra_offset

                Color(0, 0, 0, self.shadow_alpha)
                Rectangle(pos=(shadow_x, shadow_y), size=shadow_size,
                         texture=self._texture, tex_coords=tex_coords)

            # Мяч
            Color(1, 1, 1, 1)
            Rectangle(pos=self.pos, size=self.size, texture=self._texture, tex_coords=tex_coords)

    def get_ball_center(self):
        return (self.center_x, self.center_y)

    def get_ball_radius(self):
        return self.ball_size / 2

    def is_point_on_ball(self, x, y):
        center_x, center_y = self.get_ball_center()
        radius = self.get_ball_radius()
        return (x - center_x) ** 2 + (y - center_y) ** 2 <= radius ** 2


class BallPhysics:
    """Класс для физики мяча"""

    def __init__(self, pos, size, screen_width, screen_height, sound_callback=None):
        self.pos = Vector(pos)
        self.velocity = Vector(0, 0)
        self.radius = size / 2
        self.screen_width = screen_width
        self.screen_height = screen_height
        self.sound_callback = sound_callback
        self.friction = 0.995
        self.bounce_factor = 0.85
        self.min_speed = 1

    def update(self, dt):
        """Обновляет позицию мяча"""
        self.velocity *= self.friction

        if self.velocity.length() < self.min_speed:
            self.velocity = Vector(0, 0)
            return False

        new_pos = self.pos + self.velocity * dt * 60
        bounced = self._check_boundaries(new_pos)
        self.pos = new_pos
        return bounced

    def _check_boundaries(self, pos):
        """Проверяет отскоки от краёв экрана"""
        bounced = False

        if pos.x - self.radius < 0:
            self.velocity.x = abs(self.velocity.x) * self.bounce_factor
            pos.x = self.radius
            bounced = True
        if pos.x + self.radius > self.screen_width:
            self.velocity.x = -abs(self.velocity.x) * self.bounce_factor
            pos.x = self.screen_width - self.radius
            bounced = True
        if pos.y - self.radius < 0:
            self.velocity.y = abs(self.velocity.y) * self.bounce_factor
            pos.y = self.radius
            bounced = True
        if pos.y + self.radius > self.screen_height:
            self.velocity.y = -abs(self.velocity.y) * self.bounce_factor
            pos.y = self.screen_height - self.radius
            bounced = True

        if bounced and self.sound_callback:
            self.sound_callback()

        return bounced

    def apply_force(self, force):
        self.velocity += force

    def is_stopped(self):
        return self.velocity.length() < self.min_speed


class MagicBallScreen(BaseGameScreen):
    """Экран с фоном и мячом из спрайт-листа с физикой"""

    background_path = StringProperty('assets/backgrounds/football_bg.jpg')
    sprite_sheet_path = StringProperty('assets/sprites/sprites_football_ball.png')
    bounce_sound_path = StringProperty('assets/sounds/bounce.wav')

    def __init__(self, **kwargs):
        if 'background_path' not in kwargs:
            kwargs['background_path'] = self.background_path

        super().__init__(**kwargs)

        self.ball = None
        self.physics = None
        self.ball_size = 75
        self.touch_start = None
        self.is_moving = False
        self.animation_counter = 0
        self.bounce_sound = None
        self.last_velocity = Vector(0, 0)
        self.is_stopping = False

        # Параметры отдаления тени (УВЕЛИЧЕНЫ ДЛЯ БОЛЬШЕГО ЭФФЕКТА)
        self.shadow_distance = 0  # Текущее расстояние отдаления тени
        self.shadow_timer = 0  # Таймер для волнового эффекта
        self.base_shadow_offset_x = self.ball_size * 0.12  # Базовое смещение по X
        self.base_shadow_offset_y = self.ball_size * 0.12  # Базовое смещение по Y
        self.max_shadow_distance = self.ball_size * 1.5  # УВЕЛИЧЕНО: максимальное отдаление тени (150% от размера)
        self.max_shadow_scale = 1.2  # УВЕЛИЧЕНО: максимальный масштаб тени (180% от размера)

        self._load_bounce_sound()

    def _load_bounce_sound(self):
        from kivy.core.audio import SoundLoader
        if os.path.exists(self.bounce_sound_path):
            self.bounce_sound = SoundLoader.load(self.bounce_sound_path)
            if self.bounce_sound:
                self.bounce_sound.volume = 0.6

    def _play_bounce_sound(self):
        if self.bounce_sound:
            try:
                self.bounce_sound.play()
            except:
                pass

    def _update_shadow_distance(self, speed):
        """Обновляет расстояние отдаления тени в зависимости от скорости мяча (УВЕЛИЧЕННЫЙ ЭФФЕКТ)"""
        # Максимальная скорость для максимального отдаления
        max_speed = 60  # УМЕНЬШЕНО: эффект начинает проявляться при меньшей скорости
        # Коэффициент отдаления от 0 до 1
        distance_coef = min(1.0, speed / max_speed)

        if speed > 5:  # УМЕНЬШЕНО: эффект проявляется при меньшей скорости
            # Мяч движется - создаем эффект отдаления тени
            # Обновляем таймер для волнового эффекта (123454321)
            self.shadow_timer += 0.05  # УВЕЛИЧЕНО: более быстрая пульсация

            # Создаем волну: 0 -> 1 -> 2 -> 3 -> 4 -> 3 -> 2 -> 1 -> 0
            t = self.shadow_timer * 1.0  # УВЕЛИЧЕНО: более частые колебания
            wave = math.sin(t)
            # Нормализуем от 0 до 1
            wave_norm = abs(wave)

            # Усиливаем эффект - используем квадрат для более резкого подъема
            wave_norm = wave_norm ** 0.7  # Делает подъем более плавным в начале

            # Умножаем на коэффициент скорости
            wave_norm = wave_norm * distance_coef

            # Вычисляем расстояние отдаления тени (УВЕЛИЧЕНО)
            self.shadow_distance = self.max_shadow_distance * wave_norm

            # Масштаб тени (увеличивается при отдалении)
            shadow_scale = 1.0 + (self.max_shadow_scale - 1.0) * wave_norm

            # Обновляем параметры тени
            # Тень отдаляется: увеличиваем смещение по Y (вниз) и по X
            self.ball.shadow_offset_x = self.base_shadow_offset_x + self.shadow_distance * 0.5
            self.ball.shadow_offset_y = self.base_shadow_offset_y + self.shadow_distance
            self.ball.shadow_extra_offset = self.shadow_distance  # Дополнительное смещение для отдаления
            self.ball.shadow_scale = shadow_scale  # Масштаб тени

            # Отладка (выводим каждые 30 кадров)
            if int(self.shadow_timer * 10) % 30 == 0:
                print(f"💨 Скорость: {speed:.1f}, Отдаление: {self.shadow_distance:.1f}px, Масштаб: {shadow_scale:.2f}")
        else:
            # Мяч почти остановился - плавно возвращаем тень на место
            if self.shadow_distance > 0:
                self.shadow_distance = 0
                self.shadow_timer = 0
                # Анимация возврата тени
                anim = Animation(
                    shadow_offset_x=self.base_shadow_offset_x,
                    shadow_offset_y=self.base_shadow_offset_y,
                    shadow_extra_offset=0,
                    shadow_scale=1.0,
                    shadow_alpha=0.5,
                    duration=0.3,
                    t='out_quad'
                )
                anim.start(self.ball)
                print(f"🔄 Тень возвращается на место")

    def on_enter(self):
        super().on_enter()
        self._setup_ui()
        Clock.schedule_once(lambda dt: self._bring_back_button_to_front(), 0.1)
        Clock.schedule_interval(self._update_physics, 1 / 60.0)

    def on_leave(self):
        super().on_leave()
        Clock.unschedule(self._update_physics)

    def _setup_ui(self):
        if os.path.exists(self.background_path):
            bg = Image(source=self.background_path, allow_stretch=True,
                      keep_ratio=False, size_hint=(1, 1))
            self.layout.add_widget(bg, index=0)
            print("✅ Фон добавлен")

        self._create_ball()

    def _create_ball(self):
        center_x = self.layout.width / 2
        center_y = self.layout.height / 2

        self.ball = SpriteSheetBall(
            sprite_sheet_path=self.sprite_sheet_path,
            ball_size=self.ball_size,
            rows=8,
            cols=8,
            frame_index=0,
            size_hint=(None, None),
            size=(self.ball_size, self.ball_size),
            pos=(center_x - self.ball_size / 2, center_y - self.ball_size / 2),
            show_shadow=1,
            shadow_offset_x=self.base_shadow_offset_x,
            shadow_offset_y=self.base_shadow_offset_y,
            shadow_extra_offset=0,
            shadow_scale=1.0,
            shadow_alpha=0.5
        )

        self.layout.add_widget(self.ball)

        self.physics = BallPhysics(
            pos=(center_x, center_y),
            size=self.ball_size,
            screen_width=self.layout.width,
            screen_height=self.layout.height,
            sound_callback=self._play_bounce_sound
        )

        print(f"✅ Мяч создан в центре экрана, размер={self.ball_size}px")
        print(f"   Максимальное отдаление тени: {self.max_shadow_distance:.1f}px")
        print(f"   Максимальный масштаб тени: {self.max_shadow_scale:.1f}x")

    def _rollback_ball(self, dt):
        if not self.ball or not self.physics:
            return

        if self.last_velocity.length() > 0:
            direction = self.last_velocity.normalize()
            rollback_distance = 3
            rollback_x = direction.x * rollback_distance
            rollback_y = direction.y * rollback_distance

            new_x = self.ball.x + rollback_x
            new_y = self.ball.y + rollback_y

            anim = Animation(x=new_x, y=new_y, duration=0.1, t='out_quad')
            anim.start(self.ball)

        total_frames = self.ball.rows * self.ball.cols
        current_frame = self.ball.frame_index

        if self.last_velocity.x < 0:
            new_frame = (current_frame + 2) % total_frames
        else:
            new_frame = (current_frame - 2) % total_frames

        def update_frame(dt):
            self.ball.frame_index = new_frame

        Clock.schedule_once(update_frame, 0.05)

        # Возвращаем тень в исходное положение
        anim_shadow = Animation(
            shadow_offset_x=self.base_shadow_offset_x,
            shadow_offset_y=self.base_shadow_offset_y,
            shadow_extra_offset=0,
            shadow_scale=1.0,
            shadow_alpha=0.5,
            duration=0.2,
            t='out_quad'
        )
        anim_shadow.start(self.ball)

        self.is_stopping = False

    def _update_physics(self, dt):
        if not self.ball or not self.physics:
            return

        if self.is_stopping:
            return

        self.last_velocity = Vector(self.physics.velocity)
        was_moving = not self.physics.is_stopped()
        bounced = self.physics.update(dt)

        self.ball.pos = (self.physics.pos.x - self.ball_size / 2,
                         self.physics.pos.y - self.ball_size / 2)

        speed = self.physics.velocity.length()

        # Обновляем отдаление тени в зависимости от скорости
        self._update_shadow_distance(speed)

        is_stopped = self.physics.is_stopped()

        if not is_stopped:
            self.is_moving = True
            anim_speed = max(5, min(40, speed * 1.2))
            self.animation_counter += anim_speed * dt
            total_frames = self.ball.rows * self.ball.cols
            frame = int(self.animation_counter) % total_frames

            if self.physics.velocity.x < 0:
                self.ball.frame_index = total_frames - frame - 1
            else:
                self.ball.frame_index = frame
        else:
            if was_moving or self.is_moving:
                self.is_moving = False
                self.is_stopping = True
                Clock.schedule_once(self._rollback_ball, 0.2)

    def _bring_back_button_to_front(self):
        if hasattr(self, 'back_button') and self.back_button:
            if self.back_button in self.layout.children:
                self.layout.remove_widget(self.back_button)
            self.layout.add_widget(self.back_button)

    def on_touch_down(self, touch):
        if self.ball and self.ball.is_point_on_ball(touch.x, touch.y):
            self.touch_start = touch.pos
            touch.grab(self)
            return True
        return super().on_touch_down(touch)

    def on_touch_move(self, touch):
        if touch.grab_current is self:
            return True
        return super().on_touch_move(touch)

    def on_touch_up(self, touch):
        if touch.grab_current is self and self.touch_start:
            start = Vector(self.touch_start)
            end = Vector(touch.pos)
            force = (end - start) * 0.3

            print(f"🚀 Бросок мяча: сила=({force.x:.1f}, {force.y:.1f})")

            self.physics.apply_force(force)

            self.animation_counter = 0
            self.is_moving = True
            self.is_stopping = False
            self.shadow_timer = 0

            self.touch_start = None
            touch.ungrab(self)
            return True
        return super().on_touch_up(touch)

    def go_to_menu(self, instance=None):
        print("🏠 Возврат в меню из MagicBallScreen")
        super().go_to_menu()