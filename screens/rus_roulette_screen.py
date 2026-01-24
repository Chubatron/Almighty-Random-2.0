from screens.game_screen import GameScreen

class RusRouletteScreen(GameScreen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.name = 'rus_roulette'
        self.ball_image = 'assets/balls/rus_roulette.png'
        self.background_image = 'assets/backgrounds/rus_roulette_bg.jpg'
        self.sound_file = 'assets/sounds/football_bounce.wav'
        self.ball_size = 120