import math
import random
from kivy.animation import Animation
from kivy.uix.behaviors import ButtonBehavior
from kivy.uix.image import Image
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.widget import Widget
from kivy.uix.popup import Popup
from kivy.graphics import Color, Rectangle
from screens.base_game_screen import BaseGameScreen
from kivy.properties import NumericProperty
from kivy.graphics import Rotate
from kivy.graphics import Rotate, PushMatrix, PopMatrix

class RotatingImage(Image):
    """Image с поддержкой вращения вокруг центра"""
    angle = NumericProperty(0)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        # Инициализируем графические инструкции
        self._rotate = None
        self._setup_graphics()

        # Привязываем обновление центра вращения И угла!
        self.bind(
            pos=self._update_origin,
            size=self._update_origin,
            angle=self._update_angle  # Добавьте эту строку!
        )

    def _setup_graphics(self):
        """Настраиваем графические инструкции для вращения"""
        with self.canvas.before:
            PushMatrix()
            self._rotate = Rotate(angle=self.angle, origin=self.center)
        with self.canvas.after:
            PopMatrix()

    def _update_angle(self, instance, value):
        """Обновляет угол вращения"""
        if self._rotate:
            self._rotate.angle = value
            print(f"Angle updated: {value}")  # Для отладки

    def _update_origin(self, *args):
        """Обновляет центр вращения - теперь точно центр виджета"""
        if self._rotate:
            # Вычисляем абсолютный центр виджета
            center_x = self.x + self.width / 2
            center_y = self.y + self.height / 2
            self._rotate.origin = (center_x, center_y)
            print(f"Center updated: ({center_x}, {center_y})")

class ToggleButtonWithLabel(ButtonBehavior, FloatLayout):
    """Кнопка с изображением как фоном и текстом по центру"""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.size_hint = (1, 0.6)
        self.size = (350, 80)

        # Изображение как фон - растягиваем на всю кнопку
        self.bg_image = Image(
            source='',
            size_hint=(1, 1),  # Растягиваем на всю кнопку
            pos_hint={'x': 0, 'y': 0},
            allow_stretch=True,
            keep_ratio=False  # Отключаем сохранение пропорций для заполнения всей кнопки
        )

        # Текст по центру поверх изображения
        self.label = Label(
            text='',
            font_size='22sp',
            bold=True,
            color=(1, 1, 1, 1),
            size_hint=(1, 1),
            pos_hint={'center_x': 0.5, 'center_y': 0.5},
            halign='center',
            valign='middle'
        )
        self.label.bind(size=self.label.setter('text_size'))

        self.add_widget(self.bg_image)
        self.add_widget(self.label)

    @property
    def icon(self):
        """Для совместимости с существующим кодом"""
        return self.bg_image

    @icon.setter
    def icon(self, value):
        self.bg_image.source = value

class ImageButton(ButtonBehavior, Image):
    pass


