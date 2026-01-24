# test_texture_load.py
"""
Тест загрузки текстуры отдельно от всего
"""
import os
import sys
from kivy.app import App
from kivy.uix.floatlayout import FloatLayout
from kivy.core.window import Window

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

print("=" * 70)
print("ТЕСТ ЗАГРУЗКИ ТЕКСТУРЫ")
print("=" * 70)

# Сначала проверим файл
path = 'assets/sprites/sprites_football_ball.png'
print(f"\n1. ПРОВЕРКА ФАЙЛА:")
print(f"   Путь: {path}")
print(f"   Абсолютный путь: {os.path.abspath(path)}")
print(f"   Существует: {os.path.exists(path)}")

if os.path.exists(path):
    import stat

    file_info = os.stat(path)
    print(f"   Размер: {file_info.st_size} байт")
    print(f"   Дата изменения: {file_info.st_mtime}")

try:
    # Пробуем загрузить текстуру напрямую
    print(f"\n2. ЗАГРУЗКА ТЕКСТУРЫ:")
    from kivy.core.image import Image as CoreImage

    texture = CoreImage(path).texture
    print(f"   ✅ Текстура загружена!")
    print(f"   Размер: {texture.width}x{texture.height}")
    print(f"   ID: {texture.id}")
    print(f"   Mag filter: {texture.mag_filter}")
    print(f"   Min filter: {texture.min_filter}")

    # Проверяем что текстура валидна
    if texture.width == 0 or texture.height == 0:
        print(f"   ⚠️ Предупреждение: текстура имеет нулевой размер!")

    # Тест отображения
    print(f"\n3. ТЕСТ ОТОБРАЖЕНИЯ:")


    class TextureTestApp(App):
        def build(self):
            Window.clearcolor = (0.2, 0.2, 0.3, 1)
            layout = FloatLayout()

            # Создаем виджет который отобразит текстуру
            from kivy.uix.widget import Widget
            from kivy.graphics import Rectangle, Color

            test_widget = Widget(
                size_hint=(None, None),
                size=(200, 200),
                pos_hint={'center_x': 0.5, 'center_y': 0.5}
            )

            # 1. Красный фон
            with test_widget.canvas.before:
                Color(1, 0, 0, 0.3)
                Rectangle(pos=test_widget.pos, size=test_widget.size)

            # 2. Вся текстура
            with test_widget.canvas:
                Color(1, 1, 1, 1)
                Rectangle(
                    pos=test_widget.pos,
                    size=test_widget.size,
                    texture=texture
                )

            # 3. Зеленая рамка
            with test_widget.canvas.after:
                Color(0, 1, 0, 1)
                from kivy.graphics import Line
                Line(rectangle=(
                    test_widget.x, test_widget.y,
                    test_widget.width, test_widget.height
                ), width=3)

            layout.add_widget(test_widget)

            # Информация
            from kivy.uix.label import Label
            info = Label(
                text=f'ТЕКСТУРА ТЕСТ\n'
                     f'Размер: {texture.width}x{texture.height}\n'
                     f'Если видите изображение - текстура работает',
                size_hint=(None, None),
                size=(400, 100),
                pos_hint={'center_x': 0.5, 'top': 0.9},
                color=(1, 1, 1, 1),
                font_size='16sp',
                halign='center'
            )
            layout.add_widget(info)

            return layout


    print(f"\nЗапускаю тест отображения...")
    TextureTestApp().run()

except Exception as e:
    print(f"\n❌ ОШИБКА ПРИ ЗАГРУЗКЕ ТЕКСТУРЫ: {e}")
    import traceback

    traceback.print_exc()