from kivy.uix.screenmanager import Screen
from kivy.uix.floatlayout import FloatLayout
from kivy.properties import BooleanProperty, NumericProperty, StringProperty
from kivy.clock import Clock
from kivy.animation import Animation
from kivy.uix.image import Image as KivyImage
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.modalview import ModalView
from kivy.graphics import Color, Rectangle, Line
from kivy.vector import Vector
from kivy.core.window import Window
import random

from screens.base_game_screen import BaseGameScreen


class BulletIcon(Button):
    """Иконка патрона в правом верхнем углу"""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.background_normal = ''
        self.background_color = (0.8, 0.2, 0.2, 0.9)
        self.size_hint = (None, None)
        self.size = (60, 60)
        self.text = '💀'
        self.font_size = '28sp'
        self.bold = True
        self.update_border()

    def update_border(self):
        """Добавляет или обновляет обводку"""
        self.canvas.after.clear()
        with self.canvas.after:
            Color(1, 1, 1, 0.3)
            Line(width=2, rectangle=(self.x, self.y, self.width, self.height))

    def on_pos(self, *args):
        """Обновляет обводку при изменении позиции"""
        self.update_border()

    def on_size(self, *args):
        """Обновляет обводку при изменении размера"""
        self.update_border()


class BulletSlot(Button):
    """Слот для патрона в барабане револьвера"""

    def __init__(self, slot_number=0, **kwargs):
        super().__init__(**kwargs)
        self.slot_number = slot_number
        self.has_bullet = False
        self.is_current = False
        self.background_normal = ''
        self.background_color = (0.2, 0.2, 0.2, 0.8)
        self.color = (1, 1, 1, 1)
        self.font_size = '24sp'
        self.bold = True
        self.update_appearance()

    def update_appearance(self):
        """Обновляет внешний вид слота"""
        if self.has_bullet:
            self.text = "💀"
            self.background_color = (0.8, 0.1, 0.1, 0.9)
        else:
            self.text = "○"
            self.background_color = (0.3, 0.3, 0.3, 0.6)

        self.update_current_indicator()

    def update_current_indicator(self):
        """Обновляет индикатор текущего слота"""
        self.canvas.after.clear()
        if self.is_current:
            with self.canvas.after:
                Color(1, 1, 0, 0.8)
                Line(width=3, rectangle=(self.x + 2, self.y + 2, self.width - 4, self.height - 4))

    def set_current(self, is_current):
        """Устанавливает, является ли слот текущим"""
        self.is_current = is_current
        self.update_current_indicator()

    def toggle_bullet(self):
        """Переключает состояние патрона"""
        self.has_bullet = not self.has_bullet
        self.update_appearance()

    def on_pos(self, *args):
        """Обновляет индикатор при изменении позиции"""
        # Ждем пока виджет полностью инициализируется
        Clock.schedule_once(lambda dt: self.update_current_indicator(), 0.01)

    def on_size(self, *args):
        """Обновляет индикатор при изменении размера"""
        # Ждем пока виджет полностью инициализируется
        Clock.schedule_once(lambda dt: self.update_current_indicator(), 0.01)

