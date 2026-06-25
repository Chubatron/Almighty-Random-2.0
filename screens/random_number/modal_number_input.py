# modal_number_input.py
from kivy.uix.modalview import ModalView
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.textinput import TextInput
from kivy.uix.button import Button
from kivy.uix.scatter import Scatter
from kivy.uix.image import Image
from kivy.uix.label import Label
from kivy.graphics import Color, Rectangle, Ellipse
from kivy.clock import Clock
from kivy.core.window import Window
import os

from sound_manager import SoundManager

# Глобальная переменная для хранения позиции Scatter
SCATTER_POSITION = None


class ImageButton(Button):
    """Кнопка с изображением и текстом поверх"""

    def __init__(self, image_source='', text='', **kwargs):
        super().__init__(**kwargs)
        self.background_normal = ''
        self.background_down = ''
        self.background_color = (0, 0, 0, 0)

        self.button_text = text
        self.text_font_size = kwargs.get('font_size', 24)
        self.text_color = kwargs.get('color', (1, 1, 1, 1))

        # Загружаем звук нажатия
        self._click_sound = None
        self._sound_manager = SoundManager()
        self._load_click_sound()

        self.bg_image = Image(
            source=image_source,
            allow_stretch=True,
            keep_ratio=False,
            size=self.size,
            pos=self.pos
        )
        self.add_widget(self.bg_image)

        self.text_label = Label(
            text=text,
            font_size=self.text_font_size,
            color=self.text_color,
            bold=True,
            size=self.size,
            pos=self.pos,
            halign='center',
            valign='middle'
        )
        self.add_widget(self.text_label)

        self.bind(size=self._update_widgets, pos=self._update_widgets)

    def _load_click_sound(self):
        """Загружает звук нажатия кнопки"""
        try:
            from kivy.core.audio import SoundLoader
            sound_path = 'assets/sounds/r_number/set_value.mp3'
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

    def _update_widgets(self, instance, value):
        if hasattr(self, 'bg_image'):
            self.bg_image.size = self.size
            self.bg_image.pos = self.pos
        if hasattr(self, 'text_label'):
            self.text_label.size = self.size
            self.text_label.pos = self.pos

    def on_press(self):
        """При нажатии воспроизводим звук"""
        self.play_click_sound()
        super().on_press()


class RotatedPopup(ModalView):
    """Модальное окно с повёрнутым содержимым"""

    def __init__(self, current_value=0, on_submit=None, **kwargs):
        global SCATTER_POSITION

        super().__init__(**kwargs)
        self.size_hint = (0.5, 0.5)
        self.auto_dismiss = True
        self.on_submit = on_submit
        self._initialized = False
        self._sound_manager = SoundManager()

        with self.canvas.before:
            Color(0.2, 0.2, 0.2, 0.95)
            self.bg_rect = Rectangle(size=self.size, pos=self.pos)
            self.bind(size=self._update_bg, pos=self._update_bg)

        self.bg_image = Image(
            source='assets/images/popup_bg.png',
            allow_stretch=True,
            keep_ratio=False,
            size_hint=(1, 1),
            pos_hint={'x': 0, 'y': 0}
        )
        self.add_widget(self.bg_image)

        self.scatter = Scatter(
            size_hint=(0.8, 0.6),
            pos_hint={'center_x': 0.5, 'center_y': 0.5},
            do_rotation=False,
            do_scale=False,
            do_translation=False,
            rotation=-90
        )

        SCATTER_POSITION = self.scatter.pos

        self.layout = BoxLayout(
            orientation='vertical',
            padding=20,
            spacing=15,
            size_hint=(None, None)
        )

        self.text_input = TextInput(
            text="",
            font_size=40,
            size_hint=(1, 0.2),
            multiline=False,
            input_filter='int',
            halign='center',
            background_color=(0.15, 0.15, 0.15, 0),
            foreground_color=(1, 1, 1, 1),
            cursor_color=(0.2, 0.8, 1, 1)
        )
        self.text_input.bind(text=self.on_text_change)
        self.layout.add_widget(self.text_input)

        self.submit_btn = ImageButton(
            image_source='assets/images/buttons/Roulette_switch_button.png',
            text="OK",
            font_size=24,
            color=(0, 0, 0, 1),
            size_hint=(1, 0.15)
        )
        self.submit_btn.bind(on_press=self._on_submit)
        self.layout.add_widget(self.submit_btn)

        self.scatter.add_widget(self.layout)
        self.add_widget(self.scatter)

        Clock.schedule_once(self._sync_layout, 0.1)
        Clock.schedule_once(lambda dt: self._focus_input(), 0.5)

    def _sync_layout(self, dt):
        global SCATTER_POSITION

        if hasattr(self, 'scatter') and hasattr(self, 'layout'):
            self.layout.size = (self.scatter.height, self.scatter.width)
            global_pos = self.scatter.to_window(0, 0)
            offset_y = self.scatter.height - self.scatter.width
            self.layout.pos = (global_pos[0] - offset_y, global_pos[1])
            SCATTER_POSITION = self.scatter.pos

    def _focus_input(self):
        if hasattr(self, 'text_input'):
            self.text_input.focus = True

    def on_text_change(self, instance, value):
        # Разрешаем пустую строку или просто минус
        if value == '' or value == '-':
            self._last_value = value
            return

        # Проверяем длину: максимум 10 символов (минус + 9 цифр)
        if len(value) > 10:
            # Возвращаем последнее корректное значение
            if hasattr(self, '_last_value'):
                self.text_input.text = self._last_value
            return

        try:
            num = int(value)
            # Проверяем диапазон (но не заменяем, просто блокируем ввод)
            if num > 999999999 or num < -999999999:
                if hasattr(self, '_last_value'):
                    self.text_input.text = self._last_value
                return
            self._last_value = value
        except ValueError:
            # Если введено что-то нечисловое (кроме минуса), откатываем
            if hasattr(self, '_last_value'):
                self.text_input.text = self._last_value

    def _update_bg(self, instance, value):
        if hasattr(self, 'bg_rect'):
            self.bg_rect.size = self.size
            self.bg_rect.pos = self.pos

    def _on_submit(self, instance):
        text_value = self.text_input.text.strip()

        # Если поле пустое или только минус - передаём None
        if text_value == '' or text_value == '-':
            print(f"[POPUP] Поле ввода пустое, передаём None")
            if self.on_submit:
                self.on_submit(None)
            self.dismiss()
            return

        try:
            value = int(text_value)
            if value > 999999999:
                value = 999999999
            elif value < -999999999:
                value = -999999999
            if self.on_submit:
                self.on_submit(value)
        except Exception as e:
            print(f"[POPUP] Ошибка преобразования: {e}")
            if self.on_submit:
                self.on_submit(0)
        self.dismiss()


class SimpleNumberInputPopup(RotatedPopup):
    pass


class CustomModal(RotatedPopup):
    pass