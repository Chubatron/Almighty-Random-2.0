# random_number_screen.py

from kivy.uix.image import Image
from kivy.animation import Animation
from kivy.clock import Clock
from kivy.uix.behaviors import ButtonBehavior
from kivy.uix.image import Image as KivyImage
from kivy.uix.label import Label
from kivy.uix.textinput import TextInput
from kivy.uix.button import Button
from kivy.graphics import PushMatrix, PopMatrix, Rotate, Translate, Color, Rectangle, Line
from kivy.core.window import Window
from kivy.uix.modalview import ModalView
from kivy.uix.widget import Widget
from kivy.core.image import Image as CoreImage
from kivy.uix.floatlayout import FloatLayout

from screens.base_game_screen import BaseGameScreen

# Режим отладки
DEBUG_MODE = True


class AdaptiveBackground(Image):
    """Адаптивный фон - растягивается на весь экран"""

    def __init__(self, source='', **kwargs):
        super().__init__(**kwargs)
        self.source = source
        self.allow_stretch = True
        self.keep_ratio = False
        self.size_hint = (1, 1)
        self.pos_hint = {'x': 0, 'y': 0}


class ImageButton(ButtonBehavior, KivyImage):
    """Кнопка с изображением"""
    pass


class SpriteSheetButton(ButtonBehavior, Widget):
    """Кнопка с изображением из спрайтлиста"""

    def __init__(self, button_index=0, sprite_sheet_path='assets/sprites/numbers_spritesheet.png', **kwargs):
        super().__init__(**kwargs)
        self.button_index = button_index
        self.sprite_sheet_path = sprite_sheet_path
        self.sprite_image = None
        self.sprite_texture_region = None
        self.current_frame = 0
        self.total_frames = 120  # 10 строк × 12 колонок
        self.rows = 10
        self.cols = 12
        self.is_animating = False

        # Размеры одного кадра в спрайтлисте
        self.frame_width = 140
        self.frame_height = 54

        Clock.schedule_once(lambda dt: self._load_sprite(0), 0.1)

    def _load_sprite(self, frame_index):
        """Загружает конкретный кадр из спрайтлиста"""
        try:
            sprite_sheet = CoreImage(self.sprite_sheet_path)
            texture_height = sprite_sheet.texture.height

            # Вычисляем позицию кадра в спрайтлисте
            row = frame_index // self.cols
            col = frame_index % self.cols

            # Вычисляем смещение (Kivy: Y идет от нижнего левого угла)
            y_offset = texture_height - ((row + 1) * self.frame_height)
            x_offset = col * self.frame_width

            if DEBUG_MODE and frame_index == 0:
                print(f"\n🖼 ЗАГРУЗКА СПРАЙТА для кнопки #{self.button_index + 1}")
                print(f"   Всего кадров: {self.total_frames}")
                print(f"   Строк: {self.rows}, Колонок: {self.cols}")
                print(f"   Размер кадра: {self.frame_width}x{self.frame_height}")

            if x_offset + self.frame_width <= sprite_sheet.texture.width and \
                    y_offset >= 0 and y_offset + self.frame_height <= texture_height:

                self.sprite_texture_region = sprite_sheet.texture.get_region(
                    x=x_offset,
                    y=y_offset,
                    width=self.frame_width,
                    height=self.frame_height
                )

                # Если изображение еще не создано, создаем новое
                if self.sprite_image is None:
                    self.sprite_image = KivyImage(
                        texture=self.sprite_texture_region,
                        allow_stretch=True,
                        keep_ratio=False,
                        size=(self.width, self.height),
                        pos=(self.x, self.y)
                    )
                    self.add_widget(self.sprite_image)
                    self.bind(pos=self._update_image_position, size=self._update_image_size)
                else:
                    # Обновляем текстуру существующего изображения
                    self.sprite_image.texture = self.sprite_texture_region

        except Exception as e:
            if DEBUG_MODE:
                print(f"❌ Ошибка загрузки спрайтлиста: {e}")

    def set_frame(self, frame_index):
        """Устанавливает конкретный кадр"""
        if 0 <= frame_index < self.total_frames:
            self.current_frame = frame_index
            self._load_sprite(frame_index)

    def get_row_start_frame(self, row):
        """Возвращает первый кадр указанной строки"""
        return row * self.cols

    def animate_spin(self, target_row, duration=0.8, on_complete=None):
        """
        Анимация прокрутки кадров, останавливается на первом кадре целевой строки
        target_row: целевая строка (0-9)
        """
        if self.is_animating:
            return

        self.is_animating = True

        # Вычисляем целевой кадр (первый кадр целевой строки)
        target_frame = target_row * self.cols
        start_frame = self.current_frame

        # Рассчитываем, сколько кадров нужно прокрутить
        if start_frame <= target_frame:
            frames_to_pass = target_frame - start_frame
        else:
            frames_to_pass = (self.total_frames - start_frame) + target_frame

        # Всегда прокручиваем как минимум один полный круг
        frames_to_pass += self.total_frames

        step_duration = duration / frames_to_pass

        def next_frame(dt):
            if not self.is_animating:
                return

            # Переходим к следующему кадру
            self.current_frame = (self.current_frame + 1) % self.total_frames
            self._load_sprite(self.current_frame)

            # Проверяем, достигли ли целевого кадра
            if self.current_frame == target_frame:
                self.is_animating = False
                if on_complete:
                    on_complete()
            else:
                # Продолжаем анимацию
                Clock.schedule_once(next_frame, step_duration)

        # Запускаем анимацию
        Clock.schedule_once(next_frame, step_duration)

    def _update_image_position(self, instance, value):
        """Обновляет позицию изображения"""
        if self.sprite_image:
            self.sprite_image.pos = (self.x, self.y)

    def _update_image_size(self, instance, value):
        """Обновляет размер изображения"""
        if self.sprite_image:
            self.sprite_image.size = (self.width, self.height)

    def on_press(self):
        if self.sprite_image:
            Animation(opacity=0.7, duration=0.05).start(self.sprite_image)
        super().on_press()

    def on_release(self):
        if self.sprite_image:
            Animation(opacity=1.0, duration=0.05).start(self.sprite_image)
        super().on_release()


