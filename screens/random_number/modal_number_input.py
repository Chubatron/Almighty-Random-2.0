# modal_number_input.py
from kivy.uix.modalview import ModalView
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.textinput import TextInput
from kivy.uix.button import Button
from kivy.uix.image import Image
from kivy.uix.label import Label
from kivy.uix.widget import Widget
from kivy.graphics import Color, Rectangle, Line
from kivy.clock import Clock
from kivy.core.window import Window
from kivy.utils import platform
import os

from sound_manager import SoundManager


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
        self.play_click_sound()
        super().on_press()


class SimpleNumberInputPopup(ModalView):
    """Попап с полем ввода и кнопкой OK"""

    def __init__(self, current_value=0, on_submit=None, **kwargs):
        super().__init__(**kwargs)
        self.size_hint = (0.7, 0.4)
        self.auto_dismiss = True
        self.on_submit = on_submit
        self._sound_manager = SoundManager()

        # FloatLayout позволяет накладывать элементы друг на друга
        from kivy.uix.floatlayout import FloatLayout
        self.layout = FloatLayout()

        # 1. Фоновое изображение - на весь попап
        self.bg_image = Image(
            source='assets/images/popup_bg.png',
            allow_stretch=True,
            keep_ratio=False,
            size_hint=(1, 1),
            pos_hint={'x': 0, 'y': 0}
        )
        self.layout.add_widget(self.bg_image)

        # 2. Контейнер для содержимого поверх фона (вертикальный BoxLayout)
        self.content_layout = BoxLayout(
            orientation='vertical',
            padding=40,
            spacing=20,
            size_hint=(1, 1),
            pos_hint={'center_x': 0.5, 'center_y': 0.5}
        )

        # РАЗМЕР ШРИФТА ЗАВИСИТ ОТ РАЗМЕРА ПОПАПА
        popup_width = Window.width * 0.7
        popup_height = Window.height * 0.4

        text_input_font_size = min(popup_width, popup_height) * 0.15
        button_font_size = min(popup_width, popup_height) * 0.045

        text_input_font_size = max(24, min(60, text_input_font_size))
        button_font_size = max(16, min(40, button_font_size))

        # Поле ввода - ПРОЗРАЧНОЕ, виден только курсор и текст
        self.text_input = TextInput(
            text="",
            font_size=text_input_font_size,
            size_hint=(1, 0.6),
            multiline=False,
            input_filter='int',
            halign='center',
            padding=(10, 10, 10, 10),
            background_color=(0, 0, 0, 0),
            foreground_color=(1, 1, 1, 1),
            cursor_color=(0.2, 0.8, 1, 1),
            background_normal='',
            background_active=''
        )
        self.text_input.bind(text=self.on_text_change)
        self.content_layout.add_widget(self.text_input)

        # Кнопка OK (БЕЗ ПОДСВЕТКИ)
        self.submit_btn = ImageButton(
            image_source='assets/images/buttons/Roulette_switch_button.png',
            text="OK",
            font_size=button_font_size,
            color=(0, 0, 0, 1),
            size_hint=(0.4, 0.4),
            pos_hint={'center_x': 0.5}
        )
        self.submit_btn.bind(on_press=self._on_submit)
        self.content_layout.add_widget(self.submit_btn)

        # Добавляем content_layout поверх bg_image
        self.layout.add_widget(self.content_layout)

        self.add_widget(self.layout)

        # Состояние
        self._last_value = ""

        # Фокус на поле ввода
        Clock.schedule_once(lambda dt: self._focus_input(), 0.3)

    def _focus_input(self):
        if hasattr(self, 'text_input'):
            self.text_input.focus = True

    def on_text_change(self, instance, value):
        if value == '' or value == '-':
            self._last_value = value
            return

        if len(value) > 10:
            if hasattr(self, '_last_value'):
                self.text_input.text = self._last_value
            return

        try:
            num = int(value)
            if num > 999999999 or num < -999999999:
                if hasattr(self, '_last_value'):
                    self.text_input.text = self._last_value
                return
            self._last_value = value
        except ValueError:
            if hasattr(self, '_last_value'):
                self.text_input.text = self._last_value

    def _on_submit(self, instance):
        text_value = self.text_input.text.strip()

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

    def on_dismiss(self):
        """При закрытии popup скрываем клавиатуру"""
        if platform == 'android':
            try:
                from jnius import autoclass
                PythonActivity = autoclass('org.kivy.android.PythonActivity')
                InputMethodManager = autoclass('android.view.inputmethod.InputMethodManager')
                Context = autoclass('android.content.Context')

                activity = PythonActivity.mActivity
                imm = activity.getSystemService(Context.INPUT_METHOD_SERVICE)
                current_focus = activity.getCurrentFocus()

                if current_focus:
                    imm.hideSoftInputFromWindow(current_focus.getWindowToken(), 0)
                    print("[KEYBOARD] Клавиатура скрыта")
            except Exception as e:
                print(f"[KEYBOARD] Ошибка скрытия клавиатуры: {e}")
        super().on_dismiss()


class CustomModal(SimpleNumberInputPopup):
    pass