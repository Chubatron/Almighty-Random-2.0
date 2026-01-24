from screens.game_screen import GameScreen

class RouletteScreen(GameScreen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.name = 'roulette'
        self.ball_image = 'assets/balls/roulette.png'
        self.background_image = 'assets/backgrounds/roulette_bg.jpg'
        self.sound_file = 'assets/sounds/football_bounce.wav'
        self.ball_size = 120