import math
from kivy.vector import Vector


class BallPhysics:
    """Класс для физики мяча"""

    def __init__(self, pos, size, sound_callback=None, ball_type='default'):
        self.pos = Vector(pos)
        self.velocity = Vector(0, 0)
        self.size = size
        self.radius = size / 2
        self.friction = 0.995
        self.bounce_factor = 0.8
        self.sound_callback = sound_callback
        self.can_play_sound = True
        self.rotation = 0  # Текущий угол вращения
        self.prev_pos = Vector(pos)  # Предыдущая позиция для расчета вращения
        # Добавляем для анимации
        self.ball_type = ball_type
        self.rotation_angle = 0  # Угол для 2D вращения
        self.angular_velocity = 0  # Скорость вращения

        # Коэффициенты вращения для разных мячей
        self.rotation_coefficients = {
            'soccer': 1.2,
            'basketball': 0.8,
            'volleyball': 1.0,
            'tennis': 1.5,
            'default': 1.0
        }

    def update(self, dt, screen_width, screen_height):
        """Обновление физики с улучшенным вращением"""
        # Сохраняем старую скорость для вычисления вращения
        old_velocity = Vector(self.velocity)

        # Обновляем позицию (существующий код)
        self.velocity *= self.friction
        new_pos = self.pos + self.velocity * dt * 60
        self.check_boundaries(new_pos, screen_width, screen_height)
        self.pos = new_pos

        # Обновляем вращение на основе изменения скорости
        self.update_rotation(dt, old_velocity)

        if self.velocity.length() < 0.5:
            self.velocity = Vector(0, 0)
            self.angular_velocity *= 0.9  # Плавная остановка вращения
            self.can_play_sound = True

    def update_rotation(self, dt, old_velocity):
        """Обновляет параметры вращения для анимации"""
        speed = self.velocity.length()

        if speed > 0:
            # Вычисляем изменение направления
            if old_velocity.length() > 0:
                dot_product = old_velocity.dot(self.velocity.normalize())
                angle_change = math.acos(max(-1, min(1, dot_product)))

                # Преобразуем в угловую скорость
                coefficient = self.rotation_coefficients.get(
                    self.ball_type,
                    self.rotation_coefficients['default']
                )

                self.angular_velocity = angle_change * 180 / math.pi * coefficient / dt

                # Определяем направление вращения
                cross_product = old_velocity.x * self.velocity.y - old_velocity.y * self.velocity.x
                if cross_product < 0:
                    self.angular_velocity = -self.angular_velocity

            # Обновляем угол вращения
            self.rotation_angle += self.angular_velocity * dt

            # Нормализуем угол
            self.rotation_angle %= 360
        else:
            # Плавная остановка
            self.angular_velocity *= 0.95

    def get_animation_frame(self, total_frames=64, distance_traveled=0):
        """
        Вычисляет кадр анимации на основе пройденного расстояния

        Args:
            total_frames: общее количество кадров в спрайт-листе
            distance_traveled: общее пройденное расстояние мяча

        Returns:
            Номер кадра (0 до total_frames-1)
        """
        if total_frames <= 0:
            return 0

        # Длина окружности мяча
        circumference = 2 * math.pi * self.radius

        # Сколько раз мяч совершил полный оборот
        rotations = distance_traveled / circumference

        # Кадр на основе количества оборотов
        frame = int(rotations * total_frames) % total_frames

        return frame

    def check_boundaries(self, new_pos, screen_width, screen_height):
        """Проверка столкновений с границами"""
        bounce_occurred = False

        if new_pos.x + self.radius > screen_width:
            self.velocity.x = -abs(self.velocity.x) * self.bounce_factor
            new_pos.x = screen_width - self.radius
            bounce_occurred = True

        if new_pos.x - self.radius < 0:
            self.velocity.x = abs(self.velocity.x) * self.bounce_factor
            new_pos.x = self.radius
            bounce_occurred = True

        if new_pos.y + self.radius > screen_height:
            self.velocity.y = -abs(self.velocity.y) * self.bounce_factor
            new_pos.y = screen_height - self.radius
            bounce_occurred = True

        if new_pos.y - self.radius < 0:
            self.velocity.y = abs(self.velocity.y) * self.bounce_factor
            new_pos.y = self.radius
            bounce_occurred = True

        if bounce_occurred and self.sound_callback:
            self.sound_callback()

    def apply_force(self, force_vector):
        """Применить силу к мячу"""
        self.velocity += force_vector
        self.can_play_sound = True