class ChamberModal(ModalView):
    """Модальное окно барабана для зарядки патронов"""

    def __init__(self, main_screen, **kwargs):
        super().__init__(**kwargs)
        self.main_screen = main_screen
        self.background_color = (0, 0, 0, 0.7)  # Полупрозрачный черный фон
        self.auto_dismiss = True
        self.size_hint = (0.9, 0.9)
        self.pos_hint = {'center_x': 0.5, 'center_y': 0.5}

        self.layout = FloatLayout()
        self.add_widget(self.layout)

        Clock.schedule_once(self.create_chamber_ui, 0.1)  # Даем время на инициализацию

    def create_chamber_ui(self, dt=None):
        """Создает интерфейс модального окна барабана"""
        # Фон окна
        with self.layout.canvas.before:
            Color(0, 0, 0, 0)
            self.bg_rect = Rectangle(pos=self.layout.pos, size=self.layout.size)

        self.layout.bind(pos=self.update_bg, size=self.update_bg)

        radius = min(self.layout.width, self.layout.height) * 0.3

        # Изображение барабана
        try:
            # Пытаемся загрузить изображение барабана
            drum_img = KivyImage(
                source='assets/images/guns/Drum_1024x1024.png',  # Твой файл
                size_hint=(None, None),
                size=(radius * 2.2, radius * 2.2),  # Немного больше слотов
                pos_hint={'center_x': 0.5, 'center_y': 0.6},
                allow_stretch=True,
                keep_ratio=True
            )
            self.layout.add_widget(drum_img)
        except Exception as e:
            # Если изображения нет, показываем заглушку
            print(f"Не удалось загрузить изображение барабана: {e}")
            drum_placeholder = Label(
                text='БАРАБАН',
                font_size='24sp',
                bold=True,
                color=(0.5, 0.5, 0.5, 0.5),
                pos_hint={'center_x': 0.5, 'center_y': 0.6},
                size_hint=(None, None),
                size=(200, 200)
            )
            self.layout.add_widget(drum_placeholder)

        # Создаем барабан с 6 слотами по кругу
        center_x = self.layout.width * 0.5
        center_y = self.layout.height * 0.6
        radius = min(self.layout.width, self.layout.height) * 0.3

        # Создаем 6 слотов по кругу
        self.slots = []
        for i in range(6):
            # Позиции для круга
            if i == 0:  # сверху
                x, y = center_x, center_y + radius * 0.7
            elif i == 1:  # сверху-справа
                x, y = center_x + radius * 0.6, center_y + radius * 0.35
            elif i == 2:  # снизу-справа
                x, y = center_x + radius * 0.6, center_y - radius * 0.35
            elif i == 3:  # снизу
                x, y = center_x, center_y - radius * 0.7
            elif i == 4:  # снизу-слева
                x, y = center_x - radius * 0.6, center_y - radius * 0.35
            elif i == 5:  # сверху-слева
                x, y = center_x - radius * 0.6, center_y + radius * 0.35

            # Создаем слот
            slot = BulletSlot(
                slot_number=i,
                size_hint=(None, None),
                size=(70, 70),
                pos=(x - 35, y - 35)
            )

            # Копируем состояние из основного экрана
            if i < len(self.main_screen.bullet_slots):
                slot.has_bullet = self.main_screen.bullet_slots[i].has_bullet
                slot.update_appearance()

            # Обработчик касания
            slot.bind(on_release=lambda instance, idx=i: self.toggle_slot(idx))

            self.slots.append(slot)
            self.layout.add_widget(slot)

            # Номер слота
            slot_num_label = Label(
                text=str(i + 1),
                font_size='12sp',
                color=(0.8, 0.8, 0.8, 0.7),
                pos=(x - 10, y + 45)
            )
            self.layout.add_widget(slot_num_label)

        # Кнопка готово
        done_btn = Button(
            text='ГОТОВО',
            font_size='20sp',
            bold=True,
            size_hint=(None, None),
            size=(200, 60),
            pos_hint={'center_x': 0.5, 'y': 0.05},
            background_color=(0.2, 0.6, 0.2, 1),
            color=(1, 1, 1, 1)
        )
        done_btn.bind(on_release=self.close_modal)
        self.layout.add_widget(done_btn)

    def toggle_slot(self, slot_index):
        """Переключает патрон в слоте"""
        slot = self.slots[slot_index]
        slot.toggle_bullet()

    def close_modal(self, instance):
        """Закрывает модальное окно и обновляет основной экран"""
        # Переносим состояние в основной экран
        for i, slot in enumerate(self.slots):
            if i < len(self.main_screen.bullet_slots):
                self.main_screen.bullet_slots[i].has_bullet = slot.has_bullet
                self.main_screen.bullet_slots[i].update_appearance()

        # Обновляем счетчик патронов
        self.main_screen.total_bullets = sum(1 for s in self.main_screen.bullet_slots if s.has_bullet)
        self.main_screen.update_bullet_counter()

        self.dismiss()

    def update_bg(self, instance, value):
        """Обновляет фон"""
        self.bg_rect.pos = instance.pos
        self.bg_rect.size = instance.size


