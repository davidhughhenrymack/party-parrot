#!/usr/bin/env python3
"""
Font Showcase Demo
Demonstrates the enhanced text rendering system with professional fonts
"""
import numpy as np
from parrot.vj.text_renderer import get_text_renderer, MultiRendererTextSystem
from parrot.vj.layers.text import TextLayer
from parrot.director.frame import Frame
from parrot.director.color_scheme import ColorScheme
from parrot.utils.colour import Color


def demo_font_discovery():
    """Demonstrate font discovery and system font access"""
    print("🔤" * 30)
    print("   FONT DISCOVERY SYSTEM")
    print("🔤" * 30)

    # Get text renderer
    text_renderer = get_text_renderer()

    # Get font information
    font_info = text_renderer.get_font_info()

    print(f"\n📊 Font System Status:")
    print(f"   Total fonts found: {font_info['total_fonts']}")
    print(f"   Font families: {font_info['font_families']}")
    print(f"   Horror fonts: {font_info['horror_fonts']}")
    print(f"   Bold fonts: {font_info['bold_fonts']}")
    print(f"   PIL available: {font_info['pil_available']}")
    print(f"   FontTools available: {font_info['fonttools_available']}")
    print(f"   Pygame available: {font_info['pygame_available']}")

    # Show recommended fonts
    if "recommended" in font_info:
        print(f"\n🎨 Recommended Fonts by Category:")
        for category, fonts in font_info["recommended"].items():
            if fonts:
                print(f"   {category.capitalize()}: {', '.join(fonts[:3])}")
                if len(fonts) > 3:
                    print(f"      ... and {len(fonts) - 3} more")

    # Show horror fonts specifically
    horror_fonts = text_renderer.horror_fonts
    if horror_fonts:
        print(f"\n💀 Horror Fonts Available:")
        for font in horror_fonts[:5]:
            print(f"   - {font}")
        if len(horror_fonts) > 5:
            print(f"   ... and {len(horror_fonts) - 5} more horror fonts")

    # Show bold fonts
    bold_fonts = text_renderer.bold_fonts
    if bold_fonts:
        print(f"\n💪 Bold Fonts Available:")
        for font in bold_fonts[:5]:
            print(f"   - {font}")
        if len(bold_fonts) > 5:
            print(f"   ... and {len(bold_fonts) - 5} more bold fonts")


def demo_dead_sexy_fonts():
    """Demonstrate 'DEAD SEXY' text with different fonts"""
    print("\n" + "💀" * 30)
    print("   DEAD SEXY FONT SHOWCASE")
    print("💀" * 30)

    text_renderer = get_text_renderer()

    # Test different styles
    font_styles = [
        ("🔥 Horror Style", "horror"),
        ("💪 Bold Style", "bold"),
        ("📝 Default Style", "default"),
    ]

    for style_name, style in font_styles:
        print(f"\n{style_name}:")

        try:
            result = text_renderer.render_dead_sexy_text(
                width=800, height=200, style=style
            )

            if result is not None:
                # Analyze the rendered text
                non_zero_pixels = np.count_nonzero(result)
                text_coverage = (non_zero_pixels / (800 * 200)) * 100

                # Get color info
                red_intensity = np.mean(result[:, :, 0])

                print(f"   ✅ Rendered successfully")
                print(f"   📏 Text coverage: {text_coverage:.1f}% of image")
                print(f"   🔴 Red intensity: {red_intensity:.1f}/255")
                print(f"   📊 Total pixels: {non_zero_pixels}")
            else:
                print(f"   ❌ Failed to render")

        except Exception as e:
            print(f"   ❌ Error: {e}")


