# simple_sprite_viewer.py
"""
СУПЕР ПРОСТОЙ ПРОСМОТРЩИК СПРАЙТОВ
Просто укажите путь к файлу и смотрите анимацию
"""
import os
from kivy.app import App
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.clock import Clock
from kivy.core.image import Image as CoreImage
from kivy.graphics import Rectangle
from kivy.core.window import Window


class SimpleSpriteViewer(App):
    def build(self):
        Window.clearcolor = (0, 0, 0, 1)
        Window.size = (500, 500)

        layout = FloatLayout()

        # Укажите путь к вашему файлу здесь!
        SPRITE_PATH = "assets/sprites/sprites_football_ball.png"
        ROWS = 8
        COLS = 8

        print(f"Загружаю файл: {SPRITE_PATH}")
        print(f"Файл существует: {os.path.exists(SPRITE_PATH)}")

        if not os.path.exists(SPRITE_PATH):
            print("❌ Файл не найден!")
            print("Ищу файлы в проекте...")
            for root, dirs, files in os.walk("."):
                for file in files:
                    if file.endswith('.png'):
                        print(f"  {os.path.join(root, file)}")
            SPRITE_PATH = ""  # Пустая строка

        # Загружаем текстуру
        self.texture = None
        self.current_frame = 0
        self.rows = ROWS
        self.cols = COLS
        self.total_frames = ROWS * COLS

        if SPRITE_PATH:
            try:
                self.texture = CoreImage(SPRITE_PATH).texture
                print(f"✅ Текстура загружена: {self.texture.width}x{self.texture.height}")
            except Exception as e:
                print(f"❌ Ошибка загрузки: {e}")

        # Создаем виджет для отображения
        self.sprite_widget = FloatLayout(
            size_hint=(None, None),
            size=(400, 400),
            pos_hint={'center_x': 0.5, 'center_y': 0.5}
        )
        layout.add_widget(self.sprite_widget)

        # Информация
        self.info_label = Label(
            text=f'Файл: {os.path.basename(SPRITE_PATH) if SPRITE_PATH else "НЕ НАЙДЕН"}\nКадр: 0/{self.total_frames - 1}',
            size_hint=(None, None),
            size=(400, 60),
            pos_hint={'center_x': 0.5, 'top': 0.95},
            color=(1, 1, 1, 1),
            font_size='16sp'
        )
        layout.add_widget(self.info_label)

        # Кнопки
        btn_layout = FloatLayout(size_hint=(1, 0.2), pos_hint={'y': 0})

        btn_prev = Button(
            text='← Предыдущий',
            size_hint=(0.3, 0.8),
            pos_hint={'x': 0.05, 'center_y': 0.5},
            background_color=(0.2, 0.6, 0.2, 1)
        )
        btn_prev.bind(on_press=lambda x: self.change_frame(-1))

        btn_next = Button(
            text='Следующий →',
            size_hint=(0.3, 0.8),
            pos_hint={'right': 0.95, 'center_y': 0.5},
            background_color=(0.2, 0.6, 0.2, 1)
        )
        btn_next.bind(on_press=lambda x: self.change_frame(1))

        btn_anim = Button(
            text='▶ Анимация',
            size_hint=(0.3, 0.8),
            pos_hint={'center_x': 0.5, 'center_y': 0.5},
            background_color=(0.8, 0.2, 0.2, 1)
        )
        btn_anim.bind(on_press=self.toggle_animation)

        btn_layout.add_widget(btn_prev)
        btn_layout.add_widget(btn_anim)
        btn_layout.add_widget(btn_next)

        layout.add_widget(btn_layout)

        # Сразу отображаем первый кадр
        Clock.schedule_once(lambda dt: self.update_frame(), 0.01)

        self.animation_event = None
        return layout

    def change_frame(self, delta):
        """Изменяет текущий кадр"""
        self.current_frame = (self.current_frame + delta) % self.total_frames
        self.update_frame()

    def toggle_animation(self, instance):
        """Включает/выключает анимацию"""
        if self.animation_event:
            self.animation_event.cancel()
            self.animation_event = None
            instance.text = '▶ Анимация'
            instance.background_color = (0.8, 0.2, 0.2, 1)
        else:
            self.animation_event = Clock.schedule_interval(
                lambda dt: self.change_frame(1),
                0.1  # 10 FPS
            )
            instance.text = '⏸ Пауза'
            instance.background_color = (0.2, 0.2, 0.8, 1)

    def update_frame(self):
        """Обновляет отображение текущего кадра"""
        self.sprite_widget.canvas.clear()

        if not self.texture:
            # Рисуем тестовый квадрат если нет текстуры
            with self.sprite_widget.canvas:
                from kivy.graphics import Color
                Color(1, 0, 0, 1)
                Rectangle(pos=self.sprite_widget.pos, size=self.sprite_widget.size)
            return

        # Вычисляем координаты кадра
        row = self.current_frame // self.cols
        col = self.current_frame % self.cols

        tex_left = col / self.cols
        tex_right = (col + 1) / self.cols
        tex_top = 1.0 - (row / self.rows)  # Kivy текстуры перевернуты
        tex_bottom = 1.0 - ((row + 1) / self.rows)

        # Отрисовываем кадр
        with self.sprite_widget.canvas:
            Rectangle(
                pos=self.sprite_widget.pos,
                size=self.sprite_widget.size,
                texture=self.texture,
                tex_coords=(
                    tex_left, tex_bottom,
                    tex_right, tex_bottom,
                    tex_right, tex_top,
                    tex_left, tex_top
                )
            )

        # Обновляем информацию
        self.info_label.text = f'Файл: {self.texture.__class__.__name__}\nКадр: {self.current_frame}/{self.total_frames - 1}'


if __name__ == '__main__':
    print("Запуск простого просмотрщика спрайтов...")
    SimpleSpriteViewer().run()