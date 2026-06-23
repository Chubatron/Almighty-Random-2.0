# vertical_textinput.py
from kivy.uix.textinput import TextInput
from kivy.graphics import PushMatrix, PopMatrix, Rotate, Translate
from kivy.clock import Clock


class VerticalTextInput(TextInput):
    """
    Вертикальное поле ввода (повёрнуто на 90 градусов)
    С корректной обработкой касаний
    """

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._rotated = False
        Clock.schedule_once(self._apply_rotation, 0.2)

    def _apply_rotation(self, dt):
        if self._rotated or self.width == 0 or self.height == 0:
            return

        self._rotated = True
        self.canvas.before.clear()
        with self.canvas.before:
            PushMatrix()
            Translate(self.center_x, self.center_y, 0)
            Rotate(angle=90, origin=(0, 0))
            Translate(-self.center_x, -self.center_y, 0)

    def to_local(self, x, y, **kwargs):
        """Пересчитывает координаты касания для повёрнутого виджета"""
        if not self._rotated:
            return super().to_local(x, y, **kwargs)

        # Пересчёт координат для поворота на 90 градусов
        dx = x - self.center_x
        dy = y - self.center_y
        # Поворачиваем координаты обратно
        new_x = self.center_x + dy
        new_y = self.center_y - dx
        return super().to_local(new_x, new_y, **kwargs)

    def collide_point(self, x, y):
        """Проверяет, попал ли клик в область повёрнутого виджета"""
        if not self._rotated:
            return super().collide_point(x, y)

        # Пересчитываем координаты для повёрнутой области
        dx = x - self.center_x
        dy = y - self.center_y
        new_x = self.center_x + dy
        new_y = self.center_y - dx

        # Проверяем попадание с учётом поворота
        half_width = self.width / 2
        half_height = self.height / 2
        return (self.center_x - half_height <= new_x <= self.center_x + half_height and
                self.center_y - half_width <= new_y <= self.center_y + half_width)