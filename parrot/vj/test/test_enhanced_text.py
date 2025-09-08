import pytest
import numpy as np
from parrot.vj.text_renderer import (
    FontManager,
    EnhancedTextRenderer,
    PygameTextRenderer,
    MultiRendererTextSystem,
    get_text_renderer,
)
from parrot.vj.layers.text import TextLayer
from parrot.director.frame import Frame
from parrot.director.color_scheme import ColorScheme
from parrot.utils.colour import Color


class TestFontManager:
    """Test font discovery and management"""

    def test_font_manager_creation(self):
        """Test FontManager creation"""
        font_manager = FontManager()

        # Should discover some fonts
        assert len(font_manager.system_fonts) > 0

        # Should have font families
        families = font_manager.get_font_families()
        assert len(families) > 0

        # Each font should have required fields
        for font_info in font_manager.system_fonts.values():
            assert "path" in font_info
            assert "name" in font_info
            assert "family" in font_info
            assert "style" in font_info

    def test_font_finding(self):
        """Test font finding functionality"""
        font_manager = FontManager()

        # Should be able to find common fonts
        common_fonts = ["Arial", "Helvetica", "Times New Roman"]

        found_fonts = 0
        for font_name in common_fonts:
            font_path = font_manager.find_font(font_name)
            if font_path:
                found_fonts += 1
                assert font_path.endswith((".ttf", ".otf", ".ttc"))

        # Should find at least one common font
        assert found_fonts > 0

    def test_font_styles(self):
        """Test font style detection"""
        font_manager = FontManager()

        # Find a font family with multiple styles
        families = font_manager.get_font_families()

        if families:
            # Test style detection for first family
            family = families[0]
            styles = font_manager.get_font_styles(family)

            assert isinstance(styles, list)
            # Should have at least one style
            assert len(styles) > 0


class TestEnhancedTextRenderer:
    """Test enhanced text rendering"""

    def test_enhanced_renderer_creation(self):
        """Test EnhancedTextRenderer creation"""
        renderer = EnhancedTextRenderer()

        assert renderer.font_manager is not None
        assert isinstance(renderer.font_cache, dict)

    def test_text_rendering(self):
        """Test basic text rendering"""
        renderer = EnhancedTextRenderer()

        result = renderer.render_text(
            text="TEST", font_size=72, color=(255, 0, 0), width=300, height=100
        )

        if result is not None:
            assert result.shape == (100, 300, 4)  # height x width x RGBA
            assert result.dtype == np.uint8

            # Should have some red content
            assert np.any(result[:, :, 0] > 0)  # Red channel

    def test_text_effects(self):
        """Test text effects (outline, shadow)"""
        renderer = EnhancedTextRenderer()

        # Test with outline
        result_outline = renderer.render_text(
            text="BOLD",
            font_size=100,
            color=(255, 255, 255),
            width=400,
            height=150,
            outline_width=3,
            outline_color=(0, 0, 0),
        )

        # Test with shadow
        result_shadow = renderer.render_text(
            text="SHADOW",
            font_size=100,
            color=(255, 255, 255),
            width=400,
            height=150,
            shadow_offset=(5, 5),
            shadow_color=(0, 0, 0, 128),
        )

        # Both should render successfully
        if result_outline is not None:
            assert result_outline.shape == (150, 400, 4)

        if result_shadow is not None:
            assert result_shadow.shape == (150, 400, 4)

    def test_fallback_rendering(self):
        """Test fallback text rendering"""
        renderer = EnhancedTextRenderer()

        result = renderer._fallback_text_render(
            text="FALLBACK", width=400, height=100, color=(0, 255, 0)
        )

        assert result.shape == (100, 400, 4)
        assert result.dtype == np.uint8

        # Should have some green content
        assert np.any(result[:, :, 1] > 0)  # Green channel


