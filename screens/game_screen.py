import random

from kivy.uix.screenmanager import Screen
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.label import Label
from kivy.clock import Clock
from kivy.animation import Animation
from kivy.properties import StringProperty, NumericProperty
from kivy.vector import Vector
from components.ball_physics import BallPhysics
from components.sprite_sheet_ball import SpriteSheetBall


class GameScreen(Screen):
    # Основные свойства
    sprite_sheet_path = StringProperty('')  # Путь к спрайт-листу
    background_image = StringProperty('')
    sound_file = StringProperty('')
    ball_size = NumericProperty(100)

    ball_type = StringProperty('soccer')  # Тип мяча для физики

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.layout = FloatLayout()

        # Основные компоненты
        self.ball_widget = None
        self.ball_physics = None
        self.sound = None

        # Состояние
        self.touch_start_pos = None
        self.is_physics_enabled = False
        self.total_distance_traveled = 0  # Общее пройденное расстояние

        # Графика
        self.bg_image = None

        # Таймеры
        self.physics_clock = None
        self.animation_clock = None

        # Добавляем layout
        self.add_widget(self.layout)

        # Кнопка назад
        self.back_button = None

        # Привязываем обновление размеров
        self.bind(size=self._on_size_change)

        self.stop_effect = None
        self.show_stop_effect = True  # Флаг для включения/выключения

    def _on_size_change(self, instance, value):
        """Обновляет позицию мяча при изменении размера экрана"""
        if self.ball_widget and self.ball_physics:
            center_x = self.layout.width / 2
            center_y = self.layout.height / 2

            self.ball_widget.pos = (
                center_x - self.ball_size / 2,
                center_y - self.ball_size / 2
            )

            self.ball_physics.pos = Vector(center_x, center_y)

    def on_enter(self):
        """При входе на экран"""
        self.setup_background()
        self.setup_ui()
        self.start_physics_update()
        self.start_animation_update()

        self.back_button = self.create_back_button()
        self.layout.add_widget(self.back_button)
        self.checking_stop = False  # Флаг проверки остановки


    def create_back_button(self):
        """Создает кнопку возврата в меню с картинкой"""
        from kivy.uix.behaviors import ButtonBehavior
        from kivy.uix.image import Image as KivyImage

        class ImageButton(ButtonBehavior, KivyImage):
            pass

        back_btn = ImageButton(
            source='assets/images/buttons/Orange_back_to_menu_button.png',  # Укажите путь к вашей картинке
            size_hint=(None, None),
            size=(60, 60),  # Размер кнопки
            pos_hint={'x': 0.09, 'y': 0.055},
            allow_stretch=True
        )

        # Анимация при нажатии
        def on_press(instance):
            Animation(opacity=0.7, duration=0.1).start(instance)

        def on_release(instance):
            Animation(opacity=1.0, duration=0.1).start(instance)
            Clock.schedule_once(lambda dt: self.go_to_menu(instance), 0.1)

        back_btn.bind(on_press=on_press)
        back_btn.bind(on_release=on_release)

        return back_btn

    def start_physics_update(self):
        if self.physics_clock:
            self.physics_clock.cancel()
        self.physics_clock = Clock.schedule_interval(self.update_physics, 1 / 60.0)

    def start_animation_update(self):
        """Запускает обновление анимации"""
        if self.animation_clock:
            self.animation_clock.cancel()
        self.animation_clock = Clock.schedule_interval(self.update_animation, 1 / 30.0)  # 30 FPS для анимации

    def update_physics(self, dt):
        """Обновляет физику мяча"""
        if self.ball_physics and self.is_physics_enabled:
            # Сохраняем старую позицию для вычисления пройденного расстояния
            old_pos = Vector(self.ball_physics.pos)

            # Обновляем физику
            self.ball_physics.update(dt, self.layout.width, self.layout.height)

            # Вычисляем пройденное расстояние
            distance = (self.ball_physics.pos - old_pos).length()
            self.total_distance_traveled += distance

            # Обновляем позицию спрайта
            if self.ball_widget:
                self.ball_widget.pos = (
                    self.ball_physics.pos.x - self.ball_physics.radius,
                    self.ball_physics.pos.y - self.ball_physics.radius
                )

                # Передаем скорость в спрайт для анимации
                self.ball_widget.velocity = [
                    self.ball_physics.velocity.x,
                    self.ball_physics.velocity.y
                ]

            # Останавливаем физику, если мяч почти остановился
            if self.ball_physics.velocity.length() < 0.5:
                self.is_physics_enabled = False
                if self.show_stop_effect and not self.checking_stop:
                    self.checking_stop = True
                    Clock.schedule_once(self.trigger_stop_effect, 0.5)
                self.total_distance_traveled = 0

    def trigger_stop_effect(self, dt):
        """Запуск эффекта остановки с задержкой"""
        if (self.ball_physics and
                self.ball_physics.velocity.length() < 0.5 and
                self.ball_widget):

            print("🎯 Мяч остановился, запускаю эффект!")

            # Создаём эффект если ещё нет
            if not self.stop_effect:
                from components.stop_effect import BallStopEffect
                self.stop_effect = BallStopEffect(
                    ball_size=self.ball_size,
                    ball_color=[1, 1, 1, 1]
                )
                self.layout.add_widget(self.stop_effect)

            # Центр мяча
            center_x = self.ball_widget.center_x
            center_y = self.ball_widget.center_y

            # Случайное сообщение
            messages = [
                "ДА",
                "НЕТ",
                "ПОПРОБУЙ ЕЩЕ РАЗ",
                "ПОДУМАЙ ДВАЖДЫ",
                "СОМНЕВАЕШСЯ? НЕ ДЕЛАЙ!",
                "ВЫБЕРИ ДРУШУЮ СТОРОНУ"
            ]
            message = random.choice(messages)

            # Запускаем эффект
            self.stop_effect.play(center_x, center_y, message)

        self.checking_stop = False

    def update_animation(self, dt):
        """Анимация, привязанная к скорости"""
        if self.ball_widget and self.ball_physics:
            speed = self.ball_physics.velocity.length()

            # Если мяч движется - анимируем
            if speed > 0.1:
                # Чем быстрее мяч, тем быстрее анимация
                animation_speed = min(2.0, speed / 30)  # Коэффициент

                # Увеличиваем счётчик кадров в зависимости от скорости
                self.animation_counter += animation_speed

                # Вычисляем кадр
                total_frames = self.ball_widget.rows * self.ball_widget.cols
                frame_index = int(self.animation_counter) % total_frames

                self.ball_widget.frame_index = frame_index

                # Определяем направление вращения
                if self.ball_physics.velocity.x < 0:  # Движение влево
                    self.ball_widget.frame_index = total_frames - frame_index - 1
            else:
                # Мяч остановился - статичный кадр
                self.ball_widget.frame_index = 0
                self.animation_counter = 0

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

    def setup_ui(self):
        """Настраивает пользовательский интерфейс"""
        # Очищаем старые элементы, кроме фона
        for child in self.layout.children[:]:
            if child not in [self.bg_image, self.ball_widget, self.back_button]:
                self.layout.remove_widget(child)

        # Создаем мяч из спрайт-листа
        self.create_sprite_sheet_ball()

        # Добавляем инструкцию
        instruction = Label(
            text='Проведите пальцем по мячу для броска',
            font_size='14sp',
            color=(1, 1, 1, 0.8),
            size_hint=(None, None),
            size=(300, 30),
            pos_hint={'center_x': 0.5, 'top': 0.85}
        )
        self.layout.add_widget(instruction)

    def create_sprite_sheet_ball(self):
        """Создает мяч из спрайт-листа - ПОЛНАЯ ВЕРСИЯ"""
        import os

        print(f"\n=== GameScreen.create_sprite_sheet_ball() ===")
        print(f"Имя экрана: {self.name}")
        print(f"Текущий sprite_sheet_path: '{self.sprite_sheet_path}'")
        print(f"Тип self: {type(self).__name__}")

        # Проверяем путь
        if not self.sprite_sheet_path:
            print(f"❌ ОШИБКА: sprite_sheet_path пустой!")
            print(f"   self имеет sprite_sheet_path? {hasattr(self, 'sprite_sheet_path')}")
            return

        if not os.path.exists(self.sprite_sheet_path):
            print(f"❌ ОШИБКА: Файл не существует! '{self.sprite_sheet_path}'")
            # Попробуем найти файл
            current_dir = os.path.dirname(os.path.abspath(__file__))
            absolute_path = os.path.join(current_dir, self.sprite_sheet_path)
            print(f"   Абсолютный путь: {absolute_path}")
            print(f"   Существует? {os.path.exists(absolute_path)}")
            return

        print(f"✅ Путь корректен, создаю мяч...")

        # Удаляем старый мяч если есть
        if self.ball_widget:
            self.layout.remove_widget(self.ball_widget)
            print(f"   Удалил старый мяч")

        center_x = self.layout.width / 2
        center_y = self.layout.height / 2

        print(f"   Центр экрана: ({center_x}, {center_y})")
        print(f"   Размер мяча: {self.ball_size}")
        print(f"   Позиция мяча: ({center_x - self.ball_size / 2}, {center_y - self.ball_size / 2})")

        # СОЗДАЕМ МЯЧ - ЭТОГО КОДА НЕ БЫЛО!
        self.ball_widget = SpriteSheetBall(
            sprite_sheet_path=self.sprite_sheet_path,
            ball_size=self.ball_size,
            rows=8,  # 8 строк в спрайт-листе
            cols=8,  # 8 столбцов в спрайт-листе
            size_hint=(None, None),
            size=(self.ball_size, self.ball_size),
            pos=(center_x - self.ball_size / 2, center_y - self.ball_size / 2)
        )

        print(f"   SpriteSheetBall создан: {self.ball_widget}")

        # ДОБАВЛЯЕМ НА ЭКРАН
        self.layout.add_widget(self.ball_widget)
        print(f"   Мяч добавлен в layout")
        print(f"   Всего детей в layout: {len(self.layout.children)}")

        # Создаем физику мяча
        self.ball_physics = BallPhysics(
            pos=(center_x, center_y),
            size=self.ball_size,
            sound_callback=self.play_bounce_sound,
            ball_type=self.ball_type
        )
        print(f"   Физика создана")

        # Сбрасываем пройденное расстояние
        self.total_distance_traveled = 0

        print(f"✅ Мяч успешно создан и добавлен на экран!\n")

        # После создания мяча:
        print(f"\nZ-порядок в layout:")
        for i, child in enumerate(self.layout.children):
            print(f"  {i}. {type(child).__name__} - pos: {child.pos}, size: {child.size}")

        # Убедимся что мяч поверх фона
        self.ball_widget.opacity = 1.0
        self.bg_image.opacity = 1.0  # Фон не должен быть поверх мяча
    # def create_ball(self):
    #     if self.ball_widget:
    #         self.layout.remove_widget(self.ball_widget)
    #
    #     center_x = self.layout.width / 2
    #     center_y = self.layout.height / 2

    def on_touch_down(self, touch):
        if self.ball_widget and self.ball_widget.collide_point(*touch.pos):
            self.touch_start_pos = touch.pos
            self.play_bounce_sound()
            touch.grab(self)
            return True
        return super().on_touch_down(touch)

    def on_touch_move(self, touch):
        if touch.grab_current is self:
            return True
        return super().on_touch_move(touch)

    def on_touch_up(self, touch):
        if touch.grab_current is self:
            if self.touch_start_pos:
                start = Vector(self.touch_start_pos)
                end = Vector(touch.pos)
                force = (end - start) * 0.3

                self.ball_physics.apply_force(force)
                self.is_physics_enabled = True
                self.play_bounce_sound()
                self.touch_start_pos = None
            touch.ungrab(self)
            return True
        return super().on_touch_up(touch)

    def play_bounce_sound(self):
        if self.sound:
            self.sound.stop()
            self.sound.volume = 1.2
            self.sound.play()
            Clock.schedule_once(lambda dt: setattr(self.sound, 'volume', 1.0) if self.sound else None, 0.1)

    def go_to_menu(self, instance):
        self.remove_ball()
        if self.physics_clock:
            self.physics_clock.cancel()
            self.physics_clock = None
        self.manager.current = 'menu'

    def remove_ball(self):
        if self.ball_widget:
            self.layout.remove_widget(self.ball_widget)
            self.ball_widget = None
            self.ball_physics = None
            self.is_physics_enabled = False
            self.touch_start_pos = None

            # Убираем эффект если есть
            if self.stop_effect and self.stop_effect.parent:
                self.layout.remove_widget(self.stop_effect)
                self.stop_effect = None

    def remove_panel(self):
        print(self.layout.children)



    def start_game(self):
        if self.ball_widget and self.ball_physics:
            self.ball_physics.velocity = Vector(0, 0)
            self.is_physics_enabled = False
            (Animation(
                size=(self.ball_size * 1.1, self.ball_size * 1.1),
                duration=0.1
            ) + Animation(
                size=(self.ball_size, self.ball_size),
                duration=0.1
            )).start(self.ball_widget)
