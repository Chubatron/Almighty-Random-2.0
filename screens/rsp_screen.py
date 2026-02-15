# screens/rsp_screen.py
from kivy.uix.label import Label
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.behaviors import ButtonBehavior
from kivy.uix.image import Image
from kivy.properties import NumericProperty, StringProperty
from kivy.animation import Animation
from kivy.clock import Clock
import math
import random
import os

from screens.game_screen import GameScreen


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
    """Кнопка SPIN с изображением"""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Проверяем существование файла
        spin_button_path = 'assets/images/buttons/spin_button.png'
        if os.path.exists(spin_button_path):
            self.source = spin_button_path
        else:
            # Если файл не найден, создаем кнопку без изображения
            self.source = ''
            self.color = (0.3, 0.6, 0.9, 1)  # Синий цвет
        self.size_hint = (None, None)
        self.size = (80, 80)
        self.allow_stretch = True


class RSPScreen(GameScreen):
    """
    Экран игры "Камень, ножницы, бумага"
    """

    player_score = NumericProperty(0)
    computer_score = NumericProperty(0)
    result_text = StringProperty("Нажмите SPIN!")
    rotation_angle = NumericProperty(0)  # Свойство для вращения

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.background_image = 'assets/backgrounds/rsp_bg.jpg'
        # Отключаем создание мяча для этого экрана
        self.sprite_sheet_path = ''

        # Тип игры
        self.game_type = 'classic'

        # Кнопка-переключатель
        self.type_switch_button = ToggleButtonWithLabel(
            size_hint=(None, None),
            size=(150, 50),
            pos_hint={'center_x': 0.5, 'top': 0.95}
        )

        # Кнопка SPIN
        self.spin_button = None

        # Заголовок
        self.title_label = None

        # Изображения для игры
        self.rock_image = None
        self.paper_image = None
        self.scissors_image = None
        self.lizard_image = None
        self.spock_image = None

        # Параметры вращения
        self.is_spinning = False
        self.current_animation = None
        self.images_list = []  # Список всех изображений для вращения
        self.base_angles = {}  # Базовые углы для каждого изображения
        self.original_sizes = {}  # Оригинальные размеры изображений
        self.active_images = []  # Активные изображения
        self.center_x = 0  # Центр экрана по X
        self.center_y = 0  # Центр экрана по Y
        self.radius = 0  # Радиус окружности
        self.winner_image = None  # Победившее изображение

    def on_enter(self):
        """При входе на экран"""
        # Не вызываем super().on_enter() чтобы избежать создания мяча
        # Вместо этого вручную настраиваем экран

        # Сбрасываем состояние
        self.is_spinning = False
        if self.current_animation:
            self.current_animation.cancel(self)
            self.current_animation = None

        # Сбрасываем угол поворота
        self.rotation_angle = 0
        self.winner_image = None

        # Очищаем layout полностью
        self.layout.clear_widgets()

        # Заново создаем UI
        self.setup_background()
        self.show_ui()

        # Создаем кнопку назад
        self.back_button = self.create_back_button()
        self.layout.add_widget(self.back_button)

        # Обновляем биндинги
        self.layout.bind(size=self.update_layout, pos=self.update_layout)

        # Принудительно обновляем позиции
        Clock.schedule_once(lambda dt: self.update_layout(), 0.1)

        # Проверяем и применяем правильный режим
        self.apply_current_game_type()

    def on_leave(self):
        """При выходе с экрана"""
        # Отменяем все анимации
        if self.current_animation:
            self.current_animation.cancel(self)
            self.current_animation = None

        # Отвязываем все события
        if hasattr(self, 'spin_button') and self.spin_button:
            self.spin_button.unbind(on_press=self.start_spin)

        if hasattr(self, 'type_switch_button') and self.type_switch_button:
            self.type_switch_button.unbind(on_press=self.toggle_game_type)

        # Отвязываем обновление layout
        if hasattr(self, 'layout'):
            self.layout.unbind(size=self.update_layout, pos=self.update_layout)

        # Очищаем layout
        if hasattr(self, 'layout'):
            self.layout.clear_widgets()

        # Сбрасываем все ссылки на виджеты
        self.spin_button = None
        self.type_switch_button = None
        self.title_label = None
        self.rock_image = None
        self.paper_image = None
        self.scissors_image = None
        self.lizard_image = None
        self.spock_image = None
        self.winner_image = None
        self.active_images = []
        self.images_list = []
        self.base_angles = {}

        super().on_leave()

    def update_layout(self, *args):
        """Обновляет параметры layout при изменении размера"""
        self.center_x = self.layout.width / 2
        self.center_y = self.layout.height / 2
        self.radius = min(self.layout.width, self.layout.height) * 0.3
        self.update_positions()

    def setup_background(self):
        """Настраивает фон"""
        if self.bg_image:
            self.layout.remove_widget(self.bg_image)

        self.bg_image = Image(
            source=self.background_image,
            allow_stretch=True,
            keep_ratio=False
        )
        self.layout.add_widget(self.bg_image)

    def show_ui(self):
        """Показать интерфейс с кнопкой переключения"""

        # Очищаем UI
        self.clear_ui()

        # Настраиваем кнопку-переключатель
        # Убеждаемся, что кнопка создана заново
        self.type_switch_button = ToggleButtonWithLabel(
            size_hint=(None, None),
            size=(150, 50),
            pos_hint={'center_x': 0.5, 'top': 0.95}
        )
        self.type_switch_button.icon.source = 'assets/images/buttons/Roulette_switch_button.png'
        self.type_switch_button.label.text = 'SWITCH'
        self.type_switch_button.bind(on_press=self.toggle_game_type)
        self.layout.add_widget(self.type_switch_button)

        # Заголовок (временный, будет обновлен в apply_current_game_type)
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

        # Создаем кнопку SPIN по центру (добавляем ПЕРВОЙ, чтобы она была под изображениями)
        self.spin_button = SpinButton(
            pos_hint={'center_x': 0.5, 'center_y': 0.5}
        )
        self.spin_button.bind(on_press=self.start_spin)
        self.layout.add_widget(self.spin_button)

        # Создаем изображения для игры (добавляем ПОСЛЕ кнопки, чтобы они были поверх)
        self.create_game_images()

        # Сбрасываем размеры всех изображений
        self.reset_all_sizes()

        # Обновляем параметры layout
        self.update_layout()

        # Применяем текущий тип игры
        self.apply_current_game_type()

    def create_game_images(self):
        """Создает изображения для игры"""

        # Размер изображений
        image_size = 100

        # Проверяем наличие файлов
        rock_path = 'assets/images/rsp/rock.png'
        paper_path = 'assets/images/rsp/paper.png'
        scissors_path = 'assets/images/rsp/scissors.png'
        lizard_path = 'assets/images/rsp/lizard.png'
        spock_path = 'assets/images/rsp/spock.png'

        # Классические изображения
        self.rock_image = Image(
            source=rock_path if os.path.exists(rock_path) else '',
            size_hint=(None, None),
            size=(image_size, image_size),
            allow_stretch=True
        )

        self.paper_image = Image(
            source=paper_path if os.path.exists(paper_path) else '',
            size_hint=(None, None),
            size=(image_size, image_size),
            allow_stretch=True
        )

        self.scissors_image = Image(
            source=scissors_path if os.path.exists(scissors_path) else '',
            size_hint=(None, None),
            size=(image_size, image_size),
            allow_stretch=True
        )

        # Расширенные изображения
        self.lizard_image = Image(
            source=lizard_path if os.path.exists(lizard_path) else '',
            size_hint=(None, None),
            size=(image_size, image_size),
            allow_stretch=True
        )

        self.spock_image = Image(
            source=spock_path if os.path.exists(spock_path) else '',
            size_hint=(None, None),
            size=(image_size, image_size),
            allow_stretch=True
        )

        # Сохраняем оригинальные размеры
        for img in [self.rock_image, self.paper_image, self.scissors_image,
                    self.lizard_image, self.spock_image]:
            self.original_sizes[img] = (image_size, image_size)

        # Если изображения не найдены, создаем цветные прямоугольники как заглушки
        if not os.path.exists(rock_path):
            self.rock_image.color = (0.5, 0.5, 0.5, 1)  # Серый
        if not os.path.exists(paper_path):
            self.paper_image.color = (1, 1, 1, 1)  # Белый
        if not os.path.exists(scissors_path):
            self.scissors_image.color = (0.8, 0.8, 0.8, 1)  # Светло-серый
        if not os.path.exists(lizard_path):
            self.lizard_image.color = (0, 0.8, 0, 1)  # Зеленый
        if not os.path.exists(spock_path):
            self.spock_image.color = (0.6, 0.4, 0.8, 1)  # Фиолетовый

        # Добавляем все изображения в layout (все они будут поверх кнопки)
        self.layout.add_widget(self.rock_image)
        self.layout.add_widget(self.paper_image)
        self.layout.add_widget(self.scissors_image)
        self.layout.add_widget(self.lizard_image)
        self.layout.add_widget(self.spock_image)

        # Сохраняем список изображений для вращения
        self.images_list = [self.rock_image, self.paper_image, self.scissors_image,
                            self.lizard_image, self.spock_image]

        # Устанавливаем начальную видимость (все скрыты, будут показаны в apply_current_game_type)
        for img in self.images_list:
            img.opacity = 0

    def update_images_visibility(self):
        """Обновляет видимость изображений в зависимости от типа игры"""

        # Определяем активные изображения для нового режима
        if self.game_type == 'classic':
            self.active_images = [self.rock_image, self.paper_image, self.scissors_image]
        else:
            self.active_images = self.images_list

        # Устанавливаем базовые углы для активных изображений
        self.set_base_angles()

    def set_base_angles(self):
        """Устанавливает базовые углы для активных изображений"""
        num_images = len(self.active_images)
        for i, img in enumerate(self.active_images):
            # Вычисляем угол для равномерного распределения по кругу
            angle = (i * (360 / num_images)) - 90  # -90 чтобы начать с верхней точки
            self.base_angles[img] = angle

    def update_positions(self, *args):
        """Обновляет позиции изображений на окружности"""
        if not self.active_images or self.radius == 0:
            return

        for img in self.active_images:
            if img in self.base_angles:
                # Текущий угол = базовый угол + угол поворота
                current_angle = self.base_angles[img] + self.rotation_angle
                rad = math.radians(current_angle)

                x = self.center_x + self.radius * math.cos(rad)
                y = self.center_y + self.radius * math.sin(rad)

                img.pos = (x - img.width / 2, y - img.height / 2)

    def reset_winner_size(self):
        """Возвращает победившее изображение к исходному размеру"""
        if self.winner_image and self.winner_image in self.original_sizes:
            original_size = self.original_sizes[self.winner_image]

            # Сохраняем текущий центр изображения
            current_center_x = self.winner_image.x + self.winner_image.width / 2
            current_center_y = self.winner_image.y + self.winner_image.height / 2

            # Вычисляем новую позицию для исходного размера
            new_x = current_center_x - original_size[0] / 2
            new_y = current_center_y - original_size[1] / 2

            # Анимируем возврат к исходному размеру и позиции
            anim = Animation(
                size=original_size,
                x=new_x,
                y=new_y,
                duration=0.3
            )
            anim.start(self.winner_image)
            self.winner_image = None

    def start_spin(self, instance):
        """Запускает вращение изображений"""
        if self.is_spinning:
            return

        # Сбрасываем размер победителя если он был
        self.reset_winner_size()

        print("🎡 Запускаю вращение...")

        # Сохраняем текущую позицию (приводим к 0-360)
        current_position = self.rotation_angle % 360
        print(f"Текущая позиция (0-360): {current_position}")

        self.is_spinning = True
        self.result_text = "Вращение..."

        # Скрываем кнопку SPIN с анимацией
        anim_hide = Animation(opacity=0, duration=0.3)
        anim_hide.start(self.spin_button)

        # Выбираем случайный результат ДО начала вращения
        if self.game_type == 'classic':
            result = random.choice(['rock', 'paper', 'scissors'])
        else:
            result = random.choice(['rock', 'paper', 'scissors', 'lizard', 'spock'])

        # Получаем изображение-победитель
        if result == 'rock':
            self.winner_image = self.rock_image
        elif result == 'paper':
            self.winner_image = self.paper_image
        elif result == 'scissors':
            self.winner_image = self.scissors_image
        elif result == 'lizard':
            self.winner_image = self.lizard_image
        elif result == 'spock':
            self.winner_image = self.spock_image

        # Вычисляем целевой угол для остановки на верхней позиции (0-360)
        # Верхняя позиция соответствует углу 90 градусов (из-за смещения -90 в set_base_angles)
        target_rotation = 90 - self.base_angles[self.winner_image]
        target_rotation = target_rotation % 360  # Приводим к 0-360

        print(f"Целевая позиция (0-360): {target_rotation}")

        # Вычисляем, сколько нужно добавить к текущей позиции,
        # чтобы достичь target_rotation, всегда двигаясь по часовой стрелке
        delta = (target_rotation - current_position) % 360
        print(f"Дельта до цели: {delta}")

        # Добавляем от 8 до 12 полных оборотов для вариативности
        # Но с сохранением примерно одинаковой начальной скорости
        total_rotations = random.randint(8, 12)

        # Финальный целевой угол
        target_angle = current_position + (360 * total_rotations) + delta

        print(f"Финальный целевой угол: {target_angle} (позиция {target_angle % 360})")
        print(f"Количество оборотов: {total_rotations}")

        # Единая анимация с плавным замедлением с самого начала
        # Используем out_cubic для очень плавного замедления
        # Длительность зависит от количества оборотов, чтобы сохранить
        # примерно одинаковую начальную скорость
        base_duration = 8.0  # Базовая длительность для 8 оборотов
        duration = base_duration * (total_rotations / 8.0)

        anim = Animation(
            rotation_angle=target_angle,
            duration=duration,
            t='out_cubic'  # Плавное замедление с самого начала
        )

        anim.bind(on_complete=self.on_spin_complete)

        self.current_animation = anim
        anim.start(self)

    def on_spin_complete(self, animation, widget):
        """Вызывается при завершении вращения"""
        print("🎡 Вращение завершено")

        # Сохраняем только позицию (0-360) для следующего раза
        self.rotation_angle = self.rotation_angle % 360
        print(f"Финальная позиция (0-360): {self.rotation_angle}")

        self.is_spinning = False
        self.current_animation = None

        # Показываем кнопку SPIN
        anim_show = Animation(opacity=1, duration=0.5)
        anim_show.start(self.spin_button)

        # Показываем результат
        self.show_result()

    def show_result(self):
        """Показывает результат вращения"""
        if not self.winner_image:
            return

        # Определяем название результата
        if self.winner_image == self.rock_image:
            result_name = '🪨 КАМЕНЬ'
        elif self.winner_image == self.paper_image:
            result_name = '📄 БУМАГА'
        elif self.winner_image == self.scissors_image:
            result_name = '✂️ НОЖНИЦЫ'
        elif self.winner_image == self.lizard_image:
            result_name = '🦎 ЯЩЕРИЦА'
        elif self.winner_image == self.spock_image:
            result_name = '🖖 СПОК'
        else:
            result_name = ''

        self.result_text = f"ВЫПАЛО: {result_name}"

        # Анимация увеличения победившего изображения
        if self.winner_image in self.original_sizes:
            original_size = self.original_sizes[self.winner_image]
            new_size = (original_size[0] * 1.3, original_size[1] * 1.3)

            # Вычисляем новую позицию так, чтобы центр остался на том же месте
            current_center_x = self.winner_image.x + self.winner_image.width / 2
            current_center_y = self.winner_image.y + self.winner_image.height / 2

            new_x = current_center_x - new_size[0] / 2
            new_y = current_center_y - new_size[1] / 2

            # Создаем параллельную анимацию для размера и позиции
            anim = Animation(
                size=new_size,
                x=new_x,
                y=new_y,
                duration=0.3
            )
            anim.start(self.winner_image)

    def toggle_game_type(self, instance=None):
        """Переключение типа игры с анимацией и случайной перетасовкой"""
        if self.is_spinning:
            return  # Не переключаем во время вращения

        print(f"\n=== SWITCHING GAME TYPE FROM {self.game_type} ===")

        # Отменяем все текущие анимации изображений
        self.cancel_all_image_animations()

        # Отменяем анимацию вращения если она есть
        if self.current_animation:
            self.current_animation.cancel(self)
            self.current_animation = None

        # Сначала сбрасываем победителя, если он есть
        if self.winner_image:
            # Возвращаем победителю исходный размер без анимации
            if self.winner_image in self.original_sizes:
                original_size = self.original_sizes[self.winner_image]
                self.winner_image.size = original_size
            self.winner_image = None

        # Сбрасываем размеры всех изображений
        self.reset_all_sizes()

        # Сохраняем текущие позиции и прозрачность для анимации
        old_positions = {}
        old_opacities = {}
        old_active = self.active_images.copy() if self.active_images else []

        # Сохраняем данные для всех изображений
        for img in self.images_list:
            old_positions[img] = (img.x, img.y)
            old_opacities[img] = img.opacity
            print(f"Old {img}: pos={img.pos}, opacity={img.opacity}")

        # Меняем тип игры
        if self.game_type == 'classic':
            self.game_type = 'extended'
            if self.title_label:
                self.title_label.text = 'EXTENDED RSP'
        else:
            self.game_type = 'classic'
            if self.title_label:
                self.title_label.text = 'CLASSIC RSP'

        # Обновляем список активных изображений
        if self.game_type == 'classic':
            self.active_images = [self.rock_image, self.paper_image, self.scissors_image]
        else:
            self.active_images = self.images_list

        # СБРАСЫВАЕМ УГОЛ ПОВОРОТА В 0 ПЕРЕД ВЫЧИСЛЕНИЕМ НОВЫХ ПОЗИЦИЙ
        self.rotation_angle = 0

        # Устанавливаем базовые углы для активных изображений
        self.set_base_angles()

        # ПЕРЕТАСОВЫВАЕМ БАЗОВЫЕ УГЛЫ ДЛЯ СОЗДАНИЯ СЛУЧАЙНЫХ ПОЗИЦИЙ
        self.shuffle_base_angles()

        # Вычисляем новые позиции для всех изображений
        new_positions = {}
        for img in self.images_list:
            if img in self.base_angles:
                current_angle = self.base_angles[img]  # rotation_angle = 0
                rad = math.radians(current_angle)
                x = self.center_x + self.radius * math.cos(rad)
                y = self.center_y + self.radius * math.sin(rad)
                new_positions[img] = (x - img.width / 2, y - img.height / 2)
                print(f"New {img}: pos={new_positions[img]}, base_angle={self.base_angles[img]}")
            else:
                # Если изображение не в base_angles, оставляем его на старом месте
                new_positions[img] = old_positions[img]
                print(f"New {img} (not in base): {new_positions[img]}")

        # Подготавливаем изображения к анимации
        for img in self.images_list:
            target_opacity = 1.0 if img in self.active_images else 0.0
            current_opacity = old_opacities[img]

            # Если изображение должно стать видимым, но было скрыто
            if target_opacity > 0.9 and current_opacity < 0.1:
                img.opacity = 0
                # Устанавливаем начальную позицию для анимации
                if img in old_positions:
                    img.x, img.y = old_positions[img]
            # Если изображение должно остаться видимым, оставляем как есть
            elif target_opacity > 0.9 and current_opacity > 0.9:
                # Убеждаемся, что оно на старой позиции перед анимацией
                if img in old_positions:
                    img.x, img.y = old_positions[img]

        # Запускаем анимацию через небольшой промежуток времени
        Clock.schedule_once(lambda dt: self._do_switch_animation(new_positions), 0.05)

        print(f"Game type switched to: {self.game_type} with shuffled positions")

    def _do_switch_animation(self, new_positions):
        """Выполняет анимацию переключения"""
        animations = []

        for img in self.images_list:
            target_opacity = 1.0 if img in self.active_images else 0.0

            # Получаем целевую позицию
            if img in new_positions:
                target_x, target_y = new_positions[img]
            else:
                continue

            # Проверяем, нужно ли анимировать позицию
            need_position_anim = (abs(img.x - target_x) > 1 or abs(img.y - target_y) > 1)
            need_opacity_anim = abs(target_opacity - img.opacity) > 0.01

            if need_position_anim or need_opacity_anim:
                anim_props = {}

                if need_position_anim:
                    anim_props['x'] = target_x
                    anim_props['y'] = target_y
                    print(
                        f"Animating position for {img}: from ({img.x:.1f}, {img.y:.1f}) to ({target_x:.1f}, {target_y:.1f})")

                if need_opacity_anim:
                    anim_props['opacity'] = target_opacity
                    print(f"Animating opacity for {img}: from {img.opacity:.2f} to {target_opacity:.2f}")

                if anim_props:
                    duration = 0.5 if need_position_anim else 0.3
                    anim = Animation(**anim_props, duration=duration, t='out_quad')
                    animations.append(anim)
                    anim.start(img)

        if not animations:
            print("No animations needed, forcing position update")
            self.force_update_positions()
        else:
            print(f"Started {len(animations)} animations")
            Clock.schedule_once(lambda dt: self.force_update_positions(), 0.6)

    def start_game(self):
        """Метод вызывается при переходе на экран"""
        pass

    def on_rotation_angle(self, instance, value):
        """Вызывается при изменении угла поворота"""
        self.update_positions()

    def clear_ui(self):
        """Очищает все виджеты интерфейса кроме фона"""
        if not hasattr(self, 'layout') or not self.layout:
            return

        # Удаляем все виджеты кроме фона и кнопки назад
        for child in self.layout.children[:]:
            if child != self.bg_image and child != self.back_button:
                self.layout.remove_widget(child)

        # Сбрасываем ссылки
        self.spin_button = None
        self.title_label = None
        self.rock_image = None
        self.paper_image = None
        self.scissors_image = None
        self.lizard_image = None
        self.spock_image = None
        self.winner_image = None
        self.active_images = []
        self.images_list = []
        self.base_angles = {}

    def reset_all_sizes(self):
        """Сбрасывает размеры всех изображений к исходным"""
        for img in self.images_list:
            if img in self.original_sizes:
                original_size = self.original_sizes[img]

                # Просто устанавливаем исходный размер
                # Позиция будет обновлена в update_positions
                img.size = original_size

    def force_update_positions(self):
        """Принудительно обновляет позиции всех изображений"""
        if not self.active_images or self.radius == 0:
            return

        print(f"Force updating positions for {len(self.active_images)} images")
        for img in self.active_images:
            if img in self.base_angles:
                current_angle = self.base_angles[img] + self.rotation_angle
                rad = math.radians(current_angle)
                x = self.center_x + self.radius * math.cos(rad)
                y = self.center_y + self.radius * math.sin(rad)
                img.pos = (x - img.width / 2, y - img.height / 2)
                print(f"  {img}: pos={img.pos}")

    def animate_transition(self, old_active, new_active, old_positions, new_positions):
        """Анимирует переход между режимами"""

        # Анимация для изображений, которые остаются видимыми
        for img in set(old_active) & set(new_active):
            if img in old_positions and img in new_positions:
                anim = Animation(
                    x=new_positions[img][0],
                    y=new_positions[img][1],
                    duration=0.5,
                    t='out_quad'
                )
                anim.start(img)

        # Анимация для появляющихся изображений
        for img in set(new_active) - set(old_active):
            if img in new_positions:
                img.opacity = 0
                anim = Animation(
                    x=new_positions[img][0],
                    y=new_positions[img][1],
                    opacity=1,
                    duration=0.5,
                    t='out_quad'
                )
                anim.start(img)

        # Анимация для исчезающих изображений
        for img in set(old_active) - set(new_active):
            anim = Animation(opacity=0, duration=0.3)
            anim.start(img)

    def apply_current_game_type(self):
        """Применяет текущий тип игры при входе на экран"""
        # Устанавливаем правильный заголовок
        if self.title_label:
            self.title_label.text = 'CLASSIC RSP' if self.game_type == 'classic' else 'EXTENDED RSP'

        # Обновляем видимость изображений в зависимости от типа игры
        if self.game_type == 'classic':
            # Показываем только классические изображения
            self.rock_image.opacity = 1
            self.paper_image.opacity = 1
            self.scissors_image.opacity = 1
            self.lizard_image.opacity = 0
            self.spock_image.opacity = 0
            self.active_images = [self.rock_image, self.paper_image, self.scissors_image]
        else:
            # Показываем все изображения
            for img in self.images_list:
                img.opacity = 1
            self.active_images = self.images_list

        # Устанавливаем базовые углы для активных изображений
        self.set_base_angles()

        # Сбрасываем угол поворота
        self.rotation_angle = 0

        # Принудительно обновляем позиции
        Clock.schedule_once(lambda dt: self.force_update_positions(), 0.1)

        print(f"Applied game type: {self.game_type}")

    def cancel_all_image_animations(self):
        """Отменяет все анимации изображений"""
        for img in self.images_list:
            try:
                # Останавливаем все анимации для этого изображения
                Animation.cancel_all(img)
            except:
                pass

    def shuffle_base_angles(self):
        """Перетасовывает базовые углы для активных изображений"""
        if len(self.active_images) < 2:
            return

        num_images = len(self.active_images)

        # Создаем равномерные углы
        angles = []
        for i in range(num_images):
            angle = (i * (360 / num_images)) - 90  # -90 чтобы начать с верхней точки
            angles.append(angle)

        # Перетасовываем углы
        random.shuffle(angles)

        # Присваиваем перетасованные углы изображениям
        for i, img in enumerate(self.active_images):
            self.base_angles[img] = angles[i]

        print(f"Shuffled base angles: {self.base_angles}")

        # После перетасовки принудительно обновляем позиции
        self.force_update_positions()