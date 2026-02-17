from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.properties import StringProperty, BooleanProperty
from kivy.app import App
from kivy.clock import Clock


class MLTextMixin:
    """Mixin для виджетов с поддержкой мультиязычности"""
    text_key = StringProperty('')
    auto_update = BooleanProperty(True)

    def __init__(self, **kwargs):
        # Извлекаем text_key из kwargs
        if 'text_key' in kwargs:
            self.text_key = kwargs.pop('text_key')
            print(f"🏷️ Создан виджет с ключом: {self.text_key}")

        super().__init__(**kwargs)

        # Обновляем текст при создании
        Clock.schedule_once(lambda dt: self.update_text(), 0)

    def on_text_key(self, instance, value):
        """Когда меняется ключ, обновляем текст"""
        print(f"🔄 Ключ изменен: {value}")
        self.update_text()

    def update_text(self, *args):
        """Обновляет текст из текущего языка"""
        if self.text_key and hasattr(self, 'text'):
            app = App.get_running_app()
            if app and hasattr(app, '_'):
                new_text = app._(self.text_key)
                old_text = getattr(self, 'text', '')

                if new_text != old_text:
                    print(f"📝 Обновляем текст: '{old_text}' -> '{new_text}' (ключ: {self.text_key})")
                    self.text = new_text

                    # Для RTL языков
                    if hasattr(app, 'lang') and app.lang.is_rtl():
                        if hasattr(self, 'halign'):
                            self.halign = 'right'
                    else:
                        if hasattr(self, 'halign') and self.halign == 'right':
                            self.halign = 'left'

    def on_parent(self, instance, value):
        """При добавлении в дерево виджетов, подписываемся на смену языка"""
        if value and self.auto_update:
            app = App.get_running_app()
            if app and hasattr(app, 'lang'):
                print(f"🔗 Виджет '{self.text_key}' подписался на смену языка")
                # Подписываемся на изменение свойства current_lang
                app.lang.bind(current_lang=self.update_text)
                # Также подписываемся на кастомное событие
                app.lang.bind(on_language_changed=self.update_text)
                self.update_text()


class MLLabel(MLTextMixin, Label):
    """Label с поддержкой мультиязычности"""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.bind(size=self.setter('text_size'))


class MLButton(MLTextMixin, Button):
    """Button с поддержкой мультиязычности"""
    pass