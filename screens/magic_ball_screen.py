"""
Magic Ball Screen - экран с фоном и мячом из спрайт-листа с физикой
"""
import os
import math
import json
import random
from kivy.app import App
from kivy.uix.image import Image
from kivy.uix.widget import Widget
from kivy.uix.label import Label
from kivy.properties import StringProperty, NumericProperty, ListProperty, ObjectProperty
from kivy.clock import Clock
from kivy.animation import Animation
from kivy.vector import Vector
from kivy.graphics import Color, Rectangle, Ellipse, Translate, PushMatrix, PopMatrix
from kivy.graphics.texture import Texture
from kivy.core.text import Label as CoreLabel
from kivy.core.audio import SoundLoader
from PIL import Image as PILImage
import numpy as np
from screens.base_game_screen import BaseGameScreen

from components.token_widget import TokenWidget
from lucky_token import LuckyToken


class LensEffect(Widget):
    """Эффект линзы (искажение фона)"""

    def __init__(self, size_ratio, speed=1.0, amplitude=10, **kwargs):
        super().__init__(**kwargs)
        self.size_ratio = size_ratio
        self.speed = speed
        self.amplitude = amplitude
        self.angle = random.uniform(0, 360)

        self.lens_size = 0
        self.lens_x = 0
        self.lens_y = 0

        self.bind(pos=self._update_lens, size=self._update_lens)

    def update_position(self, ball_center_x, ball_center_y, ball_size, dt):
        self.angle += self.speed * dt * 50
        if self.angle > 360:
            self.angle -= 360

        radius = ball_size * (0.5 + self.size_ratio)

        offset_x = math.cos(math.radians(self.angle)) * radius * 0.8
        offset_y = math.sin(math.radians(self.angle * 1.3)) * radius * 0.6

        self.lens_x = ball_center_x + offset_x
        self.lens_y = ball_center_y + offset_y
        self.lens_size = ball_size * self.size_ratio

        self._update_lens()

    def _update_lens(self, *args):
        if self.lens_size > 0:
            self.size = (self.lens_size, self.lens_size)
            self.pos = (self.lens_x - self.lens_size / 2,
                       self.lens_y - self.lens_size / 2)


class LensCanvas(Widget):
    """Виджет для отрисовки линз с эффектом искажения"""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.lenses = []
        self.ball_pos = (0, 0)
        self.ball_size = 0

    def add_lens(self, lens):
        self.lenses.append(lens)
        self.add_widget(lens)

    def clear_lenses(self):
        for lens in self.lenses:
            if lens.parent:
                self.remove_widget(lens)
        self.lenses.clear()

    def update_lenses(self, ball_center_x, ball_center_y, ball_size, dt):
        self.ball_pos = (ball_center_x, ball_center_y)
        self.ball_size = ball_size

        for lens in self.lenses:
            lens.update_position(ball_center_x, ball_center_y, ball_size, dt)

    def draw_lenses(self, bg_texture=None):
        self.canvas.clear()

        if not bg_texture:
            return

        with self.canvas:
            for lens in self.lenses:
                if lens.lens_size > 0:
                    PushMatrix()
                    Translate(lens.lens_x, lens.lens_y)
                    Translate(-lens.lens_x, -lens.lens_y)

                    src_x = lens.lens_x - lens.lens_size / 2
                    src_y = lens.lens_y - lens.lens_size / 2

                    Color(1, 1, 1, 1)
                    Rectangle(
                        texture=bg_texture,
                        pos=(src_x, src_y),
                        size=(lens.lens_size, lens.lens_size),
                        tex_coords=(0, 0, 1, 0, 1, 1, 0, 1)
                    )
                    PopMatrix()


