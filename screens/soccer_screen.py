from screens.game_screen import GameScreen
import os


class SoccerScreen(GameScreen):
    """Экран с футбольным мячом из спрайт-листа"""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        print(f"\n=== SoccerScreen.__init__() ===")

        # Указываем путь к спрайт-листу
        self.sprite_sheet_path = 'assets/sprites/sprites_football_ball.png'
        self.name = 'soccer'

        print(f"Устанавливаю sprite_sheet_path: {self.sprite_sheet_path}")
        print(f"Файл существует: {os.path.exists(self.sprite_sheet_path)}")

        if os.path.exists(self.sprite_sheet_path):
            print(f"✅ Использую спрайт: {self.sprite_sheet_path}")
        else:
            print(f"❌ Файл спрайта не найден!")
            # Поищем файл
            print("Поиск файла...")
            for root, dirs, files in os.walk("."):
                for file in files:
                    if "football" in file.lower() or "soccer" in file.lower():
                        if file.endswith('.png'):
                            full_path = os.path.join(root, file)
                            print(f"  Найден: {full_path}")
                            self.sprite_sheet_path = full_path
                            break

        # Остальные настройки
        self.background_image = 'assets/backgrounds/football_bg.jpg'
        self.sound_file = 'assets/sounds/soccer_bounce.wav'
        self.ball_size = 110
        self.ball_type = 'soccer'  # Для физики

        print(f"ball_size: {self.ball_size}")
        print(f"ball_type: {self.ball_type}")
