from screens.game_screen import GameScreen

class RandomNumberScreen(GameScreen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.name = 'random_number'
        self.ball_image = 'assets/balls/coin.png'
        self.background_image = 'assets/backgrounds/coin_bg.jpg'
        self.sound_file = 'assets/sounds/football_bounce.wav'
        self.ball_size = 120