from kivy.uix.button import ButtonBehavior
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.image import Image
from kivy.uix.label import Label
from kivy.properties import StringProperty, ListProperty


class ControlButton(ButtonBehavior, FloatLayout):
    """Кнопка для панели управления"""
    text = StringProperty('')
    icon_path = StringProperty('')
    background_color = ListProperty([1, 1, 1, 1])

    def __init__(self, callback=None, **kwargs):
        super().__init__(**kwargs)
        self.callback = callback

        # Иконка
        if self.icon_path:
            self.icon = Image(
                source=self.icon_path,
                size_hint=(1, 1),
                pos_hint={'center_x': 0.5, 'center_y': 0.5},
                allow_stretch=True,
                keep_ratio=True
            )
            self.add_widget(self.icon)

    def setup_icon(self):
        """Настройка иконки кнопки"""
        if self.icon_path:
            # Очищаем предыдущую иконку
            self.clear_widgets()

            # Создаем новую иконку
            icon = Image(
                source=self.icon_path,
                size_hint=(None, None),
                size=(self.height * 1, self.height * 1),
                pos_hint={'center_x': 0.5, 'center_y': 0.5}
            )
            self.add_widget(icon)

    def update_icon(self, new_icon_path):
        """Обновляет иконку кнопки"""
        self.icon_path = new_icon_path
        self.setup_icon()

    def on_press(self):
        if self.callback:
            self.callback(self)