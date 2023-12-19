


import math


def clamp(n, min, max):
    if n < min:
        return min
    elif n > max:
        return max
    else:
        return n
    
def dmx_clamp(n):
    if math.isnan(n):
        return 0
    return int(clamp(n, 0, 255))

def dmx_clamp_list(items):
    return [int(clamp(item, 0, 255)) for item in items]
