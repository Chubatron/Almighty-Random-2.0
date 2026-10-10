from kivy.uix.popup import Popup
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.scrollview import ScrollView
from kivy.uix.image import Image
from kivy.uix.behaviors import ButtonBehavior
from kivy.uix.textinput import TextInput
from kivy.core.window import Window
from kivy.clock import Clock
from kivy.graphics import Color, Rectangle


class ImageButton(ButtonBehavior, Image):
    """Кнопка с изображением"""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.allow_stretch = True
        self.keep_ratio = True


class DrawTemplatePopup(Popup):
    """Попап для выбора шаблона жеребьёвки"""

    def __init__(self, template_manager, callback=None, **kwargs):
        super().__init__(**kwargs)

        self.template_manager = template_manager
        self.callback = callback

        # Настройки попапа
        self.title = 'Шаблоны жеребьёвки'
        self.size_hint = (0.9, 0.85)
        self.auto_dismiss = True
        self.separator_color = (0.5, 0.8, 1, 1)
        self.separator_height = 2

        # Создаем основной контейнер
        self.main_layout = FloatLayout()
        self.content = self.main_layout

        # Создаем содержимое
        self._build_content()

        # Принудительно обновляем размеры при открытии
        self.bind(on_open=self._on_open)

    def _build_content(self):
        """Строит содержимое попапа"""
        # Очищаем основной контейнер
        self.main_layout.clear_widgets()

        # Заголовок
        title_label = Label(
            text='📋 УПРАВЛЕНИЕ ШАБЛОНАМИ',
            font_size='20sp',
            bold=True,
            color=(1, 1, 1, 1),
            size_hint=(1, 0.08),
            pos_hint={'x': 0, 'top': 1}
        )
        self.main_layout.add_widget(title_label)

        # Верхняя панель с кнопками
        top_panel = BoxLayout(
            size_hint=(1, 0.08),
            pos_hint={'x': 0, 'y': 0.92},
            spacing=10,
            padding=[10, 5, 10, 5]
        )

        # Кнопка СОЗДАТЬ
        create_btn = Button(
            text='➕ СОЗДАТЬ',
            font_size='14sp',
            bold=True,
            color=(1, 1, 1, 1),
            background_color=(0.2, 0.6, 0.2, 1),
            size_hint_x=0.25
        )
        create_btn.bind(on_release=self._show_create_template)
        top_panel.add_widget(create_btn)

        # Кнопка РЕДАКТИРОВАТЬ
        self.edit_btn = Button(
            text='✏️ РЕДАКТИРОВАТЬ',
            font_size='14sp',
            bold=True,
            color=(1, 1, 1, 1),
            background_color=(0.2, 0.4, 0.8, 1),
            size_hint_x=0.25,
            disabled=True
        )
        self.edit_btn.bind(on_release=self._show_edit_template)
        top_panel.add_widget(self.edit_btn)

        # Кнопка УДАЛИТЬ
        self.delete_btn = Button(
            text='🗑 УДАЛИТЬ',
            font_size='14sp',
            bold=True,
            color=(1, 1, 1, 1),
            background_color=(0.8, 0.2, 0.2, 1),
            size_hint_x=0.25,
            disabled=True
        )
        self.delete_btn.bind(on_release=self._delete_selected_template)
        top_panel.add_widget(self.delete_btn)

        # Кнопка ВЫБРАТЬ
        self.select_btn = Button(
            text='✅ ВЫБРАТЬ',
            font_size='14sp',
            bold=True,
            color=(1, 1, 1, 1),
            background_color=(0.8, 0.5, 0.1, 1),
            size_hint_x=0.25,
            disabled=True
        )
        self.select_btn.bind(on_release=self._select_selected_template)
        top_panel.add_widget(self.select_btn)

        self.main_layout.add_widget(top_panel)

        # Основная область со списком шаблонов (таблица)
        scroll_layout = BoxLayout(
            orientation='vertical',
            spacing=2,
            padding=[10, 5, 10, 5],
            size_hint=(1, 0.76),
            pos_hint={'x': 0, 'y': 0.08}
        )

        # Заголовки таблицы
        header = BoxLayout(
            size_hint_y=None,
            height=35,
            spacing=2,
            padding=[5, 5, 5, 5]
        )

        # Фон заголовка
        with header.canvas.before:
            Color(0.2, 0.3, 0.5, 0.8)
            Rectangle(pos=header.pos, size=header.size)
        header.bind(pos=self._update_header_bg, size=self._update_header_bg)

        # Заголовки столбцов
        title_header = Label(
            text='📋 НАЗВАНИЕ',
            font_size='13sp',
            bold=True,
            color=(1, 1, 1, 1),
            size_hint_x=0.30,
            halign='left'
        )
        header.add_widget(title_header)

        players_header = Label(
            text='👥 ИГРОКИ',
            font_size='13sp',
            bold=True,
            color=(1, 1, 1, 1),
            size_hint_x=0.40,
            halign='left'
        )
        header.add_widget(players_header)

        teams_header = Label(
            text='🏆 КОМАНД',
            font_size='13sp',
            bold=True,
            color=(1, 1, 1, 1),
            size_hint_x=0.15,
            halign='center'
        )
        header.add_widget(teams_header)

        # Пустой заголовок для кнопки удаления
        delete_header = Label(
            text='',
            font_size='13sp',
            color=(1, 1, 1, 1),
            size_hint_x=0.15,
            halign='center'
        )
        header.add_widget(delete_header)

        scroll_layout.add_widget(header)

        # Получаем шаблоны
        templates = self.template_manager.get_templates()

        if not templates:
            # Если шаблонов нет
            empty_label = Label(
                text='Нет доступных шаблонов\n\nНажмите "СОЗДАТЬ" чтобы добавить новый',
                font_size='18sp',
                color=(0.8, 0.8, 0.8, 1),
                size_hint_y=None,
                height=200
            )
            scroll_layout.add_widget(empty_label)
        else:
            # Добавляем каждый шаблон
            for template in templates:
                self._add_template_row(scroll_layout, template)

        # Добавляем ScrollView
        scroll = ScrollView(
            size_hint=(1, 0.76),
            pos_hint={'x': 0, 'y': 0.08},
            bar_width=8,
            bar_color=(0.5, 0.8, 1, 0.5),
            bar_inactive_color=(0.3, 0.3, 0.5, 0.3)
        )
        scroll.add_widget(scroll_layout)
        self.main_layout.add_widget(scroll)

        # Информационная панель снизу
        bottom_panel = BoxLayout(
            size_hint=(1, 0.08),
            pos_hint={'x': 0, 'y': 0},
            spacing=10,
            padding=[10, 5, 10, 5]
        )

        # Информация о количестве шаблонов
        info_label = Label(
            text=f'Шаблонов: {len(templates)}',
            font_size='12sp',
            color=(0.7, 0.7, 0.7, 1),
            size_hint_x=0.7,
            halign='left'
        )
        bottom_panel.add_widget(info_label)

        # Кнопка ЗАКРЫТЬ
        close_btn = Button(
            text='❌ ЗАКРЫТЬ',
            font_size='14sp',
            bold=True,
            color=(1, 1, 1, 1),
            background_color=(0.3, 0.2, 0.5, 0.8),
            size_hint_x=0.3
        )
        close_btn.bind(on_release=self.dismiss)
        bottom_panel.add_widget(close_btn)

        self.main_layout.add_widget(bottom_panel)

        # Сохраняем ссылку на информацию
        self.info_label = info_label

    def _update_header_bg(self, instance, value):
        """Обновляет фон заголовка при изменении позиции или размера"""
        instance.canvas.before.clear()
        with instance.canvas.before:
            Color(0.2, 0.3, 0.5, 0.8)
            Rectangle(pos=instance.pos, size=instance.size)

    def _add_template_row(self, parent, template):
        """Добавляет строку с шаблоном в список"""
        row = BoxLayout(
            size_hint_y=None,
            height=45,
            spacing=2,
            padding=[5, 3, 5, 3]
        )

        # Сохраняем данные шаблона в строке
        row.template_data = template
        row.selected = False

        # Фон строки
        with row.canvas.before:
            Color(0.15, 0.15, 0.25, 0.5)
            Rectangle(pos=row.pos, size=row.size)
        row.bind(pos=self._update_row_bg, size=self._update_row_bg)

        # Название шаблона
        name_label = Label(
            text=template.get('name', 'Без названия'),
            font_size='13sp',
            color=(0.9, 0.9, 0.9, 1),
            size_hint_x=0.30,
            halign='left',
            text_size=(None, None),
            shorten=True,
            shorten_from='right'
        )
        row.add_widget(name_label)

        # Список игроков (первые 3 + ...)
        players = template.get('players', [])
        players_text = ', '.join(players[:3])
        if len(players) > 3:
            players_text += f' … (+{len(players) - 3})'
        elif not players:
            players_text = '—'

        players_label = Label(
            text=players_text,
            font_size='12sp',
            color=(0.8, 0.8, 0.8, 1),
            size_hint_x=0.40,
            halign='left',
            text_size=(None, None),
            shorten=True,
            shorten_from='right'
        )
        row.add_widget(players_label)

        # Количество команд
        teams = template.get('teams', 0)
        teams_label = Label(
            text=str(teams) if teams > 0 else '—',
            font_size='13sp',
            color=(0.9, 0.9, 0.9, 1),
            size_hint_x=0.15,
            halign='center'
        )
        row.add_widget(teams_label)

        # Кнопка удаления (крестик)
        delete_btn = Button(
            text='✕',
            font_size='16sp',
            bold=True,
            color=(1, 0.3, 0.3, 1),
            background_color=(0.3, 0.1, 0.1, 0.6),
            size_hint_x=0.15
        )
        delete_btn.bind(on_press=lambda x, t=template: self._delete_template(t))
        row.add_widget(delete_btn)

        # Делаем строку кликабельной
        row.bind(on_touch_down=self._on_row_click)

        parent.add_widget(row)

    def _update_row_bg(self, instance, value):
        """Обновляет фон строки при изменении позиции или размера"""
        instance.canvas.before.clear()
        if hasattr(instance, 'selected') and instance.selected:
            color = (0.3, 0.5, 0.8, 0.6)
        else:
            color = (0.15, 0.15, 0.25, 0.5)
        with instance.canvas.before:
            Color(*color)
            Rectangle(pos=instance.pos, size=instance.size)

    def _on_row_click(self, instance, touch):
        """Обработчик клика по строке с шаблоном"""
        if not instance.collide_point(touch.x, touch.y):
            return

        # Снимаем выделение со всех строк
        for child in instance.parent.children:
            if hasattr(child, 'selected'):
                child.selected = False
                child.canvas.before.clear()
                with child.canvas.before:
                    Color(0.15, 0.15, 0.25, 0.5)
                    Rectangle(pos=child.pos, size=child.size)

        # Выделяем текущую строку
        instance.selected = True
        instance.canvas.before.clear()
        with instance.canvas.before:
            Color(0.3, 0.5, 0.8, 0.6)
            Rectangle(pos=instance.pos, size=instance.size)

        # Сохраняем выбранный шаблон
        self.selected_template = instance.template_data

        # Активируем кнопки
        self.edit_btn.disabled = False
        self.delete_btn.disabled = False
        self.select_btn.disabled = False

        return True

    def _on_open(self, instance):
        """Обновляет содержимое при открытии"""
        self._build_content()

    def _show_create_template(self, instance):
        """Показывает форму создания шаблона"""
        self._show_template_form(is_edit=False)

    def _show_edit_template(self, instance):
        """Показывает форму редактирования шаблона"""
        if hasattr(self, 'selected_template') and self.selected_template:
            self._show_template_form(is_edit=True, template=self.selected_template)

    def _show_template_form(self, is_edit=False, template=None):
        """Показывает форму для создания/редактирования шаблона"""

        # Создаем попап для формы
        form_popup = Popup(
            title='✏️ Редактирование шаблона' if is_edit else '➕ Создание шаблона',
            size_hint=(0.85, 0.75),
            auto_dismiss=True,
            separator_color=(0.5, 0.8, 1, 1),
            separator_height=2
        )

        # Контент формы
        form_content = BoxLayout(
            orientation='vertical',
            spacing=15,
            padding=[20, 20, 20, 20]
        )

        # Поле для названия
        name_layout = BoxLayout(orientation='vertical', size_hint_y=0.15, spacing=5)
        name_layout.add_widget(Label(
            text='📋 Название шаблона:',
            font_size='14sp',
            color=(0.9, 0.9, 0.9, 1),
            size_hint_y=0.3,
            halign='left'
        ))
        name_input = TextInput(
            text=template.get('name', '') if template else '',
            font_size='14sp',
            multiline=False,
            size_hint_y=0.7,
            background_color=(0.2, 0.2, 0.3, 1),
            foreground_color=(1, 1, 1, 1),
            cursor_color=(0.5, 0.8, 1, 1)
        )
        name_layout.add_widget(name_input)
        form_content.add_widget(name_layout)

        # Поле для списка игроков
        players_layout = BoxLayout(orientation='vertical', size_hint_y=0.50, spacing=5)
        players_layout.add_widget(Label(
            text='👥 Список игроков (каждый с новой строки):',
            font_size='14sp',
            color=(0.9, 0.9, 0.9, 1),
            size_hint_y=0.15,
            halign='left'
        ))

        players_text = ''
        if template and template.get('players'):
            players_text = '\n'.join(template.get('players', []))

        players_input = TextInput(
            text=players_text,
            font_size='13sp',
            multiline=True,
            size_hint_y=0.85,
            background_color=(0.2, 0.2, 0.3, 1),
            foreground_color=(1, 1, 1, 1),
            cursor_color=(0.5, 0.8, 1, 1)
        )
        players_layout.add_widget(players_input)
        form_content.add_widget(players_layout)

        # Поле для количества команд
        teams_layout = BoxLayout(orientation='vertical', size_hint_y=0.15, spacing=5)
        teams_layout.add_widget(Label(
            text='🏆 Количество команд (0 = без команд):',
            font_size='14sp',
            color=(0.9, 0.9, 0.9, 1),
            size_hint_y=0.3,
            halign='left'
        ))
        teams_input = TextInput(
            text=str(template.get('teams', 0)) if template else '0',
            font_size='14sp',
            multiline=False,
            size_hint_y=0.7,
            background_color=(0.2, 0.2, 0.3, 1),
            foreground_color=(1, 1, 1, 1),
            cursor_color=(0.5, 0.8, 1, 1),
            input_filter='int'
        )
        teams_layout.add_widget(teams_input)
        form_content.add_widget(teams_layout)

        # Кнопки управления
        buttons_layout = BoxLayout(
            size_hint_y=0.12,
            spacing=10,
            padding=[0, 5, 0, 0]
        )

        # Кнопка ОТМЕНА
        cancel_btn = Button(
            text='❌ ОТМЕНА',
            font_size='14sp',
            bold=True,
            background_color=(0.4, 0.4, 0.4, 1),
            color=(1, 1, 1, 1)
        )
        cancel_btn.bind(on_release=form_popup.dismiss)
        buttons_layout.add_widget(cancel_btn)

        # Кнопка СОХРАНИТЬ
        save_btn = Button(
            text='💾 СОХРАНИТЬ',
            font_size='14sp',
            bold=True,
            background_color=(0.2, 0.6, 0.2, 1),
            color=(1, 1, 1, 1)
        )

        def on_save(btn):
            name = name_input.text.strip()
            players = [p.strip() for p in players_input.text.split('\n') if p.strip()]
            teams_text = teams_input.text.strip()
            teams = int(teams_text) if teams_text and teams_text.isdigit() else 0

            if not name:
                print("⚠️ Введите название шаблона")
                self._show_message_in_popup(form_popup, "⚠️ Введите название шаблона")
                return

            if not players:
                print("⚠️ Добавьте хотя бы одного игрока")
                self._show_message_in_popup(form_popup, "⚠️ Добавьте хотя бы одного игрока")
                return

            # Проверяем, что количество команд не превышает количество игроков
            if teams > 0 and teams > len(players):
                self._show_message_in_popup(form_popup,
                                            f"⚠️ Команд ({teams}) не может быть больше игроков ({len(players)})")
                return

            # Создаем данные шаблона
            template_data = {
                'name': name,
                'players': players,
                'teams': teams
            }

            if is_edit and template:
                # Обновляем существующий шаблон
                success = self.template_manager.update_template(
                    template.get('id'),
                    name=name,
                    players=players,
                    teams=teams
                )
                if success:
                    print(f"✅ Шаблон '{name}' обновлён")
                else:
                    print(f"❌ Ошибка при обновлении шаблона")
            else:
                # Создаем новый шаблон
                template_data['colors'] = template.get('colors', []) if template else []
                success = self.template_manager.create_template(template_data)
                if success:
                    print(f"✅ Шаблон '{name}' создан")
                else:
                    print(f"❌ Ошибка при создании шаблона")

            # Закрываем форму и обновляем список
            form_popup.dismiss()
            self._build_content()
            self._refresh_selection_state()

        save_btn.bind(on_release=on_save)
        buttons_layout.add_widget(save_btn)

        form_content.add_widget(buttons_layout)

        form_popup.content = form_content
        form_popup.open()

    def _show_message_in_popup(self, popup, message):
        """Показывает сообщение в попапе"""
        msg_label = Label(
            text=message,
            font_size='14sp',
            color=(1, 0.5, 0.5, 1),
            size_hint=(1, 0.1),
            pos_hint={'x': 0, 'y': 0.9}
        )
        popup.content.add_widget(msg_label)
        Clock.schedule_once(lambda dt: popup.content.remove_widget(msg_label), 2.0)

    def _delete_selected_template(self, instance):
        """Удаляет выбранный шаблон"""
        if hasattr(self, 'selected_template') and self.selected_template:
            self._delete_template(self.selected_template)

    def _delete_template(self, template):
        """Удаляет шаблон"""
        template_name = template.get('name', 'Без названия')
        template_id = template.get('id')

        # Проверяем, что это не единственный шаблон
        templates = self.template_manager.get_templates()
        if len(templates) <= 1:
            print("❌ Нельзя удалить последний шаблон")
            self._show_message("Нельзя удалить последний шаблон")
            return

        # Подтверждение удаления
        confirm_popup = Popup(
            title='⚠️ Подтверждение удаления',
            size_hint=(0.6, 0.3),
            auto_dismiss=True,
            separator_color=(0.8, 0.2, 0.2, 1),
            separator_height=2
        )

        confirm_content = BoxLayout(
            orientation='vertical',
            spacing=15,
            padding=[20, 20, 20, 20]
        )

        confirm_content.add_widget(Label(
            text=f'Удалить шаблон "{template_name}"?',
            font_size='16sp',
            color=(1, 1, 1, 1),
            halign='center'
        ))

        buttons_box = BoxLayout(size_hint_y=0.4, spacing=10)

        no_btn = Button(
            text='❌ НЕТ',
            background_color=(0.4, 0.4, 0.4, 1),
            color=(1, 1, 1, 1)
        )
        no_btn.bind(on_release=confirm_popup.dismiss)
        buttons_box.add_widget(no_btn)

        yes_btn = Button(
            text='✅ ДА, УДАЛИТЬ',
            background_color=(0.8, 0.2, 0.2, 1),
            color=(1, 1, 1, 1)
        )

        def on_delete(btn):
            success = self.template_manager.delete_template(template_id)
            if success:
                print(f"🗑️ Шаблон '{template_name}' удален")
                if hasattr(self, 'selected_template'):
                    self.selected_template = None
                self.edit_btn.disabled = True
                self.delete_btn.disabled = True
                self.select_btn.disabled = True
                confirm_popup.dismiss()
                self._build_content()
            else:
                print(f"❌ Ошибка при удалении шаблона '{template_name}'")
                self._show_message(f"Ошибка при удалении шаблона")

        yes_btn.bind(on_release=on_delete)
        buttons_box.add_widget(yes_btn)

        confirm_content.add_widget(buttons_box)
        confirm_popup.content = confirm_content
        confirm_popup.open()

    def _select_selected_template(self, instance):
        """Выбирает текущий шаблон"""
        if hasattr(self, 'selected_template') and self.selected_template:
            self._select_template(self.selected_template)

    def _select_template(self, template):
        """Выбирает шаблон"""
        print(f"✅ Выбран шаблон: {template.get('name')}")

        # Получаем количество команд из шаблона
        teams = template.get('teams', 0)
        print(f"🏆 Количество команд в шаблоне: {teams}")

        # Сохраняем выбранный шаблон
        self.template_manager.save_selected_template(template.get('id'))

        # Вызываем callback с полными данными шаблона (включая teams)
        if self.callback:
            self.callback(template)

        # Закрываем попап
        self.dismiss()

    def _show_message(self, message):
        """Показывает временное сообщение"""
        msg_label = Label(
            text=message,
            font_size='16sp',
            color=(1, 0.5, 0.5, 1),
            size_hint=(1, 0.08),
            pos_hint={'x': 0, 'y': 0.9}
        )
        self.main_layout.add_widget(msg_label)
        # Удаляем сообщение через 2 секунды
        Clock.schedule_once(lambda dt: self.main_layout.remove_widget(msg_label), 2.0)

    def _refresh_selection_state(self):
        """Обновляет состояние кнопок после обновления списка"""
        if hasattr(self, 'selected_template'):
            self.selected_template = None
        self.edit_btn.disabled = True
        self.delete_btn.disabled = True
        self.select_btn.disabled = True