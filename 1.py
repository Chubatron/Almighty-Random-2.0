from kivy.uix import widget
from kivy.graphics import Color, Rectangle, Ellipse
from kivy.uix.widget import Widget

class MyWidget(Widget):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

with widget.canvas.before:
    # Тень (рисуется ПОД виджетом)
    Color(0, 0, 0, 0.3)
    for i in range(5):  # Размытие тени
        Rectangle(pos=(i, i - 5), size=self.size)

    # Свечение
    Color(1, 1, 0, 0.2)
    Ellipse(pos=(-10, -10), size=(self.width + 20, self.height + 20))