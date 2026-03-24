from screens.magic_ball_screen import MagicBallScreen

class RandomScreen(MagicBallScreen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.name = 'random'
        self.ball_image = 'assets/balls/random.png'
        self.background_image = 'assets/backgrounds/bowling_bg.jpg'
        self.sound_file = 'assets/sounds/background.wav'
        self.ball_size = 120