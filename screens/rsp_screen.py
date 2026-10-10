# screens/rsp_screen.py
from kivy.animation import Animation
from kivy.uix.label import Label
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.behaviors import ButtonBehavior
from kivy.uix.image import Image
from kivy.uix.widget import Widget
from kivy.properties import NumericProperty, StringProperty
from kivy.clock import Clock
from kivy.graphics import (
    Rotate, PushMatrix, PopMatrix, Color, Rectangle, Line
)
from kivy.graphics.texture import Texture
from kivy.core.audio import SoundLoader
from kivy.core.window import Window
from PIL import Image as PILImage
import random
import os
import math

from screens.base_game_screen import BaseGameScreen

from components.token_widget import TokenWidget
from lucky_token import LuckyToken


class RotatingImage(Image):
    """Изображение с вращением вокруг центра и обесцвечиванием.
    Если is_shadow=True — цвет никогда не перезаписывается."""
    angle = NumericProperty(0)
    desaturation = NumericProperty(0.0)

    def __init__(self, name="", is_shadow=False, **kwargs):
        super().__init__(mipmap=True, **kwargs)
        self.name = name
        self.is_shadow = is_shadow
        self.allow_stretch = True
        self.keep_ratio = True

        self._rotate = None
        self._setup_graphics()

        self.bind(center=self._update_origin, angle=self._update_angle)
        self.bind(texture=self._smooth_texture)
        self.bind(desaturation=self._update_display)

    def _smooth_texture(self, *args):
        tex = self.texture
        if tex:
            tex.mag_filter = 'linear'
            tex.min_filter = 'linear'

    def _setup_graphics(self):
        with self.canvas.before:
            PushMatrix()
            self._rotate = Rotate(angle=self.angle, origin=self.center)
        with self.canvas.after:
            PopMatrix()

    def _update_angle(self, instance, value):
        if self._rotate:
            self._rotate.angle = value

    def _update_origin(self, *args):
        if self._rotate:
            self._rotate.origin = (self.center_x, self.center_y)

    def _update_display(self, *args):
        if self.is_shadow:
            return

        if self.desaturation >= 1.0:
            self.color = (0.4, 0.4, 0.4, 1)
        elif self.desaturation <= 0.0:
            self.color = (1, 1, 1, 1)
        else:
            v = 1.0 - (1.0 - 0.4) * self.desaturation
            self.color = (v, v, v, 1)


class RotatingImageWithShadow(FloatLayout):
    """Контейнер с двумя независимо вращающимися изображениями: тень и спиннер."""
    angle = NumericProperty(0)
    desaturation = NumericProperty(0.0)

    def __init__(self, name="", source=None, shadow_source=None, **kwargs):
        super().__init__(**kwargs)
        self.name = name
        self.size_hint = (None, None)

        self.shadow_image = RotatingImage(
            name=f"{name}_shadow",
            source=shadow_source if shadow_source else source,
            allow_stretch=True,
            keep_ratio=True,
            opacity=0.35,
            color=(0, 0, 0, 1),
            is_shadow=True,
        )

        self.main_image = RotatingImage(
            name=f"{name}_main",
            source=source,
            allow_stretch=True,
            keep_ratio=True,
            opacity=1
        )

        self.add_widget(self.shadow_image)
        self.add_widget(self.main_image)

        self.shadow_offset_y = 0

        self.bind(
            pos=self._update_position,
            size=self._update_size,
            angle=self._update_angle,
            desaturation=self._update_desaturation,
        )

    def set_shadow_offset(self, offset_y):
        self.shadow_offset_y = offset_y
        self._update_position()

    def _update_angle(self, instance, value):
        self.shadow_image.angle = value
        self.main_image.angle = value

    def _update_desaturation(self, *args):
        self.main_image.desaturation = self.desaturation
        self.shadow_image.color = (0, 0, 0, 1)

    def _update_position(self, *args):
        self.main_image.center = (self.center_x, self.center_y)
        self.main_image.size = self.size
        self.shadow_image.center = (self.center_x, self.center_y - self.shadow_offset_y)
        self.shadow_image.size = self.size

    def _update_size(self, *args):
        self.main_image.size = self.size
        self.shadow_image.size = self.size
        self._update_position()


class SpinButton(ButtonBehavior, Image):
    """Кнопка SPIN с настраиваемой зоной нажатия."""

    is_active = NumericProperty(1)

    # ❗ Зона нажатия (не влияет на визуальный размер)
    hit_scale_x = NumericProperty(1.0)
    hit_scale_y = NumericProperty(1.0)
    hit_offset_x = NumericProperty(0.0)
    hit_offset_y = NumericProperty(0.0)

    def __init__(self, **kwargs):
        passed_size = kwargs.get('size', None)

        super().__init__(mipmap=True, **kwargs)

        self.green_button_path = 'assets/images/buttons/spin_button_green.png'
        self.red_button_path = 'assets/images/buttons/spin_button_red.png'

        self.size_hint = (None, None)

        if passed_size:
            self.size = passed_size
        else:
            self.size = (80, 80)

        self.allow_stretch = True
        self.update_button_image()
        self.bind(is_active=self.update_button_image)
        self.bind(texture=self._smooth_texture)

    def _smooth_texture(self, *args):
        tex = self.texture
        if tex:
            tex.mag_filter = 'linear'
            tex.min_filter = 'linear'

    def update_button_image(self, *args):
        if self.is_active:
            if os.path.exists(self.green_button_path):
                self.source = self.green_button_path
                self.color = (1, 1, 1, 1)
        else:
            if os.path.exists(self.red_button_path):
                self.source = self.red_button_path
                self.color = (1, 1, 1, 1)

    # ---------- зона нажатия ----------
    def _hit_rect(self):
        """Возвращает (x, y, w, h) — прямоугольник зоны нажатия."""
        w = self.width * self.hit_scale_x
        h = self.height * self.hit_scale_y
        cx = self.center_x + self.hit_offset_x
        cy = self.center_y + self.hit_offset_y
        return (cx - w / 2, cy - h / 2, w, h)

    def collide_point(self, x, y):
        hx, hy, hw, hh = self._hit_rect()
        return (hx <= x <= hx + hw) and (hy <= y <= hy + hh)


