import json
import os
from kivy.event import EventDispatcher
from kivy.properties import StringProperty
from kivy.storage.jsonstore import JsonStore


class LanguageManager(EventDispatcher):
    current_lang = StringProperty('ru')

    # Регистрируем событие
    __events__ = ('on_language_changed',)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.translations = {}
        self.store = JsonStore('language_preferences.json')

        # Загружаем сохраненный язык или используем русский
        if self.store.exists('language'):
            saved_lang = self.store.get('language')['code']
            print(f"📚 Загружен сохраненный язык: {saved_lang}")
        else:
            saved_lang = 'ru'
            print("📚 Язык не сохранен, используем русский по умолчанию")

        self.load_language(saved_lang)

    def load_language(self, lang_code):
        """Загружает файл перевода для указанного языка"""
        print(f"🔄 Загружаем язык: {lang_code}")
        self.current_lang = lang_code
        file_path = os.path.join('locales', f'{lang_code}.json')

        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                self.translations = json.load(f)

            self.store.put('language', code=lang_code)
            print(f"✅ Язык загружен: {lang_code}, найдено ключей: {len(self.translations)}")
            print(f"📋 Пример: select_item = {self.translations.get('select_item', 'НЕ НАЙДЕНО')}")

            # Принудительно вызываем событие обновления
            self.dispatch('on_language_changed')
            return True

        except FileNotFoundError:
            print(f"❌ Файл перевода для {lang_code} не найден: {file_path}")
            if lang_code != 'ru':
                return self.load_language('ru')
            return False
        except json.JSONDecodeError as e:
            print(f"❌ Ошибка в JSON файле {lang_code}: {e}")
            return False

    def on_language_changed(self, *args):
        """Событие, которое вызывается при смене языка"""
        print("🔔 Событие on_language_changed вызвано")
        pass

    def _(self, key):
        """Получить перевод по ключу"""
        translated = self.translations.get(key, key)
        if key not in self.translations:
            print(f"⚠️ Ключ не найден: '{key}'")
        return translated

    def get_available_languages(self):
        """Возвращает список доступных языков"""
        languages = []
        locales_path = 'locales'

        if not os.path.exists(locales_path):
            print(f"❌ Папка {locales_path} не найдена")
            return languages

        for file in os.listdir(locales_path):
            if file.endswith('.json'):
                lang_code = file.replace('.json', '')

                lang_names = {
                    'en': 'English',
                    'ru': 'Русский',
                    'zh': '中文',
                    'hi': 'हिन्दी',
                    'es': 'Español',
                    'ar': 'العربية',
                    'uk': 'Українська',
                }

                name = lang_names.get(lang_code, lang_code)
                languages.append({'code': lang_code, 'name': name})

        languages.sort(key=lambda x: x['name'])
        print(f"🌐 Доступные языки: {languages}")
        return languages

    def is_rtl(self, lang_code=None):
        """Проверяет, является ли язык правосторонним (RTL)"""
        if lang_code is None:
            lang_code = self.current_lang
        rtl_languages = ['ar']
        return lang_code in rtl_languages