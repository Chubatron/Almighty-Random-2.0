import math
import random
from kivy.animation import Animation
from kivy.core.audio import SoundLoader
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
from kivy.graphics import Rotate, PushMatrix, PopMatrix
from kivy.clock import Clock


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
        # Убираем size_hint, чтобы кнопка не растягивалась на весь экран
        self.size_hint = (None, None)  # Отключаем автоматическое растягивание
        self.size = (150, 50)  # Размер кнопки 100x20

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
            font_size='20sp',  # Уменьшаем размер шрифта для маленькой кнопки
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
        self.ball_launched = False  # Флаг, был ли запущен шарик

        # Кнопка шарика для вращения
        self.spin_button = None

        # Звуки
        self.wheel_spin_sound = None  # Звук вращения колеса
        self.ball_roll_sound = None  # Звук качения шарика

        # Таймеры
        self.spin_timer = None
        self.ball_timer = None

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

        # Кнопка-переключатель типа рулетки с надписью
        self.type_switch_button = ToggleButtonWithLabel(
            size_hint=(1, 1),
            size=(250, 60),
            pos_hint={'center_x': 0.5, 'center_y': 0.9}
        )

    def on_enter(self):
        """При входе на экран"""
        super().on_enter()
        self.show_wheel_view()

    def show_wheel_view(self):
        print("Method show_wheel_view called")
        """Показать вид с вращающимся колесом"""
        print(f"Экран {self.roulette_data[self.roulette_type]['name']}")

        # Сбрасываем флаги состояния
        self.is_spinning = False
        self.ball_launched = False

        # Отменяем все таймеры
        if self.spin_timer:
            self.spin_timer.cancel()
            self.spin_timer = None
        if self.ball_timer:
            self.ball_timer.cancel()
            self.ball_timer = None

        self.clear_layout()
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
        self.spin_button = ImageButton(  # Сохраняем ссылку в атрибуте
            source='assets/images/buttons/Roulette_ball.png',
            size_hint=(None, None),
            size=(100, 100),
            pos_hint={'center_x': 0.5, 'y': 0.05},
            color=(1, 1, 1, 1)
        )
        self.spin_button.bind(on_press=self.spin_wheel)
        self.layout.add_widget(self.spin_button)

    def play_wheel_spin_sound(self):
        """Воспроизводит звук вращения колеса (один раз)"""
        try:
            if not self.wheel_spin_sound:
                self.wheel_spin_sound = SoundLoader.load('assets/sounds/Roulette/roulette_drum_revolution.ogg')
                if not self.wheel_spin_sound:
                    print("Не удалось загрузить звук: assets/sounds/Roulette/roulette_drum_revolution.ogg")
                    return

            if self.wheel_spin_sound:
                if self.wheel_spin_sound.state == 'play':
                    self.wheel_spin_sound.stop()
                self.wheel_spin_sound.loop = False  # ИЗМЕНЕНО: было True, стало False
                self.wheel_spin_sound.play()
        except Exception as e:
            print(f"Ошибка при воспроизведении звука вращения колеса: {e}")

    def play_ball_roll_sound(self):
        """Воспроизводит звук качения шарика и возвращает его длительность"""
        try:
            if not self.ball_roll_sound:
                self.ball_roll_sound = SoundLoader.load('assets/sounds/Roulette/ball_throw_american.ogg')
                if not self.ball_roll_sound:
                    print("Не удалось загрузить звук: assets/sounds/Roulette/ball_throw_american.ogg")
                    return 0

            if self.ball_roll_sound:
                if self.ball_roll_sound.state == 'play':
                    self.ball_roll_sound.stop()
                self.ball_roll_sound.loop = False
                self.ball_roll_sound.play()

                # Возвращаем длительность звука в секундах
                # Если длина неизвестна, используем стандартные 15 секунд
                sound_length = self.ball_roll_sound.length
                if sound_length:
                    return sound_length
                else:
                    return 15.0  # Значение по умолчанию
        except Exception as e:
            print(f"Ошибка при воспроизведении звука качения шарика: {e}")
            return 15.0

    def toggle_roulette_type(self, instance=None):
        """Переключить тип рулетки по нажатию кнопки"""
        print("Method toggle_roulette_type() called.")

        # ПРОВЕРЯЕМ, НЕ ВРАЩАЕТСЯ ЛИ КОЛЕСО
        if self.is_spinning:
            print("Колесо вращается, переключение типа запрещено")
            # Можно показать всплывающее сообщение
            return

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

    def set_switch_button_state(self, enabled):
        """Включить/выключить кнопку переключения типа рулетки"""
        if hasattr(self, 'type_switch_button') and self.type_switch_button:
            self.type_switch_button.disabled = not enabled
            # Опционально: визуальное обозначение неактивной кнопки
            if enabled:
                self.type_switch_button.opacity = 1.0
            else:
                self.type_switch_button.opacity = 0.5

    def spin_wheel(self, instance=None):
        """Запуск вращения колеса рулетки (без шарика)"""
        if self.is_spinning or not self.wheel:
            return

        print(f"🎰 Запускаю вращение колеса {self.roulette_type} рулетки...")

        # ОТКЛЮЧАЕМ КНОПКУ SWITCH
        self.set_switch_button_state(False)

        # Сбрасываем флаг запуска шарика
        self.ball_launched = False

        # Останавливаем все звуки
        self.stop_all_sounds()

        # Запускаем звук вращения колеса
        self.play_wheel_spin_sound()

        self.is_spinning = True

        # Нормализуем текущий угол
        current_angle = self.wheel.angle % 360
        self.wheel.angle = current_angle

        # Добавляем случайное количество вращений
        full_rotations = random.randint(8, 12)  # 8-12 полных оборотов
        additional_angle = random.randint(0, 360)
        target_angle = current_angle + 360 * full_rotations + additional_angle

        print(f"Начальный угол: {current_angle}°, целевой: {target_angle}°")

        # Создаем анимацию
        anim = Animation(
            angle=target_angle,
            duration=16.0,  # 16 секунд вращения
            t='out_quad'  # Плавное замедление в конце
        )

        # Привязываем обработчики
        anim.bind(on_complete=self._on_wheel_spin_complete)

        # Запускаем анимацию
        anim.start(self.wheel)

        # Сохраняем анимацию для возможной остановки
        self.current_animation = anim

        # Запускаем таймер на случай, если анимация не завершится
        self.spin_timer = Clock.schedule_once(self._force_stop_wheel, 18.0)

    def _on_spin_progress(self, animation, widget, progress):
        """Обновление вращения во время анимации"""
        if self.wheel and hasattr(self.wheel, 'canvas'):
            self.wheel.rotation = self.current_rotation
            self.wheel.canvas.ask_update()

    def launch_ball(self, instance=None):
        """Запуск шарика в рулетку"""
        if not self.is_spinning or self.ball_launched:
            # Если колесо не вращается, сначала запускаем его
            if not self.is_spinning:
                self.spin_wheel()

            # Если шарик уже запущен, игнорируем
            if self.ball_launched:
                return

        print("🎯 Запускаю шарик в рулетку...")

        # Скрываем кнопку шарика с анимацией
        if self.spin_button:
            anim_hide = Animation(
                opacity=0,
                duration=0.3,
                t='out_cubic'
            )
            anim_hide.bind(on_complete=lambda *args: setattr(self.spin_button, 'disabled', True))
            anim_hide.start(self.spin_button)

        # Запускаем звук качения шарика и получаем его длительность
        sound_duration = self.play_ball_roll_sound()

        self.ball_launched = True

        # Отменяем предыдущий таймер, если был
        if self.spin_timer:
            self.spin_timer.cancel()
            self.spin_timer = None

        # Запускаем таймер на длительность звука для показа результата
        # Добавляем небольшую задержку для плавности
        result_delay = sound_duration + 0.5
        self.ball_timer = Clock.schedule_once(self._show_ball_result, result_delay)

        print(f"⏱ Результат будет показан через {result_delay} секунд")

    def _on_wheel_spin_complete(self, animation, widget):
        """Когда вращение колеса завершено само (без шарика) - просто останавливаем"""
        print("🛑 Колесо остановилось самостоятельно, шарик не запускался")

        # Отменяем таймер
        if self.spin_timer:
            self.spin_timer.cancel()
            self.spin_timer = None

        # Если шарик не запущен - останавливаем все звуки
        if not self.ball_launched:
            self.stop_all_sounds()

        # ВКЛЮЧАЕМ КНОПКУ SWITCH
        self.set_switch_button_state(True)

        # Сбрасываем флаги
        self.is_spinning = False

    def _force_stop_wheel(self, dt):
        """Принудительная остановка колеса через таймер - без результата"""
        print("⏰ Таймер: принудительная остановка колеса")

        if self.is_spinning:
            # Останавливаем анимацию
            if hasattr(self, 'current_animation') and self.current_animation:
                self.current_animation.stop(self.wheel)

            # Если шарик не запущен - останавливаем все звуки
            if not self.ball_launched:
                self.stop_all_sounds()

            # ВКЛЮЧАЕМ КНОПКУ SWITCH
            self.set_switch_button_state(True)

            # Сбрасываем флаги
            self.is_spinning = False

            # НЕ показываем результат, просто останавливаемся

        self.spin_timer = None

    def _show_ball_result(self, dt):
        """Показывает результат после запуска шарика"""
        print("🎯 Шарик остановился, показываю результат")

        # Останавливаем звук шарика
        if self.ball_roll_sound:
            self.ball_roll_sound.stop()

        # Останавливаем звук колеса на всякий случай
        if self.wheel_spin_sound:
            self.wheel_spin_sound.stop()
            self.wheel_spin_sound.loop = False

        # Останавливаем анимацию колеса
        if hasattr(self, 'current_animation') and self.current_animation:
            self.current_animation.stop(self.wheel)

        # Сбрасываем флаги
        self.is_spinning = False
        self.ball_launched = False
        self.ball_timer = None

        # ВКЛЮЧАЕМ КНОПКУ SWITCH
        self.set_switch_button_state(True)

        # Получаем случайный результат
        winning_sector = self._get_winning_sector()

        # Показываем результат
        self._show_result(winning_sector)

    def _show_spin_button(self):
        """Показать кнопку шарика после завершения вращения"""
        if self.spin_button:
            # Сначала включаем кнопку
            self.spin_button.disabled = False

            # Плавно показываем кнопку
            anim_show = Animation(
                opacity=1,
                duration=0.5,
                t='out_cubic'
            )
            anim_show.start(self.spin_button)

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

            # Показываем кнопку шарика после закрытия попапа
            Clock.schedule_once(lambda dt: self._show_spin_button(), 0.4)

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

    @staticmethod
    def _update_rect(instance, value):
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
        # Проверяем касание колеса
        if self.wheel and hasattr(self.wheel, 'collide_point') and self.wheel.collide_point(*touch.pos):
            if not self.is_spinning:
                # Если колесо не вращается - запускаем вращение колеса
                self.spin_wheel()
            # Если колесо уже вращается, ничего не делаем при касании колеса
            return True

        # Проверяем касание кнопки шарика
        if self.spin_button and self.spin_button.collide_point(*touch.pos):
            if self.is_spinning and not self.ball_launched:
                # Если колесо вращается и шарик еще не запущен - запускаем шарик
                self.launch_ball()
            elif not self.is_spinning:
                # Если колесо не вращается - сначала запускаем колесо, потом шарик
                self.spin_wheel()
                # Запускаем шарик через небольшую задержку, чтобы колесо начало вращаться
                Clock.schedule_once(lambda dt: self.launch_ball(), 0.5)
            return True

        return super().on_touch_down(touch)

    def on_leave(self):
        """При выходе с экрана"""
        # Останавливаем все звуки
        self.stop_all_sounds()

        # Отменяем все анимации
        Animation.cancel_all(self)

        # Отменяем все таймеры
        if self.spin_timer:
            self.spin_timer.cancel()
            self.spin_timer = None

        if self.ball_timer:
            self.ball_timer.cancel()
            self.ball_timer = None

        # СБРАСЫВАЕМ ВСЕ ФЛАГИ СОСТОЯНИЯ!
        self.is_spinning = False
        self.ball_launched = False

        # ВКЛЮЧАЕМ КНОПКУ SWITCH (на случай если она была отключена)
        self.set_switch_button_state(True)

        # Сбрасываем угол колеса для единообразия (опционально)
        if self.wheel:
            self.wheel.angle = 0

        # Восстанавливаем кнопку шарика
        if self.spin_button:
            self.spin_button.opacity = 1
            self.spin_button.disabled = False

        # Вызываем родительский метод
        super().on_leave()

    def stop_all_sounds(self):
        """Останавливает все звуки"""
        if self.wheel_spin_sound:
            self.wheel_spin_sound.stop()
            self.wheel_spin_sound.loop = False

        # Добавьте эту секцию!
        if self.ball_roll_sound:
            self.ball_roll_sound.stop()
            self.ball_roll_sound.loop = False

    def stop_wheel_sound(self):
        """Останавливает только звук вращения колеса"""
        if self.wheel_spin_sound:
            self.wheel_spin_sound.stop()
            self.wheel_spin_sound.loop = False