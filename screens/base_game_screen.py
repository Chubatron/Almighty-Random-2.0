from kivy.uix.screenmanager import Screen
from kivy.uix.floatlayout import FloatLayout
from kivy.properties import StringProperty, NumericProperty
from kivy.clock import Clock
from kivy.animation import Animation
from kivy.uix.behaviors import ButtonBehavior
from kivy.uix.image import Image as KivyImage
from kivy.uix.label import Label
from kivy.graphics import Color, Rectangle, PushMatrix, PopMatrix, Rotate
from kivy.core.audio import SoundLoader
from kivy.core.window import Window
from sound_manager import SoundManager
from lucky_token import LuckyToken          # <-- Lucky_Token
import os


class ToggleButtonWithLabel(ButtonBehavior, FloatLayout):
    """Кнопка с изображением как фоном и текстом по центру"""

    def __init__(self, **kwargs):
        self._button_size = kwargs.pop('size', (250, 60))
        super().__init__(**kwargs)

        self.size_hint = (None, None)
        self.size = self._button_size

        self.bg_image = KivyImage(
            source='',
            size_hint=(1, 1),
            pos_hint={'x': 0, 'y': 0},
            allow_stretch=True,
            keep_ratio=False,
            mipmap=True,                # ❗ включены мипмапы для кнопки SWITCH
        )

        self.label = Label(
            text='',
            font_size='20sp',
            bold=True,
            color=(1, 1, 1, 1),
            size_hint=(1, 1),
            pos_hint={'center_x': 0.5, 'center_y': 0.5},
            halign='center',
            valign='middle'
        )
        self.label.bind(size=self.label.setter('text_size'))

        self.add_widget(self.bg_image)
        self.add_widget(self.label)

        # Загружаем звук для кнопки
        self.click_sound = None
        self.load_click_sound()

        Clock.schedule_once(lambda dt: self.update_font_size(), 0)

    def load_click_sound(self):
        """Загружает звук нажатия кнопки"""
        sound_path = 'assets/sounds/Schpun.ogg'
        if os.path.exists(sound_path):
            self.click_sound = SoundLoader.load(sound_path)
            if self.click_sound:
                self.click_sound.volume = 0.6

    def play_click_sound(self):
        """Воспроизводит звук нажатия кнопки"""
        if self.click_sound and not SoundManager().is_muted():
            try:
                if self.click_sound.state == 'play':
                    self.click_sound.stop()
                self.click_sound.play()
            except:
                pass

    def on_press(self):
        """При нажатии на кнопку воспроизводим звук"""
        self.play_click_sound()

    def update_font_size(self):
        if hasattr(self, 'label') and self.label:
            font_size = self.height * 0.42
            self.label.font_size = font_size

    def on_size(self, *args):
        if hasattr(self, 'label') and self.label:
            self.update_font_size()

    @property
    def icon(self):
        return self.bg_image

    @icon.setter
    def icon(self, value):
        self.bg_image.source = value


