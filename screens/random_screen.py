from screens.game_screen import GameScreen

class RandomScreen(GameScreen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.name = 'random'
        self.ball_image = 'assets/balls/random.png'
        self.background_image = 'assets/backgrounds/bowling_bg.jpg'
        self.sound_file = 'assets/sounds/background.wav'
        self.ball_size = 120