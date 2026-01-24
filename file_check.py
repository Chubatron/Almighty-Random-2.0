# quick_file_check.py
import os
from PIL import Image

path = 'assets/sprites/sprites_football_ball.png'

if os.path.exists(path):
    try:
        with Image.open(path) as img:
            print(f"✅ Файл открыт PIL")
            print(f"   Формат: {img.format}")
            print(f"   Размер: {img.size}")
            print(f"   Режим: {img.mode}")
            print(f"   Прозрачность: {'да' if 'A' in img.mode else 'нет'}")

            # Покажем первый пиксель
            if img.mode == 'RGBA':
                r, g, b, a = img.getpixel((0, 0))
                print(f"   Первый пиксель: RGBA({r}, {g}, {b}, {a})")
            else:
                pixel = img.getpixel((0, 0))
                print(f"   Первый пиксель: {pixel}")

    except Exception as e:
        print(f"❌ Ошибка PIL: {e}")
else:
    print(f"❌ Файл не существует")