class RusRouletteScreen(BaseGameScreen):
    """Реалистичная русская рулетка с жестовым управлением"""

    background_image = 'assets/backgrounds/rus_roulette_bg_1024x1024.jpg'
    # sound_file = 'assets/sounds/football_bounce.wav'

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.name = 'rus_roulette'

        # Элементы игры
        self.gun_image = None
        self.bullet_slots = []
        self.current_slot = 0
        self.result_label = None
        self.shot_counter = None
        self.shots_fired = 0
        self.total_bullets = 0
        self.gun_rotation = 0

        # Иконка патрона
        self.bullet_icon = None

        # Для жестового управления
        self.touch_start_pos = None
        self.touch_start_time = None
        self.is_dragging = False
        self.drag_start_pos = None

        # Модальное окно
        self.chamber_modal = None

        self.bind(size=self._update_positions)

    def on_enter(self):
        """При входе на экран"""
        super().on_enter()
        Clock.schedule_once(self.create_game_screen, 0.1)

    def create_game_screen(self, dt=None):
        """Создает игровой экран"""
        # Очищаем layout
        self.layout.clear_widgets()

        # Восстанавливаем фон и кнопку назад
        super().on_enter()

        # Создаем иконку патрона
        self.create_bullet_icon()

        # Создаем игровые элементы
        self.create_gun()
        self.create_bullet_chamber()
        self.create_info_labels()

        # Обновляем состояние
        self.update_bullet_counter()

    def create_bullet_icon(self):
        """Создает иконку патрона в правом верхнем углу"""
        if self.bullet_icon:
            self.layout.remove_widget(self.bullet_icon)

        self.bullet_icon = BulletIcon(
            pos_hint={'right': 0.95, 'top': 0.95}
        )
        self.bullet_icon.bind(on_release=self.show_chamber_modal)
        self.layout.add_widget(self.bullet_icon)

        # Счетчик патронов рядом с иконкой
        self.bullet_count_label = Label(
            text='0',
            font_size='16sp',
            bold=True,
            color=(1, 1, 1, 1),
            pos_hint={'right': 0.87, 'top': 0.95},
            size_hint=(None, None),
            size=(30, 30)
        )
        self.layout.add_widget(self.bullet_count_label)

    def create_gun(self):
        """Создает изображение пистолета с жестовым управлением"""
        if self.gun_image:
            self.layout.remove_widget(self.gun_image)

        try:
            self.gun_image = KivyImage(
                source='assets/images/guns/revolver.png',
                size_hint=(None, None),
                size=(400, 200),
                pos_hint={'center_x': 0.5, 'center_y': 0.55},
                allow_stretch=True
            )
        except:
            # Заглушка если нет изображения
            self.gun_image = Button(
                text='🔫\n(Жестовое управление)',
                font_size='16sp',
                size_hint=(None, None),
                size=(400, 200),
                pos_hint={'center_x': 0.5, 'center_y': 0.55},
                background_color=(0.3, 0.3, 0.3, 0.7),
                color=(1, 1, 1, 1)
            )

        # Включаем мультитач для жестов
        self.gun_image.multitouch_on_box = True

        # Обработчики жестов
        self.gun_image.bind(on_touch_down=self.on_gun_touch_down)
        self.gun_image.bind(on_touch_move=self.on_gun_touch_move)
        self.gun_image.bind(on_touch_up=self.on_gun_touch_up)

        self.layout.add_widget(self.gun_image)

    def create_bullet_chamber(self):
        """Создает барабан с 6 слотами по кругу"""
        # Удаляем старые слоты
        for slot in self.bullet_slots:
            self.layout.remove_widget(slot)
        self.bullet_slots = []

        # Центр круга
        center_x = self.width * 0.5
        center_y = self.height * 0.55
        radius = 140

        # Создаем 6 слотов по кругу
        for i in range(6):
            # Вычисляем позицию
            angle = 2 * 3.14159 * i / 6
            x = center_x + radius * 0.9 * (0.8 if i < 3 else 1.2) * 0.5
            y = center_y + radius * 0.9 * (0.6 if i < 3 else 0.8) * 0.5

            # Создаем слот
            slot = BulletSlot(
                slot_number=i,
                size_hint=(None, None),
                size=(50, 50),
                pos=(x - 25, y - 25)
            )

            # Обработчик клика по слоту
            slot.bind(on_release=lambda instance, idx=i: self.toggle_slot_bullet(idx))

            self.bullet_slots.append(slot)
            self.layout.add_widget(slot)

    def create_info_labels(self):
        """Создает информационные надписи"""
        # Заголовок
        title = Label(
            text='RUSSIAN ROULETTE',
            font_size='22sp',
            bold=True,
            color=(1, 0.2, 0.2, 1),
            pos_hint={'center_x': 0.5, 'top': 0.92},
            size_hint=(None, None),
            size=(450, 50)
        )

        # Счетчик выстрелов
        self.shot_counter = Label(
            text='Выстрелов: 0',
            font_size='16sp',
            color=(1, 1, 1, 1),
            pos_hint={'center_x': 0.5, 'y': 0.1},
            size_hint=(None, None),
            size=(150, 40)
        )

        self.layout.add_widget(title)
        self.layout.add_widget(self.shot_counter)

    def show_chamber_modal(self, instance):
        """Показывает модальное окно барабана для зарядки"""
        # Эффект затемнения
        self.chamber_modal = ChamberModal(self)
        self.chamber_modal.open()

    def on_gun_touch_down(self, instance, touch):
        """Обработка касания пистолета"""
        if not self.gun_image.collide_point(*touch.pos):
            return False

        # Сохраняем начальную позицию и время
        self.touch_start_pos = touch.pos
        self.touch_start_time = touch.time_start
        self.is_dragging = False

        # Определяем зону касания
        gun_pos = self.gun_image.pos
        gun_size = self.gun_image.size

        # Зона курка (правая верхняя часть)
        trigger_zone = (
            gun_pos[0] + gun_size[0] * 0.7,  # 70% справа
            gun_pos[1] + gun_size[1] * 0.7,  # 70% сверху
            gun_size[0] * 0.3,  # 30% ширины
            gun_size[1] * 0.3  # 30% высоты
        )

        # Зона барабана (центр левой части)
        chamber_zone = (
            gun_pos[0] + gun_size[0] * 0.15,  # 15% слева
            gun_pos[1] + gun_size[1] * 0.4,  # 40% сверху
            gun_size[0] * 0.3,  # 30% ширины
            gun_size[1] * 0.4  # 40% высоты
        )

        # Проверяем, в какой зоне касание
        tx, ty = touch.pos

        # Если тап по курку
        if (trigger_zone[0] <= tx <= trigger_zone[0] + trigger_zone[2] and
                trigger_zone[1] <= ty <= trigger_zone[1] + trigger_zone[3]):
            self.pull_trigger()
            return True

        # Если касание в зоне барабана
        elif (chamber_zone[0] <= tx <= chamber_zone[0] + chamber_zone[2] and
              chamber_zone[1] <= ty <= chamber_zone[1] + chamber_zone[3]):
            self.drag_start_pos = touch.pos
            self.is_dragging = True
            return True

        return True

    def on_gun_touch_move(self, instance, touch):
        """Обработка движения по пистолету"""
        if not self.is_dragging or not self.drag_start_pos:
            return False

        # Вычисляем расстояние свайпа
        dx = touch.pos[0] - self.drag_start_pos[0]
        dy = touch.pos[1] - self.drag_start_pos[1]
        distance = Vector(dx, dy).length()

        # Если свайп достаточно длинный - вращаем барабан
        if distance > 30:  # порог свайпа
            self.spin_chamber()
            self.is_dragging = False
            self.drag_start_pos = None

        return True

    def on_gun_touch_up(self, instance, touch):
        """Обработка отпускания пистолета"""
        self.is_dragging = False
        self.drag_start_pos = None
        return True

    def toggle_slot_bullet(self, slot_index):
        """Добавляет/убирает патрон в слоте"""
        slot = self.bullet_slots[slot_index]
        slot.toggle_bullet()

        self.total_bullets = sum(1 for s in self.bullet_slots if s.has_bullet)
        self.update_bullet_counter()

        # Визуальная обратная связь
        self.result_label.text = f'Слот {slot_index + 1}: {"заряжен" if slot.has_bullet else "разряжен"}'
        self.result_label.color = (0.8, 0.8, 0.8, 1)
        Clock.schedule_once(self.reset_result_text, 1.5)

    def update_bullet_counter(self):
        """Обновляет счетчик патронов"""
        self.total_bullets = sum(1 for s in self.bullet_slots if s.has_bullet)
        if self.bullet_count_label:
            self.bullet_count_label.text = str(self.total_bullets)

        # Обновляем цвет иконки в зависимости от количества патронов
        if self.bullet_icon:
            if self.total_bullets == 0:
                self.bullet_icon.background_color = (0.3, 0.3, 0.3, 0.7)
                self.bullet_icon.text = '○'
            elif self.total_bullets >= 4:
                self.bullet_icon.background_color = (0.8, 0.1, 0.1, 0.9)
                self.bullet_icon.text = '💀'
            else:
                self.bullet_icon.background_color = (0.8, 0.5, 0.1, 0.9)
                self.bullet_icon.text = '💀'

        if self.shot_counter:
            self.shot_counter.text = f'Выстрелов: {self.shots_fired}'

    def pull_trigger(self):
        """Спуск курка (вызывается при тапе по курку)"""
        # Визуальная обратная связь - анимация курка
        self.result_label.text = '...'
        self.result_label.color = (1, 1, 0, 1)

        # Анимация нажатия курка
        anim = Animation(pos_hint={'center_x': 0.505, 'center_y': 0.545}, duration=0.05)
        anim += Animation(pos_hint={'center_x': 0.5, 'center_y': 0.55}, duration=0.1)
        anim.start(self.gun_image)

        # Проверяем через 1 секунду
        Clock.schedule_once(lambda dt: self.check_shot_result(), 1.0)

    def check_shot_result(self):
        """Проверяет результат выстрела"""
        current_slot = self.bullet_slots[self.current_slot]

        if current_slot.has_bullet:
            # ВЫСТРЕЛ!
            self.result_label.text = 'БАХ! ВЫСТРЕЛ!'
            self.result_label.color = (1, 0, 0, 1)

            # Анимация отдачи
            anim = Animation(pos_hint={'center_x': 0.52, 'center_y': 0.55}, duration=0.1)
            anim += Animation(pos_hint={'center_x': 0.5, 'center_y': 0.55}, duration=0.1)
            anim.start(self.gun_image)

            # Убираем патрон
            current_slot.has_bullet = False
            current_slot.update_appearance()
            self.total_bullets -= 1
            self.update_bullet_counter()

        else:
            # Холостой выстрел
            self.result_label.text = 'Щелк! Холостой.'
            self.result_label.color = (0, 1, 0, 1)

        self.shots_fired += 1
        self.current_slot = (self.current_slot + 1) % 6

        self.update_bullet_counter()
        self.update_current_slot()

        # Сброс текста через 2 секунды
        Clock.schedule_once(self.reset_result_text, 2.0)

    def spin_chamber(self):
        """Вращение барабана (вызывается при свайпе)"""
        # Сохраняем старую позицию для анимации
        old_slot = self.current_slot
        self.current_slot = random.randint(0, 5)

        # Анимация вращения
        rotations = random.randint(2, 5)
        anim = Animation(rotation=self.gun_rotation + 360 * rotations, duration=1.0)
        anim.start(self.gun_image)
        self.gun_rotation += 360 * rotations

        self.result_label.text = f'Барабан вращается...'
        self.result_label.color = (1, 1, 0, 1)

        # Через 1.5 секунды готово
        Clock.schedule_once(self.finish_spin, 1.5)

    def finish_spin(self, dt):
        """Завершение вращения"""
        self.result_label.text = f'Барабан остановлен'
        self.result_label.color = (1, 1, 1, 1)

        # Нормализуем вращение
        self.gun_rotation = self.gun_rotation % 360
        self.gun_image.rotation = 0

        self.update_current_slot()

    def reset_result_text(self, dt):
        """Сбрасывает текст результата"""
        self.result_label.text = 'Готов к следующему выстрелу'
        self.result_label.color = (1, 1, 1, 1)

    def start_game(self):
        """Начать игру"""
        # Сбрасываем состояние
        self.current_slot = 0
        self.shots_fired = 0
        self.total_bullets = 0
        self.gun_rotation = 0

        # Очищаем все патроны
        for slot in self.bullet_slots:
            slot.has_bullet = False
            slot.update_appearance()

        # Создаем игровой экран
        self.create_game_screen()

    def _update_positions(self, instance, value):
        """Обновление позиций при изменении размера"""
        if self.gun_image:
            self.gun_image.pos_hint = {'center_x': 0.5, 'center_y': 0.55}

        if self.bullet_slots:
            Clock.schedule_once(lambda dt: self.create_bullet_chamber(), 0.1)