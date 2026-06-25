# history_popup.py
from kivy.uix.popup import Popup
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.scrollview import ScrollView
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.scatter import Scatter
from kivy.uix.image import Image
from kivy.graphics import Color, Rectangle, Line
from kivy.clock import Clock
from kivy.core.window import Window
from kivy.uix.behaviors import ButtonBehavior
from kivy.uix.relativelayout import RelativeLayout
import os
import re

from sound_manager import SoundManager

# History file
HISTORY_FILE = 'random_numbers_history.txt'

# Глобальная ссылка на экран для сброса счётчика
_random_number_screen_ref = None

# Путь к изображению для кнопок (относительный)
BUTTON_IMAGE_PATH = 'assets/images/buttons/Roulette_switch_button.png'


def set_random_number_screen(screen):
    """Устанавливает ссылку на экран RandomNumberScreen"""
    global _random_number_screen_ref
    _random_number_screen_ref = screen


class ImageButton(ButtonBehavior, RelativeLayout):
    """Кнопка с изображением и текстом по центру"""

    def __init__(self, text="", **kwargs):
        if 'text' in kwargs:
            text = kwargs.pop('text')

        super().__init__(**kwargs)

        # Создаем изображение
        self.image = Image(
            source=BUTTON_IMAGE_PATH,
            allow_stretch=True,
            keep_ratio=True,
            size_hint=(1, 1),
            pos_hint={'center_x': 0.5, 'center_y': 0.5}
        )
        self.add_widget(self.image)

        # Создаем текст поверх изображения (ЧЕРНЫЙ ЦВЕТ)
        self.label = Label(
            text=text,
            font_size=18,
            bold=True,
            color=(0, 0, 0, 1),
            size_hint=(1, 1),
            pos_hint={'center_x': 0.5, 'center_y': 0.5},
            halign='center',
            valign='middle'
        )
        self.add_widget(self.label)

        # РАМКА НА ВСЮ КНОПКУ
        self.debug_overlay = RelativeLayout(
            size_hint=(1, 1),
            pos_hint={'center_x': 0.5, 'center_y': 0.5}
        )

        self.debug_rect_coords = (0, 0, self.debug_overlay.width, self.debug_overlay.height)

        with self.debug_overlay.canvas.before:
            self.debug_color = Color(1, 0, 0, 0)
            self.debug_bg = Rectangle(
                pos=(0, 0),
                size=self.debug_overlay.size
            )

        with self.debug_overlay.canvas.after:
            self.debug_border_color = Color(1, 0, 1, 0)
            self.debug_rect = Line(
                rectangle=self.debug_rect_coords,
                width=3
            )

        self.debug_overlay.bind(size=self._update_debug_overlay, pos=self._update_debug_overlay)
        self.debug_overlay.bind(size=self._update_debug_rect, pos=self._update_debug_rect)

        self.add_widget(self.debug_overlay)

        self.button_name = text
        self._sound_manager = SoundManager()

    def _update_debug_overlay(self, *args):
        if hasattr(self, 'debug_bg'):
            self.debug_bg.size = self.debug_overlay.size

    def _update_debug_rect(self, *args):
        if hasattr(self, 'debug_rect'):
            self.debug_rect_coords = (0, 0, self.debug_overlay.width, self.debug_overlay.height)
            self.debug_rect.rectangle = self.debug_rect_coords

    def on_press(self):
        print(f"[DEBUG BUTTON] ImageButton нажата - ВЫПОЛНЯЮ ДЕЙСТВИЕ!")
        if hasattr(self, 'debug_color'):
            self.debug_color.rgba = (0, 1, 0, 0.5)
        super().on_press()

    def on_release(self):
        print(f"[DEBUG BUTTON] ImageButton отпущена")
        if hasattr(self, 'debug_color'):
            self.debug_color.rgba = (1, 0, 0, 0.3)
        super().on_release()

    def get_rect_global(self):
        """Возвращает глобальные координаты розового прямоугольника (debug_overlay)"""
        # Получаем координаты debug_overlay
        x1, y1 = self.debug_overlay.to_window(0, 0)
        x2, y2 = self.debug_overlay.to_window(self.debug_overlay.width, self.debug_overlay.height)

        min_x = min(x1, x2)
        max_x = max(x1, x2)
        min_y = min(y1, y2)
        max_y = max(y1, y2)

        return min_x, min_y, max_x, max_y

    def collide_point(self, x, y):
        """Проверка попадания по розовому прямоугольнику"""
        min_x, min_y, max_x, max_y = self.get_rect_global()
        result = (min_x <= x <= max_x and min_y <= y <= max_y)

        print(f"[DEBUG COLLIDE IMAGE] Кнопка: {self.label.text}")
        print(f"  Зона: x={min_x:.2f}..{max_x:.2f}, y={min_y:.2f}..{max_y:.2f}")
        print(f"  Размер: {max_x - min_x:.2f}x{max_y - min_y:.2f}")
        print(f"  Точка касания: ({x:.2f}, {y:.2f})")
        print(f"  Результат: {result}")

        return result


