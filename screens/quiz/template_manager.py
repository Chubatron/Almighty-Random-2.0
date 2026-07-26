import json
import os
import uuid


class TemplateManager:
    """Управляет сохраненными шаблонами сегментов"""

    def __init__(self):
        self.templates = []
        self.templates_dir = 'assets/templates'
        self.templates_file = os.path.join(self.templates_dir, 'templates.json')
        self.selected_template_file = os.path.join(self.templates_dir, 'selected_template.json')
        self._ensure_directory()
        self.load_templates()

    def _ensure_directory(self):
        """Создает директорию для шаблонов если её нет"""
        if not os.path.exists(self.templates_dir):
            os.makedirs(self.templates_dir)

    def load_templates(self):
        """Загружает шаблоны из файла"""
        if os.path.exists(self.templates_file):
            try:
                with open(self.templates_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.templates = data.get('templates', [])
            except:
                self.templates = []
        else:
            # Создаем шаблоны по умолчанию
            self.templates = [
                {
                    'id': 'default_1',
                    'name': 'Цифры 1-8',
                    'sectors': ['1', '2', '3', '4', '5', '6', '7', '8'],
                    'colors': [
                        [1, 0.2, 0.2], [0.2, 0.8, 0.2], [0.2, 0.4, 1],
                        [1, 0.8, 0.2], [1, 0.4, 0.8], [0.2, 0.8, 0.8],
                        [0.8, 0.4, 1], [1, 0.6, 0.2]
                    ]
                },
                {
                    'id': 'default_2',
                    'name': 'Цвета радуги',
                    'sectors': ['Красный', 'Оранжевый', 'Желтый', 'Зеленый', 'Голубой', 'Синий', 'Фиолетовый'],
                    'colors': [
                        [1, 0, 0], [1, 0.5, 0], [1, 1, 0], [0, 1, 0],
                        [0, 0.5, 1], [0, 0, 1], [0.5, 0, 1]
                    ]
                },
                {
                    'id': 'default_3',
                    'name': 'Вопросы',
                    'sectors': ['Вопрос 1', 'Вопрос 2', 'Вопрос 3', 'Вопрос 4', 'Вопрос 5', 'Вопрос 6'],
                    'colors': [
                        [1, 0.2, 0.2], [0.2, 0.8, 0.2], [0.2, 0.4, 1],
                        [1, 0.8, 0.2], [1, 0.4, 0.8], [0.2, 0.8, 0.8]
                    ]
                }
            ]
            self.save_templates()

    def reload_templates(self):
        """Перезагружает шаблоны из файла (обновляет кэш)"""
        if os.path.exists(self.templates_file):
            try:
                with open(self.templates_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.templates = data.get('templates', [])
                return True
            except Exception as e:
                print(f"❌ Ошибка при перезагрузке шаблонов: {e}")
                return False
        return False

    def save_templates(self):
        """Сохраняет шаблоны в файл"""
        try:
            with open(self.templates_file, 'w', encoding='utf-8') as f:
                json.dump({'templates': self.templates}, f, ensure_ascii=False, indent=2)
            return True
        except:
            return False

    def get_templates(self):
        """Возвращает список всех шаблонов"""
        return self.templates

    def get_template(self, template_id):
        """Возвращает шаблон по ID"""
        for template in self.templates:
            if template.get('id') == template_id:
                return template
        return None

    def create_template(self, template_data):
        """
        Создает новый шаблон из словаря с данными
        template_data: dict с полями name, categories
        Возвращает True если успешно, False если шаблон уже существует
        """
        try:
            # Проверяем, существует ли шаблон с таким именем
            for template in self.templates:
                if template.get('name') == template_data.get('name'):
                    print(f"❌ Шаблон с именем '{template_data.get('name')}' уже существует")
                    return False

            # Создаем новый шаблон с UUID
            new_template = {
                'id': str(uuid.uuid4()),
                'name': template_data.get('name', 'Unnamed'),
                'sectors': template_data.get('categories', []),  # Используем categories как sectors
                'colors': []  # Пустой список цветов
            }

            # Добавляем в список
            self.templates.append(new_template)
            self.save_templates()
            print(f"✅ Шаблон '{new_template['name']}' создан с ID: {new_template['id']}")
            return True

        except Exception as e:
            print(f"❌ Ошибка при создании шаблона: {e}")
            return False

    def add_template(self, name, sectors, colors):
        """Добавляет новый шаблон (старый метод для совместимости)"""
        template = {
            'id': str(uuid.uuid4()),
            'name': name,
            'sectors': sectors,
            'colors': colors
        }
        self.templates.append(template)
        self.save_templates()
        return template

    def update_template(self, template_id, name=None, sectors=None, colors=None):
        """Обновляет существующий шаблон"""
        for template in self.templates:
            if template.get('id') == template_id:
                if name is not None:
                    template['name'] = name
                if sectors is not None:
                    template['sectors'] = sectors
                if colors is not None:
                    template['colors'] = colors
                self.save_templates()
                return True
        return False

    def delete_template(self, template_id):
        """Удаляет шаблон"""
        for i, template in enumerate(self.templates):
            if template.get('id') == template_id:
                # Не даем удалить последний шаблон
                if len(self.templates) <= 1:
                    return False
                del self.templates[i]
                self.save_templates()
                return True
        return False

    def get_template_names(self):
        """Возвращает список имен шаблонов"""
        return [t.get('name', 'Без названия') for t in self.templates]

    # === МЕТОДЫ ДЛЯ СОХРАНЕНИЯ ВЫБРАННОГО ШАБЛОНА ===

    def save_selected_template(self, template_id):
        """Сохраняет ID выбранного шаблона"""
        try:
            with open(self.selected_template_file, 'w', encoding='utf-8') as f:
                json.dump({'selected_template_id': template_id}, f, ensure_ascii=False, indent=2)
            return True
        except:
            return False

    def load_selected_template(self):
        """Загружает ID выбранного шаблона"""
        if os.path.exists(self.selected_template_file):
            try:
                with open(self.selected_template_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    template_id = data.get('selected_template_id')
                    if template_id:
                        print(f"🔍 [load_selected_template] Загружен ID: {template_id}")
                        return self.get_template(template_id)
            except Exception as e:
                print(f"❌ Ошибка при загрузке выбранного шаблона: {e}")
                pass
        # Если нет сохраненного шаблона, возвращаем первый по умолчанию
        if self.templates:
            print(f"🔍 [load_selected_template] Нет сохраненного шаблона, возвращаем первый: {self.templates[0].get('name')}")
            return self.templates[0]
        return None

    def get_selected_template_id(self):
        """Возвращает ID выбранного шаблона"""
        if os.path.exists(self.selected_template_file):
            try:
                with open(self.selected_template_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    template_id = data.get('selected_template_id')
                    print(f"🔍 [get_selected_template_id] ID: {template_id}")
                    return template_id
            except Exception as e:
                print(f"❌ Ошибка при загрузке ID выбранного шаблона: {e}")
                return None
        return None

    def clear_selected_template(self):
        """Очищает сохраненный шаблон"""
        if os.path.exists(self.selected_template_file):
            try:
                os.remove(self.selected_template_file)
                return True
            except:
                pass
        return False