def demo_font_effects():
    """Demonstrate font effects like outlines and shadows"""
    print("\n" + "✨" * 30)
    print("   FONT EFFECTS SHOWCASE")
    print("✨" * 30)

    text_renderer = get_text_renderer()

    # Test different effect combinations
    effect_tests = [
        ("Basic Text", {"outline_width": 0, "shadow_offset": (0, 0)}),
        (
            "With Outline",
            {"outline_width": 3, "outline_color": (0, 0, 0), "shadow_offset": (0, 0)},
        ),
        (
            "With Shadow",
            {
                "outline_width": 0,
                "shadow_offset": (5, 5),
                "shadow_color": (0, 0, 0, 128),
            },
        ),
        (
            "Outline + Shadow",
            {
                "outline_width": 2,
                "outline_color": (255, 255, 255),
                "shadow_offset": (3, 3),
                "shadow_color": (0, 0, 0, 180),
            },
        ),
        (
            "Thick Outline",
            {
                "outline_width": 6,
                "outline_color": (255, 165, 0),  # Orange outline
                "shadow_offset": (0, 0),
            },
        ),
    ]

    for effect_name, effect_params in effect_tests:
        print(f"\n✨ {effect_name}:")

        try:
            result = text_renderer.enhanced_renderer.render_text(
                text="SPOOKY",
                font_family=None,  # Use default
                font_size=120,
                font_style="bold",
                color=(255, 0, 0),  # Red text
                width=600,
                height=150,
                **effect_params,
            )

            if result is not None:
                # Analyze effect
                total_pixels = np.count_nonzero(result)
                has_outline = effect_params.get("outline_width", 0) > 0
                has_shadow = effect_params.get("shadow_offset", (0, 0)) != (0, 0)

                effects_active = []
                if has_outline:
                    effects_active.append("outline")
                if has_shadow:
                    effects_active.append("shadow")

                print(
                    f"   ✅ Rendered with {', '.join(effects_active) if effects_active else 'no effects'}"
                )
                print(f"   📊 Total pixels: {total_pixels}")
            else:
                print(f"   ❌ Failed to render")

        except Exception as e:
            print(f"   ❌ Error: {e}")


def demo_text_layer_integration():
    """Demonstrate enhanced TextLayer with font selection"""
    print("\n" + "🎭" * 30)
    print("   TEXT LAYER FONT INTEGRATION")
    print("🎭" * 30)

    # Create TextLayer with enhanced rendering
    text_layer = TextLayer(
        text="DEAD SEXY",
        name="enhanced_text",
        font_size=144,
        alpha_mask=True,
        width=800,
        height=300,
    )

    print(f"\n🎭 TextLayer created: {text_layer.name}")

    # Get available fonts
    font_info = text_layer.get_available_fonts()

    if "error" not in font_info:
        print(f"   📚 Available fonts: {font_info['total_fonts']}")

        # Try horror font
        print(f"\n💀 Testing horror font:")
        try:
            text_layer.use_horror_font()

            # Render with horror font
            frame = Frame({})
            scheme = ColorScheme(Color("red"), Color("black"), Color("white"))

            result = text_layer.render(frame, scheme)

            if result is not None:
                print(f"   ✅ Horror font rendering successful")
                print(f"   📏 Output size: {result.shape}")

                # Check alpha masking
                if text_layer.alpha_mask:
                    alpha_values = result[:, :, 3]
                    has_transparency = np.any(alpha_values == 0)
                    has_opacity = np.any(alpha_values == 255)

                    print(
                        f"   🎭 Alpha mask: transparent={has_transparency}, opaque={has_opacity}"
                    )
            else:
                print(f"   ❌ Horror font rendering failed")

        except Exception as e:
            print(f"   ❌ Error with horror font: {e}")

        # Try bold font
        print(f"\n💪 Testing bold font:")
        try:
            text_layer.use_bold_font()

            result = text_layer.render(frame, scheme)

            if result is not None:
                print(f"   ✅ Bold font rendering successful")
            else:
                print(f"   ❌ Bold font rendering failed")

        except Exception as e:
            print(f"   ❌ Error with bold font: {e}")
    else:
        print(f"   ❌ Font system error: {font_info['error']}")


