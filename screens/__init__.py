from .menu_screen import MainMenuScreen
from .magic_ball_screen import MagicBallScreen
from .base_game_screen import BaseGameScreen
from .coin_screen import CoinScreen
from .random_number_screen import RandomNumberScreen
from .quiz_screen import QuizScreen  # quiz_screen.py должен быть в папке screens/

__all__ = [
    'MainMenuScreen',
    'MagicBallScreen',
    'BaseGameScreen',
    'CoinScreen',
    'RandomNumberScreen',
    'QuizScreen'
]