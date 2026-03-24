from screens.magic_ball_screen import MagicBallScreen

class DiceScreen(MagicBallScreen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.name = 'dice'
        self.ball_image = 'assets/balls/dice.png'
        self.background_image = 'assets/backgrounds/dice_bg.jpg'
        self.sound_file = 'assets/sounds/football_bounce.wav'
        self.ball_size = 120