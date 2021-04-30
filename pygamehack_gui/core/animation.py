import colorsys
import time


class Color:
    def __init__(self, v1, v2, v3, is_rgb):
        self.is_rgb = is_rgb
        self.values = v1, v2, v3
        if is_rgb:
            self.r, self.g, self.b = self.values
        else:
            self.h, self.s, self.v = self.values

    @staticmethod
    def rgb(r: float, g: float, b: float):
        return Color(r, g, b, True)

    @staticmethod
    def hsv(h: float, s: float, v: float):
        return Color(h, s, v, False)

    @property
    def hex(self) -> str:
        values = self.as_rgb().values
        return '#%03x%03x%03x' % (
            int(values[0] * 4095) % 4096,
            int(values[1] * 4095) % 4096,
            int(values[2] * 4095) % 4096
        )

    def as_rgb(self):
        if self.is_rgb:
            return self
        return Color(*colorsys.hsv_to_rgb(self.h, self.s, self.v), True)

    def as_hsv(self):
        if not self.is_rgb:
            return self
        return Color(*colorsys.rgb_to_hsv(self.r, self.g, self.b), False)

    def __add__(self, other):
        return Color(*(i + oi for i, oi in zip(self.values, other.values)), self.is_rgb)

    def __sub__(self, other):
        return Color(*(i - oi for i, oi in zip(self.values, other.values)), self.is_rgb)

    def __mul__(self, other):
        return Color(*(i * other for i in self.values), self.is_rgb)

    def __truediv__(self, other):
        return Color(*(i / other for i in self.values), self.is_rgb)

    def __repr__(self):
        props = ['r', 'g', 'b'] if self.is_rgb else ['h', 's', 'v']
        return f"Color({', '.join(f'{k}: {v}' for k, v in zip(props, self.values))})"


class Animation:
    def __init__(self, initial, final, duration=1.0, step_ms=20, setter=None, on_begin=None, on_complete=None):
        self.current_ms = 0
        self.duration_ms = duration * 1000
        self.step_ms = step_ms
        self.initial = initial
        self.final = final
        self.setter = setter
        self.on_begin = on_begin
        self.on_complete = on_complete
        self._last_update = time.time()

    def reset(self):
        self.current_ms = 0
        self._last_update = time.time()

    def update(self):
        now = time.time()
        self.current_ms += (now - self._last_update) * 1000
        self._last_update = now
        if self.setter:
            current = self.initial + (self.final - self.initial) * self.current_ms / self.duration_ms
            self.setter(current)

    @staticmethod
    def animate(widget, animation, reset=True):
        if reset:
            animation.reset()

        if animation.current_ms > animation.duration_ms:
            if animation.setter:
                animation.setter(animation.final)
            if animation.on_complete:
                animation.on_complete()
            return
        elif not animation.current_ms and animation.on_begin:
            animation.on_begin()

        animation.update()

        widget.after(animation.step_ms, lambda: Animation.animate(widget, animation, reset=False))
