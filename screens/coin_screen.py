from screens.game_screen import GameScreen

class CoinScreen(GameScreen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.name = 'coin'
        self.ball_image = 'assets/balls/coin.png'
        self.background_image = 'assets/backgrounds/coin_bg.jpg'
        self.sound_file = 'assets/sounds/football_bounce.wav'
        self.ball_size = 120