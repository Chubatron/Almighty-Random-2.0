from .menu_screen import MainMenuScreen
from .game_screen import GameScreen
from .football_screen import FootballScreen
from .basketball_screen import BasketballScreen
from .base_game_screen import BaseGameScreen  # Добавьте эту строку
from .coin_screen import CoinScreen  # Добавьте эту строку (или как у вас называется файл с монеткой)
# ... импортируйте остальные экраны

__all__ = [
    'MainMenuScreen',
    'GameScreen',
    'FootballScreen',
    'BasketballScreen',
    'BaseGameScreen',  # Добавьте эту строку
    'CoinScreen',  # Добавьте эту строку
    # ... остальные экраны
]