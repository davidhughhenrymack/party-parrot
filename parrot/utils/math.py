import math


def clamp(n, min, max):
    if n < min:
        return min
    elif n > max:
        return max
    else:
        return n


def distance(x0, x1=None, y0=None, y1=None):
    """Calculate the Euclidean distance between two points.

    Can be called in two ways:
    - distance((x0, y0), (x1, y1)) with two tuples
    - distance(x0, x1, y0, y1) with four coordinates
    """
    if isinstance(x0, tuple) and isinstance(x1, tuple):
        # Called as distance((x0, y0), (x1, y1))
        p1, p2 = x0, x1
        dx = p2[0] - p1[0]
        dy = p2[1] - p1[1]
    else:
        # Called as distance(x0, x1, y0, y1)
        dx = x1 - x0
        dy = y1 - y0

    return math.sqrt(dx * dx + dy * dy)