class DebugPopup(Popup):
    """Popup с отладкой всех касаний"""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._debug_info_printed = False
        self._sound_manager = SoundManager()

        # Загружаем звук для кнопок CLEAR и CLOSE
        self._click_sound = None
        self._load_click_sound()

    def _load_click_sound(self):
        """Загружает звук нажатия кнопки - set_value2.mp3"""
        try:
            from kivy.core.audio import SoundLoader
            sound_path = 'assets/sounds/r_number/set_value2.mp3'
            if os.path.exists(sound_path):
                self._click_sound = SoundLoader.load(sound_path)
                if self._click_sound:
                    self._click_sound.volume = 0.6
                    print(f"[SOUND] Загружен звук для кнопок CLEAR/CLOSE: {sound_path}")
            else:
                print(f"[SOUND] Файл не найден: {sound_path}")
        except Exception as e:
            print(f"[SOUND] Ошибка загрузки звука: {e}")

    def play_click_sound(self):
        """Воспроизводит звук нажатия кнопки (проверяет mute)"""
        if self._sound_manager.is_muted():
            return
        if self._click_sound:
            try:
                if self._click_sound.state == 'play':
                    self._click_sound.stop()
                self._click_sound.play()
                print(f"[SOUND] Воспроизведен звук для CLEAR/CLOSE")
            except Exception as e:
                print(f"[SOUND] Ошибка воспроизведения звука: {e}")

    def print_zone_info(self, button_name, min_x, min_y, max_x, max_y, touch_x, touch_y, hit):
        """Выводит подробную информацию о зоне и касании"""
        print(f"\n{'=' * 70}")
        print(f"🔴 [ЗОНА] {button_name}")
        print(f"{'=' * 70}")
        print(f"📐 КООРДИНАТЫ ЗОНЫ:")
        print(f"   X: {min_x:.2f} .. {max_x:.2f}  (ширина: {max_x - min_x:.2f})")
        print(f"   Y: {min_y:.2f} .. {max_y:.2f}  (высота: {max_y - min_y:.2f})")
        print(f"   Центр зоны: ({(min_x + max_x) / 2:.2f}, {(min_y + max_y) / 2:.2f})")
        print(f"📌 КООРДИНАТЫ КАСАНИЯ:")
        print(f"   X: {touch_x:.2f}")
        print(f"   Y: {touch_y:.2f}")
        print(f"🎯 РЕЗУЛЬТАТ ПОПАДАНИЯ: {'✅ ДА' if hit else '❌ НЕТ'}")
        if hit:
            print(f"   Относительное положение в зоне:")
            rel_x = ((touch_x - min_x) / (max_x - min_x)) * 100 if (max_x - min_x) > 0 else 0
            rel_y = ((touch_y - min_y) / (max_y - min_y)) * 100 if (max_y - min_y) > 0 else 0
            print(f"   X: {rel_x:.1f}%  Y: {rel_y:.1f}%")
        print(f"{'=' * 70}\n")

    def print_all_rects(self):
        """Выводит координаты всех розовых прямоугольников"""
        print(f"\n{'=' * 70}")
        print(f"📍 [DEBUG] КООРДИНАТЫ РОЗОВЫХ ПРЯМОУГОЛЬНИКОВ")
        print(f"{'=' * 70}")

        if hasattr(self, 'clear_btn'):
            min_x, min_y, max_x, max_y = self.clear_btn.get_rect_global()
            print(f"🔴 CLEAR (розовый прямоугольник):")
            print(f"   X: {min_x:.2f} .. {max_x:.2f}  (ширина: {max_x - min_x:.2f})")
            print(f"   Y: {min_y:.2f} .. {max_y:.2f}  (высота: {max_y - min_y:.2f})")
            print(f"   Центр: ({(min_x + max_x) / 2:.2f}, {(min_y + max_y) / 2:.2f})")
            print(f"   Размер прямоугольника: {self.clear_btn.debug_overlay.size}")

        if hasattr(self, 'close_btn'):
            min_x, min_y, max_x, max_y = self.close_btn.get_rect_global()
            print(f"🟢 CLOSE (розовый прямоугольник):")
            print(f"   X: {min_x:.2f} .. {max_x:.2f}  (ширина: {max_x - min_x:.2f})")
            print(f"   Y: {min_y:.2f} .. {max_y:.2f}  (высота: {max_y - min_y:.2f})")
            print(f"   Центр: ({(min_x + max_x) / 2:.2f}, {(min_y + max_y) / 2:.2f})")
            print(f"   Размер прямоугольника: {self.close_btn.debug_overlay.size}")

        print(f"{'=' * 70}\n")

    def on_touch_down(self, touch):
        """Отладка всех касаний в окне с визуализацией зон и вызовом функций"""

        # Выводим координаты прямоугольников при первом касании
        if not self._debug_info_printed:
            Clock.schedule_once(lambda dt: self.print_all_rects(), 0.1)
            self._debug_info_printed = True

        print(f"\n{'=' * 60}")
        print(f"👆 [TOUCH] КАСАНИЕ")
        print(f"   Координаты: ({touch.x:.2f}, {touch.y:.2f})")
        print(f"   Размер окна: {Window.width} x {Window.height}")
        print(f"{'=' * 60}")

        # Проверяем CLEAR
        if hasattr(self, 'clear_btn'):
            try:
                min_x, min_y, max_x, max_y = self.clear_btn.get_rect_global()
                hit = self.clear_btn.collide_point(touch.x, touch.y)

                self.print_zone_info("CLEAR", min_x, min_y, max_x, max_y, touch.x, touch.y, hit)

                if hit:
                    print(f"✅ [ACTION] CLEAR: ПОПАДАНИЕ! ВЫЗЫВАЮ clear_history()")
                    if hasattr(self.clear_btn, 'debug_color'):
                        self.clear_btn.debug_color.rgba = (0, 1, 1, 0.0)
                    self.clear_history(self.clear_btn)
                    return True
            except Exception as e:
                print(f"❌ [ERROR] Ошибка при проверке CLEAR: {e}")

        # Проверяем CLOSE
        if hasattr(self, 'close_btn'):
            try:
                min_x, min_y, max_x, max_y = self.close_btn.get_rect_global()
                hit = self.close_btn.collide_point(touch.x, touch.y)

                self.print_zone_info("CLOSE", min_x, min_y, max_x, max_y, touch.x, touch.y, hit)

                if hit:
                    print(f"✅ [ACTION] CLOSE: ПОПАДАНИЕ! ВЫЗЫВАЮ on_close_press()")
                    if hasattr(self.close_btn, 'debug_color'):
                        self.close_btn.debug_color.rgba = (0, 1, 1, 0)
                    self.on_close_press(self.close_btn)
                    return True
            except Exception as e:
                print(f"❌ [ERROR] Ошибка при проверке CLOSE: {e}")

        print(f"❌ [TOUCH] Касание вне зон кнопок")
        print(f"{'=' * 60}\n")
        return super().on_touch_down(touch)


