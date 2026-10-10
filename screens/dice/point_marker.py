"""
Маркер точки на экране
"""
from kivy.uix.widget import Widget
from kivy.graphics import Color, Ellipse


class PointMarker(Widget):
    """Виджет для отображения точки на экране"""

    def __init__(self, color=(1, 0, 0, 1), size=15, **kwargs):
        super().__init__(**kwargs)
        self.point_x = 0
        self.point_y = 0
        self.color = color
        self.point_size = size
        self.is_visible = False

    def draw_point(self):
        self.canvas.clear()
        if not self.is_visible:
            return
        with self.canvas:
            Color(self.color[0], self.color[1], self.color[2], 0.3)
            Ellipse(pos=(self.point_x - self.point_size, self.point_y - self.point_size),
                   size=(self.point_size * 2, self.point_size * 2))
            Color(self.color[0], self.color[1], self.color[2], self.color[3])
            Ellipse(pos=(self.point_x - self.point_size/2, self.point_y - self.point_size/2),
                   size=(self.point_size, self.point_size))
            Color(1, 1, 1, 0.8)
            Ellipse(pos=(self.point_x - self.point_size/4, self.point_y - self.point_size/4),
                   size=(self.point_size/2, self.point_size/2))

    def update_position(self, x, y, visible=True):
        self.point_x = x
        self.point_y = y
        self.is_visible = visible
        self.draw_point()

    def set_visible(self, visible):
        """Скрыть/показать точку без сдвига координат."""
        self.is_visible = visible
        self.draw_point()