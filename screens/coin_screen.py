from kivy.uix.screenmanager import Screen
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.image import Image
from kivy.uix.label import Label
from kivy.uix.widget import Widget
from kivy.animation import Animation
from kivy.clock import Clock
from kivy.properties import NumericProperty, BooleanProperty, ColorProperty, ListProperty
from kivy.core.window import Window
from kivy.graphics import Color, Ellipse, Rectangle, PushMatrix, PopMatrix, Rotate, Translate
from kivy.core.image import Image as CoreImage
import random
import os

from screens.base_game_screen import BaseGameScreen


class TouchArea(Widget):
    """Область для нажатия с визуальной подсветкой"""
    highlight_color = ColorProperty((0, 1, 0, 0.3))  # Зеленый полупрозрачный
    is_pressed = BooleanProperty(False)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.touch_pos = (0, 0)
        self.bind(pos=self._update_rect, size=self._update_rect)

    def on_touch_down(self, touch):
        if self.collide_point(*touch.pos):
            self.is_pressed = True
            self.touch_pos = touch.pos
            self.show_touch_feedback()
            print(f"🟢 Нажатие в области: {touch.pos}")
            return True
        return super().on_touch_down(touch)

    def on_touch_up(self, touch):
        if self.collide_point(*touch.pos):
            self.is_pressed = False
            self.hide_touch_feedback()
            return True
        return super().on_touch_up(touch)

    def show_touch_feedback(self):
        """Показывает визуальную обратную связь при нажатии"""
        self.canvas.clear()
        with self.canvas:
            # Рисуем круг в месте нажатия
            Color(*self.highlight_color)
            Ellipse(pos=(self.touch_pos[0] - 40, self.touch_pos[1] - 40), size=(80, 80))
            # Рисуем контур
            Color(0, 1, 0, 0.8)
            Ellipse(pos=(self.touch_pos[0] - 40, self.touch_pos[1] - 40), size=(80, 80), width=2)

        # Автоматически скрываем через 0.3 секунды
        Clock.schedule_once(lambda dt: self.hide_touch_feedback(), 0.3)

    def hide_touch_feedback(self):
        """Скрывает обратную связь"""
        self.canvas.clear()

    def _update_rect(self, *args):
        """Обновляет фон области"""
        self.canvas.before.clear()
        with self.canvas.before:
            # Полупрозрачный фон для визуализации области (для отладки)
            Color(0.5, 0.5, 0.5, 0.1)
            Rectangle(pos=self.pos, size=self.size)


