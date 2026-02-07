from kivy.uix.widget import Widget
from kivy.graphics import *
from kivy.animation import Animation
from kivy.clock import Clock
from kivy.properties import NumericProperty, ListProperty
import random
import math
from kivy.uix.image import Image


class BallStopEffect(Widget):
    """Эффект разрыва мяча и облака пыли при остановке"""

    # Свойства
    ball_size = NumericProperty(100)
    ball_color = ListProperty([1, 1, 1, 1])
    effect_duration = NumericProperty(3.0)  # Общая длительность эффекта

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        # Состояние
        self.is_playing = False
        self.fragments = []  # Фрагменты мяча
        self.dust_particles = []  # Частицы пыли
        self.text_label = None

        # Визуальные настройки
        self.fragment_count = 8  # Сколько фрагментов
        self.dust_count = 20  # Частиц пыли
        self.fragment_colors = []  # Цвета фрагментов

        # Создаём цвета фрагментов (для футбольного мяча)
        self.setup_football_colors()

        # Запускаем обновление для частиц пыли
        Clock.schedule_interval(self.update, 1/60.0)

    def setup_football_colors(self):
        """Цвета для футбольного мяча (чёрно-белые)"""
        self.fragment_colors = []
        for i in range(self.fragment_count):
            if i % 2 == 0:
                self.fragment_colors.append([0, 0, 0, 1])  # Чёрный
            else:
                self.fragment_colors.append([1, 1, 1, 1])  # Белый

    def play(self, ball_center_x, ball_center_y, message="Отличный бросок!"):
        """Запуск эффекта остановки"""
        if self.is_playing:
            return  # Уже играем

        self.is_playing = True
        self.center_x = ball_center_x
        self.center_y = ball_center_y

        print(f"💥 Запуск эффекта остановки в ({ball_center_x}, {ball_center_y})")

        # Очищаем старые элементы
        self.clear_effect()

        # 1. Создаём фрагменты мяча
        self.create_fragments()

        # 2. Создаём облако пыли
        self.create_dust_cloud()

        # 3. Создаём текстовое сообщение
        self.create_message(message)

        # Запускаем анимацию
        self.start_animation()

    def create_fragments(self):
        """Создание фрагментов мяча"""
        print(f"🔸 Создаю {self.fragment_count} фрагментов")

        self.fragments = []
        for i in range(self.fragment_count):
            # Пытаемся загрузить изображение осколка
            try:
                # Создаем виджет фрагмента с альфа-каналом
                fragment = Image(
                    source=f'assets/sprites/splinters/{random.randint(1, 7)}.png',
                    size=(20, 20),  # Размер как указано
                    pos=(self.center_x - 10, self.center_y - 10),  # Центрируем (-10 это половина от 20)
                    opacity=1,
                    allow_stretch=True,
                    keep_ratio=False
                )
                print(f"   Фрагмент {i}: создан с изображением")
            except Exception as e:
                print(f"   Ошибка загрузки изображения осколка: {e}")
                # Создаем простой цветной прямоугольник в качестве запасного варианта
                from kivy.uix.label import Label
                fragment = Label(
                    text="●",  # Простой кружок
                    font_size='20sp',
                    size=(20, 20),
                    pos=(self.center_x - 10, self.center_y - 10),
                    color=random.choice([(0, 0, 0, 1), (1, 1, 1, 1)]),
                    opacity=1
                )
                print(f"   Фрагмент {i}: создан как цветной кружок")

            # Добавляем на экран
            self.parent.add_widget(fragment)

            # Сохраняем информацию о фрагменте
            fragment_data = {
                'widget': fragment,
                'original_pos': (self.center_x - 10, self.center_y - 10),
                'animation': None
            }
            self.fragments.append(fragment_data)

    def create_dust_cloud(self):
        """Создаёт частицы пыли"""
        print(f"🌫️ Создаю {self.dust_count} частиц пыли")

        for i in range(self.dust_count):
            particle = {
                'pos': [0, 0],  # Начало в центре
                'size': random.uniform(3, 8),
                'color': [0.7, 0.7, 0.7, random.uniform(0.3, 0.7)],  # Серый
                'velocity': [
                    random.uniform(-2, 2),  # Уменьшил скорость в 50 раз
                    random.uniform(1, 3)    # Уменьшил скорость в 50 раз
                ],
                'life': 1.0,  # Время жизни (1 = 100%)
                'rotation': random.uniform(0, 360),
                'rotation_speed': random.uniform(-180, 180)
            }

            self.dust_particles.append(particle)

    def create_message(self, text):
        """Создаёт текстовое сообщение"""
        from kivy.uix.label import Label

        self.text_label = Label(
            text=text,
            font_size='18sp',
            bold=True,
            color=(1, 1, 1, 0),  # Начинаем прозрачным
            outline_color=(0, 0, 0, 1),
            outline_width=2,
            size_hint=(None, None),
            size=(300, 40),
            pos=(self.center_x - 150, self.center_y + 50)
        )

        self.add_widget(self.text_label)
        print(f"💬 Текст: '{text}'")

    def clear_effect(self):
        """Очистка предыдущего эффекта"""
        # Удаляем все фрагменты из родительского виджета
        for fragment_data in self.fragments:
            fragment_widget = fragment_data.get('widget')
            if fragment_widget and fragment_widget.parent:
                fragment_widget.parent.remove_widget(fragment_widget)

        self.fragments.clear()
        self.dust_particles.clear()

        if self.text_label and self.text_label.parent:
            self.remove_widget(self.text_label)
        self.text_label = None

        # Очищаем canvas
        self.canvas.clear()

    def start_animation(self):
        """Запуск анимации эффекта"""
        print("🎬 Запуск анимации...")

        # Разделим анимацию на фазы
        Clock.schedule_once(self.phase1_implosion, 0.0)  # Фаза 1: Сжатие
        Clock.schedule_once(self.phase2_explosion, 0.2)  # Фаза 2: Взрыв
        Clock.schedule_once(self.phase3_dust_text, 0.5)  # Фаза 3: Пыль + текст
        Clock.schedule_once(self.phase4_assemble, 2.0)  # Фаза 4: Сборка
        Clock.schedule_once(self.phase5_complete, 3.0)  # Фаза 5: Завершение

    def phase1_implosion(self, dt):
        """Фаза 1: Сжатие мяча перед взрывом"""
        print("⚪ Фаза 1: Сжатие")
        # Пока просто ждём, в реальности можно анимировать

    def phase2_explosion(self, dt):
        """Фаза 2: Взрыв фрагментов"""
        print("💥 Фаза 2: Взрыв!")

        # Запускаем анимацию для каждого фрагмента
        for fragment_data in self.fragments:
            # Получаем виджет фрагмента
            fragment_widget = fragment_data.get('widget')
            if not fragment_widget:
                continue

            # Случайное направление и расстояние (уменьшил для ограничения области)
            angle = random.uniform(0, 2 * math.pi)
            distance = random.uniform(30, 80)  # Уменьшил расстояние

            # Конечная позиция относительно центра эффекта
            end_x = self.center_x + math.cos(angle) * distance - 10  # -10 для центрирования
            end_y = self.center_y + math.sin(angle) * distance - 10  # -10 для центрирования

            print(f"   Фрагмент летит на расстояние: {distance:.1f} пикселей")

            # Анимация движения
            anim_pos = Animation(
                x=end_x,
                y=end_y,
                duration=0.8,
                t='out_quad'
            )

            # Анимация прозрачности
            anim_opacity = Animation(
                opacity=0,
                duration=0.8,
                t='in_quad'
            )

            # Запускаем обе анимации
            anim_pos.start(fragment_widget)
            anim_opacity.start(fragment_widget)

            # Сохраняем ссылку на анимацию для возможности отмены
            fragment_data['animation'] = anim_pos

    def phase3_dust_text(self, dt):
        """Фаза 3: Облако пыли и появление текста"""
        print("🌫️ Фаза 3: Облако пыли + текст")

        # Анимация текста
        if self.text_label:
            anim_text = Animation(
                color=[1, 1, 1, 1],  # Появление
                duration=0.5,
                t='out_back'
            )
            anim_text.start(self.text_label)

    def phase4_assemble(self, dt):
        """Фаза 4: Сборка мяча обратно"""
        print("🔧 Фаза 4: Сборка")

        # Целевая позиция (центр эффекта минус половина размера для центрирования)
        target_pos = (self.center_x - 10, self.center_y - 10)

        for fragment_data in self.fragments:
            fragment_widget = fragment_data['widget']

            # Создаем анимацию только для позиции и прозрачности
            anim = Animation(
                pos=target_pos,
                opacity=1,  # Восстанавливаем прозрачность
                duration=0.8,
                t='out_back'
            )
            anim.start(fragment_widget)

    def phase5_complete(self, dt):
        """Фаза 5: Завершение эффекта"""
        print("✅ Фаза 5: Завершение")
        self.is_playing = False

        # Убираем текст
        if self.text_label:
            anim = Animation(
                color=[1, 1, 1, 0],
                duration=0.3
            )
            anim.start(self.text_label)
            Clock.schedule_once(lambda dt: self.cleanup(), 0.5)

    def cleanup(self):
        """Полная очистка"""
        # Удаляем все фрагменты из родительского виджета
        for fragment_data in self.fragments:
            fragment_widget = fragment_data.get('widget')
            if fragment_widget and fragment_widget.parent:
                fragment_widget.parent.remove_widget(fragment_widget)

        # Очищаем списки
        self.fragments.clear()
        self.dust_particles.clear()

        # Удаляем текст
        if self.text_label and self.text_label.parent:
            self.remove_widget(self.text_label)
        self.text_label = None

        # Очищаем canvas
        self.canvas.clear()

        self.is_playing = False
        print("🧹 Эффект очищен")

    def on_pos(self, *args):
        """При изменении позиции перерисовываем"""
        pass

    def update(self, dt):
        """Обновление частиц пыли - вызывается автоматически Clock'ом"""
        if not self.is_playing:
            return

        # Обновляем частицы пыли
        particles_to_remove = []
        for i, particle in enumerate(self.dust_particles):
            # Уменьшаем время жизни
            particle['life'] -= dt * 0.8  # Немного быстрее исчезают

            # Если частица умерла, помечаем для удаления
            if particle['life'] <= 0:
                particles_to_remove.append(i)
                continue

            # Обновляем позицию (скорость уже маленькая)
            particle['pos'][0] += particle['velocity'][0]
            particle['pos'][1] += particle['velocity'][1]

            # Обновляем вращение
            particle['rotation'] += particle['rotation_speed'] * dt

        # Удаляем мертвые частицы
        for i in reversed(particles_to_remove):
            self.dust_particles.pop(i)

        # Перерисовываем частицы
        self.canvas.clear()
        with self.canvas:
            # Рисуем частицы пыли
            for particle in self.dust_particles:
                if particle['life'] > 0:
                    # Позиция (уже в пикселях)
                    x = self.center_x + particle['pos'][0]
                    y = self.center_y + particle['pos'][1]

                    # Цвет (становится прозрачнее)
                    color = particle['color'].copy()
                    color[3] *= particle['life']

                    Color(*color)
                    Ellipse(
                        pos=(x - particle['size'] / 2, y - particle['size'] / 2),
                        size=(particle['size'], particle['size'])
                    )

    def on_parent(self, *args):
        """При добавлении/удалении из родителя"""
        if self.parent:
            print(f"✅ Эффект добавлен на экран, родитель: {self.parent}")
        else:
            print("❌ Эффект удален с экрана")