class NeonButton(ButtonBehavior, KivyImage):
    """Неоновая кнопка с вертикальным текстом поверх"""

    def __init__(self, text='', text_color=(1, 1, 1, 1), text_size=30, debug_color=None, value=None, **kwargs):
        super().__init__(**kwargs)
        self.base_text = text
        self.value = value
        self.text_color = text_color
        self.text_size = text_size
        self.text_label = None
        self.debug_color = debug_color
        self.allow_stretch = True
        self.keep_ratio = False

        Clock.schedule_once(self._create_label, 0.2)

    def update_value(self, new_value):
        """Обновляет значение и текст на кнопке"""
        self.value = new_value
        if self.text_label:
            if self.value is not None and self.base_text in ["MIN", "MAX"]:
                self.text_label.text = f"{self.base_text}\n{self.value}"
                print(f"🔄 Обновлена кнопка {self.base_text}: {self.value}")
            else:
                self.text_label.text = self.base_text
            Clock.schedule_once(lambda dt: self._update_text_pos(), 0.05)

    def _create_label(self, dt):
        if self.text_label:
            return

        if not self.parent or self.width == 0 or self.height == 0:
            Clock.schedule_once(self._create_label, 0.1)
            return

        display_text = self.base_text
        if self.value is not None and self.base_text in ["MIN", "MAX"]:
            display_text = f"{self.base_text}\n{self.value}"

        self.text_label = Label(
            text=display_text,
            color=self.text_color,
            font_size=self.text_size,
            size_hint=(None, None),
            halign='center',
            valign='middle',
            bold=True,
            opacity=0
        )

        center_x = self.x + self.width / 2
        center_y = self.y + self.height / 2

        self.text_label.text_size = (None, None)
        self.text_label.size = self.text_label.texture_size

        with self.text_label.canvas.before:
            PushMatrix()
            Translate(center_x, center_y, 0)
            Rotate(angle=270, origin=(0, 0))
            Translate(-center_x, -center_y, 0)

        with self.text_label.canvas.after:
            PopMatrix()

        self.text_label.pos = (
            center_x - self.text_label.width / 2,
            center_y - self.text_label.height / 2
        )

        self.parent.add_widget(self.text_label)
        self.text_label.opacity = 1

        self.bind(pos=self._update_text_pos, size=self._update_text_pos)

    def _update_text_pos(self, *args):
        if not self.text_label or not self.text_label.parent:
            return

        center_x = self.x + self.width / 2
        center_y = self.y + self.height / 2

        self.text_label.canvas.before.clear()
        self.text_label.canvas.after.clear()

        self.text_label.text_size = (None, None)
        self.text_label.size = self.text_label.texture_size

        with self.text_label.canvas.before:
            PushMatrix()
            Translate(center_x, center_y, 0)
            Rotate(angle=270, origin=(0, 0))
            Translate(-center_x, -center_y, 0)

        with self.text_label.canvas.after:
            PopMatrix()

        self.text_label.pos = (
            center_x - self.text_label.width / 2,
            center_y - self.text_label.height / 2
        )

    def on_size(self, *args):
        if self.text_label:
            new_size = min(self.height / 1.5, self.width * 0.4)
            self.text_label.font_size = max(16, min(new_size, 50))
            self._update_text_pos()

    def on_pos(self, *args):
        if self.text_label:
            self._update_text_pos()


