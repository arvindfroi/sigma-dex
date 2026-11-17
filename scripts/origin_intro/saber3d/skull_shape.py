"""Shared outline of the gold stern skull (pirate skull): used by textures.py (drawing) and model (extruded plate).
Units: x right, y up, about 1.2 tall."""
import math
def outline(n_arc=40):
    pts = []
    a0, a1 = math.radians(-54.5), math.radians(234.5)
    for i in range(n_arc + 1):
        a = a0 + (a1 - a0) * i / n_arc
        pts.append((0.5 * math.cos(a), 0.12 + 0.5 * math.sin(a)))
    def corner(cx, cy, a_from, a_to, r=0.1, n=5):
        return [(cx + r * math.cos(math.radians(a_from + (a_to - a_from) * k / n)), cy + r * math.sin(math.radians(a_from + (a_to - a_from) * k / n))) for k in range(n + 1)]
    pts += [(-0.29, -0.36)] + corner(-0.19, -0.46, 180, 270) + corner(0.19, -0.46, 270, 360) + [(0.29, -0.36)]
    return pts
SOCKETS = [(-0.19, 0.04, 0.155, 0.17), (0.19, 0.04, 0.155, 0.17)]
NOSE = [(0.0, -0.1), (-0.075, -0.25), (0.075, -0.25)]
TEETH_Y = -0.39
TEETH_X = [-0.18, -0.09, 0.0, 0.09, 0.18]
