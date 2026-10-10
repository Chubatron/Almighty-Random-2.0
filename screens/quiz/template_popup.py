from kivy.uix.popup import Popup
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.core.window import Window
from kivy.graphics import Rectangle, Color
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.behaviors import ButtonBehavior
from kivy.uix.widget import Widget
from kivy.uix.scrollview import ScrollView
from kivy.uix.gridlayout import GridLayout
from kivy.uix.textinput import TextInput
from kivy.clock import Clock
from kivy.animation import Animation
from kivy.utils import platform

from screens.quiz.template_manager import TemplateManager


class SuperVisibleButton(ButtonBehavior, Widget):
    """Супер-видимая кнопка - использует обычный Button для гарантии"""

    def __init__(self, text='', font_size=20, color=(0.2, 0.8, 0.2, 1), **kwargs):
        super().__init__(**kwargs)
        self.text = text
        self.font_size = font_size
        self.callback = None

        self.btn = Button(
            text=text,
            font_size=font_size,
            bold=True,
            color=(1, 1, 1, 1),
            background_normal='',
            background_color=color,
            size_hint=(1, 1),
            pos=self.pos,
            size=self.size
        )
        self.btn.bind(on_press=self.on_press)
        self.add_widget(self.btn)

        self.bind(pos=self.update_graphics, size=self.update_graphics)

    def update_graphics(self, *args):
        if hasattr(self, 'btn'):
            self.btn.pos = self.pos
            self.btn.size = self.size

    def on_press(self, instance):
        print(f"🔴 [SuperVisibleButton] НАЖАТА КНОПКА: '{self.text}'")
        if self.callback:
            self.callback(self)


