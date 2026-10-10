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
from kivy.graphics.texture import Texture
from kivy.uix.behaviors import ButtonBehavior
from kivy.uix.image import Image as KivyImage
from kivy.uix.floatlayout import FloatLayout
from kivy.metrics import dp
from PIL import Image as PILImage
import random
import os
import math
from functools import partial

from screens.base_game_screen import BaseGameScreen
from components.token_widget import TokenWidget
from lucky_token import LuckyToken

DEBUG_TOKEN_WIDGET = True


# ==================== ДЕТИ КОНТЕЙНЕРА ====================

class CoinSprite(Widget):
    """Спрайт-виджет монеты. Показывает ОДИН кадр из одного из двух
    спрайт-листов. Координаты кадра задаются через (row, col).
    Умеет анимировать переход: сдвиг по X и Y, масштаб, прозрачность."""

    frame_width = NumericProperty(128)
    frame_height = NumericProperty(128)
    cols = NumericProperty(12)
    rows = NumericProperty(9)

    sheet1_source = StringProperty('assets/sprites/coin_spritesheet_1.png')
    sheet2_source = StringProperty('assets/sprites/coin_spritesheet_2.png')

    sheet1_row = NumericProperty(0)
    sheet1_col = NumericProperty(0)

    sheet2_row = NumericProperty(0)
    sheet2_col = NumericProperty(0)

    active_sheet = NumericProperty(1)

    image_rotation = NumericProperty(0)

    slide_offset_x = NumericProperty(0.0)
    slide_offset_y = NumericProperty(0.0)
    slide_scale = NumericProperty(1.0)
    slide_opacity = NumericProperty(1.0)

    pulse_scale = NumericProperty(1.0)
    darken = NumericProperty(0.0)

    debug_highlight = BooleanProperty(False)
    debug_color = ColorProperty((1, 1, 0, 1))
    debug_line_width = NumericProperty(1)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.size_hint = (None, None)
        self._texture = None
        self._sheet_cache = {1: [], 2: []}

        self.bind(
            pos=self._redraw,
            size=self._redraw,
            center=self._redraw,
            sheet1_source=self._reload_sheet1,
            sheet2_source=self._reload_sheet2,
            active_sheet=self._apply_frame,
            sheet1_row=self._apply_frame,
            sheet1_col=self._apply_frame,
            sheet2_row=self._apply_frame,
            sheet2_col=self._apply_frame,
            image_rotation=self._reload_all,
            slide_offset_x=self._redraw,
            slide_offset_y=self._redraw,
            slide_scale=self._redraw,
            slide_opacity=self._redraw,
            pulse_scale=self._redraw,
            darken=self._redraw,
            debug_highlight=self._redraw,
            debug_color=self._redraw,
        )

        self._load_sheet(1)
        self._load_sheet(2)

    def _load_sheet(self, sheet_index):
        source = self.sheet1_source if sheet_index == 1 else self.sheet2_source
        if not source or not os.path.exists(source):
            print(f"=== CoinSprite: sheet{sheet_index} не найден: {source}")
            self._sheet_cache[sheet_index] = []
            return
        try:
            img = PILImage.open(source).convert('RGBA')
            tex_w, tex_h = img.size
            frame_w = min(self.frame_width, tex_w // self.cols)
            frame_h = min(self.frame_height, tex_h // self.rows)

            frames = []
            total = self.cols * self.rows
            for idx in range(total):
                row = idx // self.cols
                col = idx % self.cols

                left = col * frame_w
                upper = tex_h - (row + 1) * frame_h
                right = left + frame_w
                lower = upper + frame_h

                crop = img.crop((left, upper, right, lower))
                crop = crop.transpose(PILImage.FLIP_TOP_BOTTOM)

                if self.image_rotation:
                    crop = crop.rotate(-self.image_rotation, expand=True)

                tex = Texture.create(size=crop.size, colorfmt='rgba')
                tex.blit_buffer(crop.tobytes(), colorfmt='rgba', bufferfmt='ubyte')
                tex.mag_filter = 'linear'
                tex.min_filter = 'linear'
                frames.append(tex)

            self._sheet_cache[sheet_index] = frames
            print(f"=== CoinSprite: sheet{sheet_index} нарезан, "
                  f"кадров={len(frames)} rot={self.image_rotation}")
        except Exception as e:
            print(f"=== CoinSprite: ошибка загрузки sheet{sheet_index}: {e}")
            self._sheet_cache[sheet_index] = []

        if sheet_index == self.active_sheet:
            self._apply_frame()

    def _reload_sheet1(self, *args):
        self._load_sheet(1)

    def _reload_sheet2(self, *args):
        self._load_sheet(2)

    def _reload_all(self, *args):
        self._load_sheet(1)
        self._load_sheet(2)

    def _frame_index_for_sheet(self, sheet):
        if sheet == 1:
            row, col = int(self.sheet1_row), int(self.sheet1_col)
        else:
            row, col = int(self.sheet2_row), int(self.sheet2_col)
        row = max(0, min(row, self.rows - 1))
        col = max(0, min(col, self.cols - 1))
        return row * self.cols + col

    def _apply_frame(self, *args):
        sheet = self.active_sheet
        frames = self._sheet_cache.get(sheet, [])
        if not frames:
            self._texture = None
            self._redraw()
            return
        idx = self._frame_index_for_sheet(sheet)
        if idx >= len(frames):
            idx = len(frames) - 1
        self._texture = frames[idx]
        self._redraw()

    def show_sheet1_frame(self):
        self.active_sheet = 1

    def show_sheet2_frame(self):
        self.active_sheet = 2

    def _redraw(self, *args):
        self.canvas.clear()
        if self.width <= 0 or self.height <= 0:
            return

        ps = max(0.01, self.pulse_scale) * max(0.01, self.slide_scale)
        draw_w = self.width * ps
        draw_h = self.height * ps

        draw_cx = self.center_x + self.slide_offset_x
        draw_cy = self.center_y + self.slide_offset_y

        draw_x = draw_cx - draw_w / 2
        draw_y = draw_cy - draw_h / 2

        d = max(0.0, min(1.0, self.darken))
        brightness = 1.0 - (1.0 - 0.35) * d

        final_op = max(0.0, min(1.0, self.slide_opacity))
        img_color = (brightness, brightness, brightness, final_op)

        with self.canvas:
            if self._texture is not None:
                Color(*img_color)
                Rectangle(pos=(draw_x, draw_y), size=(draw_w, draw_h),
                          texture=self._texture)
            else:
                Color(0.2, 0.6, 1, final_op)
                Rectangle(pos=(draw_x, draw_y), size=(draw_w, draw_h))

            if self.debug_highlight and final_op > 0.05:
                Color(*self.debug_color[:3], self.debug_color[3] * final_op)
                Line(rectangle=(draw_x, draw_y, draw_w, draw_h),
                     width=self.debug_line_width)

    def cleanup(self):
        self._sheet_cache = {1: [], 2: []}
        self._texture = None
        self.canvas.clear()


class ButtonSprite(ButtonBehavior, Widget):
    """Кнопка-треугольник. Генерирует on_press/on_release.
    ✅ Умеет анимировать прозрачность (opacity) при блокировке.
    ✅ Играет звук Schpun.ogg при нажатии."""

    source = StringProperty('')
    mirrored = BooleanProperty(False)
    flip_vertical = BooleanProperty(False)
    image_rotation = NumericProperty(0)

    opacity = NumericProperty(1.0)

    debug_highlight = BooleanProperty(False)
    debug_color = ColorProperty((1, 0.5, 0, 1))
    debug_line_width = NumericProperty(1)
    debug_name = StringProperty('ButtonSprite')

    click_sound_path = StringProperty('assets/sounds/Schpun.ogg')
    click_volume = NumericProperty(0.6)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.size_hint = (None, None)
        self._texture = None

        self.click_sound = None
        self._load_click_sound()

        self.bind(
            source=self._load_texture,
            pos=self._redraw,
            size=self._redraw,
            opacity=self._redraw,
            mirrored=self._load_texture,
            flip_vertical=self._load_texture,
            image_rotation=self._load_texture,
            debug_highlight=self._redraw,
            debug_color=self._redraw,
        )

        if self.source:
            self._load_texture()

        self.bind(on_press=self._play_click_sound)

    def _load_click_sound(self):
        if os.path.exists(self.click_sound_path):
            self.click_sound = SoundLoader.load(self.click_sound_path)
            if self.click_sound:
                self.click_sound.volume = self.click_volume
                print(f"=== ButtonSprite[{self.debug_name}]: загружен звук "
                      f"{os.path.basename(self.click_sound_path)}")

    def _play_click_sound(self, *args):
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

    def _load_texture(self, *args):
        if not self.source or not os.path.exists(self.source):
            print(f"=== ButtonSprite: источник не найден: {self.source}")
            return
        try:
            img = PILImage.open(self.source).convert('RGBA')
            if self.image_rotation:
                img = img.rotate(-self.image_rotation, expand=True)
            img = img.transpose(PILImage.FLIP_TOP_BOTTOM)
            if self.mirrored:
                img = img.transpose(PILImage.FLIP_LEFT_RIGHT)
            if self.flip_vertical:
                img = img.transpose(PILImage.FLIP_TOP_BOTTOM)

            self._texture = Texture.create(size=img.size, colorfmt='rgba')
            self._texture.blit_buffer(img.tobytes(), colorfmt='rgba', bufferfmt='ubyte')
            self._texture.mag_filter = 'linear'
            self._texture.min_filter = 'linear'
            print(f"=== ButtonSprite[{self.debug_name}]: загружено "
                  f"{os.path.basename(self.source)} rot={self.image_rotation}")
            self._redraw()
        except Exception as e:
            print(f"=== ButtonSprite: ошибка загрузки {e}")

    def _redraw(self, *args):
        self.canvas.clear()
        if self.width <= 0 or self.height <= 0:
            return
        op = max(0.0, min(1.0, self.opacity))
        with self.canvas:
            if self._texture is not None:
                Color(1, 1, 1, op)
                Rectangle(pos=self.pos, size=self.size, texture=self._texture)
            else:
                Color(1, 0.5, 0, op)
                Rectangle(pos=self.pos, size=self.size)

            if self.debug_highlight:
                Color(self.debug_color[0], self.debug_color[1],
                      self.debug_color[2], self.debug_color[3] * op)
                Line(rectangle=(self.x, self.y, self.width, self.height),
                     width=self.debug_line_width)


# ==================== КОНТЕЙНЕР ====================

class DebugOverlay(Widget):
    """Контейнер с монетой и двумя кнопками."""

    debug_color = ColorProperty((0, 1, 0, 1))
    fill_alpha = NumericProperty(0.0)
    line_width = NumericProperty(0)
    debug_name = StringProperty('DebugOverlay')
    debug_highlight = BooleanProperty(False)

    buttons_blocked = BooleanProperty(False)
    blocked_opacity = NumericProperty(0.35)
    unblocked_opacity = NumericProperty(1.0)
    block_fade_duration = NumericProperty(0.2)

    coin_size_coef = NumericProperty(0.6)
    button_size_coef = NumericProperty(0.18)
    button_margin_coef = NumericProperty(0.06)
    button_image_rotation = NumericProperty(-90)

    coin_image_rotation = NumericProperty(90)

    slide_duration = NumericProperty(0.28)
    slide_distance_coef = NumericProperty(1.2)
    slide_min_scale = NumericProperty(0.3)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._transitioning = False
        self._on_bet_changed_cb = None

        self.coin_sprite_a = CoinSprite(
            frame_width=128, frame_height=128,
            cols=12, rows=9,
            sheet1_source='assets/sprites/coin_spritesheet_1.png',
            sheet2_source='assets/sprites/coin_spritesheet_2.png',
            sheet1_row=0, sheet1_col=0,
            sheet2_row=0, sheet2_col=0,
            active_sheet=1,
            image_rotation=self.coin_image_rotation,
            debug_highlight=False,
        )
        self.coin_sprite_b = CoinSprite(
            frame_width=128, frame_height=128,
            cols=12, rows=9,
            sheet1_source='assets/sprites/coin_spritesheet_1.png',
            sheet2_source='assets/sprites/coin_spritesheet_2.png',
            sheet1_row=0, sheet1_col=0,
            sheet2_row=0, sheet2_col=0,
            active_sheet=2,
            image_rotation=self.coin_image_rotation,
            debug_highlight=False,
        )
        self.coin_sprite_b.slide_opacity = 0.0

        self.coin_sprite = self.coin_sprite_a
        self._inactive_sprite = self.coin_sprite_b

        self.top_button_sprite = ButtonSprite(
            source='assets/images/buttons/triangle_button.png',
            mirrored=False,
            flip_vertical=False,
            image_rotation=self.button_image_rotation,
            debug_highlight=False,
            debug_name='TOP',
        )

        self.bottom_button_sprite = ButtonSprite(
            source='assets/images/buttons/triangle_button.png',
            mirrored=True,
            flip_vertical=True,
            image_rotation=self.button_image_rotation,
            debug_highlight=False,
            debug_name='BOTTOM',
        )

        self.add_widget(self.coin_sprite_a)
        self.add_widget(self.coin_sprite_b)
        self.add_widget(self.top_button_sprite)
        self.add_widget(self.bottom_button_sprite)

        self.top_button_sprite.bind(on_press=self._on_top_button_press)
        self.bottom_button_sprite.bind(on_press=self._on_bottom_button_press)

        self.bind(
            pos=self._on_geometry_changed,
            size=self._on_geometry_changed,
            coin_size_coef=self._on_geometry_changed,
            button_size_coef=self._on_geometry_changed,
            button_margin_coef=self._on_geometry_changed,
            button_image_rotation=self._on_button_rotation_changed,
            coin_image_rotation=self._on_coin_rotation_changed,
        )

        Clock.schedule_once(lambda dt: self._on_geometry_changed(), 0)
        Clock.schedule_once(lambda dt: self._on_geometry_changed(), 0.05)

    def set_bet_callback(self, cb):
        self._on_bet_changed_cb = cb

    def _notify_bet_changed(self, sheet=None):
        if sheet is None:
            sheet = self.coin_sprite.active_sheet
        if self._on_bet_changed_cb:
            try:
                self._on_bet_changed_cb(sheet)
            except Exception:
                pass

    def get_active_sheet(self):
        return self.coin_sprite.active_sheet

    def block_buttons(self):
        self.buttons_blocked = True

        for btn in (self.top_button_sprite, self.bottom_button_sprite):
            if not btn:
                continue
            Animation.cancel_all(btn, 'opacity')
            Animation(
                opacity=self.blocked_opacity,
                duration=self.block_fade_duration,
                t='out_quad'
            ).start(btn)
            btn.disabled = True

        print(f"[{self.debug_name}] 🔒 кнопки переключения заблокированы "
              f"(opacity→{self.blocked_opacity})")

    def unblock_buttons(self):
        self.buttons_blocked = False

        for btn in (self.top_button_sprite, self.bottom_button_sprite):
            if not btn:
                continue
            Animation.cancel_all(btn, 'opacity')
            Animation(
                opacity=self.unblocked_opacity,
                duration=self.block_fade_duration,
                t='out_quad'
            ).start(btn)
            btn.disabled = False

        print(f"[{self.debug_name}] 🔓 кнопки переключения разблокированы "
              f"(opacity→{self.unblocked_opacity})")

    def _on_top_button_press(self, *args):
        if self.buttons_blocked:
            print(f"[{self.debug_name}] TOP pressed — но кнопки заблокированы")
            return
        target = self._opposite_sheet_of_active()
        print(f"[{self.debug_name}] TOP pressed → target_sheet={target} "
              f"(direction=+1, вниз)")
        self._notify_bet_changed(target)
        self._start_slide_transition(target_sheet=target, direction=+1)

    def _on_bottom_button_press(self, *args):
        if self.buttons_blocked:
            print(f"[{self.debug_name}] BOTTOM pressed — но кнопки заблокированы")
            return
        target = self._opposite_sheet_of_active()
        print(f"[{self.debug_name}] BOTTOM pressed → target_sheet={target} "
              f"(direction=-1, вверх)")
        self._notify_bet_changed(target)
        self._start_slide_transition(target_sheet=target, direction=-1)

    def _opposite_sheet_of_active(self):
        return 2 if self.coin_sprite.active_sheet == 1 else 1

    def _start_slide_transition(self, target_sheet, direction):
        if self._transitioning:
            print(f"[{self.debug_name}] переход уже идёт, пропускаем")
            return
        self._transitioning = True

        old_img = self.coin_sprite
        new_img = self._inactive_sprite

        dist = self.height * self.slide_distance_coef

        new_img.active_sheet = target_sheet
        new_img.sheet1_row = old_img.sheet1_row
        new_img.sheet1_col = old_img.sheet1_col
        new_img.sheet2_row = old_img.sheet2_row
        new_img.sheet2_col = old_img.sheet2_col
        new_img.image_rotation = self.coin_image_rotation
        new_img._apply_frame()

        new_img.slide_offset_x = 0.0
        new_img.slide_offset_y = -direction * dist
        new_img.slide_scale = self.slide_min_scale
        new_img.slide_opacity = 0.0
        new_img.pulse_scale = 1.0
        new_img.darken = 0.0
        new_img._redraw()

        old_img.slide_offset_x = 0.0
        old_img.slide_offset_y = 0.0
        old_img.slide_scale = 1.0
        old_img.slide_opacity = 1.0
        old_img.pulse_scale = 1.0
        old_img.darken = 0.0
        old_img._redraw()

        out_anim = Animation(
            slide_offset_y=direction * dist,
            slide_scale=self.slide_min_scale,
            slide_opacity=0.0,
            duration=self.slide_duration,
            t='in_quad',
        )
        in_anim = Animation(
            slide_offset_y=0.0,
            slide_offset_x=0.0,
            slide_scale=1.0,
            slide_opacity=1.0,
            duration=self.slide_duration,
            t='out_quad',
        )

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

        old_img = self.coin_sprite
        new_img = self._inactive_sprite

        old_img.slide_offset_x = 0.0
        old_img.slide_offset_y = 0.0
        old_img.slide_scale = 1.0
        old_img.slide_opacity = 0.0
        old_img.pulse_scale = 1.0
        old_img.darken = 0.0
        old_img._redraw()

        new_img.slide_offset_x = 0.0
        new_img.slide_offset_y = 0.0
        new_img.slide_scale = 1.0
        new_img.slide_opacity = 1.0
        new_img.pulse_scale = 1.0
        new_img.darken = 0.0
        new_img._redraw()

        self.coin_sprite = new_img
        self._inactive_sprite = old_img

        self._transitioning = False

    def _on_button_rotation_changed(self, *args):
        if self.top_button_sprite:
            self.top_button_sprite.image_rotation = self.button_image_rotation
        if self.bottom_button_sprite:
            self.bottom_button_sprite.image_rotation = self.button_image_rotation

    def _on_coin_rotation_changed(self, *args):
        for cs in (self.coin_sprite_a, self.coin_sprite_b):
            if cs:
                cs.image_rotation = self.coin_image_rotation

    def _on_geometry_changed(self, *args):
        self.update_layout()
        for cs in (self.coin_sprite_a, self.coin_sprite_b):
            if cs:
                cs._apply_frame()

    def update_layout(self):
        if self.width <= 0 or self.height <= 0:
            return
        min_dim = min(self.width, self.height)
        cx = self.center_x
        cy = self.center_y

        coin_size = min_dim * self.coin_size_coef
        for cs in (self.coin_sprite_a, self.coin_sprite_b):
            cs.size = (coin_size, coin_size)
            cs.center = (cx, cy)

        btn_size = min_dim * self.button_size_coef
        margin = min_dim * self.button_margin_coef

        self.top_button_sprite.size = (btn_size, btn_size)
        self.top_button_sprite.center = (cx, self.top - margin - btn_size / 2)

        self.bottom_button_sprite.size = (btn_size, btn_size)
        self.bottom_button_sprite.center = (cx, self.y + margin + btn_size / 2)


# ==================== ОСТАЛЬНЫЕ КЛАССЫ ====================

class RotatedTokenWidget(TokenWidget):
    rotation = NumericProperty(0)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._rotate = None
        self._setup_rotation_graphics()
        self.bind(
            pos=self._update_rotation_origin,
            size=self._update_rotation_origin,
            center=self._update_rotation_origin,
            rotation=self._update_rotation_angle,
        )

    def _setup_rotation_graphics(self):
        with self.canvas.before:
            PushMatrix()
            self._rotate = Rotate(angle=self.rotation, origin=self.center)
        with self.canvas.after:
            PopMatrix()

    def _update_rotation_angle(self, instance, value):
        if self._rotate:
            self._rotate.angle = value

    def _update_rotation_origin(self, *args):
        if self._rotate:
            self._rotate.origin = (self.center_x, self.center_y)


class AdaptiveBackground(Image):
    def __init__(self, source='', **kwargs):
        super().__init__(**kwargs)
        self.source = source
        self.allow_stretch = True
        self.keep_ratio = False
        self.size_hint = (1, 1)
        self.pos_hint = {'x': 0, 'y': 0}


class DustParticle(Widget):
    velocity_x = NumericProperty(0)
    velocity_y = NumericProperty(0)
    opacity = NumericProperty(1.0)
    size_factor = NumericProperty(1.0)
    color = ColorProperty((1, 1, 0.5, 0.8))
    glow_intensity = NumericProperty(1.0)
    target_glow = NumericProperty(1.0)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.size = (random.uniform(2, 5), random.uniform(2, 5))
        self.velocity_x = random.uniform(-30, 30)
        self.velocity_y = random.uniform(-30, 30)
        self.opacity = random.uniform(0.3, 0.8)
        self.color = (
            random.uniform(0.8, 1.0),
            random.uniform(0.5, 0.8),
            random.uniform(0.2, 0.4),
            self.opacity
        )
        self.glow_intensity = 1.0
        self.target_glow = 1.0
        self.x = random.uniform(0, Window.width)
        self.y = random.uniform(0, Window.height)
        self.bind(pos=self._update_rect, size=self._update_rect)

    def _update_rect(self, *args):
        self.canvas.clear()
        with self.canvas:
            Color(*self.color[:3], self.color[3] * self.glow_intensity)
            Ellipse(pos=self.pos, size=self.size)
            if self.glow_intensity > 0.3:
                glow_size = (self.size[0] * 3, self.size[1] * 3)
                glow_pos = (self.x - self.size[0], self.y - self.size[1])
                Color(*self.color[:3], self.color[3] * self.glow_intensity * 0.3)
                Ellipse(pos=glow_pos, size=glow_size)

    def update(self, dt):
        self.x += self.velocity_x * dt
        self.y += self.velocity_y * dt
        if random.random() < 0.05:
            self.velocity_x += random.uniform(-10, 10)
            self.velocity_y += random.uniform(-10, 10)
        max_speed = 50
        self.velocity_x = max(-max_speed, min(max_speed, self.velocity_x))
        self.velocity_y = max(-max_speed, min(max_speed, self.velocity_y))
        if self.x < -self.width:
            self.x = Window.width
        elif self.x > Window.width:
            self.x = -self.width
        if self.y < -self.height:
            self.y = Window.height
        elif self.y > Window.height:
            self.y = -self.height
        if abs(self.glow_intensity - self.target_glow) > 0.01:
            self.glow_intensity += (self.target_glow - self.glow_intensity) * 0.1


class ParticleSystem(Widget):
    particles = ListProperty([])
    is_active = BooleanProperty(False)
    glow_mode = BooleanProperty(False)
    base_glow = NumericProperty(0.5)
    active_glow = NumericProperty(1.2)

    def __init__(self, num_particles=20, **kwargs):
        super().__init__(**kwargs)
        self.num_particles = num_particles
        self.update_clock = None
        self.bind(pos=self._update_all, size=self._update_all)
        self.create_particles()
        self.start_perpetual_motion()

    def create_particles(self):
        self.particles = []
        for _ in range(self.num_particles):
            particle = DustParticle()
            self.particles.append(particle)
            self.add_widget(particle)

    def start_perpetual_motion(self):
        self.is_active = True
        if not self.update_clock:
            self.update_clock = Clock.schedule_interval(self.update_particles, 1 / 60)

    def set_glow_mode(self, active=True):
        self.glow_mode = active
        target_glow = self.active_glow if active else self.base_glow
        for particle in self.particles:
            particle.target_glow = target_glow

    def update_particles(self, dt):
        if not self.is_active:
            return
        for particle in self.particles:
            particle.update(dt)
        if self.glow_mode and random.random() < 0.02:
            for particle in self.particles:
                particle.glow_intensity = min(particle.target_glow * 1.3, 2.0)

    def _update_all(self, *args):
        for particle in self.particles:
            particle._update_rect()

    def cleanup(self):
        self.is_active = False
        if self.update_clock:
            self.update_clock.cancel()
            self.update_clock = None
        self.particles = []
        self.clear_widgets()


class FullScreenTouchArea(Widget):
    is_enabled = BooleanProperty(False)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.size_hint = (1, 1)
        self.pos_hint = {'x': 0, 'y': 0}

    def on_touch_down(self, touch):
        if self.is_enabled and self.collide_point(*touch.pos):
            return True
        return super().on_touch_down(touch)


class TouchArea(Widget):
    is_enabled = BooleanProperty(True)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def on_touch_down(self, touch):
        return super().on_touch_down(touch)


class SpritesheetCoin(Image):
    """Монета из спрайт-листа 12x9 (108 кадров) — для игровой монеты.
    ✅ Включены мипмапы для более гладкого уменьшения текстуры."""

    current_frame = NumericProperty(0)
    is_animating = BooleanProperty(False)
    frames = ListProperty([])
    rotation_angle = NumericProperty(-90)
    coin_mirror = NumericProperty(1)
    animation_range = ListProperty([0, 11])
    ellipse_offset_x = NumericProperty(0)
    ellipse_offset_y = NumericProperty(0)
    extra_offset_x = NumericProperty(0)
    extra_offset_y = NumericProperty(0)
    shadow_offset_x = NumericProperty(0)
    shadow_offset_y = NumericProperty(0)
    shadow_scale_y = NumericProperty(1)
    shadow_alpha = NumericProperty(0.6)
    frame_step = NumericProperty(1)
    spiral_factor = NumericProperty(1.0)
    coin_opacity = NumericProperty(1.0)
    current_spritesheet = StringProperty('')
    _updating = BooleanProperty(False)
    debug_mode = BooleanProperty(False)

    def __init__(self, spritesheet_paths=None, frame_width=64, frame_height=64,
                 cols=12, rows=9, total_frames=108, start_frame=0,
                 shadow_offset_x=0, shadow_offset_y=0,
                 shadow_scale_y=1.0, shadow_alpha=0.6, coin_opacity=1.0,
                 debug=False, mipmap=True, **kwargs):
        super().__init__(mipmap=mipmap, **kwargs)

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
        self.shadow_offset_x = shadow_offset_x
        self.shadow_offset_y = shadow_offset_y
        self.shadow_scale_y = shadow_scale_y
        self.shadow_alpha = shadow_alpha
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
                    frame.mag_filter = 'linear'
                    frame.min_filter = 'linear_mipmap_linear'
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
        if not self.frames:
            return
        start_frame = max(0, min(start_frame, len(self.frames) - 1))
        end_frame = max(0, min(end_frame, len(self.frames) - 1))
        if start_frame > end_frame:
            start_frame, end_frame = end_frame, start_frame
        self.animation_range = [start_frame, end_frame]

    def _apply_mipmap_filter(self):
        tex = self.texture
        if tex:
            tex.mag_filter = 'linear'
            tex.min_filter = 'linear_mipmap_linear'

    def _update_rotation(self, *args):
        if not self.texture:
            return
        if self.width <= 0 or self.height <= 0 or (self.x == 0 and self.y == 0):
            Clock.schedule_once(lambda dt: self._update_rotation(), 0.1)
            return
        if self._updating:
            return
        self._updating = True

        self._apply_mipmap_filter()

        self.canvas.clear()
        center_x = self.x + self.width / 2
        center_y = self.y + self.height / 2
        with self.canvas:
            PushMatrix()
            Translate(center_x, center_y)
            Rotate(angle=self.rotation_angle, origin=(0, 0))
            Translate(self.shadow_offset_x, self.shadow_offset_y)
            Scale(1, -abs(self.shadow_scale_y), 1)
            Translate(-center_x, -center_y)
            Color(0, 0, 0, self.shadow_alpha)
            Rectangle(texture=self.texture, pos=self.pos, size=self.size)
            PopMatrix()
            PushMatrix()
            Translate(center_x, center_y)
            Scale(self.coin_mirror, 1, 1)
            Rotate(angle=self.rotation_angle, origin=(0, 0))
            Translate(-center_x, -center_y)
            Color(1.3, 1.3, 1.3, self.coin_opacity)
            Rectangle(texture=self.texture, pos=self.pos, size=self.size)
            PopMatrix()
        self._updating = False

    def _update_position(self, *args):
        base_center_x = 0.35
        base_center_y = 0.5
        current_offset_x = self.ellipse_offset_x * self.spiral_factor
        current_offset_y = self.ellipse_offset_y * self.spiral_factor
        self.pos_hint = {
            'center_x': base_center_x + current_offset_x + (self.extra_offset_x / Window.width),
            'center_y': base_center_y + current_offset_y + (self.extra_offset_y / Window.height)
        }
        Clock.schedule_once(lambda dt: self._update_rotation(), 0.05)

    def start_animation(self, fps=60, frame_step=1):
        if not self.frames or self.is_animating:
            return
        self.is_animating = True
        self.current_fps = fps
        self.frame_step = max(1, frame_step)
        self.current_frame = self.animation_range[0]
        self.frame_duration = 1.0 / fps
        if self.anim_clock:
            self.anim_clock.cancel()
        self.anim_clock = Clock.schedule_interval(self.next_frame, self.frame_duration)

    def next_frame(self, dt):
        if not self.is_animating or not self.frames:
            return
        next_frame = self.current_frame + self.frame_step
        if next_frame > self.animation_range[1]:
            range_size = self.animation_range[1] - self.animation_range[0] + 1
            next_frame = self.animation_range[0] + ((next_frame - self.animation_range[0]) % range_size)
        elif next_frame < self.animation_range[0]:
            range_size = self.animation_range[1] - self.animation_range[0] + 1
            next_frame = self.animation_range[1] - ((self.animation_range[1] - next_frame) % range_size)
        next_frame = max(self.animation_range[0], min(next_frame, self.animation_range[1]))
        self.current_frame = next_frame
        self.texture = self.frames[self.current_frame]
        self._update_rotation()

    def stop_animation(self):
        self.is_animating = False
        if self.anim_clock:
            self.anim_clock.cancel()
            self.anim_clock = None

    def set_result(self, result):
        if not self.frames:
            return
        self.stop_animation()
        frame_index = 107
        self.texture = self.frames[frame_index]
        self.canvas.clear()
        Clock.schedule_once(lambda dt: self._force_redraw(), 0.01)

    def _force_redraw(self):
        self._updating = False
        self._update_rotation()

    def reset_to_first_animation(self, start_frame=0):
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
        Clock.schedule_once(lambda dt: self._update_rotation(), 0.02)

    def cleanup(self):
        self.stop_animation()
        self.frames = []
        self.texture = None
        self.canvas.clear()


class FinalSpritesheetCoin(Image):
    """Финальная монета — тоже с мипмапами."""

    current_frame = NumericProperty(0)
    is_animating = BooleanProperty(False)
    frames = ListProperty([])
    rotation_angle = NumericProperty(270)

    shadow_offset_x = NumericProperty(0)
    shadow_offset_y = NumericProperty(0)
    shadow_scale_y = NumericProperty(1)
    shadow_alpha = NumericProperty(0.6)
    coin_opacity = NumericProperty(1.0)

    debug_mode = BooleanProperty(False)
    _updating = BooleanProperty(False)

    def __init__(self, spritesheet_path, frame_width=128, frame_height=128,
                 cols=6, rows=6, total_frames=36, start_frame=0,
                 shadow_offset_x=0, shadow_offset_y=0,
                 shadow_scale_y=1.0, shadow_alpha=0.6, coin_opacity=1.0,
                 debug=False, mipmap=True, **kwargs):
        super().__init__(mipmap=mipmap, **kwargs)

        self.frame_width = frame_width
        self.frame_height = frame_height
        self.cols = cols
        self.rows = rows
        self.total_frames = total_frames
        self.start_frame = start_frame
        self.anim_clock = None
        self.current_fps = 60
        self.debug_mode = debug
        self.shadow_offset_x = shadow_offset_x
        self.shadow_offset_y = shadow_offset_y
        self.shadow_scale_y = shadow_scale_y
        self.shadow_alpha = shadow_alpha
        self.coin_opacity = coin_opacity

        self.load_spritesheet(spritesheet_path)

        self.bind(texture=self._update_display)
        self.bind(pos=self._update_display, size=self._update_display)
        self.bind(shadow_offset_x=self._update_display,
                  shadow_offset_y=self._update_display,
                  shadow_scale_y=self._update_display,
                  shadow_alpha=self._update_display,
                  coin_opacity=self._update_display)

    def load_spritesheet(self, spritesheet_path):
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
                    frame.mag_filter = 'linear'
                    frame.min_filter = 'linear_mipmap_linear'
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
        next_frame = self.current_frame + 1
        if next_frame >= len(self.frames):
            if self.loop:
                next_frame = 0
            else:
                self.stop_animation()
                return
        self.current_frame = next_frame
        self.texture = self.frames[self.current_frame]
        self._update_display()

    def stop_animation(self):
        self.is_animating = False
        if self.anim_clock:
            self.anim_clock.cancel()
            self.anim_clock = None

    def _apply_mipmap_filter(self):
        tex = self.texture
        if tex:
            tex.mag_filter = 'linear'
            tex.min_filter = 'linear_mipmap_linear'

    def _update_display(self, *args):
        if not self.texture:
            return
        if self.width <= 0 or self.height <= 0:
            return
        if self._updating:
            return
        self._updating = True

        self._apply_mipmap_filter()

        self.canvas.clear()
        center_x = self.x + self.width / 2
        center_y = self.y + self.height / 2

        with self.canvas:
            PushMatrix()
            Translate(center_x, center_y)
            Rotate(angle=self.rotation_angle, origin=(0, 0))
            Translate(self.shadow_offset_x, self.shadow_offset_y)
            Scale(1, -abs(self.shadow_scale_y), 1)
            Translate(-center_x, -center_y)
            Color(0, 0, 0, self.shadow_alpha)
            Rectangle(texture=self.texture, pos=self.pos, size=self.size)
            PopMatrix()

            PushMatrix()
            Translate(center_x, center_y)
            Rotate(angle=self.rotation_angle, origin=(0, 0))
            Translate(-center_x, -center_y)
            Color(1.3, 1.3, 1.3, self.coin_opacity)
            Rectangle(texture=self.texture, pos=self.pos, size=self.size)
            PopMatrix()

        self._updating = False

    def cleanup(self):
        self.stop_animation()
        self.frames = []
        self.texture = None
        self.canvas.clear()


class CoinScreen(BaseGameScreen):
    """Игровой экран с монетой из спрайт-листов 12x9 (108 кадров)"""

    # ===== КНОПКА НАЗАД (переопределение источника и позиции) =====
    BACK_BUTTON_SIZE_COEFF = 0.12
    BACK_BUTTON_POS_X_COEFF = 0.05
    BACK_BUTTON_POS_Y_COEFF = 0.91
    BACK_BUTTON_SOURCE = 'assets/images/buttons/Orange_back_to_menu_button_90.png'
    BACK_BUTTON_ROTATION = 0   # картинка _90 уже повёрнута, доп. поворот не нужен
    # =============================================================

    SWIPE_THRESHOLD = 30
    TAP_MAX_DURATION = 1

    BG_DARK_TO_LIGHT_DURATION = 12.5
    BG_LIGHT_TO_DARK_DURATION = 1.5

    TOKEN_SIZE_COEFF = 0.16
    TOKEN_CENTER_X_COEFF = 0.93
    TOKEN_CENTER_Y_COEFF = 0.5
    TOKEN_ROTATION_ANGLE = -90

    DEBUG_OVERLAY_SIZE_HINT = (0.4, 0.4)
    DEBUG_OVERLAY_POS_HINT = {'center_x': 0.8, 'center_y': 0.8}

    # ===== СТАВКИ И НАГРАДЫ =====
    BET_AMOUNT = 1
    WIN_PAYOUT = 2

    reward_rotation = -90


    # ✅ Звук отказа
    reject_sound_path = StringProperty('assets/sounds/reject.mp3')

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self.tokens = LuckyToken()
        self.token_widget = None
        self._token_base_size = None

        self.debug_overlay = None

        self.adaptive_background_dark = None
        self.adaptive_background_light = None
        self.adaptive_background = None

        self._bg_fade_anim_dark = None
        self._bg_fade_anim_light = None

        self.spritesheet_path_1 = 'assets/sprites/coin_spritesheet_1.png'
        self.spritesheet_path_2 = 'assets/sprites/coin_spritesheet_2.png'
        self.final_spritesheet_orel = 'assets/sprites/orel_spritesheet.png'
        self.final_spritesheet_reshka = 'assets/sprites/reshka_spritesheet.png'
        self.orel_image = 'assets/sprites/orel.png'
        self.reshka_image = 'assets/sprites/reshka.png'

        self.coin = None
        self.final_coin = None
        self.touch_area = None
        self.fullscreen_touch_area = None
        self.info_label = None
        self.stats_label = None
        self.flip_sound = None
        self.crystal_sound = None
        self.particle_system = None
        self.return_animation_active = False
        self.is_animating = False
        self.vibration_event = None
        self.vibration_event_pause = None

        self.current_side = 0
        self.total_flips = 0
        self.heads_count = 0
        self.tails_count = 0
        self.coin_start_frame = 0
        self.coin_start_side = 0

        self.coin_height = 55
        self.final_coin_size = 220
        self.initial_shadow_offset = -53.35
        self.current_shadow_offset = -53.35
        self.shadow_reduction_factor = 11

        self.ellipse_radius_x = 0.2
        self.ellipse_radius_y = 0.4
        self.start_offset_x = -0.2
        self.start_offset_y = 0

        self.final_offset_x_pixels = -18.15

        self.center_pos_x = 0.35
        self.center_pos_y = 0.5
        self.start_pos_x = self.center_pos_x - self.ellipse_radius_x
        self.start_pos_y = self.center_pos_y

        self.debug_mode = True
        self.rotation_direction = 1

        self._gesture_active = False
        self._gesture_start_pos = None
        self._gesture_start_time = 0
        self._gesture_swipe_handled = False
        self._window_gestures_bound = False

        # ===== СТАВКИ =====
        self._bet_placed_this_round = False
        self._no_tokens_flash_shown = False
        self._player_bet_sheet = 1

        # ✅ Звук отказа
        self.reject_sound = None
        self._load_reject_sound()

    def get_screen_size(self):
        from kivy.utils import platform
        if platform == 'android':
            width, height = Window.system_size
        else:
            if self.screen_params:
                width = self.screen_params.width
                height = self.screen_params.height
            else:
                width = Window.width
                height = Window.height
        return width, height

    # ==================== ✅ НЕДОСТАЮЩИЕ МЕТОДЫ РАСЧЁТА ====================

    def calculate_ellipse_params(self):
        screen_width, screen_height = self.get_screen_size()
        radius_y = 0.35
        radius_x = 0.2
        aspect_ratio = screen_width / screen_height
        if aspect_ratio > 1.5:
            radius_x = min(radius_x * 1.2, 0.35)
        elif aspect_ratio < 0.7:
            radius_y = min(radius_y * 1.2, 0.55)
        return radius_x, radius_y

    def calculate_coin_size(self):
        screen_width, screen_height = self.get_screen_size()
        base_width = 400
        base_coin_size = 55
        scale = screen_width / base_width
        coin_size = base_coin_size * scale
        coin_size = max(40, min(coin_size, 120))
        return coin_size

    def calculate_shadow_offset(self, coin_height):
        return -coin_height * 0.97 + coin_height * 0.13

    def calculate_final_coin_size(self, coin_height):
        return coin_height * 4

    def calculate_final_offset(self, coin_height):
        return -coin_height * 0.33

    # =======================================================================

    # ==================== ЗВУК ОТКАЗА ====================

    def _load_reject_sound(self):
        if os.path.exists(self.reject_sound_path):
            self.reject_sound = SoundLoader.load(self.reject_sound_path)
            if self.reject_sound:
                self.reject_sound.volume = 0.8

    def _play_reject_sound(self):
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

    # ==================== ЛОГИКА СТАВОК ====================

    def _can_play(self):
        if self._bet_placed_this_round:
            return True
        return self.tokens.get_balance() >= self.BET_AMOUNT

    def _try_place_bet(self):
        if self._bet_placed_this_round:
            return True

        if self.tokens.get_balance() < self.BET_AMOUNT:
            if not self._no_tokens_flash_shown:
                self._flash_token_widget()
                self._no_tokens_flash_shown = True
            print(f"🚫 [BET] Недостаточно жетонов: "
                  f"balance={self.tokens.get_balance()}, bet={self.BET_AMOUNT}")
            return False

        ok = self.tokens.spend(self.BET_AMOUNT, reason="coin_bet")
        if not ok:
            self._flash_token_widget()
            return False

        self._bet_placed_this_round = True
        print(f"💸 [BET] Ставка {self.BET_AMOUNT} списана. "
              f"balance={self.tokens.get_balance()}")
        return True

    def _refund_bet_if_needed(self):
        if not self._bet_placed_this_round:
            return

        self.tokens.add(self.BET_AMOUNT, reason="coin_bet_refund")
        print(f"↩️ [BET] Ставка {self.BET_AMOUNT} возвращена. "
              f"balance={self.tokens.get_balance()}")

        self._bet_placed_this_round = False
        self._no_tokens_flash_shown = False

    def _reset_bet_flag(self):
        self._bet_placed_this_round = False
        self._no_tokens_flash_shown = False

    def _apply_bet_result(self, result_side):
        """result_side: 0 — орёл (лист 1), 1 — решка (лист 2)."""
        result_sheet = result_side + 1
        win = (result_sheet == self._player_bet_sheet)

        print(f"🎲 [RESULT] bet_sheet={self._player_bet_sheet}, "
              f"result_sheet={result_sheet}, win={win}")

        if win and self.WIN_PAYOUT > 0:
            self.tokens.add(self.WIN_PAYOUT, reason="coin_win")
            print(f"💰 [PAYOUT] Начислено {self.WIN_PAYOUT}. "
                  f"balance={self.tokens.get_balance()}")
            # ✅ Запускаем N монет-наград — по одной за каждый жетон
            self.play_reward(amount=self.WIN_PAYOUT)
        else:
            print(f"😢 [RESULT] Проигрыш. balance={self.tokens.get_balance()}")

        self._reset_bet_flag()

    # ==================== НАГРАДА: ЯКОРЯ ====================

    def get_reward_start_hint(self):
        """Монета-награда появляется в центре экрана."""
        return {'center_x': 0.5, 'center_y': 0.5}

    def get_reward_target_hint(self):
        """Летит к виджету жетонов (справа по центру)."""
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
        """Пульс жетона, когда монета-награда долетела.
        Всегда возвращается к ИСХОДНОМУ размеру, а не к текущему."""
        if not self.token_widget:
            return
        try:
            # Эталонный размер: пересчитываем каждый раз от констант,
            # чтобы накопления не было никогда.
            layout_w, layout_h = self._get_real_layout_size()
            base_size = min(layout_w, layout_h) * self.TOKEN_SIZE_COEFF
            base = (base_size, base_size)

            # Принудительно ставим эталон перед пульсацией
            Animation.cancel_all(self.token_widget, 'size')
            self.token_widget.size = base

            big = (base[0] * 1.15, base[1] * 1.15)
            anim = (
                Animation(size=big, duration=0.12, t='out_quad') +
                Animation(size=base, duration=0.18, t='in_quad')
            )
            anim.start(self.token_widget)
        except Exception as e:
            print(f"⚠️ [CoinScreen] on_reward_arrived: {e}")

    # ==================== ЖЕТОН ====================

    def _get_real_layout_size(self):
        if self.layout and self.layout.width > 1 and self.layout.height > 1:
            return self.layout.width, self.layout.height
        return Window.width, Window.height

    def _create_token_widget(self):
        if self.token_widget and self.token_widget.parent:
            return

        # Сброс эталона — он будет заново зафиксирован при первой пульсации
        self._token_base_size = None

        self.token_widget = RotatedTokenWidget(
            size_hint=(None, None),
            pos_hint={},
        )
        self.token_widget.rotation = self.TOKEN_ROTATION_ANGLE

        self.token_widget.set_value(self.tokens.get_balance())
        self.token_widget.set_state(self.tokens.get_balance() > 0)
        self.layout.add_widget(self.token_widget)

        self.tokens.bind(on_balance_changed=self._on_balance_changed)
        self._position_token_widget()

        Clock.schedule_once(lambda dt: self._position_token_widget(), 0.1)
        Clock.schedule_once(lambda dt: self._position_token_widget(), 0.5)
        Clock.schedule_once(lambda dt: self._position_token_widget(), 1.0)

        Window.bind(on_resize=self._on_window_resize)

    def _position_token_widget(self):
        if not self.token_widget:
            return
        self.token_widget.size_hint = (None, None)
        self.token_widget.pos_hint = {}
        layout_w, layout_h = self._get_real_layout_size()
        size = min(layout_w, layout_h) * self.TOKEN_SIZE_COEFF
        self.token_widget.size = (size, size)

        # Эталонный размер обновился — сбрасываем кэш
        self._token_base_size = None

        center_x = layout_w * self.TOKEN_CENTER_X_COEFF
        center_y = layout_h * self.TOKEN_CENTER_Y_COEFF
        self.token_widget.pos = (center_x - size / 2, center_y - size / 2)

    def _on_window_resize(self, *args):
        self._position_token_widget()

    def _on_balance_changed(self, instance, new_balance):
        if self.token_widget:
            self.token_widget.set_value(int(new_balance))
            self.token_widget.set_state(int(new_balance) > 0)

    def _remove_token_widget(self):
        try:
            self.tokens.unbind(on_balance_changed=self._on_balance_changed)
        except Exception:
            pass
        try:
            Window.unbind(on_resize=self._on_window_resize)
        except Exception:
            pass
        if self.token_widget and self.token_widget.parent:
            self.layout.remove_widget(self.token_widget)
        self.token_widget = None
        self._token_base_size = None

    def _flash_token_widget(self):
        if not self.token_widget:
            return
        label = self.token_widget.value_label
        if not label:
            return

        self._play_reject_sound()

        yellow = (1, 0.9, 0.2, 1)
        red = (1, 0, 0, 1)

        original_font_size = label.font_size
        label.font_size = original_font_size * 1.15

        schedule = [
            (0.00, red), (0.25, yellow), (0.50, red),
            (0.75, yellow), (1.00, red), (1.25, yellow),
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

    # ==================== КОЛБЭК СТАВКИ ОВЕРЛЕЯ ====================

    def _on_overlay_bet_changed(self, sheet):
        self._player_bet_sheet = sheet
        print(f"🎯 [BET] Игрок выбрал лист {sheet} "
              f"({'орёл' if sheet == 1 else 'решка'})")

    # ==================== БЛОКИРОВКА КНОПОК ОВЕРЛЕЯ ====================

    def _block_debug_overlay_buttons(self):
        if self.debug_overlay:
            self.debug_overlay.block_buttons()

    def _unblock_debug_overlay_buttons(self):
        if self.debug_overlay:
            self.debug_overlay.unblock_buttons()

    # ==================== ОТЛАДОЧНЫЙ ВИДЖЕТ ====================

    def _create_debug_overlay(self):
        if self.debug_overlay and self.debug_overlay.parent:
            return

        self.debug_overlay = DebugOverlay(
            size_hint=self.DEBUG_OVERLAY_SIZE_HINT,
            pos_hint=self.DEBUG_OVERLAY_POS_HINT,
            debug_name='DebugOverlay[coin]',
            coin_size_coef=0.6,
            button_size_coef=0.3,
            button_margin_coef=0.06,
            button_image_rotation=90,
            coin_image_rotation=-90,
            slide_duration=0.28,
            slide_distance_coef=0.5,
            slide_min_scale=0.3,
        )
        self.layout.add_widget(self.debug_overlay)

        for cs in (self.debug_overlay.coin_sprite_a, self.debug_overlay.coin_sprite_b):
            cs.sheet1_row = 7
            cs.sheet1_col = 0
            cs.sheet2_row = 7
            cs.sheet2_col = 0

        self.debug_overlay.coin_sprite_a.active_sheet = 1
        self.debug_overlay.coin_sprite_b.active_sheet = 2
        self.debug_overlay.coin_sprite_a._apply_frame()
        self.debug_overlay.coin_sprite_b._apply_frame()

        self.debug_overlay.coin_sprite = self.debug_overlay.coin_sprite_a
        self.debug_overlay._inactive_sprite = self.debug_overlay.coin_sprite_b

        self.debug_overlay.set_bet_callback(self._on_overlay_bet_changed)
        self._player_bet_sheet = self.debug_overlay.get_active_sheet()
        print(f"🎯 [BET] Начальная ставка: лист {self._player_bet_sheet}")

        self.debug_overlay.unblock_buttons()

        Clock.schedule_once(lambda dt: self.debug_overlay._on_geometry_changed(), 0.05)

    def _remove_debug_overlay(self):
        if self.debug_overlay and self.debug_overlay.parent:
            self.layout.remove_widget(self.debug_overlay)
        self.debug_overlay = None

    # ==================== ФОН ====================

    def _ensure_backgrounds(self):
        if self.adaptive_background_light is None:
            self.adaptive_background_light = AdaptiveBackground(
                source='assets/backgrounds/coin_bg.png'
            )
            self.adaptive_background_light.opacity = 0
            self.layout.add_widget(self.adaptive_background_light, index=0)

        if self.adaptive_background_dark is None:
            self.adaptive_background_dark = AdaptiveBackground(
                source='assets/backgrounds/coin_dark_bg.png'
            )
            self.adaptive_background_dark.opacity = 1
            self.layout.add_widget(self.adaptive_background_dark, index=1)

        self.adaptive_background = self.adaptive_background_light

    def _fade_backgrounds(self, dark_target, light_target, duration):
        if not self.adaptive_background_dark or not self.adaptive_background_light:
            return
        if self._bg_fade_anim_dark:
            self._bg_fade_anim_dark.cancel(self.adaptive_background_dark)
            self._bg_fade_anim_dark = None
        if self._bg_fade_anim_light:
            self._bg_fade_anim_light.cancel(self.adaptive_background_light)
            self._bg_fade_anim_light = None
        self._bg_fade_anim_dark = Animation(opacity=dark_target, duration=duration, t='linear')
        self._bg_fade_anim_light = Animation(opacity=light_target, duration=duration, t='linear')
        self._bg_fade_anim_dark.start(self.adaptive_background_dark)
        self._bg_fade_anim_light.start(self.adaptive_background_light)

    def _show_dark_background(self, duration=None):
        if duration is None:
            duration = self.BG_LIGHT_TO_DARK_DURATION
        self._fade_backgrounds(dark_target=1, light_target=0, duration=duration)

    def _show_light_background(self, duration=None):
        if duration is None:
            duration = self.BG_DARK_TO_LIGHT_DURATION
        self._fade_backgrounds(dark_target=0, light_target=1, duration=duration)

    def _finalize_light_background(self):
        if self.adaptive_background_dark:
            if self._bg_fade_anim_dark:
                self._bg_fade_anim_dark.cancel(self.adaptive_background_dark)
                self._bg_fade_anim_dark = None
            self.adaptive_background_dark.opacity = 0
        if self.adaptive_background_light:
            if self._bg_fade_anim_light:
                self._bg_fade_anim_light.cancel(self.adaptive_background_light)
                self._bg_fade_anim_light = None
            self.adaptive_background_light.opacity = 1

    # ==================== ON_ENTER / ON_LEAVE ====================

    def on_enter(self):
        self._ensure_backgrounds()
        self._fade_backgrounds(dark_target=1, light_target=0, duration=0)

        super().on_enter()

        if hasattr(self, 'bg_image') and self.bg_image:
            if self.bg_image in self.layout.children:
                self.layout.remove_widget(self.bg_image)
            self.bg_image = None

        self.setup_game_ui()
        self.load_flip_sound()
        self.load_crystal_sound()
        Window.bind(on_resize=self.on_window_resize)

        self._bind_window_gestures()

        if self.coin:
            self.coin.stop_animation()
            Animation.cancel_all(self.coin)
            if self.current_side == 0:
                self.coin.load_spritesheet(self.spritesheet_path_1)
            else:
                self.coin.load_spritesheet(self.spritesheet_path_2)
            if self.coin.frames and len(self.coin.frames) > 0:
                self.coin.texture = self.coin.frames[0]
            self.coin.pos_hint = {'center_x': self.start_pos_x, 'center_y': self.start_pos_y}
            self.coin.size = (self.coin_height, self.coin_height)
            self.coin.opacity = 1
            self.coin.shadow_offset_x = 0
            self.coin.shadow_offset_y = self.initial_shadow_offset
            self.coin.shadow_scale_y = 1.0
            self.coin.shadow_alpha = 0.5
            self.coin.ellipse_offset_x = -self.ellipse_radius_x
            self.coin.ellipse_offset_y = 0
            self.coin.spiral_factor = 1.0
            self.coin.extra_offset_x = 0
            self.coin._update_position()
            self.coin._update_rotation()

        if self.final_coin:
            self.final_coin.stop_animation()
            Animation.cancel_all(self.final_coin)
            self.final_coin.opacity = 0

        self.is_animating = False
        self.return_animation_active = False
        self._reset_gesture_state()

        if self.fullscreen_touch_area:
            self.fullscreen_touch_area.is_enabled = False

        if self.touch_area:
            self.touch_area.is_enabled = True

        if self.particle_system:
            self.particle_system.set_glow_mode(False)

        self._reset_bet_flag()
        self._create_token_widget()
        self._create_debug_overlay()

        self._unblock_debug_overlay_buttons()

    def on_leave(self):
        self._unblock_debug_overlay_buttons()
        self._unbind_window_gestures()
        self._remove_token_widget()
        self._remove_debug_overlay()
        self._reset_bet_flag()
        super().on_leave()
        self.cleanup_all()
        Window.unbind(on_resize=self.on_window_resize)

    def _bind_window_gestures(self):
        if self._window_gestures_bound:
            return
        Window.bind(on_touch_down=self._on_window_touch_down)
        Window.bind(on_touch_move=self._on_window_touch_move)
        Window.bind(on_touch_up=self._on_window_touch_up)
        self._window_gestures_bound = True

    def _unbind_window_gestures(self):
        if not self._window_gestures_bound:
            return
        try:
            Window.unbind(on_touch_down=self._on_window_touch_down)
            Window.unbind(on_touch_move=self._on_window_touch_move)
            Window.unbind(on_touch_up=self._on_window_touch_up)
        except Exception:
            pass
        self._window_gestures_bound = False

    def _reset_gesture_state(self):
        self._gesture_active = False
        self._gesture_start_pos = None
        self._gesture_start_time = 0
        self._gesture_swipe_handled = False

    def _is_touch_on_coin(self, touch):
        if not self.touch_area:
            return False
        if not self.touch_area.is_enabled:
            return False
        if self.touch_area.collide_point(*touch.pos):
            return True
        if self.coin and self.coin.opacity > 0 and self.coin.collide_point(*touch.pos):
            return True
        return False

    def _is_touch_on_final_coin(self, touch):
        if not self.final_coin:
            return False
        if self.final_coin.opacity <= 0:
            return False
        return self.final_coin.collide_point(*touch.pos)

    def _on_window_touch_down(self, window, touch):
        if self._gesture_active:
            return False
        if self._is_touch_on_final_coin(touch) and not self.final_coin.is_animating:
            self.return_coin_to_start()
            return False
        if not self._is_touch_on_coin(touch):
            return False
        if self.is_animating:
            return False
        self._gesture_active = True
        self._gesture_start_pos = (touch.x, touch.y)
        self._gesture_start_time = Clock.get_boottime()
        self._gesture_swipe_handled = False
        return False

    def _on_window_touch_move(self, window, touch):
        if not self._gesture_active or self._gesture_start_pos is None:
            return False
        if self.is_animating:
            self._reset_gesture_state()
            return False
        dx = touch.x - self._gesture_start_pos[0]
        dy = touch.y - self._gesture_start_pos[1]
        distance = math.hypot(dx, dy)
        if not self._gesture_swipe_handled and distance >= self.SWIPE_THRESHOLD:
            self._gesture_swipe_handled = True
            self._on_coin_swipe(dx, dy)
        return False

    def _on_window_touch_up(self, window, touch):
        if not self._gesture_active:
            return False
        was_swipe = self._gesture_swipe_handled
        elapsed = Clock.get_boottime() - self._gesture_start_time
        self._reset_gesture_state()
        if was_swipe:
            return False
        if self.is_animating:
            return False
        if elapsed <= self.TAP_MAX_DURATION:
            self._on_coin_tap()
        return False

    def cleanup_all(self):
        if self.coin:
            Animation.cancel_all(self.coin)
            self.coin.cleanup()
            if self.coin in self.layout.children:
                self.layout.remove_widget(self.coin)
            self.coin = None
        if self.final_coin:
            Animation.cancel_all(self.final_coin)
            self.final_coin.cleanup()
            if self.final_coin in self.layout.children:
                self.layout.remove_widget(self.final_coin)
            self.final_coin = None
        if self.particle_system:
            self.particle_system.cleanup()
            if self.particle_system in self.layout.children:
                self.layout.remove_widget(self.particle_system)
            self.particle_system = None
        if self.touch_area and self.touch_area in self.layout.children:
            self.layout.remove_widget(self.touch_area)
            self.touch_area = None
        if self.fullscreen_touch_area and self.fullscreen_touch_area in self.layout.children:
            self.layout.remove_widget(self.fullscreen_touch_area)
            self.fullscreen_touch_area = None
        if self.flip_sound:
            self.flip_sound.stop()
            self.flip_sound.unload()
            self.flip_sound = None
        if self.crystal_sound:
            self.crystal_sound.stop()
            self.crystal_sound.unload()
            self.crystal_sound = None
        if self._bg_fade_anim_dark and self.adaptive_background_dark:
            self._bg_fade_anim_dark.cancel(self.adaptive_background_dark)
        if self._bg_fade_anim_light and self.adaptive_background_light:
            self._bg_fade_anim_light.cancel(self.adaptive_background_light)
        self._bg_fade_anim_dark = None
        self._bg_fade_anim_light = None
        self.is_animating = False
        self.return_animation_active = False
        self.stop_vibration()
        self.stop_pause_vibration()
        self._reset_bet_flag()
        self._unblock_debug_overlay_buttons()

    def on_window_resize(self, instance, width, height):
        if self.coin:
            new_radius_x, new_radius_y = self.calculate_ellipse_params()
            if abs(self.ellipse_radius_x - new_radius_x) > 0.01:
                self.ellipse_radius_x = new_radius_x
                self.ellipse_radius_y = new_radius_y
                self.start_pos_x = self.center_pos_x - self.ellipse_radius_x
                if not self.coin.is_animating:
                    self.coin.ellipse_offset_x = -self.ellipse_radius_x
                    self.coin._update_position()
            new_coin_size = self.calculate_coin_size()
            if abs(self.coin.size[0] - new_coin_size) > 1:
                self.coin.size = (new_coin_size, new_coin_size)
                self.coin_height = new_coin_size
                self.final_coin_size = self.calculate_final_coin_size(new_coin_size)
                self.initial_shadow_offset = self.calculate_shadow_offset(new_coin_size)
                self.coin.shadow_offset_y = self.initial_shadow_offset
                self.final_offset_x_pixels = self.calculate_final_offset(new_coin_size)
                if self.touch_area:
                    touch_area_size = min(0.4, 0.4 * (width / 400))
                    self.touch_area.size_hint = (touch_area_size, touch_area_size)
                    self.touch_area.pos_hint = {'center_x': self.start_pos_x, 'center_y': self.start_pos_y}
                Clock.schedule_once(lambda dt: self.coin._update_rotation(), 0.1)
        if self.back_button:
            btn_size = width * self.BACK_BUTTON_SIZE_COEFF
            self.back_button.size = (btn_size, btn_size)
        self._position_token_widget()

    def check_file(self, path):
        return os.path.exists(path)

    def load_flip_sound(self):
        sound_path = 'assets/sounds/coin/coin_13s.ogg'
        if os.path.exists(sound_path):
            self.flip_sound = SoundLoader.load(sound_path)
            if self.flip_sound:
                self.flip_sound.volume = 0.7

    def load_crystal_sound(self):
        sound_path = 'assets/sounds/coin/crystal.ogg'
        if os.path.exists(sound_path):
            self.crystal_sound = SoundLoader.load(sound_path)
            if self.crystal_sound:
                self.crystal_sound.volume = 1.0

    def play_flip_sound(self):
        if self.sound_manager.is_muted():
            return
        if self.flip_sound:
            try:
                if self.flip_sound.state == 'play':
                    self.flip_sound.stop()
                self.flip_sound.play()
            except:
                pass

    def stop_flip_sound(self):
        if self.flip_sound and self.flip_sound.state == 'play':
            self.flip_sound.stop()

    def play_crystal_sound(self):
        if self.sound_manager.is_muted():
            return
        if self.crystal_sound:
            try:
                if self.crystal_sound.state == 'play':
                    self.crystal_sound.stop()
                self.crystal_sound.play()
            except Exception:
                pass

    def stop_crystal_sound(self):
        if self.crystal_sound and self.crystal_sound.state == 'play':
            self.crystal_sound.stop()

    def setup_game_ui(self):
        self.check_file(self.spritesheet_path_1)
        self.check_file(self.spritesheet_path_2)
        self.check_file(self.final_spritesheet_orel)
        self.check_file(self.final_spritesheet_reshka)
        self.check_file(self.orel_image)
        self.check_file(self.reshka_image)

        screen_width, screen_height = self.get_screen_size()

        self.ellipse_radius_x, self.ellipse_radius_y = self.calculate_ellipse_params()
        self.start_pos_x = self.center_pos_x - self.ellipse_radius_x

        self.coin_height = self.calculate_coin_size()
        self.final_coin_size = self.calculate_final_coin_size(self.coin_height)
        self.initial_shadow_offset = self.calculate_shadow_offset(self.coin_height)
        self.final_offset_x_pixels = self.calculate_final_offset(self.coin_height)

        self.current_side = random.randint(0, 1)

        if self.current_side == 0:
            self.coin_start_side = 0
            self.coin_start_frame = 0
            initial_spritesheet = self.spritesheet_path_1
        else:
            self.coin_start_side = 1
            self.coin_start_frame = 0
            initial_spritesheet = self.spritesheet_path_2

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
            size=(self.coin_height, self.coin_height),
            pos_hint={'center_x': self.start_pos_x, 'center_y': self.start_pos_y},
            allow_stretch=True,
            mipmap=False,
            shadow_offset_x=0,
            shadow_offset_y=self.initial_shadow_offset,
            shadow_scale_y=1.0,
            shadow_alpha=0.5,
            coin_opacity=1.0,
            debug=self.debug_mode
        )

        self.coin.load_spritesheet(initial_spritesheet)
        if self.coin.frames and len(self.coin.frames) > 0:
            self.coin.texture = self.coin.frames[0]
        self.coin.ellipse_offset_x = -self.ellipse_radius_x
        self.coin.ellipse_offset_y = 0
        self.coin.spiral_factor = 1.0
        self.layout.add_widget(self.coin)

        self.final_coin = FinalSpritesheetCoin(
            spritesheet_path=self.final_spritesheet_orel,
            frame_width=128, frame_height=128,
            cols=6, rows=6, total_frames=36,
            start_frame=0,
            size_hint=(None, None),
            size=(self.final_coin_size, self.final_coin_size),
            pos_hint={'center_x': 0.5, 'center_y': 0.5},
            allow_stretch=True,
            mipmap=True,
            shadow_offset_x=0,
            shadow_offset_y=self.initial_shadow_offset,
            shadow_scale_y=1.0,
            shadow_alpha=0.5,
            coin_opacity=1.0,
            opacity=0,
            debug=self.debug_mode
        )
        self.layout.add_widget(self.final_coin)

        self.particle_system = ParticleSystem(num_particles=30)
        self.layout.add_widget(self.particle_system)

        self.fullscreen_touch_area = FullScreenTouchArea()
        self.fullscreen_touch_area.is_enabled = False
        self.layout.add_widget(self.fullscreen_touch_area)

        touch_area_size = min(0.4, 0.4 * (screen_width / 400))
        self.touch_area = TouchArea(
            size_hint=(touch_area_size, touch_area_size),
            pos_hint={'center_x': self.start_pos_x, 'center_y': self.start_pos_y},
        )
        self.layout.add_widget(self.touch_area)

    def create_spiral_animation(self, duration=8.0, rotations=3, direction=1):
        anim = Animation(duration=0)
        steps = 60
        step_duration = duration / steps
        start_angle = math.pi
        end_angle = start_angle + (2 * math.pi * rotations * direction)
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
                duration=step_duration, t='linear'
            )
            anim += step_anim
        return anim

    def _direction_label(self, direction):
        return "ПРОТИВ ЧАСОВОЙ" if direction == 1 else "ПО ЧАСОВОЙ"

    def _on_coin_tap(self):
        if self.is_animating:
            return
        if self.final_coin and self.final_coin.opacity == 1 and not self.final_coin.is_animating:
            self.return_coin_to_start()
            return
        if not self.coin.is_animating and not self.final_coin.is_animating:
            if not self._can_play():
                self._flash_token_widget()
                return
            self.rotation_direction = random.choice([1, -1])
            self.flip_coin()

    def _on_coin_swipe(self, dx, dy):
        if self.is_animating:
            return
        if self.final_coin and self.final_coin.opacity == 1 and not self.final_coin.is_animating:
            self.return_coin_to_start()
            return
        if not self.coin.is_animating and not self.final_coin.is_animating:
            if not self._can_play():
                self._flash_token_widget()
                return
            if dy < 0:
                self.rotation_direction = 1
            elif dy > 0:
                self.rotation_direction = -1
            else:
                self.rotation_direction = random.choice([1, -1])
            self.flip_coin()

    def set_animating_state(self, animating):
        self.is_animating = animating
        if self.touch_area:
            self.touch_area.is_enabled = not animating

    def flip_coin(self):
        if self.coin.is_animating:
            return

        if not self._try_place_bet():
            self._flash_token_widget()
            return

        self._block_debug_overlay_buttons()

        self._show_light_background()
        self.set_animating_state(True)
        if self.fullscreen_touch_area:
            self.fullscreen_touch_area.is_enabled = False
        if self.final_coin:
            self.final_coin.stop_animation()
            self.final_coin.opacity = 0
        self.vibrate_long()
        Clock.schedule_once(lambda dt: self.play_flip_sound(), 0.3)
        if self.particle_system:
            self.particle_system.set_glow_mode(True)
        result = random.randint(0, 1)
        if result == 0:
            spritesheet_to_use = self.spritesheet_path_1
            self.heads_count += 1
        else:
            spritesheet_to_use = self.spritesheet_path_2
            self.tails_count += 1
        self.total_flips += 1
        self.coin.load_spritesheet(spritesheet_to_use)
        self.coin.reset_to_first_animation(0)
        self.coin.shadow_offset_y = self.initial_shadow_offset
        self.current_shadow_offset = self.initial_shadow_offset
        self.coin.ellipse_offset_x = -self.ellipse_radius_x
        self.coin.ellipse_offset_y = 0
        self.coin.spiral_factor = 1.0
        self.coin.extra_offset_x = 0

        base_fps = 50
        base_frame_step = 1
        spiral_duration = 8.0
        center_rotation_duration = 2.0
        rotations = 3

        self.coin.set_animation_range(0, 11)
        self.coin.start_animation(fps=base_fps, frame_step=base_frame_step)

        spiral_anim = self.create_spiral_animation(
            spiral_duration, rotations, direction=self.rotation_direction
        )

        def on_spiral_complete(animation, coin):
            if self.coin is not None and not self.return_animation_active:
                self.start_center_rotation(result, base_fps, base_frame_step,
                                           center_rotation_duration)
        spiral_anim.bind(on_complete=on_spiral_complete)
        spiral_anim.start(self.coin)

    def start_center_rotation(self, result, fps, frame_step, duration):
        if self.coin is None:
            return
        self.coin.spiral_factor = 0
        self.coin.set_animation_range(0, 11)
        self.coin.start_animation(fps=fps, frame_step=frame_step)
        Clock.schedule_once(lambda dt: self.start_final_rotation_with_offset(result, fps, frame_step)
        if self.coin is not None and not self.return_animation_active else None, duration)

    def start_final_rotation_with_offset(self, result, fps, frame_step):
        if self.coin is None:
            return
        self.coin.stop_animation()
        self.coin.set_animation_range(12, 107)
        frames_to_play = 96
        frame_duration = 1.0 / fps
        total_duration = frames_to_play * frame_duration
        self.coin.current_frame = 12
        self.coin.texture = self.coin.frames[12]

        offset_anim = Animation(
            extra_offset_x=self.final_offset_x_pixels,
            duration=total_duration, t='linear'
        )
        target_shadow_offset = self.initial_shadow_offset * 0.1
        shadow_anim = Animation(
            shadow_offset_y=target_shadow_offset,
            duration=total_duration, t='linear'
        )
        self.coin.is_animating = True

        vibration_interval = 0.1
        vibration_duration_ms = 50
        self.vibration_event = Clock.schedule_interval(
            lambda dt: self.vibrate_custom(vibration_duration_ms),
            vibration_interval
        )
        Clock.schedule_once(lambda dt: self.stop_vibration(), total_duration)

        def update_frame(dt):
            if not self.coin.is_animating or self.coin is None:
                return False
            next_frame = self.coin.current_frame + 1
            if next_frame > 107:
                self.coin.is_animating = False
                self.finish_rotation(result)
                return False
            self.coin.current_frame = next_frame
            self.coin.texture = self.coin.frames[next_frame]
            self.coin._update_rotation()
            return True

        frame_interval = 1.0 / fps
        Clock.schedule_interval(update_frame, frame_interval)
        offset_anim.start(self.coin)
        shadow_anim.start(self.coin)
        Clock.schedule_once(lambda dt: self.finish_rotation(result)
        if self.coin is not None and self.coin.is_animating else None, total_duration + 0.1)

    def stop_vibration(self):
        if hasattr(self, 'vibration_event') and self.vibration_event:
            self.vibration_event.cancel()
            self.vibration_event = None

    def finish_rotation(self, result):
        if self.coin is None:
            return
        if self.coin:
            self.coin.stop_animation()
        pause_duration = 0.5
        self.vibration_event_pause = Clock.schedule_interval(
            lambda dt: self.vibrate_short(), 0.1
        )
        Clock.schedule_once(lambda dt: self.stop_pause_vibration(), pause_duration)
        Clock.schedule_once(lambda dt: self.start_final_animation(result)
        if self.coin is not None and not self.return_animation_active else None, pause_duration)

    def stop_pause_vibration(self):
        if hasattr(self, 'vibration_event_pause') and self.vibration_event_pause:
            self.vibration_event_pause.cancel()
            self.vibration_event_pause = None

    def start_final_animation(self, result):
        if self.final_coin is None:
            return
        if self.coin:
            self.coin.opacity = 0
        if result == 0:
            final_spritesheet = self.final_spritesheet_orel
        else:
            final_spritesheet = self.final_spritesheet_reshka
        self.final_coin.load_spritesheet(final_spritesheet)
        self.final_coin.opacity = 1
        self.final_coin.size = (self.coin_height, self.coin_height)
        self.final_coin.pos_hint = {'center_x': self.center_pos_x, 'center_y': self.center_pos_y}
        self.final_coin.shadow_offset_x = 0
        self.final_coin.shadow_offset_y = self.initial_shadow_offset
        self.final_coin.shadow_scale_y = 1.0
        self.final_coin.shadow_alpha = 0.5
        self.final_coin.coin_opacity = 1.0
        self.final_coin.pos = self.final_coin.pos
        self.final_coin.size = self.final_coin.size

        animation_duration = 1.5
        target_size = self.final_coin_size
        frame_fps = 36 / animation_duration
        self.final_coin.start_animation(fps=frame_fps, loop=False)

        grow_anim = Animation(
            size=(target_size, target_size),
            pos_hint={'center_x': 0.5, 'center_y': 0.5},
            duration=animation_duration, t='linear'
        )
        shadow_move_anim = Animation(
            shadow_offset_y=-self.coin_height * 15,
            shadow_alpha=0.5,
            duration=animation_duration, t='linear'
        )

        def on_grow_complete(animation, coin):
            self.play_crystal_sound()
            self.vibrate_custom(200)
            if self.particle_system:
                self.particle_system.set_glow_mode(False)
            self._finalize_light_background()
            self.set_animating_state(False)
            if self.fullscreen_touch_area:
                self.fullscreen_touch_area.is_enabled = True
            self._apply_bet_result(result)
            self._unblock_debug_overlay_buttons()

        grow_anim.bind(on_complete=on_grow_complete)
        grow_anim.start(self.final_coin)
        shadow_move_anim.start(self.final_coin)
        self.stop_flip_sound()
        self.current_side = result

    def return_coin_to_start(self):
        self.set_animating_state(True)
        if self.fullscreen_touch_area:
            self.fullscreen_touch_area.is_enabled = False
        self.return_animation_active = True
        self.stop_crystal_sound()
        self._show_dark_background()
        if self.final_coin:
            self.final_coin.stop_animation()
            self.final_coin.opacity = 0
        if self.coin:
            self.coin.opacity = 1
            if self.current_side == 0:
                self.coin.load_spritesheet(self.spritesheet_path_1)
            else:
                self.coin.load_spritesheet(self.spritesheet_path_2)
            if self.coin.frames and len(self.coin.frames) > 0:
                self.coin.texture = self.coin.frames[0]
            self.coin.shadow_offset_x = 0
            self.coin.shadow_offset_y = -Window.height
            self.coin.shadow_scale_y = 1.0
            self.coin.shadow_alpha = 0.5
            self.coin.pos_hint = {'center_x': 0.5, 'center_y': 0.5}
            self.coin.size = (self.final_coin_size, self.final_coin_size)

        return_anim = Animation(
            size=(self.coin_height, self.coin_height),
            pos_hint={'center_x': self.start_pos_x, 'center_y': self.start_pos_y},
            duration=1.2, t='out_quad'
        )
        shadow_return_anim = Animation(
            shadow_offset_y=self.initial_shadow_offset,
            shadow_offset_x=0,
            duration=1.2, t='out_quad'
        )

        def on_return_complete(animation, coin):
            self.return_animation_active = False
            self.set_animating_state(False)
            self._unblock_debug_overlay_buttons()

        return_anim.bind(on_complete=on_return_complete)
        return_anim.start(self.coin)
        shadow_return_anim.start(self.coin)

    # ==================== КНОПКА НАЗАД (переопределение) ====================

    def create_custom_back_button(self):
        """Своя кнопка «Назад» с источником Orange_back_to_menu_button_90.png
        и своими коэффициентами размера/позиции.

        Координаты кнопки задаются константами:
            BACK_BUTTON_SIZE_COEFF — размер (доля от ширины экрана)
            BACK_BUTTON_POS_X_COEFF — X (доля от ширины экрана)
            BACK_BUTTON_POS_Y_COEFF — Y (доля от высоты экрана)
            BACK_BUTTON_SOURCE      — путь к PNG
            BACK_BUTTON_ROTATION    — дополнительный поворот (в градусах)
        """
        screen_width = self.get_screen_width()
        screen_height = self.get_screen_height()
        btn_size = screen_width * self.BACK_BUTTON_SIZE_COEFF

        class ImageButton(ButtonBehavior, KivyImage):
            pass

        back_btn = ImageButton(
            source=self.BACK_BUTTON_SOURCE,
            size_hint=(None, None),
            size=(btn_size, btn_size),
            pos_hint={
                'x': self.BACK_BUTTON_POS_X_COEFF,
                'y': self.BACK_BUTTON_POS_Y_COEFF
            },
            allow_stretch=True,
            mipmap=True,
        )

        # Если задан BACK_BUTTON_ROTATION != 0 — поворачиваем через Rotate
        if self.BACK_BUTTON_ROTATION:
            from kivy.graphics import PushMatrix, PopMatrix, Rotate, Translate
            self._btn_rotate = None
            with back_btn.canvas.before:
                PushMatrix()
                self._btn_rotate = Rotate(
                    angle=self.BACK_BUTTON_ROTATION,
                    origin=back_btn.center
                )
            with back_btn.canvas.after:
                PopMatrix()

            def _update_btn_rotate(*args):
                if self._btn_rotate:
                    self._btn_rotate.origin = back_btn.center

            back_btn.bind(pos=_update_btn_rotate, size=_update_btn_rotate)

        def on_press(instance):
            Animation(opacity=0.7, duration=0.1).start(instance)

        def on_release(instance):
            Animation(opacity=1.0, duration=0.1).start(instance)
            self.play_back_sound()
            Clock.schedule_once(lambda dt: self.go_to_menu(), 0.1)

        back_btn.bind(on_press=on_press)
        back_btn.bind(on_release=on_release)

        self.back_button = back_btn
        self.layout.add_widget(back_btn)

    def create_back_button(self):
        """Переопределяем родительский метод, чтобы использовался
        именно наш create_custom_back_button (с _90.png и своими
        коэффициентами)."""
        if self.back_button and self.back_button in self.layout.children:
            self.layout.remove_widget(self.back_button)
            self.back_button = None
        self.create_custom_back_button()

    # =====================================================================

    def go_to_menu(self):
        self.cleanup_all()
        from main import switch_screen
        switch_screen('menu')