class SpriteSheetBall(Widget):
    """Виджет мяча с поддержкой спрайт-листа 8x8 и динамической тенью"""

    sprite_sheet_path = StringProperty('')
    ball_size = NumericProperty(100)
    rows = NumericProperty(8)
    cols = NumericProperty(8)
    frame_index = NumericProperty(0)
    velocity = ListProperty([0, 0])

    show_shadow = NumericProperty(1)
    shadow_offset_x = NumericProperty(0)
    shadow_offset_y = NumericProperty(0)
    shadow_alpha = NumericProperty(0.5)
    shadow_extra_offset = NumericProperty(0)
    shadow_scale = NumericProperty(1.0)

    _texture = ObjectProperty(None, allownone=True)
    _frame_width = NumericProperty(0)
    _frame_height = NumericProperty(0)
    _ball_bounds = ListProperty([0, 0, 0, 0])

    def __init__(self, **kwargs):
        self.initial_ball_size = kwargs.pop('ball_size', None)
        self.base_shadow_offset_x = kwargs.pop('base_shadow_offset_x', 0)
        self.base_shadow_offset_y = kwargs.pop('base_shadow_offset_y', 0)
        super().__init__(**kwargs)

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

        self._current_shadow_anim = None

        self.shadow_offset_x = self.base_shadow_offset_x
        self.shadow_offset_y = self.base_shadow_offset_y

    def _load_spritesheet(self, path):
        try:
            img = PILImage.open(path)
            self._frame_width = img.width // self.cols
            self._frame_height = img.height // self.rows
            self._ball_bounds = self._find_ball_bounds(img, 0, 0)

            self._texture = Texture.create(size=img.size, colorfmt='rgba' if img.mode == 'RGBA' else 'rgb')
            if img.mode == 'RGBA':
                self._texture.blit_buffer(img.tobytes(), colorfmt='rgba', bufferfmt='ubyte')
            else:
                self._texture.blit_buffer(img.convert('RGB').tobytes(), colorfmt='rgb', bufferfmt='ubyte')

            from kivy.utils import platform
            from kivy.core.window import Window

            if platform == 'android':
                real_width = Window.system_size[0]
                self.ball_size = real_width * 0.16
            else:
                if self.initial_ball_size:
                    self.ball_size = self.initial_ball_size
                else:
                    app = App.get_running_app()
                    screen_params = getattr(app, 'screen_params', None)
                    if screen_params:
                        self.ball_size = screen_params.width * 0.16
                    else:
                        self.ball_size = 64

            self.size = (self.ball_size, self.ball_size)
            self._update_display()

        except Exception:
            pass

    def _find_ball_bounds(self, img, col, row):
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
            if self.show_shadow:
                shadow_size = (self.size[0] * self.shadow_scale,
                              self.size[1] * self.shadow_scale)
                shadow_x = self.x + (self.size[0] - shadow_size[0]) / 2 + self.shadow_offset_x
                shadow_y = self.y + (self.size[1] - shadow_size[1]) / 2 + self.shadow_offset_y + self.shadow_extra_offset

                Color(0, 0, 0, self.shadow_alpha)
                Rectangle(pos=(shadow_x, shadow_y), size=shadow_size,
                         texture=self._texture, tex_coords=tex_coords)

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

    def reset_shadow(self):
        if self._current_shadow_anim:
            self._current_shadow_anim.cancel(self)
            self._current_shadow_anim = None

        Animation.cancel_all(self)

        self.shadow_offset_x = self.base_shadow_offset_x
        self.shadow_offset_y = self.base_shadow_offset_y
        self.shadow_extra_offset = 0
        self.shadow_scale = 1.0
        self.shadow_alpha = 0.5

    def stop_all_animations(self):
        Animation.cancel_all(self)
        if self._current_shadow_anim:
            self._current_shadow_anim.cancel(self)
            self._current_shadow_anim = None