class BaseFairyPopup(Popup):
    """Base popup class with fairy background image - БЕЗ ЗАТЕМНЕНИЯ"""

    BUTTON_WIDTH_COEFF = 0.7
    BUTTON_HEIGHT_COEFF = 0.12
    BUTTON_FONT_SIZE_COEFF = 0.05
    BUTTON_POSITIONS_X = [0.5, 0.5, 0.5, 0.5, 0.5]
    BUTTON_POSITIONS_Y = [0.80, 0.65, 0.50, 0.35, 0.20]

    def __init__(self, screen=None, bg_image='assets/images/fairy_popup.png', **kwargs):
        self.screen = screen
        self.bg_image = bg_image

        # Переменные для управления сдвигом попапа
        self._keyboard_height = 0
        self._is_keyboard_shown = False
        self._original_pos = (0, 0)
        self._shift_animation = None
        self._check_keyboard_clock = None
        self._active_textinput = None
        self._keyboard_check_count = 0

        super().__init__(**kwargs)
        self.auto_dismiss = False

        # Устанавливаем размер на весь экран
        self.size_hint = (1, 1)
        self.size = Window.size

        # Убираем ВСЕ отступы у попапа
        self.background_color = (0, 0, 0, 0)
        self.background = ''
        self.background_normal = ''
        self.background_down = ''

        self.padding = [0, 0, 0, 0]
        self.spacing = 0
        self.separator_height = 0
        self.separator_color = [0, 0, 0, 0]

        self.title = ''
        self.title_size = 0
        self.title_align = 'center'
        self.title_color = [0, 0, 0, 0]

        print("🔄 [KEYBOARD] BaseFairyPopup создан")

    def get_screen_width(self):
        if self.screen and hasattr(self.screen, 'get_screen_width'):
            return self.screen.get_screen_width()
        return Window.width

    def get_screen_height(self):
        if self.screen and hasattr(self.screen, 'get_screen_height'):
            return self.screen.get_screen_height()
        return Window.height

    def _on_text_input_focus(self, instance, value):
        """Обработчик фокуса TextInput"""
        print(f"⌨️ [KEYBOARD] TextInput фокус: {value}, поле: {instance.__class__.__name__}")

        if value:  # Получил фокус
            self._active_textinput = instance
            self._keyboard_check_count = 0
            print(f"⌨️ [KEYBOARD] Фокус получен, запускаем проверку клавиатуры")
            # Запускаем проверку высоты окна
            self._start_keyboard_check()
        else:  # Потерял фокус
            print(f"⌨️ [KEYBOARD] Фокус потерян, останавливаем проверку")
            self._active_textinput = None
            # Останавливаем проверку и возвращаем попап
            self._stop_keyboard_check()
            self._restore_popup_position()

    def _start_keyboard_check(self):
        """Запускает периодическую проверку высоты окна"""
        if self._check_keyboard_clock:
            print(f"⌨️ [KEYBOARD] Проверка уже запущена")
            return

        print(f"⌨️ [KEYBOARD] Запуск проверки клавиатуры (интервал 0.1с)")
        # Сохраняем исходную позицию при первом появлении
        if hasattr(self, 'content') and self._original_pos == (0, 0):
            self._original_pos = (self.content.pos[0], self.content.pos[1])
            print(f"⌨️ [KEYBOARD] Сохранена исходная позиция: {self._original_pos}")

        # Запускаем проверку каждые 0.1 секунды
        self._check_keyboard_clock = Clock.schedule_interval(self._check_window_height, 0.1)

    def _stop_keyboard_check(self):
        """Останавливает периодическую проверку"""
        if self._check_keyboard_clock:
            self._check_keyboard_clock.cancel()
            self._check_keyboard_clock = None
            print(f"⌨️ [KEYBOARD] Проверка остановлена (всего проверок: {self._keyboard_check_count})")

    def _check_window_height(self, dt):
        """Проверяет высоту окна и определяет наличие клавиатуры"""
        self._keyboard_check_count += 1

        if not hasattr(self, 'content'):
            return

        screen_height = self.get_screen_height()
        current_height = Window.height

        # Если высота окна уменьшилась более чем на 20% - клавиатура открыта
        if current_height < screen_height * 0.8:
            keyboard_height = screen_height - current_height
            if keyboard_height > 50:
                print(f"⌨️ [KEYBOARD] Проверка #{self._keyboard_check_count}: "
                      f"Высота окна {current_height}px (было {screen_height}px), "
                      f"клавиатура {keyboard_height}px")
                self._shift_popup_up(keyboard_height)
            else:
                print(f"⌨️ [KEYBOARD] Проверка #{self._keyboard_check_count}: "
                      f"Клавиатура мала ({keyboard_height}px), игнорируем")
        else:
            # Если клавиатура была открыта и закрылась
            if self._is_keyboard_shown:
                print(f"⌨️ [KEYBOARD] Проверка #{self._keyboard_check_count}: "
                      f"Клавиатура закрыта (высота окна {current_height}px)")
                self._restore_popup_position()

    def _shift_popup_up(self, keyboard_height):
        """Сдвигает попап вверх при появлении клавиатуры"""
        if keyboard_height <= 0:
            return

        # Проверяем, не изменилась ли высота клавиатуры
        if self._is_keyboard_shown and abs(self._keyboard_height - keyboard_height) < 50:
            print(f"⌨️ [KEYBOARD] Высота клавиатуры не изменилась ({keyboard_height}px), пропускаем")
            return

        self._is_keyboard_shown = True
        self._keyboard_height = keyboard_height

        print(f"⌨️ [KEYBOARD] Сдвиг попапа: высота клавиатуры {keyboard_height}px, "
              f"исходная позиция {self._original_pos}")

        # Отменяем предыдущую анимацию
        if self._shift_animation:
            self._shift_animation.cancel(self)
            self._shift_animation = None

        if hasattr(self, 'content'):
            # Сдвигаем на 60% высоты клавиатуры, но не более чем на 70% высоты экрана
            shift_amount = min(keyboard_height * 0.6, self.get_screen_height() * 0.7)
            target_y = self._original_pos[1] + shift_amount

            print(f"⌨️ [KEYBOARD] Расчет сдвига: shift={shift_amount:.0f}px, "
                  f"целевая позиция Y={target_y:.0f}px")

            # Проверяем, чтобы контент не уходил за верхний край
            max_y = self.get_screen_height() - self.content.height * 0.3
            if target_y > max_y:
                print(f"⌨️ [KEYBOARD] Корректировка: target_y {target_y:.0f} > max_y {max_y:.0f}, "
                      f"устанавливаем max_y")
                target_y = max_y

            if target_y > self._original_pos[1]:
                self._shift_animation = Animation(
                    pos=(self.content.pos[0], target_y),
                    duration=0.25,
                    transition='in_out_quad'
                )
                self._shift_animation.start(self.content)
                print(f"⌨️ [KEYBOARD] ✅ Попап сдвинут на {shift_amount:.0f}px "
                      f"(текущая позиция: {self.content.pos})")
            else:
                print(f"⌨️ [KEYBOARD] ⚠️ Сдвиг не требуется (target_y {target_y:.0f} <= {self._original_pos[1]:.0f})")

    def _restore_popup_position(self):
        """Возвращает попап на исходную позицию"""
        if not self._is_keyboard_shown:
            print(f"⌨️ [KEYBOARD] Попап уже в исходной позиции")
            return

        self._is_keyboard_shown = False
        self._keyboard_height = 0

        print(f"⌨️ [KEYBOARD] Восстановление позиции попапа: {self._original_pos}")

        if self._shift_animation:
            self._shift_animation.cancel(self)
            self._shift_animation = None

        if hasattr(self, 'content') and self._original_pos != (0, 0):
            self._shift_animation = Animation(
                pos=self._original_pos,
                duration=0.25,
                transition='in_out_quad'
            )
            self._shift_animation.start(self.content)
            print(f"⌨️ [KEYBOARD] ✅ Попап восстановлен (позиция: {self.content.pos})")

    def show_message(self, message):
        """Показывает сообщение в центре экрана на 2 секунды"""
        print(f"💬 [KEYBOARD] Показ сообщения: {message}")
        screen_width = self.get_screen_width()
        screen_height = self.get_screen_height()

        font_size = screen_height * 0.06

        msg_layout = FloatLayout()
        msg_layout.size_hint = (1, 1)
        msg_layout.pos = (0, 0)

        msg_label = Label(
            text=message,
            font_size=font_size,
            bold=True,
            color=(1, 1, 1, 1),
            outline_color=(0, 0, 0, 0.9),
            outline_width=3,
            size_hint=(1, None),
            height=screen_height * 0.2,
            pos_hint={'center_x': 0.5, 'center_y': 0.5},
            halign='center',
            valign='middle'
        )
        msg_layout.add_widget(msg_label)

        if hasattr(self, 'content'):
            self.temp_message = msg_layout
            self.content.add_widget(msg_layout)
            Clock.schedule_once(self._remove_message, 2.0)

    def _remove_message(self, dt):
        """Удаляет временное сообщение"""
        if hasattr(self, 'temp_message') and self.temp_message:
            if hasattr(self, 'content') and self.content:
                if self.temp_message in self.content.children:
                    self.content.remove_widget(self.temp_message)
            self.temp_message = None

    def on_dismiss(self):
        """При закрытии попапа восстанавливаем позицию"""
        print(f"❌ [KEYBOARD] Попап закрыт, восстанавливаем позицию")
        self._stop_keyboard_check()
        self._restore_popup_position()
        super().on_dismiss()


