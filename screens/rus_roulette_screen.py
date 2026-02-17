import os
import random

from kivy.uix.image import Image
from kivy.uix.behaviors import ButtonBehavior
from kivy.uix.floatlayout import FloatLayout
from kivy.clock import Clock
from kivy.animation import Animation
from kivy.uix.image import Image as KivyImage
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.modalview import ModalView
from kivy.graphics import Color, Line
from kivy.vector import Vector
from kivy.core.window import Window
from kivy.core.audio import SoundLoader
from sound_manager import SoundManager
from screens.base_game_screen import BaseGameScreen


class BulletSprite(KivyImage):
    """Спрайт патрона в слоте барабана с поворотом и случайным изображением"""

    def __init__(self, slot_number=0, **kwargs):
        super().__init__(**kwargs)
        self.slot_number = slot_number
        # Выбираем случайное изображение от 0 до 5
        random_index = random.randint(0, 10)
        self.source = f'assets/images/guns/Bullet_back_{random_index}.png'
        self.size_hint = (None, None)
        self.size = (100, 100)
        self.allow_stretch = True
        self.keep_ratio = True
        self.opacity = 0
        self.rotation = random.uniform(0, 360)
        self.is_loaded = False
        self.chamber_sound = None

    def set_loaded(self, loaded):
        self.is_loaded = loaded
        self.opacity = 1 if loaded else 0

