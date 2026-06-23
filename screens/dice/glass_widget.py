"""
Виджет стакана
"""
import os
from kivy.app import App
from kivy.uix.widget import Widget
from kivy.properties import StringProperty, NumericProperty, ObjectProperty, BooleanProperty
from kivy.clock import Clock
from kivy.animation import Animation
from kivy.graphics import Color, Rectangle, PushMatrix, PopMatrix, Rotate, Translate, Line
from PIL import Image as PILImage
from kivy.graphics.texture import Texture
from kivy.core.window import Window
from kivy.utils import platform


class GlassWidget(Widget):
    """Виджет стакана со своим спрайт-листом (2 ряда × 12 колонок)"""

    sprite_sheet_path = StringProperty('')
    glass_size = NumericProperty(100)
    rows = NumericProperty(2)
    cols = NumericProperty(12)
    frame_index = NumericProperty(0)
    rotation_angle = NumericProperty(-90)
    is_raised = BooleanProperty(False)
    touch_zone_scale_x = NumericProperty(1.5)  # Коэффициент увеличения зоны нажатия по горизонтали
    touch_zone_scale_y = NumericProperty(2)  # Коэффициент увеличения зоны нажатия по вертикали

    _texture = ObjectProperty(None, allownone=True)

    def __init__(self, debug_mode=False, **kwargs):
        self.debug_mode = debug_mode
        self.initial_glass_size = kwargs.pop('glass_size', None)
        self.on_glass_click = kwargs.pop('on_glass_click', None)
        self.on_glass_drag = kwargs.pop('on_glass_drag', None)
        self.on_glass_drag_end = kwargs.pop('on_glass_drag_end', None)
        self.is_animating = False
        self.drag_active = False
        self.has_moved_during_drag = False
        self.touch_start_pos = None
        self.touch_start_time = None
        super().__init__(**kwargs)

        if self.sprite_sheet_path and os.path.exists(self.sprite_sheet_path):
            self._load_spritesheet(self.sprite_sheet_path)
        else:
            if self.initial_glass_size:
                self.glass_size = self.initial_glass_size
                self.size = (self.glass_size, self.glass_size)

        self.bind(
            frame_index=self._update_display,
            pos=self._update_display,
            size=self._update_display,
            rotation_angle=self._update_display
        )

    def collide_point(self, x, y):
        """Увеличивает зону нажатия на стакан с разными коэффициентами по горизонтали и вертикали"""
        # Получаем центр виджета
        center_x = self.center_x
        center_y = self.center_y

        # Вычисляем увеличенную зону с разными коэффициентами
        width = self.width * self.touch_zone_scale_x
        height = self.height * self.touch_zone_scale_y

        # Вычисляем границы увеличенной зоны
        left = center_x - width / 2
        bottom = center_y - height / 2
        right = left + width
        top = bottom + height

        # Проверяем, попала ли точка в увеличенную зону
        return left <= x <= right and bottom <= y <= top

    def _load_spritesheet(self, path):
        try:
            img = PILImage.open(path)
            if img.mode != 'RGBA':
                img = img.convert('RGBA')

            self._texture = Texture.create(size=img.size, colorfmt='rgba')
            self._texture.blit_buffer(img.tobytes(), colorfmt='rgba', bufferfmt='ubyte')

            if self.initial_glass_size:
                self.glass_size = self.initial_glass_size
            else:
                if platform == 'android':
                    real_width = Window.system_size[0]
                    self.glass_size = real_width * 0.12
                else:
                    app = App.get_running_app()
                    screen_params = getattr(app, 'screen_params', None)
                    if screen_params:
                        self.glass_size = screen_params.width * 0.12
                    else:
                        self.glass_size = 80

            self.size = (self.glass_size, self.glass_size)
            self._update_display()

        except Exception as e:
            print(f"Error loading glass spritesheet: {e}")

    def _update_display(self, *args):
        if not self._texture or self.width == 0:
            return

        total_frames = self.rows * self.cols
        if total_frames == 0:
            return

        frame_idx = self.frame_index % total_frames
        row = frame_idx // self.cols
        col = frame_idx % self.cols

        tex_left = col / self.cols
        tex_right = (col + 1) / self.cols
        tex_top = row / self.rows
        tex_bottom = (row + 1) / self.rows

        tex_coords = (tex_left, tex_bottom,
                      tex_right, tex_bottom,
                      tex_right, tex_top,
                      tex_left, tex_top)

        self.canvas.clear()

        with self.canvas:
            PushMatrix()
            Translate(self.x + self.width / 2, self.y + self.height / 2)
            Rotate(angle=self.rotation_angle, origin=(0, 0))
            Translate(-(self.x + self.width / 2), -(self.y + self.height / 2))
            Color(1, 1, 1, 1)
            Rectangle(pos=self.pos, size=self.size, texture=self._texture, tex_coords=tex_coords)
            PopMatrix()

        # Рисуем отладочные квадраты ТОЛЬКО если debug_mode = True
        if self.debug_mode:
            self.canvas.after.clear()
            with self.canvas.after:
                # Рисуем оригинальную зону (зеленый контур)
                Color(0, 1, 0, 0.8)
                Line(rectangle=(self.x, self.y, self.width, self.height), width=2)

                # Рисуем увеличенную зону нажатия (красный контур)
                center_x = self.center_x
                center_y = self.center_y
                width = self.width * self.touch_zone_scale_x
                height = self.height * self.touch_zone_scale_y
                left = center_x - width / 2
                bottom = center_y - height / 2
                Color(1, 0, 0, 0.5)
                Line(rectangle=(left, bottom, width, height), width=2)

    def set_frame(self, frame_index):
        total_frames = self.rows * self.cols
        if 0 <= frame_index < total_frames:
            self.frame_index = frame_index
            if frame_index == 0:
                self.is_raised = False
            elif frame_index == total_frames - 1:
                self.is_raised = True

    def set_raised(self, raised):
        total_frames = self.rows * self.cols
        if raised:
            self.set_frame(total_frames - 1)
        else:
            self.set_frame(0)

    def animate_movement(self, start_pos, end_pos, duration, forward=True, callback=None):
        if self.is_animating:
            return

        self.is_animating = True
        total_frames = self.rows * self.cols
        self.pos = start_pos

        if forward:
            frames = list(range(total_frames))
        else:
            frames = list(range(total_frames - 1, -1, -1))

        frame_duration = duration / total_frames

        anim_move = Animation(pos=end_pos, duration=duration)
        anim_move.start(self)

        self._animate_frame_sequence(0, frames, frame_duration, callback)

    def _animate_frame_sequence(self, idx, frames, frame_duration, callback):
        if idx >= len(frames):
            self.frame_index = frames[-1] if frames else 0
            self.is_animating = False
            if callback:
                callback()
            return

        self.frame_index = frames[idx]
        Clock.schedule_once(
            lambda dt: self._animate_frame_sequence(idx + 1, frames, frame_duration, callback),
            frame_duration
        )

    def on_touch_down(self, touch):
        if self.collide_point(*touch.pos) and not self.is_animating:
            if self.parent and hasattr(self.parent, 'is_glass_blocked') and self.parent.is_glass_blocked:
                if self.debug_mode:
                    print("🔒 [WIDGET] Стакан заблокирован, клик игнорируется")
                return True

            self.drag_active = True
            self.has_moved_during_drag = False
            self.touch_start_pos = (touch.x, touch.y)
            self.touch_start_time = Clock.get_time()
            if self.debug_mode:
                print(f"🟢 [WIDGET] on_touch_down: начали перетаскивание, pos={self.touch_start_pos}")
            return True
        return super().on_touch_down(touch)

    def on_touch_move(self, touch):
        if self.drag_active:
            if self.parent and hasattr(self.parent, 'is_glass_blocked') and self.parent.is_glass_blocked:
                if self.debug_mode:
                    print("🔒 [WIDGET] Стакан заблокирован, движение игнорируется")
                return True

            if self.touch_start_pos:
                delta_x = touch.x - self.touch_start_pos[0]
                delta_y = touch.y - self.touch_start_pos[1]

                if abs(delta_x) > 5 or abs(delta_y) > 5:
                    self.has_moved_during_drag = True
                    if self.debug_mode:
                        print(f"🟡 [WIDGET] on_touch_move: delta=({delta_x:.1f}, {delta_y:.1f})")
                    if self.on_glass_drag:
                        self.on_glass_drag(delta_x, delta_y, touch)
                    self.touch_start_pos = (touch.x, touch.y)
            return True
        return super().on_touch_move(touch)

    def on_touch_up(self, touch):
        if self.debug_mode:
            print(f"🟢 [WIDGET] on_touch_up: drag_active={self.drag_active}, has_moved={self.has_moved_during_drag}")
        if self.drag_active:
            if self.parent and hasattr(self.parent, 'is_glass_blocked') and self.parent.is_glass_blocked:
                if self.debug_mode:
                    print("🔒 [WIDGET] Стакан заблокирован, клик игнорируется")
                self.drag_active = False
                self.has_moved_during_drag = False
                self.touch_start_pos = None
                self.touch_start_time = None
                return True

            touch_duration = Clock.get_time() - self.touch_start_time

            if not self.has_moved_during_drag and touch_duration < 0.3 and self.on_glass_click:
                if self.debug_mode:
                    print(f"   👆 Это клик")
                self.on_glass_click()
            elif self.has_moved_during_drag and self.on_glass_drag_end:
                if self.debug_mode:
                    print(f"   ✋ Это окончание перетаскивания")
                self.on_glass_drag_end(touch)

            self.drag_active = False
            self.has_moved_during_drag = False
            self.touch_start_pos = None
            self.touch_start_time = None
            return True
        return super().on_touch_up(touch)