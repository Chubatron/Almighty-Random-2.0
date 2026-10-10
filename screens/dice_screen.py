"""
Dice Screen - экран с кубиками из спрайт-листа
"""
import os
import random
import math
import inspect
from kivy.app import App
from kivy.uix.image import Image
from kivy.uix.widget import Widget
from kivy.graphics import Color, Rectangle, Ellipse, Rotate, PushMatrix, PopMatrix
from kivy.properties import StringProperty, NumericProperty
from kivy.clock import Clock
from kivy.animation import Animation
from kivy.core.window import Window
from kivy.utils import platform
from kivy.core.audio import SoundLoader
from kivy.uix.behaviors import ButtonBehavior
from kivy.uix.image import Image as KivyImage

from screens.base_game_screen import BaseGameScreen
from screens.dice import (
    DropZone, PointMarker, DiceWidget, GlassWidget, ShadowWidget
)
from screens.dice.magnetic_field import MagneticField
from screens.dice.particle_effects import ParticleSystem

from components.token_widget import TokenWidget
from lucky_token import LuckyToken

# ===== НАСТРОЙКИ ОТЛАДКИ =====
DEBUG_MODE = False
# =============================


class RotatedTokenWidget(TokenWidget):
    """TokenWidget с поворотом вокруг центра."""

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