class BaseGameScreen(Screen):
    """Базовый класс с музыкой и кнопкой назад (без собственного затемнения - использует FadeTransition)"""

    # КОЭФФИЦИЕНТЫ ДЛЯ КНОПКИ SWITCH
    SWITCH_BUTTON_WIDTH_COEFF = 0.55
    SWITCH_BUTTON_HEIGHT_COEFF = 0.08
    SWITCH_BUTTON_POS_Y_COEFF = 0.9

    background_image = StringProperty('')
    sound_file = StringProperty('')
    is_game_screen = True

    # ==================== НАГРАДА (общая логика) ====================
    reward_source = StringProperty('assets/images/luck_coin.png')
    reward_sound_path = StringProperty('assets/sounds/coin/reward.ogg')
    reward_size_coeff = NumericProperty(0.18)
    reward_fly_duration = NumericProperty(0.9)
    reward_appear_duration = NumericProperty(0.15)
    reward_fade_duration = NumericProperty(0.2)
    reward_end_scale = NumericProperty(0.5)
    reward_stagger_delay = NumericProperty(0.25)   # задержка между монетками в серии
    reward_rotation = NumericProperty(0)          # ✅ угол поворота картинки награды

    def __init__(self, **kwargs):
        self.screen_params = kwargs.pop('screen_params', None)
        super().__init__(**kwargs)

        self.layout = FloatLayout()
        self.layout.size_hint = (1, 1)

        self.sound = None
        self.back_sound = None
        self.bg_image = None
        self.back_button = None
        self.type_switch_button = None

        # ===== НАГРАДА =====
        self.reward_image = None          # одиночная (обратная совместимость)
        self.reward_images = []           # список для серии
        self.reward_sound = None

        self.sound_manager = SoundManager()
        self.tokens = LuckyToken()          # <-- Lucky_Token

        self.add_widget(self.layout)
        self.bind(size=self._on_size_change)

        self.load_back_sound()
        self._load_reward_sound()

    # ==================== МЕТОДЫ ДЛЯ РАБОТЫ С ПАРАМЕТРАМИ ЭКРАНА ====================

    def get_screen_width(self):
        from kivy.utils import platform
        from kivy.core.window import Window

        if platform == 'android':
            return Window.system_size[0]
        else:
            if self.screen_params and self.screen_params.width > 0:
                return self.screen_params.width
            return Window.width

    def get_screen_height(self):
        from kivy.utils import platform
        from kivy.core.window import Window

        if platform == 'android':
            return Window.system_size[1]
        else:
            if self.screen_params and self.screen_params.height > 0:
                return self.screen_params.height
            return Window.height

    def get_min_dimension(self):
        return min(self.get_screen_width(), self.get_screen_height())

    def get_relative_size(self, percent=1.0, use_min=True):
        base = self.get_min_dimension() if use_min else self.get_screen_width()
        return int(base * percent)

    def get_relative_size_tuple(self, percent_width=1.0, percent_height=1.0):
        return (int(self.get_screen_width() * percent_width),
                int(self.get_screen_height() * percent_height))

    def get_center(self):
        return (self.get_screen_width() / 2, self.get_screen_height() / 2)

    def get_screen_params_dict(self):
        width = self.get_screen_width()
        height = self.get_screen_height()
        return {
            'width': width,
            'height': height,
            'min_dimension': min(width, height),
            'center_x': width / 2,
            'center_y': height / 2
        }

    # ==================== МЕТОДЫ ДЛЯ КНОПКИ SWITCH ====================

    def create_switch_button(self, text="SWITCH", icon_path='assets/images/buttons/Roulette_switch_button.png',
                             callback=None, size=None, pos_hint=None):
        screen_width = self.get_screen_width()
        screen_height = self.get_screen_height()

        if size is None:
            button_width = screen_width * self.SWITCH_BUTTON_WIDTH_COEFF
            button_height = screen_height * self.SWITCH_BUTTON_HEIGHT_COEFF
            size = (button_width, button_height)

        if pos_hint is None:
            pos_hint = {'center_x': 0.5, 'center_y': self.SWITCH_BUTTON_POS_Y_COEFF}

        self.type_switch_button = ToggleButtonWithLabel(
            size_hint=(None, None),
            size=size,
            pos_hint=pos_hint
        )

        self.type_switch_button.label.text = text
        self.type_switch_button.icon.source = icon_path

        if callback:
            self.type_switch_button.bind(on_press=callback)
        self.layout.add_widget(self.type_switch_button)

        return self.type_switch_button

    def set_switch_button_state(self, enabled):
        if self.type_switch_button:
            self.type_switch_button.disabled = not enabled
            self.type_switch_button.opacity = 1.0 if enabled else 0.5

    def remove_switch_button(self):
        if self.type_switch_button and self.type_switch_button in self.layout.children:
            self.layout.remove_widget(self.type_switch_button)
            self.type_switch_button = None

    def update_switch_button_size(self):
        if self.type_switch_button:
            screen_width = self.get_screen_width()
            screen_height = self.get_screen_height()

            button_width = screen_width * self.SWITCH_BUTTON_WIDTH_COEFF
            button_height = screen_height * self.SWITCH_BUTTON_HEIGHT_COEFF
            self.type_switch_button.size = (button_width, button_height)

    # ==================== ОСТАЛЬНЫЕ МЕТОДЫ ====================

    def load_back_sound(self):
        sound_path = 'assets/sounds/Schpun.ogg'
        if os.path.exists(sound_path):
            self.back_sound = SoundLoader.load(sound_path)
            if self.back_sound:
                self.back_sound.volume = 0.8

    def play_back_sound(self):
        if self.back_sound and not self.sound_manager.is_muted():
            try:
                self.back_sound.play()
            except:
                pass

    def _on_size_change(self, instance, value):
        if self.back_button:
            Clock.schedule_once(lambda dt: self._update_button_position(), 0.05)
        if self.type_switch_button:
            Clock.schedule_once(lambda dt: self.update_switch_button_size(), 0.05)
        if self.reward_images:
            Clock.schedule_once(lambda dt: self._reset_all_rewards(), 0.05)

    def _update_button_position(self):
        if self.back_button:
            real_width = self.get_screen_width()
            real_height = self.get_screen_height()
            btn_size = real_width * 0.1
            btn_x = real_width * 0.05
            btn_y = real_height * 0.05
            self.back_button.size = (btn_size, btn_size)
            self.back_button.pos = (btn_x, btn_y)

    def on_enter(self):
        """Вызывается при входе на экран (FadeTransition из main.py обеспечивает затемнение)"""
        # Настройка фона и звука
        self.setup_background()
        self.setup_sound()
        Clock.schedule_once(lambda dt: self.create_back_button(), 0.05)

        # Награда — создаём скрытую картинку (одну)
        Clock.schedule_once(lambda dt: self._create_reward_image(), 0.1)

        if self.is_game_screen:
            if not self.sound_manager.is_muted():
                self.sound_manager.fade_to(0.05, duration=1.0)

    def on_leave(self):
        """Вызывается при выходе с экрана"""
        self._remove_all_rewards()
        self.stop_sound()
        if self.is_game_screen and not self.sound_manager.is_muted():
            self.sound_manager.fade_to(1.0, duration=1.0)

    def go_to_menu(self):
        """Возврат в меню через switch_screen (пересоздание экрана)"""
        self.stop_sound()
        if not self.sound_manager.is_muted():
            self.sound_manager.fade_to(1.0, duration=0.5)

        # Используем глобальную функцию из main.py для пересоздания экрана
        from main import switch_screen
        switch_screen('menu')

    def setup_background(self):
        if self.bg_image:
            self.layout.remove_widget(self.bg_image)

        from kivy.uix.image import Image
        self.bg_image = Image(
            source=self.background_image,
            allow_stretch=True,
            keep_ratio=False,
            size_hint=(1, 1)
        )
        self.layout.add_widget(self.bg_image)

    def setup_sound(self):
        if self.sound_file:
            self.sound = SoundLoader.load(self.sound_file)
            if self.sound:
                self.sound.loop = True
                self.sound.volume = 0.5 if not self.sound_manager.is_muted() else 0.0
                self.sound.play()

    def stop_sound(self):
        if self.sound:
            self.sound.stop()
            self.sound = None

    def create_back_button(self):
        if self.back_button and self.back_button in self.layout.children:
            self.layout.remove_widget(self.back_button)
        self._create_unified_back_button()

    def _create_unified_back_button(self):
        class ImageButton(ButtonBehavior, KivyImage):
            pass

        real_width = self.get_screen_width()
        real_height = self.get_screen_height()
        btn_size = real_width * 0.1
        btn_x = real_width * 0.05
        btn_y = real_height * 0.05

        back_btn = ImageButton(
            source='assets/images/buttons/Orange_back_to_menu_button.png',
            size_hint=(None, None),
            size=(btn_size, btn_size),
            pos=(btn_x, btn_y),
            allow_stretch=True,
            mipmap=True,                # ❗ включены мипмапы для кнопки back to menu
        )

        def on_press(instance):
            Animation(opacity=0.7, duration=0.1).start(instance)

        def on_release(instance):
            Animation(opacity=1.0, duration=0.1).start(instance)
            self.play_back_sound()
            Clock.schedule_once(lambda dt: self.go_to_menu(), 0.1)

        back_btn.bind(on_press=on_press)
        back_btn.bind(on_release=on_release)

        self.back_button = back_btn
        self.layout.add_widget(back_btn)

    def on_touch_down(self, touch):
        if hasattr(self, 'back_button') and self.back_button:
            if self.back_button.collide_point(touch.x, touch.y):
                self.back_button.on_touch_down(touch)
                return True
        return super().on_touch_down(touch)

    def start_game(self):
        pass

    # ==================== МЕТОДЫ ВИБРАЦИИ ====================

    def vibrate(self, duration=0.05):
        if hasattr(self, 'sound_manager') and self.sound_manager:
            self.sound_manager.vibrate(duration)

    def vibrate_custom(self, duration_ms):
        duration_sec = duration_ms / 1000.0
        self.vibrate(duration_sec)

    def vibrate_short(self):
        self.vibrate(0.03)

    def vibrate_medium(self):
        self.vibrate(0.06)

    def vibrate_long(self):
        self.vibrate(0.12)

    def vibrate_success(self):
        if hasattr(self, 'sound_manager') and self.sound_manager:
            self.sound_manager.vibrate_success()

    def vibrate_error(self):
        self.vibrate_long()

    def vibrate_selection(self):
        self.vibrate_short()

    # ==================== LUCKY_TOKEN: НАЧИСЛЕНИЕ И ТРАТЫ ====================

    def award_game_completed(self, game_name=None):
        if game_name is None:
            game_name = self.name or "unknown"
        self.tokens.reward_game_completed(game_name)

    def award_tokens(self, amount, reason="custom"):
        self.tokens.add(amount, reason=reason)

    def spend_tokens(self, amount, reason="purchase"):
        return self.tokens.spend(amount, reason=reason)

    def can_afford(self, amount):
        return self.tokens.can_afford(amount)

    def get_token_balance(self):
        return self.tokens.get_balance()

    def show_token_popup(self, amount, text=None):
        try:
            message = f"+{int(amount)} 🎟️"
            if text:
                message = f"{text}\n{message}"

            popup = Label(
                text=message,
                font_size='28sp',
                bold=True,
                color=(1, 0.85, 0.2, 1),
                outline_color=(0, 0, 0, 1),
                outline_width=2,
                halign='center',
                valign='middle',
                size_hint=(None, None),
                size=(self.get_screen_width() * 0.6,
                      self.get_screen_height() * 0.12),
                pos_hint={'center_x': 0.5, 'center_y': 0.5},
                opacity=0,
            )
            popup.bind(size=popup.setter('text_size'))

            self.layout.add_widget(popup)

            Animation(opacity=1, duration=0.2).start(popup)

            def fade_out(dt):
                anim = Animation(opacity=0, duration=0.4)
                anim.bind(on_complete=lambda *a: self.layout.remove_widget(popup)
                          if popup in self.layout.children else None)
                anim.start(popup)

            Clock.schedule_once(fade_out, 0.9)

        except Exception as e:
            print(f"⚠️ [BaseGameScreen] show_token_popup ошибка: {e}")

    # ==================== НАГРАДА: ЗВУК ====================

    def _load_reward_sound(self):
        if self.reward_sound_path and os.path.exists(self.reward_sound_path):
            self.reward_sound = SoundLoader.load(self.reward_sound_path)
            if self.reward_sound:
                self.reward_sound.volume = 0.9

    def _play_reward_sound(self):
        try:
            if self.sound_manager.is_muted():
                return
        except Exception:
            pass
        if self.reward_sound:
            try:
                if self.reward_sound.state == 'play':
                    self.reward_sound.stop()
                self.reward_sound.play()
            except Exception:
                pass

    # ==================== НАГРАДА: ЯКОРЯ (переопределяются) ====================

    def get_reward_start_hint(self):
        """Откуда появляется монета-награда.
        Возвращает dict для pos_hint, например {'center_x': 0.5, 'center_y': 0.5}.
        По умолчанию — центр экрана.
        """
        return {'center_x': 0.5, 'center_y': 0.5}

    def get_reward_target_hint(self):
        """Куда летит монета-награда.
        Возвращает dict для pos_hint — например, центр виджета жетонов.
        По умолчанию — центр экрана.
        """
        return {'center_x': 0.5, 'center_y': 0.5}

    def on_reward_arrived(self):
        """Хук: вызывается, когда КАЖДАЯ монетка-награда долетела до цели."""
        pass

    def on_reward_series_complete(self):
        """Хук: вызывается, когда ВСЯ серия наград долетела."""
        pass

    # ==================== НАГРАДА: РЕАЛИЗАЦИЯ ====================

    def _get_real_layout_size(self):
        if self.layout and self.layout.width > 1 and self.layout.height > 1:
            return self.layout.width, self.layout.height
        return Window.width, Window.height

    def _build_reward_image(self, size, pos_hint):
        """Создаёт KivyImage награды с поворотом на reward_rotation
        вокруг своего центра. Возвращает виджет."""
        img = KivyImage(
            source=self.reward_source,
            size_hint=(None, None),
            size=(size, size) if not isinstance(size, (list, tuple)) else size,
            pos_hint=dict(pos_hint),
            allow_stretch=True,
            keep_ratio=True,
            mipmap=True,
            opacity=0,
        )

        rotate = Rotate(angle=self.reward_rotation, origin=img.center)

        with img.canvas.before:
            PushMatrix()
            rotate = Rotate(angle=self.reward_rotation, origin=img.center)
        with img.canvas.after:
            PopMatrix()

        def _update_rotate_origin(*args):
            rotate.origin = (img.center_x, img.center_y)

        img.bind(pos=_update_rotate_origin, size=_update_rotate_origin)
        img._rotate_gfx = rotate

        return img

    def _create_reward_image(self):
        """Создаёт скрытую картинку награды (одну, для обратной совместимости)."""
        if self.reward_image and self.reward_image.parent:
            return

        layout_w, layout_h = self._get_real_layout_size()
        size = min(layout_w, layout_h) * self.reward_size_coeff

        start_hint = dict(self.get_reward_start_hint())

        self.reward_image = self._build_reward_image(size, start_hint)
        self.layout.add_widget(self.reward_image)

    def _create_single_reward(self):
        """Создаёт ещё одну картинку-награду и добавляет в список reward_images."""
        layout_w, layout_h = self._get_real_layout_size()
        size = min(layout_w, layout_h) * self.reward_size_coeff

        start_hint = dict(self.get_reward_start_hint())

        img = self._build_reward_image(size, start_hint)
        self.layout.add_widget(img)
        self.reward_images.append(img)
        return img

    def _remove_reward_image(self):
        if self.reward_image and self.reward_image.parent:
            Animation.cancel_all(self.reward_image)
            self.layout.remove_widget(self.reward_image)
        self.reward_image = None

    def _remove_all_rewards(self):
        self._remove_reward_image()
        for img in list(self.reward_images):
            if img and img.parent:
                Animation.cancel_all(img)
                self.layout.remove_widget(img)
        self.reward_images = []

    def _reset_reward_image(self):
        if not self.reward_image:
            return
        Animation.cancel_all(self.reward_image)
        self.reward_image.opacity = 0
        self.reward_image.pos_hint = dict(self.get_reward_start_hint())

    def _reset_all_rewards(self):
        self._reset_reward_image()
        start_hint = dict(self.get_reward_start_hint())
        for img in self.reward_images:
            if img:
                Animation.cancel_all(img)
                img.opacity = 0
                img.pos_hint = dict(start_hint)

    def _normalize_hint(self, hint):
        cx = hint.get('center_x', hint.get('x', 0.0) + 0.5)
        cy = hint.get('center_y', hint.get('y', 0.0) + 0.5)
        return cx, cy

    def _fly_single_reward(self, img, delay=0.0, is_last=False):
        if not img or not img.parent:
            return

        layout_w, layout_h = self._get_real_layout_size()
        size = min(layout_w, layout_h) * self.reward_size_coeff

        start_hint = dict(self.get_reward_start_hint())
        target_hint = dict(self.get_reward_target_hint())

        start_cx, start_cy = self._normalize_hint(start_hint)
        target_cx, target_cy = self._normalize_hint(target_hint)

        img.size = (size, size)
        img.pos_hint = {'center_x': start_cx, 'center_y': start_cy}
        img.opacity = 0

        end_size = size * self.reward_end_scale

        appear = Animation(
            opacity=1.0,
            duration=self.reward_appear_duration,
            t='out_quad',
        )
        fly = Animation(
            pos_hint={'center_x': target_cx, 'center_y': target_cy},
            size=(end_size, end_size),
            duration=self.reward_fly_duration,
            t='in_quad',
        )

        def _on_fly_complete(*args):
            try:
                self.on_reward_arrived()
            except Exception as e:
                print(f"⚠️ [BaseGameScreen] on_reward_arrived: {e}")

            fade = Animation(
                opacity=0.0,
                duration=self.reward_fade_duration,
                t='out_quad',
            )

            def _on_fade_complete(*a):
                if img in self.reward_images:
                    self.reward_images.remove(img)
                if img.parent:
                    self.layout.remove_widget(img)

                if is_last:
                    try:
                        self.on_reward_series_complete()
                    except Exception as e:
                        print(f"⚠️ [BaseGameScreen] on_reward_series_complete: {e}")

            fade.bind(on_complete=_on_fade_complete)
            fade.start(img)

        fly.bind(on_complete=_on_fly_complete)

        def _start_series():
            self._play_reward_sound()
            appear.start(img)
            Clock.schedule_once(
                lambda dt: fly.start(img),
                self.reward_appear_duration,
            )

        if delay > 0:
            Clock.schedule_once(lambda dt: _start_series(), delay)
        else:
            _start_series()

    def show_reward(self, amount=1):
        """Показывает amount монеток-награды, летящих к цели с задержкой."""
        try:
            amount = int(amount)
        except Exception:
            amount = 1
        if amount < 1:
            amount = 1

        max_amount = 20
        if amount > max_amount:
            amount = max_amount

        for i in range(amount):
            img = self._create_single_reward()
            is_last = (i == amount - 1)
            delay = i * self.reward_stagger_delay
            self._fly_single_reward(img, delay=delay, is_last=is_last)

    def play_reward(self, amount=1):
        """Публичный метод: показать награду."""
        Clock.schedule_once(lambda dt: self.show_reward(amount=amount), 0.05)