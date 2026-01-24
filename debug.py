# debug_visible_ball.py
from kivy.app import App
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.graphics import Color, Rectangle, Line, Ellipse
from kivy.core.image import Image as CoreImage
from kivy.properties import NumericProperty, StringProperty
from kivy.uix.widget import Widget
import os


class DebugSpriteBall(Widget):
    """Мяч с визуальной отладкой - ВСЕГДА видимый!"""

    sprite_sheet_path = StringProperty('')
    frame_index = NumericProperty(0)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.size = (200, 200)
        self.texture = None
        self.texture_loaded = False
        self.debug_mode = True  # Всегда показываем отладочную графику

        self.bind(
            sprite_sheet_path=self.load_texture,
            frame_index=self.update_canvas,
            pos=self.update_canvas,
            size=self.update_canvas
        )

        # Сразу обновляем отрисовку
        Clock.schedule_once(lambda dt: self.update_canvas(), 0.1)

    def load_texture(self, instance, path):
        """Пытается загрузить текстуру, но не критично если не получится"""
        if path and os.path.exists(path):
            try:
                self.texture = CoreImage(path).texture
                self.texture_loaded = True
                print(f"✓ Текстура загружена: {path}")
                print(f"  Размер: {self.texture.width}x{self.texture.height}")
            except Exception as e:
                print(f"✗ Ошибка загрузки текстуры: {e}")
                self.texture_loaded = False
        else:
            print(f"✗ Файл не найден: {path}")
            self.texture_loaded = False

        self.update_canvas()

    def update_canvas(self, *args):
        """Отрисовывает мяч с отладочной информацией"""
        self.canvas.clear()

        # 1. ФОН - всегда видимый (зеленый, прозрачный)
        with self.canvas:
            # Зеленый фон с низкой прозрачностью
            Color(0, 0.8, 0, 0.3)
            Rectangle(pos=self.pos, size=self.size)

            # Красная рамка для видимости границ
            Color(1, 0, 0, 1)
            Line(rectangle=(self.x, self.y, self.width, self.height), width=2)

            # Диагональные линии для видимости
            Color(1, 1, 0, 0.5)
            Line(points=[self.x, self.y, self.right, self.top], width=1)
            Line(points=[self.right, self.y, self.x, self.top], width=1)

        # 2. Если текстура загружена - пробуем отрисовать
        if self.texture_loaded and self.texture:
            try:
                with self.canvas:
                    # Желтый цвет под текстурой (будет видно если текстура прозрачная)
                    Color(1, 1, 0, 0.5)
                    Rectangle(pos=(self.x + 10, self.y + 10),
                              size=(self.width - 20, self.height - 20))

                    # Пробуем отрисовать текстуру
                    Color(1, 1, 1, 1)
                    Rectangle(pos=self.pos, size=self.size, texture=self.texture)

                    # Синяя рамка вокруг текстуры
                    Color(0, 0, 1, 1)
                    Line(rectangle=(self.x + 5, self.y + 5,
                                    self.width - 10, self.height - 10), width=3)

            except Exception as e:
                print(f"✗ Ошибка отрисовки текстуры: {e}")
                self.draw_fallback()
        else:
            self.draw_fallback()

        # 3. Текст с номером кадра (ВСЕГДА поверх всего)
        self.draw_frame_number()

    def draw_fallback(self):
        """Рисует запасной мяч если текстура не загружена"""
        with self.canvas:
            # Большой красный круг
            Color(1, 0, 0, 0.7)
            Ellipse(pos=self.pos, size=self.size)

            # Белый крест
            Color(1, 1, 1, 1)
            Line(points=[self.center_x, self.y + 20,
                         self.center_x, self.top - 20], width=4)
            Line(points=[self.x + 20, self.center_y,
                         self.right - 20, self.center_y], width=4)

            # Синий круг в центре
            Color(0, 0, 1, 1)
            Ellipse(pos=(self.center_x - 15, self.center_y - 15),
                    size=(30, 30))

    def draw_frame_number(self):
        """Рисует номер кадра"""
        # Используем Label для текста вместо canvas
        # (это проще и надежнее)
        from kivy.uix.label import Label

        # Удаляем старые лейблы
        if hasattr(self, 'frame_label'):
            self.remove_widget(self.frame_label)

        self.frame_label = Label(
            text=f'FRAME: {self.frame_index}',
            size_hint=(None, None),
            size=(150, 40),
            pos=(self.center_x - 75, self.y - 45),
            color=(1, 1, 1, 1),
            font_size='20sp',
            bold=True,
            outline_color=(0, 0, 0, 1),
            outline_width=2
        )
        self.add_widget(self.frame_label)

    def on_touch_down(self, touch):
        """При клике меняет кадр и показывает координаты"""
        if self.collide_point(*touch.pos):
            self.frame_index = (self.frame_index + 1) % 64

            # Показываем где был клик
            print(f"Клик в мяче! Координаты: {touch.pos}")
            print(f"Границы мяча: X:{self.x}-{self.right}, Y:{self.y}-{self.top}")

            # Визуально показываем место клика
            with self.canvas.after:
                Color(1, 1, 1, 0.8)
                Line(circle=(touch.x, touch.y, 15), width=3)
                # Удалим через секунду
                from kivy.clock import Clock
                Clock.schedule_once(lambda dt: self.canvas.after.clear(), 1)

            return True
        return super().on_touch_down(touch)


