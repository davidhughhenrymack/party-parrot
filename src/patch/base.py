from utils.dmx_utils import dmx_clamp, dmx_clamp_list
from utils.colour import Color

class BaseFixture: 
    def __init__(self, address, name, width):
        self.address = address
        self.name = name
        self.width = width
        self.values = [0 for i in range(width)]

    def set_color(self, color: Color):
        raise NotImplementedError()
    
    def set_dimmer(self, value):
        raise NotImplementedError()
    
    def render(self, dmx):
        for i in range(len(self.values)):
            dmx.set_channel(self.address + i, dmx_clamp(self.values[i]))
        # print(f"{self.name} @ {self.address}: {dmx_clamp_list(self.values)}")