class RotatedButton(Button):
    """Кнопка с корректной обработкой касаний при повороте на -90 градусов"""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self.debug_overlay = RelativeLayout(
            size_hint=(1, 1),
            pos_hint={'center_x': 0.5, 'center_y': 0.5}
        )

        self.debug_rect_coords = (0, 0, self.debug_overlay.width, self.debug_overlay.height)

        with self.debug_overlay.canvas.before:
            self.debug_color = Color(0, 1, 1, 0.3)
            self.debug_bg = Rectangle(
                pos=(0, 0),
                size=self.debug_overlay.size
            )

        with self.debug_overlay.canvas.after:
            self.debug_border_color = Color(1, 1, 0, 1)
            self.debug_rect = Line(
                rectangle=self.debug_rect_coords,
                width=3
            )

        self.debug_overlay.bind(size=self._update_debug_overlay, pos=self._update_debug_overlay)
        self.debug_overlay.bind(size=self._update_debug_rect, pos=self._update_debug_rect)

        self.add_widget(self.debug_overlay)
        self._sound_manager = SoundManager()

    def _update_debug_overlay(self, *args):
        if hasattr(self, 'debug_bg'):
            self.debug_bg.size = self.debug_overlay.size

    def _update_debug_rect(self, *args):
        if hasattr(self, 'debug_rect'):
            self.debug_rect_coords = (0, 0, self.debug_overlay.width, self.debug_overlay.height)
            self.debug_rect.rectangle = self.debug_rect_coords

    def on_touch_down(self, touch):
        print(f"[DEBUG BUTTON] RotatedButton {self.text} - on_touch_down вызван")
        if hasattr(self, 'debug_color'):
            self.debug_color.rgba = (0, 1, 0, 0.5)
        return super().on_touch_down(touch)

    def on_touch_up(self, touch):
        print(f"[DEBUG BUTTON] RotatedButton {self.text} - on_touch_up вызван")
        if hasattr(self, 'debug_color'):
            self.debug_color.rgba = (0, 1, 1, 0.3)
        return super().on_touch_up(touch)

    def get_rect_global(self):
        """Возвращает глобальные координаты желтого прямоугольника"""
        x1, y1 = self.debug_overlay.to_window(0, 0)
        x2, y2 = self.debug_overlay.to_window(self.debug_overlay.width, self.debug_overlay.height)

        min_x = min(x1, x2)
        max_x = max(x1, x2)
        min_y = min(y1, y2)
        max_y = max(y1, y2)

        return min_x, min_y, max_x, max_y

    def collide_point(self, x, y):
        """Проверка попадания по желтому прямоугольнику"""
        min_x, min_y, max_x, max_y = self.get_rect_global()
        result = (min_x <= x <= max_x and min_y <= y <= max_y)

        print(f"[DEBUG COLLIDE] Кнопка: {self.text}")
        print(f"  Желтый прямоугольник: x={min_x:.2f}..{max_x:.2f}, y={min_y:.2f}..{max_y:.2f}")
        print(f"  Точка касания: ({x:.2f}, {y:.2f})")
        print(f"  Результат: {result}")

        return result