class TemplatePopup(BaseFairyPopup):
    """Popup with template list and buttons"""

    BUTTON_WIDTH_COEFF = 0.12
    BUTTON_HEIGHT_COEFF = 0.09
    BUTTON_FONT_SIZE_COEFF = 0.04
    BUTTON_POSITIONS_X = [0.79, 0.65, 0.50, 0.36, 0.21]
    BUTTON_POSITIONS_Y = [0.265, 0.265, 0.265, 0.265, 0.265]

    def __init__(self, callback=None, screen=None, current_template_id=None, **kwargs):
        self.title = ''
        self.callback = callback
        self.template_manager = TemplateManager()
        self.selected_template = str(current_template_id) if current_template_id is not None else None
        print(f"🔍 [TemplatePopup] Инициализация. selected_template: {self.selected_template}")
        self.screen = screen
        super().__init__(screen=screen, bg_image='assets/images/fairy_popup.png', **kwargs)
        self.create_buttons()

    def create_buttons(self):
        """Создает список шаблонов и кнопки"""
        screen_width = self.get_screen_width()
        screen_height = self.get_screen_height()

        button_width = screen_width * self.BUTTON_WIDTH_COEFF
        button_height = screen_height * self.BUTTON_HEIGHT_COEFF
        font_size = screen_height * self.BUTTON_FONT_SIZE_COEFF

        content_layout = FloatLayout()
        content_layout.size_hint = (1, 1)
        content_layout.pos = (0, 0)

        with content_layout.canvas.before:
            Color(1, 1, 1, 1)
            self.bg_rect = Rectangle(
                source=self.bg_image,
                pos=content_layout.pos,
                size=content_layout.size
            )

        content_layout.bind(pos=self.update_bg, size=self.update_bg)

        scroll_width = screen_width * 0.5
        scroll_height = screen_height * 0.4
        scroll_x = screen_width * 0.5 - (scroll_width / 2)
        scroll_y = screen_height * 0.52 - (scroll_height / 2)

        scroll = ScrollView()
        scroll.size_hint = (None, None)
        scroll.size = (scroll_width, scroll_height)
        scroll.pos = (scroll_x, scroll_y)
        scroll.background_color = (0, 0, 0, 0)
        scroll.background = ''
        scroll.background_normal = ''
        scroll.background_down = ''

        self.templates_list = GridLayout(
            cols=1,
            spacing=5,
            size_hint_y=None
        )
        self.templates_list.bind(minimum_height=self.templates_list.setter('height'))
        self.refresh_templates_list()

        scroll.add_widget(self.templates_list)
        content_layout.add_widget(scroll)

        buttons_data = [
            {'text': 'LOAD', 'color': (0.0, 0.5, 1.0, 0)},
            {'text': 'EDIT', 'color': (1.0, 0.7, 0.0, 0)},
            {'text': 'CREATE', 'color': (0.0, 1.0, 0.3, 0)},
            {'text': 'DELETE', 'color': (1.0, 0.0, 0.0, 0)},
            {'text': 'CLOSE', 'color': (0.5, 0.5, 0.5, 0)}
        ]

        self.buttons = []

        for i, data in enumerate(buttons_data):
            x_position = self.BUTTON_POSITIONS_X[i] if i < len(self.BUTTON_POSITIONS_X) else 0.5
            y_position = self.BUTTON_POSITIONS_Y[i] if i < len(self.BUTTON_POSITIONS_Y) else 0.5

            btn = SuperVisibleButton(
                text=data['text'],
                font_size=font_size,
                color=data['color'],
                size_hint=(None, None),
                size=(button_width, button_height),
                pos_hint={'center_x': x_position, 'center_y': y_position}
            )

            btn.callback = self.on_button_press
            content_layout.add_widget(btn)
            self.buttons.append(btn)

        self.content = content_layout
        print(f"✅ [TemplatePopup] UI создан")

    def update_bg(self, instance, value):
        if hasattr(self, 'bg_rect'):
            self.bg_rect.pos = instance.pos
            self.bg_rect.size = instance.size

    def refresh_templates_list(self):
        self.templates_list.clear_widgets()

        self.template_manager.reload_templates()
        templates = self.template_manager.get_templates()

        screen_height = self.get_screen_height()
        base_font_size = screen_height * 0.04
        selected_font_size = base_font_size * 1.3
        base_height = screen_height * 0.055
        selected_height = base_height * 1.25

        for template in templates:
            template_id = str(template.get('id', ''))
            is_selected = template_id == self.selected_template

            font_size = selected_font_size if is_selected else base_font_size

            btn = Button(
                text=template.get('name', 'Unnamed'),
                size_hint_y=None,
                height=selected_height if is_selected else base_height,
                background_normal='',
                background_color=(0, 0, 0, 0),
                color=(0, 0, 0, 1),
                bold=True,
                font_size=font_size
            )
            btn.template_id = template.get('id')
            btn.bind(on_press=self.select_template)
            self.templates_list.add_widget(btn)

    def select_template(self, instance):
        self.selected_template = str(instance.template_id) if instance.template_id is not None else None
        print(f"🔍 [select_template] Выбран шаблон с ID: {self.selected_template}")
        self.refresh_templates_list()

    def on_button_press(self, instance):
        button_text = instance.text
        print(f"🔘 [TemplatePopup] НАЖАТА КНОПКА: {button_text}")

        if button_text == 'LOAD':
            self.load_template()
        elif button_text == 'EDIT':
            self.edit_template()
        elif button_text == 'CREATE':
            self.create_template()
        elif button_text == 'DELETE':
            self.delete_template()
        elif button_text == 'CLOSE':
            self.close_popup()

    def load_template(self):
        print(f"📂 [TemplatePopup] Загрузка шаблона")
        if self.selected_template:
            template = None
            for t in self.template_manager.get_templates():
                if str(t.get('id', '')) == self.selected_template:
                    template = t
                    break

            if template and self.callback:
                self.callback(template)
                self.dismiss()
            else:
                self.show_message('Template not found')
        else:
            self.show_message('Please select a template')

    def edit_template(self):
        print(f"✏️ [TemplatePopup] Редактирование шаблона")
        if not self.selected_template:
            self.show_message('Please select a template to edit')
            return

        template = None
        for t in self.template_manager.get_templates():
            if str(t.get('id', '')) == self.selected_template:
                template = t
                break

        if not template:
            self.show_message('Template not found')
            return

        edit_popup = EditTemplatePopup(
            template=template,
            callback=self.on_template_updated,
            screen=self.screen
        )
        edit_popup.open()

    def on_template_updated(self, template_data):
        print(f"✅ [TemplatePopup] Шаблон обновлен: {template_data}")
        self.refresh_templates_list()

    def create_template(self):
        print(f"➕ [TemplatePopup] Создание шаблона")
        create_popup = CreateTemplatePopup(
            callback=self.on_template_created,
            screen=self.screen
        )
        create_popup.open()

    def on_template_created(self, template_data):
        print(f"✅ [TemplatePopup] Шаблон создан: {template_data}")
        self.refresh_templates_list()

    def delete_template(self):
        print(f"🗑️ [TemplatePopup] Удаление шаблона")
        if not self.selected_template:
            self.show_message('Please select a template to delete')
            return

        template_id = None
        for t in self.template_manager.get_templates():
            if str(t.get('id', '')) == self.selected_template:
                template_id = t.get('id')
                break

        if not template_id:
            self.show_message('Template not found')
            return

        success = self.template_manager.delete_template(template_id)

        if success:
            print(f"✅ [TemplatePopup] Шаблон удален")
            self.selected_template = None
            self.refresh_templates_list()
        else:
            self.show_message('Cannot delete the last template')

    def close_popup(self):
        print(f"❌ [TemplatePopup] ЗАКРЫТИЕ ПОПАПА")
        self.dismiss()