class SpritesheetCoin(Image):
    """Монета из спрайт-листа с поворотом на 90 градусов вокруг центра"""
    current_frame = NumericProperty(0)
    is_animating = BooleanProperty(False)
    frames = ListProperty([])
    rotation_angle = NumericProperty(-90)  # Поворот на 90 градусов

    def __init__(self, spritesheet_path, frame_width=64, frame_height=64,
                 cols=5, rows=4, total_frames=20, **kwargs):
        super().__init__(**kwargs)

        self.frame_width = frame_width
        self.frame_height = frame_height
        self.cols = cols
        self.rows = rows
        self.total_frames = min(total_frames, cols * rows)
        self.anim_clock = None

        # Загружаем спрайт-лист
        self.load_spritesheet(spritesheet_path)

        # Применяем поворот
        self.bind(texture=self._update_rotation)
        self.bind(pos=self._update_rotation, size=self._update_rotation)
        self.bind(rotation_angle=self._update_rotation)

    def load_spritesheet(self, spritesheet_path):
        """Загружает и нарезает спрайт-лист"""
        if not os.path.exists(spritesheet_path):
            print(f"❌ Файл не найден: {spritesheet_path}")
            return

        try:
            img = CoreImage(spritesheet_path)
            texture = img.texture
            if not texture:
                print("❌ Не удалось загрузить текстуру")
                return

            tex_width, tex_height = texture.size
            print(f"📐 Размер спрайт-листа: {tex_width}x{tex_height}")

            frame_w = min(self.frame_width, tex_width // self.cols)
            frame_h = min(self.frame_height, tex_height // self.rows)
            print(f"🖼️ Размер кадра: {frame_w}x{frame_h}")

            self.frames = []
            for i in range(self.total_frames):
                row = i // self.cols
                col = i % self.cols
                x = col * frame_w
                y = (self.rows - 1 - row) * frame_h
                try:
                    frame = texture.get_region(x, y, frame_w, frame_h)
                    self.frames.append(frame)
                except Exception as e:
                    print(f"❌ Ошибка кадра {i}: {e}")

            print(f"✅ Загружено кадров: {len(self.frames)}")

            # Устанавливаем первый кадр и применяем поворот
            if self.frames:
                self.texture = self.frames[0]
                # Явно вызываем обновление поворота после загрузки
                Clock.schedule_once(lambda dt: self._update_rotation(), 0)

        except Exception as e:
            print(f"❌ Ошибка загрузки спрайт-листа: {e}")

    def _update_rotation(self, *args):
        """Обновляет поворот изображения вокруг центра"""
        if not self.texture:
            return

        # Полностью очищаем canvas
        self.canvas.clear()

        with self.canvas:
            # Сохраняем текущую матрицу
            PushMatrix()

            # Смещаемся к центру виджета, поворачиваем, возвращаемся обратно
            # Это гарантирует поворот вокруг центра
            Translate(self.center_x, self.center_y)
            Rotate(angle=self.rotation_angle, origin=(0, 0))
            Translate(-self.center_x, -self.center_y)

            # Делаем изображение ярче
            Color(1.3, 1.3, 1.3, 1)

            # Рисуем текстуру
            Rectangle(texture=self.texture, pos=self.pos, size=self.size)

            # Восстанавливаем матрицу
            PopMatrix()

    def start_animation(self, loop_count=6, fps=30):
        """Запускает анимацию вращения"""
        if not self.frames or self.is_animating:
            return
        self.is_animating = True
        self.current_frame = 0
        self.loops_done = 0
        self.loop_count = loop_count
        self.frame_duration = 1.0 / fps
        if self.anim_clock:
            self.anim_clock.cancel()
        self.anim_clock = Clock.schedule_interval(self.next_frame, self.frame_duration)

    def next_frame(self, dt):
        """Следующий кадр"""
        if not self.is_animating or not self.frames:
            return
        self.current_frame += 1
        if self.current_frame >= len(self.frames):
            self.loops_done += 1
            self.current_frame = 0
            if self.loops_done >= self.loop_count:
                self.stop_animation()
                return
        self.texture = self.frames[self.current_frame]
        self._update_rotation()

    def stop_animation(self):
        """Останавливает анимацию"""
        self.is_animating = False
        if self.anim_clock:
            self.anim_clock.cancel()
            self.anim_clock = None

    def set_result(self, result):
        """Устанавливает финальный кадр (0 - орел, 1 - решка)"""
        if not self.frames:
            return
        if result == 0:
            self.texture = self.frames[0]
        else:
            self.texture = self.frames[-1]
        self._update_rotation()


class CoinScreen(BaseGameScreen):
    """Игровой экран с монетой из спрайт-листа"""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self.background_image = 'assets/backgrounds/coin_bg.png'
        self.spritesheet_path = 'assets/images/coin/spritesheet_1.png'

        self.coin = None
        self.touch_area = None
        self.info_label = None
        self.stats_label = None

        # Статистика
        self.total_flips = 0
        self.heads_count = 0
        self.tails_count = 0

    def on_enter(self):
        """При входе на экран"""
        super().on_enter()
        self.setup_game_ui()
        Window.bind(on_resize=self.on_window_resize)

    def on_leave(self):
        """При выходе с экрана"""
        super().on_leave()
        Window.unbind(on_resize=self.on_window_resize)

    def on_window_resize(self, instance, width, height):
        """Обновление позиций при изменении размера окна"""
        pass

    def check_file(self, path):
        """Проверяет существование файла"""
        if os.path.exists(path):
            print(f"✅ Файл найден: {path}")
            return True
        else:
            print(f"❌ Файл НЕ найден: {path}")
            return False

    def setup_game_ui(self):
        """Создание игрового интерфейса"""

        # Проверяем наличие спрайт-листа
        self.check_file(self.spritesheet_path)

        # СОЗДАЕМ МОНЕТУ ИЗ СПРАЙТ-ЛИСТА (повернутую на 90° вокруг центра)
        self.coin = SpritesheetCoin(
            spritesheet_path=self.spritesheet_path,
            frame_width=64,
            frame_height=64,
            cols=5,
            rows=4,
            total_frames=19,
            rotation_angle=-90,  # Поворот на 90 градусов вокруг центра
            size_hint=(None, None),
            size=(150, 150),
            pos_hint={'center_x': 0.2, 'center_y': 0.5},  # Монета слева
            allow_stretch=True
        )
        self.layout.add_widget(self.coin)

        # СОЗДАЕМ ОБЛАСТЬ ДЛЯ НАЖАТИЯ (поверх монеты) - ТЕПЕРЬ ТАМ ЖЕ, ГДЕ МОНЕТА
        self.touch_area = TouchArea(
            size_hint=(0.4, 0.4),  # Чуть больше монеты для удобства
            pos_hint={'center_x': 0.2, 'center_y': 0.5},  # ← ИСПРАВЛЕНО: та же позиция, что у монеты
        )
        self.layout.add_widget(self.touch_area)

        # Привязываем обработчик касания к запуску анимации
        self.touch_area.bind(on_touch_down=self.on_area_touch)

        # ОТЛАДОЧНАЯ ИНФОРМАЦИЯ
        debug_label = Label(
            text=f'[ОТЛАДКА] Монета повернута на 90° вокруг центра | Спрайтов: {len(self.coin.frames) if self.coin.frames else 0}',
            color=(1, 1, 0, 0.8),
            size_hint=(None, None),
            size=(600, 30),
            pos_hint={'center_x': 0.5, 'center_y': 0.02},
            font_size=14
        )
        self.layout.add_widget(debug_label)

    def on_area_touch(self, instance, touch):
        """Обработка касания области"""
        if instance.collide_point(*touch.pos):
            self.flip_coin()
            return True
        return False

    def flip_coin(self):
        """Подбрасывание монеты"""
        if self.coin.is_animating:
            print("⏳ Монета уже вращается...")
            return

        # Случайный результат
        result = random.randint(0, 1)

        # Обновляем статистику
        self.total_flips += 1
        if result == 0:
            self.heads_count += 1
            result_text = 'ОРЕЛ'
        else:
            self.tails_count += 1
            result_text = 'РЕШКА'

        # ОЧЕНЬ БЫСТРОЕ ВРАЩЕНИЕ: максимальное количество оборотов за 7 секунд
        total_frames = len(self.coin.frames)  # 19 кадров

        # Используем максимальный FPS (60) для максимальной скорости
        fps = 60

        # Рассчитываем максимальное количество оборотов за 7 секунд при 60 FPS
        # Всего кадров за 7 секунд = 7 * 60 = 420 кадров
        # Количество оборотов = 420 / 19 ≈ 22
        max_loops = (7 * fps) // total_frames

        # Берем от 80% до 100% от максимального количества оборотов
        loops = int(max_loops * random.uniform(0.8, 1.0))

        print(f"⏱️ Длительность: 7 сек, Оборотов: {loops}, FPS: {fps} (МАКСИМАЛЬНО БЫСТРО)")

        self.coin.start_animation(loop_count=loops, fps=fps)

        # По окончании анимации показываем результат
        def show_result(dt):
            self.coin.set_result(result)

        # Длительность анимации 7 секунд
        Clock.schedule_once(show_result, 7.0)

    def go_to_menu(self):
        """Возврат в меню"""
        if self.coin:
            self.coin.stop_animation()
        super().go_to_menu()