class NumberInputModal(ModalView):
    """Модальное окно для ввода числа с ВЕРТИКАЛЬНЫМ текстом"""

    def __init__(self, title="Введите число", current_value=0, on_submit=None, **kwargs):
        super().__init__(**kwargs)
        self.size_hint = (1.0, 1.0)
        self.background_color = (0, 0, 0, 0)
        self.auto_dismiss = True

        self.title = title
        self.current_value = current_value
        self.on_submit = on_submit

        # Основной контейнер
        self.layout = FloatLayout(size_hint=(1, 1))
        self.add_widget(self.layout)

        # Затемненная подложка
        with self.layout.canvas.before:
            Color(0, 0, 0, 0.7)
            self.overlay_rect = Rectangle(size=self.layout.size, pos=self.layout.pos)
            self.layout.bind(size=self._update_overlay, pos=self._update_overlay)

        # Анимация появления
        self.layout.opacity = 0
        self.layout.scale = 0.8

        # Создаем UI
        Clock.schedule_once(self.create_ui, 0.1)
        Clock.schedule_once(lambda dt: self.animate_show(), 0.15)

    def _update_overlay(self, instance, value):
        self.overlay_rect.size = self.layout.size
        self.overlay_rect.pos = self.layout.pos

    def animate_show(self):
        anim = Animation(opacity=1, scale=1, duration=0.3, t='out_back')
        anim.start(self.layout)

    def create_ui(self, dt=None):
        """Создает элементы интерфейса с ВЕРТИКАЛЬНЫМ текстом"""

        # Размеры экрана
        screen_width = Window.width
        screen_height = Window.height

        # Центральная панель
        panel_width = screen_width * 0.6
        panel_height = screen_height * 0.55
        panel_x = (screen_width - panel_width) / 2
        panel_y = (screen_height - panel_height) / 2

        # Панель с фоном
        self.panel = Widget(
            size_hint=(None, None),
            size=(panel_width, panel_height),
            pos=(panel_x, panel_y)
        )

        # Рисуем фон панели
        with self.panel.canvas.before:
            Color(0.05, 0.05, 0.05, 0.95)
            self.panel_bg = Rectangle(size=self.panel.size, pos=self.panel.pos)
            Color(0.2, 0.8, 1, 0.8)
            self.panel_border = Line(
                rectangle=(self.panel.pos[0], self.panel.pos[1],
                           self.panel.size[0], self.panel.size[1]),
                width=3
            )

        self.panel.bind(size=self._update_panel_bg, pos=self._update_panel_bg)

        # === ВЕРТИКАЛЬНОЕ РАСПОЛОЖЕНИЕ С ВЕРТИКАЛЬНЫМ ТЕКСТОМ ===

        # Расстояние между элементами
        spacing = panel_height * 0.05

        # Высота каждого элемента
        title_height = panel_height * 0.15
        input_height = panel_height * 0.2
        button_height = panel_height * 0.15

        # Общая высота всех элементов
        total_height = title_height + input_height + button_height + (spacing * 2)

        # Начальная Y координата (от верхней границы панели)
        start_y = panel_y + panel_height - (panel_height - total_height) / 2 - title_height

        # 1. ЗАГОЛОВОК (С ВЕРТИКАЛЬНЫМ ТЕКСТОМ)
        self.title_label = Label(
            text=self.title,
            font_size=min(panel_height * 0.08, 28),
            color=(0.2, 0.8, 1, 1),
            size_hint=(None, None),
            size=(title_height, panel_width * 0.8),
            pos=(
                panel_x + (panel_width - title_height) / 2,
                start_y
            ),
            bold=True,
            halign='center',
            valign='middle'
        )
        self.title_label.text_size = self.title_label.size

        # Поворачиваем заголовок на 90 градусов
        center_x = self.title_label.x + self.title_label.width / 2
        center_y = self.title_label.y + self.title_label.height / 2
        with self.title_label.canvas.before:
            PushMatrix()
            Translate(center_x, center_y, 0)
            Rotate(angle=90, origin=(0, 0))
            Translate(-center_x, -center_y, 0)
        with self.title_label.canvas.after:
            PopMatrix()

        self.panel.add_widget(self.title_label)

        # 2. ПОЛЕ ВВОДА (ПОД ЗАГОЛОВКОМ) - обычное горизонтальное
        input_y = start_y - spacing - input_height

        self.text_input = TextInput(
            text=str(self.current_value),
            font_size=min(panel_height * 0.08, 36),
            size_hint=(None, None),
            size=(panel_width * 0.7, input_height),
            pos=(
                panel_x + (panel_width - panel_width * 0.7) / 2,
                input_y
            ),
            multiline=False,
            input_filter='int',
            halign='center',
            background_color=(0.15, 0.15, 0.15, 1),
            foreground_color=(1, 1, 1, 1),
            cursor_color=(0.2, 0.8, 1, 1),
            background_normal=''
        )
        self.panel.add_widget(self.text_input)

        # 3. КНОПКА ПОДТВЕРЖДЕНИЯ (С ВЕРТИКАЛЬНЫМ ТЕКСТОМ)
        button_y = input_y - spacing - button_height

        self.submit_button = Button(
            text="ПОДТВЕРДИТЬ",
            font_size=min(panel_height * 0.06, 22),
            size_hint=(None, None),
            size=(button_height, panel_width * 0.5),
            pos=(
                panel_x + (panel_width - button_height) / 2,
                button_y
            ),
            background_normal='',
            background_color=(0.2, 0.6, 0.2, 1),
            color=(1, 1, 1, 1),
            bold=True
        )

        # Поворачиваем текст кнопки на 90 градусов
        btn_center_x = self.submit_button.x + self.submit_button.width / 2
        btn_center_y = self.submit_button.y + self.submit_button.height / 2
        with self.submit_button.canvas.before:
            PushMatrix()
            Translate(btn_center_x, btn_center_y, 0)
            Rotate(angle=90, origin=(0, 0))
            Translate(-btn_center_x, -btn_center_y, 0)
        with self.submit_button.canvas.after:
            PopMatrix()

        self.submit_button.bind(on_press=self.on_button_press)
        self.submit_button.bind(on_release=self.on_button_release)
        self.panel.add_widget(self.submit_button)

        self.layout.add_widget(self.panel)

        # Фокусируемся на поле ввода
        Clock.schedule_once(lambda dt: self._focus_input(), 0.2)

        # Отладочная информация
        if DEBUG_MODE:
            print(f"\n📱 СОЗДАНО МОДАЛЬНОЕ ОКНО С ВЕРТИКАЛЬНЫМ ТЕКСТОМ:")
            print(f"   Размер экрана: {screen_width}x{screen_height}")
            print(f"   Размер панели: {panel_width}x{panel_height}")
            print(f"   Заголовок Y: {start_y:.1f}")
            print(f"   Поле ввода Y: {input_y:.1f}")
            print(f"   Кнопка Y: {button_y:.1f}")

    def _update_panel_bg(self, instance, value):
        """Обновляет фон панели"""
        if hasattr(self, 'panel_bg'):
            self.panel_bg.size = self.panel.size
            self.panel_bg.pos = self.panel.pos

        if hasattr(self, 'panel_border'):
            self.panel_border.rectangle = (
                self.panel.pos[0], self.panel.pos[1],
                self.panel.size[0], self.panel.size[1]
            )

        # Обновляем позиции при изменении размера
        self._update_vertical_positions()

    def _update_vertical_positions(self):
        """Обновляет вертикальные позиции всех элементов с сохранением поворота"""
        if not hasattr(self, 'panel'):
            return

        panel_x = self.panel.pos[0]
        panel_y = self.panel.pos[1]
        panel_width = self.panel.size[0]
        panel_height = self.panel.size[1]

        # Расстояние между элементами
        spacing = panel_height * 0.05

        # Высота каждого элемента
        title_height = panel_height * 0.15
        input_height = panel_height * 0.2
        button_height = panel_height * 0.15

        # Общая высота всех элементов
        total_height = title_height + input_height + button_height + (spacing * 2)

        # Начальная Y координата
        start_y = panel_y + panel_height - (panel_height - total_height) / 2 - title_height

        # Обновляем заголовок (с поворотом)
        if hasattr(self, 'title_label'):
            # Очищаем старые трансформации
            self.title_label.canvas.before.clear()
            self.title_label.canvas.after.clear()

            # Обновляем размер и позицию
            self.title_label.size = (title_height, panel_width * 0.8)
            self.title_label.pos = (
                panel_x + (panel_width - title_height) / 2,
                start_y
            )
            self.title_label.text_size = self.title_label.size

            # Применяем поворот заново
            center_x = self.title_label.x + self.title_label.width / 2
            center_y = self.title_label.y + self.title_label.height / 2
            with self.title_label.canvas.before:
                PushMatrix()
                Translate(center_x, center_y, 0)
                Rotate(angle=90, origin=(0, 0))
                Translate(-center_x, -center_y, 0)
            with self.title_label.canvas.after:
                PopMatrix()

        # Обновляем поле ввода (без поворота)
        if hasattr(self, 'text_input'):
            input_y = start_y - spacing - input_height
            self.text_input.size = (panel_width * 0.7, input_height)
            self.text_input.pos = (
                panel_x + (panel_width - panel_width * 0.7) / 2,
                input_y
            )

        # Обновляем кнопку (с поворотом)
        if hasattr(self, 'submit_button'):
            button_y = input_y - spacing - button_height

            # Очищаем старые трансформации
            self.submit_button.canvas.before.clear()
            self.submit_button.canvas.after.clear()

            # Обновляем размер и позицию
            self.submit_button.size = (button_height, panel_width * 0.5)
            self.submit_button.pos = (
                panel_x + (panel_width - button_height) / 2,
                button_y
            )

            # Применяем поворот заново
            btn_center_x = self.submit_button.x + self.submit_button.width / 2
            btn_center_y = self.submit_button.y + self.submit_button.height / 2
            with self.submit_button.canvas.before:
                PushMatrix()
                Translate(btn_center_x, btn_center_y, 0)
                Rotate(angle=90, origin=(0, 0))
                Translate(-btn_center_x, -btn_center_y, 0)
            with self.submit_button.canvas.after:
                PopMatrix()

    def on_button_press(self, instance):
        Animation(background_color=(0.1, 0.8, 0.1, 1), duration=0.05).start(instance)
        self.play_click_sound()

    def on_button_release(self, instance):
        Animation(background_color=(0.2, 0.6, 0.2, 1), duration=0.05).start(instance)
        self.submit_value()

    def play_click_sound(self):
        try:
            from kivy.core.audio import SoundLoader
            sound = SoundLoader.load('assets/sounds/click.wav')
            if sound:
                sound.play()
        except Exception:
            pass

    def _focus_input(self):
        self.text_input.focus = True

    def submit_value(self):
        try:
            text_value = self.text_input.text.strip()
            if text_value == '' or text_value == '-':
                value = 0
            else:
                value = int(text_value)

            # Ограничиваем до 9 символов
            value_str = str(abs(value))
            if len(value_str) > 9:
                if value >= 0:
                    value = 999999999
                else:
                    value = -999999999

            print(f"📤 Отправка значения: {value}")
            if self.on_submit:
                self.on_submit(value)

            self.dismiss_with_animation()

        except ValueError:
            print(f"❌ Ошибка преобразования: {self.text_input.text}")
            self.show_error_animation()

    def dismiss_with_animation(self):
        anim = Animation(opacity=0, duration=0.2)
        anim.bind(on_complete=lambda *args: self.dismiss())
        anim.start(self.layout)

    def show_error_animation(self):
        original_color = self.text_input.background_color
        anim = Animation(background_color=(1, 0.2, 0.2, 1), duration=0.1)
        anim += Animation(background_color=original_color, duration=0.1)
        anim.start(self.text_input)

        original_x = self.text_input.x
        shake_anim = (
                Animation(x=original_x - 10, duration=0.05) +
                Animation(x=original_x + 10, duration=0.05) +
                Animation(x=original_x - 5, duration=0.05) +
                Animation(x=original_x + 5, duration=0.05) +
                Animation(x=original_x, duration=0.05)
        )
        shake_anim.start(self.text_input)