class EditTemplatePopup(BaseFairyPopup):
    """Popup for editing an existing template"""

    BUTTON_WIDTH_COEFF = 0.19
    BUTTON_HEIGHT_COEFF = 0.10
    BUTTON_FONT_SIZE_COEFF = 0.045
    BUTTON_POSITIONS_X = [0.4, 0.6]
    BUTTON_POSITIONS_Y = [0.265, 0.265]

    MAX_NAME_LENGTH = 30
    MAX_CATEGORIES = 20

    def __init__(self, template=None, callback=None, screen=None, **kwargs):
        self.title = ''
        self.template = template
        self.callback = callback
        self.screen = screen
        self.template_manager = TemplateManager()
        print(f"✏️ [EditTemplatePopup] Инициализация с шаблоном: {template.get('name') if template else 'None'}")
        super().__init__(screen=screen, bg_image='assets/images/fairy_popup_2.png', **kwargs)
        self.create_ui()

    def create_ui(self):
        screen_width = self.get_screen_width()
        screen_height = self.get_screen_height()

        content_layout = FloatLayout()
        content_layout.size_hint = (1, 1)
        content_layout.pos = (0, 0)

        with content_layout.canvas.before:
            Color(1, 1, 1, 1)
            self.bg_rect = Rectangle(
                source=self.bg_image,
                pos=content_layout.pos,
                size=content_layout.size
            )

        content_layout.bind(pos=self.update_bg, size=self.update_bg)

        font_size = screen_height * self.BUTTON_FONT_SIZE_COEFF
        label_font_size = font_size * 0.9
        input_height = screen_height * 0.08
        input_width = screen_width * 0.5

        title_label = Label(
            text='',
            font_size=font_size * 1.5,
            bold=True,
            color=(1, 1, 1, 1),
            outline_color=(0, 0, 0, 0.9),
            outline_width=2,
            size_hint=(1, None),
            height=screen_height * 0.12,
            pos_hint={'center_x': 0.5, 'center_y': 0.85},
            halign='center',
            valign='middle'
        )
        content_layout.add_widget(title_label)

        name_label = Label(
            text=f'Template Name (max {self.MAX_NAME_LENGTH} chars):',
            font_size=label_font_size,
            bold=True,
            color=(1, 1, 1, 1),
            outline_color=(0, 0, 0, 0.7),
            outline_width=1,
            size_hint=(None, None),
            size=(input_width, input_height * 0.6),
            pos_hint={'center_x': 0.5, 'center_y': 0.68},
            halign='center',
            valign='middle'
        )
        content_layout.add_widget(name_label)

        template_name = self.template.get('name', '') if self.template else ''

        self.name_input = TextInput(
            text=template_name,
            font_size=font_size * 0.9,
            size_hint=(None, None),
            size=(input_width, input_height),
            pos_hint={'center_x': 0.5, 'center_y': 0.60},
            background_color=(1, 1, 1, 0.9),
            foreground_color=(0, 0, 0, 1),
            cursor_color=(0, 0, 0, 1),
            padding=[10, 10],
            multiline=False
        )
        self.name_input.bind(text=self._limit_name_length)
        self.name_input.bind(focus=self._on_text_input_focus)
        content_layout.add_widget(self.name_input)

        categories_label = Label(
            text=f'Categories (comma separated, max {self.MAX_CATEGORIES}):',
            font_size=label_font_size,
            bold=True,
            color=(1, 1, 1, 1),
            outline_color=(0, 0, 0, 0.7),
            outline_width=1,
            size_hint=(None, None),
            size=(input_width, input_height * 0.6),
            pos_hint={'center_x': 0.5, 'center_y': 0.46},
            halign='center',
            valign='middle'
        )
        content_layout.add_widget(categories_label)

        template_categories = self.template.get('sectors', []) if self.template else []
        categories_text = ', '.join(template_categories) if template_categories else ''

        self.categories_input = TextInput(
            text=categories_text,
            font_size=font_size * 0.9,
            size_hint=(None, None),
            size=(input_width, input_height),
            pos_hint={'center_x': 0.5, 'center_y': 0.38},
            background_color=(1, 1, 1, 0.9),
            foreground_color=(0, 0, 0, 1),
            cursor_color=(0, 0, 0, 1),
            padding=[10, 10],
            multiline=False
        )
        self.categories_input.bind(text=self._limit_categories_count)
        self.categories_input.bind(focus=self._on_text_input_focus)
        content_layout.add_widget(self.categories_input)

        buttons_data = [
            {'text': 'SAVE', 'color': (0.0, 0.8, 0.2, 0)},
            {'text': 'CANCEL', 'color': (0.8, 0.0, 0.0, 0)}
        ]

        button_width = screen_width * self.BUTTON_WIDTH_COEFF
        button_height = screen_height * self.BUTTON_HEIGHT_COEFF

        for i, data in enumerate(buttons_data):
            x_position = self.BUTTON_POSITIONS_X[i] if i < len(self.BUTTON_POSITIONS_X) else 0.5
            y_position = self.BUTTON_POSITIONS_Y[i] if i < len(self.BUTTON_POSITIONS_Y) else 0.25

            btn = SuperVisibleButton(
                text=data['text'],
                font_size=font_size,
                color=data['color'],
                size_hint=(None, None),
                size=(button_width, button_height),
                pos_hint={'center_x': x_position, 'center_y': y_position}
            )
            btn.callback = self.on_button_press
            content_layout.add_widget(btn)

        self.content = content_layout
        print(f"✅ [EditTemplatePopup] UI создан")

    def _limit_name_length(self, instance, value):
        if len(value) > self.MAX_NAME_LENGTH:
            instance.text = value[:self.MAX_NAME_LENGTH]

    def _limit_categories_count(self, instance, value):
        comma_count = value.count(',')
        if comma_count >= self.MAX_CATEGORIES - 1:
            positions = []
            for i, char in enumerate(value):
                if char == ',':
                    positions.append(i)
            if len(positions) >= self.MAX_CATEGORIES - 1:
                last_allowed_pos = positions[self.MAX_CATEGORIES - 2] if self.MAX_CATEGORIES - 2 >= 0 else -1
                if last_allowed_pos >= 0:
                    instance.text = value[:last_allowed_pos + 1]

    def update_bg(self, instance, value):
        if hasattr(self, 'bg_rect'):
            self.bg_rect.pos = instance.pos
            self.bg_rect.size = instance.size

    def on_button_press(self, instance):
        print(f"🔘 [EditTemplatePopup] НАЖАТА КНОПКА: {instance.text}")
        if instance.text == 'SAVE':
            self.save_template()
        elif instance.text == 'CANCEL':
            self.dismiss()

    def save_template(self):
        name = self.name_input.text.strip()
        categories_text = self.categories_input.text.strip()

        if not name:
            self.show_message('Please enter a template name')
            return

        if not categories_text:
            self.show_message('Please enter at least one category')
            return

        if len(name) > self.MAX_NAME_LENGTH:
            self.show_message(f'Name must be less than {self.MAX_NAME_LENGTH} chars')
            return

        categories = []
        if categories_text:
            categories = [cat.strip() for cat in categories_text.split(',') if cat.strip()]
            if len(categories) > self.MAX_CATEGORIES:
                self.show_message(f'Maximum {self.MAX_CATEGORIES} categories allowed')
                return

        template_id = self.template.get('id') if self.template else None
        if not template_id:
            self.show_message('Template ID not found')
            return

        success = self.template_manager.update_template(
            template_id,
            name=name,
            sectors=categories
        )

        if success:
            print(f"✅ [EditTemplatePopup] Шаблон обновлен: {name}")
            self.dismiss()
            if self.callback:
                updated_template = self.template_manager.get_template(template_id)
                self.callback(updated_template)
        else:
            self.show_message('Failed to update template')


