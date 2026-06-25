# random_number_screen.py

from kivy.uix.image import Image
from kivy.animation import Animation
from kivy.clock import Clock
from kivy.uix.behaviors import ButtonBehavior
from kivy.uix.image import Image as KivyImage
from kivy.uix.label import Label
from kivy.uix.textinput import TextInput
from kivy.uix.button import Button
from kivy.graphics import PushMatrix, PopMatrix, Rotate, Translate, Color, Rectangle, Line
from kivy.core.window import Window
from kivy.uix.widget import Widget
from kivy.core.image import Image as CoreImage
from kivy.uix.popup import Popup
from kivy.uix.boxlayout import BoxLayout
from kivy.graphics import Color, Rectangle
import os
import json
import random
from datetime import datetime

from screens.base_game_screen import BaseGameScreen
from screens.random_number.modal_number_input import SimpleNumberInputPopup, CustomModal
from screens.random_number.history_popup import HistoryPopup, set_random_number_screen
from sound_manager import SoundManager

# Debug mode
DEBUG_MODE = False

# History file
HISTORY_FILE = 'random_numbers_history.txt'

# State file for saving MIN/MAX between sessions
STATE_FILE = 'random_number_state.json'

# Глобальное состояние
_history_state = {
    'generation_counter': 0,
    'last_range': "0 - 1000"  # Инициализируем значением по умолчанию
}

# Глобальное состояние для MIN/MAX
_range_state = {
    'min_value': 0,
    'max_value': 1000
}


def load_range_state():
    """Загружает сохранённый диапазон из файла"""
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

                # Восстанавливаем последний диапазон из сохранённого
                saved_range = f"{_range_state['min_value']} - {_range_state['max_value']}"
                _history_state['last_range'] = saved_range
                print(f"[STATE LOAD] Восстановлен last_range: {saved_range}")

                # Загружаем счётчик
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
    """Сохраняет диапазон в файл"""
    global _range_state
    global _history_state
    try:
        _range_state['min_value'] = min_val
        _range_state['max_value'] = max_val
        # Сохраняем также счётчик
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


# Загружаем состояние при импорте модуля
load_range_state()


class AdaptiveBackground(Image):
    """Adaptive background - stretches to full screen"""

    def __init__(self, source='', **kwargs):
        super().__init__(**kwargs)
        self.source = source
        self.allow_stretch = True
        self.keep_ratio = False
        self.size_hint = (1, 1)
        self.pos_hint = {'x': 0, 'y': 0}


class SemiTransparentBackground(Widget):
    """Полупрозрачный фон для кнопок управления"""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        with self.canvas.before:
            Color(0, 0, 0, 0.1)  # Черный с прозрачностью 10%
            self.bg_rect = Rectangle(pos=self.pos, size=self.size)
        self.bind(pos=self._update_bg, size=self._update_bg)

    def _update_bg(self, *args):
        self.bg_rect.pos = self.pos
        self.bg_rect.size = self.size


class ImageButton(ButtonBehavior, KivyImage):
    """Button with image"""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._click_sound = None
        self._sound_manager = SoundManager()
        self._load_click_sound()

    def _load_click_sound(self):
        """Загружает звук нажатия кнопки"""
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
        """Воспроизводит звук нажатия кнопки (проверяет mute)"""
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
        """При нажатии воспроизводим звук"""
        self.play_click_sound()
        super().on_press()