class HistoryPopup(DebugPopup):
    """Window to display number history (rotated 90 degrees)"""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.title = ""
        self.size_hint = (1, 0.9)
        self.auto_dismiss = True
        self.background_color = [0, 0, 0, 0]

        print(f"[DEBUG HISTORY] ===== Создание HistoryPopup =====")

        main_layout = FloatLayout()

        background_file = 'assets/backgrounds/history_popup.png'

        self.bg_image = None
        if os.path.exists(background_file):
            try:
                self.bg_image = Image(
                    source=background_file,
                    size_hint=(1, 1),
                    pos_hint={'x': 0, 'y': 0},
                    allow_stretch=True,
                    keep_ratio=False
                )
                main_layout.add_widget(self.bg_image)
                print(f"[DEBUG HISTORY] Фоновое изображение добавлено как Image виджет: {background_file}")
            except Exception as e:
                print(f"[DEBUG HISTORY] Ошибка загрузки фона: {e}")
                import traceback
                traceback.print_exc()
        else:
            print(f"[DEBUG HISTORY] Файл фона не найден: {background_file}")

        self.scatter = Scatter(
            size_hint=(1, 1),
            pos_hint={'x': 0, 'y': 0},
            do_rotation=False,
            do_scale=False,
            do_translation=False,
            rotation=-90,
            opacity=0.85
        )

        print(f"[DEBUG HISTORY] Scatter создан: rotation={self.scatter.rotation}, opacity={self.scatter.opacity}")

        self.layout = BoxLayout(orientation='vertical', padding=10, spacing=10)
        self.layout.size_hint = (None, None)

        with self.layout.canvas.before:
            Color(0, 0, 0, 0)
            self.layout_bg = Rectangle(pos=self.layout.pos, size=self.layout.size)
            self.layout.bind(pos=self._update_layout_bg, size=self._update_layout_bg)

        scroll = ScrollView(
            size_hint=(1, 1),
            bar_width=0,
            bar_color=(0, 0, 0, 0),
            bar_inactive_color=(0, 0, 0, 0),
            scroll_type=['bars', 'content'],
            do_scroll_x=False,
            do_scroll_y=True
        )

        with scroll.canvas.before:
            Color(0, 0, 0, 0)
            self.scroll_bg = Rectangle(pos=scroll.pos, size=scroll.size)
            scroll.bind(pos=self._update_scroll_bg, size=self._update_scroll_bg)

        self.content_layout = BoxLayout(orientation='vertical', size_hint_y=None, spacing=5)
        self.content_layout.bind(minimum_height=self.content_layout.setter('height'))

        with self.content_layout.canvas.before:
            Color(0, 0, 0, 0)
            self.content_bg = Rectangle(pos=self.content_layout.pos, size=self.content_layout.size)
            self.content_layout.bind(pos=self._update_content_bg, size=self._update_content_bg)

        scroll.add_widget(self.content_layout)
        self.layout.add_widget(scroll)

        buttons_layout = BoxLayout(orientation='horizontal', size_hint=(1, None), height=50, spacing=10)

        if os.path.exists(BUTTON_IMAGE_PATH):
            print(f"[DEBUG HISTORY] Изображение для кнопок найдено: {BUTTON_IMAGE_PATH}")

            self.clear_btn = ImageButton(
                text="CLEAR",
                size_hint=(1, 1)
            )
            self.clear_btn.bind(on_press=self.clear_history)

            self.close_btn = ImageButton(
                text="CLOSE",
                size_hint=(1, 1)
            )
            self.close_btn.bind(on_press=self.on_close_press)

        else:
            print(f"[DEBUG HISTORY] Изображение для кнопок НЕ НАЙДЕНО: {BUTTON_IMAGE_PATH}")
            print(f"[DEBUG HISTORY] Использую стандартные кнопки с текстом")

            self.clear_btn = RotatedButton(
                text="CLEAR",
                font_size=20,
                background_color=(0.8, 0.2, 0.2, 0.7),
                color=(1, 1, 1, 1)
            )
            self.clear_btn.bind(on_press=self.clear_history)

            self.close_btn = RotatedButton(
                text="CLOSE",
                font_size=20,
                background_color=(0.2, 0.6, 0.2, 0.7),
                color=(1, 1, 1, 1)
            )
            self.close_btn.bind(on_press=self.on_close_press)

        buttons_layout.add_widget(self.clear_btn)
        buttons_layout.add_widget(self.close_btn)
        self.layout.add_widget(buttons_layout)

        self.scatter.add_widget(self.layout)
        main_layout.add_widget(self.scatter)
        self.add_widget(main_layout)

        self.scatter.bind(size=self._adjust_layout_size)

        print(f"[DEBUG HISTORY] Popup создан, size_hint={self.size_hint}")

        Clock.schedule_once(lambda dt: self.load_history(), 0.2)
        Clock.schedule_once(self._print_debug_info, 0.3)

    def _update_layout_bg(self, *args):
        if hasattr(self, 'layout_bg') and self.layout:
            self.layout_bg.pos = self.layout.pos
            self.layout_bg.size = self.layout.size

    def _update_scroll_bg(self, *args):
        if hasattr(self, 'scroll_bg') and hasattr(self, 'layout'):
            for child in self.layout.children:
                if isinstance(child, ScrollView):
                    self.scroll_bg.pos = child.pos
                    self.scroll_bg.size = child.size
                    break

    def _update_content_bg(self, *args):
        if hasattr(self, 'content_bg') and self.content_layout:
            self.content_bg.pos = self.content_layout.pos
            self.content_bg.size = self.content_layout.size

    def on_touch_down(self, touch):
        print(f"\n[DEBUG HISTORY POPUP] Касание в окне истории")
        print(f"  Координаты: ({touch.x:.2f}, {touch.y:.2f})")
        return super().on_touch_down(touch)

    def on_close_press(self, instance):
        print(f"[DEBUG HISTORY] НАЖАТА КНОПКА CLOSE - ЗАКРЫВАЮ POPUP")
        # Воспроизводим звук (проверяет mute внутри)
        self.play_click_sound()
        # Закрываем попап
        self.dismiss()

    def clear_history(self, instance):
        print(f"[DEBUG HISTORY] НАЖАТА КНОПКА CLEAR - ВЫПОЛНЯЮ ОЧИСТКУ")
        # Воспроизводим звук (проверяет mute внутри)
        self.play_click_sound()

        try:
            if os.path.exists(HISTORY_FILE):
                os.remove(HISTORY_FILE)
                print(f"[DEBUG HISTORY] Файл истории удалён: {HISTORY_FILE}")
            else:
                print(f"[DEBUG HISTORY] Файл истории не существует")

            self.reset_counter()
            self.load_history()

        except Exception as e:
            print(f"[DEBUG HISTORY] Ошибка очистки истории: {e}")

    def reset_counter(self):
        global _random_number_screen_ref
        try:
            if _random_number_screen_ref:
                _random_number_screen_ref.reset_history_state()
                print(f"[DEBUG HISTORY] Счётчик сброшен через глобальную ссылку")
            else:
                print(f"[DEBUG HISTORY] Ссылка на экран не найдена, ищу в дереве...")
                parent = self
                while parent:
                    if parent.__class__.__name__ == 'RandomNumberScreen':
                        if hasattr(parent, 'reset_history_state'):
                            parent.reset_history_state()
                            print(f"[DEBUG HISTORY] Счётчик сброшен через дерево")
                            break
                    parent = parent.parent
        except Exception as e:
            print(f"[DEBUG HISTORY] Ошибка сброса счётчика: {e}")

    def _adjust_layout_size(self, instance, value):
        if hasattr(self, 'layout'):
            visual_width = self.scatter.height
            visual_height = self.scatter.width

            layout_x = (self.scatter.width - visual_width) / 2
            layout_y = (self.scatter.height - visual_height) / 2

            offset_y = self.scatter.height - self.scatter.width
            layout_y = layout_y - offset_y / 2
            layout_x = layout_y - offset_y

            self.layout.size = (visual_width, visual_height)
            self.layout.pos = (layout_x, layout_y)

            print(f"[DEBUG HISTORY] Adjusted layout: size={self.layout.size}, pos={self.layout.pos}")
            print(f"[DEBUG HISTORY] Scatter: size={self.scatter.size}")
            print(f"[DEBUG HISTORY] Offset Y: {offset_y}")

    def _print_debug_info(self, dt):
        print(f"[DEBUG HISTORY] ===== ПОЗИЦИИ ВИДЖЕТОВ =====")
        print(f"[DEBUG HISTORY] Размер окна: {Window.width} x {Window.height}")
        print(f"[DEBUG HISTORY] Popup size: {self.size}, pos: {self.pos}")
        print(f"[DEBUG HISTORY] Popup background_color: {self.background_color}")

        if hasattr(self, 'bg_image') and self.bg_image:
            print(f"[DEBUG HISTORY] BG Image size: {self.bg_image.size}, pos: {self.bg_image.pos}")

        if hasattr(self, 'scatter') and self.scatter:
            print(f"[DEBUG HISTORY] Scatter size: {self.scatter.size}, pos: {self.scatter.pos}")
            print(f"[DEBUG HISTORY] Scatter center: {self.scatter.center}")
            print(f"[DEBUG HISTORY] Scatter rotation: {self.scatter.rotation}")
            print(f"[DEBUG HISTORY] Scatter opacity: {self.scatter.opacity}")

        if hasattr(self, 'layout') and self.layout:
            print(f"[DEBUG HISTORY] Layout size: {self.layout.size}, pos: {self.layout.pos}")

        if hasattr(self, 'clear_btn') and self.clear_btn:
            print(f"[DEBUG HISTORY] Clear button: pos={self.clear_btn.pos}, size={self.clear_btn.size}")

        if hasattr(self, 'close_btn') and self.close_btn:
            print(f"[DEBUG HISTORY] Close button: pos={self.close_btn.pos}, size={self.close_btn.size}")

        if hasattr(self, 'content_layout') and self.content_layout:
            print(f"[DEBUG HISTORY] Content layout size: {self.content_layout.size}, pos={self.content_layout.pos}")
            print(f"[DEBUG HISTORY] Количество элементов в истории: {len(self.content_layout.children)}")

        print(f"[DEBUG HISTORY] ==================================")

    def load_history(self):
        print(f"[DEBUG HISTORY] Загрузка истории из файла: {HISTORY_FILE}")
        self.content_layout.clear_widgets()

        if not os.path.exists(HISTORY_FILE):
            print(f"[DEBUG HISTORY] Файл истории не найден")
            empty_label = Label(text="History is empty\n\nGenerate at least one number",
                                font_size=18, color=(0.8, 0.8, 0.8, 1), size_hint_y=None, height=100)
            self.content_layout.add_widget(empty_label)
            return

        try:
            with open(HISTORY_FILE, 'r', encoding='utf-8') as f:
                lines = f.readlines()

            print(f"[DEBUG HISTORY] Прочитано строк из файла: {len(lines)}")

            print(f"[DEBUG HISTORY] ===== СОДЕРЖИМОЕ ФАЙЛА =====")
            for i, line in enumerate(lines):
                print(f"[DEBUG HISTORY] Строка {i}: '{line.strip()}'")
            print(f"[DEBUG HISTORY] ===============================")

            if not lines:
                empty_label = Label(text="History is empty", font_size=18, color=(0.8, 0.8, 0.8, 1))
                self.content_layout.add_widget(empty_label)
                return

            MAX_DISPLAY_ITEMS = 100
            if len(lines) > MAX_DISPLAY_ITEMS:
                lines = lines[-MAX_DISPLAY_ITEMS:]
                print(f"[DEBUG HISTORY] Отображаем последние {MAX_DISPLAY_ITEMS} записей")
            else:
                print(f"[DEBUG HISTORY] Отображаем все {len(lines)} записей")

            for line in lines:
                line = line.strip()
                if not line:
                    continue

                if line.startswith('===') or line.startswith('---'):
                    continue

                is_range = False
                if ' - ' in line:
                    parts = line.split(' - ')
                    if len(parts) == 2:
                        try:
                            int(parts[0].strip())
                            int(parts[1].strip())
                            is_range = True
                        except ValueError:
                            pass

                if is_range:
                    label = Label(
                        text=line,
                        font_size=18,
                        bold=True,
                        color=(0.2, 0.8, 1, 1),
                        size_hint_y=None,
                        height=35
                    )
                    print(f"[DEBUG HISTORY] Добавлен диапазон: {line}")
                    self.content_layout.add_widget(label)
                elif line.strip().startswith('#'):
                    label = Label(
                        text=line,
                        font_size=17,
                        color=(1, 1, 1, 0.9),
                        size_hint_y=None,
                        height=28
                    )
                    print(f"[DEBUG HISTORY] Добавлено число: {line}")
                    self.content_layout.add_widget(label)
                else:
                    label = Label(
                        text=line,
                        font_size=16,
                        color=(0.8, 0.8, 0.8, 1),
                        size_hint_y=None,
                        height=30
                    )
                    print(f"[DEBUG HISTORY] Неизвестная строка: {line}")
                    self.content_layout.add_widget(label)

            print(f"[DEBUG HISTORY] Всего добавлено виджетов: {len(self.content_layout.children)}")

            Clock.schedule_once(self._scroll_to_bottom, 0.15)

        except Exception as e:
            print(f"[DEBUG HISTORY] Ошибка загрузки истории: {e}")
            import traceback
            traceback.print_exc()
            error_label = Label(text=f"Error loading history: {e}",
                                font_size=16, color=(1, 0, 0, 1))
            self.content_layout.add_widget(error_label)

    def _scroll_to_bottom(self, dt):
        try:
            scroll = self.content_layout.parent
            while scroll and not isinstance(scroll, ScrollView):
                scroll = scroll.parent

            if scroll and isinstance(scroll, ScrollView):
                scroll.scroll_y = 0
                print(f"[DEBUG HISTORY] Прокрутка вниз выполнена")
        except Exception as e:
            print(f"[DEBUG HISTORY] Ошибка прокрутки: {e}")