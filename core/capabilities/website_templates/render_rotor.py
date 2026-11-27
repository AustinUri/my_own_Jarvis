"""Render the factory's original, unbranded brake-disc illustration offline."""
from pathlib import Path

import numpy as np
from PIL import Image


def render(destination):
    width, height = 1200, 1000
    py, px = np.indices((height, width), dtype=np.float32)
    sx = (px - width * .50) / (width * .47)
    sy = (py - height * .50) / (width * .47)
    tilt, twist = np.radians(46), np.radians(35)
    ct, st = np.cos(tilt), np.sin(tilt)
    x = sx * np.cos(twist) - sy * np.sin(twist)
    screen_y = sx * np.sin(twist) + sy * np.cos(twist)
    depth = np.full_like(px, -100.)
    rng = np.random.default_rng(8309)
    grain = rng.normal(0, 1, sx.shape)
    glow = np.exp(-((sx + .33) ** 2 + (sy + .32) ** 2) / 1.1)
    shadow = np.exp(-(x ** 2 / .73 + ((screen_y - .14) / .62) ** 2) * 1.7)
    background = 31 + 36 * glow - 31 * shadow + grain * .8
    rgb = np.stack([background * .98, background * .99, background], axis=-1)

    def paint(mask, z, value, tint=(1., 1., 1.)):
        visible = mask & (z >= depth)
        if not visible.any():
            return
        depth[visible] = z if np.isscalar(z) else z[visible]
        v = value if np.isscalar(value) else value[visible]
        for i, color in enumerate(tint):
            rgb[..., i][visible] = v * color

    def circle_face(z, inner, outer, material, bores=()):
        y = (screen_y - st * z) / ct
        radius = np.hypot(x, y)
        theta = np.arctan2(y, x)
        mask = (radius >= inner) & (radius <= outer)
        direction = theta + .17 * radius
        reflection = (.5 + .5 * np.cos(2 * direction + 1.0)) ** 5.1
        softbox = (.5 + .5 * np.cos(2 * direction - 1.15)) ** 7
        machining = (1.6 * np.sin(1700 * radius + .3 * np.sin(4 * theta)) +
                     1.9 * np.sin(580 * radius) + 1.4 * np.sin(943 * radius))
        if material == "disc":
            value = 70 + reflection * 145 + 39 * softbox + 21 * (x + 1) + machining + grain * 2
            value *= 1 - .38 * np.exp(-((radius - inner) / .021) ** 2)
            # Recessed circular cross-drilling includes a bevel catching the upper light.
            for pattern_radius, phase in ((.72, .04), (.785, .12), (.85, .195), (.915, .255)):
                nearest = (theta - phase + np.pi / 12) % (np.pi / 6) - np.pi / 12
                dx = radius * np.cos(nearest) - pattern_radius
                dy = radius * np.sin(nearest)
                distance = np.hypot(dx, dy)
                bevel = (distance < .016) & (distance >= .012)
                value = np.where(bevel, 102 + 80 * np.cos(np.arctan2(dy, dx) + theta + .8), value)
                value = np.where(distance < .012, 17 + 10 * distance / .012, value)
        elif material == "hub":
            value = 63 + 66 * reflection + 21 * softbox + 17 * (x + 1) + machining + grain * 2
        else:
            value = 33 + 22 * reflection + 7 * softbox + machining * .25 + grain * .7
        value = np.where((radius > outer - .003) | (radius < inner + .003), value * 1.3 + 8, value)
        for bx, by, br in bores:
            distance = np.hypot(x - bx, y - by)
            mask &= distance > br
            bevel = (distance > br) & (distance < br + .012)
            value = np.where(bevel, 100 + 65 * np.cos(np.arctan2(y-by, x-bx) + 1.7), value)
        paint(mask, z, value, (1.019, 1., .978))

    def wall(radius, bottom, top, brightness, *, centre=(0., 0.), inner=False, fins=False):
        bx, by = centre
        dx = x - bx
        radial_y = np.sqrt(np.maximum(0, radius * radius - dx * dx)) * (1 if inner else -1)
        y = by + radial_y
        z = (screen_y - ct * y) / st
        mask = (np.abs(dx) <= radius) & (z >= bottom) & (z <= top)
        theta = np.arctan2(radial_y, dx)
        light = (.5 + .5 * np.cos(theta + 2.45)) ** 4
        value = brightness * (.46 + .95 * light) + 5 * np.sin(1260 * z) + grain * 1.7
        if fins:
            mask &= (np.cos(55 * theta + 4 * z) > .14)
        paint(mask, z, value, (1.025, 1., .965))

    circle_face(-.18, .34, .994, "dark")
    wall(.994, -.18, -.122, 87)
    circle_face(-.122, .34, .994, "dark")
    wall(.988, -.121, -.047, 66, fins=True)
    wall(.93, -.122, -.046, 25)
    wall(1., -.047, .008, 133)
    circle_face(.008, .518, 1., "disc")
    circle_face(.01, .408, .52, "dark")
    wall(.414, .009, .122, 74)
    circle_face(.122, .18, .414, "hub",
                [(np.cos(a) * .292, np.sin(a) * .292, .044) for a in np.linspace(.28, .28+2*np.pi, 5, endpoint=False)])
    wall(.180, -.165, .122, 43, inner=True)
    wall(.408, .122, .137, 113)
    circle_face(.137, .394, .408, "hub")
    for a in np.linspace(.28, .28+2*np.pi, 5, endpoint=False):
        wall(.044, -.06, .122, 45, centre=(np.cos(a) * .292, np.sin(a) * .292), inner=True)
    image = Image.fromarray(np.clip(rgb, 0, 255).astype(np.uint8), "RGB")
    image.save(destination, "WEBP", quality=86, method=6)


if __name__ == "__main__":
    render(Path(__file__).with_name("brake-rotor.webp"))
