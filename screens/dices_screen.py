from screens.game_screen import GameScreen

class DicesScreen(GameScreen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.name = 'dices'
        self.ball_image = 'assets/balls/dices.png'
        self.background_image = 'assets/backgrounds/dices_bg.jpg'
        self.sound_file = 'assets/sounds/football_bounce.wav'
        self.ball_size = 120