from screens.magic_ball_screen import MagicBallScreen

class QuizScreen(MagicBallScreen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.name = 'quiz'
        self.ball_image = 'assets/balls/quiz.png'
        self.background_image = 'assets/backgrounds/quiz_bg.jpg'
        self.sound_file = 'assets/sounds/football_bounce.wav'
        self.ball_size = 120