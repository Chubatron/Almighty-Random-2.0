# screens/draw/draw_main.py
"""
Главный экран жеребьёвки:
- GaltonTable — единый контейнер: фон + доска + данные корзин + результаты
- DrawScreen — сам экран с кнопками, шаблонами, переходами

Виджет корзин удалён. Данные корзин (Bucket) создаются здесь, в GaltonTable,
и передаются доске через board.buckets_ref для физики.

Отладочный виджет (debug_widget) теперь внутри доски (draw_board.py).
"""

import random

from kivy.animation import Animation
from kivy.clock import Clock
from kivy.core.window import Window
from kivy.graphics import Color, Rectangle
from kivy.uix.button import Button
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.image import Image

from screens.base_game_screen import BaseGameScreen
from screens.draw.template_manager import DrawTemplateManager
from screens.draw.draw_popup import DrawTemplatePopup
from screens.draw.draw_board import GaltonBoardWithHopper
from screens.draw.draw_widgets import ResultsList, Bucket


class GaltonTable(FloatLayout):
    """Единый контейнер высотой 2 экрана."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self.size_hint = (1, None)
        self.height = Window.height * 2
        self.pos_hint = {'x': 0, 'y': 0.5}

        with self.canvas.before:
            Color(0.1, 0.1, 0.15, 1)
            self.bg_rect = Rectangle(pos=self.pos, size=self.size)

        # === ФОНЫ ===
        self.top_bg = Image(
            source='assets/backgrounds/draw_b.png',
            allow_stretch=True,
            keep_ratio=False,
            size_hint=(1, 0.5),
            pos_hint={'x': 0, 'y': 0.5}
        )
        self.add_widget(self.top_bg)

        self.bottom_bg = Image(
            source='assets/backgrounds/draw_b.png',
            allow_stretch=True,
            keep_ratio=False,
            size_hint=(1, 0.5),
            pos_hint={'x': 0, 'y': 0}
        )
        self.add_widget(self.bottom_bg)

        # === ДОСКА ГАЛЬТОНА ===
        self.board = GaltonBoardWithHopper(
            size_hint=(0.85, 0.45),
            pos_hint={'x': 0.075, 'y': 0.55}
        )
        self.add_widget(self.board)

        # === ДАННЫЕ КОРЗИН (без виджета) ===
        self.buckets = self._create_buckets_data()
        self.board.buckets_ref = self.buckets

        # === СПИСОК РЕЗУЛЬТАТОВ ===
        self.results_list = ResultsList(
            size_hint=(0.85, 0.30),
            pos_hint={'x': 0.075, 'y': 0.02},
            opacity=0
        )
        self.add_widget(self.results_list)

        self.bind(size=self._update_size)
        Window.bind(on_resize=self._on_resize)

    def _create_buckets_data(self):
        """Создаёт список Bucket-данных для физики и результатов."""
        buckets = []
        total = 10
        screen_w = Window.width

        position_width = screen_w / total
        bucket_width = position_width * 0.8
        bucket_height = Window.height * 0.15

        team_names = [
            "Команда A", "Команда B", "Команда C", "Команда D", "Команда E",
            "Команда F", "Команда G", "Команда H", "Команда I", "Команда J"
        ]
        bucket_colors = [
            (1, 0, 0, 1), (0, 0, 1, 1), (0, 1, 0, 1),
            (1, 0.5, 0, 1), (0.5, 0, 1, 1),
            (1, 1, 0, 1), (0, 1, 1, 1), (1, 0, 1, 1),
            (0.5, 0.5, 0.5, 1), (0.6, 0.3, 0.1, 1)
        ]

        for i in range(total):
            x = i * position_width + position_width / 2
            y = self.height * 0.30

            name = team_names[i] if i < len(team_names) else f"Команда {i+1}"
            color = bucket_colors[i] if i < len(bucket_colors) else (
                random.random(), random.random(), random.random(), 1
            )

            bucket = Bucket(i, name, color, x, y, bucket_width, bucket_height)
            buckets.append(bucket)

        print(f"✅ Создано {len(buckets)} корзин (данные, без виджета)")
        return buckets

    def set_top_bg_to_draw(self):
        if self.top_bg:
            self.top_bg.source = 'assets/backgrounds/draw_r.png'
            self.top_bg.reload()
            print("🖼️ Верхний фон → draw_r.png")

    def set_top_bg_to_default(self):
        if self.top_bg:
            self.top_bg.source = 'assets/backgrounds/draw_b.png'
            self.top_bg.reload()
            print("🖼️ Верхний фон → draw_b.png")

    def _update_size(self, *args):
        self.height = Window.height * 2

    def _on_resize(self, window, width, height):
        self.height = height * 2

    def scroll_to_results(self):
        print("🎬 [GaltonTable.scroll_to_results] Начат переход к результатам")
        if hasattr(self, 'board') and self.board:
            print("🎬 [GaltonTable.scroll_to_results] Вызываю play_transition_debug_animation")
            self.board.play_transition_debug_animation()
        else:
            print("⚠️ [GaltonTable.scroll_to_results] board не найден!")

        anim = Animation(pos_hint={'y': 0}, duration=1.0, t='in_out_expo')
        anim.start(self)
        Clock.schedule_once(lambda dt: self._show_results(), 1.2)

    def _show_results(self):
        if self.results_list:
            self.results_list.show()
            anim = Animation(opacity=1, duration=0.5, t='in_quad')
            anim.start(self.results_list)

    def reset_view(self):
        print("🎬 [GaltonTable.reset_view] Начат возврат на верхний экран")
        if hasattr(self, 'board') and self.board:
            print("🎬 [GaltonTable.reset_view] Вызываю play_transition_debug_animation")
            self.board.play_transition_debug_animation()
        else:
            print("⚠️ [GaltonTable.reset_view] board не найден!")

        anim = Animation(pos_hint={'y': 0.5}, duration=5.0, t='out_expo')
        anim.start(self)
        if self.results_list:
            self.results_list.hide()
            anim = Animation(opacity=0, duration=0.3)
            anim.start(self.results_list)


class DrawScreen(BaseGameScreen):
    START_BUTTON_SIZE = 0.12
    START_BUTTON_POS_X = 0.02
    START_BUTTON_POS_Y = 0.915

    TEMPLATES_BUTTON_SIZE = 0.12
    TEMPLATES_BUTTON_POS_X = 0.85
    TEMPLATES_BUTTON_POS_Y = 0.915

    BTN_START_GREEN = 'assets/images/buttons/draw_g_button.png'
    BTN_START_RED = 'assets/images/buttons/draw_r_button.png'
    BTN_TEMPLATES_BLUE = 'assets/images/buttons/draw_template_b_button.png'
    BTN_TEMPLATES_RED = 'assets/images/buttons/draw_template_r_button.png'

    TOTAL_BUCKETS = 10

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.template_manager = DrawTemplateManager()
        self._last_touch_time = 0

        self.is_drawing = False
        self.balls_dropped = 0
        self.total_balls_to_drop = 0
        self.has_template_loaded = False
        self.balls_are_dropping = False
        self.current_template = None
        self._barrier_animation_started = False

        self.showing_results = False

        self.galton_table = None
        self.start_button = None
        self.templates_button = None

        self.current_teams_count = 0

        self.layout.bind(size=self.update_layout, pos=self.update_layout)

    def on_enter(self):
        super().on_enter()
        self.clear_ui()
        self.show_ui()

        self._barrier_animation_started = False
        self.showing_results = False

        saved_template = self.template_manager.load_selected_template()
        if saved_template:
            print(f"📋 Загружен сохраненный шаблон: {saved_template.get('name')}")
            self.current_template = saved_template
            self.on_template_loaded(saved_template)
        else:
            print("📋 Нет сохраненного шаблона, используем первый по умолчанию")
            templates = self.template_manager.get_templates()
            if templates:
                self.current_template = templates[0]
                self.on_template_loaded(templates[0])

        Clock.schedule_once(lambda dt: self.update_layout(), 0.1)
        Clock.schedule_once(lambda dt: self._update_bucket_labels(), 0.3)

    def on_leave(self):
        if self.current_template:
            template_id = self.current_template.get('id')
            if template_id:
                self.template_manager.save_selected_template(template_id)
                print(f"💾 При выходе сохранен шаблон: {self.current_template.get('name')}")

        if self.galton_table and hasattr(self.galton_table, 'board'):
            self.galton_table.board.reset_swipe_state()

        self.stop_all_animations()
        super().on_leave()

    def clear_ui(self):
        if not hasattr(self, 'layout'):
            return
        for child in self.layout.children[:]:
            if child not in (self.back_button,):
                self.layout.remove_widget(child)
        self.start_button = None
        self.templates_button = None
        self.galton_table = None

    def show_ui(self):
        self.galton_table = GaltonTable()
        self.layout.add_widget(self.galton_table)

        self.galton_table.board.on_ball_in_bucket = self.on_ball_in_bucket
        self.galton_table.board.on_all_balls_in_buckets = self.on_all_balls_in_buckets

        self._create_start_button()
        self._create_templates_button()

    def _create_start_button(self):
        if not self.galton_table:
            Clock.schedule_once(lambda dt: self._create_start_button(), 0.1)
            return

        layout_width = self.layout.width if self.layout.width else Window.width
        layout_height = self.layout.height if self.layout.height else Window.height

        if layout_width == 0 or layout_height == 0:
            Clock.schedule_once(lambda dt: self._create_start_button(), 0.1)
            return

        base_size = min(layout_width, layout_height)
        size = max(60, min(150, base_size * self.START_BUTTON_SIZE))

        pos_x = layout_width * self.START_BUTTON_POS_X
        pos_y = layout_height * self.START_BUTTON_POS_Y

        self.start_button = Button(
            background_normal=self.BTN_START_GREEN,
            background_down=self.BTN_START_GREEN,
            border=(0, 0, 0, 0),
            size_hint=(None, None),
            size=(size, size),
            pos=(pos_x, pos_y)
        )
        self.start_button.bind(on_press=self.on_start_press)
        self.layout.add_widget(self.start_button)

    def _create_templates_button(self):
        if not self.galton_table:
            Clock.schedule_once(lambda dt: self._create_templates_button(), 0.1)
            return

        layout_width = self.layout.width if self.layout.width else Window.width
        layout_height = self.layout.height if self.layout.height else Window.height

        if layout_width == 0 or layout_height == 0:
            Clock.schedule_once(lambda dt: self._create_templates_button(), 0.1)
            return

        base_size = min(layout_width, layout_height)
        size = max(60, min(150, base_size * self.TEMPLATES_BUTTON_SIZE))

        pos_x = layout_width * self.TEMPLATES_BUTTON_POS_X
        pos_y = layout_height * self.TEMPLATES_BUTTON_POS_Y

        self.templates_button = Button(
            background_normal=self.BTN_TEMPLATES_BLUE,
            background_down=self.BTN_TEMPLATES_BLUE,
            border=(0, 0, 0, 0),
            size_hint=(None, None),
            size=(size, size),
            pos=(pos_x, pos_y)
        )
        self.templates_button.bind(on_press=self.on_templates_press)
        self.layout.add_widget(self.templates_button)

    def on_touch_down(self, touch):
        if touch.is_double_tap:
            if self.galton_table and hasattr(self.galton_table, 'board'):
                board = self.galton_table.board
                if (board.x <= touch.x <= board.x + board.width and
                        board.y <= touch.y <= board.y + board.height):
                    board.spawn_wave(touch.x, touch.y)
                    return True
            return False

        return super().on_touch_down(touch)

    def on_templates_press(self, instance):
        if self.showing_results:
            print("⛔ Показ результатов — кнопка шаблонов заблокирована")
            return

        if self.is_drawing or self.balls_are_dropping:
            print("⛔ Жеребьёвка активна - кнопка шаблонов заблокирована")
            return

        self._close_barrier_and_open_popup()

    def _close_barrier_and_open_popup(self):
        if self.galton_table and hasattr(self.galton_table, 'board'):
            self.galton_table.board.animate_barrier_close(callback=self._open_templates_popup)
        else:
            self._open_templates_popup()

    def _open_templates_popup(self):
        print("📋 Открываем попап с шаблонами")
        popup = DrawTemplatePopup(
            template_manager=self.template_manager,
            callback=self.on_template_loaded
        )
        popup.open()

    def on_start_press(self, instance):
        if self.showing_results:
            print("⛔ Показ результатов — кнопка СТАРТ заблокирована")
            return

        if self.is_drawing or self.balls_are_dropping:
            print("⏳ Жеребьёвка уже идет!")
            return

        if not self.galton_table or not self.galton_table.board:
            print("⚠️ Ошибка: доска не инициализирована")
            return

        if self.galton_table.board.get_ball_count() == 0:
            print("⚠️ Нет шаров для жеребьёвки! Загрузите шаблон.")
            return

        print("🎯 Запуск жеребьёвки!")
        self.is_drawing = True
        self.balls_are_dropping = True

        self.galton_table.set_top_bg_to_draw()

        if self.start_button:
            self.start_button.background_normal = self.BTN_START_RED
            self.start_button.background_down = self.BTN_START_RED

        if self.templates_button:
            self.templates_button.background_normal = self.BTN_TEMPLATES_RED
            self.templates_button.background_down = self.BTN_TEMPLATES_RED

        self.galton_table.board.start_dropping()

    def on_all_balls_in_buckets(self):
        print("🎯 ВСЕ ШАРЫ ПОПАЛИ В КОРЗИНЫ!")
        self.is_drawing = False
        self.balls_are_dropping = False

        if self.templates_button:
            self.templates_button.background_normal = self.BTN_TEMPLATES_BLUE
            self.templates_button.background_down = self.BTN_TEMPLATES_BLUE

        Clock.schedule_once(lambda dt: self._show_results_stage(), 0.5)

    def _show_results_stage(self):
        if self.showing_results:
            return

        print("📊 Второй этап: показ результатов")
        self.showing_results = True

        self._set_buttons_enabled(False)

        if self.galton_table:
            if hasattr(self.galton_table, 'results_list'):
                self.galton_table.results_list.update_results(self.galton_table.buckets)

            self.galton_table.scroll_to_results()

    def _set_buttons_enabled(self, enabled):
        if self.start_button:
            self.start_button.disabled = not enabled
        if self.templates_button:
            self.templates_button.disabled = not enabled

    def on_ball_in_bucket(self, bucket_id, ball):
        if self.galton_table:
            if 0 <= bucket_id < len(self.galton_table.buckets):
                self.galton_table.buckets[bucket_id].add_ball(ball)
        print(f"🏀 Шар {ball.player_name} в корзине {bucket_id} (строка {ball.sprite_row})")

    def _reset_view(self):
        print("🔄 Сброс вида")
        self.showing_results = False

        self._set_buttons_enabled(True)

        if self.galton_table:
            self.galton_table.pos_hint = {'x': 0, 'y': -1}
            self.galton_table.set_top_bg_to_default()

        if self.start_button:
            self.start_button.background_normal = self.BTN_START_GREEN
            self.start_button.background_down = self.BTN_START_GREEN

        if self.templates_button:
            self.templates_button.background_normal = self.BTN_TEMPLATES_BLUE
            self.templates_button.background_down = self.BTN_TEMPLATES_BLUE

    def update_layout(self, *args):
        if not hasattr(self, 'layout') or not self.layout:
            return

        layout_width = self.layout.width
        layout_height = self.layout.height

        if layout_width == 0 or layout_height == 0:
            return

        base_size = min(layout_width, layout_height)

        if self.galton_table:
            self.galton_table.height = layout_height * 2

        if hasattr(self, 'start_button') and self.start_button:
            size = max(60, min(150, base_size * self.START_BUTTON_SIZE))
            pos_x = layout_width * self.START_BUTTON_POS_X
            pos_y = layout_height * self.START_BUTTON_POS_Y

            self.start_button.size = (size, size)
            self.start_button.pos = (pos_x, pos_y)

        if hasattr(self, 'templates_button') and self.templates_button:
            size = max(60, min(150, base_size * self.TEMPLATES_BUTTON_SIZE))
            pos_x = layout_width * self.TEMPLATES_BUTTON_POS_X
            pos_y = layout_height * self.TEMPLATES_BUTTON_POS_Y

            self.templates_button.size = (size, size)
            self.templates_button.pos = (pos_x, pos_y)

    def get_screen_width(self):
        return self.layout.width if self.layout else Window.width

    def get_screen_height(self):
        return self.layout.height if self.layout else Window.height

    def stop_all_animations(self):
        Animation.cancel_all(self)
        if self.galton_table and hasattr(self.galton_table, 'board'):
            if self.galton_table.board:
                self.galton_table.board.physics_running = False
                if self.galton_table.board.physics_update_timer:
                    self.galton_table.board.physics_update_timer.cancel()
                    self.galton_table.board.physics_update_timer = None
                if self.galton_table.board.barrier_renderer:
                    self.galton_table.board.barrier_renderer.stop_animation()
                self.galton_table.board.reset_swipe_state()

    def on_template_loaded(self, template):
        print(f"📋 [DrawScreen] Шаблон загружен: {template.get('name')}")
        players = template.get('players', [])
        colors = template.get('colors', [])
        teams = template.get('teams', 0)

        if players and self.galton_table and hasattr(self.galton_table, 'board'):
            if teams == 0:
                teams = len(players)
            self.current_teams_count = min(max(teams, 1), 10)
            print(f"👥 Команд в шаблоне: {self.current_teams_count}")

            self.galton_table.set_top_bg_to_default()
            self._set_buttons_enabled(True)

            if self.start_button:
                self.start_button.background_normal = self.BTN_START_GREEN
                self.start_button.background_down = self.BTN_START_GREEN

            if self.templates_button:
                self.templates_button.background_normal = self.BTN_TEMPLATES_BLUE
                self.templates_button.background_down = self.BTN_TEMPLATES_BLUE

            board = self.galton_table.board
            board.physics_running = False
            if board.physics_update_timer:
                board.physics_update_timer.cancel()
                board.physics_update_timer = None

            board.reset_swipe_state()
            board.clear_balls()

            if hasattr(self.galton_table, 'buckets'):
                for bucket in self.galton_table.buckets:
                    bucket.clear()

            self._reset_view()

            self.is_drawing = False
            self.balls_are_dropping = False
            self.balls_dropped = 0
            self.total_balls_to_drop = 0
            self.showing_results = False
            self._barrier_animation_started = False

            self._update_buckets(teams, players, colors)

            for i, name in enumerate(players):
                color = colors[i % len(colors)] if colors else [1, 0, 0, 1]
                board.add_ball(color, name)

            Clock.schedule_once(lambda dt: board.reset_balls_positions(), 0.1)

            self.has_template_loaded = True
            self.current_template = template

            Clock.schedule_once(lambda dt: self._animate_barrier(), 0.2)

            template_id = template.get('id')
            if template_id:
                self.template_manager.save_selected_template(template_id)
                print(f"💾 Сохранен выбранный шаблон: {template.get('name')} (ID: {template_id})")

    def _animate_barrier(self):
        if self._barrier_animation_started:
            print("⏭️ Анимация барьера уже была запущена, пропускаем")
            return

        if self.galton_table and hasattr(self.galton_table, 'buckets'):
            if self.galton_table.buckets:
                teams = self.current_teams_count
                if teams <= 0:
                    teams = 1
                teams = min(teams, self.TOTAL_BUCKETS)

                print(f"🎬 Барьер: teams={teams}")

                self._barrier_animation_started = True

                self.galton_table.board.animate_barrier_for_buckets(
                    teams,
                    callback=self._on_barrier_animation_complete
                )
                return

        print("⚠️ Корзины не созданы, пропускаем анимацию барьера")

    def _on_barrier_animation_complete(self):
        print("✅ Анимация барьера завершена")

    def _update_buckets(self, teams_count, players, colors):
        if not self.galton_table or not hasattr(self.galton_table, 'buckets'):
            return

        total = self.TOTAL_BUCKETS

        team_names = []
        for i in range(total):
            if i < len(players):
                team_names.append(players[i])
            else:
                team_names.append(f"Команда {chr(65 + i)}")

        bucket_colors = []
        for i in range(total):
            if i < len(colors):
                bucket_colors.append(colors[i])
            else:
                bucket_colors.append([random.random(), random.random(), random.random(), 1])

        for i, bucket in enumerate(self.galton_table.buckets):
            if i < len(team_names):
                bucket.team_name = team_names[i]
            if i < len(bucket_colors):
                bucket.color = bucket_colors[i]

    def _update_bucket_labels(self):
        pass

    def go_to_menu(self, instance=None):
        if self.showing_results:
            print("⬆️ [DrawScreen] Кнопка НАЗАД — возврат на верхний экран")
            self._reset_view()
            return

        print(f"🏠 [DrawScreen] Возврат в меню")
        self.stop_all_animations()
        self.is_drawing = False
        self.balls_are_dropping = False
        self.has_template_loaded = False
        self.showing_results = False
        if self.galton_table:
            if hasattr(self.galton_table, 'board'):
                self.galton_table.board.clear_balls()
                self.galton_table.board.reset_swipe_state()
            if hasattr(self.galton_table, 'buckets'):
                for bucket in self.galton_table.buckets:
                    bucket.clear()
        try:
            super().go_to_menu()
        except:
            from kivy.app import App
            App.get_running_app().root.current = 'menu'