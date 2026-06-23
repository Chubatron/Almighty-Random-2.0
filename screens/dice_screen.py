"""
Dice Screen - экран с кубиками из спрайт-листа
"""
import os
import random
import math
import inspect
from kivy.app import App
from kivy.uix.image import Image
from kivy.uix.widget import Widget
from kivy.graphics import Color, Rectangle, Ellipse
from kivy.properties import StringProperty, NumericProperty
from kivy.clock import Clock
from kivy.animation import Animation
from kivy.core.window import Window
from kivy.utils import platform
from kivy.core.audio import SoundLoader
from kivy.uix.behaviors import ButtonBehavior
from kivy.uix.image import Image as KivyImage

from screens.base_game_screen import BaseGameScreen
from screens.dice import (
    DropZone, PointMarker, DiceWidget, GlassWidget, ShadowWidget
)
from screens.dice.magnetic_field import MagneticField
from screens.dice.particle_effects import ParticleSystem

# ===== НАСТРОЙКИ ОТЛАДКИ =====
DEBUG_MODE = False
# =============================


class DiceScreen(BaseGameScreen):
    """Экран с кубиками на столе и стаканом рядом"""

    # КОЭФФИЦИЕНТЫ ДЛЯ КНОПКИ BACK_TO_MENU
    BACK_BUTTON_SIZE_COEFF = 0.12
    BACK_BUTTON_POS_X_COEFF = 0.05
    BACK_BUTTON_POS_Y_COEFF = 0.91

    background_image = StringProperty('assets/backgrounds/dice_bg_dark.png')
    background_bright_image = StringProperty('assets/backgrounds/dice_bg.png')
    sprite_sheet_path = StringProperty('assets/sprites/spritesheet_cube.png')
    enlarge_sprite_sheet_path = StringProperty('assets/sprites/spritesheet_cube_changed.png')
    glass_sprite_sheet_path = StringProperty('assets/sprites/spritesheet_glass12.png')
    shadow_sprite_sheet_path = StringProperty('assets/sprites/spritesheet_shadow.png')

    shadow_scale_factor = NumericProperty(2.6)
    shadow_rotation = NumericProperty(-90)
    shadow_offset_x_factor = NumericProperty(-1.25)
    shadow_offset_y_factor = NumericProperty(-0.35)
    shadow_opacity = NumericProperty(0.7)
    shadow_move_factor_x = NumericProperty(-1.0)
    shadow_move_factor_y = NumericProperty(0.0)

    ANIMATION_DURATION = 1.5
    FIRST_ANIMATION_DURATION = 1
    SECOND_ANIMATION_DURATION = 1

    # Параметры системы заряда яркости
    BRIGHTNESS_CHARGE_RATE = 0.001
    BRIGHTNESS_DRAIN_RATE = 0.25
    MAX_BRIGHTNESS = 1.0
    MIN_BRIGHTNESS = 0.0

    # Задержка звука для анимаций перехода (секунды)
    SOUND_DELAY = 0.15

    # Параметры притяжения кубиков к стакану (коэффициенты от размера кубика)
    MAGNETIC_DISTANCE_X_FACTOR = 1.3
    MAGNETIC_DISTANCE_Y_FACTOR = 2.0
    MAGNETIC_FORCE_FACTOR = 0.8

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self.disappear_duration = 0.3
        self.appear_duration = 0.3
        self.overlap_time = 0.2

        self.single_dice_size = 0
        self.double_dice_size = 0
        self.large_dice_size = 0
        self.glass_size = 0
        self.shadow_size = 0

        self.START_POSITION_DICE_X = 0
        self.START_POSITION_DICE_Y = 0
        self.START_POSITION_GLASS_X = 0
        self.START_POSITION_GLASS_Y = 0
        self.SHADOW_POSITION_X = 0
        self.SHADOW_POSITION_Y = 0
        self.SHADOW_TARGET_POSITION_X = 0
        self.SHADOW_TARGET_POSITION_Y = 0

        self.dice_list = []
        self.glass = None
        self.shadow = None
        self.drop_zone = None
        self.point_a_marker = None
        self.current_mode = 1
        self.bg_dark = None
        self.bg_bright = None
        self.is_animating = False
        self.animation_counter = 0
        self.dice_hidden = False
        self.pending_hide_dice = False

        self.glass_start_pos = None
        self.glass_target_pos = None
        self.is_at_target = True

        self.last_dice_center = None
        self.saved_point_a_position = None
        self.saved_dice_positions = []

        self.last_touch_pos = None
        self.last_touch_time = None
        self.max_speed = 0
        self.has_moved_with_dice = False

        # Система отслеживания пути для яркости
        self.total_distance_traveled = 0.0
        self.current_brightness = 0.0
        self.drain_clock = None
        self.is_charging = False
        self.is_draining_scheduled = False
        self._reset_charge_clock = None

        self.sound_glass_lower = None
        self.sound_glass_raise = None
        self.sound_dice_roll = None
        self.sound_glass_drag = None
        self.sound_dice_appear = None
        self.sound_dice_disappear = None

        self.volume_fade_clock = None
        self.target_volume = 0.0

        self.is_dice_enlarged = False
        self.is_glass_blocked = False
        self.is_dice_blocked = False

        # Для визуализации зоны отладки
        self._drop_zone_visualization = None

        # Эффект магнитного поля
        self.magnetic_field = None

        # Система частиц
        self.particle_system = None

        # ===== ДЛЯ ВРАЩЕНИЯ КУБА ПРИ КОНТАКТЕ С МАГНИТНЫМ ПОЛЕМ =====
        self.frame_change_threshold = 40.0
        self.contact_monitor = None
        self.dice_contact_flags = {}
        self.dice_frame_accumulators = {}

    def get_screen_size(self):
        if platform == 'android':
            width, height = Window.system_size
        else:
            width = Window.width
            height = Window.height
        return width, height

    def create_back_button(self):
        """Переопределяем родительский метод - создаем свою кнопку вместо стандартной"""
        if self.back_button and self.back_button in self.layout.children:
            self.layout.remove_widget(self.back_button)
            self.back_button = None
        self.create_custom_back_button()

    def create_custom_back_button(self):
        """Создает кастомную кнопку возврата в меню"""
        screen_width = self.get_screen_width()
        btn_size = screen_width * self.BACK_BUTTON_SIZE_COEFF

        class ImageButton(ButtonBehavior, KivyImage):
            pass

        back_btn = ImageButton(
            source='assets/images/buttons/Orange_back_to_menu_button_90.png',
            size_hint=(None, None),
            size=(btn_size, btn_size),
            pos_hint={
                'x': self.BACK_BUTTON_POS_X_COEFF,
                'y': self.BACK_BUTTON_POS_Y_COEFF
            },
            allow_stretch=True
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

    def _print_widget_order(self, event_name=""):
        """Отладочная функция для вывода порядка виджетов"""
        if not DEBUG_MODE:
            return
        print(f"\n📊 [Z-ORDER] {event_name}")
        for i, child in enumerate(reversed(self.layout.children)):
            name = child.__class__.__name__
            if "DiceWidget" in name:
                widget_type = "🎲 КУБИК"
            elif "GlassWidget" in name:
                widget_type = "🥛 СТАКАН"
            elif "ShadowWidget" in name:
                widget_type = "🌑 ТЕНЬ"
            elif "DropZone" in name:
                widget_type = "🔵 ЗОНА"
            elif "PointMarker" in name:
                widget_type = "🔴 ТОЧКА_А"
            elif "Image" in name and "bg" in str(child.source).lower():
                widget_type = "🖼️ ФОН"
            elif "ParticleSystem" in name:
                widget_type = "✨ ЧАСТИЦЫ"
            elif "ImageButton" in name or "ButtonBehavior" in str(child.__class__):
                widget_type = "🔙 КНОПКА"
            else:
                widget_type = "❓ ДРУГОЕ"
            print(f"   {i}: {widget_type} - {name}")

    def _is_dice_above_glass(self, dice):
        """Определяет, находится ли кубик над стаканом (по Z-порядку)"""
        if not self.glass or not dice:
            return False

        glass_index = self.layout.children.index(self.glass) if self.glass in self.layout.children else -1
        dice_index = self.layout.children.index(dice) if dice in self.layout.children else -1
        return dice_index > glass_index

    def _ensure_dice_above_glass_for_animation(self):
        """Поднимает кубики над стаканом для анимации переключения режимов"""
        if not self.glass or not self.dice_list:
            return

        glass_center_x = self.glass.pos[0] + self.glass.width / 2

        for dice in self.dice_list:
            dice_center_x = dice.pos[0] + dice.width / 2

            if dice_center_x < glass_center_x:
                if dice.parent:
                    dice.parent.remove_widget(dice)
                self.layout.add_widget(dice)

                if DEBUG_MODE:
                    print(f"🎲 [Z-ORDER] Кубик поднят НАД стаканом для анимации")
            else:
                if DEBUG_MODE:
                    print(f"🎲 [Z-ORDER] Кубик остается ПОД стаканом")

        if self.glass and self.glass.parent:
            self.glass.parent.remove_widget(self.glass)
            self.layout.add_widget(self.glass)

    def _ensure_glass_on_top_during_lowering(self):
        """Поднимает стакан и тень ПОВЕРХ всех кубиков (для анимации опускания)"""
        if self.glass and self.glass.parent:
            self.glass.parent.remove_widget(self.glass)
        if self.glass:
            self.layout.add_widget(self.glass)

        if self.shadow and self.shadow.parent:
            self.shadow.parent.remove_widget(self.shadow)
        if self.shadow:
            self.layout.add_widget(self.shadow)

        if DEBUG_MODE:
            print("🥛 [GLASS] Стакан и тень подняты ПОВЕРХ всех кубиков для анимации опускания")

    def _update_dice_z_order(self):
        """Обновляет Z-порядок кубиков относительно стакана."""
        if not self.glass or not self.dice_list:
            return

        if not self.is_at_target:
            if self.glass.parent:
                self.glass.parent.remove_widget(self.glass)
            for dice in self.dice_list:
                if dice.parent:
                    dice.parent.remove_widget(dice)
            self.layout.add_widget(self.glass)
            for dice in self.dice_list:
                self.layout.add_widget(dice)
            if DEBUG_MODE:
                print(f"📊 [Z-ORDER] Стакан ПОДНЯТ: {len(self.dice_list)} кубиков НАД стаканом")
            return

        if self.dice_hidden:
            for dice in self.dice_list:
                if dice.parent:
                    dice.parent.remove_widget(dice)
            for dice in self.dice_list:
                self.layout.add_widget(dice, index=0)
            if self.glass.parent:
                self.glass.parent.remove_widget(self.glass)
            self.layout.add_widget(self.glass)
            if DEBUG_MODE:
                print(f"📊 [Z-ORDER] Стакан ОПУЩЕН и НАД кубами: стакан ВЫШЕ всех кубиков")
            return

        point_a_x = self._get_current_point_a_position()[0]
        above_glass = []
        below_glass = []

        for dice in self.dice_list:
            dice_center_x = dice.pos[0] + dice.width / 2
            if dice_center_x < point_a_x:
                above_glass.append(dice)
            else:
                below_glass.append(dice)

        if self.glass.parent:
            self.glass.parent.remove_widget(self.glass)
        for dice in self.dice_list:
            if dice.parent:
                dice.parent.remove_widget(dice)

        for dice in below_glass:
            self.layout.add_widget(dice)
        if self.glass:
            self.layout.add_widget(self.glass)
        for dice in above_glass:
            self.layout.add_widget(dice)

        if DEBUG_MODE:
            print(f"📊 [Z-ORDER] Стакан ОПУЩЕН (кубики видны): {len(above_glass)} кубиков НАД стаканом, {len(below_glass)} кубиков ПОД стаканом")

    def _get_center_positions(self):
        screen_width, screen_height = self.get_screen_size()
        center_x = screen_width / 2
        pos1_y = screen_height * 0.33
        pos2_y = screen_height * 0.5
        pos3_y = screen_height * 0.66

        if DEBUG_MODE:
            print(f"🎯 [CENTER] Экран: {screen_width:.0f}x{screen_height:.0f}")
            print(f"   Центр экрана: ({center_x:.0f}, {screen_height/2:.0f})")
            print(f"   Позиция 1: ({center_x:.0f}, {pos1_y:.0f})")
            print(f"   Позиция 2: ({center_x:.0f}, {pos2_y:.0f})")
            print(f"   Позиция 3: ({center_x:.0f}, {pos3_y:.0f})")

        return {
            'pos1': (center_x, pos1_y),
            'pos2': (center_x, pos2_y),
            'pos3': (center_x, pos3_y)
        }

    def _get_dice_target_position(self, dice, mode='grow'):
        positions = self._get_center_positions()
        if mode == 'grow':
            if len(self.dice_list) == 1:
                target_x = positions['pos2'][0] - dice.width / 2
                target_y = positions['pos2'][1] - dice.height / 2
                return (target_x, target_y)
            else:
                index = self.dice_list.index(dice) if dice in self.dice_list else 0
                if index == 0:
                    target_x = positions['pos1'][0] - dice.width / 2
                    target_y = positions['pos1'][1] - dice.height / 2
                else:
                    target_x = positions['pos3'][0] - dice.width / 2
                    target_y = positions['pos3'][1] - dice.height / 2
                return (target_x, target_y)
        else:
            if hasattr(dice, 'original_position') and dice.original_position:
                return dice.original_position
            return (self.START_POSITION_DICE_X, dice.pos[1] if len(self.dice_list) > 1 else self.START_POSITION_DICE_Y)

    def _get_dice_original_positions(self):
        screen_width, screen_height = self.get_screen_size()
        positions = {}
        if len(self.dice_list) == 1:
            x = self.START_POSITION_DICE_X
            y = self.START_POSITION_DICE_Y
            positions[0] = (x, y)
        else:
            distance_between = self.double_dice_size * 0.3
            center_y = self.START_POSITION_DICE_Y + (self.single_dice_size // 2) - (self.double_dice_size // 2)
            y_top = center_y - distance_between
            y_bottom = center_y + distance_between
            positions[0] = (self.START_POSITION_DICE_X, y_top)
            positions[1] = (self.START_POSITION_DICE_X, y_bottom)
        return positions

    def _load_dice_sounds(self):
        try:
            if os.path.exists('assets/sounds/dice/glass_lower.mp3'):
                self.sound_glass_lower = SoundLoader.load('assets/sounds/dice/glass_lower.mp3')
                if self.sound_glass_lower:
                    print("✅ Загружен звук: glass_lower.mp3")

            if os.path.exists('assets/sounds/dice/glass_raise.mp3'):
                self.sound_glass_raise = SoundLoader.load('assets/sounds/dice/glass_raise.mp3')
                if self.sound_glass_raise:
                    print("✅ Загружен звук: glass_raise.mp3")

            if os.path.exists('assets/sounds/dice/dice_roll.mp3'):
                self.sound_dice_roll = SoundLoader.load('assets/sounds/dice/dice_roll.mp3')
                if self.sound_dice_roll:
                    print("✅ Загружен звук: dice_roll.mp3")

            if os.path.exists('assets/sounds/dice/glass_drag.mp3'):
                self.sound_glass_drag = SoundLoader.load('assets/sounds/dice/glass_drag.mp3')
                if self.sound_glass_drag:
                    self.sound_glass_drag.loop = True
                    self.sound_glass_drag.volume = 0.0
                    self.sound_glass_drag.play()
                    print("✅ Загружен звук: glass_drag.mp3 (зацикленный)")

            if os.path.exists('assets/sounds/dice/dice_appear.mp3'):
                self.sound_dice_appear = SoundLoader.load('assets/sounds/dice/dice_appear.mp3')
                if self.sound_dice_appear:
                    print("✅ Загружен звук: dice_appear.mp3")

            if os.path.exists('assets/sounds/dice/dice_disappear.mp3'):
                self.sound_dice_disappear = SoundLoader.load('assets/sounds/dice/dice_disappear.mp3')
                if self.sound_dice_disappear:
                    print("✅ Загружен звук: dice_disappear.mp3")

        except Exception as e:
            print(f"Ошибка загрузки звуков кубиков: {e}")

    def _fade_volume(self, target_volume, duration=0.2):
        if not self.sound_glass_drag:
            return

        self.target_volume = target_volume
        start_volume = self.sound_glass_drag.volume

        if self.volume_fade_clock:
            self.volume_fade_clock.cancel()
            self.volume_fade_clock = None

        def update_volume(step, steps):
            if step <= 0:
                self.sound_glass_drag.volume = target_volume
                self.volume_fade_clock = None
                return

            progress = step / steps
            self.sound_glass_drag.volume = start_volume + (target_volume - start_volume) * (1 - progress)

            self.volume_fade_clock = Clock.schedule_once(
                lambda dt: update_volume(step - 1, steps),
                duration / steps
            )

        steps = 20
        update_volume(steps, steps)

    def play_dice_roll_sound(self):
        if self.sound_dice_roll and not self.sound_manager.is_muted():
            self.sound_dice_roll.play()
            self.sound_manager.vibrate_short()

    def play_dice_appear_sound(self):
        if self.sound_dice_appear and not self.sound_manager.is_muted():
            self.sound_dice_appear.play()
            self.sound_manager.vibrate_short()

    def play_dice_disappear_sound(self):
        if self.sound_dice_disappear and not self.sound_manager.is_muted():
            self.sound_dice_disappear.play()
            self.sound_manager.vibrate_short()

    def _block_glass(self):
        self.is_glass_blocked = True
        if DEBUG_MODE:
            print("🔒 [GLASS] Стакан заблокирован")

    def _unblock_glass(self):
        self.is_glass_blocked = False
        if DEBUG_MODE:
            print("🔓 [GLASS] Стакан разблокирован")

    def _block_dice(self):
        self.is_dice_blocked = True
        if DEBUG_MODE:
            print("🔒 [DICE] Кубики заблокированы")

    def _unblock_dice(self):
        self.is_dice_blocked = False
        if DEBUG_MODE:
            print("🔓 [DICE] Кубики разблокированы")

    def _update_brightness(self, delta_distance=0):
        """Обновление яркости фона на основе пройденного пути"""
        if delta_distance > 0 and self.dice_hidden:
            old_brightness = self.current_brightness
            self.current_brightness += delta_distance * self.BRIGHTNESS_CHARGE_RATE

            reached_max = False
            if self.current_brightness >= self.MAX_BRIGHTNESS:
                self.current_brightness = self.MAX_BRIGHTNESS
                reached_max = True

            self.is_charging = True

            if reached_max:
                self._cancel_drain()
                if DEBUG_MODE and old_brightness < self.MAX_BRIGHTNESS:
                    print("💡 [BRIGHTNESS] Достигнут максимум! Яркость зафиксирована")
                self.sound_manager.vibrate_long()

                if self.particle_system:
                    self.particle_system.set_glow_mode(True)
            else:
                self._start_drain()

        if self.bg_dark and self.bg_bright:
            self.bg_bright.opacity = self.current_brightness
            self.bg_dark.opacity = 1.0 - self.current_brightness

        if DEBUG_MODE and delta_distance > 0:
            print(f"💡 [BRIGHTNESS] Яркость: {self.current_brightness:.3f}")

    def _start_drain(self):
        """Запуск процесса разрядки яркости"""
        if self.current_brightness <= self.MIN_BRIGHTNESS:
            return

        if self.drain_clock and self.is_draining_scheduled:
            return

        if self.drain_clock:
            self.drain_clock.cancel()
            self.drain_clock = None

        self.is_draining_scheduled = True

        def drain_step(dt):
            if self.is_charging:
                if DEBUG_MODE:
                    print("💡 [DRAIN] Прервано из-за зарядки")
                self.is_draining_scheduled = False
                self.drain_clock = None
                return

            if self.current_brightness > self.MIN_BRIGHTNESS:
                self.current_brightness -= self.BRIGHTNESS_DRAIN_RATE * dt
                if self.current_brightness < self.MIN_BRIGHTNESS:
                    self.current_brightness = self.MIN_BRIGHTNESS

                if self.bg_dark and self.bg_bright:
                    self.bg_bright.opacity = self.current_brightness
                    self.bg_dark.opacity = 1.0 - self.current_brightness

                if DEBUG_MODE:
                    print(f"💡 [DRAIN] Яркость: {self.current_brightness:.3f}")

                if self.current_brightness > self.MIN_BRIGHTNESS and not self.is_charging:
                    self.drain_clock = Clock.schedule_once(drain_step, 0.05)
                    self.is_draining_scheduled = True
                else:
                    self.drain_clock = None
                    self.is_draining_scheduled = False
            else:
                self.drain_clock = None
                self.is_draining_scheduled = False

                if self.particle_system:
                    self.particle_system.set_glow_mode(False)

        self.drain_clock = Clock.schedule_once(drain_step, 0.05)

    def _cancel_drain(self):
        """Отмена разрядки"""
        if self.drain_clock:
            self.drain_clock.cancel()
            self.drain_clock = None
        self.is_draining_scheduled = False
        if DEBUG_MODE:
            print("💡 [DRAIN] Разрядка отменена")

    def _reset_brightness(self):
        """Сброс яркости (полное затемнение) - только при перезагрузке экрана"""
        self.total_distance_traveled = 0.0
        self.current_brightness = 0.0
        self.is_charging = False
        self._cancel_drain()

        if self.bg_dark and self.bg_bright:
            self.bg_bright.opacity = 0.0
            self.bg_dark.opacity = 1.0

        if self.particle_system:
            self.particle_system.set_glow_mode(False)

        if DEBUG_MODE:
            print("💡 [BRIGHTNESS] Яркость сброшена на 0")

    def _animate_dice_grow_with_move(self, dice, target_size, target_position, on_complete_callback=None):
        if DEBUG_MODE:
            print(f"🎬 [GROW] Начало анимации УВЕЛИЧЕНИЯ кубика")
        if hasattr(dice, 'is_animating_scale') and dice.is_animating_scale:
            return
        dice.is_animating_scale = True

        self._block_glass()

        if dice.original_center is None:
            original_center_x = dice.pos[0] + dice.width / 2
            original_center_y = dice.pos[1] + dice.height / 2
            dice.original_center = (original_center_x, original_center_y)

        if dice.glow:
            anim_glow_fade = Animation(opacity=0, duration=0.3)
            anim_glow_fade.start(dice.glow)

        dice.load_enlarge_spritesheet(self.enlarge_sprite_sheet_path)

        current_frame = dice.frame_index
        dice.animate_enlarge(current_frame, duration=self.FIRST_ANIMATION_DURATION + self.SECOND_ANIMATION_DURATION)

        anim_grow = Animation(dice_size=target_size, duration=self.SECOND_ANIMATION_DURATION, t='linear')
        anim_move = Animation(pos=target_position, duration=self.SECOND_ANIMATION_DURATION, t='linear')

        def on_complete(*args):
            dice.is_animating_scale = False
            self.is_dice_enlarged = True
            dice.enlarged_size = target_size
            self._unblock_dice()

            if self.particle_system:
                self.particle_system.set_glow_mode(False)

            if on_complete_callback:
                on_complete_callback()
            self._print_widget_order("После анимации УВЕЛИЧЕНИЯ кубика")
            if DEBUG_MODE:
                print(f"🎬 [GROW] Завершение анимации увеличения кубика")

        anim_grow.bind(on_complete=on_complete)
        anim_grow.start(dice)
        anim_move.start(dice)

    def _animate_dice_shrink_with_move(self, dice, original_size, target_position, on_complete_callback=None):
        if DEBUG_MODE:
            print(f"🎬 [SHRINK] Начало анимации УМЕНЬШЕНИЯ кубика")
        if hasattr(dice, 'is_animating_scale') and dice.is_animating_scale:
            return
        dice.is_animating_scale = True

        if dice.original_center is None:
            original_center_x = dice.pos[0] + dice.width / 2
            original_center_y = dice.pos[1] + dice.height / 2
        else:
            original_center_x, original_center_y = dice.original_center

        corrected_original_x = original_center_x - original_size / 2
        corrected_original_y = original_center_y - original_size / 2

        dice.load_enlarge_spritesheet(self.enlarge_sprite_sheet_path)

        current_frame = dice.frame_index
        dice.animate_shrink(current_frame, duration=self.FIRST_ANIMATION_DURATION + self.SECOND_ANIMATION_DURATION)

        if dice.glow:
            dice.glow.opacity = 0
            Clock.schedule_once(lambda dt: self._appear_glow(dice.glow), self.ANIMATION_DURATION + 0.3)

        anim_shrink = Animation(dice_size=original_size, duration=self.SECOND_ANIMATION_DURATION * 2, t='linear')
        anim_move_back = Animation(pos=target_position, duration=self.SECOND_ANIMATION_DURATION * 2, t='linear')

        def on_complete(*args):
            dice.is_animating_scale = False
            dice.original_center = None

            if self.particle_system:
                self.particle_system.set_glow_mode(True)
                Clock.schedule_once(lambda dt: self.particle_system.set_glow_mode(False) if self.particle_system else None, 0.5)

            if on_complete_callback:
                on_complete_callback()
            self._print_widget_order("После анимации УМЕНЬШЕНИЯ кубика")
            if DEBUG_MODE:
                print(f"🎬 [SHRINK] Завершение анимации уменьшения кубика")

        anim_shrink.bind(on_complete=on_complete)
        anim_shrink.start(dice)
        anim_move_back.start(dice)

    def _appear_glow(self, glow):
        if glow:
            anim = Animation(opacity=1, duration=0.1)
            anim.start(glow)

    def _bring_dice_above_glass(self):
        """Поднимает кубики над стаканом (для анимации увеличения)"""
        for dice in self.dice_list:
            if dice.parent:
                dice.parent.remove_widget(dice)
                self.layout.add_widget(dice)
        if DEBUG_MODE:
            print("🎲 [LAYER] Кубики подняты НАД стаканом")
        self._print_widget_order("После поднятия кубиков НАД стаканом")

    def _animate_dice_appearance(self):
        """Анимация увеличения кубиков - они летят к трем точкам на экране"""
        if DEBUG_MODE:
            print("🎬 [APPEAR] НАЧАЛО анимации появления/увеличения кубиков")

        self._bring_dice_above_glass()
        self._block_dice()

        self.saved_point_a_position = self._get_current_point_a_position()
        if DEBUG_MODE:
            print(f"📌 [ANIM] Сохранена точка А для возврата: {self.saved_point_a_position}")

        positions = self._get_center_positions()
        original_positions = self._get_dice_original_positions()

        completed_animations = [0]
        total_dice = len(self.dice_list)

        def check_all_complete():
            completed_animations[0] += 1
            if completed_animations[0] >= total_dice:
                self._print_widget_order("После завершения анимации APPEAR")
                if DEBUG_MODE:
                    print("🎬 [APPEAR] ЗАВЕРШЕНИЕ анимации появления/увеличения кубиков")

        for i, dice in enumerate(self.dice_list):
            if not hasattr(dice, 'original_position') or dice.original_position is None:
                dice.original_position = original_positions.get(i, dice.pos)

            if not hasattr(dice, 'original_size') or dice.original_size is None:
                dice.original_size = dice.dice_size

            if dice.original_center is None:
                original_center_x = dice.pos[0] + dice.width / 2
                original_center_y = dice.pos[1] + dice.height / 2
                dice.original_center = (original_center_x, original_center_y)

            target_size = dice.original_size * 5

            if len(self.dice_list) == 1:
                target_x = positions['pos2'][0] - target_size / 2
                target_y = positions['pos2'][1] - target_size / 2
                if DEBUG_MODE:
                    print(f"🎲 [APPEAR] Один кубик летит в центр: ({target_x:.0f}, {target_y:.0f})")
            else:
                if i == 0:
                    target_x = positions['pos1'][0] - target_size / 2
                    target_y = positions['pos1'][1] - target_size / 2
                    if DEBUG_MODE:
                        print(f"🎲 [APPEAR] Верхний кубик летит в верхнюю точку: ({target_x:.0f}, {target_y:.0f})")
                else:
                    target_x = positions['pos3'][0] - target_size / 2
                    target_y = positions['pos3'][1] - target_size / 2
                    if DEBUG_MODE:
                        print(f"🎲 [APPEAR] Нижний кубик летит в нижнюю точку: ({target_x:.0f}, {target_y:.0f})")

            self._animate_dice_grow_with_move(dice, target_size, (target_x, target_y), check_all_complete)

    def _send_dice_below_glass(self):
        """Опускает кубики под стакан (после анимации)"""
        for dice in self.dice_list:
            if dice.parent:
                dice.parent.remove_widget(dice)

        for dice in self.dice_list:
            self.layout.add_widget(dice, index=0)

        if self.glass and self.glass.parent:
            self.glass.parent.remove_widget(self.glass)
        if self.glass:
            self.layout.add_widget(self.glass)

        if DEBUG_MODE:
            print("🥛 [GLASS] Кубики опущены ПОД стакан")

    def _shrink_all_dice(self, on_complete_callback=None):
        if DEBUG_MODE:
            print("🎬 [SHRINK_ALL] НАЧАЛО анимации уменьшения ВСЕХ кубиков")

        if not self.is_dice_enlarged:
            if on_complete_callback:
                on_complete_callback()
            return

        self._block_dice()

        completed_animations = [0]
        total_dice = len(self.dice_list)

        def check_all_complete():
            completed_animations[0] += 1
            if completed_animations[0] >= total_dice:
                self.is_dice_enlarged = False
                self._unblock_glass()
                self._unblock_dice()
                self._send_dice_below_glass()

                if on_complete_callback:
                    on_complete_callback()
                if self.current_brightness > 0:
                    self.is_charging = False
                    self._start_drain()
                self._print_widget_order("После завершения анимации SHRINK_ALL")
                if DEBUG_MODE:
                    print("🎬 [SHRINK_ALL] ЗАВЕРШЕНИЕ анимации уменьшения ВСЕХ кубиков")

        for dice in self.dice_list:
            original_size = getattr(dice, 'original_size', dice.dice_size)
            if self.saved_point_a_position:
                point_a_x, point_a_y = self.saved_point_a_position
                if len(self.dice_list) == 1:
                    target_x = point_a_x - original_size / 2
                    target_y = point_a_y - original_size / 2
                else:
                    distance_between = self.double_dice_size * 0.3
                    index = self.dice_list.index(dice)
                    if index == 0:
                        target_y = point_a_y - distance_between - original_size / 2
                    else:
                        target_y = point_a_y + distance_between - original_size / 2
                    target_x = point_a_x - original_size / 2
                if DEBUG_MODE:
                    print(f"🎲 [SHRINK] Кубик возвращается в точку А: ({target_x:.0f}, {target_y:.0f})")
            else:
                target_x, target_y = dice.original_position
                if DEBUG_MODE:
                    print(f"🎲 [SHRINK] Кубик возвращается в original_position: ({target_x:.0f}, {target_y:.0f})")

            self._animate_dice_shrink_with_move(dice, original_size, (target_x, target_y), check_all_complete)

    def _raise_glass(self, on_complete_callback=None):
        if DEBUG_MODE:
            print("🥛 [GLASS] НАЧАЛО поднятия стакана")

        if self.magnetic_field:
            self.magnetic_field.stop()

        self._block_dice()

        if self.sound_glass_raise and not self.sound_manager.is_muted():
            self.sound_glass_raise.play()
            self.sound_manager.vibrate_short()

        shadow_target_pos = (self.SHADOW_TARGET_POSITION_X, self.SHADOW_TARGET_POSITION_Y)

        for dice in self.dice_list:
            if dice.glow:
                dice.glow.update_position(dice.pos, dice.dice_size)
            dice.enable_glow()

        self._print_widget_order("Перед поднятием стакана")

        def on_animation_complete(*args):
            self.is_at_target = False
            if self._on_glass_move_complete:
                self._on_glass_move_complete()
            if on_complete_callback:
                on_complete_callback()
            self._update_point_a_marker()
            self._unblock_dice()
            self._update_glass_highlight()
            self._print_widget_order("После поднятия стакана")
            self._update_dice_z_order()
            if DEBUG_MODE:
                print("🥛 [GLASS] ЗАВЕРШЕНИЕ поднятия стакана")

        self.glass.animate_movement(
            start_pos=self.glass_start_pos,
            end_pos=self.glass_target_pos,
            duration=0.6,
            forward=True,
            callback=on_animation_complete
        )

        self.shadow.animate_movement_to_target(
            target_pos=shadow_target_pos,
            duration=0.6,
            forward=True
        )

    def _lower_glass(self):
        if DEBUG_MODE:
            print("🥛 [GLASS] НАЧАЛО опускания стакана")

        if self.magnetic_field:
            self.magnetic_field.update_glass_position(self.glass_start_pos)

        self._block_dice()
        self._ensure_glass_on_top_during_lowering()

        self.max_speed = 0
        self.last_touch_pos = None
        self.last_touch_time = None

        self.shadow.pos = (self.SHADOW_TARGET_POSITION_X, self.SHADOW_TARGET_POSITION_Y)
        shadow_target_pos = (self.SHADOW_POSITION_X, self.SHADOW_POSITION_Y)

        self._print_widget_order("Перед опусканием стакана")

        def on_animation_complete(*args):
            self.is_at_target = True
            if self.sound_glass_lower and not self.sound_manager.is_muted():
                self.sound_glass_lower.play()
                self.sound_manager.vibrate_short()
            if self._on_glass_move_complete:
                self._on_glass_move_complete()
            self._update_point_a_marker()
            self._unblock_dice()
            self._update_glass_highlight()
            self._print_widget_order("После опускания стакана")

            if self.magnetic_field and not self.dice_hidden and not self.is_dice_enlarged:
                print("🧲 [MAGNETIC] Запуск поля после опускания стакана")
                self.magnetic_field.start()

            if DEBUG_MODE:
                print("🥛 [GLASS] ЗАВЕРШЕНИЕ опускания стакана")

        self.glass.animate_movement(
            start_pos=self.glass_target_pos,
            end_pos=self.glass_start_pos,
            duration=0.6,
            forward=False,
            callback=on_animation_complete
        )

        self.shadow.animate_movement_to_target(
            target_pos=shadow_target_pos,
            duration=0.6,
            forward=False
        )

    def _lower_glass_to_center(self, target_center_x, target_center_y):
        """Анимация опускания стакана в центр кубиков (самонаведение)"""

        self.saved_dice_positions = []
        for dice in self.dice_list:
            self.saved_dice_positions.append((dice.pos[0], dice.pos[1]))

        if self.magnetic_field:
            self.magnetic_field.update_glass_position(self.glass_start_pos)

        self._block_dice()
        self._ensure_glass_on_top_during_lowering()

        self.max_speed = 0
        self.last_touch_pos = None
        self.last_touch_time = None

        old_start_x = self.glass_start_pos[0]
        old_start_y = self.glass_start_pos[1]
        old_target_x = self.glass_target_pos[0]
        old_target_y = self.glass_target_pos[1]
        old_shadow_x = self.SHADOW_POSITION_X
        old_shadow_y = self.SHADOW_POSITION_Y
        old_shadow_target_x = self.SHADOW_TARGET_POSITION_X
        old_shadow_target_y = self.SHADOW_TARGET_POSITION_Y

        new_start_x = target_center_x - self.glass_size / 6.5
        new_start_y = target_center_y - self.glass_size / 2

        offset_x = new_start_x - old_start_x
        offset_y = new_start_y - old_start_y

        new_target_x = old_target_x + offset_x
        new_target_y = old_target_y + offset_y
        new_shadow_x = old_shadow_x + offset_x
        new_shadow_y = old_shadow_y + offset_y
        new_shadow_target_x = old_shadow_target_x + offset_x
        new_shadow_target_y = old_shadow_target_y + offset_y

        self.shadow.pos = (old_shadow_target_x, old_shadow_target_y)
        shadow_target_pos = (new_shadow_x, new_shadow_y)

        Clock.schedule_once(lambda dt: self._disable_glow_for_all_dice(), 0.7)

        self._print_widget_order("Перед опусканием стакана в центр")

        animation_duration = 0.8

        def on_animation_complete(*args):
            self.glass_start_pos = (new_start_x, new_start_y)
            self.glass_target_pos = (new_target_x, new_target_y)
            self.SHADOW_POSITION_X = new_shadow_x
            self.SHADOW_POSITION_Y = new_shadow_y
            self.SHADOW_TARGET_POSITION_X = new_shadow_target_x
            self.SHADOW_TARGET_POSITION_Y = new_shadow_target_y

            self.glass.pos = self.glass_start_pos

            self.is_at_target = True

            if self.sound_glass_lower and not self.sound_manager.is_muted():
                self.sound_glass_lower.play()
                self.sound_manager.vibrate_short()

            if self.pending_hide_dice:
                for dice in self.dice_list:
                    dice.opacity = 0
                    if dice.glow:
                        dice.glow.opacity = 0
                self.dice_hidden = True
                self.pending_hide_dice = False

            self._update_point_a_marker()
            self._unblock_dice()
            self._update_glass_highlight()
            self._print_widget_order("После опускания стакана в центр")
            self._update_dice_z_order()

            if self._on_glass_move_complete:
                self._on_glass_move_complete()

        self.glass.animate_movement(
            start_pos=self.glass_target_pos,
            end_pos=(new_start_x, new_start_y),
            duration=animation_duration,
            forward=False,
            callback=on_animation_complete
        )

        self.shadow.animate_movement_to_target(
            target_pos=shadow_target_pos,
            duration=animation_duration,
            forward=False
        )

    # ===== ВРАЩЕНИЕ КУБА ПРИ КОНТАКТЕ С МАГНИТНЫМ ПОЛЕМ =====

    def _update_dice_rotation_by_magnetic_field(self, glass_delta_x, glass_delta_y):
        """Обновляет вращение куба при контакте с магнитным полем"""
        if not self.dice_list:
            return

        distance = math.sqrt(glass_delta_x * glass_delta_x + glass_delta_y * glass_delta_y)
        if distance <= 0:
            return

        for dice in self.dice_list:
            if not self.dice_contact_flags.get(dice, False):
                continue

            if self._is_dice_above_glass(dice):
                if abs(glass_delta_x) > abs(glass_delta_y):
                    frame_change = -1 if glass_delta_x > 0 else 1
                else:
                    frame_change = -1 if glass_delta_y > 0 else 1
            else:
                if abs(glass_delta_x) > abs(glass_delta_y):
                    frame_change = 1 if glass_delta_x > 0 else -1
                else:
                    frame_change = 1 if glass_delta_y > 0 else -1

            accumulator = self.dice_frame_accumulators.get(dice, 0.0)
            accumulator += distance

            while accumulator >= self.frame_change_threshold:
                current_frame = dice.frame_index
                new_frame = current_frame + frame_change

                total_frames = dice.rows * dice.cols
                if new_frame >= total_frames:
                    new_frame = 0
                elif new_frame < 0:
                    new_frame = total_frames - 1

                dice.set_frame_direct(new_frame)
                accumulator -= self.frame_change_threshold

            self.dice_frame_accumulators[dice] = accumulator

            if DEBUG_MODE and distance > 0:
                above_status = "НАД" if self._is_dice_above_glass(dice) else "ПОД"
                print(f"🔄 [MAGNETIC_ROTATION] Кубик {above_status} стаканом, накоплено: {accumulator:.1f}/{self.frame_change_threshold}")

    def _start_magnetic_contact_monitoring(self):
        """Запускает периодическую проверку контакта полей для каждого кубика"""
        def check_contact(dt):
            if not self.magnetic_field or not self.glass or not self.dice_list:
                return

            glass_x = self.glass.pos[0] + self.glass.width / 2
            glass_y = self.glass.pos[1] + self.glass.height / 2
            contact_radius = self.glass_size * 0.8

            for dice in self.dice_list:
                dice_x = dice.pos[0] + dice.width / 2
                dice_y = dice.pos[1] + dice.height / 2
                distance = math.sqrt((glass_x - dice_x)**2 + (glass_y - dice_y)**2)

                was_contact = self.dice_contact_flags.get(dice, False)
                is_contact = distance < contact_radius

                if is_contact and not was_contact:
                    self.dice_contact_flags[dice] = True
                    self.dice_frame_accumulators[dice] = 0.0
                    if DEBUG_MODE:
                        above_status = "НАД" if self._is_dice_above_glass(dice) else "ПОД"
                        print(f"🧲 [CONTACT] Кубик {above_status} стаканом - контакт УСТАНОВЛЕН!")
                elif not is_contact and was_contact:
                    self.dice_contact_flags[dice] = False
                    self.dice_frame_accumulators[dice] = 0.0
                    if DEBUG_MODE:
                        print(f"🧲 [CONTACT] Кубик - контакт ПОТЕРЯН!")

        self.contact_monitor = Clock.schedule_interval(check_contact, 0.1)

    def _on_dice_click(self):
        if self.is_dice_blocked:
            if DEBUG_MODE:
                print("🔒 [DiceScreen] Кубики заблокированы, клик игнорируется")
            return

        if self.is_animating:
            return

        if self.is_dice_enlarged:
            self._shrink_all_dice()
        else:
            self._start_switch_animation()

    def on_enter(self):
        super().on_enter()
        self._load_dice_sounds()

        screen_width, screen_height = self.get_screen_size()

        if DEBUG_MODE:
            print(f"\n{'='*60}")
            print(f"🎮 [DiceScreen] ВХОД на экран")
            print(f"📱 Размер экрана: {screen_width:.0f} x {screen_height:.0f}")
            print(f"🎯 Центр экрана: ({screen_width/2:.0f}, {screen_height/2:.0f})")
            print(f"{'='*60}\n")

        self.single_dice_size = screen_width * 0.126
        self.double_dice_size = screen_width * 0.1
        self.large_dice_size = self.single_dice_size * 5

        self.glass_size = screen_width * 0.20
        self.shadow_size = self.glass_size * 0.9

        self.START_POSITION_DICE_X = screen_width * 0.3
        self.START_POSITION_DICE_Y = screen_height * 0.5 - (self.single_dice_size // 2)

        self.START_POSITION_GLASS_X = screen_width * 0.27
        self.START_POSITION_GLASS_Y = screen_height * 0.25

        self.SHADOW_POSITION_X = self.START_POSITION_GLASS_X + (self.glass_size * self.shadow_offset_x_factor)
        self.SHADOW_POSITION_Y = self.START_POSITION_GLASS_Y + (self.glass_size * self.shadow_offset_y_factor)

        self.glass_start_pos = (self.START_POSITION_GLASS_X, self.START_POSITION_GLASS_Y)
        self.glass_target_pos = (self.START_POSITION_GLASS_X + self.glass_size, self.START_POSITION_GLASS_Y - self.glass_size)

        self.SHADOW_TARGET_POSITION_X = self.SHADOW_POSITION_X + (self.glass_size * self.shadow_move_factor_x)
        self.SHADOW_TARGET_POSITION_Y = self.SHADOW_POSITION_Y - (self.glass_size * self.shadow_move_factor_y)

        self._setup_ui()

        Clock.schedule_once(lambda dt: self._create_drop_zone(), 0.1)
        Clock.schedule_once(lambda dt: self._create_magnetic_field(), 0.3)

    def _create_drop_zone(self):
        screen_width, screen_height = self.get_screen_size()
        self.drop_zone = DropZone(screen_width, screen_height)
        self.layout.add_widget(self.drop_zone)

        if DEBUG_MODE:
            ellipse_center_x = self.drop_zone.pos[0] + self.drop_zone.size[0] / 2
            ellipse_center_y = self.drop_zone.pos[1] + self.drop_zone.size[1] / 2

            print(f"\n{'='*60}")
            print(f"🔵 [DROPZONE] Зона создана")
            print(f"   Позиция: ({self.drop_zone.pos[0]:.0f}, {self.drop_zone.pos[1]:.0f})")
            print(f"   Размер: {self.drop_zone.size[0]:.0f} x {self.drop_zone.size[1]:.0f}")
            print(f"   🎯 Центр эллипса: ({ellipse_center_x:.0f}, {ellipse_center_y:.0f})")
            print(f"   Радиусы: X={self.drop_zone.size[0]/2:.0f}, Y={self.drop_zone.size[1]/2:.0f}")
            print(f"{'='*60}\n")

            self.drop_zone.update_zone_visibility()
            Clock.schedule_once(lambda dt: self._visualize_drop_zone(), 0.1)

    def _create_magnetic_field(self):
        if self.drop_zone and self.dice_list:
            current_dice_size = self.single_dice_size if self.current_mode == 1 else self.double_dice_size
            self.magnetic_field = MagneticField(
                drop_zone=self.drop_zone,
                dice_list=self.dice_list,
                glass_start_pos=self.glass_start_pos,
                glass_size=self.glass_size,
                dice_size=current_dice_size
            )
            print("🧲 [MAGNETIC] Эффект магнитного поля создан")

            if self.is_at_target and not self.dice_hidden and not self.is_dice_enlarged:
                self.magnetic_field.start()
                print("🧲 [MAGNETIC] Поле автоматически запущено при входе на экран")

            for dice in self.dice_list:
                self.dice_contact_flags[dice] = False
                self.dice_frame_accumulators[dice] = 0.0

            self._start_magnetic_contact_monitoring()

    def _visualize_drop_zone(self):
        if not DEBUG_MODE or not self.drop_zone:
            return

        if hasattr(self, '_drop_zone_visualization') and self._drop_zone_visualization:
            try:
                self.drop_zone.canvas.before.remove(self._drop_zone_visualization)
            except:
                pass

        with self.drop_zone.canvas.before:
            Color(0, 1, 0, 0.25)
            self._drop_zone_visualization = Ellipse(
                pos=self.drop_zone.pos,
                size=self.drop_zone.size
            )

        if DEBUG_MODE:
            ellipse_center_x = self.drop_zone.pos[0] + self.drop_zone.size[0] / 2
            ellipse_center_y = self.drop_zone.pos[1] + self.drop_zone.size[1] / 2
            print(f"🎨 [DROPZONE] Визуализация добавлена")
            print(f"   Центр эллипса: ({ellipse_center_x:.0f}, {ellipse_center_y:.0f})")
            print(f"   Зеленая зона активна\n")

    def _get_current_point_a_position(self):
        point_a_x = self.glass_start_pos[0] + self.glass_size / 6.5
        point_a_y = self.glass_start_pos[1] + self.glass_size / 2
        return (point_a_x, point_a_y)

    def _sync_dice_to_point_a(self):
        if not self.dice_list:
            return

        point_a_x, point_a_y = self._get_current_point_a_position()

        if len(self.dice_list) == 1:
            dice = self.dice_list[0]

            if not self.has_moved_with_dice and self.saved_dice_positions and len(self.saved_dice_positions) >= 1:
                target_x, target_y = self.saved_dice_positions[0]
            else:
                target_x = point_a_x - dice.width / 2
                target_y = point_a_y - dice.height / 2

            dice.pos = (target_x, target_y)
            dice.opacity = 1
            if dice.glow:
                dice.glow.update_position(dice.pos, dice.dice_size)
                dice.glow.opacity = 1
        else:
            distance_between = self.double_dice_size * 0.3
            for i, dice in enumerate(self.dice_list):
                if not self.has_moved_with_dice and self.saved_dice_positions and len(self.saved_dice_positions) > i:
                    target_x, target_y = self.saved_dice_positions[i]
                else:
                    if i == 0:
                        target_y = point_a_y - distance_between - dice.height / 2
                    else:
                        target_y = point_a_y + distance_between - dice.height / 2
                    target_x = point_a_x - dice.width / 2

                dice.pos = (target_x, target_y)
                dice.opacity = 1
                if dice.glow:
                    dice.glow.update_position(dice.pos, dice.dice_size)
                    dice.glow.opacity = 1

        self.saved_dice_positions = []
        for dice in self.dice_list:
            dice.canvas.ask_update()
            if dice.glow:
                dice.glow.canvas.ask_update()
        self._update_dice_z_order()

    def _update_dice_position(self, delta_x, delta_y):
        if not self.dice_list:
            return
        for dice in self.dice_list:
            new_x = dice.pos[0] + delta_x
            new_y = dice.pos[1] + delta_y
            dice.pos = (new_x, new_y)
            if dice.glow:
                dice.glow.update_position(dice.pos, dice.dice_size)
        self._update_dice_z_order()

    def _enforce_point_a_in_zone(self):
        if not self.drop_zone or not self.glass:
            return

        point_a_x, point_a_y = self._get_current_point_a_position()

        if self.drop_zone.check_point_in_zone(point_a_x, point_a_y):
            return

        clamped_point_a = self.drop_zone.clamp_point_to_zone(point_a_x, point_a_y)

        new_glass_x = clamped_point_a[0] - self.glass_size / 6.5
        new_glass_y = clamped_point_a[1] - self.glass_size / 2

        delta_x = new_glass_x - self.glass_start_pos[0]
        delta_y = new_glass_y - self.glass_start_pos[1]

        self.glass_start_pos = (new_glass_x, new_glass_y)
        self.glass_target_pos = (self.glass_target_pos[0] + delta_x, self.glass_target_pos[1] + delta_y)

        if self.is_at_target:
            self.glass.pos = self.glass_start_pos
        else:
            self.glass.pos = self.glass_target_pos

        self.SHADOW_POSITION_X += delta_x
        self.SHADOW_POSITION_Y += delta_y
        self.SHADOW_TARGET_POSITION_X += delta_x
        self.SHADOW_TARGET_POSITION_Y += delta_y
        self.shadow.move_by_delta(delta_x, delta_y)

        if self.dice_hidden:
            self._update_dice_position(delta_x, delta_y)

        if self.magnetic_field:
            self.magnetic_field.update_glass_position(self.glass_start_pos)

        self._update_dice_z_order()

    def _clamp_position_to_zone(self, pos_x, pos_y):
        if not self.drop_zone:
            return (pos_x, pos_y)

        if not self.is_at_target:
            delta_x = pos_x - self.glass_target_pos[0]
            delta_y = pos_y - self.glass_target_pos[1]

            new_start_x = self.glass_start_pos[0] + delta_x
            new_start_y = self.glass_start_pos[1] + delta_y

            point_a_x = new_start_x + self.glass_size / 6.5
            point_a_y = new_start_y + self.glass_size / 2
        else:
            point_a_x = pos_x + self.glass_size / 6.5
            point_a_y = pos_y + self.glass_size / 2

        if self.drop_zone.check_point_in_zone(point_a_x, point_a_y):
            return (pos_x, pos_y)

        clamped_point_a = self.drop_zone.clamp_point_to_zone(point_a_x, point_a_y)

        if not self.is_at_target:
            new_start_x = clamped_point_a[0] - self.glass_size / 6.5
            new_start_y = clamped_point_a[1] - self.glass_size / 2

            delta_x = new_start_x - self.glass_start_pos[0]
            delta_y = new_start_y - self.glass_start_pos[1]

            new_target_x = self.glass_target_pos[0] + delta_x
            new_target_y = self.glass_target_pos[1] + delta_y

            return (new_target_x, new_target_y)
        else:
            new_pos_x = clamped_point_a[0] - self.glass_size / 6.5
            new_pos_y = clamped_point_a[1] - self.glass_size / 2

            return (new_pos_x, new_pos_y)

    def _update_glass_highlight(self):
        if not DEBUG_MODE or not self.glass or not self.drop_zone:
            return

        point_a_x, point_a_y = self._get_current_point_a_position()
        is_in_zone = self.drop_zone.check_point_in_zone(point_a_x, point_a_y)

        if hasattr(self.glass, 'color_overlay') and self.glass.color_overlay:
            try:
                self.glass.canvas.before.remove(self.glass.color_overlay)
            except:
                pass
            self.glass.color_overlay = None

        with self.glass.canvas.before:
            if is_in_zone:
                Color(0, 1, 0, 0.3)
            else:
                Color(1, 0, 0, 0.5)
            self.glass.color_overlay = Rectangle(pos=self.glass.pos, size=self.glass.size)

        return is_in_zone

    def _create_point_a_marker(self):
        if DEBUG_MODE:
            self.point_a_marker = PointMarker(color=(1, 0, 0, 1), size=10)
        else:
            self.point_a_marker = PointMarker(color=(1, 1, 1, 0), size=2)

        self.layout.add_widget(self.point_a_marker)
        self._bring_point_a_to_top()
        self._update_point_a_marker()

    def _bring_point_a_to_top(self):
        if self.point_a_marker and self.point_a_marker.parent:
            self.point_a_marker.parent.remove_widget(self.point_a_marker)
            self.layout.add_widget(self.point_a_marker)

    def _update_point_a_marker(self):
        if self.point_a_marker and self.drop_zone:
            self._enforce_point_a_in_zone()

            point_a_x, point_a_y = self._get_current_point_a_position()

            if DEBUG_MODE:
                in_zone = self.drop_zone.check_point_in_zone(point_a_x, point_a_y)
                self.point_a_marker.color = (0, 1, 0, 1) if in_zone else (1, 0, 0, 1)
            else:
                self.point_a_marker.color = (1, 1, 1, 0)

            self.point_a_marker.update_position(point_a_x, point_a_y, visible=True)
            self._bring_point_a_to_top()

            return in_zone if DEBUG_MODE else True
        return True

    def on_leave(self):
        if hasattr(self, 'contact_monitor') and self.contact_monitor:
            self.contact_monitor.cancel()
            self.contact_monitor = None

        if hasattr(self, '_animation_monitor') and self._animation_monitor:
            self._animation_monitor.cancel()

        if self.particle_system:
            self.particle_system.cleanup()
            if self.particle_system in self.layout.children:
                self.layout.remove_widget(self.particle_system)
            self.particle_system = None

        if self.magnetic_field:
            self.magnetic_field.stop()
            self.magnetic_field = None

        self._reset_brightness()

        if self.volume_fade_clock:
            self.volume_fade_clock.cancel()
            self.volume_fade_clock = None
        if self.sound_glass_drag:
            try:
                self.sound_glass_drag.stop()
            except:
                pass

        if hasattr(self, '_drop_zone_visualization') and self._drop_zone_visualization:
            try:
                if self.drop_zone and self.drop_zone.canvas:
                    self.drop_zone.canvas.before.remove(self._drop_zone_visualization)
            except:
                pass

        self._clear_all_dice()
        if self.glass and self.glass.parent:
            if hasattr(self.glass, 'color_overlay') and self.glass.color_overlay:
                try:
                    self.glass.canvas.before.remove(self.glass.color_overlay)
                except:
                    pass
            self.layout.remove_widget(self.glass)
            self.glass = None
        if self.shadow and self.shadow.parent:
            self.layout.remove_widget(self.shadow)
            self.shadow = None
        if self.drop_zone and self.drop_zone.parent:
            self.layout.remove_widget(self.drop_zone)
            self.drop_zone = None
        if self.point_a_marker and self.point_a_marker.parent:
            self.layout.remove_widget(self.point_a_marker)
            self.point_a_marker = None
        if self.bg_dark and self.bg_dark.parent:
            self.layout.remove_widget(self.bg_dark)
            self.bg_dark = None
        if self.bg_bright and self.bg_bright.parent:
            self.layout.remove_widget(self.bg_bright)
            self.bg_bright = None
        super().on_leave()

    def _setup_ui(self):
        if os.path.exists(self.background_image):
            self.bg_dark = Image(source=self.background_image, allow_stretch=True, keep_ratio=False, size_hint=(1, 1), opacity=1)
            self.layout.add_widget(self.bg_dark, index=0)

        if os.path.exists(self.background_bright_image):
            self.bg_bright = Image(source=self.background_bright_image, allow_stretch=True, keep_ratio=False, size_hint=(1, 1), opacity=0)
            self.layout.add_widget(self.bg_bright, index=0)

        self.particle_system = ParticleSystem(num_particles=30)
        self.layout.add_widget(self.particle_system)

        self._reset_brightness()

        self._create_point_a_marker()
        self._create_shadow()
        self._create_dice_for_mode(1, animate=False)
        self._create_glass()

        self.create_back_button()

        self._print_widget_order("После инициализации UI")

    def _create_shadow(self):
        offset_x_px = self.glass_size * self.shadow_offset_x_factor
        offset_y_px = self.glass_size * self.shadow_offset_y_factor

        self.shadow = ShadowWidget(
            sprite_sheet_path=self.shadow_sprite_sheet_path,
            shadow_size=self.shadow_size,
            rows=2,
            cols=12,
            frame_index=0,
            rotation_angle=self.shadow_rotation,
            scale_factor=self.shadow_scale_factor,
            offset_x=offset_x_px,
            offset_y=offset_y_px,
            opacity=self.shadow_opacity,
            move_factor_x=self.shadow_move_factor_x,
            move_factor_y=self.shadow_move_factor_y,
            glass_size=self.glass_size,
            size_hint=(None, None),
            size=(self.shadow_size * self.shadow_scale_factor, self.shadow_size * self.shadow_scale_factor),
            pos=(self.SHADOW_POSITION_X, self.SHADOW_POSITION_Y)
        )
        self.shadow.set_frame(0)
        self.layout.add_widget(self.shadow)

    def _create_glass(self):
        self.glass = GlassWidget(
            sprite_sheet_path=self.glass_sprite_sheet_path,
            glass_size=self.glass_size,
            rows=2,
            cols=12,
            frame_index=0,
            rotation_angle=-90,
            size_hint=(None, None),
            size=(self.glass_size, self.glass_size),
            pos=self.glass_start_pos,
            on_glass_click=self._on_glass_click,
            on_glass_drag=self._on_glass_drag,
            on_glass_drag_end=self._on_glass_drag_end,
            debug_mode=DEBUG_MODE
        )
        self.glass.set_frame(0)
        self.layout.add_widget(self.glass)
        self.is_at_target = True

        if DEBUG_MODE:
            Clock.schedule_once(lambda dt: self._update_glass_highlight(), 0.1)

    def _on_glass_drag(self, delta_x, delta_y, touch):
        if self.is_glass_blocked:
            return

        if self.is_animating:
            return
        if delta_x == 0 and delta_y == 0:
            return

        self._update_dice_rotation_by_magnetic_field(delta_x, delta_y)

        if self.dice_hidden:
            self.has_moved_with_dice = True

            distance = math.sqrt(delta_x * delta_x + delta_y * delta_y)

            if distance > 0:
                self._update_brightness(delta_distance=distance)

            def reset_charging_flag(dt):
                if not self.dice_hidden:
                    self.is_charging = False
                elif self.current_brightness >= self.MAX_BRIGHTNESS:
                    pass
                else:
                    self.is_charging = False
                    if self.current_brightness > 0:
                        self._start_drain()

            if self._reset_charge_clock:
                self._reset_charge_clock.cancel()
            self._reset_charge_clock = Clock.schedule_once(reset_charging_flag, 0.05)

        if self.is_at_target:
            current_time = Clock.get_time()
            current_pos = (touch.x, touch.y)

            if self.last_touch_pos is None or self.last_touch_time is None:
                self.last_touch_pos = current_pos
                self.last_touch_time = current_time
                current_speed = 0
            else:
                dx = current_pos[0] - self.last_touch_pos[0]
                dy = current_pos[1] - self.last_touch_pos[1]
                distance = math.sqrt(dx * dx + dy * dy)
                dt = current_time - self.last_touch_time
                if dt > 0:
                    current_speed = distance / dt
                    if current_speed > self.max_speed:
                        self.max_speed = current_speed
                else:
                    current_speed = 0
                self.last_touch_pos = current_pos
                self.last_touch_time = current_time

            MIN_SPEED = 50
            MAX_SPEED = 800
            MIN_VOLUME = 0.0
            MAX_VOLUME = 0.5

            if current_speed > MIN_SPEED:
                target_volume = MIN_VOLUME + (current_speed - MIN_SPEED) / (MAX_SPEED - MIN_SPEED) * (MAX_VOLUME - MIN_VOLUME)
                target_volume = max(MIN_VOLUME, min(MAX_VOLUME, target_volume))
            else:
                target_volume = 0.0

            if self.sound_glass_drag and not self.sound_manager.is_muted():
                if abs(target_volume - self.sound_glass_drag.volume) > 0.1:
                    self._fade_volume(target_volume, 0.1)
                else:
                    self.sound_glass_drag.volume = target_volume
        else:
            if self.sound_glass_drag:
                self._fade_volume(0.0, 0.2)

        if self.dice_hidden:
            self._update_dice_position(delta_x, delta_y)

        if self.is_at_target:
            new_glass_x = self.glass_start_pos[0] + delta_x
            new_glass_y = self.glass_start_pos[1] + delta_y
        else:
            new_glass_x = self.glass_target_pos[0] + delta_x
            new_glass_y = self.glass_target_pos[1] + delta_y

        clamped_pos = self._clamp_position_to_zone(new_glass_x, new_glass_y)

        if self.is_at_target:
            actual_delta_x = clamped_pos[0] - self.glass_start_pos[0]
            actual_delta_y = clamped_pos[1] - self.glass_start_pos[1]
            self.glass_start_pos = clamped_pos
            self.glass_target_pos = (self.glass_target_pos[0] + actual_delta_x, self.glass_target_pos[1] + actual_delta_y)
            self.glass.pos = self.glass_start_pos
        else:
            actual_delta_x = clamped_pos[0] - self.glass_target_pos[0]
            actual_delta_y = clamped_pos[1] - self.glass_target_pos[1]
            self.glass_target_pos = clamped_pos
            self.glass_start_pos = (self.glass_start_pos[0] + actual_delta_x, self.glass_start_pos[1] + actual_delta_y)
            self.glass.pos = self.glass_target_pos

        self.SHADOW_POSITION_X += actual_delta_x
        self.SHADOW_POSITION_Y += actual_delta_y
        self.SHADOW_TARGET_POSITION_X += actual_delta_x
        self.SHADOW_TARGET_POSITION_Y += actual_delta_y
        self.shadow.move_by_delta(actual_delta_x, actual_delta_y)

        if self.magnetic_field and self.is_at_target:
            self.magnetic_field.update_glass_position(self.glass_start_pos)

        if not self.dice_hidden:
            self._update_dice_z_order()

        self._update_point_a_marker()

    def _on_glass_drag_end(self, touch):
        if DEBUG_MODE:
            print("🔴 [DRAG_END] Вызван")
        if self.sound_glass_drag:
            self._fade_volume(0.0, 0.3)
        self.last_touch_pos = None
        self.last_touch_time = None

        if self._reset_charge_clock:
            self._reset_charge_clock.cancel()
            self._reset_charge_clock = None

        self._enforce_point_a_in_zone()
        self._update_point_a_marker()

        if self.dice_hidden and self.current_brightness > 0 and not self.is_charging:
            self.is_charging = False
            if self.current_brightness < self.MAX_BRIGHTNESS:
                self._start_drain()

        self._update_dice_z_order()

        if self.magnetic_field and self.is_at_target and not self.dice_hidden and not self.is_dice_enlarged:
            if not self.magnetic_field.is_magnetic_active():
                print("🧲 [MAGNETIC] Запуск поля после перетаскивания")
                self.magnetic_field.start()

    def _on_glass_click(self):
        if self.is_glass_blocked:
            return

        if self.is_animating:
            return

        if self.is_at_target:
            if self.dice_hidden:
                if DEBUG_MODE:
                    print("🖱️ [CLICK] Кубики скрыты (были под стаканом), показываем их")

                self._sync_dice_to_point_a()

                for dice in self.dice_list:
                    dice.opacity = 1
                    if dice.glow:
                        dice.glow.opacity = 1
                self.dice_hidden = False
                self.pending_hide_dice = False

                for dice in self.dice_list:
                    dice.enable_glow()

                if DEBUG_MODE:
                    print(f"🖱️ [CLICK] После показа: dice_hidden={self.dice_hidden}")

            if self.current_brightness >= self.MAX_BRIGHTNESS - 0.001:
                if DEBUG_MODE:
                    print(f"🎲 [DICE] Яркость {self.current_brightness:.2f} = 100%, запускаем анимацию увеличения кубиков")

                self.play_dice_roll_sound()

                if self.has_moved_with_dice:
                    SPEED_THRESHOLD = 300
                    if self.max_speed > SPEED_THRESHOLD:
                        for dice in self.dice_list:
                            dice.set_random_frame()
                    else:
                        for dice in self.dice_list:
                            dice.set_random_frame_same_row()
                    self.has_moved_with_dice = False
                else:
                    if DEBUG_MODE:
                        print("   Не было движения с кубами - кадр НЕ меняется")

                self.max_speed = 0
                self.last_touch_pos = None
                self.last_touch_time = None

                def after_glass_raise():
                    Clock.schedule_once(lambda dt: self._animate_dice_appearance(), 0.1)

                self._raise_glass(on_complete_callback=after_glass_raise)
            else:
                if DEBUG_MODE:
                    print(f"🎲 [DICE] Яркость {self.current_brightness:.2f} < 100%, поднимаем стакан")

                if self.has_moved_with_dice:
                    SPEED_THRESHOLD = 300
                    if self.max_speed > SPEED_THRESHOLD:
                        for dice in self.dice_list:
                            dice.set_random_frame()
                    else:
                        for dice in self.dice_list:
                            dice.set_random_frame_same_row()
                    self.has_moved_with_dice = False
                else:
                    if DEBUG_MODE:
                        print("   Не было движения с кубами - кадр НЕ меняется")

                self.max_speed = 0
                self.last_touch_pos = None
                self.last_touch_time = None

                self._raise_glass()
        else:
            if DEBUG_MODE:
                print("🖱️ [CLICK] Стакан поднят, опускаем")
            if self.is_dice_enlarged:
                self._cancel_drain()
                self._shrink_all_dice()
                Clock.schedule_once(lambda dt: self._process_glass_lower(), 0.4)
            else:
                self._process_glass_lower()

    def _process_glass_lower(self):
        if DEBUG_MODE:
            print("🔄 [PROCESS] Начало обработки опускания стакана")

        if self.dice_list and not self.dice_hidden:
            if len(self.dice_list) == 1:
                target_dice = self.dice_list[0]
                dice_center_x = target_dice.pos[0] + target_dice.width / 2
                dice_center_y = target_dice.pos[1] + target_dice.height / 2
            else:
                total_x = 0
                total_y = 0
                for dice in self.dice_list:
                    total_x += dice.pos[0] + dice.width / 2
                    total_y += dice.pos[1] + dice.height / 2
                dice_center_x = total_x / len(self.dice_list)
                dice_center_y = total_y / len(self.dice_list)

            current_point_a_x = self.glass_start_pos[0] + self.glass_size / 6.5
            current_point_a_y = self.glass_start_pos[1] + self.glass_size / 2

            distance_x = abs(current_point_a_x - dice_center_x)
            distance_y = abs(current_point_a_y - dice_center_y)

            current_dice_size = self.single_dice_size if self.current_mode == 1 else self.double_dice_size
            max_distance_x = current_dice_size * self.MAGNETIC_DISTANCE_X_FACTOR
            max_distance_y = current_dice_size * self.MAGNETIC_DISTANCE_Y_FACTOR

            if DEBUG_MODE:
                print(f"   Размер кубика: {current_dice_size:.1f}px")
                print(f"   Макс расстояние: X={max_distance_x:.1f}px, Y={max_distance_y:.1f}px")
                print(f"   Расстояние до кубиков: X={distance_x:.0f}, Y={distance_y:.0f}")

            if distance_x <= max_distance_x and distance_y <= max_distance_y:
                if DEBUG_MODE:
                    print(f"   ✅ Кубики рядом со стаканом, опускаем в центр")
                    print(f"      (X={distance_x:.0f} <= {max_distance_x:.0f}, Y={distance_y:.0f} <= {max_distance_y:.0f})")

                if self.magnetic_field:
                    self.magnetic_field.stop()

                self.pending_hide_dice = True
                self._lower_glass_to_center(dice_center_x, dice_center_y)
            else:
                if DEBUG_MODE:
                    print(f"   📍 Кубики далеко, просто опускаем стакан")
                    print(f"      (X={distance_x:.0f} > {max_distance_x:.0f} или Y={distance_y:.0f} > {max_distance_y:.0f})")
                self._lower_glass()
        else:
            if DEBUG_MODE:
                print("   🥛 Нет кубиков или они уже скрыты, просто опускаем стакан")
            self._lower_glass()

    def _disable_glow_for_all_dice(self):
        for dice in self.dice_list:
            dice.disable_glow()

    def _on_glass_move_complete(self):
        if DEBUG_MODE:
            print("✅ [MOVE] Движение стакана завершено")
        pass

    def _on_appearance_complete(self, dice):
        self.animation_counter += 1
        if self.animation_counter >= 2:
            self.is_animating = False
            if DEBUG_MODE:
                print("✅ [ANIM] Анимация появления кубиков завершена")
            self.animation_counter = 0

    def _get_dice_center(self):
        if not self.dice_list:
            if self.last_dice_center:
                return self.last_dice_center
            center_x = self.START_POSITION_DICE_X + self.single_dice_size // 2
            center_y = self.START_POSITION_DICE_Y + self.single_dice_size // 2
            return (center_x, center_y)

        if len(self.dice_list) == 1:
            dice = self.dice_list[0]
            center = (dice.pos[0] + dice.width / 2, dice.pos[1] + dice.height / 2)
            self.last_dice_center = center
            return center
        else:
            total_x = 0
            total_y = 0
            for dice in self.dice_list:
                total_x += dice.pos[0] + dice.width / 2
                total_y += dice.pos[1] + dice.height / 2
            center = (total_x / len(self.dice_list), total_y / len(self.dice_list))
            self.last_dice_center = center
            return center

    def _create_dice_for_mode(self, mode, animate=True, sound_delay=0.15):
        self._clear_all_dice()
        self.saved_dice_positions = []
        self.dice_hidden = False
        self.pending_hide_dice = False
        self.is_dice_enlarged = False

        if not animate:
            if mode == 1:
                dice = DiceWidget(
                    sprite_sheet_path=self.sprite_sheet_path,
                    dice_size=self.single_dice_size,
                    rows=6,
                    cols=24,
                    frame_index=0,
                    rotation_angle=-90,
                    size_hint=(None, None),
                    size=(self.single_dice_size, self.single_dice_size),
                    pos=(self.START_POSITION_DICE_X, self.START_POSITION_DICE_Y),
                    on_dice_click=self._on_dice_click
                )
                dice.set_random_frame()
                dice.original_position = dice.pos
                dice.original_size = dice.dice_size
                dice.opacity = 1
                self.layout.add_widget(dice)
                self.dice_list.append(dice)
                Clock.schedule_once(lambda dt: dice._create_glow(), 0)

            elif mode == 2:
                distance_between = self.double_dice_size * 0.3
                center_y = self.START_POSITION_DICE_Y + (self.single_dice_size // 2) - (self.double_dice_size // 2)

                y_top = center_y - distance_between
                y_bottom = center_y + distance_between

                dice1 = DiceWidget(
                    sprite_sheet_path=self.sprite_sheet_path,
                    dice_size=self.double_dice_size,
                    rows=6,
                    cols=24,
                    frame_index=0,
                    rotation_angle=-90,
                    size_hint=(None, None),
                    size=(self.double_dice_size, self.double_dice_size),
                    pos=(self.START_POSITION_DICE_X, y_top),
                    on_dice_click=self._on_dice_click
                )
                dice1.original_position = dice1.pos
                dice1.original_size = dice1.dice_size
                dice1.opacity = 1

                dice2 = DiceWidget(
                    sprite_sheet_path=self.sprite_sheet_path,
                    dice_size=self.double_dice_size,
                    rows=6,
                    cols=24,
                    frame_index=0,
                    rotation_angle=-90,
                    size_hint=(None, None),
                    size=(self.double_dice_size, self.double_dice_size),
                    pos=(self.START_POSITION_DICE_X, y_bottom),
                    on_dice_click=self._on_dice_click
                )
                dice2.original_position = dice2.pos
                dice2.original_size = dice2.dice_size
                dice2.opacity = 1

                dice1.set_random_frame()
                dice2.set_random_frame()

                self.layout.add_widget(dice1)
                self.layout.add_widget(dice2)
                self.dice_list.append(dice1)
                self.dice_list.append(dice2)

                Clock.schedule_once(lambda dt: dice1._create_glow(), 0)
                Clock.schedule_once(lambda dt: dice2._create_glow(), 0)

            if self.glass and self.glass.parent:
                self.layout.remove_widget(self.glass)
                self.layout.add_widget(self.glass)

            if self.drop_zone:
                Clock.schedule_once(lambda dt: self._create_magnetic_field(), 0.1)
            return

        center = self._get_dice_center()

        if mode == 1:
            target_x = center[0] - self.single_dice_size / 2
            target_y = center[1] - self.single_dice_size / 2
            start_pos = (target_x, target_y)

            dice = DiceWidget(
                sprite_sheet_path=self.sprite_sheet_path,
                dice_size=self.single_dice_size,
                rows=6,
                cols=24,
                frame_index=0,
                rotation_angle=-90,
                size_hint=(None, None),
                size=(self.single_dice_size, self.single_dice_size),
                pos=start_pos,
                on_dice_click=self._on_dice_click
            )
            dice.set_random_frame()
            dice.opacity = 1
            self.layout.add_widget(dice)
            self.dice_list.append(dice)

            dice.animate_appearance_from_center(
                (target_x, target_y),
                start_pos,
                self.appear_duration,
                None,
                sound_delay=sound_delay
            )

        elif mode == 2:
            distance_between = self.double_dice_size * 0.3

            y_top = center[1] - distance_between - self.double_dice_size / 2
            y_bottom = center[1] + distance_between - self.double_dice_size / 2
            dice_x = center[0] - self.double_dice_size / 2

            start_pos = (center[0] - self.double_dice_size / 2, center[1] - self.double_dice_size / 2)

            dice1 = DiceWidget(
                sprite_sheet_path=self.sprite_sheet_path,
                dice_size=self.double_dice_size,
                rows=6,
                cols=24,
                frame_index=0,
                rotation_angle=-90,
                size_hint=(None, None),
                size=(self.double_dice_size, self.double_dice_size),
                pos=start_pos,
                on_dice_click=self._on_dice_click
            )

            dice2 = DiceWidget(
                sprite_sheet_path=self.sprite_sheet_path,
                dice_size=self.double_dice_size,
                rows=6,
                cols=24,
                frame_index=0,
                rotation_angle=-90,
                size_hint=(None, None),
                size=(self.double_dice_size, self.double_dice_size),
                pos=start_pos,
                on_dice_click=self._on_dice_click
            )

            self.layout.add_widget(dice1)
            self.layout.add_widget(dice2)
            self.dice_list.append(dice1)
            self.dice_list.append(dice2)

            self.is_animating = True
            self.animation_counter = 0

            Clock.schedule_once(lambda dt: dice1._create_glow(), 0)
            Clock.schedule_once(lambda dt: dice2._create_glow(), 0)

            def on_both_appear_complete(dice):
                self._on_appearance_complete(dice)
                if self.drop_zone and self.is_at_target and not self.dice_hidden:
                    Clock.schedule_once(lambda dt: self._create_magnetic_field(), 0.1)

            dice1.animate_appearance_from_center(
                (dice_x, y_top),
                start_pos,
                self.appear_duration,
                on_both_appear_complete,
                sound_delay=sound_delay
            )
            dice2.animate_appearance_from_center(
                (dice_x, y_bottom),
                start_pos,
                self.appear_duration,
                on_both_appear_complete,
                sound_delay=sound_delay
            )

        if self.glass and self.glass.parent:
            self.layout.remove_widget(self.glass)
            self.layout.add_widget(self.glass)

        self._print_widget_order(f"После создания {mode} кубика(ов)")

    def _start_switch_animation(self):
        if self.is_animating:
            return

        if self.is_dice_enlarged:
            self._shrink_all_dice()
            return

        if self.particle_system:
            self.particle_system.set_glow_mode(True)

        if self.magnetic_field:
            self.magnetic_field.stop()

        self.is_animating = True
        self._get_dice_center()

        if self.current_mode == 1:
            self._animate_one_to_two()
        else:
            self._animate_two_to_one()

        Clock.schedule_once(lambda dt: self.particle_system.set_glow_mode(False) if self.particle_system else None, 1.5)

    def _animate_one_to_two(self, sound_delay=0.4):
        if not self.dice_list:
            self.is_animating = False
            return

        if DEBUG_MODE:
            print("🔄 [SWITCH] Анимация перехода 1 кубик -> 2 кубика")

        # Поднимаем кубик над стаканом для анимации
        self._ensure_dice_above_glass_for_animation()

        self.sound_manager.vibrate_short()

        old_dice = self.dice_list[0]
        old_dice.animate_disappear_in_place(self.disappear_duration, None, sound_delay=sound_delay)

        appear_delay = self.disappear_duration - self.overlap_time
        Clock.schedule_once(lambda dt: self._create_small_dice(sound_delay=sound_delay), appear_delay)

    def _create_small_dice(self, sound_delay=0.15):
        self._clear_all_dice()
        self.current_mode = 2
        self._create_dice_for_mode(2, animate=True, sound_delay=sound_delay)

        # После создания проверяем Z-порядок
        Clock.schedule_once(lambda dt: self._ensure_dice_above_glass_for_animation(), 0.05)

    def _animate_two_to_one(self, sound_delay=0.4):
        if len(self.dice_list) < 2:
            self.is_animating = False
            return

        if DEBUG_MODE:
            print("🔄 [SWITCH] Анимация перехода 2 кубика -> 1 кубик")

        # Поднимаем кубики над стаканом для анимации
        self._ensure_dice_above_glass_for_animation()

        self.sound_manager.vibrate_short()

        dice_top = self.dice_list[0]
        dice_bottom = self.dice_list[1]

        center = self._get_dice_center()
        center_pos = (center[0] - self.single_dice_size / 2, center[1] - self.single_dice_size / 2)

        dice_top.animate_disappear_to_center(center_pos, self.disappear_duration, None, sound_delay=sound_delay)
        dice_bottom.animate_disappear_to_center(center_pos, self.disappear_duration, None, sound_delay=sound_delay)

        appear_delay = self.disappear_duration - self.overlap_time
        Clock.schedule_once(lambda dt: self._create_big_dice(sound_delay=sound_delay), appear_delay)

    def _create_big_dice(self, sound_delay=0.15):
        self._clear_all_dice()
        self.current_mode = 1
        self._create_dice_for_mode(1, animate=True, sound_delay=sound_delay)
        self.is_animating = False

        # После создания проверяем Z-порядок
        Clock.schedule_once(lambda dt: self._ensure_dice_above_glass_for_animation(), 0.05)

    def _clear_all_dice(self):
        for dice in self.dice_list:
            if dice.parent:
                self.layout.remove_widget(dice)
        self.dice_list.clear()

    def go_to_menu(self):
        if hasattr(self, 'contact_monitor') and self.contact_monitor:
            self.contact_monitor.cancel()
            self.contact_monitor = None

        if hasattr(self, '_animation_monitor') and self._animation_monitor:
            self._animation_monitor.cancel()

        if self.particle_system:
            self.particle_system.cleanup()
            if self.particle_system in self.layout.children:
                self.layout.remove_widget(self.particle_system)
            self.particle_system = None

        self._reset_brightness()

        if self.volume_fade_clock:
            self.volume_fade_clock.cancel()
            self.volume_fade_clock = None
        if self.sound_glass_drag:
            try:
                self.sound_glass_drag.stop()
            except:
                pass

        if self.magnetic_field:
            self.magnetic_field.stop()
            self.magnetic_field = None

        self._clear_all_dice()
        if self.glass and self.glass.parent:
            if hasattr(self.glass, 'color_overlay') and self.glass.color_overlay:
                try:
                    self.glass.canvas.before.remove(self.glass.color_overlay)
                except:
                    pass
            self.layout.remove_widget(self.glass)
            self.glass = None
        if self.shadow and self.shadow.parent:
            self.layout.remove_widget(self.shadow)
            self.shadow = None
        if self.drop_zone and self.drop_zone.parent:
            self.layout.remove_widget(self.drop_zone)
            self.drop_zone = None
        if self.point_a_marker and self.point_a_marker.parent:
            self.layout.remove_widget(self.point_a_marker)
            self.point_a_marker = None
        self.sound_manager.fade_to(1.0, duration=0.5)
        from main import switch_screen
        switch_screen('menu')