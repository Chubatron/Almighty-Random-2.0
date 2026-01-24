from kivy.uix.floatlayout import FloatLayout
from kivy.uix.image import Image
from kivy.uix.label import Label
from kivy.uix.behaviors import ButtonBehavior


class IconButton(ButtonBehavior, FloatLayout):
    """Кнопка с иконкой и текстом"""

    def __init__(self, text, icon_path, sport, callback, **kwargs):
        super().__init__(**kwargs)

        self.sport = sport

        # Устанавливаем фон кнопки
        with self.canvas.before:
            from kivy.graphics import Color, RoundedRectangle
            Color(0.2, 0.2, 0.2, 0.0)
            self.rect = RoundedRectangle(size=self.size, pos=self.pos, radius=[10, ])

        # Обновляем фон при изменении размера/позиции
        self.bind(pos=self.update_rect, size=self.update_rect)

        # Иконка
        self.icon = Image(
            source=icon_path if icon_path else '',
            size_hint=(0.7, 0.7),
            pos_hint={'center_x': 0.5, 'center_y': 0.65},
            allow_stretch=True
        )

        # Текст
        self.label = Label(
            text=text,
            font_size='12sp',
            color=(1, 1, 1, 1),
            size_hint=(1, 0.3),
            pos_hint={'center_x': 0.5, 'y': 0}
        )

        self.add_widget(self.icon)
        self.add_widget(self.label)

        # Привязываем callback
        if callback:
            self.bind(on_press=callback)

    def update_rect(self, *args):
        self.rect.pos = self.pos
        self.rect.size = self.size

    def on_press(self):
        """Анимация при нажатии"""
        self.canvas.before.clear()
        with self.canvas.before:
            from kivy.graphics import Color, RoundedRectangle
            Color(0.3, 0.3, 0.3, 0.1)  # Более темный цвет
            RoundedRectangle(size=self.size, pos=self.pos, radius=[10, ])

    def on_release(self):
        """Возвращаем обычный цвет"""
        self.canvas.before.clear()
        with self.canvas.before:
            from kivy.graphics import Color, RoundedRectangle
            Color(0.2, 0.2, 0.2, 0.0)
            RoundedRectangle(size=self.size, pos=self.pos, radius=[10, ])