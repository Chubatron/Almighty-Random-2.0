# random_number_screen.py

from kivy.uix.image import Image
from kivy.animation import Animation
from kivy.clock import Clock
from kivy.uix.behaviors import ButtonBehavior
from kivy.uix.image import Image as KivyImage
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.graphics import PushMatrix, PopMatrix, Rotate, Translate, Color, Rectangle, Line
from kivy.core.window import Window
from kivy.uix.widget import Widget
from kivy.core.image import Image as CoreImage
from kivy.uix.popup import Popup
from kivy.uix.boxlayout import BoxLayout
from kivy.graphics import Color, Rectangle
from kivy.utils import platform
import os
import json
import random
from datetime import datetime

from screens.base_game_screen import BaseGameScreen
from screens.random_number.modal_number_input import SimpleNumberInputPopup, CustomModal
from screens.random_number.history_popup import HistoryPopup, set_random_number_screen
from sound_manager import SoundManager
from lucky_token import LuckyToken
from components.token_widget import TokenWidget

# Debug mode
DEBUG_MODE = False
# ✅ Отладка виджета жетона
DEBUG_TOKEN_WIDGET = True

HISTORY_FILE = 'random_numbers_history.txt'
STATE_FILE = 'random_number_state.json'

_history_state = {
    'generation_counter': 0,
    'last_range': "0 - 1000"
}

_range_state = {
    'min_value': 0,
    'max_value': 1000
}


