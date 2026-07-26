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
        super().__init__(**kwargs)
        self.auto_dismiss = False

        # Устанавливаем размер на весь экран
        self.size_hint = (1, 1)
        self.size = Window.size

        # Убираем ВСЕ отступы у попапа
        self.background_color = (0, 0, 0, 0)  # Прозрачный фон
        self.background = ''  # Убираем стандартный фон
        self.background_normal = ''  # Убираем стандартный фон
        self.background_down = ''  # Убираем стандартный фон

        # ОБНУЛЯЕМ ВСЕ ОТСТУПЫ
        self.padding = [0, 0, 0, 0]
        self.spacing = 0
        self.separator_height = 0
        self.separator_color = [0, 0, 0, 0]

        # Дополнительные параметры для гарантии
        self.title = ''  # Убираем заголовок
        self.title_size = 0
        self.title_align = 'center'

        # Убираем содержимое заголовка
        self.title_color = [0, 0, 0, 0]

    def get_screen_width(self):
        if self.screen and hasattr(self.screen, 'get_screen_width'):
            return self.screen.get_screen_width()
        return Window.width

    def get_screen_height(self):
        if self.screen and hasattr(self.screen, 'get_screen_height'):
            return self.screen.get_screen_height()
        return Window.height

    def show_message(self, message):
        """Показывает сообщение в центре экрана на 2 секунды"""
        screen_width = self.get_screen_width()
        screen_height = self.get_screen_height()

        font_size = screen_height * 0.06

        msg_layout = FloatLayout()
        msg_layout.size_hint = (1, 1)
        msg_layout.pos = (0, 0)

        # ФОН УБРАН - никаких Canvas инструкций

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
        # Сохраняем как строку для надежного сравнения
        self.selected_template = str(current_template_id) if current_template_id is not None else None
        print(
            f"🔍 [TemplatePopup] Инициализация. current_template_id: {current_template_id}, selected_template: {self.selected_template}")
        self.screen = screen
        # Используем стандартный фон для основного попапа
        super().__init__(screen=screen, bg_image='assets/images/fairy_popup.png', **kwargs)
        self.create_buttons()

    def create_buttons(self):
        """Создает список шаблонов и кнопки"""
        screen_width = self.get_screen_width()
        screen_height = self.get_screen_height()

        # ВЫЧИСЛЯЕМ РАЗМЕРЫ КНОПОК
        button_width = screen_width * self.BUTTON_WIDTH_COEFF
        button_height = screen_height * self.BUTTON_HEIGHT_COEFF
        font_size = screen_height * self.BUTTON_FONT_SIZE_COEFF

        # ============ СОЗДАЕМ FloatLayout НАПРЯМУЮ КАК CONTENT ============
        content_layout = FloatLayout()
        content_layout.size_hint = (1, 1)
        content_layout.pos = (0, 0)

        # Фоновое изображение (в before) - НА ВЕСЬ ЭКРАН
        with content_layout.canvas.before:
            Color(1, 1, 1, 1)
            self.bg_rect = Rectangle(
                source=self.bg_image,
                pos=content_layout.pos,
                size=content_layout.size
            )

        # Обновляем фон при изменении позиции или размера
        content_layout.bind(pos=self.update_bg, size=self.update_bg)

        # ============ КОНТЕЙНЕР СО СПИСКОМ ============
        # Создаем ScrollView с абсолютными координатами
        scroll_width = screen_width * 0.5
        scroll_height = screen_height * 0.4
        scroll_x = screen_width * 0.5 - (scroll_width / 2)
        scroll_y = screen_height * 0.52 - (scroll_height / 2)

        scroll = ScrollView()
        scroll.size_hint = (None, None)
        scroll.size = (scroll_width, scroll_height)
        scroll.pos = (scroll_x, scroll_y)
        # Убираем фон ScrollView
        scroll.background_color = (0, 0, 0, 0)
        scroll.background = ''
        scroll.background_normal = ''
        scroll.background_down = ''

        # Список шаблонов
        self.templates_list = GridLayout(
            cols=1,
            spacing=5,
            size_hint_y=None
        )
        self.templates_list.bind(minimum_height=self.templates_list.setter('height'))
        self.refresh_templates_list()

        scroll.add_widget(self.templates_list)
        content_layout.add_widget(scroll)

        # ============ КНОПКИ ============
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

        # Устанавливаем content_layout как content напрямую
        self.content = content_layout

    def update_bg(self, instance, value):
        """Обновляет фоновое изображение"""
        if hasattr(self, 'bg_rect'):
            self.bg_rect.pos = instance.pos
            self.bg_rect.size = instance.size

    def refresh_templates_list(self):
        """Обновляет список шаблонов"""
        self.templates_list.clear_widgets()

        # Перезагружаем шаблоны из файла перед обновлением
        self.template_manager.reload_templates()
        templates = self.template_manager.get_templates()

        # Получаем размеры экрана
        screen_height = self.get_screen_height()
        screen_width = self.get_screen_width()

        # Вычисляем размеры шрифта в зависимости от экрана
        base_font_size = screen_height * 0.04
        selected_font_size = base_font_size * 1.3

        # Вычисляем высоту кнопок
        base_height = screen_height * 0.055
        selected_height = base_height * 1.25

        print(f"🔍 [refresh_templates_list] Выбранный ID: {self.selected_template}")
        print(f"🔍 [refresh_templates_list] Всего шаблонов: {len(templates)}")

        # Выводим все ID шаблонов для отладки
        for t in templates:
            print(f"   Шаблон: {t.get('name')}, ID: {t.get('id')} (тип: {type(t.get('id'))})")

        for template in templates:
            # Приводим ID к строке для надежного сравнения
            template_id = str(template.get('id', ''))
            is_selected = template_id == self.selected_template

            if is_selected:
                print(f"✅ [refresh_templates_list] ВЫБРАН шаблон: {template.get('name')} (ID: {template_id})")
            else:
                print(f"   Обычный шаблон: {template.get('name')} (ID: {template_id})")

            # Для выбранного шаблона увеличиваем шрифт, для остальных - стандартный
            font_size = selected_font_size if is_selected else base_font_size

            btn = Button(
                text=template.get('name', 'Unnamed'),
                size_hint_y=None,
                height=selected_height if is_selected else base_height,
                background_normal='',
                background_color=(0, 0, 0, 0),  # Прозрачный фон для всех
                color=(0, 0, 0, 1),  # Черный цвет текста
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
            # Ищем шаблон по ID
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

        # Получаем выбранный шаблон
        template = None
        for t in self.template_manager.get_templates():
            if str(t.get('id', '')) == self.selected_template:
                template = t
                break

        if not template:
            self.show_message('Template not found')
            return

        # Открываем попап редактирования с данными шаблона
        edit_popup = EditTemplatePopup(
            template=template,
            callback=self.on_template_updated,
            screen=self.screen
        )
        edit_popup.open()

    def on_template_updated(self, template_data):
        """Обработчик обновления шаблона"""
        print(f"✅ [TemplatePopup] Шаблон обновлен: {template_data}")
        # Обновляем список шаблонов
        self.refresh_templates_list()

    def create_template(self):
        print(f"➕ [TemplatePopup] Создание шаблона")
        # Открываем попап создания шаблона
        create_popup = CreateTemplatePopup(
            callback=self.on_template_created,
            screen=self.screen
        )
        create_popup.open()

    def on_template_created(self, template_data):
        """Обработчик создания нового шаблона"""
        print(f"✅ [TemplatePopup] Шаблон создан: {template_data}")
        # Обновляем список шаблонов
        self.refresh_templates_list()

    def delete_template(self):
        """Удаляет выбранный шаблон без подтверждения"""
        print(f"🗑️ [TemplatePopup] Удаление шаблона")
        if not self.selected_template:
            self.show_message('Please select a template to delete')
            return

        # Ищем ID шаблона
        template_id = None
        for t in self.template_manager.get_templates():
            if str(t.get('id', '')) == self.selected_template:
                template_id = t.get('id')
                break

        if not template_id:
            self.show_message('Template not found')
            return

        # Пытаемся удалить шаблон
        success = self.template_manager.delete_template(template_id)

        if success:
            print(f"✅ [TemplatePopup] Шаблон удален")
            # Сбрасываем выбранный шаблон
            self.selected_template = None
            # Обновляем список
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

    # Ограничения
    MAX_NAME_LENGTH = 30
    MAX_CATEGORIES = 20

    def __init__(self, template=None, callback=None, screen=None, **kwargs):
        self.title = ''
        self.template = template
        self.callback = callback
        self.screen = screen
        self.template_manager = TemplateManager()
        # Используем fairy_popup_2.png для редактирования
        super().__init__(screen=screen, bg_image='assets/images/fairy_popup_2.png', **kwargs)
        self.create_ui()

    def create_ui(self):
        screen_width = self.get_screen_width()
        screen_height = self.get_screen_height()

        content_layout = FloatLayout()
        content_layout.size_hint = (1, 1)
        content_layout.pos = (0, 0)

        # Фоновое изображение (в before) - НА ВЕСЬ ЭКРАН
        with content_layout.canvas.before:
            Color(1, 1, 1, 1)
            self.bg_rect = Rectangle(
                source=self.bg_image,
                pos=content_layout.pos,
                size=content_layout.size
            )

        # Обновляем фон при изменении позиции или размера
        content_layout.bind(pos=self.update_bg, size=self.update_bg)

        font_size = screen_height * self.BUTTON_FONT_SIZE_COEFF
        label_font_size = font_size * 0.9
        input_height = screen_height * 0.08
        input_width = screen_width * 0.5

        # Заголовок
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

        # Поле для названия шаблона (заполнено данными из шаблона)
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

        # Заполняем поле названия из шаблона
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
        # Добавляем ограничение на длину
        self.name_input.bind(text=self._limit_name_length)
        content_layout.add_widget(self.name_input)

        # Поле для категорий (заполнено данными из шаблона)
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

        # Заполняем поле категорий из шаблона (преобразуем список в строку через запятую)
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
        # Добавляем ограничение на количество категорий через запятые
        self.categories_input.bind(text=self._limit_categories_count)
        content_layout.add_widget(self.categories_input)

        # Кнопки с прозрачным фоном
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

    def _limit_name_length(self, instance, value):
        """Ограничивает длину названия"""
        if len(value) > self.MAX_NAME_LENGTH:
            instance.text = value[:self.MAX_NAME_LENGTH]

    def _limit_categories_count(self, instance, value):
        """Ограничивает количество категорий по числу запятых"""
        # Считаем количество запятых
        comma_count = value.count(',')
        # Если запятых больше или равно MAX_CATEGORIES - 1 (так как категорий на 1 больше чем запятых)
        if comma_count >= self.MAX_CATEGORIES - 1:
            # Находим позицию последней запятой, которая превышает лимит
            # Ищем позицию (MAX_CATEGORIES - 1)-й запятой
            positions = []
            for i, char in enumerate(value):
                if char == ',':
                    positions.append(i)
            if len(positions) >= self.MAX_CATEGORIES - 1:
                # Обрезаем текст до позиции последней допустимой запятой
                last_allowed_pos = positions[self.MAX_CATEGORIES - 2] if self.MAX_CATEGORIES - 2 >= 0 else -1
                if last_allowed_pos >= 0:
                    instance.text = value[:last_allowed_pos + 1]

    def update_bg(self, instance, value):
        """Обновляет фоновое изображение"""
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
        """Сохраняет изменения в шаблоне"""
        name = self.name_input.text.strip()
        categories_text = self.categories_input.text.strip()

        # Проверка на пустые поля
        if not name:
            self.show_message('Please enter a template name')
            return

        if not categories_text:
            self.show_message('Please enter at least one category')
            return

        # Проверка длины названия
        if len(name) > self.MAX_NAME_LENGTH:
            self.show_message(f'Name must be less than {self.MAX_NAME_LENGTH} chars')
            return

        # Разбираем категории
        categories = []
        if categories_text:
            categories = [cat.strip() for cat in categories_text.split(',') if cat.strip()]

            # Проверка количества категорий
            if len(categories) > self.MAX_CATEGORIES:
                self.show_message(f'Maximum {self.MAX_CATEGORIES} categories allowed')
                return

        # Обновляем шаблон
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
                # Возвращаем обновленные данные
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

    # Ограничения
    MAX_NAME_LENGTH = 30
    MAX_CATEGORIES = 20

    def __init__(self, callback=None, screen=None, **kwargs):
        self.title = 'Create New Template'
        self.callback = callback
        self.screen = screen
        self.template_manager = TemplateManager()
        # Используем fairy_popup_2.png для создания
        super().__init__(screen=screen, bg_image='assets/images/fairy_popup_2.png', **kwargs)
        self.create_ui()

    def create_ui(self):
        screen_width = self.get_screen_width()
        screen_height = self.get_screen_height()

        content_layout = FloatLayout()
        content_layout.size_hint = (1, 1)
        content_layout.pos = (0, 0)

        # Фоновое изображение (в before) - НА ВЕСЬ ЭКРАН
        with content_layout.canvas.before:
            Color(1, 1, 1, 1)
            self.bg_rect = Rectangle(
                source=self.bg_image,
                pos=content_layout.pos,
                size=content_layout.size
            )

        # Обновляем фон при изменении позиции или размера
        content_layout.bind(pos=self.update_bg, size=self.update_bg)

        font_size = screen_height * self.BUTTON_FONT_SIZE_COEFF
        label_font_size = font_size * 0.9
        input_height = screen_height * 0.08
        input_width = screen_width * 0.5

        # Заголовок
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

        # Поле для названия шаблона
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
        # Добавляем ограничение на длину
        self.name_input.bind(text=self._limit_name_length)
        content_layout.add_widget(self.name_input)

        # Поле для категорий
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
        # Добавляем ограничение на количество категорий через запятые
        self.categories_input.bind(text=self._limit_categories_count)
        content_layout.add_widget(self.categories_input)

        # Кнопки с прозрачным фоном
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

    def _limit_name_length(self, instance, value):
        """Ограничивает длину названия"""
        if len(value) > self.MAX_NAME_LENGTH:
            instance.text = value[:self.MAX_NAME_LENGTH]

    def _limit_categories_count(self, instance, value):
        """Ограничивает количество категорий по числу запятых"""
        # Считаем количество запятых
        comma_count = value.count(',')
        # Если запятых больше или равно MAX_CATEGORIES - 1 (так как категорий на 1 больше чем запятых)
        if comma_count >= self.MAX_CATEGORIES - 1:
            # Находим позицию последней запятой, которая превышает лимит
            # Ищем позицию (MAX_CATEGORIES - 1)-й запятой
            positions = []
            for i, char in enumerate(value):
                if char == ',':
                    positions.append(i)
            if len(positions) >= self.MAX_CATEGORIES - 1:
                # Обрезаем текст до позиции последней допустимой запятой
                last_allowed_pos = positions[self.MAX_CATEGORIES - 2] if self.MAX_CATEGORIES - 2 >= 0 else -1
                if last_allowed_pos >= 0:
                    instance.text = value[:last_allowed_pos + 1]

    def update_bg(self, instance, value):
        """Обновляет фоновое изображение"""
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
        """Создает новый шаблон из введенных данных"""
        name = self.name_input.text.strip()
        categories_text = self.categories_input.text.strip()

        # Проверка на пустые поля
        if not name:
            self.show_message('Please enter a template name')
            return

        if not categories_text:
            self.show_message('Please enter at least one category')
            return

        # Проверка длины названия
        if len(name) > self.MAX_NAME_LENGTH:
            self.show_message(f'Name must be less than {self.MAX_NAME_LENGTH} chars')
            return

        # Разбираем категории
        categories = []
        if categories_text:
            categories = [cat.strip() for cat in categories_text.split(',') if cat.strip()]

            # Проверка количества категорий
            if len(categories) > self.MAX_CATEGORIES:
                self.show_message(f'Maximum {self.MAX_CATEGORIES} categories allowed')
                return

        # Создаем шаблон
        template_data = {
            'name': name,
            'categories': categories
        }

        # Сохраняем шаблон через менеджер
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
        # Используем стандартный фон
        super().__init__(screen=screen, bg_image='assets/images/fairy_popup.png', **kwargs)
        self.create_buttons()

    def create_buttons(self):
        screen_width = self.get_screen_width()
        screen_height = self.get_screen_height()

        content_layout = FloatLayout()
        content_layout.size_hint = (1, 1)
        content_layout.pos = (0, 0)

        # Фоновое изображение (в before) - НА ВЕСЬ ЭКРАН
        with content_layout.canvas.before:
            Color(1, 1, 1, 1)
            self.bg_rect = Rectangle(
                source=self.bg_image,
                pos=content_layout.pos,
                size=content_layout.size
            )

        # Обновляем фон при изменении позиции или размера
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
        """Обновляет фоновое изображение"""
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