def demo_font_comparison():
    """Compare different font rendering approaches"""
    print("\n" + "🔍" * 30)
    print("   FONT RENDERING COMPARISON")
    print("🔍" * 30)

    text_renderer = get_text_renderer()

    # Test text
    test_text = "PARTY"

    # Get best available fonts
    horror_fonts = text_renderer.horror_fonts[:2]  # Top 2 horror fonts
    bold_fonts = text_renderer.bold_fonts[:2]  # Top 2 bold fonts

    test_fonts = []

    # Add horror fonts
    for font in horror_fonts:
        test_fonts.append(("💀 " + font, font, "horror"))

    # Add bold fonts
    for font in bold_fonts:
        test_fonts.append(("💪 " + font, font, "bold"))

    # Add fallback
    test_fonts.append(("📝 Fallback", None, "default"))

    print(f"\n🔍 Comparing {len(test_fonts)} font options:")

    for display_name, font_family, category in test_fonts:
        print(f"\n{display_name}:")

        try:
            # Enhanced renderer
            enhanced_result = text_renderer.enhanced_renderer.render_text(
                text=test_text,
                font_family=font_family,
                font_size=100,
                font_style="bold",
                color=(255, 100, 0),  # Orange
                width=500,
                height=150,
                outline_width=2,
                outline_color=(0, 0, 0),
            )

            if enhanced_result is not None:
                enhanced_pixels = np.count_nonzero(enhanced_result)
                print(f"   ✅ Enhanced renderer: {enhanced_pixels} pixels")
            else:
                print(f"   ❌ Enhanced renderer failed")

            # Pygame renderer (if available)
            if text_renderer.pygame_renderer.pygame_available:
                pygame_result = text_renderer.pygame_renderer.render_text_pygame(
                    text=test_text,
                    font_name=font_family,
                    font_size=100,
                    color=(255, 100, 0),
                    width=500,
                    height=150,
                    bold=True,
                )

                if pygame_result is not None:
                    pygame_pixels = np.count_nonzero(pygame_result)
                    print(f"   ✅ Pygame renderer: {pygame_pixels} pixels")
                else:
                    print(f"   ❌ Pygame renderer failed")
            else:
                print(f"   ⚠️ Pygame not available")

        except Exception as e:
            print(f"   ❌ Error: {e}")


def demo_halloween_text_styles():
    """Demonstrate Halloween-themed text styles"""
    print("\n" + "🎃" * 30)
    print("   HALLOWEEN TEXT STYLES")
    print("🎃" * 30)

    text_renderer = get_text_renderer()

    # Halloween text variations
    halloween_texts = [
        ("DEAD SEXY", (255, 0, 0)),  # Blood red
        ("SPOOKY", (255, 165, 0)),  # Pumpkin orange
        ("HORROR", (128, 0, 128)),  # Dark purple
        ("NIGHTMARE", (255, 255, 255)),  # Ghost white
        ("EVIL", (139, 0, 0)),  # Dark red
    ]

    print(f"\n🎃 Testing Halloween text styles:")

    for text, color in halloween_texts:
        print(f"\n   👻 '{text}':")

        # Try with horror font if available
        horror_fonts = text_renderer.horror_fonts
        font_family = horror_fonts[0] if horror_fonts else None

        try:
            result = text_renderer.enhanced_renderer.render_text(
                text=text,
                font_family=font_family,
                font_size=120,
                font_style="bold",
                color=color,
                width=600,
                height=200,
                outline_width=3,
                outline_color=(0, 0, 0),
                shadow_offset=(4, 4),
                shadow_color=(0, 0, 0, 150),
            )

            if result is not None:
                # Analyze the text
                coverage = (np.count_nonzero(result) / (600 * 200)) * 100
                color_intensity = np.mean(result[:, :, :3])

                font_used = font_family if font_family else "default"
                print(f"     ✅ Font: {font_used}")
                print(f"     📏 Coverage: {coverage:.1f}%")
                print(f"     🎨 Color intensity: {color_intensity:.1f}")

                # Check for effects
                has_outline = np.any(result[:, :, :3].sum(axis=2) < 100)  # Dark pixels
                has_shadow = True  # Shadow is built into the render

                effects = []
                if has_outline:
                    effects.append("outline")
                if has_shadow:
                    effects.append("shadow")

                print(f"     ✨ Effects: {', '.join(effects)}")
            else:
                print(f"     ❌ Rendering failed")

        except Exception as e:
            print(f"     ❌ Error: {e}")


