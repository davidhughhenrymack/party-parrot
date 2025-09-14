# VJ

VJ is a parallel visual system that runs seperate from the GUI window. It uses moderngl and other libraries to use shaders and gl primatives to make a cool "Video Jockey" style accompanient to the music.

It primarily has two parts:
1. A fullscreen canvas that plays videos and layers affects and text
2. A 3d space with virtual lighting fixtures (E.g. moving heads) that render in 3d space to feel like there are more lights in the room.

All of these respond to Frame, ColorScheme and Mode to provide effects complementary to the DMX lighting system in party parrot.

The fullscreen canvas has a major component that will open up videos in `media/videos/[function_group]/[video_group]/x.mp4` and play them on loop where "function_group" could be "bg" (for background), and video group are names to group together visually similar videos, which can be swapped between when one video ends

The BaseInterpretationNode is the underlying method of coordinating the canvas affects, and the virtual lighting fixtures. For example, the canvas could be rendered like such:

canvas = LayerCompose(
    LightningEffectOnLoud(),
    TextOverlay(text="Dead Sexy")
    BrightnessFromBass(VideoPlayer(fn_group="bg"))
    Black()
)

In vj_director.py step(frame, scheme):
    canvas.render(frame, scheme, gl_fbo_context)


For the virtual lighting, it could be like this:

lighting = pipeline(
    children = FixtureGroup([MovingHead() for i in range(10)]),
    operations = [
        MoveFan,
        DimmerChase,
        ColorFg
    ]
)

where each operation like DimmerChase will iterate over the fixtures in the group and call e.g. set_dimmer() or set_color() on them to update their state

(where MoveFan etc are BaseInterpreterNodes like the interpreters elsewhere in the code)

then in vj_director step():
    updated_fixture_states = lighting.render(frame, scheme, None)
    for fixst, rdr in zip(updated_fixture_states, fixture_renderers):
        rdr(fixst)