class SpriteSheetButton(ButtonBehavior, Widget):
    """Button with image from spritesheet - НЕ РЕАГИРУЕТ НА НАЖАТИЯ"""

    # Коэффициенты для размера виджета относительно экрана
    WIDGET_WIDTH_COEFF = 0.33
    WIDGET_HEIGHT_COEFF = 0.068

    def __init__(self, button_index=0, sprite_sheet_path='assets/sprites/numbers_spritesheet.png', **kwargs):
        super().__init__(**kwargs)
        self.button_index = button_index
        self.sprite_sheet_path = sprite_sheet_path
        self.sprite_image = None
        self.sprite_texture_region = None
        self.current_frame = 0
        self.total_frames = 120
        self.rows = 10
        self.cols = 12
        self.is_animating = False
        self.frame_width = 140  # Фиксированный размер кадра из спрайтлиста
        self.frame_height = 54  # Фиксированный размер кадра из спрайтлиста
        self._is_spinning = False
        self.debug_border = None

        # Устанавливаем размер виджета относительно экрана
        screen_width = Window.width
        screen_height = Window.height
        self.size_hint = (None, None)
        self.width = screen_width * self.WIDGET_WIDTH_COEFF
        self.height = screen_height * self.WIDGET_HEIGHT_COEFF

        Clock.schedule_once(lambda dt: self._load_sprite(0), 0.1)
        Clock.schedule_once(lambda dt: self._add_debug_border(), 0.2)

    def _add_debug_border(self):
        """Добавляет отладочную рамку вокруг кнопки"""
        if DEBUG_MODE:
            with self.canvas.after:
                Color(1, 0, 0, 0.8)  # Красная рамка
                self.debug_border = Line(
                    rectangle=(self.x, self.y, self.width, self.height),
                    width=1
                )
            self.bind(pos=self._update_debug_border, size=self._update_debug_border)
            print(f"[DEBUG] Добавлена рамка для кнопки {self.button_index + 1}")

    def _update_debug_border(self, *args):
        """Обновляет позицию рамки"""
        if self.debug_border:
            self.debug_border.rectangle = (self.x, self.y, self.width, self.height)

    def _load_sprite(self, frame_index):
        try:
            sprite_sheet = CoreImage(self.sprite_sheet_path)
            texture_height = sprite_sheet.texture.height
            row = frame_index // self.cols
            col = frame_index % self.cols
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
        except Exception as e:
            if DEBUG_MODE:
                print(f"❌ Sprite loading error: {e}")

    def set_frame(self, frame_index):
        if 0 <= frame_index < self.total_frames:
            self.current_frame = frame_index
            self._load_sprite(frame_index)

    def get_row_start_frame(self, row):
        return row * self.cols

    def animate_spin(self, target_row, duration=0.8, on_complete=None):
        if self._is_spinning:
            return

        self._is_spinning = True
        target_frame = target_row * self.cols
        start_frame = self.current_frame

        if start_frame <= target_frame:
            frames_to_pass = target_frame - start_frame
        else:
            frames_to_pass = (self.total_frames - start_frame) + target_frame

        frames_to_pass += self.total_frames
        step_duration = duration / frames_to_pass

        def next_frame(dt):
            if not self._is_spinning:
                return
            self.current_frame = (self.current_frame + 1) % self.total_frames
            self._load_sprite(self.current_frame)

            if self.current_frame == target_frame:
                self._is_spinning = False
                if on_complete:
                    on_complete()
            else:
                Clock.schedule_once(next_frame, step_duration)

        Clock.schedule_once(next_frame, step_duration)

    def _update_image_position(self, instance, value):
        if self.sprite_image:
            self.sprite_image.pos = (self.x, self.y)

    def _update_image_size(self, instance, value):
        if self.sprite_image:
            self.sprite_image.size = (self.width, self.height)

    # ===== ЗАГЛУШКА - кнопка НЕ РЕАГИРУЕТ на нажатия =====
    def on_press(self):
        """Заглушка - кнопка не реагирует на нажатие"""
        pass  # Ничего не делаем

    def on_release(self):
        """Заглушка - кнопка не реагирует на отпускание"""
        pass  # Ничего не делаем


class NeonButton(ButtonBehavior, KivyImage):
    """Neon button with vertical text overlay"""

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
        """Загружает звук нажатия кнопки"""
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
        """Воспроизводит звук нажатия кнопки (проверяет mute)"""
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
            Rotate(angle=270, origin=(0, 0))
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
            Rotate(angle=270, origin=(0, 0))
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
        """При нажатии воспроизводим звук"""
        self.play_click_sound()
        super().on_press()