class TriangleButton(ButtonBehavior, Widget):
    """Кнопка-треугольник с зеркалированием, анимацией нажатия
    и звуком клика (тот же, что у кнопки back и SWITCH)."""

    source = StringProperty('')
    mirrored = NumericProperty(0)

    show_shadow = NumericProperty(0)
    shadow_offset_y = NumericProperty(0)
    shadow_alpha = NumericProperty(0.35)
    shadow_scale = NumericProperty(0.9)

    press_offset_y = NumericProperty(0)
    press_press_depth_coef = NumericProperty(0.5)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.size_hint = (None, None)
        self._texture = None
        self._press_anim = None

        # ❗ Звук клика (тот же Schpun.ogg, что у back и switch)
        self.click_sound = None
        self._load_click_sound()

        self.bind(
            source=self._load_texture,
            pos=self._update_display,
            size=self._update_display,
            opacity=self._update_display,
            show_shadow=self._update_display,
            shadow_offset_y=self._update_display,
            shadow_alpha=self._update_display,
            shadow_scale=self._update_display,
            press_offset_y=self._update_display,
        )

        self.bind(on_press=self._on_press_anim, on_release=self._on_release_anim)

        if self.source:
            self._load_texture()

    # ---------- звук ----------
    def _load_click_sound(self):
        sound_path = 'assets/sounds/Schpun.ogg'
        if os.path.exists(sound_path):
            self.click_sound = SoundLoader.load(sound_path)
            if self.click_sound:
                self.click_sound.volume = 0.6

    def _play_click_sound(self):
        if not self.click_sound:
            return
        try:
            from sound_manager import SoundManager
            if SoundManager().is_muted():
                return
        except Exception:
            pass

        try:
            if self.click_sound.state == 'play':
                self.click_sound.stop()
            self.click_sound.play()
        except Exception:
            pass

    # ---------- анимация нажатия ----------
    def _on_press_anim(self, *args):
        # ❗ Сначала звук клика
        self._play_click_sound()

        if self._press_anim:
            self._press_anim.cancel(self)
            self._press_anim = None
        depth = self.shadow_offset_y * self.press_press_depth_coef
        self._press_anim = Animation(press_offset_y=depth, duration=0.08, t='out_quad')
        self._press_anim.start(self)

    def _on_release_anim(self, *args):
        if self._press_anim:
            self._press_anim.cancel(self)
            self._press_anim = None
        self._press_anim = Animation(press_offset_y=0, duration=0.12, t='out_quad')
        self._press_anim.start(self)

    # ---------- текстура ----------
    def _load_texture(self, *args):
        if not self.source or not os.path.exists(self.source):
            print(f"=== TriangleButton: источник не найден: {self.source}")
            return

        try:
            img = PILImage.open(self.source).convert('RGBA')
            img = img.transpose(PILImage.FLIP_TOP_BOTTOM)

            if self.mirrored:
                img = img.transpose(PILImage.FLIP_LEFT_RIGHT)

            self._texture = Texture.create(size=img.size, colorfmt='rgba')
            self._texture.blit_buffer(img.tobytes(), colorfmt='rgba', bufferfmt='ubyte')
            self._texture.mag_filter = 'linear'
            self._texture.min_filter = 'linear'

            print(f"=== TriangleButton: текстура загружена {img.size}, mirrored={self.mirrored}")
            self._update_display()
        except Exception as e:
            print(f"=== TriangleButton: ошибка загрузки {e}")

    def _update_display(self, *args):
        if self._texture is None or self.width <= 0 or self.height <= 0:
            return

        self.canvas.clear()

        shadow_current_offset = max(0, self.shadow_offset_y - self.press_offset_y)
        btn_pos = (self.x, self.y - self.press_offset_y)

        with self.canvas:
            if self.show_shadow:
                sh_w = self.width * self.shadow_scale
                sh_h = self.height * self.shadow_scale
                sh_x = self.center_x - sh_w / 2
                sh_y = self.center_y - sh_h / 2 - shadow_current_offset

                Color(0, 0, 0, self.shadow_alpha * self.opacity)
                Rectangle(pos=(sh_x, sh_y), size=(sh_w, sh_h), texture=self._texture)

            Color(1, 1, 1, self.opacity)
            Rectangle(pos=btn_pos, size=self.size, texture=self._texture)


class SpriteFrame(Widget):
    """Один кадр из спрайт-листа с тенью, пульсацией, затемнением и слайдом."""

    source = StringProperty('')
    frames_count = NumericProperty(5)
    current_frame = NumericProperty(0)

    show_shadow = NumericProperty(0)
    shadow_offset_y = NumericProperty(0)
    shadow_alpha = NumericProperty(0.35)
    shadow_scale = NumericProperty(0.9)

    pulse_scale = NumericProperty(1.0)
    darken = NumericProperty(0.0)

    slide_offset_x = NumericProperty(0.0)
    slide_scale = NumericProperty(1.0)
    slide_opacity = NumericProperty(1.0)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.size_hint = (None, None)
        self._texture = None

        self.bind(
            source=self._load_texture,
            frames_count=self._update_display,
            current_frame=self._update_display,
            pos=self._update_display,
            size=self._update_display,
            opacity=self._update_display,
            show_shadow=self._update_display,
            shadow_offset_y=self._update_display,
            shadow_alpha=self._update_display,
            shadow_scale=self._update_display,
            pulse_scale=self._update_display,
            darken=self._update_display,
            slide_offset_x=self._update_display,
            slide_scale=self._update_display,
            slide_opacity=self._update_display,
        )

        if self.source:
            self._load_texture()

    def _load_texture(self, *args):
        if not self.source or not os.path.exists(self.source):
            print(f"=== SpriteFrame: источник не найден: {self.source}")
            return

        try:
            img = PILImage.open(self.source).convert('RGBA')
            img = img.transpose(PILImage.FLIP_TOP_BOTTOM)

            self._texture = Texture.create(size=img.size, colorfmt='rgba')
            self._texture.blit_buffer(img.tobytes(), colorfmt='rgba', bufferfmt='ubyte')
            self._texture.mag_filter = 'linear'
            self._texture.min_filter = 'linear'

            print(f"=== SpriteFrame: текстура загружена {img.size}")
            self._update_display()
        except Exception as e:
            print(f"=== SpriteFrame: ошибка загрузки {e}")

    def _update_display(self, *args):
        if self._texture is None or self.width <= 0 or self.height <= 0:
            return

        n = max(1, int(self.frames_count))
        idx = int(self.current_frame) % n

        uv_w = 1.0 / n
        uv_x0 = idx * uv_w
        uv_x1 = uv_x0 + uv_w

        tex_coords = (uv_x0, 0.0, uv_x1, 0.0, uv_x1, 1.0, uv_x0, 1.0)

        ps = max(0.01, self.pulse_scale) * max(0.01, self.slide_scale)
        draw_w = self.width * ps
        draw_h = self.height * ps

        draw_cx = self.center_x + self.slide_offset_x
        draw_cy = self.center_y

        draw_x = draw_cx - draw_w / 2
        draw_y = draw_cy - draw_h / 2

        d = max(0.0, min(1.0, self.darken))
        brightness = 1.0 - (1.0 - 0.35) * d

        final_op = max(0.0, min(1.0, self.opacity * self.slide_opacity))
        img_color = (brightness, brightness, brightness, final_op)

        self.canvas.clear()
        with self.canvas:
            if self.show_shadow:
                sh_w = draw_w * self.shadow_scale
                sh_h = draw_h * self.shadow_scale
                sh_x = draw_cx - sh_w / 2
                sh_y = draw_cy - sh_h / 2 - self.shadow_offset_y

                Color(0, 0, 0, self.shadow_alpha * final_op)
                Rectangle(pos=(sh_x, sh_y), size=(sh_w, sh_h),
                          texture=self._texture, tex_coords=tex_coords)

            Color(*img_color)
            Rectangle(pos=(draw_x, draw_y), size=(draw_w, draw_h),
                      texture=self._texture, tex_coords=tex_coords)