class BulletIcon(ButtonBehavior, Image):
    """Иконка патрона в правом верхнем углу"""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.source = 'assets/images/guns/Drum_1024x1024.png'
        self.size_hint = (None, None)
        self.size = (60, 60)
        self.allow_stretch = True
        self.keep_ratio = True
        self.update_border()

    def update_border(self):
        """Добавляет или обновляет обводку"""
        self.canvas.after.clear()
        with self.canvas.after:
            Color(1, 1, 1, 0.3)
            Line(width=2, rectangle=(self.x, self.y, self.width, self.height))

    def on_pos(self, *args):
        self.update_border()

    def on_size(self, *args):
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
        self.background_color = (0, 0, 0, 0)  # УБРАН черный фон!
        self.auto_dismiss = True
        self.size_hint = (0.9, 0.9)
        self.pos_hint = {'center_x': 0.5, 'center_y': 0.5}

        self.layout = FloatLayout()
        self.add_widget(self.layout)

        self.bullet_sprites = []
        self.slot_buttons = []

        Clock.schedule_once(self.create_chamber_ui, 0.1)

    def create_chamber_ui(self, dt=None):
        """Создает интерфейс модального окна барабана"""
        # === 1. БАРАБАН (фон) ===
        drum_size = min(self.layout.width, self.layout.height) * 0.7
        try:
            drum_img = KivyImage(
                source='assets/images/guns/Drum_1024x1024.png',
                size_hint=(None, None),
                size=(drum_size, drum_size),
                pos_hint={'center_x': 0.5, 'center_y': 0.6},
                allow_stretch=True,
                keep_ratio=True
            )
            self.layout.add_widget(drum_img)
        except Exception as e:
            # Рисуем круг-заглушку
            with self.layout.canvas:
                Color(0.3, 0.3, 0.3, 0.8)
                Line(circle=(self.layout.width * 0.5, self.layout.height * 0.6,
                             drum_size / 2), width=3)

        # Координаты в процентах от размера окна - ПОВЕРНУТЫ на 1/12 (30°)
        slot_positions = [
            (0.66, 0.77),  # слот 1 - верх
            (0.785, 0.66),  # слот 2 - верх-право
            (0.675, 0.55),  # слот 3 - право
            (0.45, 0.55),  # слот 4 - низ
            (0.33, 0.66),  # слот 5 - лево
            (0.445, 0.765),  # слот 6 - верх-лево
        ]

        # Создаем патроны и зоны касания
        for i, (rel_x, rel_y) in enumerate(slot_positions):
            # Конвертируем относительные координаты в абсолютные
            x = self.layout.width * rel_x
            y = self.layout.height * rel_y

            # === СПРАЙТ ПАТРОНА (сверху) ===
            bullet = BulletSprite(
                slot_number=i,
                pos=(x - 50, y - 50)  # 100/2 = 50
            )

            # Копируем состояние из основного экрана
            if i < len(self.main_screen.bullet_slots):
                bullet.set_loaded(self.main_screen.bullet_slots[i].has_bullet)

            self.bullet_sprites.append(bullet)
            self.layout.add_widget(bullet)

            # === ЗОНА КАСАНИЯ (невидимая кнопка) ===
            slot_btn = Button(
                size_hint=(None, None),
                size=(70, 70),
                pos=(x - 35, y - 35),
                background_normal='',
                background_color=(0, 0, 0, 0),
                opacity=0.01
            )
            slot_btn.bind(on_release=lambda instance, idx=i: self.toggle_slot(idx))

            self.slot_buttons.append(slot_btn)
            self.layout.add_widget(slot_btn)

        # ✅ ИЗМЕНЕНО: Вместо кнопки LOAD - изображение
        self.create_close_image()

    def create_close_image(self):
        """Создает изображение для закрытия модального окна"""

        # Путь к изображению (измените на ваш файл)
        close_image_path = 'assets/images/guns/load_button.png'

        # Проверяем существование файла
        if os.path.exists(close_image_path):
            # Создаем изображение с поведением кнопки
            class ImageButton(ButtonBehavior, KivyImage):
                pass

            close_btn = ImageButton(
                source=close_image_path,
                size_hint=(None, None),
                size=(200, 200),  # Размер под ваш дизайн
                pos_hint={'center_x': 0.5, 'y': 0.05},
                allow_stretch=True,
                keep_ratio=True
            )
        else:
            # Если файл не найден, создаем текстовую кнопку как запасной вариант
            print(f"⚠️ Файл {close_image_path} не найден, использую текстовую кнопку")
            close_btn = Button(
                text='ЗАКРЫТЬ',
                font_size='20sp',
                bold=True,
                size_hint=(None, None),
                size=(150, 60),
                pos_hint={'center_x': 0.5, 'y': 0.05},
                background_color=(0.3, 0.3, 0.3, 0.8),
                background_normal='',
                color=(1, 1, 1, 1)
            )

        # Привязываем закрытие с звуком
        close_btn.bind(on_release=self.close_modal_with_sound)
        self.layout.add_widget(close_btn)

    def toggle_slot(self, slot_index):
        """Переключает патрон в слоте"""
        bullet = self.bullet_sprites[slot_index]
        new_state = not bullet.is_loaded
        bullet.set_loaded(new_state)

        # Воспроизводим звук зарядки/разрядки через главный экран
        if hasattr(self.main_screen, 'play_bullet_load_sound'):
            self.main_screen.play_bullet_load_sound()

        # Визуальная обратная связь
        btn = self.slot_buttons[slot_index]
        original_color = btn.background_color
        btn.background_color = (1, 1, 1, 0.2)
        Clock.schedule_once(lambda dt: self.reset_button_color(btn, original_color), 0.1)

    def reset_button_color(self, btn, original_color):
        """Сбрасывает цвет кнопки"""
        btn.background_color = original_color

    def close_modal(self, instance):
        """Закрывает модальное окно и обновляет основной экран"""
        # Переносим состояние в основной экран
        for i, bullet in enumerate(self.bullet_sprites):
            if i < len(self.main_screen.bullet_slots):
                self.main_screen.bullet_slots[i].has_bullet = bullet.is_loaded
                self.main_screen.bullet_slots[i].update_appearance()

        # Обновляем счетчик патронов
        self.main_screen.total_bullets = sum(1 for s in self.main_screen.bullet_slots if s.has_bullet)
        self.main_screen.update_bullet_counter()

        self.dismiss()

    def close_modal_with_sound(self, instance):
        """Закрывает модальное окно с воспроизведением звука"""
        # Воспроизводим звук через главный экран
        if hasattr(self.main_screen, 'play_chamber_sound'):
            self.main_screen.play_chamber_sound()

        # Вызываем существующий метод close_modal для закрытия и обновления
        self.close_modal(instance)

    def update_bg(self, instance, value):
        """Обновляет фон"""
        pass  # Фон больше не нужен

