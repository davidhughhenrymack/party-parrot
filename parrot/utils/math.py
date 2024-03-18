def clamp(n, min, max):
    if n < min:
        return min
    elif n > max:
        return max
    else:
        return n
