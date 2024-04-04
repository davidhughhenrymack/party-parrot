import math


def clamp(n, min, max):
    if n < min:
        return min
    elif n > max:
        return max
    else:
        return n


def distance(x0, x1, y0, y1):
    dx = x1 - x0
    dy = y1 - y0
    return math.sqrt(dx * dx + dy * dy)
