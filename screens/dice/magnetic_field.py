"""
Эффект магнитного поля - отталкивание кубиков от стакана
"""
import math
from kivy.clock import Clock
from kivy.graphics import Color, Ellipse, Rectangle

DEBUG_MAGNETIC = False  # Отладка магнитного поля - ТОЛЬКО ДЛЯ РАЗРАБОТКИ


class MagneticField:
    """Класс для управления эффектом отталкивания кубиков от стакана"""

    def __init__(self, drop_zone, dice_list, glass_start_pos, glass_size, dice_size):
        """
        Инициализация эффекта магнитного поля

        Параметры:
            drop_zone: зона, в которой могут находиться кубики
            dice_list: список кубиков
            glass_start_pos: позиция стакана (x, y)
            glass_size: размер стакана
            dice_size: размер кубика
        """
        self.drop_zone = drop_zone
        self.dice_list = dice_list
        self.glass_start_pos = glass_start_pos
        self.glass_size = glass_size
        self.dice_size = dice_size

        # Параметры эффекта
        self.REPULSION_RADIUS_MULTIPLIER = 0.2  # Множитель радиуса относительно размера стакана

        # Параметры полей кубиков
        # БОЛЬШОЕ поле кубика (для взаимодействия со стаканом)
        self.DICE_BIG_COLLIDER_RADIUS_MULTIPLIER = 0.5  # Радиус = размер кубика * 0.4
        # МАЛЕНЬКОЕ поле кубика (для взаимодействия между кубиками)
        self.DICE_SMALL_COLLIDER_RADIUS_MULTIPLIER = 0.25  # Радиус = размер кубика * 0.25

        # Параметры расстояний между кубиками
        self.MIN_DISTANCE_MULTIPLIER = 0.5    # Минимальное расстояние = размер куба * 0.5
        self.MAX_DISTANCE_MULTIPLIER = 0.35   # Максимальное расстояние = размер куба * 0.35
        self.ATTRACTION_FORCE = 100           # Сила притяжения

        # Коэффициент овальности полей (соотношение X/Y от drop_zone)
        self.oval_ratio_x = 1.0  # Будет вычислен из drop_zone
        self.oval_ratio_y = 1.0  # Будет вычислен из drop_zone

        self.is_active = False
        self.update_event = None

        # Сохраняем исходные позиции кубиков
        self.original_positions = []

        # Для визуализации зоны отталкивания стакана
        self.glass_visualization = None

        # Для визуализации полей кубиков
        self.dice_big_visualizations = {}   # Большие поля (фиолетовые)
        self.dice_small_visualizations = {} # Маленькие поля (желтые)

        # Предыдущая позиция стакана для отслеживания движения
        self.prev_glass_pos = glass_start_pos

        # Вычисляем текущий радиус
        self.current_radius = int(self.glass_size * self.REPULSION_RADIUS_MULTIPLIER)

        # Вычисляем коэффициенты овальности из drop_zone
        self._update_oval_ratio()

        if DEBUG_MAGNETIC:
            print("🧲 [MAGNETIC] Инициализация магнитного поля (ОВАЛЬНЫЕ ПОЛЯ)")
            print(f"   Размер стакана: {self.glass_size}px")
            print(f"   Радиус поля стакана: {self.current_radius}px")
            print(f"   БОЛЬШОЕ поле кубика (со стаканом): {int(self.dice_size * self.DICE_BIG_COLLIDER_RADIUS_MULTIPLIER)}px")
            print(f"   МАЛЕНЬКОЕ поле кубика (между кубами): {int(self.dice_size * self.DICE_SMALL_COLLIDER_RADIUS_MULTIPLIER)}px")
            print(f"   Мин. расстояние между кубами: {self.dice_size * self.MIN_DISTANCE_MULTIPLIER:.0f}px")
            print(f"   Макс. расстояние между кубами: {self.dice_size * self.MAX_DISTANCE_MULTIPLIER:.0f}px")
            print(f"   Сила притяжения: {self.ATTRACTION_FORCE}")
            print(f"   Овальность X: {self.oval_ratio_x:.2f}, Y: {self.oval_ratio_y:.2f}")

    def _update_oval_ratio(self):
        """Обновляет коэффициенты овальности на основе drop_zone"""
        if self.drop_zone:
            zone_width = self.drop_zone.size[0]
            zone_height = self.drop_zone.size[1]
            if zone_width > 0 and zone_height > 0:
                # Нормализуем соотношение (большая сторона = 1, меньшая = пропорция)
                if zone_width >= zone_height:
                    self.oval_ratio_x = 1.0
                    self.oval_ratio_y = zone_height / zone_width
                else:
                    self.oval_ratio_x = zone_width / zone_height
                    self.oval_ratio_y = 1.0

                if DEBUG_MAGNETIC:
                    print(f"🧲 [OVAL] Размер drop_zone: {zone_width:.0f}x{zone_height:.0f}")
                    print(f"   Коэффициенты: X={self.oval_ratio_x:.2f}, Y={self.oval_ratio_y:.2f}")

    def get_repulsion_radius_oval(self, base_radius):
        """
        Возвращает овальные размеры поля (width, height) на основе базового радиуса
        """
        return (base_radius * self.oval_ratio_x * 2, base_radius * self.oval_ratio_y * 2)

    def get_repulsion_radius(self):
        """Возвращает актуальный радиус отталкивания стакана (привязан к размеру стакана)"""
        return int(self.glass_size * self.REPULSION_RADIUS_MULTIPLIER)

    def get_dice_big_radius(self):
        """Возвращает радиус БОЛЬШОГО поля кубика (для взаимодействия со стаканом)"""
        return int(self.dice_size * self.DICE_BIG_COLLIDER_RADIUS_MULTIPLIER)

    def get_dice_small_radius(self):
        """Возвращает радиус МАЛЕНЬКОГО поля кубика (для взаимодействия между кубиками)"""
        return int(self.dice_size * self.DICE_SMALL_COLLIDER_RADIUS_MULTIPLIER)

    def get_point_a_position(self):
        """Возвращает позицию точки А (центра стакана)"""
        point_a_x = self.glass_start_pos[0] + self.glass_size / 6.5
        point_a_y = self.glass_start_pos[1] + self.glass_size / 2
        return (point_a_x, point_a_y)

    def get_dice_center(self, dice_pos):
        """Возвращает центр кубика"""
        return (dice_pos[0] + self.dice_size / 2, dice_pos[1] + self.dice_size / 2)

    def is_colliding_with_glass(self, dice_pos, point_a_pos, glass_radius):
        """
        Проверяет, сталкивается ли БОЛЬШОЕ поле кубика (овальное) с полем стакана (овальное)

        Возвращает: (colliding, overlap, dx, dy, distance)
        """
        # Центр кубика
        dice_center_x, dice_center_y = self.get_dice_center(dice_pos)

        # Радиусы полей
        dice_radius = self.get_dice_big_radius()

        # Применяем овальность к радиусам
        dice_radius_x = dice_radius * self.oval_ratio_x
        dice_radius_y = dice_radius * self.oval_ratio_y

        glass_radius_x = glass_radius * self.oval_ratio_x
        glass_radius_y = glass_radius * self.oval_ratio_y

        # Вектор от стакана к кубику
        dx = dice_center_x - point_a_pos[0]
        dy = dice_center_y - point_a_pos[1]

        # Нормализованное расстояние с учетом овальности
        # Уравнение эллипса: (x/a)^2 + (y/b)^2 <= 1
        # Для столкновения двух эллипсов используем приближение
        norm_dx = dx / (glass_radius_x + dice_radius_x)
        norm_dy = dy / (glass_radius_y + dice_radius_y)
        distance = math.sqrt(norm_dx * norm_dx + norm_dy * norm_dy)

        # Столкновение, если нормализованное расстояние <= 1
        colliding = distance <= 1.0

        # Вычисляем перекрытие
        overlap = (1.0 - distance) * (glass_radius_x + dice_radius_x) if colliding else 0

        return colliding, overlap, dx, dy, distance

    def is_colliding_between_dice(self, pos1, pos2):
        """
        Проверяет, сталкиваются ли МАЛЕНЬКИЕ поля двух кубиков (овальные)

        Возвращает: (colliding, overlap, dx, dy, distance)
        """
        # Центры кубиков
        center1_x, center1_y = self.get_dice_center(pos1)
        center2_x, center2_y = self.get_dice_center(pos2)

        # Радиус МАЛЕНЬКОГО поля кубиков
        dice_radius = self.get_dice_small_radius()

        # Применяем овальность
        dice_radius_x = dice_radius * self.oval_ratio_x
        dice_radius_y = dice_radius * self.oval_ratio_y

        # Вектор между кубиками
        dx = center1_x - center2_x
        dy = center1_y - center2_y

        # Нормализованное расстояние с учетом овальности
        norm_dx = dx / (dice_radius_x * 2)
        norm_dy = dy / (dice_radius_y * 2)
        distance = math.sqrt(norm_dx * norm_dx + norm_dy * norm_dy)

        # Столкновение, если нормализованное расстояние <= 1
        colliding = distance <= 1.0

        # Вычисляем перекрытие
        overlap = (1.0 - distance) * (dice_radius_x * 2) if colliding else 0

        return colliding, overlap, dx, dy, distance

    def calculate_repulsion_from_glass(self, dice_pos, point_a_pos, glass_radius):
        """
        Вычисляет смещение кубика от стакана (используя БОЛЬШОЕ поле)

        Возвращает: (offset_x, offset_y) - смещение кубика
        """
        colliding, overlap, dx, dy, distance = self.is_colliding_with_glass(dice_pos, point_a_pos, glass_radius)

        # Если нет столкновения - не двигаем
        if not colliding:
            return (0, 0)

        # Радиусы полей с учетом овальности
        dice_radius = self.get_dice_big_radius()
        dice_radius_x = dice_radius * self.oval_ratio_x
        dice_radius_y = dice_radius * self.oval_ratio_y
        glass_radius_x = glass_radius * self.oval_ratio_x
        glass_radius_y = glass_radius * self.oval_ratio_y

        # Вычисляем, насколько нужно отодвинуть кубик, чтобы выйти из столкновения
        if abs(dx) > 0.01 or abs(dy) > 0.01:
            # Нужно отодвинуть на (перекрытие + небольшой запас) с учетом овальности
            needed_offset = overlap + 3  # +3 пикселя запаса
            # Направление от стакана с учетом овальности
            direction_x = dx / (glass_radius_x + dice_radius_x)
            direction_y = dy / (glass_radius_y + dice_radius_y)
            norm = math.sqrt(direction_x * direction_x + direction_y * direction_y)
            if norm > 0:
                direction_x /= norm
                direction_y /= norm
            # Смещение
            offset_x = direction_x * needed_offset
            offset_y = direction_y * needed_offset
        else:
            # Центры совпадают - отодвигаем вправо
            offset_x = glass_radius_x + dice_radius_x + 3
            offset_y = 0

        if DEBUG_MAGNETIC and colliding:
            print(f"🧲 [GLASS_COLLISION] СТОЛКНОВЕНИЕ СО СТАКАНОМ!")
            print(f"   Дистанция: {distance:.2f}, Перекрытие: {overlap:.0f}px")
            print(f"   Смещение: ({offset_x:.1f}, {offset_y:.1f})")

        return (offset_x, offset_y)

    def calculate_repulsion_between_dice(self, pos1, pos2):
        """
        Вычисляет смещение для двух кубиков при столкновении их МАЛЕНЬКИХ полей

        Возвращает: (offset1_x, offset1_y, offset2_x, offset2_y) - смещение для обоих кубиков
        """
        colliding, overlap, dx, dy, distance = self.is_colliding_between_dice(pos1, pos2)

        # Если нет столкновения - не двигаем
        if not colliding:
            return (0, 0, 0, 0)

        # Радиус МАЛЕНЬКОГО поля кубика с учетом овальности
        dice_radius = self.get_dice_small_radius()
        dice_radius_x = dice_radius * self.oval_ratio_x
        dice_radius_y = dice_radius * self.oval_ratio_y

        # Вычисляем, насколько нужно раздвинуть кубики
        if abs(dx) > 0.01 or abs(dy) > 0.01:
            # Нужно раздвинуть на (перекрытие + небольшой запас)
            needed_offset = overlap + 2  # +2 пикселя запаса
            # Направление между кубиками с учетом овальности
            direction_x = dx / (dice_radius_x * 2)
            direction_y = dy / (dice_radius_y * 2)
            norm = math.sqrt(direction_x * direction_x + direction_y * direction_y)
            if norm > 0:
                direction_x /= norm
                direction_y /= norm
            # Смещение для каждого кубика (половина от нужного смещения)
            half_offset = needed_offset / 2
            offset1_x = direction_x * half_offset
            offset1_y = direction_y * half_offset
            offset2_x = -direction_x * half_offset
            offset2_y = -direction_y * half_offset
        else:
            # Центры совпадают - раздвигаем в разные стороны
            offset1_x = dice_radius_x + 2
            offset1_y = 0
            offset2_x = -dice_radius_x - 2
            offset2_y = 0

        if DEBUG_MAGNETIC and colliding:
            print(f"🧲 [DICE_COLLISION] СТОЛКНОВЕНИЕ МЕЖДУ КУБИКАМИ!")
            print(f"   Дистанция: {distance:.2f}, Перекрытие: {overlap:.0f}px")
            print(f"   Смещение1: ({offset1_x:.1f}, {offset1_y:.1f})")
            print(f"   Смещение2: ({offset2_x:.1f}, {offset2_y:.1f})")

        return (offset1_x, offset1_y, offset2_x, offset2_y)

    def clamp_to_zone(self, pos, dice):
        """
        Ограничивает позицию кубика пределами drop_zone
        """
        if not self.drop_zone:
            return pos

        # Получаем границы зоны
        zone_left = self.drop_zone.pos[0]
        zone_right = self.drop_zone.pos[0] + self.drop_zone.size[0]
        zone_bottom = self.drop_zone.pos[1]
        zone_top = self.drop_zone.pos[1] + self.drop_zone.size[1]

        # Ограничиваем позицию
        new_x = max(zone_left, min(zone_right - dice.width, pos[0]))
        new_y = max(zone_bottom, min(zone_top - dice.height, pos[1]))

        return (new_x, new_y)

    def enforce_min_distance_between_dice(self):
        """
        Обеспечивает минимальное расстояние между кубиками (отталкивание)
        """
        if len(self.dice_list) < 2:
            return

        # Получаем актуальный размер кубика
        current_dice_size = self.dice_list[0].width
        min_distance = current_dice_size * self.MIN_DISTANCE_MULTIPLIER

        # Несколько итераций для плавного разделения
        for _ in range(5):
            for i, dice1 in enumerate(self.dice_list):
                for j, dice2 in enumerate(self.dice_list):
                    if i >= j:
                        continue

                    # Центры кубиков
                    center1_x = dice1.pos[0] + dice1.width / 2
                    center1_y = dice1.pos[1] + dice1.height / 2
                    center2_x = dice2.pos[0] + dice2.width / 2
                    center2_y = dice2.pos[1] + dice2.height / 2

                    # Расстояние между центрами
                    dx = center1_x - center2_x
                    dy = center1_y - center2_y
                    distance = math.sqrt(dx * dx + dy * dy)

                    # Если кубики слишком близко
                    if distance < min_distance and distance > 0:
                        # Вычисляем перекрытие
                        overlap = min_distance - distance
                        force = overlap * 0.5

                        # Направление отталкивания
                        nx = dx / distance
                        ny = dy / distance

                        # Смещаем оба кубика в противоположные стороны
                        half_force = force / 2
                        offset1_x = nx * half_force
                        offset1_y = ny * half_force
                        offset2_x = -nx * half_force
                        offset2_y = -ny * half_force

                        # Применяем смещение
                        new_pos1 = (dice1.pos[0] + offset1_x, dice1.pos[1] + offset1_y)
                        new_pos2 = (dice2.pos[0] + offset2_x, dice2.pos[1] + offset2_y)

                        # Ограничиваем зоной
                        new_pos1 = self.clamp_to_zone(new_pos1, dice1)
                        new_pos2 = self.clamp_to_zone(new_pos2, dice2)

                        # Устанавливаем новые позиции
                        dice1.pos = new_pos1
                        dice2.pos = new_pos2

                        # Обновляем позицию свечения
                        if dice1.glow:
                            dice1.glow.update_position(dice1.pos, dice1.dice_size)
                        if dice2.glow:
                            dice2.glow.update_position(dice2.pos, dice2.dice_size)

                        if DEBUG_MAGNETIC:
                            print(f"🧲 [MIN_DISTANCE] Раздвигаем кубики!")
                            print(f"   Расстояние: {distance:.1f}px, Нужно: {min_distance:.1f}px")
                            print(f"   Перекрытие: {overlap:.1f}px")
                            print(f"   Смещение1: ({offset1_x:.1f}, {offset1_y:.1f})")
                            print(f"   Смещение2: ({offset2_x:.1f}, {offset2_y:.1f})")

    def enforce_max_distance_between_dice(self):
        """
        Обеспечивает максимальное расстояние между кубиками (притягивание)
        """
        if len(self.dice_list) < 2:
            return

        # Получаем актуальный размер кубика
        current_dice_size = self.dice_list[0].width
        max_distance = current_dice_size * self.MAX_DISTANCE_MULTIPLIER

        # Находим центр масс всех кубиков
        center_x = 0
        center_y = 0
        for dice in self.dice_list:
            center_x += dice.pos[0] + dice.width / 2
            center_y += dice.pos[1] + dice.height / 2
        center_x /= len(self.dice_list)
        center_y /= len(self.dice_list)

        # Для каждого кубика проверяем расстояние до центра масс
        for dice in self.dice_list:
            dice_center_x = dice.pos[0] + dice.width / 2
            dice_center_y = dice.pos[1] + dice.height / 2

            # Вектор от кубика к центру масс
            dx = center_x - dice_center_x
            dy = center_y - dice_center_y
            distance = math.sqrt(dx * dx + dy * dy)

            # Если кубик слишком далеко от центра масс
            if distance > max_distance and distance > 0:
                # Вычисляем силу притяжения
                force = self.ATTRACTION_FORCE * (distance / max_distance)
                force = min(force, 2.0)  # Ограничиваем максимальную силу

                # Направление к центру масс
                nx = dx / distance
                ny = dy / distance

                # Смещение к центру
                offset_x = nx * force
                offset_y = ny * force

                # Применяем смещение
                new_x = dice.pos[0] + offset_x
                new_y = dice.pos[1] + offset_y
                new_pos = self.clamp_to_zone((new_x, new_y), dice)

                if new_pos[0] != dice.pos[0] or new_pos[1] != dice.pos[1]:
                    dice.pos = new_pos

                    # Обновляем позицию свечения
                    if dice.glow:
                        dice.glow.update_position(dice.pos, dice.dice_size)

                    if DEBUG_MAGNETIC:
                        print(f"🧲 [MAX_DISTANCE] Притягиваем кубик к центру!")
                        print(f"   Расстояние: {distance:.0f}px, Максимум: {max_distance:.0f}px")
                        print(f"   Смещение: ({offset_x:.1f}, {offset_y:.1f})")

    def update_visualizations(self, point_a_pos, glass_radius):
        """Обновляет визуализацию полей (овальные)"""
        if not DEBUG_MAGNETIC or not self.drop_zone:
            return

        # Обновляем визуализацию поля стакана (овальное)
        if self.glass_visualization:
            try:
                self.drop_zone.canvas.before.remove(self.glass_visualization)
            except:
                pass
            self.glass_visualization = None

        glass_width = glass_radius * self.oval_ratio_x * 2
        glass_height = glass_radius * self.oval_ratio_y * 2

        with self.drop_zone.canvas.before:
            Color(0.5, 0, 1, 0.3)  # Фиолетовый полупрозрачный - поле стакана
            self.glass_visualization = Ellipse(
                pos=(point_a_pos[0] - glass_width/2, point_a_pos[1] - glass_height/2),
                size=(glass_width, glass_height)
            )

        # Обновляем визуализацию БОЛЬШИХ полей кубиков (овальные)
        for viz in self.dice_big_visualizations.values():
            try:
                self.drop_zone.canvas.before.remove(viz)
            except:
                pass
        self.dice_big_visualizations.clear()

        big_radius = self.get_dice_big_radius()
        big_width = big_radius * self.oval_ratio_x * 2
        big_height = big_radius * self.oval_ratio_y * 2

        with self.drop_zone.canvas.before:
            for i, dice in enumerate(self.dice_list):
                center_x, center_y = self.get_dice_center(dice.pos)
                Color(0, 0.5, 1, 0.3)  # Синий - БОЛЬШОЕ поле кубика (для стакана)
                self.dice_big_visualizations[i] = Ellipse(
                    pos=(center_x - big_width/2, center_y - big_height/2),
                    size=(big_width, big_height)
                )

        # Обновляем визуализацию МАЛЕНЬКИХ полей кубиков (овальные)
        for viz in self.dice_small_visualizations.values():
            try:
                self.drop_zone.canvas.before.remove(viz)
            except:
                pass
        self.dice_small_visualizations.clear()

        small_radius = self.get_dice_small_radius()
        small_width = small_radius * self.oval_ratio_x * 2
        small_height = small_radius * self.oval_ratio_y * 2

        with self.drop_zone.canvas.before:
            for i, dice in enumerate(self.dice_list):
                center_x, center_y = self.get_dice_center(dice.pos)
                Color(1, 1, 0, 0.25)  # Желтый - МАЛЕНЬКОЕ поле кубика (между кубами)
                self.dice_small_visualizations[i] = Ellipse(
                    pos=(center_x - small_width/2, center_y - small_height/2),
                    size=(small_width, small_height)
                )

    def update_repulsion(self, dt):
        """
        Мгновенно обновляет позиции кубиков при каждом движении стакана
        """
        if not self.is_active or not self.dice_list or not self.drop_zone:
            return

        # Получаем актуальный радиус стакана
        glass_radius = self.get_repulsion_radius()

        # Получаем позицию точки А (стакан)
        point_a_pos = self.get_point_a_position()

        # Обновляем визуализацию
        self.update_visualizations(point_a_pos, glass_radius)

        # 1. Проверяем столкновение кубиков со стаканом (через БОЛЬШИЕ поля)
        for dice in self.dice_list:
            offset_x, offset_y = self.calculate_repulsion_from_glass(dice.pos, point_a_pos, glass_radius)
            if offset_x != 0 or offset_y != 0:
                new_x = dice.pos[0] + offset_x
                new_y = dice.pos[1] + offset_y
                new_pos = self.clamp_to_zone((new_x, new_y), dice)
                dice.pos = new_pos
                if dice.glow:
                    dice.glow.update_position(dice.pos, dice.dice_size)

        # 2. Обеспечиваем минимальное расстояние между кубиками (отталкивание)
        self.enforce_min_distance_between_dice()

        # 3. Обеспечиваем максимальное расстояние между кубиками (притягивание)
        self.enforce_max_distance_between_dice()

    def start(self):
        """Запускает эффект магнитного поля"""
        if self.is_active:
            if DEBUG_MAGNETIC:
                print("🧲 [MAGNETIC] Поле уже активно")
            return

        self.is_active = True

        # Сохраняем исходные позиции кубиков
        self.original_positions = []
        for dice in self.dice_list:
            self.original_positions.append(dice.pos)

        # Сохраняем начальную позицию стакана
        self.prev_glass_pos = (self.glass_start_pos[0], self.glass_start_pos[1])

        # Запускаем периодическое обновление
        self.update_event = Clock.schedule_interval(self.update_repulsion, 0.05)

        if DEBUG_MAGNETIC:
            glass_radius = self.get_repulsion_radius()
            big_radius = self.get_dice_big_radius()
            small_radius = self.get_dice_small_radius()
            min_dist = self.dice_size * self.MIN_DISTANCE_MULTIPLIER
            max_dist = self.dice_size * self.MAX_DISTANCE_MULTIPLIER
            glass_width = glass_radius * self.oval_ratio_x * 2
            glass_height = glass_radius * self.oval_ratio_y * 2
            print("🧲 [MAGNETIC] Эффект магнитного поля ВКЛЮЧЕН (ОВАЛЬНЫЕ ПОЛЯ)")
            print(f"   Размер поля стакана: {glass_width:.0f}x{glass_height:.0f}px")
            print(f"   БОЛЬШОЕ поле кубика: {big_radius * self.oval_ratio_x * 2:.0f}x{big_radius * self.oval_ratio_y * 2:.0f}px")
            print(f"   МАЛЕНЬКОЕ поле кубика: {small_radius * self.oval_ratio_x * 2:.0f}x{small_radius * self.oval_ratio_y * 2:.0f}px")
            print(f"   Мин. расстояние между кубами: {min_dist:.0f}px")
            print(f"   Макс. расстояние между кубами: {max_dist:.0f}px")
            print(f"   Сила притяжения: {self.ATTRACTION_FORCE}")
            print(f"   Позиция стакана: {self.glass_start_pos}")
            point_a = self.get_point_a_position()
            print(f"   Точка А: ({point_a[0]:.0f}, {point_a[1]:.0f})")
            print(f"   Кубиков в поле: {len(self.dice_list)}")

    def stop(self):
        """Останавливает эффект магнитного поля и возвращает кубики на место"""
        if not self.is_active:
            if DEBUG_MAGNETIC:
                print("🧲 [MAGNETIC] Поле уже выключено")
            return

        self.is_active = False

        # Останавливаем периодическое обновление
        if self.update_event:
            self.update_event.cancel()
            self.update_event = None

        # Удаляем визуализации
        if self.glass_visualization:
            try:
                self.drop_zone.canvas.before.remove(self.glass_visualization)
            except:
                pass
            self.glass_visualization = None

        for viz in self.dice_big_visualizations.values():
            try:
                self.drop_zone.canvas.before.remove(viz)
            except:
                pass
        self.dice_big_visualizations.clear()

        for viz in self.dice_small_visualizations.values():
            try:
                self.drop_zone.canvas.before.remove(viz)
            except:
                pass
        self.dice_small_visualizations.clear()

        # Возвращаем кубики на исходные позиции
        for i, dice in enumerate(self.dice_list):
            if i < len(self.original_positions):
                original_pos = self.original_positions[i]
                dice.pos = original_pos
                if dice.glow:
                    dice.glow.update_position(dice.pos, dice.dice_size)

        if DEBUG_MAGNETIC:
            print("🧲 [MAGNETIC] Эффект магнитного поля ВЫКЛЮЧЕН")

    def update_glass_position(self, glass_start_pos):
        """Обновляет позицию стакана"""
        self.glass_start_pos = glass_start_pos
        if DEBUG_MAGNETIC and self.is_active:
            print(f"🧲 [MAGNETIC] Обновлена позиция стакана: {glass_start_pos}")

    def set_active(self, active):
        """Включает/выключает эффект"""
        if active and not self.is_active:
            self.start()
        elif not active and self.is_active:
            self.stop()

    def is_magnetic_active(self):
        """Возвращает состояние эффекта"""
        return self.is_active