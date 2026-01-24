from kivy.uix.widget import Widget
from kivy.graphics import Color, Ellipse, Rectangle, Triangle
from kivy.clock import Clock
from kivy.properties import ListProperty
from random import random, randint, choice
import math


class AnimatedBackground(Widget):
    """Виджет с анимированными фигурами на фоне"""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.shapes = []
        self.max_shapes = 20  # Меньше для производительности

        # Более светлые и прозрачные цвета
        self.colors = [
            [1, 0.6, 0.3, 0.25],  # Светло-оранжевый
            [0.3, 0.7, 1, 0.25],  # Светло-синий
            [0.5, 0.9, 0.5, 0.25],  # Светло-зеленый
            [1, 1, 0.4, 0.25],  # Светло-желтый
            [0.9, 0.4, 0.9, 0.25],  # Светло-фиолетовый
        ]

        # Отслеживаем размеры
        self.bind(size=self._update_shapes_position)

        # Запускаем с задержкой, чтобы виджет инициализировался
        Clock.schedule_once(self._start_animation, 0.5)

    def _start_animation(self, dt):
        """Запуск анимации после инициализации виджета"""
        Clock.schedule_interval(self._update, 1 / 30.0)  # 30 FPS
        Clock.schedule_interval(self._add_shape, 1.2)  # Новая фигура каждые 1.2 сек

        # Сразу добавляем несколько фигур
        for _ in range(5):
            self._add_shape(0)

    def _add_shape(self, dt):
        """Добавление новой фигуры"""
        if len(self.shapes) >= self.max_shapes or self.width == 0 or self.height == 0:
            return

        shape = {
            'id': len(self.shapes),
            'type': randint(0, 2),  # 0=круг, 1=квадрат, 2=треугольник
            'x': random() * self.width,
            'y': random() * self.height,
            'size': randint(10, 25),
            'color': choice(self.colors),
            'growth': random() * 0.8 + 0.2,
            'max_size': randint(40, 70),
            'min_size': randint(5, 15),
            'speed_x': random() * 30 - 15,
            'speed_y': random() * 30 - 15,
            'life': 1.0,
            'decay': random() * 0.08 + 0.02,
            'rotation': random() * 360,
            'rotation_speed': random() * 20 - 10,
            'direction': 1  # 1 = растет, -1 = уменьшается
        }

        self.shapes.append(shape)
        self._draw_shape(shape)

    def _draw_shape(self, shape):
        """Рисует одну фигуру на canvas"""
        with self.canvas:
            # Устанавливаем цвет с учетом прозрачности
            color = shape['color'].copy()
            color[3] = shape['life'] * color[3]  # Учитываем время жизни
            Color(*color)

            x, y = shape['x'], shape['y']
            size = shape['size']

            if shape['type'] == 0:  # Круг
                Ellipse(pos=(x - size / 2, y - size / 2), size=(size, size))

            elif shape['type'] == 1:  # Квадрат
                Rectangle(pos=(x - size / 2, y - size / 2), size=(size, size))

            elif shape['type'] == 2:  # Треугольник
                # Треугольник с вращением
                angle = shape['rotation'] * math.pi / 180
                points = []
                for i in range(3):
                    point_angle = angle + i * 2 * math.pi / 3
                    px = x + math.cos(point_angle) * size / 2
                    py = y + math.sin(point_angle) * size / 2
                    points.extend([px, py])
                Triangle(points=points)

    def _update(self, dt):
        """Обновляет все фигуры"""
        # Очищаем canvas
        self.canvas.clear()

        shapes_to_remove = []

        # Обновляем каждую фигуру
        for shape in self.shapes[:]:
            # Обновляем жизнь
            shape['life'] -= shape['decay'] * dt

            if shape['life'] <= 0:
                shapes_to_remove.append(shape)
                continue

            # Обновляем позицию
            shape['x'] += shape['speed_x'] * dt
            shape['y'] += shape['speed_y'] * dt

            # Отскок от границ
            if shape['x'] < 0 or shape['x'] > self.width:
                shape['speed_x'] *= -0.95
                shape['x'] = max(0, min(shape['x'], self.width))
            if shape['y'] < 0 or shape['y'] > self.height:
                shape['speed_y'] *= -0.95
                shape['y'] = max(0, min(shape['y'], self.height))

            # Обновляем вращение
            shape['rotation'] += shape['rotation_speed'] * dt

            # Анимация размера (пульсация)
            if shape['direction'] == 1:
                shape['size'] += shape['growth'] * 20 * dt
                if shape['size'] >= shape['max_size']:
                    shape['direction'] = -1
                    shape['size'] = shape['max_size']
            else:
                shape['size'] -= shape['growth'] * 25 * dt
                if shape['size'] <= shape['min_size']:
                    shape['direction'] = 1
                    shape['size'] = shape['min_size']

            # Рисуем обновленную фигуру
            self._draw_shape(shape)

        # Удаляем "умершие" фигуры
        for shape in shapes_to_remove:
            if shape in self.shapes:
                self.shapes.remove(shape)

        # Добавляем новую фигуру, если нужно
        if len(self.shapes) < self.max_shapes and random() < 0.1:
            self._add_shape(0)

    def _update_shapes_position(self, instance, value):
        """При изменении размера виджета корректируем позиции фигур"""
        if not self.shapes:
            return

        # Масштабируем позиции фигур при изменении размера
        old_width, old_height = getattr(self, '_old_size', (self.width, self.height))
        if old_width == 0 or old_height == 0:
            self._old_size = (self.width, self.height)
            return

        width_ratio = self.width / old_width if old_width > 0 else 1
        height_ratio = self.height / old_height if old_height > 0 else 1

        for shape in self.shapes:
            shape['x'] *= width_ratio
            shape['y'] *= height_ratio

        self._old_size = (self.width, self.height)

    def _add_shape_at(self, x, y):
        """Добавляет фигуру в указанной позиции"""
        if len(self.shapes) >= self.max_shapes:
            return

        shape = {
            'id': len(self.shapes),
            'type': randint(0, 2),
            'x': x,
            'y': y,
            'size': randint(15, 30),
            'color': choice(self.colors),
            'growth': random() * 0.8 + 0.2,
            'max_size': randint(50, 80),
            'min_size': randint(8, 18),
            'speed_x': random() * 40 - 20,
            'speed_y': random() * 40 - 20,
            'life': 1.0,
            'decay': random() * 0.1 + 0.03,
            'rotation': random() * 360,
            'rotation_speed': random() * 30 - 15,
            'direction': 1
        }

        self.shapes.append(shape)