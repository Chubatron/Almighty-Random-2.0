# components/token_widget.py
# UI-виджет «кнопка Lucky_Token + счётчик внутри жетона».

import os
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.image import Image
from kivy.uix.label import Label
from kivy.uix.behaviors import ButtonBehavior
from kivy.properties import NumericProperty, BooleanProperty
from kivy.clock import Clock


# ==================== ПУТИ К КАРТИНКАМ ====================
TOKEN_BUTTON = 'assets/images/buttons/luck.png'


class _ClickableImage(ButtonBehavior, Image):
    """Картинка, которая умеет нажиматься."""
    pass


class TokenWidget(FloatLayout):
    """Виджет «жетон + счётчик внутри жетона»."""

    # ==================== СТАНДАРТНАЯ ПОЗИЦИЯ НА ЭКРАНЕ ====================
    # Меняется в одном месте — применяется во всех экранах.
    DEFAULT_SIZE_HINT = (0.32, 0.09)
    DEFAULT_POS_HINT = {'center_x': 0.5, 'top': 1.01}
    # ====================================================================

    # ==================== НАСТРОЙКИ ====================

    # Доля ширины виджета, которую занимает жетон.
    BUTTON_WIDTH_FRACTION = 1.0

    # Размер цифры как доля от высоты жетона.
    VALUE_FONT_TO_TOKEN_HEIGHT_RATIO = 0.2

    # Смещение цифры внутри жетона (в долях от размера жетона).
    VALUE_OFFSET_X = 0.1
    VALUE_OFFSET_Y = 0.0

    # Цвета цифры
    VALUE_COLOR_OK   = (1, 0.9, 0.2, 1)
    VALUE_COLOR_FAIL = (1, 0.3, 0.3, 1)
    # ===================================================

    value = NumericProperty(0)
    can_afford = BooleanProperty(True)

    def __init__(self, **kwargs):
        # Подставляем стандартные size_hint/pos_hint, если не переданы явно
        kwargs.setdefault('size_hint', self.DEFAULT_SIZE_HINT)
        kwargs.setdefault('pos_hint', dict(self.DEFAULT_POS_HINT))

        super().__init__(**kwargs)

        # --- Кнопка (жетон) ---
        self.button_image = _ClickableImage(
            source=TOKEN_BUTTON,
            fit_mode='contain',
            size_hint=(None, None),
            mipmap=True,
        )
        self.button_image.bind(on_press=self._on_button_press)
        self.button_image.bind(texture=self._smooth_texture)
        self.add_widget(self.button_image)

        # --- Счётчик (поверх жетона) ---
        self.value_label = Label(
            text='0',
            font_size='20sp',
            bold=True,
            color=self.VALUE_COLOR_OK,
            halign='center',
            valign='middle',
            size_hint=(None, None),
        )
        self.add_widget(self.value_label)

        self.bind(pos=self._update_layout, size=self._update_layout)
        Clock.schedule_once(lambda dt: self._update_layout(), 0)

    # ==================== ПУБЛИЧНОЕ API ====================

    def set_value(self, n):
        n = int(n)
        self.value = n
        self.value_label.text = str(n)

    def set_state(self, can_afford):
        can_afford = bool(can_afford)
        self.can_afford = can_afford
        if can_afford:
            self.value_label.color = self.VALUE_COLOR_OK
        else:
            self.value_label.color = self.VALUE_COLOR_FAIL

    # ==================== ВНУТРЕННЕЕ ====================

    def _smooth_texture(self, *args):
        tex = self.button_image.texture
        if tex:
            tex.mag_filter = 'linear'
            tex.min_filter = 'linear_mipmap_linear'
            tex.mipmap = True

    def _on_button_press(self, *args):
        print(f"🎟️ [TokenWidget] Нажата кнопка (balance={self.value}, afford={self.can_afford})")

    def _update_layout(self, *args):
        if self.width <= 0 or self.height <= 0:
            Clock.schedule_once(lambda dt: self._update_layout(), 0.05)
            return

        w, h = self.width, self.height

        # Жетон — квадрат, вписанный в виджет
        token_size = min(w * self.BUTTON_WIDTH_FRACTION, h)
        token_center_x = self.x + w / 2
        token_center_y = self.y + h / 2

        self.button_image.size = (token_size, token_size)
        self.button_image.center = (token_center_x, token_center_y)

        # Цифра — по центру жетона (или со смещением)
        self.value_label.size = (token_size, token_size)
        self.value_label.center = (
            token_center_x + self.VALUE_OFFSET_X * token_size,
            token_center_y + self.VALUE_OFFSET_Y * token_size,
        )
        self.value_label.text_size = (token_size, token_size)

        # Размер шрифта от размера жетона
        font_size = token_size * self.VALUE_FONT_TO_TOKEN_HEIGHT_RATIO

        # Автоподгонка: если текст шире жетона — уменьшаем шрифт
        text = str(self.value)
        needed_width = len(text) * font_size * 0.62
        if needed_width > token_size and token_size > 0:
            font_size = font_size * (token_size / needed_width)

        self.value_label.font_size = max(10, font_size)