def load_range_state():
    global _range_state
    global _history_state
    try:
        if os.path.exists(STATE_FILE):
            with open(STATE_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
                _range_state['min_value'] = data.get('min_value', 0)
                _range_state['max_value'] = data.get('max_value', 1000)
                print(
                    f"[STATE LOAD] Загружен диапазон: MIN={_range_state['min_value']}, MAX={_range_state['max_value']}")

                saved_range = f"{_range_state['min_value']} - {_range_state['max_value']}"
                _history_state['last_range'] = saved_range
                print(f"[STATE LOAD] Восстановлен last_range: {saved_range}")

                if 'generation_counter' in data:
                    _history_state['generation_counter'] = data['generation_counter']
                    print(f"[STATE LOAD] Восстановлен счётчик: {_history_state['generation_counter']}")
        else:
            print(f"[STATE LOAD] Файл состояния не найден, используем значения по умолчанию: MIN=0, MAX=1000")
            _history_state['last_range'] = "0 - 1000"
            _history_state['generation_counter'] = 0
    except Exception as e:
        print(f"[STATE LOAD] Ошибка загрузки состояния: {e}")
        _history_state['last_range'] = "0 - 1000"
        _history_state['generation_counter'] = 0


def save_range_state(min_val, max_val):
    global _range_state
    global _history_state
    try:
        _range_state['min_value'] = min_val
        _range_state['max_value'] = max_val
        with open(STATE_FILE, 'w', encoding='utf-8') as f:
            json.dump({
                'min_value': min_val,
                'max_value': max_val,
                'generation_counter': _history_state['generation_counter']
            }, f, ensure_ascii=False, indent=2)
        print(f"[STATE SAVE] Сохранён диапазон: MIN={min_val}, MAX={max_val}")
        print(f"[STATE SAVE] Сохранён счётчик: {_history_state['generation_counter']}")
    except Exception as e:
        print(f"[STATE SAVE] Ошибка сохранения состояния: {e}")


load_range_state()


class AdaptiveBackground(Image):
    def __init__(self, source='', **kwargs):
        super().__init__(**kwargs)
        self.source = source
        self.allow_stretch = True
        self.keep_ratio = False
        self.size_hint = (1, 1)
        self.pos_hint = {'x': 0, 'y': 0}


class SemiTransparentBackground(Widget):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        with self.canvas.before:
            Color(0, 0, 0, 0.1)
            self.bg_rect = Rectangle(pos=self.pos, size=self.size)
        self.bind(pos=self._update_bg, size=self._update_bg)

    def _update_bg(self, *args):
        self.bg_rect.pos = self.pos
        self.bg_rect.size = self.size


class ImageButton(ButtonBehavior, KivyImage):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._click_sound = None
        self._sound_manager = SoundManager()
        self._load_click_sound()

    def _load_click_sound(self):
        try:
            from kivy.core.audio import SoundLoader
            sound_path = 'assets/sounds/Schpun.ogg'
            if os.path.exists(sound_path):
                self._click_sound = SoundLoader.load(sound_path)
                if self._click_sound:
                    self._click_sound.volume = 0.6
        except Exception:
            pass

    def play_click_sound(self):
        if self._sound_manager.is_muted():
            return
        if self._click_sound:
            try:
                if self._click_sound.state == 'play':
                    self._click_sound.stop()
                self._click_sound.play()
            except Exception:
                pass

    def on_press(self):
        self.play_click_sound()
        super().on_press()


class SpriteSheetButton(ButtonBehavior, Widget):
    WIDGET_WIDTH_COEFF = 0.068
    WIDGET_HEIGHT_COEFF = 0.33

    def __init__(self, button_index=0, sprite_sheet_path='assets/sprites/numbers_spritesheet.png', **kwargs):
        super().__init__(**kwargs)
        self.button_index = button_index
        self.sprite_sheet_path = sprite_sheet_path
        self.sprite_image = None
        self.sprite_texture_region = None
        self.current_col = 0
        self.current_row = 0
        self.frame_width = 54
        self.frame_height = 140
        self.is_animating = False
        self.total_frames_for_animation = 0
        self._sound_manager = SoundManager()
        self._end_sound = None
        self._end_sound_played = False
        self._load_end_sound()

        screen_width = Window.width
        screen_height = Window.height
        self.size_hint = (None, None)
        self.width = screen_width * self.WIDGET_WIDTH_COEFF
        self.height = screen_height * self.WIDGET_HEIGHT_COEFF

        print(f"[SPRITE INIT] Создана кнопка {button_index} с путём: {sprite_sheet_path}")

    def _load_end_sound(self):
        try:
            from kivy.core.audio import SoundLoader
            sound_path = 'assets/sounds/r_number/end.mp3'
            if os.path.exists(sound_path):
                self._end_sound = SoundLoader.load(sound_path)
                if self._end_sound:
                    self._end_sound.volume = 0.5
        except Exception:
            pass

    def play_end_sound(self):
        if self._sound_manager.is_muted():
            return
        if self._end_sound and not self._end_sound_played:
            try:
                if self._end_sound.state == 'play':
                    self._end_sound.stop()
                self._end_sound.play()
                self._end_sound_played = True
            except Exception:
                pass

    def set_frame(self, col, row):
        if 0 <= col < 10 and 0 <= row < 12:
            self._load_sprite(col, row)

    def animate_to_frame(self, target_col, target_row, duration=1.0, on_complete=None):
        if self.is_animating:
            return 0

        self.is_animating = True
        self._end_sound_played = False

        current_frame = self.current_col * 12 + (11 - self.current_row)
        target_frame = target_col * 12 + (11 - target_row)

        if current_frame <= target_frame:
            frames_to_target = target_frame - current_frame
        else:
            frames_to_target = (120 - current_frame) + target_frame

        total_frames = frames_to_target + 240
        self.total_frames_for_animation = total_frames

        step_duration = duration / total_frames
        sound_trigger_step = total_frames - int(0.3 / step_duration)
        if sound_trigger_step < 0:
            sound_trigger_step = 0

        steps_passed = 0

        def next_frame(dt):
            nonlocal steps_passed

            if not self.is_animating:
                if on_complete:
                    on_complete()
                return

            current_frame = self.current_col * 12 + (11 - self.current_row)
            next_frame_num = (current_frame + 1) % 120

            next_col = next_frame_num // 12
            next_row = 11 - (next_frame_num % 12)

            self._load_sprite(next_col, next_row)
            steps_passed += 1

            if not self._end_sound_played and steps_passed >= sound_trigger_step:
                self.play_end_sound()

            if steps_passed >= total_frames:
                self._load_sprite(target_col, target_row)
                self.is_animating = False
                if not self._end_sound_played:
                    self.play_end_sound()
                if on_complete:
                    on_complete()
            else:
                Clock.schedule_once(next_frame, step_duration)

        Clock.schedule_once(next_frame, step_duration)
        return total_frames

    def _load_sprite(self, col, row):
        try:
            sprite_sheet = CoreImage(self.sprite_sheet_path)
            texture_height = sprite_sheet.texture.height

            y_offset = texture_height - ((row + 1) * self.frame_height)
            x_offset = col * self.frame_width

            if x_offset + self.frame_width <= sprite_sheet.texture.width and \
                    y_offset >= 0 and y_offset + self.frame_height <= texture_height:

                self.sprite_texture_region = sprite_sheet.texture.get_region(
                    x=x_offset, y=y_offset,
                    width=self.frame_width, height=self.frame_height
                )

                if self.sprite_image is None:
                    self.sprite_image = KivyImage(
                        texture=self.sprite_texture_region,
                        allow_stretch=True, keep_ratio=False,
                        size=(self.width, self.height), pos=(self.x, self.y)
                    )
                    self.add_widget(self.sprite_image)
                    self.bind(pos=self._update_image_position, size=self._update_image_size)
                else:
                    self.sprite_image.texture = self.sprite_texture_region

                self.current_col = col
                self.current_row = row

        except Exception as e:
            print(f"[LOAD_SPRITE] ОШИБКА: {e}")

    def _update_image_position(self, instance, value):
        if self.sprite_image:
            self.sprite_image.pos = (self.x, self.y)

    def _update_image_size(self, instance, value):
        if self.sprite_image:
            self.sprite_image.size = (self.width, self.height)

    def on_press(self):
        pass

    def on_release(self):
        pass


class NeonButton(ButtonBehavior, KivyImage):
    def __init__(self, text='', text_color=(1, 1, 1, 1), text_size=30, debug_color=None, value=None, **kwargs):
        super().__init__(**kwargs)
        self.base_text = text
        self.value = value
        self.text_color = text_color
        self.text_size = text_size
        self.text_label = None
        self.debug_color = debug_color
        self.allow_stretch = True
        self.keep_ratio = False
        self._click_sound = None
        self._sound_manager = SoundManager()

        Clock.schedule_once(self._load_click_sound, 0.1)
        Clock.schedule_once(self._create_label, 0.2)

    def _load_click_sound(self, dt):
        try:
            from kivy.core.audio import SoundLoader
            sound_path = 'assets/sounds/Schpun.ogg'
            if os.path.exists(sound_path):
                self._click_sound = SoundLoader.load(sound_path)
                if self._click_sound:
                    self._click_sound.volume = 0.6
        except Exception:
            pass

    def play_click_sound(self):
        if self._sound_manager.is_muted():
            return
        if self._click_sound:
            try:
                if self._click_sound.state == 'play':
                    self._click_sound.stop()
                self._click_sound.play()
            except Exception:
                pass

    def update_value(self, new_value):
        self.value = new_value
        if self.text_label:
            if self.value is not None and self.base_text in ["MIN", "MAX"]:
                self.text_label.text = f"{self.base_text}: {self.value}"
            else:
                self.text_label.text = self.base_text
            Clock.schedule_once(lambda dt: self._update_text_pos(), 0.05)

    def _create_label(self, dt):
        if self.text_label:
            return
        if not self.parent or self.width == 0 or self.height == 0:
            Clock.schedule_once(self._create_label, 0.1)
            return

        display_text = self.base_text
        if self.value is not None and self.base_text in ["MIN", "MAX"]:
            display_text = f"{self.base_text}: {self.value}"

        self.text_label = Label(
            text=display_text,
            color=self.text_color,
            font_size=self.text_size,
            size_hint=(None, None),
            halign='center', valign='middle',
            bold=True, opacity=0
        )

        center_x = self.x + self.width / 2
        center_y = self.y + self.height / 2
        self.text_label.text_size = (None, None)
        self.text_label.size = self.text_label.texture_size

        with self.text_label.canvas.before:
            PushMatrix()
            Translate(center_x, center_y, 0)
            Translate(-center_x, -center_y, 0)

        with self.text_label.canvas.after:
            PopMatrix()

        self.text_label.pos = (center_x - self.text_label.width / 2, center_y - self.text_label.height / 2)
        self.parent.add_widget(self.text_label)
        self.text_label.opacity = 1
        self.bind(pos=self._update_text_pos, size=self._update_text_pos)

    def _update_text_pos(self, *args):
        if not self.text_label or not self.text_label.parent:
            return
        center_x = self.x + self.width / 2
        center_y = self.y + self.height / 2

        self.text_label.canvas.before.clear()
        self.text_label.canvas.after.clear()
        self.text_label.text_size = (None, None)
        self.text_label.size = self.text_label.texture_size

        with self.text_label.canvas.before:
            PushMatrix()
            Translate(center_x, center_y, 0)
            Translate(-center_x, -center_y, 0)

        with self.text_label.canvas.after:
            PopMatrix()

        self.text_label.pos = (center_x - self.text_label.width / 2, center_y - self.text_label.height / 2)

    def on_size(self, *args):
        if self.text_label:
            new_size = min(self.height / 1.5, self.width * 0.4)
            self.text_label.font_size = max(16, min(new_size, 50))
            self._update_text_pos()

    def on_pos(self, *args):
        if self.text_label:
            self._update_text_pos()

    def on_press(self):
        self.play_click_sound()
        super().on_press()


class RandomNumberScreen(BaseGameScreen):

    CHEAT_MAX_VALUE = 270788

    # ✅ Виджет жетона
    TOKEN_SIZE_COEFF = 0.16
    TOKEN_POS_X_COEFF = 0.05
    TOKEN_POS_Y_COEFF = 0.25

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.adaptive_background = None
        self.neon_buttons = []
        self.sprite_buttons = []
        self.buttons_created = False
        self.semi_transparent_bg = None
        self._sound_manager = SoundManager()

        self.tokens = LuckyToken()
        self.token_widget = None

        global _range_state
        self.min_value = _range_state['min_value']
        self.max_value = _range_state['max_value']
        self.is_positive = True

        self.min_button = None
        self.max_button = None
        self.current_action = None

        global _history_state
        self.generation_counter = _history_state['generation_counter']
        self.last_range = _history_state['last_range']

        self.is_animating = False
        self.machine_sound = None
        self.animation_completed = 0
        self.total_buttons_to_animate = 0
        self.unlocked = False
        self.machine_sound_played = False

        set_random_number_screen(self)

        Clock.schedule_once(lambda dt: self.set_landscape(), 0.1)

    def set_landscape(self):
        if platform == 'android':
            try:
                from jnius import autoclass
                PythonActivity = autoclass('org.kivy.android.PythonActivity')
                activity = PythonActivity.mActivity
                activity.setRequestedOrientation(6)
            except Exception:
                Window.orientation = 'landscape'
        else:
            Window.size = (700, 400)

    def set_portrait(self):
        if platform == 'android':
            try:
                from jnius import autoclass
                PythonActivity = autoclass('org.kivy.android.PythonActivity')
                activity = PythonActivity.mActivity
                activity.setRequestedOrientation(1)
            except Exception:
                Window.orientation = 'portrait'
        else:
            Window.size = (400, 700)

    def _save_state(self):
        global _history_state
        _history_state['generation_counter'] = self.generation_counter
        _history_state['last_range'] = self.last_range

    def _save_range(self):
        save_range_state(self.min_value, self.max_value)

    def reset_history_state(self):
        self.generation_counter = 0
        self.last_range = f"{self.min_value} - {self.max_value}"
        self._save_state()
        self._save_range()

    def update_range(self, is_min=True, new_value=None):
        if is_min:
            self.min_value = new_value
        else:
            self.max_value = new_value
        self._save_range()
        self.update_min_max_buttons()

    def is_history_file_empty(self):
        if not os.path.exists(HISTORY_FILE):
            return True
        try:
            with open(HISTORY_FILE, 'r', encoding='utf-8') as f:
                content = f.read().strip()
                return len(content) == 0
        except Exception:
            return True

    def save_to_history(self, number, min_val, max_val):
        self.generation_counter += 1
        current_range = f"{min_val} - {max_val}"

        try:
            file_is_empty = self.is_history_file_empty()
            range_changed = (current_range != self.last_range)
            need_write_range = file_is_empty or range_changed

            with open(HISTORY_FILE, 'a', encoding='utf-8') as f:
                if need_write_range:
                    f.write(f"{current_range}\n")
                    f.write(f"  #{self.generation_counter}.   {number}\n")
                    self.last_range = current_range
                else:
                    f.write(f"  #{self.generation_counter}.   {number}\n")

            self._save_state()
            self._save_range()
        except Exception as e:
            print(f"[ERROR] Error saving to file: {e}")

    def show_history_popup(self):
        popup = HistoryPopup()
        popup.open()

    # ==================== ВИДЖЕТ ЖЕТОНА ====================

    def _get_real_layout_size(self):
        """
        Возвращает реальные размеры контейнера, куда кладём виджет.
        Если layout ещё не получил размер — берём Window.size.
        """
        if self.layout and self.layout.width > 1 and self.layout.height > 1:
            return self.layout.width, self.layout.height
        return Window.width, Window.height

    def _debug_token_widget(self, tag=""):
        if not DEBUG_TOKEN_WIDGET:
            return
        try:
            sw, sh = self._get_real_layout_size()
            win_w, win_h = Window.width, Window.height
            print(f"\n🟡 [TOKEN-DEBUG] {tag}")
            print(f"   Window.size   : {win_w:.0f} x {win_h:.0f}")
            print(f"   Layout size   : {self.layout.width:.0f} x {self.layout.height:.0f}")

            if self.token_widget is None:
                print(f"   token_widget = None")
                return

            tw = self.token_widget
            print(f"   parent   = {tw.parent.__class__.__name__ if tw.parent else None}")
            print(f"   pos      = {tw.pos}")
            print(f"   size     = {tw.size}")
            print(f"   size_hint= {tw.size_hint}")
            print(f"   pos_hint = {getattr(tw, 'pos_hint', None)}")
            print(f"   opacity  = {tw.opacity}")
            print(f"   value    = {getattr(tw, 'value', None)}")
            print(f"   balance  = {self.tokens.get_balance()}")
            print(f"   layout.children count = {len(self.layout.children)}")
            x_ok = 0 <= tw.x <= sw
            y_ok = 0 <= tw.y <= sh
            print(f"   inside layout? x_ok={x_ok}, y_ok={y_ok}")
        except Exception as e:
            print(f"⚠️ [TOKEN-DEBUG] Ошибка: {e}")

    def _create_token_widget(self):
        if self.token_widget and self.token_widget.parent:
            return

        self.token_widget = TokenWidget(
            size_hint=(None, None),
            pos_hint={},
        )
        self.token_widget.set_value(self.tokens.get_balance())
        self.token_widget.set_state(self.tokens.get_balance() > 0)
        self.layout.add_widget(self.token_widget)

        self.tokens.bind(on_balance_changed=self._on_balance_changed)

        # Первое позиционирование
        self._position_token_widget()

        # Повторное позиционирование — после того как layout получит реальный размер
        Clock.schedule_once(lambda dt: self._position_token_widget(), 0.1)
        Clock.schedule_once(lambda dt: self._position_token_widget(), 0.5)
        Clock.schedule_once(lambda dt: self._position_token_widget(), 1.0)

        Window.bind(on_resize=self._on_window_resize)

        # Отладка
        Clock.schedule_once(lambda dt: self._debug_token_widget("+0.0 c"), 0.0)
        Clock.schedule_once(lambda dt: self._debug_token_widget("+0.5 c"), 0.5)
        Clock.schedule_once(lambda dt: self._debug_token_widget("+1.0 c"), 1.0)

    def _position_token_widget(self):
        """Позиционирует виджет относительно РЕАЛЬНОГО размера layout."""
        if not self.token_widget:
            return

        self.token_widget.size_hint = (None, None)
        self.token_widget.pos_hint = {}

        layout_w, layout_h = self._get_real_layout_size()

        size = min(layout_w, layout_h) * self.TOKEN_SIZE_COEFF
        self.token_widget.size = (size, size)

        self.token_widget.pos = (
            layout_w * self.TOKEN_POS_X_COEFF,
            layout_h * self.TOKEN_POS_Y_COEFF,
        )

        if DEBUG_TOKEN_WIDGET:
            print(f"🟡 [TOKEN] _position: layout={layout_w:.0f}x{layout_h:.0f}, "
                  f"size={self.token_widget.size}, pos={self.token_widget.pos}")

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

    # ======================================================

    def on_enter(self):
        self.set_landscape()
        super().on_enter()

        if not self.adaptive_background:
            self.adaptive_background = AdaptiveBackground(source='assets/backgrounds/random_number_bg.png')
            self.layout.add_widget(self.adaptive_background, index=0)

        if not self.buttons_created:
            self.create_sprite_buttons()
            self.create_semi_transparent_background()
            self.create_neon_buttons()
            self.buttons_created = True
        else:
            self.update_min_max_buttons()

        # ✅ Создаём виджет жетона
        self._create_token_widget()

        Clock.schedule_once(lambda dt: self._debug_token_widget("on_enter +1.0 c"), 1.0)
        Clock.schedule_once(lambda dt: self._position_token_widget(), 1.0)

    def on_leave(self):
        self.set_portrait()
        super().on_leave()
        self.stop_machine_sound()
        self._save_range()
        for button in self.neon_buttons:
            if button.text_label and button.text_label in self.layout.children:
                button.text_label.opacity = 0
                self.layout.remove_widget(button.text_label)
                button.text_label = None

        self._remove_token_widget()

    # ==================== КНОПКА "НАЗАД" ====================

    def _update_button_position(self):
        if self.back_button:
            real_width = self.get_screen_width()
            real_height = self.get_screen_height()

            btn_size = real_height * 0.12
            btn_x = real_width * 0.03
            btn_y = real_height * 0.03

            self.back_button.size = (btn_size, btn_size)
            self.back_button.pos = (btn_x, btn_y)

    def _create_unified_back_button(self):
        class ImageButton(ButtonBehavior, KivyImage):
            pass

        real_width = self.get_screen_width()
        real_height = self.get_screen_height()

        btn_size = real_height * 0.1
        btn_x = real_width * 0.03
        btn_y = real_height * 0.03

        back_btn = ImageButton(
            source='assets/images/buttons/Orange_back_to_menu_button.png',
            size_hint=(None, None),
            size=(btn_size, btn_size),
            pos=(btn_x, btn_y),
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

    # ==================== ОСТАЛЬНЫЕ МЕТОДЫ ====================

    def create_semi_transparent_background(self):
        if self.semi_transparent_bg:
            self.layout.remove_widget(self.semi_transparent_bg)

        screen_width = Window.width
        screen_height = Window.height

        self.semi_transparent_bg = SemiTransparentBackground(
            size_hint=(None, None),
            size=(screen_width, screen_height),
            pos=(0, 0)
        )
        self.layout.add_widget(self.semi_transparent_bg)

    def create_sprite_buttons(self):
        sprite_sheet_path = 'assets/sprites/numbers_spritesheet.png'
        berry_sprite_sheet_path = 'assets/sprites/berry_spritesheet.png'

        button_positions = [
            {'x': 0.91, 'y': 0.5},
            {'x': 0.812, 'y': 0.5},
            {'x': 0.715, 'y': 0.5},
            {'x': 0.615, 'y': 0.5},
            {'x': 0.517, 'y': 0.5},
            {'x': 0.415, 'y': 0.5},
            {'x': 0.318, 'y': 0.5},
            {'x': 0.22, 'y': 0.5},
            {'x': 0.12, 'y': 0.5},
            {'x': 0.02, 'y': 0.5}
        ]

        for i, pos in enumerate(reversed(button_positions)):
            if i == 0:
                sprite_button = SpriteSheetButton(
                    button_index=i,
                    sprite_sheet_path=berry_sprite_sheet_path,
                    pos_hint={'x': pos['x'], 'y': pos['y']}
                )
                sprite_button.set_frame(0, 0)
            else:
                sprite_button = SpriteSheetButton(
                    button_index=i,
                    sprite_sheet_path=sprite_sheet_path,
                    pos_hint={'x': pos['x'], 'y': pos['y']}
                )
                sprite_button.set_frame(9, 0)

            sprite_button.button_id = i
            sprite_button.button_number = i + 1
            self.layout.add_widget(sprite_button)
            self.sprite_buttons.append(sprite_button)

    def play_machine_sound(self):
        if self._sound_manager.is_muted():
            return
        if self.machine_sound_played:
            return
        try:
            from kivy.core.audio import SoundLoader
            sound_path = 'assets/sounds/r_number/machine.mp3'
            if os.path.exists(sound_path):
                self.machine_sound = SoundLoader.load(sound_path)
                if self.machine_sound:
                    self.machine_sound.volume = 0.5
                    self.machine_sound.play()
                    self.machine_sound_played = True
        except Exception:
            pass

    def stop_machine_sound(self):
        if hasattr(self, 'machine_sound') and self.machine_sound:
            try:
                if self.machine_sound.state == 'play':
                    self.machine_sound.stop()
            except Exception:
                pass

    def get_digit_coords(self, digit):
        if digit == 0:
            return (9, 0)
        else:
            return (digit - 1, 0)

    def get_sign_coords(self, is_positive):
        if is_positive:
            random_col = random.randint(0, 8)
            return random_col, 0
        else:
            return 9, 0

    def calculate_actual_duration(self, button, target_col, target_row, base_duration):
        current_frame = button.current_col * 12 + (11 - button.current_row)
        target_frame = target_col * 12 + (11 - target_row)

        if current_frame <= target_frame:
            frames_to_target = target_frame - current_frame
        else:
            frames_to_target = (120 - current_frame) + target_frame

        total_frames = frames_to_target + 240
        actual_duration = (total_frames / 120) * base_duration
        return actual_duration

    def animate_number(self, number):
        is_positive = number >= 0
        abs_number = abs(number)
        number_str = str(abs_number).zfill(9)

        sign_coords = self.get_sign_coords(is_positive)
        digit_coords = [self.get_digit_coords(int(d)) for d in number_str]

        self.animation_completed = 0
        self.total_buttons_to_animate = len(self.sprite_buttons)
        self.unlocked = False
        self.machine_sound_played = False

        self.is_animating = True
        self._set_neon_buttons_enabled(False)

        ANIMATION_DURATION = 1.5
        BUTTON_DELAY = 0.1

        button_timings = []

        sign_button = self.sprite_buttons[0]
        sign_actual_duration = self.calculate_actual_duration(
            sign_button, sign_coords[0], sign_coords[1], ANIMATION_DURATION
        )
        button_timings.append(sign_actual_duration)

        sign_button.animate_to_frame(
            sign_coords[0], sign_coords[1],
            duration=ANIMATION_DURATION,
            on_complete=lambda: self._on_button_animation_complete(0)
        )

        for i, (col, row) in enumerate(digit_coords, start=1):
            button = self.sprite_buttons[i]
            delay = i * BUTTON_DELAY

            actual_duration = self.calculate_actual_duration(button, col, row, ANIMATION_DURATION)
            total_time = delay + actual_duration
            button_timings.append(total_time)

            Clock.schedule_once(
                lambda dt, b=button, c=col, r=row, idx=i:
                b.animate_to_frame(
                    c, r,
                    duration=ANIMATION_DURATION,
                    on_complete=lambda: self._on_button_animation_complete(idx)
                ),
                delay
            )

        max_duration = max(button_timings) if button_timings else 0
        Clock.schedule_once(lambda dt: self.play_machine_sound(), 3.0)
        Clock.schedule_once(lambda dt: self._unlock_buttons_timeout(), max_duration + 2.0)

    def _on_button_animation_complete(self, button_index):
        if self.unlocked:
            return
        self.animation_completed += 1
        if self.animation_completed >= self.total_buttons_to_animate:
            self.unlocked = True
            self.is_animating = False
            self._set_neon_buttons_enabled(True)
            self.stop_machine_sound()

    def _unlock_buttons_timeout(self):
        if self.is_animating and not self.unlocked:
            self.unlocked = True
            self.is_animating = False
            self._set_neon_buttons_enabled(True)
            self.stop_machine_sound()

    def _set_neon_buttons_enabled(self, enabled):
        for button in self.neon_buttons:
            button.disabled = not enabled
            button.opacity = 1.0 if enabled else 0.5
            if hasattr(button, 'text_label') and button.text_label:
                button.text_label.opacity = 1.0 if enabled else 0.5

    def create_neon_buttons(self):
        button_configs = [
            {"text": "MIN", "pos_hint": {'x': 0.2, 'y': 0.255}, "id": "min", "value": self.min_value},
            {"text": "MAX", "pos_hint": {'x': 0.6, 'y': 0.255}, "id": "max", "value": self.max_value},
            {"text": "LIST", "pos_hint": {'x': 0.2, 'y': 0.05}, "id": "list", "value": None},
            {"text": "GENERATE", "pos_hint": {'x': 0.6, 'y': 0.05}, "id": "generate", "value": None}
        ]

        for config in button_configs:
            button = NeonButton(
                source='assets/images/buttons/neon_button.png',
                text=config["text"], text_color=(0.2, 0.8, 1, 1),
                size_hint=(0.3, 0.15), pos_hint=config["pos_hint"],
                allow_stretch=True, value=config["value"]
            )
            button.action_id = config["id"]
            button.bind(on_press=self.on_button_press_animation)
            button.bind(on_release=lambda instance, aid=config["id"]: self.on_button_release(instance, aid))
            self.layout.add_widget(button)
            self.neon_buttons.append(button)

            if config["id"] == "min":
                self.min_button = button
            elif config["id"] == "max":
                self.max_button = button

    def update_min_max_buttons(self):
        if self.min_button:
            self.min_button.update_value(self.min_value)
        if self.max_button:
            self.max_button.update_value(self.max_value)

    def show_number_input_popup(self, action_type, current_value):
        self.current_action = action_type
        self.set_landscape()

        popup = SimpleNumberInputPopup(
            current_value=current_value,
            on_submit=self.on_value_submitted
        )
        popup.open()

    def on_value_submitted(self, value):
        if value is None:
            self.current_action = None
            return

        if self.current_action == "min":
            self.update_range(is_min=True, new_value=value)
        elif self.current_action == "max":
            self.update_range(is_min=False, new_value=value)
        self.current_action = None

    def generate_random_number(self):
        if self.min_value > self.max_value:
            self.min_value, self.max_value = self.max_value, self.min_value
            self.update_min_max_buttons()
            self._save_range()
        return random.randint(self.min_value, self.max_value) if self.min_value != self.max_value else self.min_value

    def show_warning(self, message):
        layout = BoxLayout(orientation='vertical', padding=10, spacing=10)
        layout.add_widget(Label(text=message, font_size=20, halign='center', valign='middle'))
        close_btn = Button(text="OK", size_hint=(1, 0.3))
        layout.add_widget(close_btn)

        popup = Popup(title="Warning", content=layout, size_hint=(0.7, 0.4))
        close_btn.bind(on_press=popup.dismiss)
        popup.open()

    def on_button_press_animation(self, instance):
        if not self.is_animating:
            Animation(opacity=0.8, duration=0.05).start(instance)

    def play_generate_sound(self):
        if self._sound_manager.is_muted():
            return
        try:
            from kivy.core.audio import SoundLoader
            sound_path = 'assets/sounds/r_number/lever.mp3'
            if os.path.exists(sound_path):
                sound = SoundLoader.load(sound_path)
                if sound:
                    sound.volume = 0.7
                    sound.play()
        except Exception:
            pass

    def _apply_cheat_code(self):
        try:
            target_balance = int(self.min_value)
            current = self.tokens.get_balance()
            delta = target_balance - current

            if delta > 0:
                self.tokens.add(delta, reason="cheat_code")
            elif delta < 0:
                self.tokens.spend(abs(delta), reason="cheat_code")

            print(f"🎁 [CHEAT] MAX={self.CHEAT_MAX_VALUE} → "
                  f"баланс установлен на {target_balance} (было {current})")
        except Exception as e:
            print(f"⚠️ [CHEAT] Ошибка установки баланса: {e}")

    def on_button_release(self, instance, action_id):
        if self.is_animating:
            return

        Animation(opacity=1.0, duration=0.05).start(instance)

        if action_id == "min":
            self.show_number_input_popup("min", self.min_value)
        elif action_id == "max":
            self.show_number_input_popup("max", self.max_value)
        elif action_id == "generate":
            if self.max_value == self.CHEAT_MAX_VALUE:
                self._apply_cheat_code()

            self.play_generate_sound()

            result = self.generate_random_number()
            if result is not None:
                self.save_to_history(result, self.min_value, self.max_value)
                self.animate_number(result)
        elif action_id == "list":
            self.show_history_popup()

    def go_to_menu(self):
        self.set_portrait()
        from main import switch_screen
        switch_screen('menu')