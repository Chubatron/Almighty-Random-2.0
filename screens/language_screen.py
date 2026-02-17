from kivy.uix.screenmanager import Screen
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.button import Button
from kivy.uix.scrollview import ScrollView
from kivy.uix.gridlayout import GridLayout
from kivy.app import App
from multilanguage_widgets import MLLabel


class LanguageScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        layout = FloatLayout()

        # Заголовок
        title = MLLabel(
            text_key='language',
            font_size='32sp',
            size_hint=(None, None),
            size=(400, 50),
            pos_hint={'center_x': 0.5, 'top': 0.95},
            color=(1, 1, 1, 1)
        )
        layout.add_widget(title)

        # Область прокрутки
        scroll = ScrollView(
            size_hint=(0.9, 0.7),
            pos_hint={'center_x': 0.5, 'center_y': 0.5}
        )

        grid = GridLayout(
            cols=1,
            spacing=10,
            size_hint_y=None,
            padding=20
        )
        grid.bind(minimum_height=grid.setter('height'))

        # Получаем список языков
        app = App.get_running_app()
        languages = app.lang.get_available_languages()
        print(f"📋 Загружено языков для отображения: {len(languages)}")

        for lang in languages:
            btn = Button(
                text=lang['name'],
                size_hint_y=None,
                height=60,
                background_normal='',
                background_color=(0.3, 0.5, 0.8, 1),
                color=(1, 1, 1, 1)
            )
            btn.lang_code = lang['code']
            btn.bind(on_press=self.change_language)
            grid.add_widget(btn)

        scroll.add_widget(grid)
        layout.add_widget(scroll)

        # Кнопка назад
        back_btn = Button(
            text='← Назад',
            size_hint=(0.3, 0.1),
            pos_hint={'x': 0.05, 'y': 0.05},
            background_normal='',
            background_color=(0.8, 0.2, 0.2, 1)
        )
        back_btn.bind(on_press=self.go_back)
        layout.add_widget(back_btn)

        self.add_widget(layout)

    def change_language(self, instance):
        """Смена языка"""
        app = App.get_running_app()
        print(f"🎯 Выбран язык: {instance.lang_code}")
        app.lang.load_language(instance.lang_code)

        # Принудительно обновляем все тексты на текущем экране
        self.force_update_all_texts()

        self.go_back(instance)

    def force_update_all_texts(self):
        """Принудительно обновляет все тексты на экране"""
        print("🔄 Принудительное обновление всех текстов")
        app = App.get_running_app()

        # Проходим по всем экранам и обновляем виджеты
        for screen in app.sm.screens:
            self.update_widgets_recursive(screen)

    def update_widgets_recursive(self, widget):
        """Рекурсивно обновляет все ML виджеты"""
        if hasattr(widget, 'update_text'):
            widget.update_text()

        if hasattr(widget, 'children'):
            for child in widget.children:
                self.update_widgets_recursive(child)

    def go_back(self, instance):
        self.manager.current = 'menu'