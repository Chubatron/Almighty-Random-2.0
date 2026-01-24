# components/sprite_sheet_ball.py - ИСПРАВЛЕННАЯ ВЕРСИЯ
from kivy.uix.widget import Widget
from kivy.properties import StringProperty, NumericProperty, ListProperty, ObjectProperty
from kivy.graphics import Rectangle, Color
import os


class SpriteSheetBall(Widget):
    """Виджет мяча с поддержкой спрайт-листа"""

    sprite_sheet_path = StringProperty('')
    ball_size = NumericProperty(100)
    rows = NumericProperty(8)
    cols = NumericProperty(8)
    frame_index = NumericProperty(0)
    rotation_angle = NumericProperty(0)
    velocity = ListProperty([0, 0])

    # Внутренние свойства
    _texture = ObjectProperty(None, allownone=True)

    def __init__(self, **kwargs):
        # ИЗВЛЕКАЕМ sprite_sheet_path ДО вызова super().__init__()
        sprite_path = kwargs.get('sprite_sheet_path', '')

        print(f"\n=== SpriteSheetBall.__init__() ===")
        print(f"sprite_sheet_path из kwargs: '{sprite_path}'")

        super().__init__(**kwargs)

        self.size = (self.ball_size, self.ball_size)

        print(f"После super().__init__():")
        print(f"  self.sprite_sheet_path: '{self.sprite_sheet_path}'")
        print(f"  Размер: {self.size}")
        print(f"  Позиция: {self.pos}")

        # ВАЖНО: Принудительно загружаем текстуру сразу
        if self.sprite_sheet_path:
            print(f"Загружаю текстуру немедленно...")
            self._load_texture_immediate(self.sprite_sheet_path)
        elif sprite_path:
            print(f"Загружаю из kwargs...")
            self._load_texture_immediate(sprite_path)
        else:
            print(f"❌ Нет пути к текстуре!")
            self._draw_debug()

        # Привязываем события для будущих изменений
        self.bind(
            sprite_sheet_path=self._load_texture,
            frame_index=self._update_display,
            pos=self._update_display,
            size=self._update_display
        )

    def _load_texture_immediate(self, path):
        """Загружает текстуру немедленно (без ожидания события)"""
        print(f"\n=== SpriteSheetBall._load_texture_immediate() ===")
        print(f"Путь: {path}")
        print(f"Файл существует: {os.path.exists(path) if path else False}")

        if not path:
            print("❌ Путь пустой!")
            self._draw_debug()
            return

        try:
            from kivy.core.image import Image as CoreImage

            print(f"Пытаюсь загрузить текстуру...")
            self._texture = CoreImage(path).texture

            if not self._texture:
                print("❌ Текстура не загрузилась (None)")
                self._draw_debug()
                return

            print(f"✅ Текстура загружена!")
            print(f"  Размер: {self._texture.width}x{self._texture.height}")
            print(f"  ID: {self._texture.id}")

            if self._texture.width == 0 or self._texture.height == 0:
                print("❌ Текстура имеет нулевой размер!")
                self._draw_debug()
                return

            # Вычисляем размер кадра
            self._frame_width = self._texture.width // self.cols
            self._frame_height = self._texture.height // self.rows

            print(f"  Размер кадра: {self._frame_width}x{self._frame_height}")

            # Немедленно обновляем отображение
            self._update_display()

        except Exception as e:
            print(f"❌ ОШИБКА при загрузке текстуры: {e}")
            import traceback
            traceback.print_exc()
            self._draw_debug()

    def _load_texture(self, instance, path):
        """Загружает текстуру при изменении свойства"""
        print(f"\n=== SpriteSheetBall._load_texture() (по событию) ===")
        self._load_texture_immediate(path)

    def _draw_debug(self):
        """Рисует отладочную графику"""
        self.canvas.clear()

        with self.canvas:
            # 1. ЯРКИЙ КРАСНЫЙ фон
            Color(1, 0, 0, 0.8)
            Rectangle(pos=self.pos, size=self.size)

            # 2. Желтая рамка
            Color(1, 1, 0, 1)
            from kivy.graphics import Line
            Line(rectangle=(self.x, self.y, self.width, self.height), width=3)

            # 3. Белый крест
            Color(1, 1, 1, 1)
            Line(points=[self.x, self.y, self.right, self.top], width=2)
            Line(points=[self.right, self.y, self.x, self.top], width=2)

            # 4. Текст "NO TEXTURE"
            from kivy.core.text import Label as CoreLabel
            text = CoreLabel(text="NO\nTEXTURE", font_size=14)
            text.refresh()

            Color(1, 1, 1, 1)
            Rectangle(
                texture=text.texture,
                pos=(
                    self.center_x - text.texture.width / 2,
                    self.center_y - text.texture.height / 2
                ),
                size=text.texture.size
            )

        print(f"✅ Нарисован отладочный квадрат")

    def _update_display(self, *args):
        """Обновляет отображение с текущим кадром"""
        print(f"\n=== SpriteSheetBall._update_display() ===")
        print(f"Текстура загружена: {self._texture is not None}")

        if not self._texture:
            print("❌ Нет текстуры, рисую отладочный квадрат")
            self._draw_debug()
            return

        if self.width == 0 or self.height == 0:
            print("❌ Нулевой размер виджета")
            return

        total_frames = self.rows * self.cols
        if total_frames == 0:
            print("❌ Нет кадров")
            return

        frame_idx = self.frame_index % total_frames
        row = frame_idx // self.cols
        col = frame_idx % self.cols

        # Координаты текстуры
        tex_left = col / self.cols
        tex_right = (col + 1) / self.cols
        tex_top = row / self.rows
        tex_bottom = (row + 1) / self.rows

        # Kivy использует перевернутые Y-координаты
        tex_coords = (
            tex_left, 1 - tex_bottom,
            tex_right, 1 - tex_bottom,
            tex_right, 1 - tex_top,
            tex_left, 1 - tex_top
        )

        print(f"Кадр {frame_idx} (row={row}, col={col})")
        print(f"Координаты: {tex_coords}")

        self.canvas.clear()

        with self.canvas:
            # 2. Текстура
            Color(1, 1, 1, 1)
            Rectangle(
                pos=self.pos,
                size=self.size,
                texture=self._texture,
                tex_coords=tex_coords
            )

        print(f"✅ Текстура отрисована")