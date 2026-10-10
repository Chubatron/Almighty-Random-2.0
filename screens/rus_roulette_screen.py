import os
import random

from kivy.uix.image import Image
from kivy.uix.behaviors import ButtonBehavior
from kivy.uix.floatlayout import FloatLayout
from kivy.clock import Clock
from kivy.animation import Animation
from kivy.uix.image import Image as KivyImage
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.modalview import ModalView
from kivy.graphics import Color, Line, Rectangle
from kivy.vector import Vector
from kivy.core.window import Window
from kivy.core.audio import SoundLoader
from sound_manager import SoundManager
from screens.base_game_screen import BaseGameScreen

from components.token_widget import TokenWidget
from lucky_token import LuckyToken


class BulletSprite(KivyImage):
    """Спрайт патрона в слоте барабана с поворотом и случайным изображением"""

    def __init__(self, slot_number=0, bullet_size=(100, 100), **kwargs):
        super().__init__(mipmap=True, **kwargs)
        self.slot_number = slot_number
        random_index = random.randint(0, 10)
        self.source = f'assets/images/guns/Bullet_back_{random_index}.png'
        self.size_hint = (None, None)
        self.size = bullet_size
        self.allow_stretch = True
        self.keep_ratio = True
        self.opacity = 0
        self.rotation = random.uniform(0, 360)
        self.is_loaded = False
        self.chamber_sound = None
        self._debug_rect = None

        self.bind(texture=self._smooth_texture)

    def _smooth_texture(self, *args):
        tex = self.texture
        if tex:
            tex.mag_filter = 'linear'
            tex.min_filter = 'linear_mipmap_linear'
            tex.mipmap = True

    def set_loaded(self, loaded):
        self.is_loaded = loaded
        self.opacity = 1 if loaded else 0


class BulletIcon(ButtonBehavior, Image):
    """Иконка патрона в правом верхнем углу (без серого контура)"""

    def __init__(self, **kwargs):
        super().__init__(
            mipmap=True,
            **kwargs
        )
        self.source = 'assets/images/guns/Drum_1024x1024.png'
        self.size_hint = (None, None)
        self.size = (60, 60)
        self.allow_stretch = True
        self.keep_ratio = True
        self._debug_rect = None

        self.bind(texture=self._smooth_texture)

    def _smooth_texture(self, *args):
        tex = self.texture
        if tex:
            tex.mag_filter = 'linear'
            tex.min_filter = 'linear_mipmap_linear'
            tex.mipmap = True


class BulletSlot(Button):
    """Слот для патрона в барабане револьвера"""

    def __init__(self, slot_number=0, **kwargs):
        super().__init__(**kwargs)
        self.slot_number = slot_number
        self.has_bullet = False
        self.is_current = False
        self.background_normal = ''
        self.background_color = (0.2, 0.2, 0.2, 0.8)
        self.color = (1, 1, 1, 1)
        self.font_size = '24sp'
        self.bold = True
        self._debug_rect = None
        self.update_appearance()

    def update_appearance(self):
        if self.has_bullet:
            self.text = "💀"
            self.background_color = (0.8, 0.1, 0.1, 0.9)
        else:
            self.text = "○"
            self.background_color = (0.3, 0.3, 0.3, 0.6)

    def update_current_indicator(self):
        self.canvas.after.clear()
        if self.is_current:
            with self.canvas.after:
                Color(1, 1, 0, 0.8)
                Line(width=3, rectangle=(self.x + 2, self.y + 2, self.width - 4, self.height - 4))

    def set_current(self, is_current):
        self.is_current = is_current
        self.update_current_indicator()

    def toggle_bullet(self):
        self.has_bullet = not self.has_bullet
        self.update_appearance()

    def on_pos(self, *args):
        Clock.schedule_once(lambda dt: self.update_current_indicator(), 0.01)
        if hasattr(self, '_debug_rect') and self._debug_rect:
            self._debug_rect.pos = self.pos

    def on_size(self, *args):
        Clock.schedule_once(lambda dt: self.update_current_indicator(), 0.01)
        if hasattr(self, '_debug_rect') and self._debug_rect:
            self._debug_rect.size = self.size