class RSPResultBar(FloatLayout):
    """Панель с центральной картинкой (двойной буфер) и двумя кнопками."""

    y_coef = NumericProperty(0.75)
    center_img_h_coef = NumericProperty(0.30)
    center_img_ratio = NumericProperty(1.0)
    frames_count = NumericProperty(5)
    side_button_h_coef = NumericProperty(0.09)
    side_button_ratio = NumericProperty(1.0)
    side_offset_x_coef = NumericProperty(0.30)

    game_type = StringProperty('classic')

    center_source = StringProperty('assets/images/5images.png')
    left_source = StringProperty('assets/images/buttons/triangle_button.png')
    right_source = StringProperty('assets/images/buttons/triangle_button.png')

    current_frame = NumericProperty(0)
    buttons_enabled = NumericProperty(1)

    shadow_offset_y_coef = NumericProperty(0.05)
    shadow_alpha = NumericProperty(0.4)
    shadow_scale = NumericProperty(0.9)

    press_depth_coef = NumericProperty(0.5)

    slide_duration = NumericProperty(0.22)
    slide_distance_coef = NumericProperty(1.2)
    slide_min_scale = NumericProperty(0.3)

    pulse_anim = None
    darken_anim = None
    slide_anim_out = None
    slide_anim_in = None
    _slide_in_progress = False

    CLASSIC_FRAMES = [0, 3, 4]
    EXTENDED_FRAMES = [0, 1, 2, 3, 4]

    _left_callback = None
    _right_callback = None

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.size_hint = (1, 1)

        initial_frame = self._active_frames()[0] if self._active_frames() else 0

        self.center_image_a = SpriteFrame(
            source=self.center_source,
            frames_count=self.frames_count,
            current_frame=initial_frame,
            show_shadow=1,
            shadow_offset_y=0,
            shadow_alpha=self.shadow_alpha,
            shadow_scale=self.shadow_scale,
        )
        self.center_image_b = SpriteFrame(
            source=self.center_source,
            frames_count=self.frames_count,
            current_frame=initial_frame,
            show_shadow=1,
            shadow_offset_y=0,
            shadow_alpha=self.shadow_alpha,
            shadow_scale=self.shadow_scale,
        )
        self.center_image_b.slide_opacity = 0.0

        self.center_image = self.center_image_a
        self._inactive_image = self.center_image_b

        self.left_button = TriangleButton(
            source=self.left_source,
            mirrored=0,
            show_shadow=1,
            shadow_offset_y=0,
            shadow_alpha=self.shadow_alpha,
            shadow_scale=self.shadow_scale,
            press_press_depth_coef=self.press_depth_coef,
        )
        self.right_button = TriangleButton(
            source=self.right_source,
            mirrored=1,
            show_shadow=1,
            shadow_offset_y=0,
            shadow_alpha=self.shadow_alpha,
            shadow_scale=self.shadow_scale,
            press_press_depth_coef=self.press_depth_coef,
        )

        self.add_widget(self.center_image_a)
        self.add_widget(self.center_image_b)
        self.add_widget(self.left_button)
        self.add_widget(self.right_button)

        self.bind(
            size=self.update_layout,
            pos=self.update_layout,
            y_coef=self.update_layout,
            center_img_h_coef=self.update_layout,
            center_img_ratio=self.update_layout,
            side_button_h_coef=self.update_layout,
            side_button_ratio=self.update_layout,
            side_offset_x_coef=self.update_layout,
            shadow_offset_y_coef=self.update_layout,
            shadow_alpha=self._on_shadow_params_changed,
            shadow_scale=self._on_shadow_params_changed,
            press_depth_coef=self._on_shadow_params_changed,
            center_source=self._update_center_source,
            left_source=self._update_left_source,
            right_source=self._update_right_source,
            game_type=self._on_game_type_changed,
            buttons_enabled=self._on_buttons_enabled_changed,
        )

        self.left_button.bind(on_press=self._on_left_click)
        self.right_button.bind(on_press=self._on_right_click)

        self.update_layout()

    def _on_shadow_params_changed(self, *args):
        for img in (self.center_image_a, self.center_image_b):
            img.shadow_alpha = self.shadow_alpha
            img.shadow_scale = self.shadow_scale
        if self.left_button:
            self.left_button.shadow_alpha = self.shadow_alpha
            self.left_button.shadow_scale = self.shadow_scale
            self.left_button.press_press_depth_coef = self.press_depth_coef
        if self.right_button:
            self.right_button.shadow_alpha = self.shadow_alpha
            self.right_button.shadow_scale = self.shadow_scale
            self.right_button.press_press_depth_coef = self.press_depth_coef

    def play_win_pulse(self, times=3, scale_up=1.10, duration=0.15):
        if self.pulse_anim:
            self.pulse_anim.cancel(self.center_image)
            self.pulse_anim = None

        self.center_image.pulse_scale = 1.0

        seq = Animation(pulse_scale=scale_up, duration=duration, t='out_quad') + \
              Animation(pulse_scale=1.0,     duration=duration, t='in_quad')

        for _ in range(times - 1):
            seq += Animation(pulse_scale=scale_up, duration=duration, t='out_quad')
            seq += Animation(pulse_scale=1.0,     duration=duration, t='in_quad')

        self.pulse_anim = seq
        self.pulse_anim.start(self.center_image)

    def play_lose_darken(self, target=0.6, duration=0.35):
        if self.darken_anim:
            self.darken_anim.cancel(self.center_image)
            self.darken_anim = None
        self.darken_anim = Animation(darken=target, duration=duration, t='out_quad')
        self.darken_anim.start(self.center_image)

    def clear_darken(self, duration=0.2):
        if self.darken_anim:
            self.darken_anim.cancel(self.center_image)
            self.darken_anim = None
        self.darken_anim = Animation(darken=0.0, duration=duration, t='out_quad')
        self.darken_anim.start(self.center_image)

    def _play_slide_transition(self, direction, new_frame):
        if self._slide_in_progress:
            return
        self._slide_in_progress = True

        old_img = self.center_image
        new_img = self._inactive_image

        dist = self.width * self.side_offset_x_coef * self.slide_distance_coef

        if self.slide_anim_out:
            self.slide_anim_out.cancel(old_img)
        if self.slide_anim_in:
            self.slide_anim_in.cancel(new_img)
        self.slide_anim_out = None
        self.slide_anim_in = None

        new_img.current_frame = new_frame
        new_img.slide_offset_x = -direction * dist
        new_img.slide_scale = self.slide_min_scale
        new_img.slide_opacity = 0.0
        new_img.pulse_scale = 1.0
        new_img.darken = 0.0
        new_img._update_display()

        old_img.slide_offset_x = 0.0
        old_img.slide_scale = 1.0
        old_img.slide_opacity = 1.0
        old_img.pulse_scale = 1.0
        old_img._update_display()

        out_anim = Animation(slide_offset_x=direction * dist,
                             slide_scale=self.slide_min_scale,
                             slide_opacity=0.0,
                             duration=self.slide_duration, t='in_quad')
        in_anim = Animation(slide_offset_x=0.0, slide_scale=1.0, slide_opacity=1.0,
                            duration=self.slide_duration, t='out_quad')

        self.slide_anim_out = out_anim
        self.slide_anim_in = in_anim

        finished = {'out': False, 'in': False}

        def on_out_done(*args):
            finished['out'] = True
            self._check_slide_finished(finished)

        def on_in_done(*args):
            finished['in'] = True
            self._check_slide_finished(finished)

        out_anim.bind(on_complete=lambda *a: Clock.schedule_once(on_out_done, 0))
        in_anim.bind(on_complete=lambda *a: Clock.schedule_once(on_in_done, 0))

        out_anim.start(old_img)
        in_anim.start(new_img)

    def _check_slide_finished(self, finished):
        if not (finished['out'] and finished['in']):
            return

        old_img = self.center_image
        new_img = self._inactive_image

        old_img.slide_offset_x = 0.0
        old_img.slide_scale = 1.0
        old_img.slide_opacity = 0.0
        old_img.pulse_scale = 1.0
        old_img.darken = 0.0
        old_img._update_display()

        new_img.slide_offset_x = 0.0
        new_img.slide_scale = 1.0
        new_img.slide_opacity = 1.0
        new_img.pulse_scale = 1.0
        new_img.darken = 0.0
        new_img._update_display()

        self.center_image = new_img
        self._inactive_image = old_img

        self.slide_anim_out = None
        self.slide_anim_in = None
        self._slide_in_progress = False

    def _active_frames(self):
        if self.game_type == 'classic':
            return list(self.CLASSIC_FRAMES)
        return list(self.EXTENDED_FRAMES)

    def _on_game_type_changed(self, *args):
        frames = self._active_frames()
        if frames:
            f = frames[0]
            self.current_frame = f
            self.center_image_a.current_frame = f
            self.center_image_b.current_frame = f

    def _current_active_index(self):
        frames = self._active_frames()
        if not frames:
            return 0
        try:
            return frames.index(self.current_frame)
        except ValueError:
            return 0

    def _set_active_frame(self, frame_index_in_sheet):
        self.current_frame = frame_index_in_sheet
        if self.center_image:
            self.center_image.current_frame = frame_index_in_sheet
        if self._inactive_image:
            self._inactive_image.current_frame = frame_index_in_sheet

    def _next_active_frame(self, direction):
        frames = self._active_frames()
        if not frames:
            return 0
        pos = self._current_active_index()
        pos = (pos + direction) % len(frames)
        return frames[pos]

    def _on_buttons_enabled_changed(self, *args):
        if self.buttons_enabled:
            Animation.cancel_all(self.left_button, 'opacity')
            Animation.cancel_all(self.right_button, 'opacity')
            Animation(opacity=1.0, duration=0.2).start(self.left_button)
            Animation(opacity=1.0, duration=0.2).start(self.right_button)
            self.left_button.disabled = False
            self.right_button.disabled = False
        else:
            Animation.cancel_all(self.left_button, 'opacity')
            Animation.cancel_all(self.right_button, 'opacity')
            Animation(opacity=0.35, duration=0.2).start(self.left_button)
            Animation(opacity=0.35, duration=0.2).start(self.right_button)
            self.left_button.disabled = True
            self.right_button.disabled = True

    def _update_center_source(self, *args):
        if self.center_image_a:
            self.center_image_a.source = self.center_source
        if self.center_image_b:
            self.center_image_b.source = self.center_source

    def _update_left_source(self, *args):
        self.left_button.source = self.left_source

    def _update_right_source(self, *args):
        self.right_button.source = self.right_source

    def _on_left_click(self, *args):
        if not self.buttons_enabled or self._slide_in_progress:
            return
        self.clear_darken()
        new_frame = self._next_active_frame(-1)
        self.current_frame = new_frame
        self._play_slide_transition(direction=-1, new_frame=new_frame)
        print(f"⬅️ LEFT click → new_frame={new_frame} (game_type={self.game_type})")
        if self._left_callback:
            self._left_callback(new_frame)

    def _on_right_click(self, *args):
        if not self.buttons_enabled or self._slide_in_progress:
            return
        self.clear_darken()
        new_frame = self._next_active_frame(+1)
        self.current_frame = new_frame
        self._play_slide_transition(direction=+1, new_frame=new_frame)
        print(f"➡️ RIGHT click → new_frame={new_frame} (game_type={self.game_type})")
        if self._right_callback:
            self._right_callback(new_frame)

    def bind_left(self, callback):
        self._left_callback = callback

    def bind_right(self, callback):
        self._right_callback = callback

    def unbind_left(self, callback):
        if self._left_callback == callback:
            self._left_callback = None

    def unbind_right(self, callback):
        if self._right_callback == callback:
            self._right_callback = None

    def update_layout(self, *args):
        if self.width <= 0 or self.height <= 0:
            return

        min_dim = min(self.width, self.height)
        center_x = self.x + self.width / 2
        center_y = self.y + self.height * self.y_coef

        shadow_offset = self.height * self.shadow_offset_y_coef

        img_h = min_dim * self.center_img_h_coef
        img_w = img_h * self.center_img_ratio

        for img in (self.center_image_a, self.center_image_b):
            img.size = (img_w, img_h)
            img.center = (center_x, center_y)
            img.shadow_offset_y = shadow_offset

        btn_h = min_dim * self.side_button_h_coef
        btn_w = btn_h * self.side_button_ratio
        offset_x = self.width * self.side_offset_x_coef

        self.left_button.size = (btn_w, btn_h)
        self.left_button.center = (center_x - offset_x, center_y)
        self.left_button.shadow_offset_y = shadow_offset

        self.right_button.size = (btn_w, btn_h)
        self.right_button.center = (center_x + offset_x, center_y)
        self.right_button.shadow_offset_y = shadow_offset