class RandomNumberScreen(BaseGameScreen):
    """Random number generation screen"""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.adaptive_background = None
        self.neon_buttons = []
        self.sprite_buttons = []
        self.buttons_created = False
        self.semi_transparent_bg = None  # Полупрозрачный фон
        self._sound_manager = SoundManager()

        # Загружаем MIN/MAX из глобального состояния
        global _range_state
        self.min_value = _range_state['min_value']
        self.max_value = _range_state['max_value']
        self.is_positive = True

        self.min_button = None
        self.max_button = None
        self.current_action = None

        # Загружаем состояние истории из глобальной переменной
        global _history_state
        self.generation_counter = _history_state['generation_counter']
        self.last_range = _history_state['last_range']

        # Флаг блокировки кнопок во время анимации
        self.is_animating = False

        # Звук машины
        self.machine_sound = None

        # Регистрируем себя для сброса счётчика из HistoryPopup
        set_random_number_screen(self)
        print(f"[INIT] RandomNumberScreen зарегистрирован в HistoryPopup")
        print(f"[INIT] Загружено состояние: generation_counter={self.generation_counter}")
        print(f"[INIT] last_range={self.last_range}")
        print(f"[INIT] Текущий MIN={self.min_value}, MAX={self.max_value}")

    def _save_state(self):
        """Сохраняет текущее состояние в глобальную переменную"""
        global _history_state
        _history_state['generation_counter'] = self.generation_counter
        _history_state['last_range'] = self.last_range
        print(f"[STATE] Сохранено состояние: generation_counter={self.generation_counter}")
        print(f"[STATE] last_range={self.last_range}")

    def _save_range(self):
        """Сохраняет текущий диапазон и счётчик в файл"""
        save_range_state(self.min_value, self.max_value)

    def reset_history_state(self):
        """Сбрасывает состояние истории - вызывается ТОЛЬКО при нажатии CLEAR"""
        self.generation_counter = 0
        self.last_range = f"{self.min_value} - {self.max_value}"
        self._save_state()
        self._save_range()
        print(f"[RESET] ===== СБРОС СОСТОЯНИЯ (CLEAR) =====")
        print(f"[RESET] Счётчик = 0")
        print(f"[RESET] last_range = {self.last_range}")
        print(f"[RESET] =============================\n")

    def update_range(self, is_min=True, new_value=None):
        """Обновляет диапазон"""
        if is_min:
            old_value = self.min_value
            self.min_value = new_value
            print(f"[RANGE] MIN изменён: {old_value} -> {new_value}")
        else:
            old_value = self.max_value
            self.max_value = new_value
            print(f"[RANGE] MAX изменён: {old_value} -> {new_value}")

        # Сохраняем диапазон в файл
        self._save_range()

        # Обновляем отображение кнопок
        self.update_min_max_buttons()

    def is_history_file_empty(self):
        """Проверяет, пуст ли файл истории или не существует"""
        if not os.path.exists(HISTORY_FILE):
            return True
        try:
            with open(HISTORY_FILE, 'r', encoding='utf-8') as f:
                content = f.read().strip()
                return len(content) == 0
        except Exception:
            return True

    def save_to_history(self, number, min_val, max_val):
        """Сохраняет сгенерированное число в историю"""
        self.generation_counter += 1

        # Формируем строку текущего диапазона
        current_range = f"{min_val} - {max_val}"

        print(f"\n[HISTORY] ===== ЗАПИСЬ В ИСТОРИЮ =====")
        print(f"[HISTORY] Число: {number}")
        print(f"[HISTORY] Текущий диапазон: {current_range}")
        print(f"[HISTORY] Последний диапазон: {self.last_range}")
        print(f"[HISTORY] Счётчик: {self.generation_counter}")

        try:
            # Проверяем, пуст ли файл истории
            file_is_empty = self.is_history_file_empty()
            print(f"[HISTORY] Файл истории пуст: {file_is_empty}")

            # Проверяем, изменился ли диапазон
            range_changed = (current_range != self.last_range)

            # Если файл пуст ИЛИ диапазон изменился - записываем диапазон
            need_write_range = file_is_empty or range_changed

            with open(HISTORY_FILE, 'a', encoding='utf-8') as f:
                if need_write_range:
                    # Записываем новый диапазон
                    f.write(f"{current_range}\n")
                    f.write(f"  #{self.generation_counter}.   {number}\n")
                    # Сохраняем новый диапазон как последний
                    self.last_range = current_range
                    print(f"[HISTORY] ✅ Записан НОВЫЙ диапазон: {current_range}")
                    if file_is_empty:
                        print(f"[HISTORY] 📝 Причина: файл был пуст")
                    else:
                        print(f"[HISTORY] 📝 Причина: диапазон изменился")
                else:
                    # Диапазон не изменился и файл не пуст - записываем только число
                    f.write(f"  #{self.generation_counter}.   {number}\n")
                    print(f"[HISTORY] ✅ Диапазон не изменился, записано только число {number}")

            # Сохраняем состояние
            self._save_state()
            # Сохраняем обновлённый счётчик в файл
            self._save_range()
            print(f"[HISTORY] ================================\n")

        except Exception as e:
            print(f"[ERROR] Error saving to file: {e}")

    def show_history_popup(self):
        """Show history popup"""
        popup = HistoryPopup()
        popup.open()

    def on_enter(self):
        """Вызывается при входе на экран"""
        # Вызываем родительский on_enter для обработки звука
        super().on_enter()

        if not self.adaptive_background:
            self.adaptive_background = AdaptiveBackground(source='assets/backgrounds/random_number_bg.png')
            self.layout.add_widget(self.adaptive_background, index=0)

        if not self.buttons_created:
            self.create_back_button()
            self.create_sprite_buttons()  # Сначала создаем спрайтовые кнопки (они будут снизу)
            self.create_semi_transparent_background()  # Затем полупрозрачный фон (поверх спрайтов)
            self.create_neon_buttons()  # Затем кнопки управления (поверх фона)
            self.buttons_created = True
        else:
            self.update_min_max_buttons()

    def on_leave(self):
        """Вызывается при выходе с экрана"""
        # Вызываем родительский on_leave для обработки звука
        super().on_leave()

        # Останавливаем звук машины если он играет
        self.stop_machine_sound()

        self._save_range()
        for button in self.neon_buttons:
            if button.text_label and button.text_label in self.layout.children:
                button.text_label.opacity = 0
                self.layout.remove_widget(button.text_label)
                button.text_label = None

    def create_back_button(self):
        back_btn = ImageButton(
            source='assets/images/buttons/Orange_back_to_menu_button_90.png',
            size_hint=(0.12, 0.12),
            pos_hint={'x': 0.03, 'y': 0.85},
            allow_stretch=True
        )

        def on_press(instance):
            Animation(opacity=0.7, duration=0.1).start(instance)

        def on_release(instance):
            Animation(opacity=1.0, duration=0.1).start(instance)
            if not self.is_animating:
                Clock.schedule_once(lambda dt: self.go_to_menu(), 0.1)

        back_btn.bind(on_press=on_press, on_release=on_release)
        self.back_button = back_btn
        self.layout.add_widget(back_btn)

    def create_semi_transparent_background(self):
        """Создает полупрозрачный фон для кнопок управления"""
        if self.semi_transparent_bg:
            self.layout.remove_widget(self.semi_transparent_bg)

        # Определяем область для фона - левая часть экрана (где кнопки LIST, MIN, MAX, GENERATE)
        screen_width = Window.width
        screen_height = Window.height

        # Фон занимает левую часть экрана (0-0.45 ширины) и всю высоту
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
            {'x': 0.5, 'y': 0.91},
            {'x': 0.5, 'y': 0.812},
            {'x': 0.5, 'y': 0.715},
            {'x': 0.5, 'y': 0.615},
            {'x': 0.5, 'y': 0.517},
            {'x': 0.5, 'y': 0.415},
            {'x': 0.5, 'y': 0.318},
            {'x': 0.5, 'y': 0.22},
            {'x': 0.5, 'y': 0.12},
            {'x': 0.5, 'y': 0.02}
        ]

        for i, pos in enumerate(button_positions):
            # Для первой кнопки (индекс 0) используем berry_spritesheet
            if i == 0:  # Первая кнопка
                sprite_button = SpriteSheetButton(
                    button_index=i,
                    sprite_sheet_path=berry_sprite_sheet_path,
                    pos_hint={'x': pos['x'], 'y': pos['y']}
                )
            else:
                sprite_button = SpriteSheetButton(
                    button_index=i,
                    sprite_sheet_path=sprite_sheet_path,
                    pos_hint={'x': pos['x'], 'y': pos['y']}
                )

            sprite_button.button_id = i
            sprite_button.button_number = i + 1
            # НЕ ПРИВЯЗЫВАЕМ обработчик нажатия - кнопки не реагируют
            # sprite_button.bind(on_press=self.on_sprite_button_press)
            self.layout.add_widget(sprite_button)
            self.sprite_buttons.append(sprite_button)

            # Выводим информацию о созданной кнопке с рамкой
            print(f"[DEBUG] Создана кнопка {i + 1} с рамкой в позиции: x={pos['x']}, y={pos['y']}")

    def on_sprite_button_press(self, instance):
        # Этот метод больше не используется, так как кнопки не реагируют на нажатия
        pass

    def play_machine_sound(self):
        """Воспроизводит звук работы механизма при анимации (один раз) - проверяет mute"""
        if self._sound_manager.is_muted():
            return
        try:
            from kivy.core.audio import SoundLoader
            sound_path = 'assets/sounds/r_number/machine.mp3'
            if os.path.exists(sound_path):
                self.machine_sound = SoundLoader.load(sound_path)
                if self.machine_sound:
                    self.machine_sound.volume = 0.5
                    # Без зацикливания - звук проиграется один раз
                    self.machine_sound.play()
                    print(f"[SOUND] Воспроизведен звук машины: {sound_path}")
            else:
                print(f"[SOUND] Файл не найден: {sound_path}")
        except Exception as e:
            print(f"[SOUND] Ошибка воспроизведения звука машины: {e}")

    def stop_machine_sound(self):
        """Останавливает звук машины"""
        if hasattr(self, 'machine_sound') and self.machine_sound:
            try:
                if self.machine_sound.state == 'play':
                    self.machine_sound.stop()
                    print(f"[SOUND] Звук машины остановлен")
            except Exception as e:
                print(f"[SOUND] Ошибка остановки звука машины: {e}")

    def spin_all_buttons(self, target_rows, sign_row=None):
        """Запускает анимацию всех кнопок"""
        if self.is_animating:
            return

        print(f"\n🎬 STARTING ANIMATION FOR {len(self.sprite_buttons)} BUTTONS")

        self.is_animating = True
        self._set_neon_buttons_enabled(False)

        # Воспроизводим звук машины (один раз) с задержкой
        Clock.schedule_once(lambda dt: self.play_machine_sound(), 0.4)

        completed = [0]
        total_buttons = len(self.sprite_buttons)
        unlocked = [False]

        def on_animation_complete():
            if unlocked[0]:
                return
            completed[0] += 1
            if completed[0] >= total_buttons:
                print(f"🎬 ALL ANIMATIONS COMPLETED!")
                unlocked[0] = True
                self.is_animating = False
                self._set_neon_buttons_enabled(True)
                # Останавливаем звук машины
                self.stop_machine_sound()

        # Анимация для первой кнопки (знак)
        if sign_row is not None and total_buttons > 0:
            sign_button = self.sprite_buttons[0]

            if sign_row == 1:  # Отрицательное число - останавливаемся на кадре (0, 0)
                target_frame = 0
                # Запускаем анимацию до кадра 0
                sign_button.set_frame(0)
                Clock.schedule_once(
                    lambda dt: sign_button.animate_spin(0, duration=0.8, on_complete=on_animation_complete), 0)
            else:  # Положительное число или ноль - останавливаемся на случайном кадре из строк 1-9
                # Выбираем случайную строку от 1 до 9
                random_row = random.randint(1, 9)
                target_frame = random_row * sign_button.cols
                # Запускаем анимацию до случайного кадра
                Clock.schedule_once(
                    lambda dt: sign_button.animate_spin(random_row, duration=0.8, on_complete=on_animation_complete), 0)

        # Анимация для остальных кнопок (цифры)
        for i, button in enumerate(self.sprite_buttons[1:], start=1):
            target_row = target_rows[i - 1]
            delay = i * 0.03
            Clock.schedule_once(
                lambda dt, b=button, r=target_row: b.animate_spin(r, duration=0.8, on_complete=on_animation_complete),
                delay)

        Clock.schedule_once(lambda dt: self._unlock_buttons_timeout(unlocked), 5.0)

    def _set_neon_buttons_enabled(self, enabled):
        for button in self.neon_buttons:
            button.disabled = not enabled
            button.opacity = 1.0 if enabled else 0.5
            if hasattr(button, 'text_label') and button.text_label:
                button.text_label.opacity = 1.0 if enabled else 0.5

    def _unlock_buttons_timeout(self, unlocked):
        if self.is_animating and not unlocked[0]:
            print(f"⚠️ Таймаут анимации! Принудительная разблокировка кнопок")
            unlocked[0] = True
            self.is_animating = False
            self._set_neon_buttons_enabled(True)
            # Останавливаем звук машины при таймауте
            self.stop_machine_sound()

    def get_digit_row(self, digit):
        return digit

    def get_sign_row(self, is_positive):
        # Возвращаем 0 для положительных, 1 для отрицательных
        return 0 if is_positive else 1

    def create_neon_buttons(self):
        button_configs = [
            {"text": "LIST", "pos_hint": {'x': 0.0, 'y': 0.475}, "id": "list", "value": None},
            {"text": "MIN", "pos_hint": {'x': 0.2, 'y': 0.475}, "id": "min", "value": self.min_value},
            {"text": "GENERATE", "pos_hint": {'x': 0.0, 'y': 0.075}, "id": "generate", "value": None},
            {"text": "MAX", "pos_hint": {'x': 0.2, 'y': 0.075}, "id": "max", "value": self.max_value}
        ]

        for config in button_configs:
            button = NeonButton(
                source='assets/images/buttons/neon_button.png',
                text=config["text"], text_color=(0.2, 0.8, 1, 1),
                size_hint=(0.25, 0.35), pos_hint=config["pos_hint"],
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
        print(f"[SCREEN] show_number_input_popup called: action_type={action_type}, current_value={current_value}")
        self.current_action = action_type
        popup = SimpleNumberInputPopup(
            current_value=current_value,
            on_submit=self.on_value_submitted
        )
        popup.open()

    def on_value_submitted(self, value):
        # === ЕСЛИ ЗНАЧЕНИЕ None - НИЧЕГО НЕ ДЕЛАЕМ ===
        if value is None:
            print(f"[SCREEN] Получено None - диапазон не изменяется")
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
        """Воспроизводит специальный звук для кнопки GENERATE - проверяет mute"""
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
                    print(f"[SOUND] Воспроизведен звук GENERATE: {sound_path}")
            else:
                print(f"[SOUND] Файл не найден: {sound_path}")
        except Exception as e:
            print(f"[SOUND] Ошибка воспроизведения звука: {e}")

    def on_button_release(self, instance, action_id):
        if self.is_animating:
            print(f"[LOCKED] Кнопка {action_id} заблокирована во время анимации")
            return

        Animation(opacity=1.0, duration=0.05).start(instance)

        if action_id == "min":
            self.show_number_input_popup("min", self.min_value)
        elif action_id == "max":
            self.show_number_input_popup("max", self.max_value)
        elif action_id == "generate":
            # Воспроизводим специальный звук для GENERATE
            self.play_generate_sound()

            print(f"\n[GENERATE] ===== НАЖАТА КНОПКА GENERATE =====")
            print(f"[GENERATE] Текущий MIN: {self.min_value}")
            print(f"[GENERATE] Текущий MAX: {self.max_value}")
            print(f"[GENERATE] last_range: {self.last_range}")
            print(f"[GENERATE] Счётчик: {self.generation_counter}")
            print(f"[GENERATE] =====================================\n")

            result = self.generate_random_number()
            if result is not None:
                self.save_to_history(result, self.min_value, self.max_value)

                is_positive = result >= 0
                abs_result = abs(result)
                result_str = str(abs_result).zfill(9)
                target_rows = [self.get_digit_row(int(d)) for d in result_str]
                sign_row = self.get_sign_row(is_positive)
                self.spin_all_buttons(target_rows, sign_row)
        elif action_id == "list":
            self.show_history_popup()

    def go_to_menu(self):
        from main import switch_screen
        switch_screen('menu')