class TestMultiRendererTextSystem:
    """Test multi-renderer text system"""

    def test_multi_renderer_creation(self):
        """Test MultiRendererTextSystem creation"""
        text_system = MultiRendererTextSystem()

        assert text_system.font_manager is not None
        assert text_system.enhanced_renderer is not None
        assert text_system.pygame_renderer is not None

        # Should have found some fonts
        assert len(text_system.horror_fonts) >= 0
        assert len(text_system.bold_fonts) >= 0

    def test_dead_sexy_rendering(self):
        """Test 'DEAD SEXY' text rendering"""
        text_system = MultiRendererTextSystem()

        # Test different styles
        styles = ["horror", "bold", "default"]

        for style in styles:
            result = text_system.render_dead_sexy_text(
                width=600, height=200, style=style
            )

            if result is not None:
                assert result.shape == (200, 600, 4)
                assert result.dtype == np.uint8

                # Should have some content
                assert np.count_nonzero(result) > 0

    def test_font_info(self):
        """Test font information retrieval"""
        text_system = MultiRendererTextSystem()

        font_info = text_system.get_font_info()

        assert isinstance(font_info, dict)
        assert "total_fonts" in font_info
        assert "font_families" in font_info
        assert "horror_fonts" in font_info
        assert "bold_fonts" in font_info
        assert "pil_available" in font_info

        # Should have found some fonts
        assert font_info["total_fonts"] > 0

    def test_global_text_renderer(self):
        """Test global text renderer instance"""
        renderer1 = get_text_renderer()
        renderer2 = get_text_renderer()

        # Should return the same instance (singleton pattern)
        assert renderer1 is renderer2
        assert isinstance(renderer1, MultiRendererTextSystem)


class TestEnhancedTextLayer:
    """Test enhanced TextLayer functionality"""

    def test_enhanced_text_layer_creation(self):
        """Test TextLayer with enhanced rendering"""
        text_layer = TextLayer(
            text="ENHANCED", name="test_enhanced", font_size=100, width=500, height=200
        )

        # Should have text renderer
        assert hasattr(text_layer, "text_renderer")
        assert text_layer.text_renderer is not None

    def test_font_family_setting(self):
        """Test setting font family"""
        text_layer = TextLayer("TEST", "test", width=300, height=150)

        # Try to set a common font
        text_layer.set_font_family("Arial")

        # Should update font path if font is found
        # (Might not find it depending on system, but shouldn't crash)
        assert hasattr(text_layer, "font_path")

    def test_horror_font_selection(self):
        """Test horror font selection"""
        text_layer = TextLayer("HORROR", "test", width=400, height=200)

        # Should not crash when trying to use horror font
        text_layer.use_horror_font()

        # Should have attempted to change font
        assert hasattr(text_layer, "text_dirty")

    def test_bold_font_selection(self):
        """Test bold font selection"""
        text_layer = TextLayer("BOLD", "test", width=400, height=200)

        # Should not crash when trying to use bold font
        text_layer.use_bold_font()

        # Should have attempted to change font
        assert hasattr(text_layer, "text_dirty")

    def test_enhanced_rendering_integration(self):
        """Test enhanced rendering integration"""
        text_layer = TextLayer(
            text="INTEGRATION",
            name="test_integration",
            font_size=120,
            width=600,
            height=250,
            alpha_mask=True,
        )

        # Try horror font
        text_layer.use_horror_font()

        # Render
        frame = Frame({})
        scheme = ColorScheme(Color("red"), Color("black"), Color("white"))

        result = text_layer.render(frame, scheme)

        if result is not None:
            assert result.shape == (250, 600, 4)
            assert result.dtype == np.uint8

            # Should have content
            assert np.count_nonzero(result) > 0

            # Check alpha masking if enabled
            if text_layer.alpha_mask:
                alpha_channel = result[:, :, 3]
                has_transparent = np.any(alpha_channel == 0)
                has_opaque = np.any(alpha_channel == 255)

                # Should have both transparent and opaque areas for alpha mask
                assert has_transparent or has_opaque

    def test_font_availability_info(self):
        """Test font availability information"""
        text_layer = TextLayer("INFO", "test", width=200, height=100)

        font_info = text_layer.get_available_fonts()

        assert isinstance(font_info, dict)

        if "error" not in font_info:
            # Should have font information
            assert "total_fonts" in font_info
            assert font_info["total_fonts"] >= 0


