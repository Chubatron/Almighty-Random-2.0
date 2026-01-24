from kivy.uix.floatlayout import FloatLayout
from kivy.uix.label import Label
from kivy.uix.image import Image
from kivy.animation import Animation
from kivy.clock import Clock
from animated_background import AnimatedBackground
from components.icon_button import IconButton
from screens.menu_screen import MainMenuScreen

class IntermediateDice(MainMenuScreen):
    def __init__(self, **kwargs):
        # Сначала очистить все виджеты
        self.clear_widgets()

        # Затем вызвать конструктор родителя
        super().__init__(**kwargs)

        layout = FloatLayout()

        # Удаляем панель управления после инициализации родителя
        # Найдите и удалите ControlPanel
        for child in self.children[:]:  # Копируем список
            print(child)
            if hasattr(child, '__class__') and child.__class__.__name__ == 'FloatLayout':
                self.remove_widget(child)
                break

        # Анимированный фон
        self.background = AnimatedBackground()
        layout.add_widget(self.background)

        # Статический фон (полупрозрачный)
        bg = Image(
            source='assets/backgrounds/indigo_bg.png',
            allow_stretch=True,
            keep_ratio=True,
            size_hint=(1, 1),
            fit_mode='fill',
            opacity=0.7
        )
        layout.add_widget(bg)

        # Заголовок
        title = Label(
            text='SELECT AN ITEM',
            font_name='assets/fonts/JockeyOne-Regular.ttf',
            font_size='32sp',
            bold=True,
            color=(1, 1, 1, 1),
            outline_color=(0, 0, 0, 1),
            outline_width=2,
            size_hint=(None, None),
            size=(400, 50),
            pos_hint={'center_x': 0.5, 'top': 0.95}
        )
        layout.add_widget(title)

        # Создаем кнопки
        self.create_buttons(layout)
        self.add_back_button(layout)
        self.add_widget(layout)

    def create_buttons(self, layout):
        """Создает кнопки видов спорта"""
        sports = [
            ('Dice', 'assets/images/buttons/Dice_button.png', 'dice', self.change_to_game),
            ('Dices', 'assets/images/buttons/Pink_dices_button.png', 'dices', self.change_to_game)
        ]

        # Сетка 5x2
        rows, cols = 2, 1
        button_width, button_height = 0.2, 0.2
        horizontal_spacing, vertical_spacing = 0.1, 0.02
        start_x, start_y = 0.5 - (button_width / 2) , 0.65

        for i, (text, icon_path, screen_name, callback) in enumerate(sports):
            row, col = i // cols, i % cols
            x_pos = start_x + col * (button_width + horizontal_spacing)
            y_pos = start_y - row * (button_height + vertical_spacing)

            btn = IconButton(
                text=text,
                icon_path=icon_path,
                sport=screen_name,
                size_hint=(button_width, button_height),
                pos_hint={'x': x_pos, 'y': y_pos},
                callback=callback
            )

            layout.add_widget(btn)

    def go_to_menu(self, instance):
        self.manager.current = 'menu'

    def change_to_game(self, instance):
        """Переход к игровому экрану"""
        self.manager.current = instance.sport
        self.manager.get_screen(instance.sport).start_game()

    def create_back_button(self, layout):
        """Создает кнопку назад с картинкой"""
        from kivy.uix.behaviors import ButtonBehavior
        from kivy.uix.image import Image

        class BackImageButton(ButtonBehavior, Image):
            pass

        back_btn = BackImageButton(
            source='assets/images/buttons/Orange_back_to_menu_button.png',  # Укажите путь к вашей картинке
            size_hint=(None, None),
            size=(60, 60),
            pos_hint={'x': 0.09, 'y': 0.055}, # совпадаем с кнопкой mute
            allow_stretch=True
        )

        # Анимация при нажатии
        def on_press(instance):
            Animation(opacity=0.7, duration=0.1).start(instance)

        def on_release(instance):
            Animation(opacity=1.0, duration=0.1).start(instance)
            Clock.schedule_once(lambda dt: self.go_to_menu(instance), 0.1)

        back_btn.bind(on_press=on_press)
        back_btn.bind(on_release=on_release)

        layout.add_widget(back_btn)
        return back_btn

    def add_back_button(self, layout):
        """Добавляет кнопку назад на layout"""
        # Проверяем, есть ли уже кнопка назад
        for child in layout.children:
            if hasattr(child, 'source') and 'back_icon' in child.source:
                return

        # Создаем новую кнопку
        self.create_back_button(layout)