class RandomNumberScreen(BaseGameScreen):
    """Экран для генерации случайного числа"""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.adaptive_background = None
        self.neon_buttons = []
        self.sprite_buttons = []
        self.buttons_created = False

        self.min_value = 0
        self.max_value = 1000
        self.is_positive = True

        self.min_button = None
        self.max_button = None
        self.current_action = None

    def on_enter(self):
        """При входе на экран"""
        if not self.adaptive_background:
            self.adaptive_background = AdaptiveBackground(
                source='assets/backgrounds/random_number_bg.png'
            )
            self.layout.add_widget(self.adaptive_background, index=0)

        if not self.buttons_created:
            self.create_back_button()
            self.create_neon_buttons()
            self.create_sprite_buttons()
            self.buttons_created = True
        else:
            self.update_min_max_buttons()

    def on_leave(self):
        """При выходе с экрана"""
        for button in self.neon_buttons:
            if button.text_label and button.text_label in self.layout.children:
                button.text_label.opacity = 0
                self.layout.remove_widget(button.text_label)
                button.text_label = None

        super().on_leave()

    def create_back_button(self):
        """Создает кнопку возврата в меню"""
        back_btn = ImageButton(
            source='assets/images/buttons/Orange_back_to_menu_button_90.png',
            size_hint=(0.12, 0.12),
            pos_hint={'x': 0.03, 'y': 0.85},
            allow_stretch=True
        )

        def on_press(instance):
            Animation(opacity=0.7, duration=0.1).start(instance)

        def on_release(instance):
            Animation(opacity=1.0, duration=0.1).start(instance)
            self.play_back_sound()
            Clock.schedule_once(lambda dt: self.go_to_menu(), 0.1)

        back_btn.bind(on_press=on_press)
        back_btn.bind(on_release=on_release)

        self.back_button = back_btn
        self.layout.add_widget(back_btn)

    def create_sprite_buttons(self):
        """Создает 10 кнопок с изображениями из спрайтлиста"""
        sprite_sheet_path = 'assets/sprites/numbers_spritesheet.png'

        button_positions = [
            {'x': 0.52, 'y': 0.915},  # Кнопка 1 - ЗНАК (+/-)
            {'x': 0.52, 'y': 0.815},  # Кнопка 2 - миллиарды
            {'x': 0.52, 'y': 0.72},  # Кнопка 3 - сотни миллионов
            {'x': 0.52, 'y': 0.62},  # Кнопка 4 - десятки миллионов
            {'x': 0.52, 'y': 0.52},  # Кнопка 5 - единицы миллионов
            {'x': 0.52, 'y': 0.42},  # Кнопка 6 - сотни тысяч
            {'x': 0.52, 'y': 0.32},  # Кнопка 7 - десятки тысяч
            {'x': 0.52, 'y': 0.225},  # Кнопка 8 - единицы тысяч
            {'x': 0.52, 'y': 0.125},  # Кнопка 9 - сотни
            {'x': 0.52, 'y': 0.025},  # Кнопка 10 - единицы
        ]

        button_size_hint = (0.28, 0.062)

        for i, pos in enumerate(button_positions):
            sprite_button = SpriteSheetButton(
                button_index=i,
                sprite_sheet_path=sprite_sheet_path,
                size_hint=button_size_hint,
                pos_hint={'x': pos['x'], 'y': pos['y']}
            )

            sprite_button.button_id = i
            sprite_button.button_number = i + 1

            sprite_button.bind(on_press=self.on_sprite_button_press)
            sprite_button.bind(on_release=self.on_sprite_button_release)

            self.layout.add_widget(sprite_button)
            self.sprite_buttons.append(sprite_button)

    def on_sprite_button_press(self, instance):
        print(f"🎮 Нажата кнопка #{instance.button_number}")
        self.play_click_sound()

    def on_sprite_button_release(self, instance):
        pass

    def spin_all_buttons(self, target_rows, sign_row=None):
        """Запускает анимацию прокрутки для всех кнопок"""
        print(f"\n🎬 ЗАПУСК АНИМАЦИИ ДЛЯ {len(self.sprite_buttons)} КНОПОК")

        completed = [0]

        def on_animation_complete():
            completed[0] += 1
            if completed[0] >= len(self.sprite_buttons):
                print(f"🎬 ВСЕ АНИМАЦИИ ЗАВЕРШЕНЫ!")

        # Анимация для кнопки знака
        if sign_row is not None and len(self.sprite_buttons) > 0:
            sign_button = self.sprite_buttons[0]
            Clock.schedule_once(
                lambda dt: sign_button.animate_spin(sign_row, duration=0.8, on_complete=on_animation_complete), 0)
            print(f"   Кнопка 1 (ЗНАК): цель - строка {sign_row}")

        # Анимация для цифровых кнопок
        for i, button in enumerate(self.sprite_buttons[1:], start=1):
            target_row = target_rows[i - 1]
            delay = i * 0.03

            def start_animation(btn, row, delay_time):
                Clock.schedule_once(lambda dt: btn.animate_spin(row, duration=0.8, on_complete=on_animation_complete),
                                    delay_time)

            start_animation(button, target_row, delay)
            print(f"   Кнопка {i + 1}: цель - строка {target_row} (кадр {target_row * 12})")

    def get_digit_row(self, digit):
        """Возвращает номер строки для цифры"""
        return digit

    def get_sign_row(self, is_positive):
        """Возвращает строку для знака: 0 = плюс, 1 = минус"""
        return 0 if is_positive else 1

    def create_neon_buttons(self):
        """Создает 4 неоновые кнопки"""
        button_configs = [
            {"text": "LIST", "pos_hint": {'x': 0.0, 'y': 0.475}, "id": "list", "value": None},
            {"text": "MIN", "pos_hint": {'x': 0.2, 'y': 0.475}, "id": "min", "value": self.min_value},
            {"text": "GENERATE", "pos_hint": {'x': 0.0, 'y': 0.075}, "id": "generate", "value": None},
            {"text": "MAX", "pos_hint": {'x': 0.2, 'y': 0.075}, "id": "max", "value": self.max_value}
        ]

        for config in button_configs:
            button = NeonButton(
                source='assets/images/buttons/neon_button.png',
                text=config["text"],
                text_color=(0.2, 0.8, 1, 1),
                size_hint=(0.25, 0.35),
                pos_hint=config["pos_hint"],
                allow_stretch=True,
                value=config["value"]
            )
            button.action_id = config["id"]
            button.bind(on_press=self.on_button_press_animation)
            button.bind(on_release=lambda instance, aid=config["id"], txt=config["text"]:
            self.on_button_release(instance, aid, txt))
            self.layout.add_widget(button)
            self.neon_buttons.append(button)

            if config["id"] == "min":
                self.min_button = button
                print(f"✅ Создана кнопка MIN с начальным значением {self.min_value}")
            elif config["id"] == "max":
                self.max_button = button
                print(f"✅ Создана кнопка MAX с начальным значением {self.max_value}")

    def update_min_max_buttons(self):
        """Обновляет текст на кнопках MIN и MAX"""
        if self.min_button:
            self.min_button.update_value(self.min_value)
            print(f"🔄 Вызван update_min_max_buttons: MIN = {self.min_value}")
        if self.max_button:
            self.max_button.update_value(self.max_value)
            print(f"🔄 Вызван update_min_max_buttons: MAX = {self.max_value}")

    def show_number_input_popup(self, action_type, current_value):
        """Показывает модальное окно для ввода числа"""
        self.current_action = action_type
        title = "Введите MIN значение" if action_type == "min" else "Введите MAX значение"

        popup = NumberInputModal(
            title=title,
            current_value=current_value,
            on_submit=self.on_value_submitted
        )
        popup.open()

    def on_value_submitted(self, value):
        """Обработка введенного значения"""
        print(f"📥 Получено значение {value} для {self.current_action}")

        if self.current_action == "min":
            if value > self.max_value:
                self.show_warning(f"MIN не может быть больше MAX!\nТекущий MAX: {self.max_value}")
                return
            self.min_value = value
            self.update_min_max_buttons()
            print(f"✅ Установлено MIN = {self.min_value}")

            # Визуальный фидбек
            if self.min_button:
                anim = Animation(opacity=0.7, duration=0.1) + Animation(opacity=1, duration=0.1)
                anim.start(self.min_button)

        elif self.current_action == "max":
            if value < self.min_value:
                self.show_warning(f"MAX не может быть меньше MIN!\nТекущий MIN: {self.min_value}")
                return
            self.max_value = value
            self.update_min_max_buttons()
            print(f"✅ Установлено MAX = {self.max_value}")

            # Визуальный фидбек
            if self.max_button:
                anim = Animation(opacity=0.7, duration=0.1) + Animation(opacity=1, duration=0.1)
                anim.start(self.max_button)

        self.current_action = None

    def generate_random_number(self):
        import random

        if self.min_value > self.max_value:
            self.show_warning(f"Ошибка: MIN ({self.min_value}) > MAX ({self.max_value})")
            return None

        if self.min_value == self.max_value:
            result = self.min_value
        else:
            result = random.randint(self.min_value, self.max_value)

        return result

    def show_warning(self, message):
        from kivy.uix.popup import Popup
        from kivy.uix.label import Label
        from kivy.uix.button import Button
        from kivy.uix.boxlayout import BoxLayout

        layout = BoxLayout(orientation='vertical', padding=10, spacing=10)
        layout.add_widget(Label(text=message, font_size=20, halign='center', valign='middle'))

        close_btn = Button(text="OK", size_hint=(1, 0.3))
        layout.add_widget(close_btn)

        popup = Popup(title="Предупреждение", content=layout, size_hint=(0.7, 0.4))
        close_btn.bind(on_press=popup.dismiss)
        popup.open()

    def on_button_press_animation(self, instance):
        Animation(opacity=0.8, duration=0.05).start(instance)

    def on_button_release(self, instance, action_id, button_text):
        Animation(opacity=1.0, duration=0.05).start(instance)
        self.play_click_sound()

        if action_id == "min":
            print(f"🎲 Нажата кнопка MIN, текущее значение: {self.min_value}")
            self.show_number_input_popup("min", self.min_value)
        elif action_id == "max":
            print(f"🎲 Нажата кнопка MAX, текущее значение: {self.max_value}")
            self.show_number_input_popup("max", self.max_value)
        elif action_id == "generate":
            result = self.generate_random_number()
            if result is not None:
                is_positive = result >= 0
                abs_result = abs(result)
                result_str = str(abs_result).zfill(9)

                print(f"\n{'=' * 60}")
                print(f"🎲 Сгенерировано число: {result}")
                print(f"   Знак: {'+' if is_positive else '-'}")
                print(f"   Формат (9 цифр): {result_str}")

                # Определяем целевые строки для кнопок
                target_rows = []
                for digit_char in result_str:
                    digit = int(digit_char)
                    target_rows.append(self.get_digit_row(digit))

                sign_row = self.get_sign_row(is_positive)

                print(f"\n📊 РАСПРЕДЕЛЕНИЕ ПО КНОПКАМ (сверху вниз):")
                print(f"   Кнопка 1 (ЗНАК): {'+' if is_positive else '-'} -> строка {sign_row}")
                for i, (char, row) in enumerate(zip(result_str, target_rows)):
                    print(f"   Кнопка {i + 2}: цифра {char} -> строка {row}")
                print(f"{'=' * 60}\n")

                self.spin_all_buttons(target_rows, sign_row)

        elif action_id == "list":
            self.show_warning("Функция LIST будет доступна в следующем обновлении!")

    def play_click_sound(self):
        try:
            from kivy.core.audio import SoundLoader
            sound = SoundLoader.load('assets/sounds/click.wav')
            if sound:
                sound.play()
        except Exception:
            pass

    def play_back_sound(self):
        try:
            from kivy.core.audio import SoundLoader
            sound = SoundLoader.load('assets/sounds/back.wav')
            if sound:
                sound.play()
        except Exception:
            pass

    def go_to_menu(self):
        from main import switch_screen
        switch_screen('menu')