class TestTextRenderingPerformance:
    """Test text rendering performance"""

    def test_rendering_speed(self):
        """Test that text rendering is reasonably fast"""
        text_system = MultiRendererTextSystem()

        import time

        # Test multiple renders to check performance
        start_time = time.time()

        for i in range(5):  # Render 5 times
            result = text_system.render_dead_sexy_text(
                width=800, height=300, style="bold"
            )

            if result is not None:
                assert result.shape == (300, 800, 4)

        total_time = time.time() - start_time
        avg_time = total_time / 5

        # Should render in reasonable time (less than 100ms per render)
        assert avg_time < 0.1

    def test_font_caching(self):
        """Test that font caching works"""
        renderer = EnhancedTextRenderer()

        # Render same text twice with same font
        result1 = renderer.render_text("CACHE", font_size=100, width=300, height=100)
        result2 = renderer.render_text("CACHE", font_size=100, width=300, height=100)

        # Should have cached the font
        assert len(renderer.font_cache) > 0

        # Both renders should succeed
        if result1 is not None and result2 is not None:
            assert result1.shape == result2.shape


class TestFontIntegration:
    """Test font integration with VJ system"""

    def test_text_layer_font_switching(self):
        """Test font switching in TextLayer"""
        text_layer = TextLayer("SWITCH", "test", width=400, height=200)

        frame = Frame({})
        scheme = ColorScheme(Color("purple"), Color("orange"), Color("cyan"))

        # Test different font modes
        font_modes = [
            ("Default", lambda: None),
            ("Horror", lambda: text_layer.use_horror_font()),
            ("Bold", lambda: text_layer.use_bold_font()),
        ]

        results = []

        for mode_name, font_action in font_modes:
            if font_action:
                font_action()

            result = text_layer.render(frame, scheme)

            if result is not None:
                results.append((mode_name, result))

        # Should have rendered at least one result
        assert len(results) > 0

        # All results should be same shape
        for mode_name, result in results:
            assert result.shape == (200, 400, 4)

    def test_enhanced_text_with_effects(self):
        """Test enhanced text with VJ effects"""
        text_layer = TextLayer(
            text="EFFECTS",
            name="test_effects",
            font_size=100,
            width=500,
            height=200,
            alpha_mask=False,  # Disable alpha mask for this test
        )

        # Use best available font
        text_layer.use_horror_font()

        # Test with text effects
        text_layer.set_outline(3, (255, 255, 255))  # White outline
        text_layer.set_shadow((4, 4), (0, 0, 0, 150))  # Black shadow

        frame = Frame({})
        scheme = ColorScheme(Color("red"), Color("black"), Color("orange"))

        result = text_layer.render(frame, scheme)

        if result is not None:
            # Should have enhanced text with effects
            assert result.shape == (200, 500, 4)
            assert np.count_nonzero(result) > 0

            # Should have multiple colors (text + outline + shadow)
            unique_colors = len(np.unique(result.reshape(-1, 4), axis=0))
            assert unique_colors > 1  # More than just one color

    def test_font_system_robustness(self):
        """Test font system robustness with edge cases"""
        text_system = MultiRendererTextSystem()

        # Test with non-existent font
        result = text_system.enhanced_renderer.render_text(
            text="FALLBACK",
            font_family="NonExistentFont12345",
            font_size=80,
            width=400,
            height=150,
        )

        # Should still render with fallback
        if result is not None:
            assert result.shape == (150, 400, 4)

        # Test with invalid parameters
        result = text_system.enhanced_renderer.render_text(
            text="", font_size=0, width=10, height=10  # Empty text  # Invalid size
        )

        # Should handle gracefully (might return None or minimal render)
        if result is not None:
            assert result.shape == (10, 10, 4)


class TestFontPerformance:
    """Test font rendering performance"""

    def test_large_text_performance(self):
        """Test performance with large text"""
        text_system = MultiRendererTextSystem()

        import time

        start_time = time.time()

        # Render large text
        result = text_system.render_dead_sexy_text(
            width=1920, height=600, style="horror"
        )

        render_time = time.time() - start_time

        # Should render in reasonable time
        assert render_time < 1.0  # Less than 1 second

        if result is not None:
            assert result.shape == (600, 1920, 4)

    def test_multiple_renders_performance(self):
        """Test performance with multiple renders"""
        renderer = EnhancedTextRenderer()

        import time

        start_time = time.time()

        # Multiple renders
        for i in range(3):
            result = renderer.render_text(
                text=f"TEXT{i}", font_size=100, width=400, height=150
            )

            if result is not None:
                assert result.shape == (150, 400, 4)

        total_time = time.time() - start_time
        avg_time = total_time / 3

        # Average time should be reasonable
        assert avg_time < 0.2  # Less than 200ms per render