class BallPhysics:
    def __init__(self, pos, size, screen_width, screen_height, sound_callback=None, vibration_callback=None):
        self.pos = Vector(pos)
        self.velocity = Vector(0, 0)
        self.radius = size / 2
        self.screen_width = screen_width
        self.screen_height = screen_height
        self.sound_callback = sound_callback
        self.vibration_callback = vibration_callback
        self.friction = 0.995
        self.bounce_factor = 0.85
        self.min_speed = 1
        self.active = True

    def update(self, dt):
        if not self.active:
            return False

        self.velocity *= self.friction

        if self.velocity.length() < self.min_speed:
            self.velocity = Vector(0, 0)
            return False

        new_pos = self.pos + self.velocity * dt * 60
        bounced = self._check_boundaries(new_pos)
        self.pos = new_pos
        return bounced

    def _check_boundaries(self, pos):
        bounced = False
        bounce_speed = 0

        if pos.x - self.radius < 0:
            bounce_speed = abs(self.velocity.x)
            self.velocity.x = abs(self.velocity.x) * self.bounce_factor
            pos.x = self.radius
            bounced = True
        if pos.x + self.radius > self.screen_width:
            bounce_speed = abs(self.velocity.x)
            self.velocity.x = -abs(self.velocity.x) * self.bounce_factor
            pos.x = self.screen_width - self.radius
            bounced = True
        if pos.y - self.radius < 0:
            bounce_speed = abs(self.velocity.y)
            self.velocity.y = abs(self.velocity.y) * self.bounce_factor
            pos.y = self.radius
            bounced = True
        if pos.y + self.radius > self.screen_height:
            bounce_speed = abs(self.velocity.y)
            self.velocity.y = -abs(self.velocity.y) * self.bounce_factor
            pos.y = self.screen_height - self.radius
            bounced = True

        if bounced and self.sound_callback:
            self.sound_callback(bounce_speed)

        if bounced and self.vibration_callback:
            if bounce_speed <= 5:
                vibration_duration = 0.02
            else:
                vibration_duration = min(0.03 + (bounce_speed / 60) * 0.05, 0.08)
            self.vibration_callback(vibration_duration)

        return bounced

    def apply_force(self, force):
        self.velocity += force

    def is_stopped(self):
        return self.velocity.length() < self.min_speed

    def deactivate(self):
        self.active = False
        self.velocity = Vector(0, 0)

    def reset(self, pos):
        self.pos = Vector(pos)
        self.velocity = Vector(0, 0)
        self.active = True


class AnswerManager:
    def __init__(self, locales_path='locales'):
        self.locales_path = locales_path
        self.answers = {}
        self.answer_keys = [
            "yes", "no", "maybe", "think_twice",
            "doubt_dont_do", "try_other_side", "definitely_yes", "definitely_no"
        ]
        self._load_answers()

    def _load_answers(self):
        en_file = os.path.join(self.locales_path, 'en.json')

        if os.path.exists(en_file):
            try:
                with open(en_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)

                for key in self.answer_keys:
                    if key in data:
                        self.answers[key] = data[key]

            except Exception:
                self._create_default_answers()
        else:
            self._create_default_answers()

        missing_keys = []
        for key in self.answer_keys:
            if key not in self.answers or not self.answers[key]:
                missing_keys.append(key)

        if missing_keys:
            self._fill_missing_answers(missing_keys)

    def _create_default_answers(self):
        default_answers = {
            "yes": "YES",
            "no": "NO",
            "maybe": "MAYBE",
            "think_twice": "THINK TWICE",
            "doubt_dont_do": "IF IN DOUBT, DON'T",
            "try_other_side": "TRY THE OTHER SIDE",
            "definitely_yes": "DEFINITELY YES",
            "definitely_no": "DEFINITELY NO"
        }

        for key, value in default_answers.items():
            self.answers[key] = value

    def _fill_missing_answers(self, missing_keys):
        default_answers = {
            "yes": "YES",
            "no": "NO",
            "maybe": "MAYBE",
            "think_twice": "THINK TWICE",
            "doubt_dont_do": "IF IN DOUBT, DON'T",
            "try_other_side": "TRY THE OTHER SIDE",
            "definitely_yes": "DEFINITELY YES",
            "definitely_no": "DEFINITELY NO"
        }

        for key in missing_keys:
            if key in default_answers:
                self.answers[key] = default_answers[key]

    def get_random_answer(self):
        if not self.answer_keys:
            return "NO ANSWER AVAILABLE"

        random_key = random.choice(self.answer_keys)

        if random_key in self.answers:
            return self.answers[random_key]

        return f"ANSWER NOT FOUND: {random_key}"


