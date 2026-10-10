import json
import os
import uuid


class DrawTemplateManager:
    """Управляет сохраненными шаблонами для экрана жеребьёвки (Машина Гальтона)"""

    def __init__(self):
        self.templates = []
        self.templates_dir = 'assets/templates'
        self.templates_file = os.path.join(self.templates_dir, 'templates_draw.json')
        self.selected_template_file = os.path.join(self.templates_dir, 'selected_template_draw.json')
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
                print(f"✅ Загружено {len(self.templates)} шаблонов для жеребьёвки")
                return True
            except Exception as e:
                print(f"❌ Ошибка загрузки шаблонов для жеребьёвки: {e}")
                self.templates = []
                return False
        else:
            # Создаем шаблоны по умолчанию
            print("📋 Файл шаблонов для жеребьёвки не найден, создаю стандартные")
            self._create_default_templates()
            return True

    def _create_default_templates(self):
        """Создает шаблоны по умолчанию для жеребьёвки"""
        self.templates = [
            {
                'id': 'draw_default_1',
                'name': 'Команды A-E',
                'players': ['Команда A', 'Команда B', 'Команда C', 'Команда D', 'Команда E'],
                'teams': 5,
                'colors': [
                    [1, 0, 0, 1],  # Красный
                    [0, 0, 1, 1],  # Синий
                    [0, 1, 0, 1],  # Зеленый
                    [1, 0.5, 0, 1],  # Оранжевый
                    [0.5, 0, 1, 1]  # Фиолетовый
                ]
            },
            {
                'id': 'draw_default_2',
                'name': 'Игроки 1-8',
                'players': ['Игрок 1', 'Игрок 2', 'Игрок 3', 'Игрок 4',
                            'Игрок 5', 'Игрок 6', 'Игрок 7', 'Игрок 8'],
                'teams': 0,
                'colors': [
                    [1, 0, 0, 1], [0, 0, 1, 1], [0, 1, 0, 1],
                    [1, 0.5, 0, 1], [0.5, 0, 1, 1], [1, 0, 1, 1],
                    [0, 1, 1, 1], [1, 1, 0, 1]
                ]
            },
            {
                'id': 'draw_default_3',
                'name': 'Цвета радуги',
                'players': ['Красный', 'Оранжевый', 'Желтый', 'Зеленый',
                            'Голубой', 'Синий', 'Фиолетовый'],
                'teams': 0,
                'colors': [
                    [1, 0, 0, 1], [1, 0.5, 0, 1], [1, 1, 0, 1],
                    [0, 1, 0, 1], [0, 0.5, 1, 1], [0, 0, 1, 1], [0.5, 0, 1, 1]
                ]
            },
            {
                'id': 'draw_default_4',
                'name': 'Страны',
                'players': ['Россия', 'США', 'Китай', 'Индия',
                            'Бразилия', 'Австралия', 'Египет', 'Франция'],
                'teams': 0,
                'colors': [
                    [0.2, 0.4, 0.8, 1], [0.8, 0.2, 0.2, 1], [0.8, 0.2, 0.8, 1],
                    [1, 0.6, 0.2, 1], [0.2, 0.8, 0.4, 1], [0.8, 0.8, 0.2, 1],
                    [0.2, 0.6, 0.8, 1], [0.8, 0.4, 0.6, 1]
                ]
            },
            {
                'id': 'draw_default_5',
                'name': 'Животные',
                'players': ['Лев', 'Тигр', 'Медведь', 'Волк',
                            'Лиса', 'Заяц', 'Сова', 'Орел'],
                'teams': 0,
                'colors': [
                    [0.8, 0.6, 0.2, 1], [0.8, 0.4, 0.1, 1], [0.4, 0.2, 0.1, 1],
                    [0.6, 0.6, 0.6, 1], [0.8, 0.4, 0.2, 1], [0.7, 0.7, 0.7, 1],
                    [0.4, 0.3, 0.2, 1], [0.3, 0.3, 0.3, 1]
                ]
            },
            {
                'id': 'draw_default_6',
                'name': 'Фрукты',
                'players': ['Яблоко', 'Банан', 'Апельсин', 'Груша',
                            'Виноград', 'Киви', 'Манго', 'Ананас'],
                'teams': 0,
                'colors': [
                    [0.8, 0.2, 0.2, 1], [1, 0.8, 0.2, 1], [1, 0.5, 0, 1],
                    [0.6, 0.8, 0.2, 1], [0.4, 0.2, 0.6, 1], [0.4, 0.7, 0.2, 1],
                    [1, 0.6, 0.2, 1], [0.8, 0.8, 0.2, 1]
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
                print(f"✅ Шаблоны для жеребьёвки перезагружены: {len(self.templates)}")
                return True
            except Exception as e:
                print(f"❌ Ошибка при перезагрузке шаблонов для жеребьёвки: {e}")
                return False
        return False

    def save_templates(self):
        """Сохраняет шаблоны в файл"""
        try:
            with open(self.templates_file, 'w', encoding='utf-8') as f:
                json.dump({'templates': self.templates}, f, ensure_ascii=False, indent=2)
            print(f"✅ Шаблоны для жеребьёвки сохранены в {self.templates_file}")
            return True
        except Exception as e:
            print(f"❌ Ошибка сохранения шаблонов для жеребьёвки: {e}")
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
        template_data: dict с полями name, players, teams (опционально), colors (опционально)
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
                'name': template_data.get('name', 'Новый шаблон'),
                'players': template_data.get('players', []),
                'teams': template_data.get('teams', 0),
                'colors': template_data.get('colors', [])
            }

            self.templates.append(new_template)
            self.save_templates()
            print(f"✅ Шаблон для жеребьёвки '{new_template['name']}' создан с ID: {new_template['id']}")
            return True

        except Exception as e:
            print(f"❌ Ошибка при создании шаблона для жеребьёвки: {e}")
            return False

    def add_template(self, name, players, colors, teams=0):
        """Добавляет новый шаблон (старый метод для совместимости)"""
        template = {
            'id': str(uuid.uuid4()),
            'name': name,
            'players': players,
            'teams': teams,
            'colors': colors
        }
        self.templates.append(template)
        self.save_templates()
        return template

    def update_template(self, template_id, name=None, players=None, colors=None, teams=None):
        """Обновляет существующий шаблон"""
        for template in self.templates:
            if template.get('id') == template_id:
                if name is not None:
                    template['name'] = name
                if players is not None:
                    template['players'] = players
                if colors is not None:
                    template['colors'] = colors
                if teams is not None:
                    template['teams'] = teams
                self.save_templates()
                return True
        return False

    def delete_template(self, template_id):
        """Удаляет шаблон"""
        for i, template in enumerate(self.templates):
            if template.get('id') == template_id:
                if len(self.templates) <= 1:
                    print("❌ Нельзя удалить последний шаблон")
                    return False
                del self.templates[i]
                self.save_templates()
                print(f"✅ Шаблон удален: {template_id}")
                return True
        return False

    def get_template_names(self):
        """Возвращает список имен шаблонов"""
        return [t.get('name', 'Без названия') for t in self.templates]

    def get_players_from_template(self, template_id):
        """Возвращает список игроков из шаблона"""
        template = self.get_template(template_id)
        if template:
            return template.get('players', [])
        return []

    def get_colors_from_template(self, template_id):
        """Возвращает список цветов из шаблона"""
        template = self.get_template(template_id)
        if template:
            return template.get('colors', [])
        return []

    def get_teams_from_template(self, template_id):
        """Возвращает количество команд из шаблона"""
        template = self.get_template(template_id)
        if template:
            return template.get('teams', 0)
        return 0

    # === МЕТОДЫ ДЛЯ СОХРАНЕНИЯ ВЫБРАННОГО ШАБЛОНА ===

    def save_selected_template(self, template_id):
        """Сохраняет ID выбранного шаблона"""
        try:
            with open(self.selected_template_file, 'w', encoding='utf-8') as f:
                json.dump({'selected_template_id': template_id}, f, ensure_ascii=False, indent=2)
            print(f"✅ Выбранный шаблон для жеребьёвки сохранен: {template_id}")
            return True
        except Exception as e:
            print(f"❌ Ошибка сохранения выбранного шаблона для жеребьёвки: {e}")
            return False

    def load_selected_template(self):
        """Загружает выбранный шаблон"""
        if os.path.exists(self.selected_template_file):
            try:
                with open(self.selected_template_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    template_id = data.get('selected_template_id')
                    if template_id:
                        template = self.get_template(template_id)
                        if template:
                            print(f"🔍 [load_selected_template] Загружен шаблон: {template.get('name')}")
                            return template
                        else:
                            print(f"⚠️ Шаблон с ID {template_id} не найден")
            except Exception as e:
                print(f"❌ Ошибка при загрузке выбранного шаблона для жеребьёвки: {e}")

        # Если нет сохраненного шаблона, возвращаем первый по умолчанию
        if self.templates:
            print(
                f"🔍 [load_selected_template] Нет сохраненного шаблона, возвращаем первый: {self.templates[0].get('name')}")
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
                print(f"❌ Ошибка при загрузке ID выбранного шаблона для жеребьёвки: {e}")
                return None
        return None

    def clear_selected_template(self):
        """Очищает сохраненный шаблон"""
        if os.path.exists(self.selected_template_file):
            try:
                os.remove(self.selected_template_file)
                print("🗑️ Выбранный шаблон для жеребьёвки очищен")
                return True
            except Exception as e:
                print(f"❌ Ошибка при очистке выбранного шаблона для жеребьёвки: {e}")
                pass
        return False