from screens.game_screen import GameScreen

class BasketballScreen(GameScreen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.name = 'basketball'
        self.ball_image = 'assets/balls/basket.png'
        self.background_image = 'assets/backgrounds/basket_bg.jpg'
        self.sound_file = 'assets/sounds/football_bounce.wav'
        self.ball_size = 120