class ChamberModal(ModalView):
    """Модальное окно барабана для зарядки патронов"""

    reject_sound_path = 'assets/sounds/reject.mp3'

    def __init__(self, main_screen, **kwargs):
        super().__init__(**kwargs)
        self.main_screen = main_screen
        self.background_color = (0, 0, 0, 0)
        self.auto_dismiss = True
        self.size_hint = (1.0, 1.0)
        self.pos_hint = {'center_x': 0.5, 'center_y': 0.5}

        self.layout = FloatLayout()
        self.add_widget(self.layout)

        self.bullet_sprites = []
        self.slot_buttons = []
        self.drum_img = None
        self._debug_drum_rect = None

        self.token_widget = None

        # ✅ Звук отказа
        self.reject_sound = None
        self._load_reject_sound()

        Clock.schedule_once(self.create_chamber_ui, 0.1)

    # ==================== ЗВУК ОТКАЗА ====================

    def _load_reject_sound(self):
        if os.path.exists(self.reject_sound_path):
            self.reject_sound = SoundLoader.load(self.reject_sound_path)
            if self.reject_sound:
                self.reject_sound.volume = 0.8

    def _play_reject_sound(self):
        """Звук отказа — играет, когда нет жетонов."""
        sm = SoundManager()
        if sm.is_muted():
            return
        if self.reject_sound:
            try:
                if self.reject_sound.state == 'play':
                    self.reject_sound.stop()
                self.reject_sound.play()
            except Exception:
                pass

    # ======================================================

    # ==================== ЖЕТОН ВНУТРИ МОДАЛКИ ====================

    def _create_token_widget(self):
        if self.token_widget and self.token_widget.parent:
            return
        # size_hint и pos_hint берутся из TokenWidget.DEFAULT_*
        self.token_widget = TokenWidget()
        self.token_widget.set_value(self.main_screen.tokens.get_balance())
        self.token_widget.set_state(self.main_screen.tokens.get_balance() > 0)
        self.layout.add_widget(self.token_widget)

        self.main_screen.tokens.bind(on_balance_changed=self._on_balance_changed)

    def _on_balance_changed(self, instance, new_balance):
        if self.token_widget:
            self.token_widget.set_value(int(new_balance))
            self.token_widget.set_state(int(new_balance) > 0)

    def _remove_token_widget(self):
        try:
            self.main_screen.tokens.unbind(on_balance_changed=self._on_balance_changed)
        except Exception:
            pass
        self.token_widget = None

    def _flash_token_widget(self):
        """Трижды мигает цифрой в модалке: красный → жёлтый (3 цикла). Шрифт +15%."""
        if not self.token_widget:
            return
        label = self.token_widget.value_label
        if not label:
            return

        # ✅ Звук отказа — играет, когда виджет начинает мигать красным
        self._play_reject_sound()

        yellow = (1, 0.9, 0.2, 1)
        red = (1, 0, 0, 1)

        original_font_size = label.font_size
        label.font_size = original_font_size * 1.15

        schedule = [
            (0.00, red), (0.25, yellow), (0.50, red),
            (0.75, yellow), (1.00, red), (1.25, yellow),
        ]

        def make_apply(color, is_last=False):
            def _apply(dt):
                if not (self.token_widget and self.token_widget.value_label):
                    return
                self.token_widget.value_label.color = color
                if is_last:
                    self.token_widget._update_layout()
            return _apply

        for delay, color in schedule:
            is_last = (delay == schedule[-1][0])
            Clock.schedule_once(make_apply(color, is_last), delay)

    # =========================================================

    def create_chamber_ui(self, dt=None):
        if hasattr(self.main_screen, 'get_screen_width'):
            screen_width = self.main_screen.get_screen_width()
        else:
            screen_width = Window.width

        drum_size = screen_width * 0.8

        try:
            self.drum_img = KivyImage(
                source='assets/images/guns/Drum_1024x1024.png',
                size_hint=(None, None),
                size=(drum_size, drum_size),
                pos_hint={'center_x': 0.5, 'center_y': 0.5},
                allow_stretch=True,
                keep_ratio=True,
                mipmap=True,
            )
            self.layout.add_widget(self.drum_img)
        except:
            pass

        bullet_size_percent = 0.325
        bullet_size = int(drum_size * bullet_size_percent)
        charge_zone_size = int(bullet_size * 1.1)

        drum_x = self.layout.width / 2
        drum_y = self.layout.height / 2

        slot_offsets = [
            (0.155, 0.285),
            (0.33, 0.02),
            (0.18, -0.265),
            (-0.15, -0.265),
            (-0.32, -0.0),
            (-0.17, 0.28),
        ]

        slot_positions = []
        for i, (offset_x, offset_y) in enumerate(slot_offsets):
            x = drum_x + (drum_size * offset_x)
            y = drum_y + (drum_size * offset_y)
            slot_positions.append((x, y))

        for i, (x, y) in enumerate(slot_positions):
            bullet = BulletSprite(
                slot_number=i,
                bullet_size=(bullet_size, bullet_size),
                pos=(x - bullet_size // 2, y - bullet_size // 2)
            )
            if i < len(self.main_screen.bullet_slots):
                bullet.set_loaded(self.main_screen.bullet_slots[i].has_bullet)
            self.bullet_sprites.append(bullet)
            self.layout.add_widget(bullet)

            charge_zone = Button(
                size_hint=(None, None),
                size=(charge_zone_size, charge_zone_size),
                pos=(x - charge_zone_size // 2, y - charge_zone_size // 2),
                background_normal='',
                background_color=(0, 0, 0, 0),
                opacity=0
            )
            charge_zone.bind(on_release=lambda instance, idx=i: self.toggle_slot(idx))
            self.slot_buttons.append(charge_zone)
            self.layout.add_widget(charge_zone)

        self.create_close_image()
        self._create_token_widget()

    def create_close_image(self):
        close_image_path = 'assets/images/guns/load_button.png'

        if os.path.exists(close_image_path):
            class ImageButton(ButtonBehavior, KivyImage):
                pass

            close_btn = ImageButton(
                source=close_image_path,
                size_hint=(None, None),
                size=(200, 200),
                pos_hint={'center_x': 0.5, 'y': 0.05},
                allow_stretch=True,
                keep_ratio=True
            )
        else:
            close_btn = Button(
                text='ЗАКРЫТЬ',
                font_size='20sp',
                bold=True,
                size_hint=(None, None),
                size=(150, 60),
                pos_hint={'center_x': 0.5, 'y': 0.05},
                background_color=(0.3, 0.3, 0.3, 0.8),
                background_normal='',
                color=(1, 1, 1, 1)
            )

        close_btn.bind(on_release=self.close_modal_with_sound)
        self.layout.add_widget(close_btn)

    def toggle_slot(self, slot_index):
        bullet = self.bullet_sprites[slot_index]
        was_loaded = bullet.is_loaded
        new_state = not was_loaded

        tokens = self.main_screen.tokens

        if new_state and not was_loaded:
            if tokens.get_balance() <= 0:
                self._flash_token_widget()
                return
            tokens.spend(1, reason="load_bullet")
        elif was_loaded and not new_state:
            tokens.add(1, reason="unload_bullet")

        bullet.set_loaded(new_state)

        if hasattr(self.main_screen, 'vibrate_short'):
            self.main_screen.vibrate_short()

        if hasattr(self.main_screen, 'play_bullet_load_sound'):
            self.main_screen.play_bullet_load_sound()

    def close_modal(self, instance):
        for i, bullet in enumerate(self.bullet_sprites):
            if i < len(self.main_screen.bullet_slots):
                self.main_screen.bullet_slots[i].has_bullet = bullet.is_loaded
                self.main_screen.bullet_slots[i].update_appearance()

        self.main_screen.total_bullets = sum(1 for s in self.main_screen.bullet_slots if s.has_bullet)
        self.main_screen.update_bullet_counter()
        self.dismiss()

    def close_modal_with_sound(self, instance):
        if hasattr(self.main_screen, 'play_chamber_sound'):
            self.main_screen.play_chamber_sound()
        self.close_modal(instance)

    def dismiss(self, *args, **kwargs):
        self._remove_token_widget()
        super().dismiss(*args, **kwargs)


class RusRouletteScreen(BaseGameScreen):
    """Реалистичная русская рулетка с жестовым управлением"""

    background_image = 'assets/backgrounds/rus_roulette_bg_1024x1024.jpg'
    GUN_WIDTH_COEFF = 1.1

    CHAMBER_HIGHLIGHT_WIDTH_COEFF = 0.2
    CHAMBER_HIGHLIGHT_HEIGHT_COEFF = 0.15
    CHAMBER_HIGHLIGHT_POS_X_COEFF = 0.65
    CHAMBER_HIGHLIGHT_POS_Y_COEFF = 0.55

    reject_sound_path = 'assets/sounds/reject.mp3'

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.name = 'rus_roulette'

        self.gun_image = None
        self.bullet_slots = []
        self.current_slot = 0
        self.result_label = None
        self.shot_counter = None
        self.shots_fired = 0
        self.total_bullets = 0
        self.gun_rotation = 0
        self.bullet_icon = None
        self.touch_start_pos = None
        self.touch_start_time = None
        self.is_dragging = False
        self.drag_start_pos = None
        self.chamber_modal = None
        self.chamber_highlight = None
        self.sound_manager = SoundManager()
        self._tap_timer = None

        self.is_processing_shot = False

        self.chamber_sound = None
        self.gun_shot_sound = None
        self.misfire_sound = None
        self.bullet_load_sound = None
        self.revolve_sound = None

        # --- Жетон ---
        self.tokens = LuckyToken()
        self.token_widget = None

        # ✅ Звук отказа
        self.reject_sound = None
        self._load_reject_sound()

        self.bind(size=self._update_positions)

    def get_screen_width(self):
        return super().get_screen_width()

    def get_screen_height(self):
        return super().get_screen_height()

    # ==================== ЗВУК ОТКАЗА ====================

    def _load_reject_sound(self):
        if os.path.exists(self.reject_sound_path):
            self.reject_sound = SoundLoader.load(self.reject_sound_path)
            if self.reject_sound:
                self.reject_sound.volume = 0.8

    def _play_reject_sound(self):
        """Звук отказа — играет, когда нет жетонов."""
        if self.sound_manager.is_muted():
            return
        if self.reject_sound:
            try:
                if self.reject_sound.state == 'play':
                    self.reject_sound.stop()
                self.reject_sound.play()
            except Exception:
                pass

    # ======================================================

    # ==================== ЗВУКИ ====================

    def play_revolve_sound(self):
        if self.sound_manager.is_muted():
            return
        try:
            if not self.revolve_sound:
                self.revolve_sound = SoundLoader.load('assets/sounds/Roulette/revolve.ogg')
            if self.revolve_sound:
                if self.revolve_sound.state == 'play':
                    self.revolve_sound.stop()
                self.revolve_sound.play()
        except:
            pass

    def play_bullet_load_sound(self):
        if self.sound_manager.is_muted():
            return
        try:
            if not self.bullet_load_sound:
                self.bullet_load_sound = SoundLoader.load('assets/sounds/Roulette/bullet_load.ogg')
            if self.bullet_load_sound:
                if self.bullet_load_sound.state == 'play':
                    self.bullet_load_sound.stop()
                self.bullet_load_sound.play()
        except:
            pass

    def play_chamber_sound(self):
        if self.sound_manager.is_muted():
            return
        try:
            if not self.chamber_sound:
                self.chamber_sound = SoundLoader.load('assets/sounds/Roulette/chamber_out.ogg')
            if self.chamber_sound:
                if self.chamber_sound.state == 'play':
                    self.chamber_sound.stop()
                self.chamber_sound.play()
        except:
            pass

    def play_gun_shot_sound(self):
        if self.sound_manager.is_muted():
            return
        try:
            if not self.gun_shot_sound:
                self.gun_shot_sound = SoundLoader.load('assets/sounds/Roulette/gun_shot.ogg')
            if self.gun_shot_sound:
                if self.gun_shot_sound.state == 'play':
                    self.gun_shot_sound.stop()
                self.gun_shot_sound.play()
        except:
            pass

    def play_misfire_sound(self):
        if self.sound_manager.is_muted():
            return
        try:
            if not self.misfire_sound:
                self.misfire_sound = SoundLoader.load('assets/sounds/Roulette/misfire.ogg')
            if self.misfire_sound:
                if self.misfire_sound.state == 'play':
                    self.misfire_sound.stop()
                self.misfire_sound.play()
        except:
            pass

    # ==================== ЖИЗНЕННЫЙ ЦИКЛ ====================

    def on_enter(self):
        print(f"🎬 [RusRouletteScreen] Вход на экран, is_muted={self.sound_manager.is_muted()}")
        if not self.sound_manager.is_muted():
            self.sound_manager.fade_to(0.05, duration=1.0)
        else:
            print(f"🔇 [RusRouletteScreen] Звук выключен, пропускаем fade_to")
        self.start_game()

    def create_game_screen(self, dt=None):
        self.layout.clear_widgets()
        super().on_enter()

        self.create_gun()
        self.create_back_button()
        self.create_bullet_chamber()
        self.create_info_labels()
        self.create_bullet_icon()
        self.initialize_empty_chamber()
        self.update_bullet_counter()
        self.update_current_slot()

        self._create_token_widget()

        Clock.schedule_once(lambda dt: self.create_chamber_highlight(), 0.2)

    # ==================== ЖЕТОН ====================

    def _create_token_widget(self):
        if self.token_widget and self.token_widget.parent:
            return
        # size_hint и pos_hint берутся из TokenWidget.DEFAULT_*
        self.token_widget = TokenWidget()
        self.token_widget.set_value(self.tokens.get_balance())
        self.token_widget.set_state(self.tokens.get_balance() > 0)
        self.layout.add_widget(self.token_widget)
        self.tokens.bind(on_balance_changed=self._on_balance_changed)

    def _on_balance_changed(self, instance, new_balance):
        if self.token_widget:
            self.token_widget.set_value(int(new_balance))
            self.token_widget.set_state(int(new_balance) > 0)

    def _remove_token_widget(self):
        try:
            self.tokens.unbind(on_balance_changed=self._on_balance_changed)
        except Exception:
            pass
        if self.token_widget and self.token_widget.parent:
            self.layout.remove_widget(self.token_widget)
        self.token_widget = None

    def _flash_token_widget(self):
        """Трижды мигает цифрой: красный → жёлтый (3 цикла). Шрифт +15%."""
        if not self.token_widget:
            return
        label = self.token_widget.value_label
        if not label:
            return

        # ✅ Звук отказа — играет, когда виджет начинает мигать красным
        self._play_reject_sound()

        yellow = (1, 0.9, 0.2, 1)
        red = (1, 0, 0, 1)

        original_font_size = label.font_size
        label.font_size = original_font_size * 1.15

        schedule = [
            (0.00, red), (0.25, yellow), (0.50, red),
            (0.75, yellow), (1.00, red), (1.25, yellow),
        ]

        def make_apply(color, is_last=False):
            def _apply(dt):
                if not (self.token_widget and self.token_widget.value_label):
                    return
                self.token_widget.value_label.color = color
                if is_last:
                    self.token_widget._update_layout()
            return _apply

        for delay, color in schedule:
            is_last = (delay == schedule[-1][0])
            Clock.schedule_once(make_apply(color, is_last), delay)

    def _return_unfired_bullets(self):
        """Возвращает жетоны за невыстреленные патроны."""
        if not self.bullet_slots:
            return
        unfired = sum(1 for s in self.bullet_slots if s.has_bullet)
        if unfired > 0:
            self.tokens.add(unfired, reason="return_unfired")
            for s in self.bullet_slots:
                s.has_bullet = False
                s.update_appearance()
            self.total_bullets = 0
            self.update_bullet_counter()

    # ====================================================

    def update_chamber_highlight_position(self):
        if not self.chamber_highlight or not self.gun_image:
            return

        gun_pos = self.gun_image.pos
        gun_size = self.gun_image.size

        zone_width = gun_size[0] * self.CHAMBER_HIGHLIGHT_WIDTH_COEFF
        zone_height = gun_size[1] * self.CHAMBER_HIGHLIGHT_HEIGHT_COEFF

        pos_x = gun_pos[0] + gun_size[0] * self.CHAMBER_HIGHLIGHT_POS_X_COEFF - zone_width / 2
        pos_y = gun_pos[1] + gun_size[1] * self.CHAMBER_HIGHLIGHT_POS_Y_COEFF - zone_height / 2

        self.chamber_highlight.size = (zone_width, zone_height)
        self.chamber_highlight.pos = (pos_x, pos_y)

        if hasattr(self, 'highlight_rect'):
            self.highlight_rect.pos = self.chamber_highlight.pos
            self.highlight_rect.size = self.chamber_highlight.size

    def create_chamber_highlight(self):
        from kivy.uix.widget import Widget

        if not self.gun_image:
            Clock.schedule_once(lambda dt: self.create_chamber_highlight(), 0.2)
            return

        self.chamber_highlight = Widget()
        self.chamber_highlight.size_hint = (None, None)

        self.update_chamber_highlight_position()

        with self.chamber_highlight.canvas:
            Color(0.5, 0.5, 0.5, 0.5)
            self.highlight_rect = Rectangle(pos=self.chamber_highlight.pos, size=self.chamber_highlight.size)

        self.chamber_highlight.opacity = 0
        self.layout.add_widget(self.chamber_highlight)

    def spin_chamber(self):
        self.play_revolve_sound()
        self.vibrate_custom(600)

        self.current_slot = random.randint(0, 5)

        self.update_chamber_highlight_position()
        self.animate_chamber_highlight()

    def animate_chamber_highlight(self):
        if not self.chamber_highlight:
            return

        if hasattr(self, 'gun_image') and self.gun_image:
            Animation.cancel_all(self.gun_image)
            self.gun_image.opacity = 1

        self.chamber_highlight.opacity = 1
        anim = Animation(opacity=0.2, duration=0.1) + Animation(opacity=0.9, duration=0.1)
        anim.repeat = True
        anim.start(self.chamber_highlight)
        Clock.schedule_once(lambda dt: self.stop_chamber_animation(anim), 0.5)

    def stop_chamber_animation(self, anim):
        if self.chamber_highlight:
            anim.stop(self.chamber_highlight)
            self.chamber_highlight.opacity = 0
        self.finish_spin(0)

    def finish_spin(self, dt):
        self.result_label.color = (1, 1, 1, 1)
        self.update_current_slot()

    def initialize_empty_chamber(self):
        for slot in self.bullet_slots:
            slot.has_bullet = False
            slot.update_appearance()
        self.current_slot = 0
        self.total_bullets = 0

    def create_bullet_icon(self):
        if self.bullet_icon:
            self.layout.remove_widget(self.bullet_icon)

        self.bullet_icon = BulletIcon(pos_hint={'right': 0.95, 'top': 0.95})
        self.bullet_icon.bind(on_release=self.show_chamber_modal)
        self.layout.add_widget(self.bullet_icon)

    def create_gun(self):
        if self.gun_image:
            self.layout.remove_widget(self.gun_image)

        screen_width = self.get_screen_width()
        gun_width = screen_width * self.GUN_WIDTH_COEFF

        try:
            from kivy.core.image import Image as CoreImage
            core_image = CoreImage.load('assets/images/guns/revolver.png')
            orig_width, orig_height = core_image.texture.size
            aspect_ratio = orig_height / orig_width
            gun_height = gun_width * aspect_ratio
        except:
            gun_height = gun_width

        self.gun_image = KivyImage(
            source='assets/images/guns/revolver.png',
            size_hint=(None, None),
            size=(gun_width, gun_height),
            pos_hint={'center_x': 0.5, 'center_y': 0.5},
            allow_stretch=True,
            keep_ratio=True
        )
        self.layout.add_widget(self.gun_image)

        self.gun_image.multitouch_on_box = True
        self.gun_image.bind(on_touch_down=self.on_gun_touch_down)
        self.gun_image.bind(on_touch_move=self.on_gun_touch_move)
        self.gun_image.bind(on_touch_up=self.on_gun_touch_up)

    def create_bullet_chamber(self):
        for slot in self.bullet_slots:
            self.layout.remove_widget(slot)
        self.bullet_slots = []

        for i in range(6):
            slot = BulletSlot(slot_number=i, size_hint=(None, None), size=(1, 1), pos=(-100, -100), opacity=1)
            self.bullet_slots.append(slot)
            self.layout.add_widget(slot)

    def create_info_labels(self):
        title = Label(text='RUSSIAN ROULETTE', font_size='22sp', bold=True, color=(1, 0.2, 0.2, 1),
                      pos_hint={'center_x': 0.5, 'top': 1}, size_hint=(None, None), size=(450, 50))
        self.layout.add_widget(title)

        self.result_label = Label(text='', font_size='14sp', color=(1, 1, 1, 1), halign='center',
                                  pos_hint={'center_x': 0.5, 'top': 0.85}, size_hint=(None, None), size=(500, 60))
        self.layout.add_widget(self.result_label)

    def update_current_slot(self):
        for i, slot in enumerate(self.bullet_slots):
            slot.set_current(i == self.current_slot)

    def check_shot_result(self):
        if not self.bullet_slots or self.current_slot >= len(self.bullet_slots):
            self.result_label.text = 'Ошибка: нет данных о патронах'
            self.result_label.color = (1, 0, 0, 1)
            Clock.schedule_once(self.reset_result_text, 2.0)
            return

        current_slot = self.bullet_slots[self.current_slot]

        if current_slot.has_bullet:
            current_slot.has_bullet = False
            current_slot.update_appearance()
            self.total_bullets -= 1
            self.update_bullet_counter()

        self.shots_fired += 1
        self.current_slot = (self.current_slot + 1) % 6
        self.update_bullet_counter()
        self.gun_rotation = self.gun_rotation % 360
        self.gun_image.rotation = 0
        self.update_current_slot()

    def show_chamber_modal(self, instance):
        self.play_chamber_sound()
        self.chamber_modal = ChamberModal(self)
        self.chamber_modal.open()

    def on_chamber_tap(self):
        if self.is_dragging and self.drag_start_pos:
            self.spin_chamber()
            self.is_dragging = False
            self.drag_start_pos = None

    def on_gun_touch_down(self, instance, touch):
        if not self.gun_image.collide_point(*touch.pos):
            return False

        gun_pos = self.gun_image.pos
        gun_size = self.gun_image.size

        trigger_zone = (
            gun_pos[0] + gun_size[0] * 0.1,
            gun_pos[1] + gun_size[1] * 0.05,
            gun_size[0] * 0.8,
            gun_size[1] * 0.35
        )

        chamber_zone = (
            gun_pos[0] + gun_size[0] * 0.15,
            gun_pos[1] + gun_size[1] * 0.45,
            gun_size[0] * 0.7,
            gun_size[1] * 0.35
        )

        tx, ty = touch.pos

        if (trigger_zone[0] <= tx <= trigger_zone[0] + trigger_zone[2] and
                trigger_zone[1] <= ty <= trigger_zone[1] + trigger_zone[3]):
            self.pull_trigger()
            return True

        elif (chamber_zone[0] <= tx <= chamber_zone[0] + chamber_zone[2] and
              chamber_zone[1] <= ty <= chamber_zone[1] + chamber_zone[3]):
            self.drag_start_pos = touch.pos
            self.is_dragging = True
            self._tap_timer = Clock.schedule_once(lambda dt: self.on_chamber_tap(), 0.1)
            return True

        return True

    def on_gun_touch_move(self, instance, touch):
        if not self.is_dragging or not self.drag_start_pos:
            return False

        dx = touch.pos[0] - self.drag_start_pos[0]
        dy = touch.pos[1] - self.drag_start_pos[1]
        distance = Vector(dx, dy).length()

        if distance > 30:
            if self._tap_timer:
                self._tap_timer.cancel()
                self._tap_timer = None

            self.spin_chamber()
            self.is_dragging = False
            self.drag_start_pos = None

        return True

    def on_gun_touch_up(self, instance, touch):
        if self._tap_timer:
            self._tap_timer.cancel()
            self._tap_timer = None

        self.is_dragging = False
        self.drag_start_pos = None
        return True

    def toggle_slot_bullet(self, slot_index):
        slot = self.bullet_slots[slot_index]
        slot.toggle_bullet()
        self.total_bullets = sum(1 for s in self.bullet_slots if s.has_bullet)
        self.update_bullet_counter()
        self.result_label.text = f'Слот {slot_index + 1}: {"заряжен" if slot.has_bullet else "разряжен"}'
        self.result_label.color = (0.8, 0.8, 0.8, 1)
        Clock.schedule_once(self.reset_result_text, 1.5)

    def update_bullet_counter(self):
        self.total_bullets = sum(1 for s in self.bullet_slots if s.has_bullet)

    def pull_trigger(self):
        if self.is_processing_shot:
            print("⚠️ Выстрел уже обрабатывается, игнорирую")
            return

        self.is_processing_shot = True
        current_slot = self.bullet_slots[self.current_slot]

        if current_slot.has_bullet:
            self.play_gun_shot_sound()
            self.vibrate_long()
            anim = Animation(pos_hint={'center_x': 0.5, 'center_y': 0.46}, duration=0.04)
            anim += Animation(pos_hint={'center_x': 0.5, 'center_y': 0.51}, duration=0.04)
            anim += Animation(pos_hint={'center_x': 0.5, 'center_y': 0.5}, duration=0.04)
            anim.start(self.gun_image)
            Clock.schedule_once(lambda dt: self._finish_shot(), 0.3)
        else:
            self.play_misfire_sound()
            self.vibrate_short()
            anim = Animation(pos_hint={'center_x': 0.5, 'center_y': 0.48}, duration=0.03)
            anim += Animation(pos_hint={'center_x': 0.5, 'center_y': 0.5}, duration=0.03)
            anim.start(self.gun_image)
            Clock.schedule_once(lambda dt: self._finish_shot(), 0.15)

    def _finish_shot(self):
        self.check_shot_result()
        self.is_processing_shot = False

    def reset_result_text(self, dt):
        self.result_label.text = ''

    def start_game(self):
        self.current_slot = 0
        self.shots_fired = 0
        self.total_bullets = 0
        self.gun_rotation = 0
        self.is_processing_shot = False

        for slot in self.bullet_slots:
            slot.has_bullet = False
            slot.update_appearance()

        self.create_game_screen()

    def _update_positions(self, instance, value):
        if self.gun_image:
            screen_width = self.get_screen_width()
            gun_width = screen_width * self.GUN_WIDTH_COEFF

            if hasattr(self.gun_image, 'texture') and self.gun_image.texture:
                orig_width, orig_height = self.gun_image.texture.size
                aspect_ratio = orig_height / orig_width
                gun_height = gun_width * aspect_ratio
            else:
                gun_height = gun_width

            self.gun_image.size = (gun_width, gun_height)
            self.update_chamber_highlight_position()

        if self.bullet_slots:
            Clock.schedule_once(lambda dt: self.create_bullet_chamber(), 0.1)

    def on_leave(self):
        print(f"🎬 [RusRouletteScreen] Выход с экрана, is_muted={self.sound_manager.is_muted()}")
        if not self.sound_manager.is_muted():
            self.sound_manager.fade_to(1.0, duration=0.5)
        else:
            print(f"🔇 [RusRouletteScreen] Звук выключен, пропускаем fade_to")

        for sound in [self.chamber_sound, self.gun_shot_sound, self.misfire_sound,
                      self.bullet_load_sound, self.revolve_sound]:
            if sound:
                sound.stop()

        self._return_unfired_bullets()
        self._remove_token_widget()

        super().on_leave()

    def go_to_menu(self):
        print(f"🏠 [RusRouletteScreen] Возврат в меню, is_muted={self.sound_manager.is_muted()}")
        if not self.sound_manager.is_muted():
            self.sound_manager.fade_to(1.0, duration=0.5)

        self._return_unfired_bullets()
        self._remove_token_widget()

        from main import switch_screen
        switch_screen('menu')