from kivy.clock import Clock


class DebugApp(App):
    def build(self):
        layout = FloatLayout()

        # ТЕМНЫЙ ФОН для контраста
        with layout.canvas.before:
            Color(0.05, 0.05, 0.1, 1)
            Rectangle(pos=layout.pos, size=layout.size)

        # ЗАГОЛОВОК
        title = Label(
            text='[color=ff5555]ДЕБАГ МЯЧА[/color] - должен быть ВИДЕН!',
            markup=True,
            size_hint=(None, None),
            size=(500, 50),
            pos_hint={'center_x': 0.5, 'top': 0.97},
            font_size='24sp',
            color=(1, 1, 1, 1)
        )
        layout.add_widget(title)

        # ИНФОРМАЦИЯ
        info = Label(
            text='[color=ffff00]•[/color] Зеленый фон = виджет\n'
                 '[color=ffff00]•[/color] Красная рамка = границы\n'
                 '[color=ffff00]•[/color] Кликните на мяч -> меняется кадр',
            markup=True,
            size_hint=(None, None),
            size=(400, 100),
            pos_hint={'x': 0.05, 'top': 0.85},
            font_size='16sp',
            color=(0.8, 0.8, 1, 1),
            halign='left'
        )
        layout.add_widget(info)

        # ПУТЬ К ФАЙЛУ (попробуйте разные варианты!)
        test_paths = [
            "soccer_64.png",  # 1. В той же папке
            "assets/sprites/sprites_football_ball.png",  # 2. Относительный
            os.path.join(os.getcwd(), "assets", "images", "balls", "sprite_sheets", "soccer_64.png"),  # 3. Абсолютный
        ]

        current_path = ""
        for path in test_paths:
            if os.path.exists(path):
                current_path = path
                print(f"✓ Найден файл: {path}")
                break

        if not current_path:
            print("✗ Ни один файл не найден!")
            current_path = "soccer_64.png"  # Все равно попробуем

        path_label = Label(
            text=f'Файл: [color=88ff88]{current_path}[/color]',
            markup=True,
            size_hint=(None, None),
            size=(600, 30),
            pos_hint={'center_x': 0.5, 'top': 0.7},
            font_size='14sp'
        )
        layout.add_widget(path_label)

        # СОЗДАЕМ МЯЧ
        self.ball = DebugSpriteBall(
            sprite_sheet_path=current_path,
            size_hint=(None, None),
            pos_hint={'center_x': 0.5, 'center_y': 0.5}
        )
        layout.add_widget(self.ball)

        # КНОПКИ УПРАВЛЕНИЯ
        btn_frame = Button(
            text='СЛЕДУЮЩИЙ КАДР',
            size_hint=(None, None),
            size=(200, 60),
            pos_hint={'center_x': 0.3, 'y': 0.1},
            background_color=(0.2, 0.7, 0.2, 1),
            font_size='18sp'
        )
        btn_frame.bind(on_press=lambda x: setattr(self.ball, 'frame_index', self.ball.frame_index + 1))
        layout.add_widget(btn_frame)

        btn_test = Button(
            text='ТЕСТ КЛИКА',
            size_hint=(None, None),
            size=(200, 60),
            pos_hint={'center_x': 0.7, 'y': 0.1},
            background_color=(0.7, 0.2, 0.2, 1),
            font_size='18sp'
        )
        btn_test.bind(on_press=lambda x: print(f"Тест: мяч на позиции {self.ball.pos}, размер {self.ball.size}"))
        layout.add_widget(btn_test)

        # СТАТУС БАР
        self.status = Label(
            text='Готов к работе. Кликните на мяч!',
            size_hint=(None, None),
            size=(500, 30),
            pos_hint={'center_x': 0.5, 'y': 0.02},
            color=(0, 1, 1, 1)
        )
        layout.add_widget(self.status)

        # Обновляем статус при изменении кадра
        self.ball.bind(frame_index=lambda i, v: setattr(
            self.status, 'text', f'Кадр: {v} | Кликните на зеленую область'
        ))

        return layout


if __name__ == '__main__':
    print("=" * 70)
    print("ДЕБАГ МЯЧА С ВИЗУАЛЬНОЙ ОТЛАДКОЙ")
    print("=" * 70)
    print("Даже если текстура не загрузится - вы УВИДИТЕ мяч!")
    print("Зеленый фон = область виджета")
    print("Красная рамка = границы")
    print("=" * 70)

    DebugApp().run()