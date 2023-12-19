from random import shuffle
from director.color_scheme import ColorScheme
import math
from utils.math import lerp
from utils.colour import Color, RGB
from patch.patch_bay import patch_bay
from patch.motionstrip import Motionstrip38
from patch.led_par import LedPar
from utils.dmx_utils import dmx_clamp
from utils.math import lerp_list

class Director:
    def __init__(self):
        self.scheme = ColorScheme(
            Color('white'),
            Color('red'),
            Color('blue')
        )

        pars = [i for i in patch_bay if isinstance(i, LedPar)]
        # assign phase in radians based off index
        self.pars_with_phase = [(i, math.pi * 2 / len(pars) * index) for (index, i) in enumerate(pars)]
        
        self.motionstrips = [i for i in patch_bay if isinstance(i, Motionstrip38)]

        self.lower_intensity_buffer = 0

    def step(self, intensity, slow_intensity, time):

        upper_intensity = dmx_clamp(intensity * 2 - 255)
        top_10_percent_intensity = dmx_clamp(intensity - (255 * 0.9) * 10)

        # lower_intensity = dmx_clamp(intensity * 2)
        # only_when_low_intensity = dmx_clamp(255 - abs(50 - (intensity)))
        # self.lower_intensity_buffer = lerp(self.lower_intensity_buffer, only_when_low_intensity, 0.5)
        par_intensity =  dmx_clamp(255 - (abs(slow_intensity -10) / 50 * 255))

        print(slow_intensity, par_intensity)

        for par, phase in self.pars_with_phase:
            par.set_dimmer(par_intensity)

            if (top_10_percent_intensity > 0):
                par.set_strobe(top_10_percent_intensity)
                par.set_dimmer(255)
            else:
                par.set_strobe(0)

            a = math.cos(time/2 + phase) * 0.5 + 0.5
            color = Color()
            color.set_rgb(lerp_list(self.scheme.bg.rgb, self.scheme.bg_contrast.rgb, a))

            par.set_color(color)

        for i in self.motionstrips:
            i.set_dimmer(upper_intensity)
            i.set_color(self.scheme.fg)
            i.set_pan(math.cos(time) * 127 + 128)
    

    def render(self, dmx):
        for i in patch_bay:
            i.render(dmx)