class CreateTemplatePopup(BaseFairyPopup):
    """Popup for creating a new template with name and categories"""

    BUTTON_WIDTH_COEFF = 0.19
    BUTTON_HEIGHT_COEFF = 0.10
    BUTTON_FONT_SIZE_COEFF = 0.045
    BUTTON_POSITIONS_X = [0.4, 0.6]
    BUTTON_POSITIONS_Y = [0.265, 0.265]

    MAX_NAME_LENGTH = 30
    MAX_CATEGORIES = 20

    def __init__(self, callback=None, screen=None, **kwargs):
        self.title = 'Create New Template'
        self.callback = callback
        self.screen = screen
        self.template_manager = TemplateManager()
        print(f"➕ [CreateTemplatePopup] Инициализация")
        super().__init__(screen=screen, bg_image='assets/images/fairy_popup_2.png', **kwargs)
        self.create_ui()

    def create_ui(self):
        screen_width = self.get_screen_width()
        screen_height = self.get_screen_height()

        content_layout = FloatLayout()
        content_layout.size_hint = (1, 1)
        content_layout.pos = (0, 0)

        with content_layout.canvas.before:
            Color(1, 1, 1, 1)
            self.bg_rect = Rectangle(
                source=self.bg_image,
                pos=content_layout.pos,
                size=content_layout.size
            )

        content_layout.bind(pos=self.update_bg, size=self.update_bg)

        font_size = screen_height * self.BUTTON_FONT_SIZE_COEFF
        label_font_size = font_size * 0.9
        input_height = screen_height * 0.08
        input_width = screen_width * 0.5

        title_label = Label(
            text='',
            font_size=font_size * 1.5,
            bold=True,
            color=(1, 1, 1, 1),
            outline_color=(0, 0, 0, 0.9),
            outline_width=2,
            size_hint=(1, None),
            height=screen_height * 0.12,
            pos_hint={'center_x': 0.5, 'center_y': 0.85},
            halign='center',
            valign='middle'
        )
        content_layout.add_widget(title_label)

        name_label = Label(
            text=f'Template Name (max {self.MAX_NAME_LENGTH} chars):',
            font_size=label_font_size,
            bold=True,
            color=(1, 1, 1, 1),
            outline_color=(0, 0, 0, 0.7),
            outline_width=1,
            size_hint=(None, None),
            size=(input_width, input_height * 0.6),
            pos_hint={'center_x': 0.5, 'center_y': 0.68},
            halign='center',
            valign='middle'
        )
        content_layout.add_widget(name_label)

        self.name_input = TextInput(
            hint_text='Enter template name...',
            font_size=font_size * 0.9,
            size_hint=(None, None),
            size=(input_width, input_height),
            pos_hint={'center_x': 0.5, 'center_y': 0.60},
            background_color=(1, 1, 1, 0.9),
            foreground_color=(0, 0, 0, 1),
            cursor_color=(0, 0, 0, 1),
            padding=[10, 10],
            multiline=False
        )
        self.name_input.bind(text=self._limit_name_length)
        self.name_input.bind(focus=self._on_text_input_focus)
        content_layout.add_widget(self.name_input)

        categories_label = Label(
            text=f'Categories (comma separated, max {self.MAX_CATEGORIES}):',
            font_size=label_font_size,
            bold=True,
            color=(1, 1, 1, 1),
            outline_color=(0, 0, 0, 0.7),
            outline_width=1,
            size_hint=(None, None),
            size=(input_width, input_height * 0.6),
            pos_hint={'center_x': 0.5, 'center_y': 0.46},
            halign='center',
            valign='middle'
        )
        content_layout.add_widget(categories_label)

        self.categories_input = TextInput(
            hint_text='e.g. math, science, history',
            font_size=font_size * 0.9,
            size_hint=(None, None),
            size=(input_width, input_height),
            pos_hint={'center_x': 0.5, 'center_y': 0.38},
            background_color=(1, 1, 1, 0.9),
            foreground_color=(0, 0, 0, 1),
            cursor_color=(0, 0, 0, 1),
            padding=[10, 10],
            multiline=False
        )
        self.categories_input.bind(text=self._limit_categories_count)
        self.categories_input.bind(focus=self._on_text_input_focus)
        content_layout.add_widget(self.categories_input)

        buttons_data = [
            {'text': 'CREATE', 'color': (0.0, 1.0, 0.3, 0)},
            {'text': 'CANCEL', 'color': (1.0, 0.0, 0.0, 0)}
        ]

        button_width = screen_width * self.BUTTON_WIDTH_COEFF
        button_height = screen_height * self.BUTTON_HEIGHT_COEFF

        for i, data in enumerate(buttons_data):
            x_position = self.BUTTON_POSITIONS_X[i] if i < len(self.BUTTON_POSITIONS_X) else 0.5
            y_position = self.BUTTON_POSITIONS_Y[i] if i < len(self.BUTTON_POSITIONS_Y) else 0.25

            btn = SuperVisibleButton(
                text=data['text'],
                font_size=font_size,
                color=data['color'],
                size_hint=(None, None),
                size=(button_width, button_height),
                pos_hint={'center_x': x_position, 'center_y': y_position}
            )
            btn.callback = self.on_button_press
            content_layout.add_widget(btn)

        self.content = content_layout
        print(f"✅ [CreateTemplatePopup] UI создан")

    def _limit_name_length(self, instance, value):
        if len(value) > self.MAX_NAME_LENGTH:
            instance.text = value[:self.MAX_NAME_LENGTH]

    def _limit_categories_count(self, instance, value):
        comma_count = value.count(',')
        if comma_count >= self.MAX_CATEGORIES - 1:
            positions = []
            for i, char in enumerate(value):
                if char == ',':
                    positions.append(i)
            if len(positions) >= self.MAX_CATEGORIES - 1:
                last_allowed_pos = positions[self.MAX_CATEGORIES - 2] if self.MAX_CATEGORIES - 2 >= 0 else -1
                if last_allowed_pos >= 0:
                    instance.text = value[:last_allowed_pos + 1]

    def update_bg(self, instance, value):
        if hasattr(self, 'bg_rect'):
            self.bg_rect.pos = instance.pos
            self.bg_rect.size = instance.size

    def on_button_press(self, instance):
        print(f"🔘 [CreateTemplatePopup] НАЖАТА КНОПКА: {instance.text}")
        if instance.text == 'CREATE':
            self.create_template()
        elif instance.text == 'CANCEL':
            self.dismiss()

    def create_template(self):
        name = self.name_input.text.strip()
        categories_text = self.categories_input.text.strip()

        if not name:
            self.show_message('Please enter a template name')
            return

        if not categories_text:
            self.show_message('Please enter at least one category')
            return

        if len(name) > self.MAX_NAME_LENGTH:
            self.show_message(f'Name must be less than {self.MAX_NAME_LENGTH} chars')
            return

        categories = []
        if categories_text:
            categories = [cat.strip() for cat in categories_text.split(',') if cat.strip()]
            if len(categories) > self.MAX_CATEGORIES:
                self.show_message(f'Maximum {self.MAX_CATEGORIES} categories allowed')
                return

        template_data = {
            'name': name,
            'categories': categories
        }

        success = self.template_manager.create_template(template_data)

        if success:
            print(f"✅ [CreateTemplatePopup] Шаблон создан: {name}")
            self.dismiss()
            if self.callback:
                self.callback(template_data)
        else:
            self.show_message('Failed to create template. Template may already exist.')