class RusRouletteScreen(BaseGameScreen):
    """Реалистичная русская рулетка с жестовым управлением"""

    background_image = 'assets/backgrounds/rus_roulette_bg_1024x1024.jpg'

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

        # НОВОЕ: прямоугольник для анимации барабана
        self.chamber_highlight = None

        # SoundManager для управления фоновой музыкой
        self.sound_manager = SoundManager()

        # Звуки
        self.chamber_sound = None
        self.gun_shot_sound = None  # Звук выстрела
        self.misfire_sound = None  # Звук осечки
        self.bullet_load_sound = None  # Звук зарядки/разрядки патрона
        self.revolve_sound = None
        self.bind(size=self._update_positions)

    def play_revolve_sound(self):
        """Воспроизводит звук вращения барабана"""
        try:
            if not self.revolve_sound:
                self.revolve_sound = SoundLoader.load('assets/sounds/Roulette/revolve.ogg')
                if not self.revolve_sound:
                    print("Не удалось загрузить звук: assets/sounds/Roulette/revolve.ogg")
                    return

            if self.revolve_sound:
                if self.revolve_sound.state == 'play':
                    self.revolve_sound.stop()
                self.revolve_sound.play()
        except Exception as e:
            print(f"Ошибка при воспроизведении звука вращения: {e}")


    def play_bullet_load_sound(self):
        """Воспроизводит звук зарядки/разрядки патрона"""
        try:
            if not self.bullet_load_sound:
                self.bullet_load_sound = SoundLoader.load('assets/sounds/Roulette/bullet_load.ogg')
                if not self.bullet_load_sound:
                    print("Не удалось загрузить звук: assets/sounds/Roulette/bullet_load.ogg")
                    return

            if self.bullet_load_sound:
                if self.bullet_load_sound.state == 'play':
                    self.bullet_load_sound.stop()
                self.bullet_load_sound.play()
        except Exception as e:
            print(f"Ошибка при воспроизведении звука зарядки: {e}")

    def play_chamber_sound(self):
        """Воспроизводит звук открытия барабана"""
        try:
            if not self.chamber_sound:
                self.chamber_sound = SoundLoader.load('assets/sounds/Roulette/chamber_out.ogg')

            if self.chamber_sound:
                if self.chamber_sound.state == 'play':
                    self.chamber_sound.stop()
                self.chamber_sound.play()
        except Exception as e:
            print(f"Ошибка при воспроизведении звука: {e}")

    def on_enter(self):
        """При входе на экран"""
        # Убавляем фоновую музыку до 5% за 1 секунду
        self.sound_manager.fade_to(0.05, duration=1.0)

        # Сбрасываем игру при входе
        self.start_game()

    def create_game_screen(self, dt=None):
        """Создает игровой экран"""
        # Очищаем layout
        self.layout.clear_widgets()

        # Восстанавливаем фон и кнопку назад
        super().on_enter()

        # Сначала создаем пистолет (нижний слой)
        self.create_gun()

        self.create_back_button()

        # Затем барабанные слоты (для хранения состояния)
        self.create_bullet_chamber()

        # Затем информационные надписи (средний слой)
        self.create_info_labels()

        # НОВОЕ: создаем прямоугольник для анимации барабана (поверх пистолета)
        self.create_chamber_highlight()

        # Иконка патрона должна быть ПОСЛЕДНЕЙ (верхний слой)
        self.create_bullet_icon()

        # Инициализируем все слоты как пустые
        self.initialize_empty_chamber()

        # Обновляем состояние
        self.update_bullet_counter()
        self.update_current_slot()

    def create_chamber_highlight(self):
        """Создает прямоугольник для анимации барабана"""
        from kivy.uix.widget import Widget
        from kivy.graphics import Color, Rectangle

        self.chamber_highlight = Widget()
        self.chamber_highlight.size_hint = (None, None)
        self.chamber_highlight.size = (110, 117)  # РАЗМЕР ПРЯМОУГОЛЬНИКА

        # Позиция по умолчанию - центр пистолета
        self.chamber_highlight.pos = (Window.width * 0.54, Window.height * 0.47)  # ПОЗИЦИЯ

        # Рисуем прямоугольник с прозрачностью
        with self.chamber_highlight.canvas:
            Color(0.1, 0.1, 0.1, 0.5)  # Серый
            self.highlight_rect = Rectangle(
                pos=self.chamber_highlight.pos,
                size=self.chamber_highlight.size
            )

        # По умолчанию скрыт
        self.chamber_highlight.opacity = 0
        self.layout.add_widget(self.chamber_highlight)

    def spin_chamber(self):
        """Вращение барабана (вызывается при свайпе)"""
        # Воспроизводим звук вращения
        self.play_revolve_sound()

        # Сохраняем старую позицию для анимации
        old_slot = self.current_slot
        self.current_slot = random.randint(0, 5)
        self.animate_chamber_highlight()

    def animate_chamber_highlight(self):
        """Анимация прямоугольника барабана (мерцание)"""
        if not self.chamber_highlight:
            return

        # Сначала убеждаемся, что пистолет НЕ анимируется
        if hasattr(self, 'gun_image') and self.gun_image:
            # Отменяем все текущие анимации пистолета
            Animation.cancel_all(self.gun_image)
            # Возвращаем нормальную прозрачность
            self.gun_image.opacity = 1

        # Показываем прямоугольник
        self.chamber_highlight.opacity = 1

        # МЕДЛЕННОЕ МЕРЦАНИЕ - увеличиваем duration
        anim = Animation(opacity=0.2, duration=0.1) + Animation(opacity=0.9, duration=0.1)
        anim.repeat = True
        anim.start(self.chamber_highlight)

        # УВЕЛИЧИВАЕМ ПРОДОЛЖИТЕЛЬНОСТЬ
        Clock.schedule_once(lambda dt: self.stop_chamber_animation(anim), 0.5)

    def stop_chamber_animation(self, anim):
        """Останавливает анимацию барабана"""
        if self.chamber_highlight:
            anim.stop(self.chamber_highlight)
            self.chamber_highlight.opacity = 0  # Скрываем прямоугольник
        self.finish_spin(0)

    def finish_spin(self, dt):
        """Завершение вращения"""
        self.result_label.color = (1, 1, 1, 1)
        self.update_current_slot()

    def initialize_empty_chamber(self):
        """Инициализирует все слоты как пустые"""
        for slot in self.bullet_slots:
            slot.has_bullet = False
            slot.update_appearance()

        # Устанавливаем текущий слот (первый)
        self.current_slot = 0
        self.total_bullets = 0

    def create_bullet_icon(self):
        """Создает иконку патрона в правом верхнем углу"""
        if self.bullet_icon:
            self.layout.remove_widget(self.bullet_icon)

        self.bullet_icon = BulletIcon(
            pos_hint={'right': 0.95, 'top': 0.95}
        )
        self.bullet_icon.bind(on_release=self.show_chamber_modal)
        self.layout.add_widget(self.bullet_icon)

    def create_gun(self):
        """Создает изображение пистолета с жестовым управлением"""
        if self.gun_image:
            self.layout.remove_widget(self.gun_image)

        try:
            self.gun_image = KivyImage(
                source='assets/images/guns/revolver.png',
                size_hint=(1, 1),  # На весь экран
                pos_hint={'center_x': 0.5, 'center_y': 0.5},
                allow_stretch=True,
                keep_ratio=True  # Сохраняем пропорции
            )
        except:
            # Заглушка если нет изображения
            self.gun_image = Button(
                text='🔫\n(Жестовое управление)\nВесь экран',
                font_size='20sp',
                size_hint=(1, 1),
                pos_hint={'center_x': 0.5, 'center_y': 0.5},
                background_color=(0.3, 0.3, 0.3, 1),
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
        """Создает барабан с 6 слотами для патронов"""
        # Удаляем старые слоты
        for slot in self.bullet_slots:
            self.layout.remove_widget(slot)
        self.bullet_slots = []

        # СОЗДАЕМ 6 СЛОТОВ (невидимых, для хранения состояния)
        for i in range(6):
            slot = BulletSlot(
                slot_number=i,
                size_hint=(None, None),
                size=(1, 1),  # Крошечные, невидимые
                pos=(-100, -100),  # За экраном
                opacity=0  # Полностью прозрачные
            )
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
            pos_hint={'center_x': 0.5, 'top': 1},
            size_hint=(None, None),
            size=(450, 50)
        )
        self.layout.add_widget(title)

        # ВЕРНУЛИ result_label - он нужен для отображения состояния!
        self.result_label = Label(
            text='',
            font_size='14sp',
            color=(1, 1, 1, 1),
            halign='center',
            pos_hint={'center_x': 0.5, 'top': 0.85},
            size_hint=(None, None),
            size=(500, 60)
        )
        self.layout.add_widget(self.result_label)

    def update_current_slot(self):
        """Обновляет подсветку текущего слота"""
        for i, slot in enumerate(self.bullet_slots):
            slot.set_current(i == self.current_slot)

    def play_gun_shot_sound(self):
        """Воспроизводит звук выстрела"""
        try:
            if not self.gun_shot_sound:
                self.gun_shot_sound = SoundLoader.load('assets/sounds/Roulette/gun_shot.ogg')
                if not self.gun_shot_sound:
                    print("Не удалось загрузить звук: assets/sounds/Roulette/gun_shot.ogg")
                    return

            if self.gun_shot_sound:
                if self.gun_shot_sound.state == 'play':
                    self.gun_shot_sound.stop()
                self.gun_shot_sound.play()
        except Exception as e:
            print(f"Ошибка при воспроизведении звука выстрела: {e}")

    def play_misfire_sound(self):
        """Воспроизводит звук осечки"""
        try:
            if not self.misfire_sound:
                self.misfire_sound = SoundLoader.load('assets/sounds/Roulette/misfire.ogg')
                if not self.misfire_sound:
                    print("Не удалось загрузить звук: assets/sounds/Roulette/misfire.ogg")
                    return

            if self.misfire_sound:
                if self.misfire_sound.state == 'play':
                    self.misfire_sound.stop()
                self.misfire_sound.play()
        except Exception as e:
            print(f"Ошибка при воспроизведении звука осечки: {e}")

    def check_shot_result(self):
        """Проверяет результат выстрела"""
        # Проверяем, что есть слоты
        if not self.bullet_slots or self.current_slot >= len(self.bullet_slots):
            # Если слотов нет, просто показываем сообщение
            self.result_label.text = 'Ошибка: нет данных о патронах'
            self.result_label.color = (1, 0, 0, 1)
            Clock.schedule_once(self.reset_result_text, 2.0)
            return

        current_slot = self.bullet_slots[self.current_slot]

        if current_slot.has_bullet:
            # Анимация отдачи (звук уже воспроизведен в pull_trigger)
            anim = Animation(pos_hint={'center_x': 0.52, 'center_y': 0.55}, duration=0.1)
            anim += Animation(pos_hint={'center_x': 0.5, 'center_y': 0.55}, duration=0.1)
            anim.start(self.gun_image)

            # Убираем патрон
            current_slot.has_bullet = False
            current_slot.update_appearance()
            self.total_bullets -= 1
            self.update_bullet_counter()

        self.shots_fired += 1
        self.current_slot = (self.current_slot + 1) % 6

        self.update_bullet_counter()

        # Нормализуем вращение
        self.gun_rotation = self.gun_rotation % 360
        self.gun_image.rotation = 0

        self.update_current_slot()

    def show_chamber_modal(self, instance):
        """Показывает модальное окно барабана для зарядки"""
        # Воспроизводим звук открытия барабана
        self.play_chamber_sound()  # Звук при открытии

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

        # === ЗОНА КУРКА (центр-вниз) ===
        trigger_zone = (
            gun_pos[0] + gun_size[0] * 0.1,  # 30% слева
            gun_pos[1] + gun_size[1] * 0.05,  # 5% сверху (внизу)
            gun_size[0] * 1,  # 90% ширины
            gun_size[1] * 0.4  # 30% высоты
        )

        # === ЗОНА БАРАБАНА (весь центр) ===
        chamber_zone = (
            gun_pos[0] + gun_size[0] * 0.1,  # 10% слева
            gun_pos[1] + gun_size[1] * 0.3,  # 30% сверху
            gun_size[0] * 0.8,  # 80% ширины
            gun_size[1] * 0.4  # 40% высоты
        )

        # Проверяем, в какой зоне касание
        tx, ty = touch.pos

        # Если тап по курку (центр-вниз)
        if (trigger_zone[0] <= tx <= trigger_zone[0] + trigger_zone[2] and
                trigger_zone[1] <= ty <= trigger_zone[1] + trigger_zone[3]):
            self.pull_trigger()
            return True

        # Если касание в зоне барабана (весь центр)
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

    def pull_trigger(self):
        """Спуск курка (вызывается при тапе по курку)"""
        current_slot = self.bullet_slots[self.current_slot]

        if current_slot.has_bullet:
            # ЗАРЯЖЕН - звук выстрела
            self.play_gun_shot_sound()

            # ДВОЙНАЯ ТРЯСКА (0.4 сек)
            anim = Animation(pos_hint={'center_x': 0.52, 'center_y': 0.53}, duration=0.05)
            anim += Animation(pos_hint={'center_x': 0.48, 'center_y': 0.57}, duration=0.05)
            anim += Animation(pos_hint={'center_x': 0.52, 'center_y': 0.53}, duration=0.05)
            anim += Animation(pos_hint={'center_x': 0.48, 'center_y': 0.57}, duration=0.05)
            anim += Animation(pos_hint={'center_x': 0.5, 'center_y': 0.55}, duration=0.05)
            anim.start(self.gun_image)
            Clock.schedule_once(lambda dt: self.check_shot_result(), 0.3)
        else:
            # ПУСТОЙ - звук осечки
            self.play_misfire_sound()

            # МИНИМАЛЬНАЯ ТРЯСКА (0.15 сек)
            anim = Animation(pos_hint={'center_x': 0.51, 'center_y': 0.51}, duration=0.03)
            anim += Animation(pos_hint={'center_x': 0.49, 'center_y': 0.5}, duration=0.03)
            anim += Animation(pos_hint={'center_x': 0.5, 'center_y': 0.49}, duration=0.03)
            anim.start(self.gun_image)
            Clock.schedule_once(lambda dt: self.check_shot_result(), 0.15)

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

        # НОВОЕ: обновляем позицию прямоугольника при изменении размера окна
        if self.chamber_highlight:
            # Автоматически подстраиваем позицию под размер окна
            self.chamber_highlight.pos = (Window.width * 0.43, Window.height * 0.45)
            if hasattr(self, 'highlight_rect'):
                self.highlight_rect.pos = self.chamber_highlight.pos

        if self.bullet_slots:
            Clock.schedule_once(lambda dt: self.create_bullet_chamber(), 0.1)

    def on_leave(self):
        """При выходе с экрана"""
        # Возвращаем громкость фоновой музыки до 100%
        self.sound_manager.fade_to(1.0, duration=0.5)

        # Очищаем звуки
        if hasattr(self, 'chamber_sound') and self.chamber_sound:
            self.chamber_sound.stop()
            self.chamber_sound = None

        if hasattr(self, 'gun_shot_sound') and self.gun_shot_sound:
            self.gun_shot_sound.stop()
            self.gun_shot_sound = None

        if hasattr(self, 'misfire_sound') and self.misfire_sound:
            self.misfire_sound.stop()
            self.misfire_sound = None

        if hasattr(self, 'bullet_load_sound') and self.bullet_load_sound:
            self.bullet_load_sound.stop()
            self.bullet_load_sound = None

        if hasattr(self, 'revolve_sound') and self.revolve_sound:
            self.revolve_sound.stop()
            self.revolve_sound = None

        # Вызываем родительский метод
        super().on_leave()

    def go_to_menu(self):
        """Возврат в меню с восстановлением громкости"""
        # Возвращаем громкость фоновой музыки до 100%
        self.sound_manager.fade_to(1.0, duration=0.5)

        # Вызываем родительский метод для перехода
        super().go_to_menu()