class RSPScreen(BaseGameScreen):
    """Экран игры "Камень, ножницы, бумага" (игрок против компьютера)."""

    player_score = NumericProperty(0)
    computer_score = NumericProperty(0)
    result_text = StringProperty("Выберите ставку и нажмите SPIN!")

    spinner_y_coef = NumericProperty(0.35)

    # ===== НАГРАДА =====
    # Куда летит награда-монетка (относительно layout)
    TOKEN_SIZE_COEFF = 0.16
    TOKEN_CENTER_X_COEFF = 0.10
    TOKEN_CENTER_Y_COEFF = 0.92

    reward_rotation = 0
    reward_size_coeff = 0.14
    reward_fly_duration = 0.85
    reward_stagger_delay = 0.25

    # ✅ Звук отказа
    reject_sound_path = StringProperty('assets/sounds/reject.mp3')

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.background_image = 'assets/backgrounds/rsp_bg.jpg'

        self.game_type = 'classic'

        self.spin_button = None
        self.spinner_image_3 = None
        self.spinner_image_5 = None
        self.current_spinner = None

        self.is_spinning = False

        self.spinner_center_x = 0
        self.spinner_center_y = 0
        self.radius = 0
        self.winner_image = None

        self.current_animation = None
        self.spin_timer = None
        self.vibration_check_timer = None
        self.last_vibration_angle = None
        self.start_angle = 0
        self.total_rotations = 0
        self.target_angle = 0

        self.spin_sound = None
        self.result_sounds = {}

        self.classic_angles = {0: 'scissors', 120: 'paper', 240: 'rock'}
        self.classic_ordered_angles = [0, 120, 240]

        self.extended_angles = {0: 'spock', 72: 'scissors', 144: 'lizard',
                                216: 'rock', 288: 'paper'}
        self.extended_ordered_angles = [0, 72, 144, 216, 288]

        self.result_to_frame = {'scissors': 0, 'spock': 1, 'lizard': 2,
                                'rock': 3, 'paper': 4}
        self.frame_to_result = {0: 'scissors', 1: 'spock', 2: 'lizard',
                                3: 'rock', 4: 'paper'}

        self.classic_beats = {
            'rock': ['scissors'],
            'scissors': ['paper'],
            'paper': ['rock'],
        }
        self.extended_beats = {
            'rock': ['scissors', 'lizard'],
            'paper': ['rock', 'spock'],
            'scissors': ['paper', 'lizard'],
            'lizard': ['paper', 'spock'],
            'spock': ['scissors', 'rock'],
        }

        self.player_bet_frame = 0
        self.win_reward = 2

        self.tokens = LuckyToken()
        self.token_widget = None

        # ✅ Звук отказа
        self.reject_sound = None
        self._load_reject_sound()

        self.result_bar = None

        self._spinner_grey_anim = None
        self._is_darkened = False

        self.bind(spinner_y_coef=self.update_layout)

    # ==================== ЗВУК ОТКАЗА ====================

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

    # ======================================================

    # ==================== НАГРАДА: ЯКОРЯ ====================

    def _get_real_layout_size(self):
        if self.layout and self.layout.width > 1 and self.layout.height > 1:
            return self.layout.width, self.layout.height
        return Window.width, Window.height

    def get_reward_start_hint(self):
        """Монета-награда появляется в центре экрана."""
        return {'center_x': 0.5, 'center_y': 0.5}

    def get_reward_target_hint(self):
        """Летит к виджету жетонов."""
        layout_w, layout_h = self._get_real_layout_size()

        if self.token_widget and self.token_widget.parent:
            return {
                'center_x': self.token_widget.center_x / layout_w,
                'center_y': self.token_widget.center_y / layout_h,
            }

        return {
            'center_x': self.TOKEN_CENTER_X_COEFF,
            'center_y': self.TOKEN_CENTER_Y_COEFF,
        }

    def on_reward_arrived(self):
        """Пульс жетона, когда монета-награда долетела."""
        if not self.token_widget:
            return
        try:
            layout_w, layout_h = self._get_real_layout_size()
            base_size = min(layout_w, layout_h) * self.TOKEN_SIZE_COEFF
            base = (base_size, base_size)

            Animation.cancel_all(self.token_widget, 'size')
            self.token_widget.size = base

            big = (base[0] * 1.15, base[1] * 1.15)
            anim = (
                Animation(size=big, duration=0.12, t='out_quad') +
                Animation(size=base, duration=0.18, t='in_quad')
            )
            anim.start(self.token_widget)
        except Exception as e:
            print(f"⚠️ [RSPScreen] on_reward_arrived: {e}")

    # ======================================================

    def on_enter(self):
        super().on_enter()

        self.is_spinning = False
        self.winner_image = None
        self._is_darkened = False

        self.clear_ui()
        self.show_ui()
        self.load_result_sounds()
        self.reset_spinner()

        self.layout.bind(size=self.update_layout, pos=self.update_layout)
        self.update_layout()

    def on_leave(self):
        self.stop_all_vibration()

        if self.current_spinner:
            Animation.cancel_all(self.current_spinner)
            self.current_spinner.angle = 0
        if self.spinner_image_3:
            Animation.cancel_all(self.spinner_image_3)
            self.spinner_image_3.angle = 0
            self.spinner_image_3.opacity = 0
            self.spinner_image_3.desaturation = 0.0
        if self.spinner_image_5:
            Animation.cancel_all(self.spinner_image_5)
            self.spinner_image_5.angle = 0
            self.spinner_image_5.opacity = 0
            self.spinner_image_5.desaturation = 0.0

        if self.current_animation:
            if self.current_spinner:
                self.current_animation.stop(self.current_spinner)
            self.current_animation = None

        if self._spinner_grey_anim:
            self._spinner_grey_anim.cancel(self.current_spinner)
            self._spinner_grey_anim = None

        self.stop_all_sounds()
        self.stop_spinner_animation()

        if self.spin_timer:
            self.spin_timer.cancel()
            self.spin_timer = None

        if hasattr(self, 'spin_button') and self.spin_button:
            self.spin_button.unbind(on_press=self.start_spin)

        if hasattr(self, 'layout'):
            self.layout.unbind(size=self.update_layout, pos=self.update_layout)

        if self.result_bar:
            try:
                self.result_bar.unbind_left(self.on_left_pressed)
                self.result_bar.unbind_right(self.on_right_pressed)
            except Exception:
                pass

        self.spin_button = None
        self.spinner_image_3 = None
        self.spinner_image_5 = None
        self.current_spinner = None
        self.winner_image = None
        self.current_animation = None
        self.result_bar = None

        self.remove_switch_button()
        self._remove_token_widget()

        super().on_leave()

    def determine_winner(self, player_result, computer_result):
        if player_result == computer_result:
            return 'draw'
        beats = self.classic_beats if self.game_type == 'classic' else self.extended_beats
        if player_result in beats and computer_result in beats[player_result]:
            return 'player'
        if computer_result in beats and player_result in beats[computer_result]:
            return 'computer'
        return 'draw'

    def _play_win_pulse(self):
        if self.result_bar:
            self.result_bar.play_win_pulse(times=3, scale_up=1.10, duration=0.15)

    def _play_spinner_grey_out(self):
        if not self.current_spinner:
            return
        if self._spinner_grey_anim:
            self._spinner_grey_anim.cancel(self.current_spinner)
            self._spinner_grey_anim = None
        self._spinner_grey_anim = (
            Animation(desaturation=1.0, duration=0.35, t='out_quad') +
            Animation(desaturation=0.0, duration=0.35, t='in_quad')
        )
        self._spinner_grey_anim.start(self.current_spinner)

    def _play_lose_darken(self):
        if self.result_bar:
            self.result_bar.play_lose_darken(target=0.6, duration=0.35)
        self._is_darkened = True

    def _clear_darken(self):
        if self._is_darkened and self.result_bar:
            self.result_bar.clear_darken(duration=0.2)
            self._is_darkened = False

    def _create_token_widget(self):
        if self.token_widget and self.token_widget.parent:
            return
        self.token_widget = TokenWidget()
        self.token_widget.set_value(self.tokens.get_balance())
        self.token_widget.set_state(self.tokens.get_balance() > 0)
        self.layout.add_widget(self.token_widget)
        self.tokens.bind(on_balance_changed=self._on_balance_changed)
        self._position_token_widget()

    def _position_token_widget(self):
        if not self.token_widget:
            return
        layout_w, layout_h = self._get_real_layout_size()
        size = min(layout_w, layout_h) * self.TOKEN_SIZE_COEFF
        self.token_widget.size = (size, size)
        cx = layout_w * self.TOKEN_CENTER_X_COEFF
        cy = layout_h * self.TOKEN_CENTER_Y_COEFF
        self.token_widget.pos = (cx - size / 2, cy - size / 2)

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
        schedule = [(0.00, red), (0.25, yellow), (0.50, red),
                    (0.75, yellow), (1.00, red), (1.25, yellow)]

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

    def _create_result_bar(self):
        self.result_bar = RSPResultBar(
            y_coef=0.75,
            center_img_h_coef=0.30,
            center_img_ratio=1.0,
            frames_count=5,
            side_button_h_coef=0.15,
            side_button_ratio=1.0,
            side_offset_x_coef=0.30,
            game_type=self.game_type,
            shadow_offset_y_coef=0.05,
            shadow_alpha=0.4,
            shadow_scale=0.9,
            press_depth_coef=0.5,
        )
        self.result_bar.bind_left(self.on_left_pressed)
        self.result_bar.bind_right(self.on_right_pressed)
        self.layout.add_widget(self.result_bar)
        self.player_bet_frame = self.result_bar.current_frame

    def on_left_pressed(self, frame_index=None):
        if frame_index is not None:
            self.player_bet_frame = frame_index
        print(f"⬅️ Ставка игрока: frame={self.player_bet_frame} "
              f"({self.frame_to_result.get(self.player_bet_frame)})")

    def on_right_pressed(self, frame_index=None):
        if frame_index is not None:
            self.player_bet_frame = frame_index
        print(f"➡️ Ставка игрока: frame={self.player_bet_frame} "
              f"({self.frame_to_result.get(self.player_bet_frame)})")

    def stop_all_vibration(self):
        if self.vibration_check_timer:
            self.vibration_check_timer.cancel()
            self.vibration_check_timer = None
        self.last_vibration_angle = None

    def stop_all_sounds(self):
        if self.spin_sound:
            try:
                if self.spin_sound.state == 'play':
                    self.spin_sound.stop()
            except:
                pass
            self.spin_sound = None
        for sound in self.result_sounds.values():
            try:
                if sound.state == 'play':
                    sound.stop()
            except:
                pass

    def stop_spinner_animation(self):
        Animation.cancel_all(self)
        self.is_spinning = False
        self.stop_all_vibration()
        if self.current_spinner:
            self.current_spinner.angle = 0
        if self.spin_button:
            self.spin_button.is_active = 1
            self.spin_button.disabled = False

    def set_switch_button_state(self, enabled):
        super().set_switch_button_state(enabled)

    def reset_spinner(self):
        self.stop_all_sounds()
        self.stop_spinner_animation()
        self.stop_all_vibration()
        if self.spinner_image_3:
            Animation.cancel_all(self.spinner_image_3)
            self.spinner_image_3.angle = 0
            self.spinner_image_3.desaturation = 0.0
        if self.spinner_image_5:
            Animation.cancel_all(self.spinner_image_5)
            self.spinner_image_5.angle = 0
            self.spinner_image_5.desaturation = 0.0
        if self.current_animation:
            self.current_animation = None

    def go_to_menu(self):
        print(f"🏠 [RSPScreen] Возврат в меню")
        self.stop_all_sounds()
        self.stop_spinner_animation()
        self.stop_all_vibration()
        self._remove_token_widget()
        super().go_to_menu()

    def apply_current_game_type(self):
        if self.spinner_image_3:
            Animation.cancel_all(self.spinner_image_3)
            self.spinner_image_3.angle = 0
            self.spinner_image_3.opacity = 0
            self.spinner_image_3.desaturation = 0.0
        if self.spinner_image_5:
            Animation.cancel_all(self.spinner_image_5)
            self.spinner_image_5.angle = 0
            self.spinner_image_5.opacity = 0
            self.spinner_image_5.desaturation = 0.0

        if self.game_type == 'classic':
            if self.spinner_image_3:
                self.spinner_image_3.opacity = 1
                self.current_spinner = self.spinner_image_3
        else:
            if self.spinner_image_5:
                self.spinner_image_5.opacity = 1
                self.current_spinner = self.spinner_image_5

        if self.result_bar:
            self.result_bar.game_type = self.game_type
            self.player_bet_frame = self.result_bar.current_frame

        self.recreate_spin_button()

    def update_layout(self, *args):
        try:
            super().update_layout(*args)
        except AttributeError:
            pass

        if not hasattr(self, 'layout') or not self.layout:
            return

        self.spinner_center_x = self.layout.width / 2
        self.spinner_center_y = self.layout.height * self.spinner_y_coef

        min_dimension = min(self.layout.width, self.layout.height)
        self.radius = min_dimension * 0.3

        spinner_size_3 = min_dimension * 1.1
        spinner_size_5 = min_dimension * 1.0
        shadow_offset_y = self.layout.height * 0.05

        if self.spinner_image_3:
            self.spinner_image_3.size = (spinner_size_3, spinner_size_3)
            self.spinner_image_3.center = (self.spinner_center_x, self.spinner_center_y)
            self.spinner_image_3.set_shadow_offset(shadow_offset_y)

        if self.spinner_image_5:
            self.spinner_image_5.size = (spinner_size_5, spinner_size_5)
            self.spinner_image_5.center = (self.spinner_center_x, self.spinner_center_y)
            self.spinner_image_5.set_shadow_offset(shadow_offset_y)

        if self.spin_button:
            self.spin_button.center = (self.spinner_center_x, self.spinner_center_y)

        if self.result_bar:
            self.result_bar.update_layout()

        # Пересчитать позицию жетона при ресайзе
        self._position_token_widget()

    def setup_background(self):
        if self.bg_image:
            self.layout.remove_widget(self.bg_image)
        from kivy.uix.image import Image
        self.bg_image = Image(
            source=self.background_image,
            allow_stretch=True,
            keep_ratio=False
        )
        self.layout.add_widget(self.bg_image)

    def show_ui(self):
        self.create_switch_button(
            text="SWITCH",
            icon_path='assets/images/buttons/Roulette_switch_button.png',
            callback=self.toggle_game_type
        )

        self.create_spinner_images()
        self.create_spin_button()

        self._create_token_widget()
        self._create_result_bar()

        self.update_layout()
        self.apply_current_game_type()

    def create_spin_button(self):
        if self.game_type == 'classic' and self.spinner_image_3:
            spinner_size = self.spinner_image_3.width
        elif self.spinner_image_5:
            spinner_size = self.spinner_image_5.width
        else:
            spinner_size = 0

        koef = 1.15
        button_size = (spinner_size * koef, spinner_size * koef)

        self.spin_button = SpinButton(is_active=1, size=button_size)

        # ❗ Зона нажатия SPIN (настраивается здесь)
        self.spin_button.hit_scale_x = 1.3
        self.spin_button.hit_scale_y = 0.7
        self.spin_button.hit_offset_x = 0
        self.spin_button.hit_offset_y = 0

        self.spin_button.bind(on_press=self.start_spin)
        self.layout.add_widget(self.spin_button)

    def recreate_spin_button(self):
        if self.spin_button:
            self.spin_button.unbind(on_press=self.start_spin)
            self.layout.remove_widget(self.spin_button)
            self.spin_button = None
        self.create_spin_button()
        if hasattr(self, 'spinner_center_x') and hasattr(self, 'spinner_center_y'):
            self.spin_button.center = (self.spinner_center_x, self.spinner_center_y)

    def create_spinner_images(self):
        if os.path.exists('assets/images/rsp/spinner_3.png'):
            self.spinner_image_3 = RotatingImageWithShadow(
                name="spinner_3",
                source='assets/images/rsp/spinner_3.png',
                shadow_source='assets/images/rsp/spinner_3.png',
                size_hint=(None, None),
                opacity=0, angle=0
            )
            self.layout.add_widget(self.spinner_image_3)

        if os.path.exists('assets/images/rsp/spinner_5.png'):
            self.spinner_image_5 = RotatingImageWithShadow(
                name="spinner_5",
                source='assets/images/rsp/spinner_5.png',
                shadow_source='assets/images/rsp/spinner_5.png',
                size_hint=(None, None),
                opacity=0, angle=0
            )
            self.layout.add_widget(self.spinner_image_5)

    def load_result_sounds(self):
        sound_files = {
            'rock': 'assets/sounds/rsp/stone.ogg',
            'paper': 'assets/sounds/rsp/paper.ogg',
            'scissors': 'assets/sounds/rsp/scissors.ogg',
            'lizard': 'assets/sounds/rsp/lizard.ogg',
            'spock': 'assets/sounds/rsp/Spock.ogg'
        }
        from kivy.core.audio import SoundLoader
        for key, path in sound_files.items():
            if os.path.exists(path):
                sound = SoundLoader.load(path)
                if sound:
                    sound.volume = 0.8
                    self.result_sounds[key] = sound

    def play_result_sound(self, result):
        """Проиграть звук, соответствующий указанному результату."""
        if self.sound_manager.is_muted():
            return
        if result in self.result_sounds:
            sound = self.result_sounds[result]
            if self.spin_sound and self.spin_sound.state == 'play':
                self.spin_sound.stop()
                self.spin_sound = None
            sound.play()

    def start_spin(self, instance):
        if self.is_spinning or not self.current_spinner:
            return
        if self.tokens.get_balance() <= 0:
            self._spin_without_token()
            return
        self._clear_darken()
        self.tokens.spend(1, reason="rsp_spin")

        if self.result_bar:
            self.result_bar.buttons_enabled = 0

        self.set_switch_button_state(False)
        self.play_spin_sound()
        self.vibrate_long()

        self.is_spinning = True
        self.result_text = "ВРАЩЕНИЕ..."

        self.spin_button.is_active = 0
        self.spin_button.disabled = True

        self.start_angle = self.current_spinner.angle % 360

        if self.game_type == 'classic':
            valid_angles = [0, 120, 240]
        else:
            valid_angles = [0, 72, 144, 216, 288]

        target_base_angle = random.choice(valid_angles)
        full_rotations = random.randint(16, 24)
        self.total_rotations = full_rotations
        self.target_angle = target_base_angle - 360 * full_rotations

        anim = Animation(angle=self.target_angle, duration=14.0, t='out_quad')
        anim.bind(on_complete=self._on_spin_complete)
        anim.start(self.current_spinner)

        self.current_animation = anim
        self.spin_timer = Clock.schedule_once(self._force_stop_spin, 16.0)
        self.start_vibration_sync()

    def _spin_without_token(self):
        if not self.current_spinner:
            return
        self._clear_darken()
        self.is_spinning = True
        self.result_text = "НЕДОСТАТОЧНО ЖЕТОНОВ"
        if self.spin_button:
            self.spin_button.is_active = 0
            self.spin_button.disabled = True
        start_angle = self.current_spinner.angle
        target_angle = start_angle - 720
        anim = Animation(angle=target_angle, duration=1.2, t='in_out_quad')
        anim.bind(on_complete=lambda *a: self._after_empty_spin())
        anim.start(self.current_spinner)
        self._flash_token_widget()
        self.vibrate_short()

    def _after_empty_spin(self):
        self.is_spinning = False
        if self.spin_button:
            self.spin_button.is_active = 1
            self.spin_button.disabled = False
        if self.current_spinner:
            normalized = self.current_spinner.angle % 360
            if normalized < 0:
                normalized += 360
            self.current_spinner.angle = normalized
        self.result_text = "Выберите ставку и нажмите SPIN!"

    def start_vibration_sync(self):
        self.last_vibration_angle = None
        if self.game_type == 'classic':
            self.vibration_angles = [0, 120, 240]
        else:
            self.vibration_angles = [0, 72, 144, 216, 288]

        def check_angle(dt):
            if not self.is_spinning or not self.current_spinner:
                return
            current_angle = self.current_spinner.angle % 360
            if current_angle < 0:
                current_angle += 360
            for target_angle in self.vibration_angles:
                if self.last_vibration_angle is not None:
                    angle_passed = False
                    old_angle = self.last_vibration_angle
                    new_angle = current_angle
                    if old_angle > new_angle:
                        if target_angle <= old_angle and target_angle >= new_angle:
                            angle_passed = True
                    else:
                        if target_angle <= old_angle and target_angle >= 0:
                            angle_passed = True
                        elif target_angle >= new_angle and target_angle <= 360:
                            angle_passed = True
                    if angle_passed:
                        self.vibrate_short()
            self.last_vibration_angle = current_angle

        self.vibration_check_timer = Clock.schedule_interval(check_angle, 0.02)

    def _on_spin_complete(self, animation, widget):
        if not hasattr(self, 'layout') or not self.layout:
            return
        self.stop_vibration_check()
        if self.spin_timer:
            self.spin_timer.cancel()
            self.spin_timer = None
        if not widget or widget not in self.layout.children:
            return
        normalized_angle = widget.angle % 360
        if normalized_angle < 0:
            normalized_angle += 360
        if self.game_type == 'classic':
            valid_angles = [0, 120, 240]
        else:
            valid_angles = [0, 72, 144, 216, 288]
        closest_angle = min(valid_angles, key=lambda x: min(abs(x - normalized_angle),
                                                            abs(x + 360 - normalized_angle)))
        widget.angle = closest_angle
        self._finish_spin()

    def stop_vibration_check(self):
        if self.vibration_check_timer:
            self.vibration_check_timer.cancel()
            self.vibration_check_timer = None
        self.last_vibration_angle = None

    def _force_stop_spin(self, dt):
        if not hasattr(self, 'layout') or not self.layout:
            return
        self.stop_vibration_check()
        if self.is_spinning and self.current_animation:
            self.current_animation.stop(self.current_spinner)
            normalized_angle = self.current_spinner.angle % 360
            if normalized_angle < 0:
                normalized_angle += 360
            if self.game_type == 'classic':
                valid_angles = [0, 120, 240]
            else:
                valid_angles = [0, 72, 144, 216, 288]
            closest_angle = min(valid_angles, key=lambda x: min(abs(x - normalized_angle),
                                                                abs(x + 360 - normalized_angle)))
            self.current_spinner.angle = closest_angle
            self._finish_spin()
        self.spin_timer = None

    def _finish_spin(self):
        self.is_spinning = False
        self.set_switch_button_state(True)
        self.stop_vibration_check()

        if self.spin_button:
            self.spin_button.is_active = 1
            self.spin_button.disabled = False

        if not self.current_spinner:
            return

        current_angle = self.current_spinner.angle % 360
        if self.game_type == 'classic':
            computer_result = self.classic_angles.get(current_angle, 'scissors')
        else:
            computer_result = self.extended_angles.get(current_angle, 'spock')

        player_result = self.frame_to_result.get(self.player_bet_frame, 'scissors')
        winner = self.determine_winner(player_result, computer_result)

        result_names = {
            'rock': '🪨 КАМЕНЬ', 'paper': '📄 БУМАГА',
            'scissors': '✂️ НОЖНИЦЫ', 'lizard': '🦎 ЯЩЕРИЦА',
            'spock': '🖖 СПОК'
        }
        player_name = result_names.get(player_result, '—')
        computer_name = result_names.get(computer_result, '—')

        if winner == 'player':
            # Звук победившего варианта игрока
            self.play_result_sound(player_result)

            self.tokens.add(self.win_reward, reason="rsp_win")
            self.result_text = (
                f"Ставка: {player_name}\n"
                f"Выпало: {computer_name}\n"
                f"🎉 ВЫ ПОБЕДИЛИ! +{self.win_reward} жетон"
            )
            print(f"✅ Игрок победил: {player_result} vs {computer_result}, +{self.win_reward} жетон")
            self.vibrate_long()
            self._play_win_pulse()
            self._play_spinner_grey_out()

            # ✅ Запускаем анимацию награды — N монеток летят к жетону
            self.play_reward(amount=self.win_reward)

        elif winner == 'computer':
            # Звук победившего варианта компьютера
            self.play_result_sound(computer_result)

            self.result_text = (
                f"Ставка: {player_name}\n"
                f"Выпало: {computer_name}\n"
                f"❌ ВЫ ПРОИГРАЛИ"
            )
            print(f"❌ Игрок проиграл: {player_result} vs {computer_result}")
            self.vibrate_short()
            self._play_lose_darken()

        else:
            # Ничья — звук выпавшего варианта
            self.play_result_sound(computer_result)

            self.result_text = (
                f"Ставка: {player_name}\n"
                f"Выпало: {computer_name}\n"
                f"🤝 НИЧЬЯ"
            )
            print(f"🤝 Ничья: {player_result} vs {computer_result}")
            self.vibrate_short()
            self._play_lose_darken()

        if self.result_bar:
            self.result_bar.buttons_enabled = 1

    def show_result(self, result):
        result_names = {
            'rock': '🪨 КАМЕНЬ', 'paper': '📄 БУМАГА',
            'scissors': '✂️ НОЖНИЦЫ', 'lizard': '🦎 ЯЩЕРИЦА',
            'spock': '🖖 СПОК'
        }
        self.result_text = f"ВЫПАЛО: {result_names.get(result, '')}"

    def toggle_game_type(self, instance=None):
        if self.is_spinning:
            return
        self._clear_darken()
        self.stop_vibration_check()
        Animation.cancel_all(self)
        if self.spin_timer:
            self.spin_timer.cancel()
            self.spin_timer = None
        if self.game_type == 'classic':
            self.game_type = 'extended'
        else:
            self.game_type = 'classic'
        self.apply_current_game_type()

    def clear_ui(self):
        if not hasattr(self, 'layout') or not self.layout:
            return
        back_button = self.back_button
        for child in self.layout.children[:]:
            if child != self.bg_image and child != back_button:
                self.layout.remove_widget(child)
        self.spin_button = None
        self.spinner_image_3 = None
        self.spinner_image_5 = None
        self.current_spinner = None
        self.winner_image = None
        self.token_widget = None
        self.result_bar = None

    def play_spin_sound(self):
        if self.sound_manager.is_muted():
            return
        from kivy.core.audio import SoundLoader
        sound_path = 'assets/sounds/rsp/spinner_14.ogg'
        if os.path.exists(sound_path):
            self.spin_sound = SoundLoader.load(sound_path)
            if self.spin_sound:
                self.spin_sound.volume = 0.7
                self.spin_sound.play()