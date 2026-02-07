from kivy.uix.floatlayout import FloatLayout
from kivy.app import App
from components.control_button import ControlButton
from sound_manager import SoundManager


class ControlPanel(FloatLayout):
    """Панель служебных кнопок внизу экрана"""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.size_hint = (1, 0.15)
        self.pos_hint = {'x': 0, 'y': 0}
        self.create_buttons()

    def create_buttons(self):
        """Создает кнопки на панели управления"""
        # Проверяем начальное состояние звука
        sound_mgr = SoundManager()
        is_sound_on = not (sound_mgr.is_muted() or sound_mgr.get_volume() == 0)

        # Определяем параметры для каждой кнопки
        buttons_data = [
            {
                'text': 'SOUND ON' if is_sound_on else 'SOUND OFF',
                'callback': self.toggle_sound,
                'icon_path': 'assets/images/buttons/White_sound_on_button.png' if is_sound_on else 'assets/images/buttons/White_sound_off_button.png',
                'background_color': (0.2, 0.8, 0.2, 1) if is_sound_on else (0.5, 0.5, 0.5, 1)
            },
            {
                'text': 'SHARE',
                'callback': self.share_game,
                'icon_path': 'assets/images/buttons/White_share_button.png',
                'background_color': (0.1, 0.6, 0.9, 1)
            },
            {
                'text': 'RATE',
                'callback': self.rate_game,
                'icon_path': 'assets/images/buttons/White_rate_button.png',
                'background_color': (1, 0.8, 0.1, 1)
            },
            {
                'text': 'EXIT',
                'callback': self.exit_game,
                'icon_path': 'assets/images/buttons/White_exit_button.png',
                'background_color': (0.8, 0.1, 0.1, 1)
            },
        ]

        # Создаем кнопки
        for i, btn_data in enumerate(buttons_data):
            self.create_single_button(i, btn_data)

    def create_single_button(self, index, btn_data):
        """Создает одну кнопку"""
        btn = ControlButton(
            text=btn_data['text'],
            icon_path=btn_data['icon_path'],
            background_color=btn_data['background_color'],
            size_hint=(0.15, 1),
            pos_hint={'x': 0.045 + index * 0.25, 'y': 0.1},
            callback=btn_data['callback']
        )
        self.add_widget(btn)
        return btn

    def toggle_sound(self, instance):
        """Переключение звука вкл/выкл"""
        sound_mgr = SoundManager()

        if sound_mgr.is_muted() or sound_mgr.get_volume() == 0:
            # Включаем звук
            sound_mgr.unmute()
            self.update_sound_button(instance, True)
        else:
            # Выключаем звук
            sound_mgr.mute()
            self.update_sound_button(instance, False)

    def update_sound_button(self, instance, sound_on):
        """Обновляет внешний вид кнопки звука"""
        if sound_on:
            instance.text = 'SOUND ON'
            instance.background_color = (0.2, 0.8, 0.2, 1)
            instance.update_icon('assets/images/buttons/White_sound_on_button.png')


        else:
            instance.text = 'SOUND OFF'
            instance.background_color = (0.5, 0.5, 0.5, 1)
            instance.update_icon('assets/images/buttons/White_sound_off_button.png')

    def share_game(self, instance):
        print("Share feature would be implemented here")
        # Для Android можно использовать:
        # from plyer import share
        # share.share(title="Check out this game!", text="Amazing game!")

    def rate_game(self, instance):
        print("Rate feature would be implemented here")
        # Для Android можно использовать:
        # from plyer import notification
        # notification.notify(title="Rate us", message="Please rate our app!")

    def exit_game(self, instance):
        App.get_running_app().stop()