class ConfirmPopup(BaseFairyPopup):
    BUTTON_WIDTH_COEFF = 0.35
    BUTTON_HEIGHT_COEFF = 0.12
    BUTTON_FONT_SIZE_COEFF = 0.05
    BUTTON_POSITIONS_X = [0.5, 0.5]
    BUTTON_POSITIONS_Y = [0.40, 0.25]

    def __init__(self, message='Are you sure?', callback=None, screen=None, **kwargs):
        self.title = message
        self.callback = callback
        self.screen = screen
        super().__init__(screen=screen, bg_image='assets/images/fairy_popup.png', **kwargs)
        self.create_buttons()

    def create_buttons(self):
        screen_width = self.get_screen_width()
        screen_height = self.get_screen_height()

        content_layout = FloatLayout()
        content_layout.size_hint = (1, 1)
        content_layout.pos = (0, 0)

        with content_layout.canvas.before:
            Color(1, 1, 1, 1)
            self.bg_rect = Rectangle(
                source=self.bg_image,
                pos=content_layout.pos,
                size=content_layout.size
            )

        content_layout.bind(pos=self.update_bg, size=self.update_bg)

        button_width = screen_width * self.BUTTON_WIDTH_COEFF
        button_height = screen_height * self.BUTTON_HEIGHT_COEFF
        font_size = screen_height * self.BUTTON_FONT_SIZE_COEFF

        message_label = Label(
            text=self.title,
            font_size=font_size * 1.2,
            bold=True,
            color=(1, 1, 1, 1),
            outline_color=(0, 0, 0, 0.9),
            outline_width=2,
            size_hint=(1, None),
            height=screen_height * 0.15,
            pos_hint={'center_x': 0.5, 'center_y': 0.65},
            halign='center',
            valign='middle'
        )
        content_layout.add_widget(message_label)

        buttons_data = [
            {'text': '✅ YES', 'color': (0.0, 1.0, 0.3, 1)},
            {'text': '❌ NO', 'color': (1.0, 0.0, 0.0, 1)}
        ]

        for i, data in enumerate(buttons_data):
            x_position = self.BUTTON_POSITIONS_X[i] if i < len(self.BUTTON_POSITIONS_X) else 0.5
            y_position = self.BUTTON_POSITIONS_Y[i] if i < len(self.BUTTON_POSITIONS_Y) else 0.5

            btn = SuperVisibleButton(
                text=data['text'],
                font_size=font_size,
                color=data['color'],
                size_hint=(None, None),
                size=(button_width, button_height),
                pos_hint={'center_x': x_position, 'center_y': y_position}
            )
            btn.callback = self.on_button_press
            content_layout.add_widget(btn)

        self.content = content_layout

    def update_bg(self, instance, value):
        if hasattr(self, 'bg_rect'):
            self.bg_rect.pos = instance.pos
            self.bg_rect.size = instance.size

    def on_button_press(self, instance):
        print(f"🔘 [ConfirmPopup] НАЖАТА КНОПКА: {instance.text}")
        if instance.text == '✅ YES':
            self.confirm(True)
        elif instance.text == '❌ NO':
            self.confirm(False)

    def confirm(self, result):
        print(f"✅ [ConfirmPopup] Результат: {result}")
        if self.callback:
            self.callback(result)
        self.dismiss()


