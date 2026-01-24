from screens.game_screen import GameScreen

class BowlingScreen(GameScreen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.name = 'bowling'
        self.ball_image = 'assets/balls/bowling.png'
        self.background_image = 'assets/backgrounds/bowling_bg.jpg'
        self.sound_file = 'assets/sounds/football_bounce.wav'
        self.ball_size = 120