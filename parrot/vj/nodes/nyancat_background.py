#!/usr/bin/env python3
"""Fullscreen Nyancat-style shader backdrop (after mu6k, Shadertoy 4dXGWH, CC BY-NC-SA 3.0).

Sprite / cat texture removed: starfield, rainbow trail, and audio-driven zoom remain.
"""

from __future__ import annotations

import time

import moderngl as mgl
import numpy as np
from beartype import beartype

from parrot.graph.BaseInterpretationNode import Vibe
from parrot.director.frame import Frame, FrameSignal
from parrot.director.color_scheme import ColorScheme
from parrot.vj.nodes.canvas_effect_base import GenerativeEffectBase

# Match the published shader’s default (2×2 supersampling).
_NYAN_QUALITY = 2


@beartype
class NyancatBackground(GenerativeEffectBase):
    """Procedural starfield + rainbow trail; audio modulates zoom and shimmer (no sprite)."""

    def __init__(self, width: int = 1920, height: int = 1080) -> None:
        super().__init__(width, height)
        self._t0 = time.perf_counter()
        self._spectrum_texture: mgl.Texture | None = None

    def generate(self, vibe: Vibe) -> None:
        """No discrete assets to pick; animation is continuous."""

    def enter(self, context: mgl.Context) -> None:
        super().enter(context)
        self._create_spectrum_texture(context)

    def exit(self) -> None:
        if self._spectrum_texture is not None:
            self._spectrum_texture.release()
            self._spectrum_texture = None
        super().exit()

    def render(
        self, frame: Frame, scheme: ColorScheme, context: mgl.Context
    ) -> mgl.Framebuffer:
        if not self.framebuffer:
            self._setup_gl_resources(context, self.width, self.height)
        self._upload_spectrum(frame)
        assert self.framebuffer is not None
        assert self.shader_program is not None
        assert self.quad_vao is not None
        assert self._spectrum_texture is not None

        self.framebuffer.use()
        context.clear(0.0, 0.0, 0.0)

        self._spectrum_texture.use(0)
        self.shader_program["u_channel1"] = 0

        self._set_effect_uniforms(frame, scheme)
        self.quad_vao.render(mgl.TRIANGLE_STRIP)
        return self.framebuffer

    def _create_spectrum_texture(self, context: mgl.Context) -> None:
        blank = np.zeros((2, 256, 4), dtype=np.uint8)
        blank[:, :, 3] = 255
        tex = context.texture((256, 2), 4, data=blank.tobytes())
        tex.filter = (mgl.LINEAR, mgl.LINEAR)
        tex.repeat_x = False
        tex.repeat_y = False
        self._spectrum_texture = tex

    def _upload_spectrum(self, frame: Frame) -> None:
        if self._spectrum_texture is None:
            return
        g = np.zeros(256, dtype=np.float32)
        ts = getattr(frame, "timeseries", None) or {}
        fh = ts.get(FrameSignal.freq_high.name) if ts else None
        if fh is not None and len(fh) > 0:
            a = np.asarray(fh, dtype=np.float32)
            if len(a) >= 256:
                idx = (np.linspace(0, len(a) - 1, 256)).astype(np.int64)
                g = np.clip(a[idx], 0.0, 1.0)
            else:
                xi = np.linspace(0.0, float(len(a) - 1), 256)
                g = np.clip(np.interp(xi, np.arange(len(a), dtype=np.float32), a), 0.0, 1.0)
        else:
            lo = float(frame[FrameSignal.freq_low])
            hi = float(frame[FrameSignal.freq_high])
            for i in range(256):
                t = i / 255.0
                g[i] = (lo * (1.0 - t) + hi * t) * (0.75 + 0.25 * np.sin(float(i) * 0.15))
            g = np.clip(g, 0.0, 1.0)
        rgba = np.zeros((2, 256, 4), dtype=np.uint8)
        rgba[:, :, 1] = (g * 255.0).astype(np.uint8)
        rgba[:, :, 3] = 255
        self._spectrum_texture.write(rgba.tobytes())

    def _set_effect_uniforms(self, frame: Frame, scheme: ColorScheme) -> None:
        t = float(time.perf_counter() - self._t0)
        self._safe_set_uniform("iTime", t)
        self._safe_set_uniform("iResolution", (float(self.width), float(self.height)))

    def _get_fragment_shader(self) -> str:
        q = _NYAN_QUALITY
        return f"""
        #version 330 core
        #define NYAN_QUALITY {q}

        in vec2 uv;
        out vec3 fragColor;

        uniform float iTime;
        uniform vec2 iResolution;
        uniform sampler2D u_channel1;

        float hash(float x)
        {{
            return fract(sin(x*.0127863)*17143.321);
        }}

        float hash(vec2 x)
        {{
            return fract(sin(dot(x,vec2(1.4,52.14)))*17143.321);
        }}

        float hashmix(float x0, float x1, float interp)
        {{
            x0 = hash(x0);
            x1 = hash(x1);
            return mix(x0,x1,interp);
        }}

        float hashmix(vec2 p0, vec2 p1, vec2 interp)
        {{
            float v0 = hashmix(p0[0]+p0[1]*128.0,p1[0]+p1[1]*128.0,interp[0]);
            float v1 = hashmix(p0[0]+p1[1]*128.0,p1[0]+p1[1]*128.0,interp[0]);
            return mix(v0,v1,interp[1]);
        }}

        float hashmix(vec3 p0, vec3 p1, vec3 interp)
        {{
            float v0 = hashmix(p0.xy+vec2(p0.z*43.0,0.0),p1.xy+vec2(p0.z*43.0,0.0),interp.xy);
            float v1 = hashmix(p0.xy+vec2(p1.z*43.0,0.0),p1.xy+vec2(p1.z*43.0,0.0),interp.xy);
            return mix(v0,v1,interp[2]);
        }}

        float hashmix(vec4 p0, vec4 p1, vec4 interp)
        {{
            float v0 = hashmix(p0.xyz+vec3(p0.w*17.0,0.0,0.0),p1.xyz+vec3(p0.w*17.0,0.0,0.0),interp.xyz);
            float v1 = hashmix(p0.xyz+vec3(p1.w*17.0,0.0,0.0),p1.xyz+vec3(p1.w*17.0,0.0,0.0),interp.xyz);
            return mix(v0,v1,interp[3]);
        }}

        float noise(float p)
        {{
            float pm = mod(p,1.0);
            float pd = p-pm;
            return hashmix(pd,pd+1.0,pm);
        }}

        float noise(vec2 p)
        {{
            vec2 pm = mod(p,1.0);
            vec2 pd = p-pm;
            return hashmix(pd,(pd+vec2(1.0,1.0)), pm);
        }}

        float noise(vec3 p)
        {{
            vec3 pm = mod(p,1.0);
            vec3 pd = p-pm;
            return hashmix(pd,(pd+vec3(1.0,1.0,1.0)), pm);
        }}

        float noise(vec4 p)
        {{
            vec4 pm = mod(p,1.0);
            vec4 pd = p-pm;
            return hashmix(pd,(pd+vec4(1.0,1.0,1.0,1.0)), pm);
        }}

        vec3 background(vec2 p)
        {{
            // Dark navy field (was 13,66,121 — kept deliberately dim for contrast with stars)
            vec3 color = vec3(3,14,32)/255.0;

            vec2 visuv = p*0.5;
            vec2 visuvm = mod(visuv,vec2(0.05,0.05));
            visuv-=visuvm;
            float vis = texture(u_channel1,vec2((visuv.x+1.0)*.5,0.25)).g*2.0-visuv.y;

            if (vis>1.0&&visuvm.x<0.04&&visuvm.y<0.04)
                color.xyz *=0.68;

            vec2 p2;
            float stars;
            for (int i=0; i<5; i++)
            {{
                float s = float(i)*0.2+1.0;
                p2=p*s+vec2(iTime/s,s*16.0)-mod(p*s+vec2(iTime/s,s*16.0),vec2(0.05));
                stars=noise(p2*16.0);
                // Sparse small bright stars (slightly rarer than original 0.98)
                if (stars>0.988) color=vec3(1.0,1.0,1.0);
            }}

            vec2 visuv2 = p*0.25+vec2(iTime*0.1,0);
            vec2 visuvm2 = mod(visuv2,vec2(0.05,0.05));
            visuv2-=visuvm2;

            float vis2p = hash(visuv2);
            float vis2 = texture(u_channel1,vec2(vis2p,0.25)).g;

            vis2 = pow(vis2,20.0)*261.0;
            vis2 *= vis2p;

            if (vis2>1.0) vis2=1.0;

            if (vis2>0.2&&visuvm2.x<0.09&&visuvm2.y<0.09)
                color+=vec3(vis2,vis2,vis2)*0.28;

            return color;
        }}

        vec4 rainbow(vec2 p)
        {{
            p.x-=mod(p.x,0.05);
            float s = sin(p.x*(8.0)+iTime*8.0)*0.09;
            s-=mod(s,0.05);
            p.y+=s;

            vec4 c;

            if (p.x>0.0) c=vec4(0,0,0,0);
            else if (0.0/6.0<p.y&&p.y<1.0/6.0) c= vec4(255,43,14,255)/255.0;
            else if (1.0/6.0<p.y&&p.y<2.0/6.0) c= vec4(255,168,6,255)/255.0;
            else if (2.0/6.0<p.y&&p.y<3.0/6.0) c= vec4(255,244,0,255)/255.0;
            else if (3.0/6.0<p.y&&p.y<4.0/6.0) c= vec4(51,234,5,255)/255.0;
            else if (4.0/6.0<p.y&&p.y<5.0/6.0) c= vec4(8,163,255,255)/255.0;
            else if (5.0/6.0<p.y&&p.y<6.0/6.0) c= vec4(122,85,255,255)/255.0;
            else
                c=vec4(0,0,0,0);
            return c;
        }}

        vec4 scene(vec2 uv)
        {{
            vec3 c2 = background(uv);
            vec4 c3 = rainbow(vec2(uv.x+0.4,0.05-uv.y*2.0+.5));
            return mix(vec4(c2,1.0),c3,c3.a);
        }}

        void main()
        {{
            float vol = .0;
            for (int i = 0; i < 256; i++) {{
                float x = (float(i)+0.5)/256.0;
                vol += texture(u_channel1, vec2(x, 0.25)).g;
            }}
            vol*=1.0/256.0;
            vol = pow(vol,16.0)*256.0;

            vec2 fragCoord = gl_FragCoord.xy;
            vec2 ouv = fragCoord.xy / iResolution.xy-0.5;
            ouv.x *= iResolution.x/iResolution.y;
            vec2 uv = ouv;
            float t = iTime-length(uv)*0.5;

            uv.x+=sin(t*0.4)*0.05;
            uv.y+=cos(t)*0.05;

            float angle = (cos(t*0.461)+cos(t*0.71)+cos(t*0.342)+cos(t*0.512))*0.2;
            angle+=sin(t*16.0)*vol*0.1;
            float zoom = (cos(t*0.364)+cos(t*0.686)+cos(t*0.286)+cos(t*0.496))*0.2;
            uv*=pow(2.0,zoom+1.0-vol*4.0);
            uv=uv*mat2(cos(angle),-sin(angle),sin(angle),cos(angle));

            vec4 color = vec4(0);

            uv.y+=vol;

            for(int x = 0; x < NYAN_QUALITY; x++)
            for(int y = 0; y < NYAN_QUALITY; y++)
            {{
                float xx = float(x)*2.0/float(NYAN_QUALITY)/iResolution.y;
                float yy = float(y)*2.0/float(NYAN_QUALITY)/iResolution.y;
                float n = hash(color.xy+ouv+vec2(float(x),float(y)));
                float s = 1.0-pow(n,10.0)*vol*17.0;
                color += scene((uv+vec2(xx,yy))*s)/float(NYAN_QUALITY*NYAN_QUALITY)*(1.0+vol);
            }}

            color-=vec4(length(uv)*0.065);
            color.xyz+=vec3(hash(color.xy+ouv))*0.012;
            fragColor = color.rgb;
        }}
        """
