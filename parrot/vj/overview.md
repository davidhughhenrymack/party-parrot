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
    fbo = canvas.render(frame, scheme, gl_fbo_context)
    blit_to_screen(fbo)


These canvas nodes have render methods that take 1 or more (some only take 1) child inputs (fbos) and transform those using shaders, then return a new fbo.

VideoPlayer on generate() randomly picks a folder [video group] and then will play the videos from it. when one video ends it plays the next one, and keeps cycling through them.

For the virtual lighting, it could be like this:

lighting = pipeline(
    children = FixtureGroup([MovingHead() for i in range(10)]),
    operations = [
        MoveFan,
        DimmerChase,
        ColorFg
    ]
)

where each operation like DimmerChase will iterate over the fixtures in the group and call e.g. set_dimmer() or set_color() on them to update their state (MovingHead is a lightweight class that just has set-get methods for its key properties like tilt, pan, dimmer etc)

Where MoveFan etc are BaseInterpreterNodes mimicing the existing "old-style" interpreters elsewhere in the code.

then in vj_director step():
    updated_fixture_states = lighting.render(frame, scheme, None)
    for fixst, rdr in zip(updated_fixture_states, fixture_renderers):
        rdr(fixst)


where fixture_renderers is a list of classes that have their 3d location set and know how to make a volumetric haze-beam rendering based off the properties of a moving head (e.g. color, dimmer, strobe).

when the overall director wants to call shift interpreter, it will call into "recursive_generate" to update the vj interpretations. We need to have a way to provide a percentage that controls how much of the vj node tree will have generate called on it so we can do partial shifts as well as total shifts.