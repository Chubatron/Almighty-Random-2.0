# screens/rsp_screen.py
from kivy.animation import Animation
from kivy.uix.label import Label
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.behaviors import ButtonBehavior
from kivy.uix.image import Image
from kivy.uix.button import Button
from kivy.properties import NumericProperty, StringProperty
from kivy.clock import Clock
import math
import random
import os

from screens.game_screen import GameScreen


class RotatingImage(Image):
    """Image с поддержкой вращения вокруг центра (как в рулетке)"""
    angle = NumericProperty(0)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.allow_stretch = True
        self.keep_ratio = True

        # Инициализируем графические инструкции
        self._rotate = None
        self._setup_graphics()

        # Привязываем обновление центра вращения и угла
        self.bind(
            pos=self._update_origin,
            size=self._update_origin,
            angle=self._update_angle
        )

    def _setup_graphics(self):
        """Настраиваем графические инструкции для вращения"""
        from kivy.graphics import Rotate, PushMatrix, PopMatrix

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
        """Обновляет центр вращения"""
        if self._rotate:
            center_x = self.x + self.width / 2
            center_y = self.y + self.height / 2
            self._rotate.origin = (center_x, center_y)


class ToggleButtonWithLabel(ButtonBehavior, FloatLayout):
    """Кнопка с изображением как фоном и текстом по центру"""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.size_hint = (None, None)
        self.size = (150, 50)

        self.bg_image = Image(
            source='',
            size_hint=(1, 1),
            pos_hint={'x': 0, 'y': 0},
            allow_stretch=True,
            keep_ratio=False
        )

        self.label = Label(
            text='',
            font_size='20sp',
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
        return self.bg_image

    @icon.setter
    def icon(self, value):
        self.bg_image.source = value


class SpinButton(ButtonBehavior, Image):
    """Кнопка SPIN с кастомными изображениями для разных состояний"""

    is_active = NumericProperty(1)

    def __init__(self, **kwargs):
        passed_size = kwargs.get('size', None)

        super().__init__(**kwargs)

        self.green_button_path = 'assets/images/buttons/spin_button_green.png'
        self.red_button_path = 'assets/images/buttons/spin_button_red.png'

        self.size_hint = (None, None)

        if passed_size:
            self.size = passed_size
        else:
            self.size = (80, 80)

        self.allow_stretch = True
        self.update_button_image()
        self.bind(is_active=self.update_button_image)

    def update_button_image(self, *args):
        """Обновляет изображение в зависимости от состояния is_active"""
        if self.is_active:
            if os.path.exists(self.green_button_path):
                self.source = self.green_button_path
                self.color = (1, 1, 1, 1)
            else:
                print(f"⚠️ Файл {self.green_button_path} не найден!")
                self.source = ''
                self.color = (0, 1, 0, 1)
        else:
            if os.path.exists(self.red_button_path):
                self.source = self.red_button_path
                self.color = (1, 1, 1, 1)
            else:
                print(f"⚠️ Файл {self.red_button_path} не найден!")
                self.source = ''
                self.color = (1, 0, 0, 1)


class RSPScreen(GameScreen):
    """
    Экран игры "Камень, ножницы, бумага"
    """

    player_score = NumericProperty(0)
    computer_score = NumericProperty(0)
    result_text = StringProperty("Нажмите SPIN!")

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.background_image = 'assets/backgrounds/rsp_bg.jpg'
        self.sprite_sheet_path = ''

        self.game_type = 'classic'

        self.type_switch_button = None
        self.spin_button = None
        self.title_label = None

        # Спиннеры - теперь RotatingImage как в рулетке
        self.spinner_image_3 = None
        self.spinner_image_5 = None
        self.current_spinner = None

        self.is_spinning = False
        self.center_x = 0
        self.center_y = 0
        self.radius = 0
        self.winner_image = None

        # Для анимации вращения (как в рулетке)
        self.current_animation = None
        self.spin_timer = None

        # Для звуков
        self.spin_sound = None
        self.result_sounds = {}

        # Соответствие углов и элементов
        self.classic_angles = {
            0: 'scissors',  # 0° - ножницы
            120: 'paper',  # 120° - бумага
            240: 'rock'  # 240° - камень
        }

        self.extended_angles = {
            0: 'spock',  # 0° - спок
            72: 'scissors',  # 72° - ножницы
            144: 'lizard',  # 144° - ящерица
            216: 'rock',  # 216° - камень
            288: 'paper'  # 288° - бумага
        }

    def on_enter(self):
        """При входе на экран"""
        # Сначала вызываем родительский метод для управления музыкой и фоном
        super().on_enter()

        self.is_spinning = False
        self.winner_image = None

        # Очищаем layout (кроме фона и кнопки назад)
        self.clear_ui()

        # Показываем интерфейс игры
        self.show_ui()

        # Загружаем звуки результатов
        self.load_result_sounds()

        # Сбрасываем спиннер в стартовое положение
        self.reset_spinner()

        self.layout.bind(size=self.update_layout, pos=self.update_layout)

        Clock.schedule_once(lambda dt: self.update_layout(), 0.1)

    def on_leave(self):
        """При выходе с экрана"""
        # Останавливаем все звуки
        self.stop_all_sounds()

        # Останавливаем анимацию вращения (как в рулетке)
        self.stop_spinner_animation()

        # Отменяем таймер
        if self.spin_timer:
            self.spin_timer.cancel()
            self.spin_timer = None

        if hasattr(self, 'spin_button') and self.spin_button:
            self.spin_button.unbind(on_press=self.start_spin)

        if hasattr(self, 'type_switch_button') and self.type_switch_button:
            self.type_switch_button.unbind(on_press=self.toggle_game_type)

        if hasattr(self, 'layout'):
            self.layout.unbind(size=self.update_layout, pos=self.update_layout)

        # Очищаем виджеты (но не вызываем clear_widgets, так как это сделает родитель)
        self.spin_button = None
        self.title_label = None
        self.type_switch_button = None
        self.spinner_image_3 = None
        self.spinner_image_5 = None
        self.current_spinner = None
        self.winner_image = None

        # Вызываем родительский метод для управления музыкой
        super().on_leave()

    def stop_all_sounds(self):
        """Останавливает все звуки"""
        # Останавливаем звук спиннера
        if self.spin_sound:
            try:
                if self.spin_sound.state == 'play':
                    self.spin_sound.stop()
            except:
                pass  # Игнорируем ошибки при закрытии
            self.spin_sound = None

        # Останавливаем все звуки результатов
        for sound in self.result_sounds.values():
            try:
                if sound.state == 'play':
                    sound.stop()
            except:
                pass  # Игнорируем ошибки при закрытии

    def stop_spinner_animation(self):
        """Останавливает анимацию спиннера и возвращает его в исходное состояние"""
        # Останавливаем текущую анимацию
        Animation.cancel_all(self)

        # Сбрасываем флаг вращения
        self.is_spinning = False

        # Возвращаем спиннер в стартовое положение (0 градусов)
        if self.current_spinner:
            self.current_spinner.angle = 0

        # Возвращаем кнопку в зеленое состояние и включаем
        if self.spin_button:
            self.spin_button.is_active = 1
            self.spin_button.disabled = False

    def set_switch_button_state(self, enabled):
        """Включить/выключить кнопку переключения типа игры"""
        if hasattr(self, 'type_switch_button') and self.type_switch_button:
            self.type_switch_button.disabled = not enabled
            # Визуальное обозначение неактивной кнопки
            if enabled:
                self.type_switch_button.opacity = 1.0
            else:
                self.type_switch_button.opacity = 0.5

    def reset_spinner(self):
        """Сбрасывает спиннер в стартовое положение"""
        # Останавливаем все звуки
        self.stop_all_sounds()

        # Останавливаем анимацию
        self.stop_spinner_animation()

        # Сбрасываем угол для всех спиннеров
        if self.spinner_image_3:
            self.spinner_image_3.angle = 0
        if self.spinner_image_5:
            self.spinner_image_5.angle = 0

        print("🔄 Spinner reset to start position")

    def go_to_menu(self):
        """Переопределяем метод для возврата в меню с остановкой всех процессов"""
        # Останавливаем все звуки и анимации перед уходом
        self.stop_all_sounds()
        self.stop_spinner_animation()

        # Вызываем родительский метод для перехода в меню
        super().go_to_menu()

    def apply_current_game_type(self):
        """Применяет текущий тип игры при входе на экран"""
        if self.title_label:
            self.title_label.text = 'CLASSIC RSP' if self.game_type == 'classic' else 'EXTENDED RSP'

        # Скрываем оба спиннера и сбрасываем угол
        if self.spinner_image_3:
            self.spinner_image_3.opacity = 0
            self.spinner_image_3.angle = 0
        if self.spinner_image_5:
            self.spinner_image_5.opacity = 0
            self.spinner_image_5.angle = 0

        # Показываем нужный спиннер
        if self.game_type == 'classic':
            if self.spinner_image_3:
                self.spinner_image_3.opacity = 1
                self.current_spinner = self.spinner_image_3
            print("Classic mode: showing spinner_3")
        else:
            if self.spinner_image_5:
                self.spinner_image_5.opacity = 1
                self.current_spinner = self.spinner_image_5
            print("Extended mode: showing spinner_5")

        # Пересоздаём кнопку с правильным размером
        self.recreate_spin_button()

        print(f"Applied game type: {self.game_type}")

    def update_layout(self, *args):
        """Обновляет параметры layout при изменении размера"""
        self.center_x = self.layout.width / 2
        self.center_y = self.layout.height / 2

        min_dimension = min(self.layout.width, self.layout.height)
        self.radius = min_dimension * 0.3

        # Разные размеры для разных спиннеров
        spinner_size_3 = min_dimension * 1.1  # Для 3 лучей
        spinner_size_5 = min_dimension * 1.0  # Для 5 лучей (увеличен)

        if self.spinner_image_3:
            self.spinner_image_3.size = (spinner_size_3, spinner_size_3)
            self.spinner_image_3.center = (self.center_x, self.center_y)

        if self.spinner_image_5:
            self.spinner_image_5.size = (spinner_size_5, spinner_size_5)
            self.spinner_image_5.center = (self.center_x, self.center_y)

        if self.spin_button:
            self.spin_button.center = (self.center_x, self.center_y)

        # Обновляем позицию back_button при изменении layout
        # (но не меняем её, если она уже установлена через pos_hint)

    def setup_background(self):
        """Настраивает фон"""
        if self.bg_image:
            self.layout.remove_widget(self.bg_image)

        from kivy.uix.image import Image
        self.bg_image = Image(
            source=self.background_image,
            allow_stretch=True,
            keep_ratio=False
        )
        self.layout.add_widget(self.bg_image)

    def show_ui(self):
        """Показать интерфейс с кнопкой переключения"""
        # Не вызываем clear_ui здесь, так как мы уже очистили в on_enter

        self.type_switch_button = ToggleButtonWithLabel(
            size_hint=(None, None),
            size=(150, 50),
            pos_hint={'center_x': 0.5, 'top': 0.95}
        )
        self.type_switch_button.icon.source = 'assets/images/buttons/Roulette_switch_button.png'
        self.type_switch_button.label.text = 'SWITCH'
        self.type_switch_button.bind(on_press=self.toggle_game_type)
        self.layout.add_widget(self.type_switch_button)

        self.title_label = Label(
            text='',
            font_size='24sp',
            bold=True,
            color=(1, 1, 1, 1),
            size_hint=(None, None),
            size=(400, 40),
            pos_hint={'center_x': 0.5, 'top': 1}
        )
        self.layout.add_widget(self.title_label)

        # СОЗДАЁМ ТОЛЬКО СПИННЕРЫ (теперь RotatingImage)
        self.create_spinner_images()

        # СОЗДАЁМ КНОПКУ
        self.create_spin_button()

        self.update_layout()
        self.apply_current_game_type()

    def create_spin_button(self):
        """Создаёт кнопку SPIN с размером в зависимости от режима"""
        button_size = (610, 610) if self.game_type == 'classic' else (580, 580)

        self.spin_button = SpinButton(
            is_active=1,
            size=button_size
        )
        self.spin_button.bind(on_press=self.start_spin)
        self.layout.add_widget(self.spin_button)

    def recreate_spin_button(self):
        """Пересоздаёт кнопку SPIN с новым размером"""
        if self.spin_button:
            self.spin_button.unbind(on_press=self.start_spin)
            self.layout.remove_widget(self.spin_button)
            self.spin_button = None

        self.create_spin_button()

        # Обновляем позицию новой кнопки
        if hasattr(self, 'center_x') and hasattr(self, 'center_y'):
            self.spin_button.center = (self.center_x, self.center_y)

    def create_spinner_images(self):
        """Создает изображения спиннеров для 3 и 5 лучей (теперь RotatingImage)"""
        if os.path.exists('assets/images/rsp/spinner_3.png'):
            self.spinner_image_3 = RotatingImage(
                source='assets/images/rsp/spinner_3.png',
                size_hint=(None, None),
                allow_stretch=True,
                keep_ratio=True,
                opacity=0,
                angle=0
            )
            self.layout.add_widget(self.spinner_image_3)
            print("Created spinner_3 image")
        else:
            print("⚠️ Файл spinner_3.png не найден")

        if os.path.exists('assets/images/rsp/spinner_5.png'):
            self.spinner_image_5 = RotatingImage(
                source='assets/images/rsp/spinner_5.png',
                size_hint=(None, None),
                allow_stretch=True,
                keep_ratio=True,
                opacity=0,
                angle=0
            )
            self.layout.add_widget(self.spinner_image_5)
            print("Created spinner_5 image")
        else:
            print("⚠️ Файл spinner_5.png не найден")

    def load_result_sounds(self):
        """Загружает звуки для каждого результата"""
        sound_files = {
            'rock': 'assets/sounds/rsp/stone.ogg',
            'paper': 'assets/sounds/rsp/paper.ogg',
            'scissors': 'assets/sounds/rsp/scissors.ogg',
            'lizard': 'assets/sounds/rsp/lizard.ogg',
            'spock': 'assets/sounds/rsp/spock.ogg'
        }

        from kivy.core.audio import SoundLoader

        for key, path in sound_files.items():
            if os.path.exists(path):
                sound = SoundLoader.load(path)
                if sound:
                    sound.volume = 0.8  # Громкость для звуков результатов
                    self.result_sounds[key] = sound
                    print(f"✅ Loaded sound: {path}")
                else:
                    print(f"⚠️ Failed to load sound: {path}")
            else:
                print(f"⚠️ Sound file not found: {path}")

    def play_result_sound(self, result):
        """Воспроизводит звук для выпавшего результата"""
        if result in self.result_sounds:
            sound = self.result_sounds[result]
            # Останавливаем звук спиннера, если он еще играет
            if self.spin_sound and self.spin_sound.state == 'play':
                self.spin_sound.stop()
                self.spin_sound = None

            # Воспроизводим звук результата
            sound.play()
            print(f"🔊 Playing result sound: {result}")
        else:
            print(f"⚠️ No sound loaded for result: {result}")

    def start_spin(self, instance):
        """Запускает вращение спиннера (против часовой стрелки)"""
        if self.is_spinning or not self.current_spinner:
            return

        print("🎡 Spin button pressed - starting rotation (counter-clockwise)")

        # ОТКЛЮЧАЕМ КНОПКУ SWITCH
        self.set_switch_button_state(False)

        # Воспроизводим звук вращения спиннера
        self.play_spin_sound()

        self.is_spinning = True
        self.result_text = "ВРАЩЕНИЕ..."

        # Меняем кнопку на красную и отключаем
        self.spin_button.is_active = 0
        self.spin_button.disabled = True

        # Нормализуем текущий угол
        current_angle = self.current_spinner.angle % 360
        self.current_spinner.angle = current_angle

        # Определяем допустимые углы в зависимости от режима
        if self.game_type == 'classic':
            # Для classic: ножницы (0°), бумага (120°), камень (240°)
            valid_angles = [0, 120, 240]
            print(f"Classic mode: stopping at angles: {valid_angles}")
        else:
            # Для extended: спок (0°), ножницы (72°), ящерица (144°), камень (216°), бумага (288°)
            valid_angles = [0, 72, 144, 216, 288]
            print(f"Extended mode: stopping at angles: {valid_angles}")

        # Выбираем случайный целевой угол из допустимых
        target_base_angle = random.choice(valid_angles)
        print(f"Selected target base angle: {target_base_angle}°")

        # Добавляем случайное количество полных оборотов (вращение против часовой стрелки)
        full_rotations = random.randint(16, 24)  # 16-24 полных оборотов

        # Для вращения против часовой стрелки используем отрицательный угол
        # Целевой угол будет меньше текущего
        target_angle = target_base_angle - 360 * full_rotations

        # Корректируем, чтобы анимация шла в правильном направлении (против часовой стрелки)
        # Если текущий угол меньше целевого, отнимаем ещё один оборот
        if current_angle < target_base_angle:
            target_angle -= 360

        print(f"Начальный угол: {current_angle}°, целевой базовый: {target_base_angle}°, финальный: {target_angle}°")

        # Создаем анимацию с вращением против часовой стрелки
        anim = Animation(
            angle=target_angle,
            duration=14.0,  # 14 секунд вращения
            t='out_quad'  # Плавное замедление в конце
        )

        # Привязываем обработчики
        anim.bind(on_complete=self._on_spin_complete)

        # Запускаем анимацию
        anim.start(self.current_spinner)

        # Сохраняем анимацию для возможной остановки
        self.current_animation = anim

        # Запускаем таймер на случай, если анимация не завершится
        self.spin_timer = Clock.schedule_once(self._force_stop_spin, 16.0)  # 16 секунд (запас 2 секунды)

    def _on_spin_complete(self, animation, widget):
        """Когда вращение завершено (как в рулетке)"""
        print("🛑 Спиннер остановился")

        # Проверяем, не закрывается ли приложение
        if not hasattr(self, 'layout') or not self.layout:
            print("⚠️ Layout уже уничтожен, останавливаем обработку")
            return

        # Отменяем таймер
        if self.spin_timer:
            self.spin_timer.cancel()
            self.spin_timer = None

        # Проверяем, существует ли еще виджет
        if not widget or widget not in self.layout.children:
            print("⚠️ Widget уже уничтожен, останавливаем обработку")
            return

        # Нормализуем угол (приводим к положительному значению 0-360)
        normalized_angle = widget.angle % 360
        if normalized_angle < 0:
            normalized_angle += 360

        # Определяем шаг в зависимости от режима
        if self.game_type == 'classic':
            valid_angles = [0, 120, 240]
        else:
            valid_angles = [0, 72, 144, 216, 288]

        # Находим ближайший допустимый угол
        closest_angle = min(valid_angles, key=lambda x: min(abs(x - normalized_angle), abs(x + 360 - normalized_angle)))

        print(f"Корректировка угла: {normalized_angle}° -> {closest_angle}°")
        widget.angle = closest_angle

        print(f"Финальный угол: {widget.angle}°")

        # Завершаем вращение
        self._finish_spin()

    def _force_stop_spin(self, dt):
        """Принудительная остановка через таймер (как в рулетке)"""
        print("⏰ Таймер: принудительная остановка спиннера")

        # Проверяем, не закрывается ли приложение
        if not hasattr(self, 'layout') or not self.layout:
            print("⚠️ Layout уже уничтожен, останавливаем обработку")
            return

        if self.is_spinning and self.current_animation:
            self.current_animation.stop(self.current_spinner)

            # При принудительной остановке тоже корректируем угол
            normalized_angle = self.current_spinner.angle % 360
            if normalized_angle < 0:
                normalized_angle += 360

            if self.game_type == 'classic':
                valid_angles = [0, 120, 240]
            else:
                valid_angles = [0, 72, 144, 216, 288]

            closest_angle = min(valid_angles,
                                key=lambda x: min(abs(x - normalized_angle), abs(x + 360 - normalized_angle)))

            self.current_spinner.angle = closest_angle
            print(f"Принудительная остановка на угле: {closest_angle}°")

            self._finish_spin()

        self.spin_timer = None

    def _finish_spin(self):
        """Завершение вращения с показом результата"""
        self.is_spinning = False

        # ВКЛЮЧАЕМ КНОПКУ SWITCH
        self.set_switch_button_state(True)

        # Проверяем, существует ли еще spin_button
        if self.spin_button:
            # Возвращаем кнопку в зелёный цвет и включаем
            self.spin_button.is_active = 1
            self.spin_button.disabled = False

        # Проверяем, существует ли current_spinner
        if not self.current_spinner:
            print("⚠️ current_spinner is None, cannot determine result")
            return

        # Определяем результат по углу остановки
        current_angle = self.current_spinner.angle % 360
        print(f"Определение результата по углу: {current_angle}°")

        if self.game_type == 'classic':
            # Для 3 элементов: 0° -> ножницы, 120° -> бумага, 240° -> камень
            result = self.classic_angles.get(current_angle, 'scissors')
        else:
            # Для 5 элементов: 0° -> спок, 72° -> ножницы, 144° -> ящерица,
            # 216° -> камень, 288° -> бумага
            result = self.extended_angles.get(current_angle, 'spock')

        print(f"Результат по углу: {result}")
        self.show_result(result)

        # Воспроизводим звук результата
        self.play_result_sound(result)

    def show_result(self, result):
        """Показывает результат вращения"""
        if result == 'rock':
            result_name = '🪨 КАМЕНЬ'
        elif result == 'paper':
            result_name = '📄 БУМАГА'
        elif result == 'scissors':
            result_name = '✂️ НОЖНИЦЫ'
        elif result == 'lizard':
            result_name = '🦎 ЯЩЕРИЦА'
        elif result == 'spock':
            result_name = '🖖 СПОК'
        else:
            result_name = ''

        self.result_text = f"ВЫПАЛО: {result_name}"
        print(f"Result: {result_name}")

    def toggle_game_type(self, instance=None):
        """Переключение типа игры"""
        if self.is_spinning:
            print("Нельзя переключить режим во время вращения!")
            return

        print(f"\n=== SWITCHING GAME TYPE FROM {self.game_type} ===")

        # Останавливаем анимацию если была
        Animation.cancel_all(self)
        if self.spin_timer:
            self.spin_timer.cancel()
            self.spin_timer = None

        if self.game_type == 'classic':
            self.game_type = 'extended'
            if self.title_label:
                self.title_label.text = 'EXTENDED RSP'
        else:
            self.game_type = 'classic'
            if self.title_label:
                self.title_label.text = 'CLASSIC RSP'

        self.apply_current_game_type()
        print(f"Game type switched to: {self.game_type}")

    def clear_ui(self):
        """Очищает все виджеты интерфейса кроме фона и кнопки назад"""
        if not hasattr(self, 'layout') or not self.layout:
            return

        # Сохраняем ссылку на кнопку назад
        back_button = self.back_button

        for child in self.layout.children[:]:
            # Удаляем все, кроме фона и кнопки назад
            if child != self.bg_image and child != back_button:
                self.layout.remove_widget(child)

        self.spin_button = None
        self.title_label = None
        self.type_switch_button = None
        self.spinner_image_3 = None
        self.spinner_image_5 = None
        self.current_spinner = None
        self.winner_image = None

    def play_spin_sound(self):
        """Воспроизводит звук вращения спиннера"""
        from kivy.core.audio import SoundLoader

        sound_path = 'assets/sounds/rsp/spinner_14.ogg'

        if os.path.exists(sound_path):
            # Загружаем звук и СОХРАНЯЕМ ссылку
            self.spin_sound = SoundLoader.load(sound_path)
            if self.spin_sound:
                self.spin_sound.volume = 0.7
                self.spin_sound.play()
                print(f"🎵 Playing spin sound: {sound_path}")
            else:
                print(f"⚠️ Failed to load spin sound: {sound_path}")
        else:
            print(f"⚠️ Spin sound file not found: {sound_path}")