class AnswerLabel(Label):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        app = App.get_running_app()
        screen_params = getattr(app, 'screen_params', None)

        if screen_params:
            self.font_size = screen_params.width * 0.1
        else:
            self.font_size = 48
        self.color = (0, 0, 0, 1)
        self.size_hint = (None, None)
        self.opacity = 0
        self.halign = 'center'
        self.valign = 'middle'
        self.text_size = (None, None)
        self.bold = True

    def show_answer(self, answer_text):
        self.text = answer_text

        label = CoreLabel(text=answer_text, font_size=self.font_size, font_name='Roboto-Bold')
        label.refresh()
        text_size = label.texture.size

        padding = self.font_size * 0.5
        self.width = text_size[0] + padding * 2
        self.height = text_size[1] + padding

        screen_width = self.parent.width if self.parent else 800
        screen_height = self.parent.height if self.parent else 600
        self.x = (screen_width - self.width) / 2
        self.y = (screen_height - self.height) / 2

        self.opacity = 0
        anim = Animation(opacity=1, duration=0.5, t='out_quad')
        anim.start(self)

    def hide_answer(self):
        if self.opacity > 0:
            anim = Animation(opacity=0, duration=0.3, t='in_quad')
            anim.start(self)


class MagicBallScreen(BaseGameScreen):

    background_path = StringProperty('assets/backgrounds/football_bg.jpg')
    sprite_sheet_path = StringProperty('assets/sprites/sprites_football_ball.png')
    bounce_sound_path = StringProperty('assets/sounds/football_bounce.wav')
    reject_sound_path = StringProperty('assets/sounds/reject.mp3')

    def __init__(self, **kwargs):
        self.screen_params = kwargs.pop('screen_params', None)
        super().__init__(**kwargs)

        if not self.screen_params:
            app = App.get_running_app()
            self.screen_params = getattr(app, 'screen_params', None)

        from kivy.utils import platform
        from kivy.core.window import Window

        if platform == 'android':
            real_width = Window.system_size[0]
            self.ball_size = real_width * 0.16
        else:
            if self.screen_params:
                self.ball_size = self.screen_params.width * 0.16
            else:
                self.ball_size = 64

        self.base_shadow_offset_x = self.ball_size * 0.12
        self.base_shadow_offset_y = self.ball_size * 0.12
        self.max_shadow_distance = self.ball_size * 1.5
        self.max_shadow_scale = 1.2

        self.ball = None
        self.physics = None
        self.touch_start = None
        self.is_moving = False
        self.animation_counter = 0
        self.bounce_sound = None
        self.reject_sound = None
        self.last_velocity = Vector(0, 0)
        self.is_stopping = False

        self.is_zoom_animation = False
        self.zoom_animation_counter = 0
        self.zoom_animation_scheduled = False
        self.is_falling_animation = False
        self.is_rolling_animation = False
        self.waiting_for_touch = False
        self.animation_paused = False

        self.input_enabled = True

        self.answer_manager = AnswerManager('locales')
        self.answer_label = None
        self.answer_displayed = False

        self.original_center = None
        self.original_pos = None

        self.shadow_distance = 0
        self.shadow_timer = 0
        self._current_shadow_anim = None

        self.lens_canvas = None
        self.lenses = []

        # --- Жетон ---
        self.tokens = LuckyToken()
        self.token_widget = None

        self._load_bounce_sound()
        self._load_reject_sound()

    def _load_bounce_sound(self):
        if os.path.exists(self.bounce_sound_path):
            self.bounce_sound = SoundLoader.load(self.bounce_sound_path)
            if self.bounce_sound:
                self.bounce_sound.volume = 0.7

    def _load_reject_sound(self):
        if os.path.exists(self.reject_sound_path):
            self.reject_sound = SoundLoader.load(self.reject_sound_path)
            if self.reject_sound:
                self.reject_sound.volume = 0.8

    def _play_reject_sound(self):
        """Звук отказа — играет, когда нет жетонов."""
        if self.sound_manager.is_muted():
            return
        if self.reject_sound:
            try:
                if self.reject_sound.state == 'play':
                    self.reject_sound.stop()
                self.reject_sound.play()
            except Exception:
                pass

    def _play_bounce_sound(self, speed=0):
        if self.sound_manager.is_muted():
            return

        if self.bounce_sound:
            try:
                max_speed = 60
                volume = min(1.0, speed / max_speed)
                volume = max(0.3, volume)

                self.bounce_sound.volume = volume
                self.bounce_sound.stop()
                self.bounce_sound.play()
            except Exception:
                pass

    def _play_bounce_vibration(self, duration=0.03):
        self.vibrate(duration)

    def _play_impact_sound(self):
        if self.sound_manager.is_muted():
            return

        if self.bounce_sound:
            try:
                self.bounce_sound.volume = 1.0
                self.bounce_sound.stop()
                self.bounce_sound.play()
            except Exception:
                pass

    def _stop_all_animations(self):
        if self.ball:
            self.ball.stop_all_animations()
            self.ball.reset_shadow()

        if self._current_shadow_anim:
            self._current_shadow_anim.cancel(self.ball)
            self._current_shadow_anim = None

        Clock.unschedule(self._update_zoom_animation)
        Clock.unschedule(self._animate_ball_fall)
        Clock.unschedule(self._show_random_answer)
        Clock.unschedule(self._update_physics)
        Clock.unschedule(self._update_lenses)

    def _get_random_ball_position(self):
        screen_width = self.layout.width
        screen_height = self.layout.height

        min_x = self.ball_size * 0.5
        max_x = screen_width - self.ball_size * 1.5
        random_x = random.uniform(min_x, max_x)

        min_y = screen_height * 0.25
        max_y = screen_height * 0.5
        random_y = random.uniform(min_y, max_y)

        return (random_x, random_y)

    def _clear_old_ball(self):
        if self.ball:
            self._stop_all_animations()
            if self.ball.parent:
                self.layout.remove_widget(self.ball)
            self.ball = None

        if self.physics:
            self.physics = None

    def _reset_to_initial_state(self):
        self._stop_all_animations()

        self.is_zoom_animation = False
        self.is_falling_animation = False
        self.is_rolling_animation = False
        self.waiting_for_touch = False
        self.animation_paused = False
        self.is_stopping = False
        self.is_moving = False
        self.zoom_animation_scheduled = False
        self.input_enabled = True
        self.answer_displayed = False
        self.shadow_distance = 0
        self.shadow_timer = 0

        if self.answer_label and self.answer_label.parent:
            self.answer_label.hide_answer()
            self.answer_label = None

        self._clear_old_ball()

    def _update_shadow_distance(self, speed):
        max_speed = 60
        distance_coef = min(1.0, speed / max_speed)

        if speed > 5:
            self.shadow_timer += 0.05
            t = self.shadow_timer * 1.0
            wave = math.sin(t)
            wave_norm = abs(wave)
            wave_norm = wave_norm ** 0.7
            wave_norm = wave_norm * distance_coef

            self.shadow_distance = self.max_shadow_distance * wave_norm
            shadow_scale = 1.0 + (self.max_shadow_scale - 1.0) * wave_norm

            self.ball.shadow_offset_x = self.base_shadow_offset_x + self.shadow_distance * 0.5
            self.ball.shadow_offset_y = self.base_shadow_offset_y + self.shadow_distance
            self.ball.shadow_extra_offset = self.shadow_distance
            self.ball.shadow_scale = shadow_scale
        else:
            if self.shadow_distance > 0:
                self.shadow_distance = 0
                self.shadow_timer = 0
                if self._current_shadow_anim:
                    self._current_shadow_anim.cancel(self.ball)

                self._current_shadow_anim = Animation(
                    shadow_offset_x=self.base_shadow_offset_x,
                    shadow_offset_y=self.base_shadow_offset_y,
                    shadow_extra_offset=0,
                    shadow_scale=1.0,
                    shadow_alpha=0.5,
                    duration=0.3,
                    t='out_quad'
                )
                self._current_shadow_anim.start(self.ball)

    # ==================== ПЕРЕСТАНОВКА ВИДЖЕТОВ ====================

    def _bring_ball_to_front(self):
        if self.ball and self.ball.parent:
            self.layout.remove_widget(self.ball)
            self.layout.add_widget(self.ball)

    def _send_ball_to_back(self):
        if self.ball and self.ball.parent:
            self.layout.remove_widget(self.ball)
            self.layout.add_widget(self.ball, index=1)

    def _bring_token_to_front(self):
        if self.token_widget and self.token_widget.parent:
            self.layout.remove_widget(self.token_widget)
            self.layout.add_widget(self.token_widget)

    # =========================================================

    def _animate_ball_fall(self):
        self.input_enabled = False
        self.is_falling_animation = True

        target_y = -self.ball.height

        total_frames = 12
        self.fall_frame_counter = 0

        def update_fall_frame(dt):
            if not self.is_falling_animation:
                return
            if self.fall_frame_counter < total_frames:
                self.ball.frame_index = self.fall_frame_counter
                self.fall_frame_counter += 1
                Clock.schedule_once(update_fall_frame, 1.0/20.0)

        update_fall_frame(0)

        anim = Animation(y=target_y, duration=0.5, t='in_quad')
        anim.start(self.ball)

        Clock.schedule_once(lambda dt: self._after_fall(), 0.5)

    def _after_fall(self):
        self.ball.opacity = 0
        self.is_falling_animation = False
        self.waiting_for_touch = True
        self.input_enabled = True

        self._send_ball_to_back()
        self._bring_token_to_front()

    def _animate_ball_roll_in(self):
        self.input_enabled = False
        self.is_rolling_animation = True

        self._send_ball_to_back()

        if self.answer_label and self.answer_label.parent:
            self.answer_label.hide_answer()
            self.answer_displayed = False

        self.ball.ball_size = self.ball_size
        self.ball.size = (self.ball_size, self.ball_size)
        self.ball.opacity = 1
        self.ball.show_shadow = 1
        self.ball.reset_shadow()

        target_pos = self._get_random_ball_position()
        target_x = target_pos[0]
        target_y = target_pos[1]

        self.ball.pos = (target_x, -self.ball.height)

        total_frames = 12
        self.roll_frame_counter = 0

        def update_roll_frame(dt):
            if not self.is_rolling_animation:
                return
            if self.roll_frame_counter < total_frames:
                self.ball.frame_index = self.roll_frame_counter
                self.roll_frame_counter += 1
                Clock.schedule_once(update_roll_frame, 1.0/20.0)

        update_roll_frame(0)

        anim_x = Animation(x=target_x, duration=0.6, t='out_quad')
        anim_y = Animation(y=target_y, duration=0.6, t='out_quad')
        anim_x.start(self.ball)
        anim_y.start(self.ball)

        Clock.schedule_once(lambda dt: self._after_roll_in(target_pos), 0.6)

    def _after_roll_in(self, target_pos):
        self.is_rolling_animation = False
        self.waiting_for_touch = False
        self.input_enabled = True

        if self.physics:
            center_x = target_pos[0] + self.ball_size / 2
            center_y = target_pos[1] + self.ball_size / 2
            self.physics.reset((center_x, center_y))

        self.is_zoom_animation = False
        self.is_stopping = False
        self.is_moving = False
        self.zoom_animation_scheduled = False
        self.animation_paused = False

    def _show_random_answer(self):
        answer_text = self.answer_manager.get_random_answer()

        if not self.answer_label:
            self.answer_label = AnswerLabel()
            self.layout.add_widget(self.answer_label)

        self.answer_label.show_answer(answer_text)
        self.answer_displayed = True

        Clock.schedule_once(lambda dt: self._animate_ball_fall(), 0.1)

    def _start_zoom_animation(self):
        if self.is_zoom_animation:
            return

        if not self.ball:
            return

        self.input_enabled = False

        if self.physics:
            self.physics.deactivate()

        self._bring_ball_to_front()

        self.zoom_animation_scheduled = False
        self.is_zoom_animation = True
        self.zoom_animation_counter = 0

        self.original_ball_size = self.ball_size
        self.original_pos = (self.ball.x, self.ball.y)
        self.ball.show_shadow = 0

        screen_width = self.layout.width
        screen_height = self.layout.height

        self.target_size = screen_width * 3

        screen_center_x = screen_width / 2
        screen_center_y = screen_height / 2

        self.target_x = screen_center_x - self.target_size / 2
        self.target_y = screen_center_y - self.target_size / 2

        self._update_zoom_animation(0)

    def _update_zoom_animation(self, dt):
        if not self.is_zoom_animation:
            return

        total_frames = 12

        if self.zoom_animation_counter < total_frames:
            self.ball.frame_index = self.zoom_animation_counter

            progress = self.zoom_animation_counter / total_frames
            ease_progress = 1 - (1 - progress) ** 2

            current_size = self.original_ball_size + (self.target_size - self.original_ball_size) * ease_progress
            current_x = self.original_pos[0] + (self.target_x - self.original_pos[0]) * ease_progress
            current_y = self.original_pos[1] + (self.target_y - self.original_pos[1]) * ease_progress

            self.ball.ball_size = current_size
            self.ball.size = (current_size, current_size)
            self.ball.pos = (current_x, current_y)

            self.zoom_animation_counter += 1

            frame_duration = 1.0 / 15.0
            Clock.schedule_once(self._update_zoom_animation, frame_duration)
        else:
            self.ball.ball_size = self.target_size
            self.ball.size = (self.target_size, self.target_size)
            self.ball.pos = (self.target_x, self.target_y)
            self.ball.frame_index = 10

            self._play_impact_sound()
            self.vibrate_long()

            self.is_zoom_animation = False
            self.animation_paused = True

            Clock.schedule_once(lambda dt: self._show_random_answer(), 0.1)

    def _update_lenses(self, dt):
        if self.ball and self.lens_canvas and self.is_moving:
            ball_center = self.ball.get_ball_center()
            self.lens_canvas.update_lenses(ball_center[0], ball_center[1], self.ball_size, dt)

    def _create_lenses(self):
        self.lens_canvas = LensCanvas()
        self.layout.add_widget(self.lens_canvas)

        lens_sizes = [0.5, 0.33, 0.2]
        lens_speeds = [0.8, 1.2, 1.5]

        for i, (size_ratio, speed) in enumerate(zip(lens_sizes, lens_speeds)):
            lens = LensEffect(
                size_ratio=size_ratio,
                speed=speed,
                amplitude=10 + i * 5
            )
            self.lens_canvas.add_lens(lens)
            self.lenses.append(lens)

        Clock.schedule_interval(self._update_lenses, 1 / 60.0)

    # ==================== ЖЕТОН ====================

    def _create_token_widget(self):
        if self.token_widget and self.token_widget.parent:
            return

        # size_hint и pos_hint берутся из TokenWidget.DEFAULT_*
        self.token_widget = TokenWidget()
        self.token_widget.set_value(self.tokens.get_balance())
        self.token_widget.set_state(self.tokens.get_balance() > 0)
        self.layout.add_widget(self.token_widget)

        self.tokens.bind(on_balance_changed=self._on_balance_changed)

    def _on_balance_changed(self, instance, new_balance):
        if self.token_widget:
            self.token_widget.set_value(int(new_balance))
            self.token_widget.set_state(int(new_balance) > 0)

    def _remove_token_widget(self):
        try:
            self.tokens.unbind(on_balance_changed=self._on_balance_changed)
        except Exception:
            pass

        if self.token_widget and self.token_widget.parent:
            self.layout.remove_widget(self.token_widget)
        self.token_widget = None

    def _flash_token_widget(self):
        """Трижды мигает цифрой: красный → жёлтый (3 цикла). Шрифт +15%."""
        if not self.token_widget:
            return
        label = self.token_widget.value_label
        if not label:
            return

        # ✅ Звук отказа — играет, когда виджет начинает мигать красным
        self._play_reject_sound()

        yellow = (1, 0.9, 0.2, 1)
        red = (1, 0, 0, 1)

        original_font_size = label.font_size
        label.font_size = original_font_size * 1.15

        schedule = [
            (0.00, red),
            (0.25, yellow),
            (0.50, red),
            (0.75, yellow),
            (1.00, red),
            (1.25, yellow),
        ]

        def make_apply(color, is_last=False):
            def _apply(dt):
                if not (self.token_widget and self.token_widget.value_label):
                    return
                self.token_widget.value_label.color = color
                if is_last:
                    self.token_widget._update_layout()
            return _apply

        for delay, color in schedule:
            is_last = (delay == schedule[-1][0])
            Clock.schedule_once(make_apply(color, is_last), delay)

    def _try_spend_token_and_zoom(self):
        """Проверяет баланс, списывает жетон и запускает зум, либо мигает счётчиком."""
        if self.tokens.get_balance() > 0:
            self.tokens.spend(1, reason="magic_ball")
            Clock.schedule_once(lambda dt: self._start_zoom_animation(), 0.5)
        else:
            self._flash_token_widget()

    # ====================================================

    def on_enter(self):
        super().on_enter()
        self._setup_ui()
        self._create_lenses()
        self._create_token_widget()
        Clock.schedule_interval(self._update_physics, 1 / 60.0)

    def on_leave(self):
        super().on_leave()

        self._stop_all_animations()
        Clock.unschedule(self._update_physics)
        Clock.unschedule(self._update_lenses)

        if self.answer_label and self.answer_label.parent:
            self.answer_label.hide_answer()
            self.answer_label = None

        if self.lens_canvas:
            self.lens_canvas.clear_lenses()
            if self.lens_canvas.parent:
                self.layout.remove_widget(self.lens_canvas)
            self.lens_canvas = None

        self._clear_old_ball()
        self._reset_to_initial_state()
        self._remove_token_widget()

    def _setup_ui(self):
        if os.path.exists(self.background_path):
            bg = Image(source=self.background_path, allow_stretch=True,
                      keep_ratio=False, size_hint=(1, 1))
            self.layout.add_widget(bg, index=0)

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
            base_shadow_offset_x=self.base_shadow_offset_x,
            base_shadow_offset_y=self.base_shadow_offset_y,
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
            sound_callback=self._play_bounce_sound,
            vibration_callback=self._play_bounce_vibration
        )

        self.original_pos = (center_x, center_y)

    def _rollback_ball(self, dt):
        if not self.ball or not self.physics:
            return

        if self._current_shadow_anim:
            self._current_shadow_anim.cancel(self.ball)

        self._current_shadow_anim = Animation(
            shadow_offset_x=self.base_shadow_offset_x,
            shadow_offset_y=self.base_shadow_offset_y,
            shadow_extra_offset=0,
            shadow_scale=1.0,
            shadow_alpha=0.5,
            duration=0.2,
            t='out_quad'
        )
        self._current_shadow_anim.start(self.ball)

        self.is_stopping = False

        self._try_spend_token_and_zoom()

    def _update_physics(self, dt):
        if not self.ball or not self.physics:
            return

        if self.is_zoom_animation or self.is_falling_animation or self.is_rolling_animation or self.animation_paused:
            return

        if self.is_stopping:
            return

        if not self.physics.active:
            return

        self.last_velocity = Vector(self.physics.velocity)
        was_moving = not self.physics.is_stopped()
        self.physics.update(dt)

        self.ball.pos = (self.physics.pos.x - self.ball_size / 2,
                         self.physics.pos.y - self.ball_size / 2)

        speed = self.physics.velocity.length()
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

    def on_touch_down(self, touch):
        if hasattr(self, 'back_button') and self.back_button:
            if self.back_button.collide_point(touch.x, touch.y):
                self.go_to_menu()
                return True

        if not self.input_enabled:
            return True

        if self.waiting_for_touch:
            self._animate_ball_roll_in()
            return True

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

            if self.physics:
                self.physics.active = True
                self.physics.velocity = Vector(0, 0)

            self.physics.apply_force(force)

            self.animation_counter = 0
            self.is_moving = True
            self.is_stopping = False
            self.shadow_timer = 0
            self.zoom_animation_scheduled = False
            self.is_zoom_animation = False
            self.animation_paused = False

            if self.answer_displayed and self.answer_label and self.answer_label.parent:
                self.answer_label.hide_answer()
                self.answer_displayed = False

            self.touch_start = None
            touch.ungrab(self)
            return True
        return super().on_touch_up(touch)

    def go_to_menu(self, instance=None):
        print("[DEBUG] go_to_menu called")

        self._stop_all_animations()
        Clock.unschedule(self._update_physics)
        Clock.unschedule(self._update_lenses)

        if self.ball and self.ball.parent:
            self.layout.remove_widget(self.ball)
            self.ball = None

        self.physics = None

        if self.lens_canvas:
            self.lens_canvas.clear_lenses()
            if self.lens_canvas.parent:
                self.layout.remove_widget(self.lens_canvas)
            self.lens_canvas = None

        self._remove_token_widget()

        self.play_back_sound()
        self.sound_manager.fade_to(1.0, duration=0.5)

        from main import switch_screen
        switch_screen('menu')