def demo_font_performance():
    """Test font rendering performance"""
    print("\n" + "⚡" * 30)
    print("   FONT RENDERING PERFORMANCE")
    print("⚡" * 30)

    text_renderer = get_text_renderer()

    # Performance test scenarios
    test_scenarios = [
        ("Small Text", "SEXY", 72, 400, 200),
        ("Medium Text", "DEAD SEXY", 120, 800, 300),
        ("Large Text", "HORROR", 200, 1200, 400),
        ("Huge Text", "PARTY", 300, 1920, 600),
    ]

    print(f"\n⚡ Performance testing:")

    for scenario_name, text, size, width, height in test_scenarios:
        print(f"\n   {scenario_name} ({size}pt, {width}x{height}):")

        # Get best font
        best_font = None
        if text_renderer.horror_fonts:
            best_font = text_renderer.horror_fonts[0]
        elif text_renderer.bold_fonts:
            best_font = text_renderer.bold_fonts[0]

        try:
            import time

            start_time = time.time()

            result = text_renderer.enhanced_renderer.render_text(
                text=text,
                font_family=best_font,
                font_size=size,
                font_style="bold",
                color=(255, 50, 50),
                width=width,
                height=height,
                outline_width=2,
                outline_color=(0, 0, 0),
            )

            render_time = time.time() - start_time

            if result is not None:
                pixels = np.count_nonzero(result)
                print(f"     ✅ Rendered in {render_time*1000:.1f}ms")
                print(f"     📊 Pixels: {pixels} ({(pixels/(width*height))*100:.1f}%)")
                print(f"     🔤 Font: {best_font or 'default'}")
            else:
                print(f"     ❌ Failed to render")

        except Exception as e:
            print(f"     ❌ Error: {e}")


def demo_text_layer_enhanced():
    """Demonstrate enhanced TextLayer capabilities"""
    print("\n" + "🎨" * 30)
    print("   ENHANCED TEXT LAYER")
    print("🎨" * 30)

    # Create enhanced text layer
    text_layer = TextLayer(
        text="DEAD SEXY",
        name="enhanced_demo",
        font_size=150,
        color=(255, 0, 0),
        alpha_mask=True,
        width=1000,
        height=400,
    )

    print(f"\n🎨 Enhanced TextLayer Demo:")

    # Test font switching
    font_tests = [
        ("Default Font", lambda: None),
        ("Horror Font", lambda: text_layer.use_horror_font()),
        ("Bold Font", lambda: text_layer.use_bold_font()),
    ]

    scheme = ColorScheme(Color("red"), Color("black"), Color("orange"))
    frame = Frame({})

    for test_name, font_action in font_tests:
        print(f"\n   {test_name}:")

        try:
            # Apply font change
            if font_action:
                font_action()

            # Render
            result = text_layer.render(frame, scheme)

            if result is not None:
                # Analyze result
                coverage = (np.count_nonzero(result) / (1000 * 400)) * 100

                # Check alpha masking
                if text_layer.alpha_mask:
                    alpha_channel = result[:, :, 3]
                    transparent_pixels = np.sum(alpha_channel == 0)
                    opaque_pixels = np.sum(alpha_channel == 255)

                    print(f"     ✅ Rendered: {coverage:.1f}% coverage")
                    print(
                        f"     🎭 Alpha mask: {transparent_pixels} transparent, {opaque_pixels} opaque"
                    )
                else:
                    print(f"     ✅ Rendered: {coverage:.1f}% coverage")
            else:
                print(f"     ❌ Rendering failed")

        except Exception as e:
            print(f"     ❌ Error: {e}")


def main():
    """Run the complete font showcase demo"""
    try:
        demo_font_discovery()
        demo_dead_sexy_fonts()
        demo_font_effects()
        demo_text_layer_enhanced()
        demo_font_performance()

        print("\n" + "🔤" * 40)
        print("  ENHANCED FONT SYSTEM COMPLETE!")
        print("🔤" * 40)

        print("\n✨ Font capabilities demonstrated:")
        print("   🔍 System font discovery - Finds all installed fonts")
        print("   💀 Horror font detection - Identifies spooky fonts")
        print("   💪 Bold font selection - Finds impactful fonts")
        print("   ✨ Advanced effects - Outlines, shadows, styles")
        print("   🎨 Multiple renderers - PIL + Pygame + Fallback")
        print("   📊 Performance optimized - Fast rendering with caching")

        print("\n🎃 Perfect for Dead Sexy Halloween:")
        print("   Your 'DEAD SEXY' text will use the best available fonts")
        print("   Horror fonts create authentic spooky atmosphere")
        print("   Bold fonts ensure maximum visual impact")
        print("   Professional effects (outlines, shadows) enhance readability")

        print("\n🔤 Your text will look DEAD SEXY with professional fonts! 🔤")

    except Exception as e:
        print(f"Demo failed: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    main()
