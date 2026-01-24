from screens.game_screen import GameScreen

class FootballScreen(GameScreen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.name = 'football'
        self.ball_image = 'assets/balls/football.png'
        self.background_image = 'assets/backgrounds/football_bg.jpg'
        self.sound_file = 'assets/sounds/football_bounce.wav'
        self.ball_size = 120