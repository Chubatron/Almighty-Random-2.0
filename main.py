from kivy.app import App
from kivy.clock import Clock
from kivy.uix.screenmanager import ScreenManager, FadeTransition
from kivy.core.window import Window


# Импортируем экраны
from screens.game_screen import GameScreen
from screens.menu_screen import MainMenuScreen

# Импортируем звуковой менеджер
from sound_manager import SoundManager

from screens.soccer_screen import SoccerScreen


from screens.football_screen import FootballScreen
from screens.basketball_screen import BasketballScreen
from screens.bowling_screen import BowlingScreen
from screens.coin_screen import CoinScreen
from screens.dice_screen import DiceScreen
from screens.dices_screen import DicesScreen
from screens.roulette_screen import RouletteScreen
from screens.rus_roulette_screen import RusRouletteScreen
from screens.quiz_screen import QuizScreen
from screens.random_screen import RandomScreen
from screens.random_number import RandomNumberScreen

from screens.intermediate_magic_ball import IntermediateMagicBall
from screens.intermediate_dice import IntermediateDice
from screens.intermediate_roulette import IntermediateRoulette
from screens.intermediate_random import IntermediateRandom

class SportsGameApp(App):
    def build(self):
        # Настройка окна
        Window.size = (400, 700)
        Window.clearcolor = (0.1, 0.1, 0.1, 1)

        # Инициализация SoundManager
        sound_mgr = SoundManager()
        sound_mgr.initialize("assets/sounds/background.wav")

        # Создаем менеджер экранов
        self.sm = ScreenManager(transition=FadeTransition(duration=0.3))

        # Добавляем экраны
        self.sm.add_widget(MainMenuScreen(name='menu'))
        self.sm.add_widget(GameScreen(name='game'))

        self.sm.add_widget(SoccerScreen(name='soccer'))

        self.sm.add_widget(FootballScreen(name='football'))
        self.sm.add_widget(BasketballScreen(name='basketball'))
        self.sm.add_widget(BowlingScreen(name='bowling'))
        self.sm.add_widget(CoinScreen(name='coin'))
        self.sm.add_widget(DiceScreen(name='dice'))
        self.sm.add_widget(DicesScreen(name='dices'))
        self.sm.add_widget(RouletteScreen(name='roulette'))
        self.sm.add_widget(RusRouletteScreen(name='rus_roulette'))
        self.sm.add_widget(RandomScreen(name='random'))
        self.sm.add_widget(QuizScreen(name='quiz'))
        self.sm.add_widget(RandomNumberScreen(name='random_number'))

        # промежуточные экраны
        self.sm.add_widget(IntermediateMagicBall(name='intermediate_magic_ball'))
        self.sm.add_widget(IntermediateDice(name='intermediate_dice'))
        self.sm.add_widget(IntermediateRoulette(name='intermediate_roulette'))
        self.sm.add_widget(IntermediateRandom(name='intermediate_random'))

        # Запускаем музыку через небольшой интервал
        Clock.schedule_once(lambda dt: sound_mgr.play(), 0.2)

        return self.sm

    def on_pause(self):
        """Пауза при сворачивании приложения"""
        SoundManager().pause()
        return True

    def on_resume(self):
        """Возобновление при разворачивании"""
        SoundManager().play()



if __name__ == '__main__':
    SportsGameApp().run()