"""
Модуль с эффектами частиц для использования в разных экранах
"""

from kivy.uix.widget import Widget
from kivy.clock import Clock
from kivy.properties import NumericProperty, BooleanProperty, ColorProperty, ListProperty
from kivy.core.window import Window
from kivy.graphics import Color, Ellipse
import random


class DustParticle(Widget):
    """Частица пыли/искры с анимацией"""
    velocity_x = NumericProperty(0)
    velocity_y = NumericProperty(0)
    opacity = NumericProperty(1.0)
    size_factor = NumericProperty(1.0)
    color = ColorProperty((1, 1, 0.5, 0.8))
    glow_intensity = NumericProperty(1.0)
    target_glow = NumericProperty(1.0)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.size = (random.uniform(2, 5), random.uniform(2, 5))
        self.velocity_x = random.uniform(-30, 30)
        self.velocity_y = random.uniform(-30, 30)
        self.opacity = random.uniform(0.3, 0.8)
        self.color = (
            random.uniform(0.8, 1.0),
            random.uniform(0.5, 0.8),
            random.uniform(0.2, 0.4),
            self.opacity
        )
        self.glow_intensity = 1.0
        self.target_glow = 1.0
        self.x = random.uniform(0, Window.width)
        self.y = random.uniform(0, Window.height)
        self.bind(pos=self._update_rect, size=self._update_rect)

    def _update_rect(self, *args):
        self.canvas.clear()
        with self.canvas:
            Color(*self.color[:3], self.color[3] * self.glow_intensity)
            Ellipse(pos=self.pos, size=self.size)
            if self.glow_intensity > 0.3:
                glow_size = (self.size[0] * 3, self.size[1] * 3)
                glow_pos = (self.x - self.size[0], self.y - self.size[1])
                Color(*self.color[:3], self.color[3] * self.glow_intensity * 0.3)
                Ellipse(pos=glow_pos, size=glow_size)

    def update(self, dt):
        self.x += self.velocity_x * dt
        self.y += self.velocity_y * dt
        if random.random() < 0.05:
            self.velocity_x += random.uniform(-10, 10)
            self.velocity_y += random.uniform(-10, 10)
        max_speed = 50
        self.velocity_x = max(-max_speed, min(max_speed, self.velocity_x))
        self.velocity_y = max(-max_speed, min(max_speed, self.velocity_y))
        if self.x < -self.width:
            self.x = Window.width
        elif self.x > Window.width:
            self.x = -self.width
        if self.y < -self.height:
            self.y = Window.height
        elif self.y > Window.height:
            self.y = -self.height
        if abs(self.glow_intensity - self.target_glow) > 0.01:
            self.glow_intensity += (self.target_glow - self.glow_intensity) * 0.1


class ParticleSystem(Widget):
    """Система частиц для создания эффекта пыли/искр"""
    particles = ListProperty([])
    is_active = BooleanProperty(False)
    glow_mode = BooleanProperty(False)
    base_glow = NumericProperty(0.5)
    active_glow = NumericProperty(1.2)

    def __init__(self, num_particles=20, **kwargs):
        super().__init__(**kwargs)
        self.num_particles = num_particles
        self.update_clock = None
        self.bind(pos=self._update_all, size=self._update_all)
        self.create_particles()
        self.start_perpetual_motion()

    def create_particles(self):
        self.particles = []
        for _ in range(self.num_particles):
            particle = DustParticle()
            self.particles.append(particle)
            self.add_widget(particle)

    def start_perpetual_motion(self):
        self.is_active = True
        if not self.update_clock:
            self.update_clock = Clock.schedule_interval(self.update_particles, 1 / 60)

    def set_glow_mode(self, active=True):
        self.glow_mode = active
        target_glow = self.active_glow if active else self.base_glow
        for particle in self.particles:
            particle.target_glow = target_glow

    def update_particles(self, dt):
        if not self.is_active:
            return
        for particle in self.particles:
            particle.update(dt)
        if self.glow_mode and random.random() < 0.02:
            for particle in self.particles:
                particle.glow_intensity = min(particle.target_glow * 1.3, 2.0)

    def _update_all(self, *args):
        for particle in self.particles:
            particle._update_rect()

    def cleanup(self):
        self.is_active = False
        if self.update_clock:
            self.update_clock.cancel()
            self.update_clock = None
        self.particles = []
        self.clear_widgets()