class DiceScreen(BaseGameScreen):
    """Экран с кубиками на столе и стаканом рядом"""

    BACK_BUTTON_SIZE_COEFF = 0.12
    BACK_BUTTON_POS_X_COEFF = 0.05
    BACK_BUTTON_POS_Y_COEFF = 0.91

    TOKEN_SIZE_COEFF = 0.18
    TOKEN_POS_X_COEFF = 0.85
    TOKEN_POS_Y_COEFF = 0.45

    BET_AMOUNT = 1
    WIN_PAYOUT = 2

    # ===== РЕЖИМ 1 КУБИК: награды за значения =====
    SINGLE_PAYOUTS = {
        5: 2,
        6: 3,
    }

    # ===== РЕЖИМ 2 КУБИКА =====
    DOUBLE_SUM_PAYOUTS = {
        9: 2,
        10: 2,
        11: 2,
        12: 2,
    }
    DOUBLE_PAYOUTS = {
        1: 2,
        2: 2,
        3: 3,
        4: 3,
        5: 4,
        6: 4,
    }

    # ✅ Звук отказа (когда нет жетонов)
    reject_sound_path = StringProperty('assets/sounds/reject.mp3')

    # ✅ Звук награды (бонус)
    bonus_sound_path = StringProperty('assets/sounds/bonus.mp3')

    # ✅ Задержка между воспроизведениями bonus (по одному за каждый жетон)
    BONUS_STAGGER_DELAY = 0.35

    background_image = StringProperty('assets/backgrounds/dice_bg_dark.png')
    background_bright_image = StringProperty('assets/backgrounds/dice_bg.png')
    sprite_sheet_path = StringProperty('assets/sprites/spritesheet_cube.png')
    enlarge_sprite_sheet_path = StringProperty('assets/sprites/spritesheet_cube_changed.png')
    glass_sprite_sheet_path = StringProperty('assets/sprites/spritesheet_glass12.png')
    shadow_sprite_sheet_path = StringProperty('assets/sprites/spritesheet_shadow.png')

    shadow_scale_factor = NumericProperty(2.6)
    shadow_rotation = NumericProperty(-90)
    shadow_offset_x_factor = NumericProperty(-1.25)
    shadow_offset_y_factor = NumericProperty(-0.35)
    shadow_opacity = NumericProperty(0.7)
    shadow_move_factor_x = NumericProperty(-1.0)
    shadow_move_factor_y = NumericProperty(0.0)

    ANIMATION_DURATION = 1.5
    FIRST_ANIMATION_DURATION = 1
    SECOND_ANIMATION_DURATION = 1

    BRIGHTNESS_CHARGE_RATE = 0.001
    BRIGHTNESS_DRAIN_RATE = 0.25
    MAX_BRIGHTNESS = 1.0
    MIN_BRIGHTNESS = 0.0

    SOUND_DELAY = 0.15

    MAGNETIC_DISTANCE_X_FACTOR = 0.7
    MAGNETIC_DISTANCE_Y_FACTOR = 0.9
    MAGNETIC_FORCE_FACTOR = 0.8

    TOKEN_ROTATION_ANGLE = -90

    # ✅ Поворот ЛЕТЯЩЕЙ МОНЕТКИ-НАГРАДЫ на 90°
    reward_rotation = -90

    DICE_ROWS = 6
    DICE_COLS = 24
    DICE_ROW_TO_VALUE = (1, 2, 3, 4, 5, 6)

    DICE_MOVE_SOUND_PATHS = [
        'assets/sounds/dice/1.ogg',
        'assets/sounds/dice/2.ogg',
        'assets/sounds/dice/3.ogg',
        'assets/sounds/dice/4.ogg',
        'assets/sounds/dice/5.ogg',
    ]

    DICE_MOVE_MAX_VOLUME = 1.0
    DICE_MOVE_DEBUG = False

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self.disappear_duration = 0.3
        self.appear_duration = 0.3
        self.overlap_time = 0.2

        self.single_dice_size = 0
        self.double_dice_size = 0
        self.large_dice_size = 0
        self.glass_size = 0
        self.shadow_size = 0

        self.START_POSITION_DICE_X = 0
        self.START_POSITION_DICE_Y = 0
        self.START_POSITION_GLASS_X = 0
        self.START_POSITION_GLASS_Y = 0
        self.SHADOW_POSITION_X = 0
        self.SHADOW_POSITION_Y = 0
        self.SHADOW_TARGET_POSITION_X = 0
        self.SHADOW_TARGET_POSITION_Y = 0

        self.dice_list = []
        self.glass = None
        self.shadow = None
        self.drop_zone = None
        self.point_a_marker = None
        self.current_mode = 1
        self.bg_dark = None
        self.bg_bright = None
        self.is_animating = False
        self.animation_counter = 0
        self.dice_hidden = False
        self.pending_hide_dice = False

        self.glass_start_pos = None
        self.glass_target_pos = None
        self.is_at_target = True

        self.last_dice_center = None
        self.saved_point_a_position = None
        self.saved_dice_positions = []

        self.last_touch_pos = None
        self.last_touch_time = None
        self.max_speed = 0
        self.has_moved_with_dice = False

        self.total_distance_traveled = 0.0
        self.current_brightness = 0.0
        self.drain_clock = None
        self.is_charging = False
        self.is_draining_scheduled = False
        self._reset_charge_clock = None

        self.sound_glass_lower = None
        self.sound_glass_raise = None
        self.sound_dice_roll = None
        self.sound_glass_drag = None
        self.sound_dice_appear = None
        self.sound_dice_disappear = None

        # ✅ Звук отказа
        self.reject_sound = None

        # ✅ Звук награды (бонус)
        self.bonus_sound = None

        # ✅ Звуки движения кубиков — плейлист
        self.dice_move_sounds = []
        self._dice_move_index = 0
        self._dice_move_playing = False
        self._dice_move_current = None
        self._dice_move_clock = None
        self._dice_move_target_volume = 0.0
        self._dice_move_current_volume = 0.0

        self.volume_fade_clock = None
        self.target_volume = 0.0

        self._last_drag_time = 0.0
        self._glass_drag_silence_clock = None

        self._reward_start_queue = []
        self._current_start_hint = None

        self.is_dice_enlarged = False
        self.is_glass_blocked = False
        self.is_dice_blocked = False

        self._drop_zone_visualization = None
        self.magnetic_field = None
        self.particle_system = None

        self.frame_change_threshold = 40.0
        self.contact_monitor = None
        self.dice_contact_flags = {}
        self.dice_frame_accumulators = {}

        self.tokens = LuckyToken()
        self.token_widget = None

        self._bet_placed_this_round = False
        self._no_tokens_flash_shown = False
        self._last_result = None

        # ✅ Очередь воспроизведения bonus_sound (для последовательного проигрывания)
        self._bonus_queue = 0
        self._bonus_clock = None

        # ✅ Отладка анимации вращения кубиков
        self.ANIM_DEBUG = True

        self._load_reject_sound()
        self._load_bonus_sound()

    def get_screen_size(self):
        if platform == 'android':
            width, height = Window.system_size
        else:
            width = Window.width
            height = Window.height
        return width, height

    # ==================== НАГРАДА: ПОВОРОТ ЛЕТЯЩЕЙ МОНЕТКИ ====================

    def _build_reward_image(self, size, pos_hint):
        """
        Переопределяем базовый метод ТОЛЬКО для этого экрана.
        Летящая монетка-награда поворачивается на reward_rotation вокруг центра.
        """
        if isinstance(size, (list, tuple)):
            img_size = tuple(size)
        else:
            img_size = (size, size)

        img = KivyImage(
            source=self.reward_source,
            size_hint=(None, None),
            size=img_size,
            pos_hint=dict(pos_hint),
            allow_stretch=True,
            keep_ratio=True,
            mipmap=True,
            opacity=0,
        )

        # ✅ Rotate вокруг центра самой картинки-награды
        with img.canvas.before:
            PushMatrix()
            rotate_gfx = Rotate(angle=self.reward_rotation, origin=img.center)

        with img.canvas.after:
            PopMatrix()

        def _update_rotate_origin(*args):
            rotate_gfx.origin = (img.center_x, img.center_y)

        img.bind(pos=_update_rotate_origin, size=_update_rotate_origin)

        def _on_rotation_change(instance, value):
            rotate_gfx.angle = value

        self.bind(reward_rotation=_on_rotation_change)

        img._rotate_gfx = rotate_gfx
        return img

    # =========================================================================

    # ==================== НАГРАДА: ЯКОРЯ ====================

    def _get_real_layout_size(self):
        if self.layout and self.layout.width > 1 and self.layout.height > 1:
            return self.layout.width, self.layout.height
        return Window.width, Window.height

    def _dice_center_hint(self, dice):
        layout_w, layout_h = self._get_real_layout_size()
        cx = dice.center_x / layout_w if layout_w > 0 else 0.5
        cy = dice.center_y / layout_h if layout_h > 0 else 0.5
        return {'center_x': cx, 'center_y': cy}

    def _build_reward_start_points(self, amount):
        if not self.dice_list:
            base = {'center_x': 0.5, 'center_y': 0.5}
            return [dict(base) for _ in range(amount)]

        if len(self.dice_list) == 1:
            base = self._dice_center_hint(self.dice_list[0])
            return [dict(base) for _ in range(amount)]

        hint_a = self._dice_center_hint(self.dice_list[0])
        hint_b = self._dice_center_hint(self.dice_list[1])

        points = []
        i = 0
        while len(points) < amount:
            points.append(dict(hint_a) if i % 2 == 0 else dict(hint_b))
            i += 1

        random.shuffle(points)
        return points

    def get_reward_start_hint(self):
        if self._current_start_hint is not None:
            return dict(self._current_start_hint)
        if self.dice_list:
            return self._dice_center_hint(self.dice_list[0])
        return {'center_x': 0.5, 'center_y': 0.5}

    def get_reward_target_hint(self):
        layout_w, layout_h = self._get_real_layout_size()

        if self.token_widget and self.token_widget.parent:
            return {
                'center_x': self.token_widget.center_x / layout_w,
                'center_y': self.token_widget.center_y / layout_h,
            }

        return {
            'center_x': self.TOKEN_POS_X_COEFF,
            'center_y': self.TOKEN_POS_Y_COEFF,
        }

    def on_reward_arrived(self):
        """Пульс жетона, когда монетка долетела. Без звука."""
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
            print(f"⚠️ [DiceScreen] on_reward_arrived: {e}")

    def _create_single_reward(self):
        if self._reward_start_queue:
            self._current_start_hint = self._reward_start_queue.pop(0)
        else:
            self._current_start_hint = None
        return super()._create_single_reward()

    def show_reward(self, amount=1):
        try:
            amount = int(amount)
        except Exception:
            amount = 1
        if amount < 1:
            amount = 1

        self._reward_start_queue = self._build_reward_start_points(amount)
        self._current_start_hint = None

        super().show_reward(amount=amount)

    # ======================================================

    # ==================== ЗВУКИ ====================

    def _load_reject_sound(self):
        if os.path.exists(self.reject_sound_path):
            self.reject_sound = SoundLoader.load(self.reject_sound_path)
            if self.reject_sound:
                self.reject_sound.volume = 0.8

    def _load_bonus_sound(self):
        if os.path.exists(self.bonus_sound_path):
            self.bonus_sound = SoundLoader.load(self.bonus_sound_path)
            if self.bonus_sound:
                self.bonus_sound.volume = 0.9

    def _play_reject_sound(self):
        """Звук отказа — только когда нет жетонов."""
        if self.sound_manager.is_muted():
            return
        if self.reject_sound:
            try:
                if self.reject_sound.state == 'play':
                    self.reject_sound.stop()
                self.reject_sound.play()
            except Exception:
                pass

    def _play_bonus_sound(self):
        """Один раз проигрывает bonus5.mp3."""
        if self.ANIM_DEBUG:
            print(f"🔊 [BONUS] играем bonus5.mp3 (осталось в очереди: {self._bonus_queue})")
        if self.sound_manager.is_muted():
            return
        if self.bonus_sound:
            try:
                if self.bonus_sound.state == 'play':
                    self.bonus_sound.stop()
                self.bonus_sound.play()
            except Exception:
                pass

    # ✅ Планирует N воспроизведений bonus5.mp3 с задержкой между ними
    def _schedule_bonus_sounds(self, count):
        if count <= 0:
            return
        if self.ANIM_DEBUG:
            print(f"🔊 [BONUS] планирую {count} воспроизведений bonus5.mp3")
        self._bonus_queue = count

        # отменяем предыдущий таймер, если был
        if self._bonus_clock:
            self._bonus_clock.cancel()
            self._bonus_clock = None

        def _tick(dt):
            if self._bonus_queue <= 0:
                self._bonus_clock = None
                return
            self._bonus_queue -= 1
            self._play_bonus_sound()
            if self._bonus_queue > 0:
                self._bonus_clock = Clock.schedule_once(_tick, self.BONUS_STAGGER_DELAY)
            else:
                self._bonus_clock = None

        # стартуем без задержки — первый звук играет сразу
        self._bonus_clock = Clock.schedule_once(_tick, 0.0)

    # ======================================================

    # ==================== ЛОГИКА ИГРЫ: СТАВКИ ====================

    def _can_play(self):
        if self._bet_placed_this_round:
            return True
        return self.tokens.get_balance() >= self.BET_AMOUNT

    def _try_place_bet(self):
        if self._bet_placed_this_round:
            return True

        if self.tokens.get_balance() < self.BET_AMOUNT:
            if not self._no_tokens_flash_shown:
                self._flash_token_widget(with_reject_sound=True)
                self._no_tokens_flash_shown = True
            return False

        ok = self.tokens.spend(self.BET_AMOUNT, reason="dice_bet")
        if not ok:
            self._flash_token_widget(with_reject_sound=True)
            return False

        self._bet_placed_this_round = True
        return True

    def _refund_bet_if_needed(self):
        if not self._bet_placed_this_round:
            return

        self.tokens.add(self.BET_AMOUNT, reason="dice_bet_refund")
        self._bet_placed_this_round = False
        self._no_tokens_flash_shown = False

    def _reset_bet_flag(self):
        self._bet_placed_this_round = False
        self._no_tokens_flash_shown = False

    # ==================== ЛОГИКА ИГРЫ: РЕЗУЛЬТАТ ====================

    def _frame_to_value(self, frame_index):
        if frame_index is None:
            return None
        total_frames = self.DICE_ROWS * self.DICE_COLS
        if total_frames <= 0:
            return None
        frame_index = frame_index % total_frames
        row = frame_index // self.DICE_COLS
        if 0 <= row < len(self.DICE_ROW_TO_VALUE):
            return self.DICE_ROW_TO_VALUE[row]
        return None

    def _get_dice_result_value(self, dice):
        try:
            frame = getattr(dice, 'frame_index', None)
            return self._frame_to_value(frame)
        except Exception:
            return None

    def _evaluate_result(self):
        result = {
            'win': False,
            'payout': 0,
            'mode': self.current_mode,
            'values': [],
            'sum': 0,
            'reason': '',
        }

        values = []
        for dice in self.dice_list:
            v = self._get_dice_result_value(dice)
            if v is not None:
                values.append(v)

        result['values'] = values
        if not values:
            result['reason'] = 'no_values'
            return result

        # ===== РЕЖИМ 1 КУБИК =====
        if self.current_mode == 1:
            v = values[0]
            result['sum'] = v
            if v in self.SINGLE_PAYOUTS:
                result['win'] = True
                result['payout'] = self.SINGLE_PAYOUTS[v]
                result['reason'] = f'single {v} -> payout {result["payout"]}'
            else:
                result['reason'] = f'single {v} -> no win'
            return result

        # ===== РЕЖИМ 2 КУБИКА =====
        if len(values) < 2:
            result['reason'] = 'double mode but <2 dice'
            return result

        v1, v2 = values[0], values[1]
        total = v1 + v2
        result['sum'] = total
        is_double = (v1 == v2)

        # ✅ СНАЧАЛА проверяем дубль
        if is_double:
            payout = self.DOUBLE_PAYOUTS.get(v1, 0)
            if payout > 0:
                result['win'] = True
                result['payout'] = payout
                result['reason'] = (f'double {v1}+{v2} = {total} '
                                    f'(duplicate) -> payout {payout}')
            else:
                result['reason'] = f'double {v1}+{v2} = {total} (no payout)'
            return result

        # ✅ Только если НЕ дубль — проверяем сумму
        if total in self.DOUBLE_SUM_PAYOUTS:
            result['win'] = True
            result['payout'] = self.DOUBLE_SUM_PAYOUTS[total]
            result['reason'] = f'sum {total} -> payout {result["payout"]}'
        else:
            result['reason'] = f'sum {total} -> no win'

        return result

    def _apply_bet_result(self):
        result = self._evaluate_result()
        self._last_result = result

        if result['win'] and result['payout'] > 0:
            self.tokens.add(result['payout'], reason="dice_win")
            self._flash_token_widget(with_reject_sound=False)
            self.play_reward(amount=result['payout'])

            # ✅ bonus5.mp3 — ровно payout раз (по одному за каждый жетон)
            self._schedule_bonus_sounds(result['payout'])

        self._reset_bet_flag()
        return result

    # ==================== ЖЕТОН ====================

    def _create_token_widget(self):
        if self.token_widget and self.token_widget.parent:
            return

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
        Window.bind(on_resize=self._on_window_resize)

    def _position_token_widget(self):
        if not self.token_widget:
            return
        self.token_widget.size_hint = (None, None)
        self.token_widget.pos_hint = {}
        screen_width, screen_height = self.get_screen_size()
        size = screen_width * self.TOKEN_SIZE_COEFF
        self.token_widget.size = (size, size)
        self.token_widget.pos = (
            screen_width * self.TOKEN_POS_X_COEFF,
            screen_height * self.TOKEN_POS_Y_COEFF,
        )

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

    def _flash_token_widget(self, with_reject_sound=False):
        if not self.token_widget:
            return
        label = self.token_widget.value_label
        if not label:
            return

        if with_reject_sound:
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

    # ==================== КНОПКА BACK ====================

    def create_back_button(self):
        if self.back_button and self.back_button in self.layout.children:
            self.layout.remove_widget(self.back_button)
            self.back_button = None
        self.create_custom_back_button()

    def create_custom_back_button(self):
        screen_width = self.get_screen_width()
        btn_size = screen_width * self.BACK_BUTTON_SIZE_COEFF

        class ImageButton(ButtonBehavior, KivyImage):
            pass

        back_btn = ImageButton(
            source='assets/images/buttons/Orange_back_to_menu_button_90.png',
            size_hint=(None, None),
            size=(btn_size, btn_size),
            pos_hint={
                'x': self.BACK_BUTTON_POS_X_COEFF,
                'y': self.BACK_BUTTON_POS_Y_COEFF
            },
            allow_stretch=True
        )

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

    def _print_widget_order(self, event_name=""):
        if not DEBUG_MODE:
            return
        print(f"\n📊 [Z-ORDER] {event_name}")
        for i, child in enumerate(reversed(self.layout.children)):
            name = child.__class__.__name__
            if "DiceWidget" in name:
                widget_type = "🎲 КУБИК"
            elif "GlassWidget" in name:
                widget_type = "🥛 СТАКАН"
            elif "ShadowWidget" in name:
                widget_type = "🌑 ТЕНЬ"
            elif "DropZone" in name:
                widget_type = "🔵 ЗОНА"
            elif "PointMarker" in name:
                widget_type = "🔴 ТОЧКА_А"
            elif "Image" in name and "bg" in str(child.source).lower():
                widget_type = "🖼️ ФОН"
            elif "ParticleSystem" in name:
                widget_type = "✨ ЧАСТИЦЫ"
            elif "RotatedTokenWidget" in name or "TokenWidget" in name:
                widget_type = "🎟️ ЖЕТОН"
            elif "ImageButton" in name or "ButtonBehavior" in str(child.__class__):
                widget_type = "🔙 КНОПКА"
            else:
                widget_type = "❓ ДРУГОЕ"
            print(f"   {i}: {widget_type} - {name}")

    def _is_dice_above_glass(self, dice):
        if not self.glass or not dice:
            return False
        glass_index = self.layout.children.index(self.glass) if self.glass in self.layout.children else -1
        dice_index = self.layout.children.index(dice) if dice in self.layout.children else -1
        return dice_index > glass_index

    def _ensure_dice_above_glass_for_animation(self):
        if not self.glass or not self.dice_list:
            return
        glass_center_x = self.glass.pos[0] + self.glass.width / 2
        for dice in self.dice_list:
            dice_center_x = dice.pos[0] + dice.width / 2
            if dice_center_x < glass_center_x:
                if dice.parent:
                    dice.parent.remove_widget(dice)
                self.layout.add_widget(dice)
        if self.glass and self.glass.parent:
            self.glass.parent.remove_widget(self.glass)
            self.layout.add_widget(self.glass)

    def _ensure_glass_on_top_during_lowering(self):
        if self.glass and self.glass.parent:
            self.glass.parent.remove_widget(self.glass)
        if self.glass:
            self.layout.add_widget(self.glass)
        if self.shadow and self.shadow.parent:
            self.shadow.parent.remove_widget(self.shadow)
        if self.shadow:
            self.layout.add_widget(self.shadow)

    def _update_dice_z_order(self):
        if not self.glass or not self.dice_list:
            return

        if not self.is_at_target:
            if self.glass.parent:
                self.glass.parent.remove_widget(self.glass)
            for dice in self.dice_list:
                if dice.parent:
                    dice.parent.remove_widget(dice)
            self.layout.add_widget(self.glass)
            for dice in self.dice_list:
                self.layout.add_widget(dice)
            return

        if self.dice_hidden:
            for dice in self.dice_list:
                if dice.parent:
                    dice.parent.remove_widget(dice)
            for dice in self.dice_list:
                self.layout.add_widget(dice, index=0)
            if self.glass.parent:
                self.glass.parent.remove_widget(self.glass)
            self.layout.add_widget(self.glass)
            return

        point_a_x = self._get_current_point_a_position()[0]
        above_glass = []
        below_glass = []

        for dice in self.dice_list:
            dice_center_x = dice.pos[0] + dice.width / 2
            if dice_center_x < point_a_x:
                above_glass.append(dice)
            else:
                below_glass.append(dice)

        if self.glass.parent:
            self.glass.parent.remove_widget(self.glass)
        for dice in self.dice_list:
            if dice.parent:
                dice.parent.remove_widget(dice)

        for dice in below_glass:
            self.layout.add_widget(dice)
        if self.glass:
            self.layout.add_widget(self.glass)
        for dice in above_glass:
            self.layout.add_widget(dice)

    def _get_center_positions(self):
        screen_width, screen_height = self.get_screen_size()
        center_x = screen_width / 2
        pos1_y = screen_height * 0.33
        pos2_y = screen_height * 0.5
        pos3_y = screen_height * 0.66
        return {
            'pos1': (center_x, pos1_y),
            'pos2': (center_x, pos2_y),
            'pos3': (center_x, pos3_y)
        }

    def _get_dice_target_position(self, dice, mode='grow'):
        positions = self._get_center_positions()
        if mode == 'grow':
            if len(self.dice_list) == 1:
                target_x = positions['pos2'][0] - dice.width / 2
                target_y = positions['pos2'][1] - dice.height / 2
                return (target_x, target_y)
            else:
                index = self.dice_list.index(dice) if dice in self.dice_list else 0
                if index == 0:
                    target_x = positions['pos1'][0] - dice.width / 2
                    target_y = positions['pos1'][1] - dice.height / 2
                else:
                    target_x = positions['pos3'][0] - dice.width / 2
                    target_y = positions['pos3'][1] - dice.height / 2
                return (target_x, target_y)
        else:
            if hasattr(dice, 'original_position') and dice.original_position:
                return dice.original_position
            return (self.START_POSITION_DICE_X, dice.pos[1] if len(self.dice_list) > 1 else self.START_POSITION_DICE_Y)

    def _get_dice_original_positions(self):
        positions = {}
        if len(self.dice_list) == 1:
            positions[0] = (self.START_POSITION_DICE_X, self.START_POSITION_DICE_Y)
        else:
            distance_between = self.double_dice_size * 0.3
            center_y = self.START_POSITION_DICE_Y + (self.single_dice_size // 2) - (self.double_dice_size // 2)
            y_top = center_y - distance_between
            y_bottom = center_y + distance_between
            positions[0] = (self.START_POSITION_DICE_X, y_top)
            positions[1] = (self.START_POSITION_DICE_X, y_bottom)
        return positions

    def _load_dice_sounds(self):
        try:
            if os.path.exists('assets/sounds/dice/glass_lower.mp3'):
                self.sound_glass_lower = SoundLoader.load('assets/sounds/dice/glass_lower.mp3')
            if os.path.exists('assets/sounds/dice/glass_raise.mp3'):
                self.sound_glass_raise = SoundLoader.load('assets/sounds/dice/glass_raise.mp3')
            if os.path.exists('assets/sounds/dice/dice_roll.mp3'):
                self.sound_dice_roll = SoundLoader.load('assets/sounds/dice/dice_roll.mp3')
            if os.path.exists('assets/sounds/dice/glass_drag.mp3'):
                self.sound_glass_drag = SoundLoader.load('assets/sounds/dice/glass_drag.mp3')
                if self.sound_glass_drag:
                    self.sound_glass_drag.loop = True
                    self.sound_glass_drag.volume = 0.0
                    self.sound_glass_drag.play()
            if os.path.exists('assets/sounds/dice/dice_appear.mp3'):
                self.sound_dice_appear = SoundLoader.load('assets/sounds/dice/dice_appear.mp3')
            if os.path.exists('assets/sounds/dice/dice_disappear.mp3'):
                self.sound_dice_disappear = SoundLoader.load('assets/sounds/dice/dice_disappear.mp3')

            self.dice_move_sounds = []
            for path in self.DICE_MOVE_SOUND_PATHS:
                if os.path.exists(path):
                    snd = SoundLoader.load(path)
                    if snd:
                        snd.volume = 0.0
                        self.dice_move_sounds.append(snd)
                else:
                    print(f"⚠️ Не найден звук движения: {path}")
            print(f"📦 [DICE MOVE] Загружено звуков: {len(self.dice_move_sounds)}")
        except Exception as e:
            print(f"Ошибка загрузки звуков кубиков: {e}")

    # ==================== ПЛЕЙЛИСТ ДВИЖЕНИЯ КУБИКОВ ====================

    def _start_dice_move_playlist(self):
        if self.sound_manager.is_muted():
            return
        if not self.dice_move_sounds:
            return
        if self._dice_move_playing:
            return
        self._dice_move_index = 0
        self._dice_move_current_volume = 0.0
        self._dice_move_target_volume = 0.0
        self._dice_move_playing = True
        self._play_next_dice_move_sound()

    def _play_next_dice_move_sound(self):
        if not self._dice_move_playing:
            return
        if self.sound_manager.is_muted():
            self._stop_dice_move_playlist()
            return
        if not self.dice_move_sounds:
            self._dice_move_playing = False
            return

        snd = self.dice_move_sounds[self._dice_move_index]
        self._dice_move_index = (self._dice_move_index + 1) % len(self.dice_move_sounds)
        self._dice_move_current = snd

        try:
            snd.volume = self._dice_move_current_volume
            snd.play()
            if self._dice_move_clock:
                self._dice_move_clock.cancel()
            self._dice_move_clock = Clock.schedule_once(
                lambda dt: self._check_dice_move_playlist(), 0.05)
        except Exception as e:
            print(f"❌ [DICE MOVE PLAYLIST] Ошибка play: {e}")
            self._dice_move_playing = False
            self._dice_move_current = None

    def _check_dice_move_playlist(self):
        if not self._dice_move_playing:
            return
        if self.sound_manager.is_muted():
            self._stop_dice_move_playlist()
            return
        snd = self._dice_move_current
        try:
            if snd is not None and snd.state == 'play':
                self._dice_move_clock = Clock.schedule_once(
                    lambda dt: self._check_dice_move_playlist(), 0.05)
            else:
                self._play_next_dice_move_sound()
        except Exception as e:
            print(f"❌ [DICE MOVE PLAYLIST] Ошибка check: {e}")
            self._play_next_dice_move_sound()

    def _stop_dice_move_playlist(self):
        self._dice_move_playing = False
        if self._dice_move_clock:
            self._dice_move_clock.cancel()
            self._dice_move_clock = None
        for snd in self.dice_move_sounds:
            try:
                snd.volume = 0.0
                if snd.state == 'play':
                    snd.stop()
            except Exception:
                pass
        self._dice_move_current = None
        self._dice_move_current_volume = 0.0
        self._dice_move_target_volume = 0.0

    def _set_dice_move_volume(self, volume):
        if self.sound_manager.is_muted():
            self._dice_move_target_volume = 0.0
            return
        self._dice_move_target_volume = max(0.0, min(self.DICE_MOVE_MAX_VOLUME, volume))

    def _tick_dice_move_volume(self, dt):
        if self.sound_manager.is_muted():
            self._dice_move_target_volume = 0.0
            self._dice_move_current_volume = 0.0
            for snd in self.dice_move_sounds:
                try:
                    snd.volume = 0.0
                except Exception:
                    pass
            return

        diff = self._dice_move_target_volume - self._dice_move_current_volume
        if abs(diff) < 0.005:
            self._dice_move_current_volume = self._dice_move_target_volume
        else:
            self._dice_move_current_volume += diff * 0.5
        for snd in self.dice_move_sounds:
            try:
                snd.volume = self._dice_move_current_volume
            except Exception:
                pass

        if self.DICE_MOVE_DEBUG:
            playing = self._dice_move_playing
            idx = self._dice_move_index
            state = "?"
            if self._dice_move_current:
                state = self._dice_move_current.state
            print(f"🔊 [VOL] current={self._dice_move_current_volume:.3f} "
                  f"target={self._dice_move_target_volume:.3f} "
                  f"max={self.DICE_MOVE_MAX_VOLUME} "
                  f"playing={playing} idx={idx} state={state}")

    # ======================================================

    # ==================== ТИШИНА ДВИЖЕНИЯ СТАКАНА ====================

    def _tick_glass_drag_silence(self, dt):
        if not self.sound_glass_drag:
            return
        if self.sound_manager.is_muted():
            return

        if not self.is_at_target:
            if self.sound_glass_drag.volume > 0.01:
                self._fade_volume(0.0, 0.15)
            return

        elapsed = Clock.get_time() - self._last_drag_time
        if elapsed > 0.1:
            if self.sound_glass_drag.volume > 0.01:
                self._fade_volume(0.0, 0.15)

    # ============================================================

    def _fade_volume(self, target_volume, duration=0.2):
        if not self.sound_glass_drag:
            return
        self.target_volume = target_volume
        start_volume = self.sound_glass_drag.volume
        if self.volume_fade_clock:
            self.volume_fade_clock.cancel()
            self.volume_fade_clock = None

        def update_volume(step, steps):
            if step <= 0:
                self.sound_glass_drag.volume = target_volume
                self.volume_fade_clock = None
                return
            progress = step / steps
            self.sound_glass_drag.volume = start_volume + (target_volume - start_volume) * (1 - progress)
            self.volume_fade_clock = Clock.schedule_once(
                lambda dt: update_volume(step - 1, steps), duration / steps)

        steps = 20
        update_volume(steps, steps)

    def play_dice_roll_sound(self):
        if self.sound_dice_roll and not self.sound_manager.is_muted():
            self.sound_dice_roll.play()
            self.sound_manager.vibrate_short()

    def play_dice_appear_sound(self):
        if self.sound_dice_appear and not self.sound_manager.is_muted():
            self.sound_dice_appear.play()
            self.sound_manager.vibrate_short()

    def play_dice_disappear_sound(self):
        if self.sound_dice_disappear and not self.sound_manager.is_muted():
            self.sound_dice_disappear.play()
            self.sound_manager.vibrate_short()

    def _block_glass(self):
        self.is_glass_blocked = True

    def _unblock_glass(self):
        self.is_glass_blocked = False

    def _block_dice(self):
        self.is_dice_blocked = True

    def _unblock_dice(self):
        self.is_dice_blocked = False

    def _update_brightness(self, delta_distance=0):
        if delta_distance > 0 and self.dice_hidden:
            if not self._bet_placed_this_round:
                if not self._try_place_bet():
                    return

            old_brightness = self.current_brightness
            self.current_brightness += delta_distance * self.BRIGHTNESS_CHARGE_RATE

            reached_max = False
            if self.current_brightness >= self.MAX_BRIGHTNESS:
                self.current_brightness = self.MAX_BRIGHTNESS
                reached_max = True

            self.is_charging = True

            if reached_max:
                self._cancel_drain()
                self.sound_manager.vibrate_long()
                if self.particle_system:
                    self.particle_system.set_glow_mode(True)
            else:
                self._start_drain()

        if self.bg_dark and self.bg_bright:
            self.bg_bright.opacity = self.current_brightness
            self.bg_dark.opacity = 1.0 - self.current_brightness

    def _start_drain(self):
        if self.current_brightness <= self.MIN_BRIGHTNESS:
            return
        if self.drain_clock and self.is_draining_scheduled:
            return
        if self.drain_clock:
            self.drain_clock.cancel()
            self.drain_clock = None

        self.is_draining_scheduled = True

        def drain_step(dt):
            if self.is_charging:
                self.is_draining_scheduled = False
                self.drain_clock = None
                return
            if self.current_brightness > self.MIN_BRIGHTNESS:
                self.current_brightness -= self.BRIGHTNESS_DRAIN_RATE * dt
                if self.current_brightness < self.MIN_BRIGHTNESS:
                    self.current_brightness = self.MIN_BRIGHTNESS
                if self.bg_dark and self.bg_bright:
                    self.bg_bright.opacity = self.current_brightness
                    self.bg_dark.opacity = 1.0 - self.current_brightness
                if self.current_brightness > self.MIN_BRIGHTNESS and not self.is_charging:
                    self.drain_clock = Clock.schedule_once(drain_step, 0.05)
                    self.is_draining_scheduled = True
                else:
                    self.drain_clock = None
                    self.is_draining_scheduled = False
            else:
                self.drain_clock = None
                self.is_draining_scheduled = False
                if self.particle_system:
                    self.particle_system.set_glow_mode(False)

        self.drain_clock = Clock.schedule_once(drain_step, 0.05)

    def _cancel_drain(self):
        if self.drain_clock:
            self.drain_clock.cancel()
            self.drain_clock = None
        self.is_draining_scheduled = False

    def _reset_brightness(self):
        self.total_distance_traveled = 0.0
        self.current_brightness = 0.0
        self.is_charging = False
        self._cancel_drain()
        if self.bg_dark and self.bg_bright:
            self.bg_bright.opacity = 0.0
            self.bg_dark.opacity = 1.0
        if self.particle_system:
            self.particle_system.set_glow_mode(False)

    def _animate_dice_grow_with_move(self, dice, target_size, target_position, on_complete_callback=None):
        if hasattr(dice, 'is_animating_scale') and dice.is_animating_scale:
            return
        dice.is_animating_scale = True
        self._block_glass()
        if dice.original_center is None:
            dice.original_center = (dice.pos[0] + dice.width / 2, dice.pos[1] + dice.height / 2)
        if dice.glow:
            Animation(opacity=0, duration=0.3).start(dice.glow)

        if self.ANIM_DEBUG:
            print(f"🎲 [ANIM] СТАРТ анимаций для кубика {dice}")
            print(f"🎲 [ANIM]   - вращение (animate_enlarge): "
                  f"{self.FIRST_ANIMATION_DURATION + self.SECOND_ANIMATION_DURATION} сек")
            print(f"🎲 [ANIM]   - рост (anim_grow): {self.SECOND_ANIMATION_DURATION} сек")
            print(f"🎲 [ANIM]   - перемещение (anim_move): {self.SECOND_ANIMATION_DURATION} сек")

        dice.load_enlarge_spritesheet(self.enlarge_sprite_sheet_path)
        current_frame = dice.frame_index

        dice.animate_enlarge(
            current_frame,
            duration=self.FIRST_ANIMATION_DURATION + self.SECOND_ANIMATION_DURATION
        )

        anim_grow = Animation(
            dice_size=target_size,
            duration=self.SECOND_ANIMATION_DURATION,
            t='linear'
        )
        anim_move = Animation(
            pos=target_position,
            duration=self.SECOND_ANIMATION_DURATION,
            t='linear'
        )

        already_called = {'done': False}

        def fire_callback():
            if already_called['done']:
                return
            already_called['done'] = True
            if self.ANIM_DEBUG:
                print(f"✅ [ANIM] ЗАВЕРШЕНО вращение кубика {dice}")
            dice.is_animating_scale = False
            self.is_dice_enlarged = True
            dice.enlarged_size = target_size
            self._unblock_dice()
            if self.particle_system:
                self.particle_system.set_glow_mode(False)
            if on_complete_callback:
                on_complete_callback()

        Clock.schedule_once(
            lambda dt: fire_callback(),
            self.FIRST_ANIMATION_DURATION + self.SECOND_ANIMATION_DURATION
        )

        anim_grow.start(dice)
        anim_move.start(dice)

    def _animate_dice_shrink_with_move(self, dice, original_size, target_position, on_complete_callback=None):
        if hasattr(dice, 'is_animating_scale') and dice.is_animating_scale:
            return
        dice.is_animating_scale = True
        if dice.original_center is None:
            original_center_x = dice.pos[0] + dice.width / 2
            original_center_y = dice.pos[1] + dice.height / 2
        else:
            original_center_x, original_center_y = dice.original_center
        dice.load_enlarge_spritesheet(self.enlarge_sprite_sheet_path)
        current_frame = dice.frame_index
        dice.animate_shrink(current_frame, duration=self.FIRST_ANIMATION_DURATION + self.SECOND_ANIMATION_DURATION)
        if dice.glow:
            dice.glow.opacity = 0
            Clock.schedule_once(lambda dt: self._appear_glow(dice.glow), self.ANIMATION_DURATION + 0.3)
        anim_shrink = Animation(dice_size=original_size, duration=self.SECOND_ANIMATION_DURATION * 2, t='linear')
        anim_move_back = Animation(pos=target_position, duration=self.SECOND_ANIMATION_DURATION * 2, t='linear')

        def on_complete(*args):
            dice.is_animating_scale = False
            dice.original_center = None
            if self.particle_system:
                self.particle_system.set_glow_mode(True)
                Clock.schedule_once(lambda dt: self.particle_system.set_glow_mode(False) if self.particle_system else None, 0.5)
            if on_complete_callback:
                on_complete_callback()

        anim_shrink.bind(on_complete=on_complete)
        anim_shrink.start(dice)
        anim_move_back.start(dice)

    def _appear_glow(self, glow):
        if glow:
            Animation(opacity=1, duration=0.1).start(glow)

    def _bring_dice_above_glass(self):
        for dice in self.dice_list:
            if dice.parent:
                dice.parent.remove_widget(dice)
                self.layout.add_widget(dice)

    def _animate_dice_appearance(self):
        if self.ANIM_DEBUG:
            print("🚀 [ANIM] СТАРТ _animate_dice_appearance "
                  f"(кубиков: {len(self.dice_list)})")
        self._bring_dice_above_glass()
        self._block_dice()
        self.saved_point_a_position = self._get_current_point_a_position()
        positions = self._get_center_positions()
        original_positions = self._get_dice_original_positions()
        completed_animations = [0]
        total_dice = len(self.dice_list)

        def check_all_complete():
            completed_animations[0] += 1
            if self.ANIM_DEBUG:
                print(f"📊 [ANIM] check_all_complete: "
                      f"{completed_animations[0]}/{total_dice}")
            if completed_animations[0] >= total_dice:
                if self.ANIM_DEBUG:
                    print("🎯 [ANIM] ВСЕ вращения завершены — "
                          "применяем результат и играем звуки бонуса")
                self._apply_bet_result()

        for i, dice in enumerate(self.dice_list):
            if not hasattr(dice, 'original_position') or dice.original_position is None:
                dice.original_position = original_positions.get(i, dice.pos)
            if not hasattr(dice, 'original_size') or dice.original_size is None:
                dice.original_size = dice.dice_size
            if dice.original_center is None:
                dice.original_center = (dice.pos[0] + dice.width / 2, dice.pos[1] + dice.height / 2)
            target_size = dice.original_size * 5
            if len(self.dice_list) == 1:
                target_x = positions['pos2'][0] - target_size / 2
                target_y = positions['pos2'][1] - target_size / 2
            else:
                if i == 0:
                    target_x = positions['pos1'][0] - target_size / 2
                    target_y = positions['pos1'][1] - target_size / 2
                else:
                    target_x = positions['pos3'][0] - target_size / 2
                    target_y = positions['pos3'][1] - target_size / 2
            self._animate_dice_grow_with_move(dice, target_size, (target_x, target_y), check_all_complete)

    def _send_dice_below_glass(self):
        for dice in self.dice_list:
            if dice.parent:
                dice.parent.remove_widget(dice)
        for dice in self.dice_list:
            self.layout.add_widget(dice, index=0)
        if self.glass and self.glass.parent:
            self.glass.parent.remove_widget(self.glass)
        if self.glass:
            self.layout.add_widget(self.glass)

    def _shrink_all_dice(self, on_complete_callback=None):
        if not self.is_dice_enlarged:
            if on_complete_callback:
                on_complete_callback()
            return
        self._block_dice()
        completed_animations = [0]
        total_dice = len(self.dice_list)

        def check_all_complete():
            completed_animations[0] += 1
            if completed_animations[0] >= total_dice:
                self.is_dice_enlarged = False
                self._unblock_glass()
                self._unblock_dice()
                self._send_dice_below_glass()
                if on_complete_callback:
                    on_complete_callback()
                if self.current_brightness > 0:
                    self.is_charging = False
                    self._start_drain()

        for dice in self.dice_list:
            original_size = getattr(dice, 'original_size', dice.dice_size)
            if self.saved_point_a_position:
                point_a_x, point_a_y = self.saved_point_a_position
                if len(self.dice_list) == 1:
                    target_x = point_a_x - original_size / 2
                    target_y = point_a_y - original_size / 2
                else:
                    distance_between = self.double_dice_size * 0.3
                    index = self.dice_list.index(dice)
                    if index == 0:
                        target_y = point_a_y - distance_between - original_size / 2
                    else:
                        target_y = point_a_y + distance_between - original_size / 2
                    target_x = point_a_x - original_size / 2
            else:
                target_x, target_y = dice.original_position
            self._animate_dice_shrink_with_move(dice, original_size, (target_x, target_y), check_all_complete)

    def _raise_glass(self, on_complete_callback=None, flash_after=False):
        if self.magnetic_field:
            self.magnetic_field.stop()
        self._block_dice()
        if self.sound_glass_raise and not self.sound_manager.is_muted():
            self.sound_glass_raise.play()
            self.sound_manager.vibrate_short()
        shadow_target_pos = (self.SHADOW_TARGET_POSITION_X, self.SHADOW_TARGET_POSITION_Y)
        for dice in self.dice_list:
            if dice.glow:
                dice.glow.update_position(dice.pos, dice.dice_size)
            dice.enable_glow()

        def on_animation_complete(*args):
            self.is_at_target = False
            if self._on_glass_move_complete:
                self._on_glass_move_complete()
            if on_complete_callback:
                on_complete_callback()
            self._update_point_a_marker()
            self._unblock_dice()
            self._update_glass_highlight()
            self._update_dice_z_order()

            if flash_after:
                self._flash_token_widget(with_reject_sound=True)

        self.glass.animate_movement(
            start_pos=self.glass_start_pos,
            end_pos=self.glass_target_pos,
            duration=0.6,
            forward=True,
            callback=on_animation_complete
        )
        self.shadow.animate_movement_to_target(
            target_pos=shadow_target_pos,
            duration=0.6,
            forward=True
        )

    def _lower_glass(self):
        if self.magnetic_field:
            self.magnetic_field.update_glass_position(self.glass_start_pos)
        self._block_dice()
        self._ensure_glass_on_top_during_lowering()
        self.max_speed = 0
        self.last_touch_pos = None
        self.last_touch_time = None
        self.shadow.pos = (self.SHADOW_TARGET_POSITION_X, self.SHADOW_TARGET_POSITION_Y)
        shadow_target_pos = (self.SHADOW_POSITION_X, self.SHADOW_POSITION_Y)

        def on_animation_complete(*args):
            self.is_at_target = True
            if self.sound_glass_lower and not self.sound_manager.is_muted():
                self.sound_glass_lower.play()
                self.sound_manager.vibrate_short()
            if self._on_glass_move_complete:
                self._on_glass_move_complete()
            self._update_point_a_marker()
            self._unblock_dice()
            self._update_glass_highlight()
            if self.magnetic_field and not self.dice_hidden and not self.is_dice_enlarged:
                self.magnetic_field.start()

        self.glass.animate_movement(
            start_pos=self.glass_target_pos,
            end_pos=self.glass_start_pos,
            duration=0.6,
            forward=False,
            callback=on_animation_complete
        )
        self.shadow.animate_movement_to_target(
            target_pos=shadow_target_pos,
            duration=0.6,
            forward=False
        )

    def _lower_glass_to_center(self, target_center_x, target_center_y):
        self.saved_dice_positions = []
        for dice in self.dice_list:
            self.saved_dice_positions.append((dice.pos[0], dice.pos[1]))
        if self.magnetic_field:
            self.magnetic_field.update_glass_position(self.glass_start_pos)
        self._block_dice()
        self._ensure_glass_on_top_during_lowering()
        self.max_speed = 0
        self.last_touch_pos = None
        self.last_touch_time = None

        old_start_x = self.glass_start_pos[0]
        old_start_y = self.glass_start_pos[1]
        old_target_x = self.glass_target_pos[0]
        old_target_y = self.glass_target_pos[1]
        old_shadow_x = self.SHADOW_POSITION_X
        old_shadow_y = self.SHADOW_POSITION_Y
        old_shadow_target_x = self.SHADOW_TARGET_POSITION_X
        old_shadow_target_y = self.SHADOW_TARGET_POSITION_Y

        new_start_x = target_center_x - self.glass_size / 6.5
        new_start_y = target_center_y - self.glass_size / 2

        offset_x = new_start_x - old_start_x
        offset_y = new_start_y - old_start_y

        new_target_x = old_target_x + offset_x
        new_target_y = old_target_y + offset_y
        new_shadow_x = old_shadow_x + offset_x
        new_shadow_y = old_shadow_y + offset_y
        new_shadow_target_x = old_shadow_target_x + offset_x
        new_shadow_target_y = old_shadow_target_y + offset_y

        self.shadow.pos = (old_shadow_target_x, old_shadow_target_y)
        shadow_target_pos = (new_shadow_x, new_shadow_y)
        Clock.schedule_once(lambda dt: self._disable_glow_for_all_dice(), 0.7)
        animation_duration = 0.8

        def on_animation_complete(*args):
            self.glass_start_pos = (new_start_x, new_start_y)
            self.glass_target_pos = (new_target_x, new_target_y)
            self.SHADOW_POSITION_X = new_shadow_x
            self.SHADOW_POSITION_Y = new_shadow_y
            self.SHADOW_TARGET_POSITION_X = new_shadow_target_x
            self.SHADOW_TARGET_POSITION_Y = new_shadow_target_y
            self.glass.pos = self.glass_start_pos
            self.is_at_target = True
            if self.sound_glass_lower and not self.sound_manager.is_muted():
                self.sound_glass_lower.play()
                self.sound_manager.vibrate_short()
            if self.pending_hide_dice:
                for dice in self.dice_list:
                    dice.opacity = 0
                    if dice.glow:
                        dice.glow.opacity = 0
                self.dice_hidden = True
                self.pending_hide_dice = False
                self._start_dice_move_playlist()
            self._update_point_a_marker()
            self._unblock_dice()
            self._update_glass_highlight()
            self._update_dice_z_order()
            if self._on_glass_move_complete:
                self._on_glass_move_complete()

        self.glass.animate_movement(
            start_pos=self.glass_target_pos,
            end_pos=(new_start_x, new_start_y),
            duration=animation_duration,
            forward=False,
            callback=on_animation_complete
        )
        self.shadow.animate_movement_to_target(
            target_pos=shadow_target_pos,
            duration=animation_duration,
            forward=False
        )

    # ===== ВРАЩЕНИЕ КУБА ПРИ КОНТАКТЕ С МАГНИТНЫМ ПОЛЕМ =====

    def _update_dice_rotation_by_magnetic_field(self, glass_delta_x, glass_delta_y):
        if not self.dice_list:
            return
        distance = math.sqrt(glass_delta_x * glass_delta_x + glass_delta_y * glass_delta_y)
        if distance <= 0:
            return
        for dice in self.dice_list:
            if not self.dice_contact_flags.get(dice, False):
                continue
            if self._is_dice_above_glass(dice):
                if abs(glass_delta_x) > abs(glass_delta_y):
                    frame_change = -1 if glass_delta_x > 0 else 1
                else:
                    frame_change = -1 if glass_delta_y > 0 else 1
            else:
                if abs(glass_delta_x) > abs(glass_delta_y):
                    frame_change = 1 if glass_delta_x > 0 else -1
                else:
                    frame_change = 1 if glass_delta_y > 0 else -1
            accumulator = self.dice_frame_accumulators.get(dice, 0.0)
            accumulator += distance
            while accumulator >= self.frame_change_threshold:
                current_frame = dice.frame_index
                new_frame = current_frame + frame_change
                total_frames = dice.rows * dice.cols
                if new_frame >= total_frames:
                    new_frame = 0
                elif new_frame < 0:
                    new_frame = total_frames - 1
                dice.set_frame_direct(new_frame)
                accumulator -= self.frame_change_threshold
            self.dice_frame_accumulators[dice] = accumulator

    def _start_magnetic_contact_monitoring(self):
        def check_contact(dt):
            if not self.magnetic_field or not self.glass or not self.dice_list:
                return
            glass_x = self.glass.pos[0] + self.glass.width / 2
            glass_y = self.glass.pos[1] + self.glass.height / 2
            contact_radius = self.glass_size * 0.8
            for dice in self.dice_list:
                dice_x = dice.pos[0] + dice.width / 2
                dice_y = dice.pos[1] + dice.height / 2
                distance = math.sqrt((glass_x - dice_x)**2 + (glass_y - dice_y)**2)
                was_contact = self.dice_contact_flags.get(dice, False)
                is_contact = distance < contact_radius
                if is_contact and not was_contact:
                    self.dice_contact_flags[dice] = True
                    self.dice_frame_accumulators[dice] = 0.0
                elif not is_contact and was_contact:
                    self.dice_contact_flags[dice] = False
                    self.dice_frame_accumulators[dice] = 0.0

        self.contact_monitor = Clock.schedule_interval(check_contact, 0.1)

    def _on_dice_click(self):
        if self.is_dice_blocked:
            return
        if self.is_animating:
            return
        if self.is_dice_enlarged:
            self._shrink_all_dice()
        else:
            self._start_switch_animation()

    def on_enter(self):
        super().on_enter()
        self._load_dice_sounds()
        screen_width, screen_height = self.get_screen_size()

        self.single_dice_size = screen_width * 0.126
        self.double_dice_size = screen_width * 0.1
        self.large_dice_size = self.single_dice_size * 5
        self.glass_size = screen_width * 0.20
        self.shadow_size = self.glass_size * 0.9

        self.START_POSITION_DICE_X = screen_width * 0.3
        self.START_POSITION_DICE_Y = screen_height * 0.5 - (self.single_dice_size // 2)
        self.START_POSITION_GLASS_X = screen_width * 0.27
        self.START_POSITION_GLASS_Y = screen_height * 0.25

        self.SHADOW_POSITION_X = self.START_POSITION_GLASS_X + (self.glass_size * self.shadow_offset_x_factor)
        self.SHADOW_POSITION_Y = self.START_POSITION_GLASS_Y + (self.glass_size * self.shadow_offset_y_factor)

        self.glass_start_pos = (self.START_POSITION_GLASS_X, self.START_POSITION_GLASS_Y)
        self.glass_target_pos = (self.START_POSITION_GLASS_X + self.glass_size, self.START_POSITION_GLASS_Y - self.glass_size)

        self.SHADOW_TARGET_POSITION_X = self.SHADOW_POSITION_X + (self.glass_size * self.shadow_move_factor_x)
        self.SHADOW_TARGET_POSITION_Y = self.SHADOW_POSITION_Y - (self.glass_size * self.shadow_move_factor_y)

        self._reset_bet_flag()
        self._last_result = None

        self._dice_move_index = 0
        self._dice_move_playing = False
        self._dice_move_current = None
        if self._dice_move_clock:
            self._dice_move_clock.cancel()
            self._dice_move_clock = None
        self._dice_move_target_volume = 0.0
        self._dice_move_current_volume = 0.0

        self._last_drag_time = Clock.get_time()
        if self._glass_drag_silence_clock:
            self._glass_drag_silence_clock.cancel()
            self._glass_drag_silence_clock = None
        self._glass_drag_silence_clock = Clock.schedule_interval(
            self._tick_glass_drag_silence, 0.05)

        self._setup_ui()
        self._create_token_widget()

        Clock.schedule_interval(self._tick_dice_move_volume, 0.05)

        Clock.schedule_once(lambda dt: self._create_drop_zone(), 0.1)
        Clock.schedule_once(lambda dt: self._create_magnetic_field(), 0.3)

    def _create_drop_zone(self):
        screen_width, screen_height = self.get_screen_size()
        self.drop_zone = DropZone(screen_width, screen_height)
        self.layout.add_widget(self.drop_zone)
        if DEBUG_MODE:
            self.drop_zone.update_zone_visibility()
            Clock.schedule_once(lambda dt: self._visualize_drop_zone(), 0.1)

    def _create_magnetic_field(self):
        if self.drop_zone and self.dice_list:
            current_dice_size = self.single_dice_size if self.current_mode == 1 else self.double_dice_size
            self.magnetic_field = MagneticField(
                drop_zone=self.drop_zone,
                dice_list=self.dice_list,
                glass_start_pos=self.glass_start_pos,
                glass_size=self.glass_size,
                dice_size=current_dice_size
            )
            if self.is_at_target and not self.dice_hidden and not self.is_dice_enlarged:
                self.magnetic_field.start()
            for dice in self.dice_list:
                self.dice_contact_flags[dice] = False
                self.dice_frame_accumulators[dice] = 0.0
            self._start_magnetic_contact_monitoring()

    def _visualize_drop_zone(self):
        if not DEBUG_MODE or not self.drop_zone:
            return
        if hasattr(self, '_drop_zone_visualization') and self._drop_zone_visualization:
            try:
                self.drop_zone.canvas.before.remove(self._drop_zone_visualization)
            except:
                pass
        with self.drop_zone.canvas.before:
            Color(0, 1, 0, 0.25)
            self._drop_zone_visualization = Ellipse(pos=self.drop_zone.pos, size=self.drop_zone.size)

    def _get_current_point_a_position(self):
        point_a_x = self.glass_start_pos[0] + self.glass_size / 6.5
        point_a_y = self.glass_start_pos[1] + self.glass_size / 2
        return (point_a_x, point_a_y)

    def _sync_dice_to_point_a(self):
        if not self.dice_list:
            return
        point_a_x, point_a_y = self._get_current_point_a_position()

        if len(self.dice_list) == 1:
            dice = self.dice_list[0]
            if not self.has_moved_with_dice and self.saved_dice_positions and len(self.saved_dice_positions) >= 1:
                target_x, target_y = self.saved_dice_positions[0]
            else:
                target_x = point_a_x - dice.width / 2
                target_y = point_a_y - dice.height / 2
            dice.pos = (target_x, target_y)
            dice.opacity = 1
            if dice.glow:
                dice.glow.update_position(dice.pos, dice.dice_size)
                dice.glow.opacity = 1
        else:
            distance_between = self.double_dice_size * 0.3
            for i, dice in enumerate(self.dice_list):
                if not self.has_moved_with_dice and self.saved_dice_positions and len(self.saved_dice_positions) > i:
                    target_x, target_y = self.saved_dice_positions[i]
                else:
                    if i == 0:
                        target_y = point_a_y - distance_between - dice.height / 2
                    else:
                        target_y = point_a_y + distance_between - dice.height / 2
                    target_x = point_a_x - dice.width / 2
                dice.pos = (target_x, target_y)
                dice.opacity = 1
                if dice.glow:
                    dice.glow.update_position(dice.pos, dice.dice_size)
                    dice.glow.opacity = 1

        self.saved_dice_positions = []
        for dice in self.dice_list:
            dice.canvas.ask_update()
            if dice.glow:
                dice.glow.canvas.ask_update()
        self._update_dice_z_order()

    def _update_dice_position(self, delta_x, delta_y):
        if not self.dice_list:
            return
        for dice in self.dice_list:
            new_x = dice.pos[0] + delta_x
            new_y = dice.pos[1] + delta_y
            dice.pos = (new_x, new_y)
            if dice.glow:
                dice.glow.update_position(dice.pos, dice.dice_size)
        self._update_dice_z_order()

    def _enforce_point_a_in_zone(self):
        if not self.drop_zone or not self.glass:
            return
        point_a_x, point_a_y = self._get_current_point_a_position()
        if self.drop_zone.check_point_in_zone(point_a_x, point_a_y):
            return
        clamped_point_a = self.drop_zone.clamp_point_to_zone(point_a_x, point_a_y)
        new_glass_x = clamped_point_a[0] - self.glass_size / 6.5
        new_glass_y = clamped_point_a[1] - self.glass_size / 2
        delta_x = new_glass_x - self.glass_start_pos[0]
        delta_y = new_glass_y - self.glass_start_pos[1]
        self.glass_start_pos = (new_glass_x, new_glass_y)
        self.glass_target_pos = (self.glass_target_pos[0] + delta_x, self.glass_target_pos[1] + delta_y)
        if self.is_at_target:
            self.glass.pos = self.glass_start_pos
        else:
            self.glass.pos = self.glass_target_pos
        self.SHADOW_POSITION_X += delta_x
        self.SHADOW_POSITION_Y += delta_y
        self.SHADOW_TARGET_POSITION_X += delta_x
        self.SHADOW_TARGET_POSITION_Y += delta_y
        self.shadow.move_by_delta(delta_x, delta_y)
        if self.dice_hidden:
            self._update_dice_position(delta_x, delta_y)
        if self.magnetic_field:
            self.magnetic_field.update_glass_position(self.glass_start_pos)
        self._update_dice_z_order()

    def _clamp_position_to_zone(self, pos_x, pos_y):
        if not self.drop_zone:
            return (pos_x, pos_y)
        if not self.is_at_target:
            delta_x = pos_x - self.glass_target_pos[0]
            delta_y = pos_y - self.glass_target_pos[1]
            new_start_x = self.glass_start_pos[0] + delta_x
            new_start_y = self.glass_start_pos[1] + delta_y
            point_a_x = new_start_x + self.glass_size / 6.5
            point_a_y = new_start_y + self.glass_size / 2
        else:
            point_a_x = pos_x + self.glass_size / 6.5
            point_a_y = pos_y + self.glass_size / 2
        if self.drop_zone.check_point_in_zone(point_a_x, point_a_y):
            return (pos_x, pos_y)
        clamped_point_a = self.drop_zone.clamp_point_to_zone(point_a_x, point_a_y)
        if not self.is_at_target:
            new_start_x = clamped_point_a[0] - self.glass_size / 6.5
            new_start_y = clamped_point_a[1] - self.glass_size / 2
            delta_x = new_start_x - self.glass_start_pos[0]
            delta_y = new_start_y - self.glass_start_pos[1]
            new_target_x = self.glass_target_pos[0] + delta_x
            new_target_y = self.glass_target_pos[1] + delta_y
            return (new_target_x, new_target_y)
        else:
            new_pos_x = clamped_point_a[0] - self.glass_size / 6.5
            new_pos_y = clamped_point_a[1] - self.glass_size / 2
            return (new_pos_x, new_pos_y)

    def _update_glass_highlight(self):
        if not DEBUG_MODE or not self.glass or not self.drop_zone:
            return
        point_a_x, point_a_y = self._get_current_point_a_position()
        is_in_zone = self.drop_zone.check_point_in_zone(point_a_x, point_a_y)
        if hasattr(self.glass, 'color_overlay') and self.glass.color_overlay:
            try:
                self.glass.canvas.before.remove(self.glass.color_overlay)
            except:
                pass
            self.glass.color_overlay = None
        with self.glass.canvas.before:
            if is_in_zone:
                Color(0, 1, 0, 0.3)
            else:
                Color(1, 0, 0, 0.5)
            self.glass.color_overlay = Rectangle(pos=self.glass.pos, size=self.glass.size)
        return is_in_zone

    def _create_point_a_marker(self):
        if DEBUG_MODE:
            self.point_a_marker = PointMarker(color=(1, 0, 0, 1), size=10)
        else:
            self.point_a_marker = PointMarker(color=(1, 1, 1, 0), size=2)
        self.layout.add_widget(self.point_a_marker)
        self._bring_point_a_to_top()
        self._update_point_a_marker()

    def _bring_point_a_to_top(self):
        if self.point_a_marker and self.point_a_marker.parent:
            self.point_a_marker.parent.remove_widget(self.point_a_marker)
            self.layout.add_widget(self.point_a_marker)

    def _update_point_a_marker(self):
        if self.point_a_marker and self.drop_zone:
            self._enforce_point_a_in_zone()
            point_a_x, point_a_y = self._get_current_point_a_position()
            if DEBUG_MODE:
                in_zone = self.drop_zone.check_point_in_zone(point_a_x, point_a_y)
                self.point_a_marker.color = (0, 1, 0, 1) if in_zone else (1, 0, 0, 1)
            else:
                self.point_a_marker.color = (1, 1, 1, 0)
            self.point_a_marker.update_position(point_a_x, point_a_y, visible=True)
            self._bring_point_a_to_top()
            return in_zone if DEBUG_MODE else True
        return True

    def on_leave(self):
        if hasattr(self, 'contact_monitor') and self.contact_monitor:
            self.contact_monitor.cancel()
            self.contact_monitor = None
        if hasattr(self, '_animation_monitor') and self._animation_monitor:
            self._animation_monitor.cancel()
        if self.particle_system:
            self.particle_system.cleanup()
            if self.particle_system in self.layout.children:
                self.layout.remove_widget(self.particle_system)
            self.particle_system = None
        if self.magnetic_field:
            self.magnetic_field.stop()
            self.magnetic_field = None
        self._reset_brightness()
        if self.volume_fade_clock:
            self.volume_fade_clock.cancel()
            self.volume_fade_clock = None
        if self.sound_glass_drag:
            try:
                self.sound_glass_drag.stop()
            except:
                pass
        self._stop_dice_move_playlist()
        if self._glass_drag_silence_clock:
            self._glass_drag_silence_clock.cancel()
            self._glass_drag_silence_clock = None
        if self._bonus_clock:
            self._bonus_clock.cancel()
            self._bonus_clock = None
        self._bonus_queue = 0
        if hasattr(self, '_drop_zone_visualization') and self._drop_zone_visualization:
            try:
                if self.drop_zone and self.drop_zone.canvas:
                    self.drop_zone.canvas.before.remove(self._drop_zone_visualization)
            except:
                pass
        self._clear_all_dice()
        if self.glass and self.glass.parent:
            if hasattr(self.glass, 'color_overlay') and self.glass.color_overlay:
                try:
                    self.glass.canvas.before.remove(self.glass.color_overlay)
                except:
                    pass
            self.layout.remove_widget(self.glass)
            self.glass = None
        if self.shadow and self.shadow.parent:
            self.layout.remove_widget(self.shadow)
            self.shadow = None
        if self.drop_zone and self.drop_zone.parent:
            self.layout.remove_widget(self.drop_zone)
            self.drop_zone = None
        if self.point_a_marker and self.point_a_marker.parent:
            self.layout.remove_widget(self.point_a_marker)
            self.point_a_marker = None
        if self.bg_dark and self.bg_dark.parent:
            self.layout.remove_widget(self.bg_dark)
            self.bg_dark = None
        if self.bg_bright and self.bg_bright.parent:
            self.layout.remove_widget(self.bg_bright)
            self.bg_bright = None
        self._remove_token_widget()
        self._reset_bet_flag()
        super().on_leave()

    def _setup_ui(self):
        if os.path.exists(self.background_image):
            self.bg_dark = Image(source=self.background_image, allow_stretch=True, keep_ratio=False, size_hint=(1, 1), opacity=1)
            self.layout.add_widget(self.bg_dark, index=0)
        if os.path.exists(self.background_bright_image):
            self.bg_bright = Image(source=self.background_bright_image, allow_stretch=True, keep_ratio=False, size_hint=(1, 1), opacity=0)
            self.layout.add_widget(self.bg_bright, index=0)
        self.particle_system = ParticleSystem(num_particles=30)
        self.layout.add_widget(self.particle_system)
        self._reset_brightness()
        self._create_point_a_marker()
        self._create_shadow()
        self._create_dice_for_mode(1, animate=False)
        self._create_glass()
        self.create_back_button()

    def _create_shadow(self):
        offset_x_px = self.glass_size * self.shadow_offset_x_factor
        offset_y_px = self.glass_size * self.shadow_offset_y_factor
        self.shadow = ShadowWidget(
            sprite_sheet_path=self.shadow_sprite_sheet_path,
            shadow_size=self.shadow_size,
            rows=2,
            cols=12,
            frame_index=0,
            rotation_angle=self.shadow_rotation,
            scale_factor=self.shadow_scale_factor,
            offset_x=offset_x_px,
            offset_y=offset_y_px,
            opacity=self.shadow_opacity,
            move_factor_x=self.shadow_move_factor_x,
            move_factor_y=self.shadow_move_factor_y,
            glass_size=self.glass_size,
            size_hint=(None, None),
            size=(self.shadow_size * self.shadow_scale_factor, self.shadow_size * self.shadow_scale_factor),
            pos=(self.SHADOW_POSITION_X, self.SHADOW_POSITION_Y)
        )
        self.shadow.set_frame(0)
        self.layout.add_widget(self.shadow)

    def _create_glass(self):
        self.glass = GlassWidget(
            sprite_sheet_path=self.glass_sprite_sheet_path,
            glass_size=self.glass_size,
            rows=2,
            cols=12,
            frame_index=0,
            rotation_angle=-90,
            size_hint=(None, None),
            size=(self.glass_size, self.glass_size),
            pos=self.glass_start_pos,
            on_glass_click=self._on_glass_click,
            on_glass_drag=self._on_glass_drag,
            on_glass_drag_end=self._on_glass_drag_end,
            debug_mode=DEBUG_MODE
        )
        self.glass.set_frame(0)
        self.layout.add_widget(self.glass)
        self.is_at_target = True

    def _on_glass_drag(self, delta_x, delta_y, touch):
        if self.is_glass_blocked:
            return
        if self.is_animating:
            return
        if delta_x == 0 and delta_y == 0:
            return
        self._last_drag_time = Clock.get_time()

        self._update_dice_rotation_by_magnetic_field(delta_x, delta_y)

        if self.dice_hidden:
            self.has_moved_with_dice = True
            distance = math.sqrt(delta_x * delta_x + delta_y * delta_y)
            if distance > 0:
                self._update_brightness(delta_distance=distance)
                if not self.sound_manager.is_muted():
                    added_volume = distance * 0.5
                    new_target = self._dice_move_target_volume + added_volume
                    self._set_dice_move_volume(new_target)

            def reset_charging_flag(dt):
                if not self.dice_hidden:
                    self.is_charging = False
                elif self.current_brightness >= self.MAX_BRIGHTNESS:
                    pass
                else:
                    self.is_charging = False
                    if self.current_brightness > 0:
                        self._start_drain()

            if self._reset_charge_clock:
                self._reset_charge_clock.cancel()
            self._reset_charge_clock = Clock.schedule_once(reset_charging_flag, 0.05)

            def decay_move_volume(dt):
                if not self.dice_hidden:
                    return
                self._set_dice_move_volume(0.0)
            Clock.schedule_once(decay_move_volume, 0.15)

        if self.is_at_target:
            current_time = Clock.get_time()
            current_pos = (touch.x, touch.y)
            if self.last_touch_pos is None or self.last_touch_time is None:
                self.last_touch_pos = current_pos
                self.last_touch_time = current_time
                current_speed = 0
            else:
                dx = current_pos[0] - self.last_touch_pos[0]
                dy = current_pos[1] - self.last_touch_pos[1]
                distance = math.sqrt(dx * dx + dy * dy)
                dt = current_time - self.last_touch_time
                if dt > 0:
                    current_speed = distance / dt
                    if current_speed > self.max_speed:
                        self.max_speed = current_speed
                else:
                    current_speed = 0
                self.last_touch_pos = current_pos
                self.last_touch_time = current_time
            MIN_SPEED = 50
            MAX_SPEED = 800
            MIN_VOLUME = 0.0
            MAX_VOLUME = 0.5
            if current_speed > MIN_SPEED:
                target_volume = MIN_VOLUME + (current_speed - MIN_SPEED) / (MAX_SPEED - MIN_SPEED) * (MAX_VOLUME - MIN_VOLUME)
                target_volume = max(MIN_VOLUME, min(MAX_VOLUME, target_volume))
            else:
                target_volume = 0.0
            if self.sound_glass_drag and not self.sound_manager.is_muted():
                if abs(target_volume - self.sound_glass_drag.volume) > 0.1:
                    self._fade_volume(target_volume, 0.1)
                else:
                    self.sound_glass_drag.volume = target_volume
        else:
            if self.sound_glass_drag:
                self._fade_volume(0.0, 0.2)

        if self.dice_hidden:
            self._update_dice_position(delta_x, delta_y)

        if self.is_at_target:
            new_glass_x = self.glass_start_pos[0] + delta_x
            new_glass_y = self.glass_start_pos[1] + delta_y
        else:
            new_glass_x = self.glass_target_pos[0] + delta_x
            new_glass_y = self.glass_target_pos[1] + delta_y

        clamped_pos = self._clamp_position_to_zone(new_glass_x, new_glass_y)
        if self.is_at_target:
            actual_delta_x = clamped_pos[0] - self.glass_start_pos[0]
            actual_delta_y = clamped_pos[1] - self.glass_start_pos[1]
            self.glass_start_pos = clamped_pos
            self.glass_target_pos = (self.glass_target_pos[0] + actual_delta_x, self.glass_target_pos[1] + actual_delta_y)
            self.glass.pos = self.glass_start_pos
        else:
            actual_delta_x = clamped_pos[0] - self.glass_target_pos[0]
            actual_delta_y = clamped_pos[1] - self.glass_target_pos[1]
            self.glass_target_pos = clamped_pos
            self.glass_start_pos = (self.glass_start_pos[0] + actual_delta_x, self.glass_start_pos[1] + actual_delta_y)
            self.glass.pos = self.glass_target_pos

        self.SHADOW_POSITION_X += actual_delta_x
        self.SHADOW_POSITION_Y += actual_delta_y
        self.SHADOW_TARGET_POSITION_X += actual_delta_x
        self.SHADOW_TARGET_POSITION_Y += actual_delta_y
        self.shadow.move_by_delta(actual_delta_x, actual_delta_y)
        if self.magnetic_field and self.is_at_target:
            self.magnetic_field.update_glass_position(self.glass_start_pos)
        if not self.dice_hidden:
            self._update_dice_z_order()
        self._update_point_a_marker()

    def _on_glass_drag_end(self, touch):
        if self.sound_glass_drag:
            self._fade_volume(0.0, 0.3)
        self._set_dice_move_volume(0.0)
        self.last_touch_pos = None
        self.last_touch_time = None
        if self._reset_charge_clock:
            self._reset_charge_clock.cancel()
            self._reset_charge_clock = None
        self._enforce_point_a_in_zone()
        self._update_point_a_marker()
        if self.dice_hidden and self.current_brightness > 0 and not self.is_charging:
            self.is_charging = False
            if self.current_brightness < self.MAX_BRIGHTNESS:
                self._start_drain()
        self._update_dice_z_order()
        if self.magnetic_field and self.is_at_target and not self.dice_hidden and not self.is_dice_enlarged:
            if not self.magnetic_field.is_magnetic_active():
                self.magnetic_field.start()

    def _on_glass_click(self):
        if self.is_glass_blocked:
            return
        if self.is_animating:
            return

        if self.is_at_target:
            was_dice_hidden = self.dice_hidden

            if self.dice_hidden:
                self._sync_dice_to_point_a()
                for dice in self.dice_list:
                    dice.opacity = 1
                    if dice.glow:
                        dice.glow.opacity = 1
                self.dice_hidden = False
                self.pending_hide_dice = False
                for dice in self.dice_list:
                    dice.enable_glow()
                self._stop_dice_move_playlist()

            if self.current_brightness >= self.MAX_BRIGHTNESS - 0.001:
                if not self._bet_placed_this_round and not self._can_play():
                    self._flash_token_widget(with_reject_sound=True)
                    return

                self.play_dice_roll_sound()
                if self.has_moved_with_dice:
                    SPEED_THRESHOLD = 300
                    if self.max_speed > SPEED_THRESHOLD:
                        for dice in self.dice_list:
                            dice.set_random_frame()
                    else:
                        for dice in self.dice_list:
                            dice.set_random_frame_same_row()
                    self.has_moved_with_dice = False
                self.max_speed = 0
                self.last_touch_pos = None
                self.last_touch_time = None

                def after_glass_raise():
                    Clock.schedule_once(lambda dt: self._animate_dice_appearance(), 0.1)

                self._raise_glass(on_complete_callback=after_glass_raise)
            else:
                if self.dice_hidden or self._bet_placed_this_round:
                    self._refund_bet_if_needed()

                flash_after = (was_dice_hidden
                               and self.tokens.get_balance() <= 0
                               and not self._bet_placed_this_round)

                if self.has_moved_with_dice:
                    SPEED_THRESHOLD = 300
                    if self.max_speed > SPEED_THRESHOLD:
                        for dice in self.dice_list:
                            dice.set_random_frame()
                    else:
                        for dice in self.dice_list:
                            dice.set_random_frame_same_row()
                    self.has_moved_with_dice = False
                self.max_speed = 0
                self.last_touch_pos = None
                self.last_touch_time = None
                self._raise_glass(flash_after=flash_after)
        else:
            if self.is_dice_enlarged:
                self._cancel_drain()
                self._shrink_all_dice()
                Clock.schedule_once(lambda dt: self._process_glass_lower(), 0.4)
            else:
                self._process_glass_lower()

    def _process_glass_lower(self):
        if self.dice_list and not self.dice_hidden:
            if len(self.dice_list) == 1:
                target_dice = self.dice_list[0]
                dice_center_x = target_dice.pos[0] + target_dice.width / 2
                dice_center_y = target_dice.pos[1] + target_dice.height / 2
            else:
                total_x = 0
                total_y = 0
                for dice in self.dice_list:
                    total_x += dice.pos[0] + dice.width / 2
                    total_y += dice.pos[1] + dice.height / 2
                dice_center_x = total_x / len(self.dice_list)
                dice_center_y = total_y / len(self.dice_list)

            current_point_a_x = self.glass_start_pos[0] + self.glass_size / 6.5
            current_point_a_y = self.glass_start_pos[1] + self.glass_size / 2
            distance_x = abs(current_point_a_x - dice_center_x)
            distance_y = abs(current_point_a_y - dice_center_y)
            current_dice_size = self.single_dice_size if self.current_mode == 1 else self.double_dice_size
            max_distance_x = current_dice_size * self.MAGNETIC_DISTANCE_X_FACTOR
            max_distance_y = current_dice_size * self.MAGNETIC_DISTANCE_Y_FACTOR

            if distance_x <= max_distance_x and distance_y <= max_distance_y:
                if self.magnetic_field:
                    self.magnetic_field.stop()
                self.pending_hide_dice = True
                self._lower_glass_to_center(dice_center_x, dice_center_y)
            else:
                self._lower_glass()
        else:
            self._lower_glass()

    def _disable_glow_for_all_dice(self):
        for dice in self.dice_list:
            dice.disable_glow()

    def _on_glass_move_complete(self):
        pass

    def _on_appearance_complete(self, dice):
        self.animation_counter += 1
        if self.animation_counter >= 2:
            self.is_animating = False
            self.animation_counter = 0

    def _get_dice_center(self):
        if not self.dice_list:
            if self.last_dice_center:
                return self.last_dice_center
            center_x = self.START_POSITION_DICE_X + self.single_dice_size // 2
            center_y = self.START_POSITION_DICE_Y + self.single_dice_size // 2
            return (center_x, center_y)
        if len(self.dice_list) == 1:
            dice = self.dice_list[0]
            center = (dice.pos[0] + dice.width / 2, dice.pos[1] + dice.height / 2)
            self.last_dice_center = center
            return center
        else:
            total_x = 0
            total_y = 0
            for dice in self.dice_list:
                total_x += dice.pos[0] + dice.width / 2
                total_y += dice.pos[1] + dice.height / 2
            center = (total_x / len(self.dice_list), total_y / len(self.dice_list))
            self.last_dice_center = center
            return center

    def _create_dice_for_mode(self, mode, animate=True, sound_delay=0.15):
        self._clear_all_dice()
        self.saved_dice_positions = []
        self.dice_hidden = False
        self.pending_hide_dice = False
        self.is_dice_enlarged = False

        if not animate:
            if mode == 1:
                dice = DiceWidget(
                    sprite_sheet_path=self.sprite_sheet_path,
                    dice_size=self.single_dice_size,
                    rows=self.DICE_ROWS,
                    cols=self.DICE_COLS,
                    frame_index=0,
                    rotation_angle=-90,
                    size_hint=(None, None),
                    size=(self.single_dice_size, self.single_dice_size),
                    pos=(self.START_POSITION_DICE_X, self.START_POSITION_DICE_Y),
                    on_dice_click=self._on_dice_click
                )
                dice.set_random_frame()
                dice.original_position = dice.pos
                dice.original_size = dice.dice_size
                dice.opacity = 1
                self.layout.add_widget(dice)
                self.dice_list.append(dice)
                Clock.schedule_once(lambda dt: dice._create_glow(), 0)
            elif mode == 2:
                distance_between = self.double_dice_size * 0.3
                center_y = self.START_POSITION_DICE_Y + (self.single_dice_size // 2) - (self.double_dice_size // 2)
                y_top = center_y - distance_between
                y_bottom = center_y + distance_between

                dice1 = DiceWidget(
                    sprite_sheet_path=self.sprite_sheet_path,
                    dice_size=self.double_dice_size,
                    rows=self.DICE_ROWS,
                    cols=self.DICE_COLS,
                    frame_index=0,
                    rotation_angle=-90,
                    size_hint=(None, None),
                    size=(self.double_dice_size, self.double_dice_size),
                    pos=(self.START_POSITION_DICE_X, y_top),
                    on_dice_click=self._on_dice_click
                )
                dice1.original_position = dice1.pos
                dice1.original_size = dice1.dice_size
                dice1.opacity = 1

                dice2 = DiceWidget(
                    sprite_sheet_path=self.sprite_sheet_path,
                    dice_size=self.double_dice_size,
                    rows=self.DICE_ROWS,
                    cols=self.DICE_COLS,
                    frame_index=0,
                    rotation_angle=-90,
                    size_hint=(None, None),
                    size=(self.double_dice_size, self.double_dice_size),
                    pos=(self.START_POSITION_DICE_X, y_bottom),
                    on_dice_click=self._on_dice_click
                )
                dice2.original_position = dice2.pos
                dice2.original_size = dice2.dice_size
                dice2.opacity = 1

                dice1.set_random_frame()
                dice2.set_random_frame()
                self.layout.add_widget(dice1)
                self.layout.add_widget(dice2)
                self.dice_list.append(dice1)
                self.dice_list.append(dice2)
                Clock.schedule_once(lambda dt: dice1._create_glow(), 0)
                Clock.schedule_once(lambda dt: dice2._create_glow(), 0)

            if self.glass and self.glass.parent:
                self.layout.remove_widget(self.glass)
                self.layout.add_widget(self.glass)
            if self.drop_zone:
                Clock.schedule_once(lambda dt: self._create_magnetic_field(), 0.1)
            return

        center = self._get_dice_center()
        if mode == 1:
            target_x = center[0] - self.single_dice_size / 2
            target_y = center[1] - self.single_dice_size / 2
            start_pos = (target_x, target_y)
            dice = DiceWidget(
                sprite_sheet_path=self.sprite_sheet_path,
                dice_size=self.single_dice_size,
                rows=self.DICE_ROWS,
                cols=self.DICE_COLS,
                frame_index=0,
                rotation_angle=-90,
                size_hint=(None, None),
                size=(self.single_dice_size, self.single_dice_size),
                pos=start_pos,
                on_dice_click=self._on_dice_click
            )
            dice.set_random_frame()
            dice.opacity = 1
            self.layout.add_widget(dice)
            self.dice_list.append(dice)
            dice.animate_appearance_from_center(
                (target_x, target_y), start_pos, self.appear_duration, None, sound_delay=sound_delay)
        elif mode == 2:
            distance_between = self.double_dice_size * 0.3
            y_top = center[1] - distance_between - self.double_dice_size / 2
            y_bottom = center[1] + distance_between - self.double_dice_size / 2
            dice_x = center[0] - self.double_dice_size / 2
            start_pos = (center[0] - self.double_dice_size / 2, center[1] - self.double_dice_size / 2)

            dice1 = DiceWidget(
                sprite_sheet_path=self.sprite_sheet_path,
                dice_size=self.double_dice_size,
                rows=self.DICE_ROWS,
                cols=self.DICE_COLS,
                frame_index=0,
                rotation_angle=-90,
                size_hint=(None, None),
                size=(self.double_dice_size, self.double_dice_size),
                pos=start_pos,
                on_dice_click=self._on_dice_click
            )
            dice2 = DiceWidget(
                sprite_sheet_path=self.sprite_sheet_path,
                dice_size=self.double_dice_size,
                rows=self.DICE_ROWS,
                cols=self.DICE_COLS,
                frame_index=0,
                rotation_angle=-90,
                size_hint=(None, None),
                size=(self.double_dice_size, self.double_dice_size),
                pos=start_pos,
                on_dice_click=self._on_dice_click
            )
            self.layout.add_widget(dice1)
            self.layout.add_widget(dice2)
            self.dice_list.append(dice1)
            self.dice_list.append(dice2)
            self.is_animating = True
            self.animation_counter = 0
            Clock.schedule_once(lambda dt: dice1._create_glow(), 0)
            Clock.schedule_once(lambda dt: dice2._create_glow(), 0)

            def on_both_appear_complete(dice):
                self._on_appearance_complete(dice)
                if self.drop_zone and self.is_at_target and not self.dice_hidden:
                    Clock.schedule_once(lambda dt: self._create_magnetic_field(), 0.1)

            dice1.animate_appearance_from_center(
                (dice_x, y_top), start_pos, self.appear_duration,
                on_both_appear_complete, sound_delay=sound_delay)
            dice2.animate_appearance_from_center(
                (dice_x, y_bottom), start_pos, self.appear_duration,
                on_both_appear_complete, sound_delay=sound_delay)

        if self.glass and self.glass.parent:
            self.layout.remove_widget(self.glass)
            self.layout.add_widget(self.glass)

    def _start_switch_animation(self):
        if self.is_animating:
            return
        if self.is_dice_enlarged:
            self._shrink_all_dice()
            return
        if self.particle_system:
            self.particle_system.set_glow_mode(True)
        if self.magnetic_field:
            self.magnetic_field.stop()
        self.is_animating = True
        self._get_dice_center()
        if self.current_mode == 1:
            self._animate_one_to_two()
        else:
            self._animate_two_to_one()
        Clock.schedule_once(lambda dt: self.particle_system.set_glow_mode(False) if self.particle_system else None, 1.5)

    def _animate_one_to_two(self, sound_delay=0.4):
        if not self.dice_list:
            self.is_animating = False
            return
        self._ensure_dice_above_glass_for_animation()
        self.sound_manager.vibrate_short()
        old_dice = self.dice_list[0]
        old_dice.animate_disappear_in_place(self.disappear_duration, None, sound_delay=sound_delay)
        appear_delay = self.disappear_duration - self.overlap_time
        Clock.schedule_once(lambda dt: self._create_small_dice(sound_delay=sound_delay), appear_delay)

    def _create_small_dice(self, sound_delay=0.15):
        self._clear_all_dice()
        self.current_mode = 2
        self._create_dice_for_mode(2, animate=True, sound_delay=sound_delay)
        Clock.schedule_once(lambda dt: self._ensure_dice_above_glass_for_animation(), 0.05)

    def _animate_two_to_one(self, sound_delay=0.4):
        if len(self.dice_list) < 2:
            self.is_animating = False
            return
        self._ensure_dice_above_glass_for_animation()
        self.sound_manager.vibrate_short()
        dice_top = self.dice_list[0]
        dice_bottom = self.dice_list[1]
        center = self._get_dice_center()
        center_pos = (center[0] - self.single_dice_size / 2, center[1] - self.single_dice_size / 2)
        dice_top.animate_disappear_to_center(center_pos, self.disappear_duration, None, sound_delay=sound_delay)
        dice_bottom.animate_disappear_to_center(center_pos, self.disappear_duration, None, sound_delay=sound_delay)
        appear_delay = self.disappear_duration - self.overlap_time
        Clock.schedule_once(lambda dt: self._create_big_dice(sound_delay=sound_delay), appear_delay)

    def _create_big_dice(self, sound_delay=0.15):
        self._clear_all_dice()
        self.current_mode = 1
        self._create_dice_for_mode(1, animate=True, sound_delay=sound_delay)
        self.is_animating = False
        Clock.schedule_once(lambda dt: self._ensure_dice_above_glass_for_animation(), 0.05)

    def _clear_all_dice(self):
        for dice in self.dice_list:
            if dice.parent:
                self.layout.remove_widget(dice)
        self.dice_list.clear()

    def go_to_menu(self):
        if hasattr(self, 'contact_monitor') and self.contact_monitor:
            self.contact_monitor.cancel()
            self.contact_monitor = None
        if hasattr(self, '_animation_monitor') and self._animation_monitor:
            self._animation_monitor.cancel()
        if self.particle_system:
            self.particle_system.cleanup()
            if self.particle_system in self.layout.children:
                self.layout.remove_widget(self.particle_system)
            self.particle_system = None
        self._reset_brightness()
        if self.volume_fade_clock:
            self.volume_fade_clock.cancel()
            self.volume_fade_clock = None
        if self.sound_glass_drag:
            try:
                self.sound_glass_drag.stop()
            except:
                pass
        self._stop_dice_move_playlist()
        if self._glass_drag_silence_clock:
            self._glass_drag_silence_clock.cancel()
            self._glass_drag_silence_clock = None
        if self._bonus_clock:
            self._bonus_clock.cancel()
            self._bonus_clock = None
        self._bonus_queue = 0
        if self.magnetic_field:
            self.magnetic_field.stop()
            self.magnetic_field = None
        self._clear_all_dice()
        if self.glass and self.glass.parent:
            if hasattr(self.glass, 'color_overlay') and self.glass.color_overlay:
                try:
                    self.glass.canvas.before.remove(self.glass.color_overlay)
                except:
                    pass
            self.layout.remove_widget(self.glass)
            self.glass = None
        if self.shadow and self.shadow.parent:
            self.layout.remove_widget(self.shadow)
            self.shadow = None
        if self.drop_zone and self.drop_zone.parent:
            self.layout.remove_widget(self.drop_zone)
            self.drop_zone = None
        if self.point_a_marker and self.point_a_marker.parent:
            self.layout.remove_widget(self.point_a_marker)
            self.point_a_marker = None
        self._remove_token_widget()
        self._reset_bet_flag()
        self.sound_manager.fade_to(1.0, duration=0.5)
        from main import switch_screen
        switch_screen('menu')