class RouletteScreen(BaseGameScreen):
    """Экран рулетки - только колесо и запуск"""

    def __init__(self, game_manager=None, **kwargs):
        super().__init__(**kwargs)
        self.name = 'roulette'
        self.background_image = 'assets/backgrounds/roulette_bg.jpg'
        self.sound_file = 'assets/sounds/roulette_music.mp3'

        # Тип рулетки: 'european' (0-36) или 'american' (0, 00, 1-36)
        self.roulette_type = 'european'  # По умолчанию европейская

        # Колесо рулетки
        self.wheel = None
        self.is_spinning = False
        self.current_rotation = 0

        # Тип рулетки: 'european' (0-36) или 'american' (0, 00, 1-36)

        # Данные для разных типов рулеток
        self.roulette_data = {
            'european': {
                'button_image': 'assets/images/buttons/Roulette_switch_button.png',  # ДОБАВ
                'name': 'EUROPEAN ROULETTE',
                'button_text': 'SWITCH',  # Добавьте
                'button_color': (0.2, 0.4, 0.8, 1),  # Синий цвет - добавьте
                'numbers': [
                    '0', '32', '15', '19', '4', '21', '2', '25', '17', '34',
                    '6', '27', '13', '36', '11', '30', '8', '23', '10', '5',
                    '24', '16', '33', '1', '20', '14', '31', '9', '22', '18',
                    '29', '7', '28', '12', '35', '3', '26'
                ],
                'colors': {
                    '0': (0, 0.5, 0, 1),  # Зеленый
                    '32': (0.8, 0, 0, 1), '15': (0, 0, 0, 1), '19': (0.8, 0, 0, 1),
                    '4': (0, 0, 0, 1), '21': (0.8, 0, 0, 1), '2': (0, 0, 0, 1),
                    '25': (0.8, 0, 0, 1), '17': (0, 0, 0, 1), '34': (0.8, 0, 0, 1),
                    '6': (0, 0, 0, 1), '27': (0.8, 0, 0, 1), '13': (0, 0, 0, 1),
                    '36': (0.8, 0, 0, 1), '11': (0, 0, 0, 1), '30': (0.8, 0, 0, 1),
                    '8': (0, 0, 0, 1), '23': (0.8, 0, 0, 1), '10': (0, 0, 0, 1),
                    '5': (0.8, 0, 0, 1), '24': (0, 0, 0, 1), '16': (0.8, 0, 0, 1),
                    '33': (0, 0, 0, 1), '1': (0.8, 0, 0, 1), '20': (0, 0, 0, 1),
                    '14': (0.8, 0, 0, 1), '31': (0, 0, 0, 1), '9': (0.8, 0, 0, 1),
                    '22': (0, 0, 0, 1), '18': (0.8, 0, 0, 1), '29': (0, 0, 0, 1),
                    '7': (0.8, 0, 0, 1), '28': (0, 0, 0, 1), '12': (0.8, 0, 0, 1),
                    '35': (0, 0, 0, 1), '3': (0.8, 0, 0, 1), '26': (0, 0, 0, 1)
                }
            },
            'american': {
                'button_image': 'assets/images/buttons/Roulette_switch_button.png',  # ДОБАВЬТЕ
                'name': 'AMERICAN ROULETTE',
                'button_text': 'SWITCH',  # Добавьте
                'button_color': (0.8, 0.2, 0.2, 1),  # Красный цвет - добавьте
                'numbers': [
                    '0', '28', '9', '26', '30', '11', '7', '20', '32', '17',
                    '5', '22', '34', '15', '3', '24', '36', '13', '1', '00',
                    '27', '10', '25', '29', '12', '8', '19', '31', '18', '6',
                    '21', '33', '16', '4', '23', '35', '14', '2'
                ],
                'colors': {
                    '0': (0, 0.5, 0, 1),  # Зеленый
                    '00': (0, 0.5, 0, 1),  # Зеленый
                    '28': (0, 0, 0, 1), '9': (0.8, 0, 0, 1), '26': (0, 0, 0, 1),
                    '30': (0, 0, 0, 1), '11': (0.8, 0, 0, 1), '7': (0.8, 0, 0, 1),
                    '20': (0, 0, 0, 1), '32': (0.8, 0, 0, 1), '17': (0.8, 0, 0, 1),
                    '5': (0, 0, 0, 1), '22': (0.8, 0, 0, 1), '34': (0, 0, 0, 1),
                    '15': (0.8, 0, 0, 1), '3': (0, 0, 0, 1), '24': (0.8, 0, 0, 1),
                    '36': (0, 0, 0, 1), '13': (0.8, 0, 0, 1), '1': (0.8, 0, 0, 1),
                    '27': (0.8, 0, 0, 1), '10': (0, 0, 0, 1), '25': (0.8, 0, 0, 1),
                    '29': (0, 0, 0, 1), '12': (0, 0, 0, 1), '8': (0, 0, 0, 1),
                    '19': (0.8, 0, 0, 1), '31': (0, 0, 0, 1), '18': (0.8, 0, 0, 1),
                    '6': (0, 0, 0, 1), '21': (0.8, 0, 0, 1), '33': (0, 0, 0, 1),
                    '16': (0.8, 0, 0, 1), '4': (0, 0, 0, 1), '23': (0.8, 0, 0, 1),
                    '35': (0, 0, 0, 1), '14': (0.8, 0, 0, 1), '2': (0, 0, 0, 1)
                }
            }
        }

    def on_enter(self):
        """При входе на экран"""
        super().on_enter()
        self.show_wheel_view()

    def show_wheel_view(self):
        print("Method show_wheel_view called")
        """Показать вид с вращающимся колесом"""
        print(f"Экран {self.roulette_data[self.roulette_type]['name']}")
        self.clear_layout()

        # Кнопка-переключатель типа рулетки с надписью
        self.type_switch_button = ToggleButtonWithLabel(
            size_hint=(1, 1),
            size=(250, 60),
            pos_hint={'center_x': 0.5, 'center_y': 0.9}
        )

        # Устанавливаем изображение и текст
        data = self.roulette_data[self.roulette_type]
        self.type_switch_button.icon.source = data['button_image']
        self.type_switch_button.label.text = data['button_text']

        self.type_switch_button.bind(on_press=self.toggle_roulette_type)
        self.layout.add_widget(self.type_switch_button)

        # Заголовок с названием типа рулетки
        title_label = Label(
            text=self.roulette_data[self.roulette_type]['name'],
            font_size='24sp',
            bold=True,
            color=(1, 1, 1, 1),
            size_hint=(None, None),
            size=(400, 40),
            pos_hint={'center_x': 0.5, 'top': 1}
        )
        self.layout.add_widget(title_label)

        # Создаем контейнер для колеса
        wheel_container = FloatLayout(
            size_hint=(None, None),
            size=(500, 500),
            pos_hint={'center_x': 0.5, 'center_y': 0.6}
        )

        # Создаем колесо рулетки с учетом типа
        wheel_size = 450 if self.roulette_type == 'american' else 400
        wheel_source = 'assets/images/Roulette_wheel_00.png' if self.roulette_type == 'american' else 'assets/images/Roulette_wheel_0.png'

        self.wheel = RotatingImage(
            source=wheel_source,
            size_hint=(None, None),
            size=(wheel_size, wheel_size),
            pos_hint={'center_x': 0.5, 'center_y': 0.5}
        )

        # Если файл не найден, создаем простую рулетку
        if not self.wheel.source or 'not found' in str(self.wheel.source).lower():
            self.create_simple_wheel(wheel_container)
        else:
            wheel_container.add_widget(self.wheel)

        self.layout.add_widget(wheel_container)

        # Кнопка запуска рулетки (изображение белого шарика)
        spin_button = ImageButton(
            source='assets/images/buttons/Roulette_ball.png',
            size_hint=(None, None),
            size=(100, 100),
            pos_hint={'center_x': 0.5, 'y': 0.05},
            color=(1, 1, 1, 1)
        )
        spin_button.bind(on_press=self.spin_wheel)
        self.layout.add_widget(spin_button)

    def toggle_roulette_type(self, instance=None):
        """Переключить тип рулетки по нажатию кнопки"""
        print("Method toggle_roulette_type() called.")
        # Сначала меняем тип на противоположный
        new_type = 'american' if self.roulette_type == 'european' else 'european'
        self.roulette_type = new_type

        # Потом получаем данные для нового типа
        data = self.roulette_data[self.roulette_type]

        # Обновляем иконку и текст кнопки
        if hasattr(self, 'type_switch_button') and self.type_switch_button:
            self.type_switch_button.icon.source = data['button_image']
            self.type_switch_button.label.text = data['button_text']

        # Обновляем весь экран
        self.show_wheel_view()

    def switch_roulette_type(self, roulette_type):
        """Альтернативный метод для переключения типа (для совместимости)"""
        if self.roulette_type != roulette_type:
            self.roulette_type = roulette_type

            # Обновляем кнопку если она существует
            if hasattr(self, 'type_switch_button') and self.type_switch_button:
                data = self.roulette_data[self.roulette_type]
                self.type_switch_button.icon.source = data['button_image']
                self.type_switch_button.label.text = data['button_text']

            self.show_wheel_view()

    def return_to_menu(self, instance=None):
        """Вернуться в главное меню"""
        self.manager.current = 'menu'

    def spin_wheel(self, instance=None):
        """Запуск вращения колеса рулетки"""
        if self.is_spinning or not self.wheel:
            return

        print(f"🎰 Запускаю {self.roulette_type} рулетку...")
        print(f"Позиция колеса: {self.wheel.pos}, размер: {self.wheel.size}")
        print(f"Центр колеса: {self.wheel.center}")

        self.is_spinning = True

        # Убедимся, что угол сбрасывается
        current_angle = self.wheel.angle % 360

        # Добавляем случайное количество вращений
        additional_rotations = (360 * random.randint(3, 8)) + random.randint(0, 360)
        target_angle = current_angle + additional_rotations

        # Создаем анимацию
        anim = Animation(
            angle=target_angle,
            duration=random.uniform(3.0, 5.0),
            t='out_cubic'
        )

        # Привязываем обработчики
        anim.bind(on_complete=self._on_spin_complete)

        # Запускаем анимацию
        anim.start(self.wheel)

        # Обновляем позицию для отладки
        if hasattr(self.wheel, '_update_origin'):
            self.wheel._update_origin()

    def _on_spin_progress(self, animation, widget, progress):
        """Обновление вращения во время анимации"""
        if self.wheel and hasattr(self.wheel, 'canvas'):
            self.wheel.rotation = self.current_rotation
            self.wheel.canvas.ask_update()

    def _on_spin_complete(self, animation, widget):
        """Когда вращение завершено"""
        print(f"🎰 {self.roulette_data[self.roulette_type]['name']} остановилась!")
        self.is_spinning = False

        # Определяем выигрышный сектор
        winning_sector = self._get_winning_sector()

        # Показываем результат
        self._show_result(winning_sector)

    def _get_winning_sector(self):
        """Определяет выигрышный сектор"""
        data = self.roulette_data[self.roulette_type]
        winning_number = random.choice(data['numbers'])

        # Определяем цвет для отображения
        if winning_number in ['0', '00']:
            color_name = 'GREEN'
        elif data['colors'][winning_number] == (0.8, 0, 0, 1):
            color_name = 'RED'
        else:
            color_name = 'BLACK'

        return f'{winning_number} {color_name}'

    def _show_result(self, result):
        """Показывает результат рулетки с анимацией масштабирования"""
        # Создаем FloatLayout для фона и содержимого
        main_layout = FloatLayout()

        # Начальный масштаб для анимации
        main_layout.scale = 0.8
        main_layout.opacity = 0

        # Добавляем фон-изображение для попапа
        try:
            popup_bg = Image(
                source='assets/images/Out_image.png',
                allow_stretch=True,
                keep_ratio=True,
                size_hint=(1, 1),
                pos_hint={'x': 0, 'y': 0}
            )
            main_layout.add_widget(popup_bg)
        except Exception as e:
            print(f"Не удалось загрузить фоновое изображение: {e}")
            with main_layout.canvas.before:
                Color(0.1, 0.1, 0.2, 0.95)
                Rectangle(size=main_layout.size, pos=main_layout.pos)
            main_layout.bind(size=self._update_rect, pos=self._update_rect)

        # Разделяем результат на число и цвет
        parts = result.split()
        number = parts[0]
        color = parts[1] if len(parts) > 1 else ''

        # Цвет для отображения
        number_color = (0, 0.5, 0, 1) if color == 'GREEN' else \
            (0.8, 0, 0, 1) if color == 'RED' else \
                (0, 0, 0, 1)

        # Выигрышный номер (содержимое попапа)
        number_label = Label(
            text=number,
            font_size='96sp',  # Увеличил размер шрифта
            bold=True,
            color=number_color,
            size_hint=(None, None),
            size=(200, 200),
            pos_hint={'center_x': 0.5, 'center_y': 0.5}
        )
        main_layout.add_widget(number_label)

        # Функция для плавного закрытия попапа при нажатии
        def dismiss_popup_with_animation(instance):
            """Плавное закрытие попапа с анимацией"""
            # Анимация исчезновения с уменьшением масштаба
            anim_scale = Animation(
                scale=0.8,
                opacity=0,
                duration=0.3,
                t='out_cubic'
            )
            anim_scale.start(main_layout)

            # Анимация для текста
            anim_text = Animation(
                opacity=0,
                duration=0.3,
                t='out_cubic'
            )
            anim_text.start(number_label)

            # Закрываем попап после анимации
            from kivy.clock import Clock
            Clock.schedule_once(lambda dt: self.result_popup.dismiss(), 0.35)

        # Создаем прозрачную кнопку на весь попап для закрытия
        close_button = Button(
            text='',
            size_hint=(1, 1),
            background_color=(0, 0, 0, 0),  # Прозрачная
            background_normal=''
        )
        close_button.bind(on_press=dismiss_popup_with_animation)
        main_layout.add_widget(close_button)

        # Создаем попап
        self.result_popup = Popup(
            title='',
            content=main_layout,
            size_hint=(0.7, 0.7),  # Немного увеличил размер
            pos_hint={'center_x': 0.5, 'center_y': 0.5},
            separator_height=0,
            background='',
            background_color=(0, 0, 0, 0),
            auto_dismiss=False,
            opacity=0
        )

        # Функция для плавного открытия попапа
        def animate_popup_open():
            # Сначала делаем попап видимым
            self.result_popup.opacity = 1

            # Анимация для фона: увеличение масштаба + появление
            anim_bg = Animation(
                scale=1,
                opacity=1,
                duration=0.4,
                t='out_back'
            )
            anim_bg.start(main_layout)

            # Анимация для текста с задержкой для лучшего эффекта
            from kivy.clock import Clock
            number_label.opacity = 0
            number_label.scale = 1.2

            anim_text_scale = Animation(
                scale=1,
                duration=0.4,
                t='out_back'
            )

            anim_text_opacity = Animation(
                opacity=1,
                duration=0.4,
                t='out_cubic'
            )

            Clock.schedule_once(
                lambda dt: (
                    anim_text_scale.start(number_label),
                    anim_text_opacity.start(number_label)
                ),
                0.15
            )

        # Открываем попап и запускаем анимацию
        self.result_popup.open()
        animate_popup_open()

    def _update_rect(self, instance, value):
        """Обновляет размер прямоугольника фона"""
        if hasattr(instance, 'canvas'):
            instance.canvas.before.clear()
            with instance.canvas.before:
                Color(0.1, 0.1, 0.2, 0.95)
                Rectangle(pos=instance.pos, size=instance.size)

    def clear_layout(self):
        """Очистить layout"""
        for child in self.layout.children[:]:
            if child not in [self.bg_image, self.back_button]:
                self.layout.remove_widget(child)

    def create_simple_wheel(self, container):
        """Создает простую рулетку если нет картинки"""
        from kivy.graphics import Color, Ellipse, Line, Rotate

        class SimpleWheel(Widget):
            angle = NumericProperty(0)

            def __init__(self, roulette_type='european', **kwargs):
                super().__init__(**kwargs)
                self.roulette_type = roulette_type
                self.size = (450, 450) if roulette_type == 'american' else (400, 400)
                self.pos_hint = {'center_x': 0.5, 'center_y': 0.5}

                # Установка графических инструкций для вращения
                with self.canvas.before:
                    PushMatrix()
                    self.rotate_instruction = Rotate(angle=self.angle, origin=self.center)
                with self.canvas.after:
                    PopMatrix()

                # Привязка обновлений
                self.bind(pos=self.update_origin, size=self.update_origin, angle=self.update_angle)

                self.draw_wheel()

            def update_origin(self, *args):
                """Обновить центр вращения"""
                self.rotate_instruction.origin = (self.center_x, self.center_y)

            def update_angle(self, *args):
                """Обновить угол вращения"""
                self.rotate_instruction.angle = self.angle

            def draw_wheel(self):
                self.canvas.clear()
                center_x, center_y = self.width / 2, self.height / 2

                with self.canvas:
                    # Основной круг
                    Color(0.7, 0.1, 0.1, 1)
                    Ellipse(pos=(0, 0), size=self.size)

                    # Внутренний круг
                    Color(0.1, 0.1, 0.1, 1)
                    inner_size = self.size[0] - 100, self.size[1] - 100
                    inner_pos = 50, 50
                    Ellipse(pos=inner_pos, size=inner_size)

                    # Сектора
                    Color(1, 1, 1, 1)
                    radius = min(self.size) / 2 - 50

                    # Разное количество секторов для разных типов
                    sectors = 38 if self.roulette_type == 'american' else 37

                    for i in range(sectors):
                        angle = i * (360 / sectors)
                        rad = angle * 3.14159 / 180
                        x1 = center_x + radius * 0.9 * math.cos(rad)
                        y1 = center_y + radius * 0.9 * math.sin(rad)
                        x2 = center_x + radius * 0.7 * math.cos(rad)
                        y2 = center_y + radius * 0.7 * math.sin(rad)
                        Line(points=[x1, y1, x2, y2], width=2)

                    # Центральный индикатор
                    Color(0, 0.5, 0, 1)
                    indicator_size = 20, 20
                    indicator_pos = center_x - 10, center_y - 10
                    Ellipse(pos=indicator_pos, size=indicator_size)

        self.wheel = SimpleWheel(self.roulette_type)
        container.add_widget(self.wheel)

    def on_touch_down(self, touch):
        """Обработка касаний"""
        if self.wheel and hasattr(self.wheel, 'collide_point') and self.wheel.collide_point(*touch.pos):
            if not self.is_spinning:
                self.spin_wheel()
            return True
        return super().on_touch_down(touch)

    def on_leave(self):
        """При выходе с экрана"""
        super().on_leave()
        Animation.cancel_all(self)