class MessagePopup(BaseFairyPopup):
    """Старый класс для сообщений - больше не используется, оставлен для совместимости"""
    BUTTON_WIDTH_COEFF = 0.35
    BUTTON_HEIGHT_COEFF = 0.12
    BUTTON_FONT_SIZE_COEFF = 0.05
    BUTTON_POSITIONS_X = [0.5]
    BUTTON_POSITIONS_Y = [0.30]

    def __init__(self, title='Message', message='', screen=None, **kwargs):
        self.title = title
        self.message = message
        self.screen = screen
        super().__init__(screen=screen, bg_image='assets/images/fairy_popup.png', **kwargs)
        self.create_ui()
        Clock.schedule_once(self.dismiss, 2.0)

    def create_ui(self):
        screen_width = self.get_screen_width()
        screen_height = self.get_screen_height()

        content_layout = FloatLayout()
        content_layout.size_hint = (1, 1)
        content_layout.pos = (0, 0)

        with content_layout.canvas.before:
            Color(1, 1, 1, 1)
            self.bg_rect = Rectangle(
                source=self.bg_image,
                pos=content_layout.pos,
                size=content_layout.size
            )

        content_layout.bind(pos=self.update_bg, size=self.update_bg)

        font_size = screen_height * self.BUTTON_FONT_SIZE_COEFF

        title_label = Label(
            text=self.title,
            font_size=font_size * 1.2,
            bold=True,
            color=(1, 1, 1, 1),
            outline_color=(0, 0, 0, 0.9),
            outline_width=2,
            size_hint=(1, None),
            height=screen_height * 0.12,
            pos_hint={'center_x': 0.5, 'center_y': 0.65},
            halign='center',
            valign='middle'
        )
        content_layout.add_widget(title_label)

        message_label = Label(
            text=self.message,
            font_size=font_size * 0.9,
            bold=False,
            color=(1, 1, 1, 1),
            outline_color=(0, 0, 0, 0.7),
            outline_width=1,
            size_hint=(1, None),
            height=screen_height * 0.1,
            pos_hint={'center_x': 0.5, 'center_y': 0.50},
            halign='center',
            valign='middle'
        )
        content_layout.add_widget(message_label)

        self.content = content_layout

    def update_bg(self, instance, value):
        if hasattr(self, 'bg_rect'):
            self.bg_rect.pos = instance.pos
            self.bg_rect.size = instance.size