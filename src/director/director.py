from random import shuffle
from director.color_scheme import ColorScheme
import math
from patch.chauvet import ChauvetSpot160
from utils.math import lerp
from utils.colour import Color, RGB
from patch.patch_bay import patch_bay
from patch.motionstrip import Motionstrip38
from patch.led_par import LedPar
from utils.dmx_utils import dmx_clamp
from utils.math import lerp_list

class Frame:
    def __init__(self, intensity, time, vocals, other, drums, bass):
        self.intensity = intensity
        self.time = time
        self.vocals = vocals
        self.other = other
        self.drums = drums
        self.bass = bass

    def __str__(self):
        return f"Frame(intensity={int(self.intensity*100)}, vocals={int(self.vocals* 100)}, other={int(self.other* 100)}, drums={int(self.drums* 100)}, bass={int(self.bass* 100)})"

class Director:
    def __init__(self):
        self.scheme = ColorScheme(
            Color('green'),
            Color('blue'),
            Color('blue')
        )

        pars = [i for i in patch_bay if isinstance(i, LedPar)]
        # assign phase in radians based off index
        self.pars_with_phase = [(i, math.pi * 2 / len(pars) * index) for (index, i) in enumerate(pars)]
        
        self.motionstrips = [i for i in patch_bay if isinstance(i, Motionstrip38)]
        self.movers = [i for i in patch_bay if isinstance(i, ChauvetSpot160)]

        self.lower_intensity_buffer = 0

    def step(self, frame: Frame):

        time = frame.time

        # print(frame)
        par_intensity =  dmx_clamp(frame.other * 255)

        for par, phase in self.pars_with_phase:
            par.set_dimmer(par_intensity)

            # if (top_10_percent_intensity > 0):
            #     par.set_strobe(top_10_percent_intensity)
            #     par.set_dimmer(255)
            # else:
            #     par.set_strobe(0)

            a = math.cos(time/2 + phase) * 0.5 + 0.5
            color = Color()
            color.set_rgb(lerp_list(self.scheme.bg.rgb, self.scheme.bg_contrast.rgb, a))

            par.set_color(color)

        for i in self.motionstrips:
            i.set_dimmer((frame.bass) * 255)
            i.set_color(self.scheme.fg) 
            i.set_pan(math.cos(time) * 127 + 128)

        for i in self.movers:
            i.set_dimmer(frame.drums * 255 * 2 - 255)
            i.set_color(self.scheme.fg)
            i.set_pan(math.cos(time) * 127 + 128)
            i.set_tilt(math.sin(time) * 127 + 128)
    

    def render(self, dmx):
        for i in patch_bay:
            i.render(dmx)

        dmx.submit()

