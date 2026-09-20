"""Unit tests for scripts/build_gallery_thumbs.py.

Only the pure helpers are covered, which is also the reason they are written
as pure helpers: the script needs Pillow, CI does not install it, and the
arithmetic worth testing is the arithmetic that does not need an image. The
resizing itself is checked by running the script and looking at the result.

The sharp edges here are the ones that were got wrong while writing it: a mean
colour that made every park the same shade, and hue averaging that turns two
opposite colours into a grey neither photo contains.
"""

import colorsys
import os

import pytest

import build_gallery_thumbs as bgt


class TestScaledSize:
    @pytest.mark.parametrize('size, target, expected', [
        ((4032, 3024), 800, (800, 600)),
        ((5712, 4284), 2000, (2000, 1500)),
        ((3024, 4032), 800, (800, 1067)),
        ((3022, 2159), 800, (800, 572)),
    ])
    def test_preserves_aspect_ratio(self, size, target, expected) -> None:
        assert bgt.scaled_size(size, target) == expected

    @pytest.mark.parametrize('size', [(640, 480), (800, 600), (16, 9)])
    def test_never_upscales(self, size) -> None:
        # A photo already narrower than the target comes back untouched, so
        # the declared width/height cannot disagree with the file written.
        assert bgt.scaled_size(size, 800) == size

    def test_height_never_rounds_to_zero(self) -> None:
        assert bgt.scaled_size((10000, 3), 16)[1] == 1

    @pytest.mark.parametrize('size', [(0, 100), (100, 0), (-1, 5)])
    def test_rejects_a_degenerate_size(self, size) -> None:
        with pytest.raises(ValueError):
            bgt.scaled_size(size, 800)


class TestDerivativePath:
    @pytest.mark.parametrize('kind', ['thumbs', 'large'])
    def test_keeps_the_basename_under_the_kind(self, kind: str) -> None:
        path = bgt.derivative_path('/photos/zion_1.jpeg', kind,
                                   derivatives_dir='/site')
        assert path == '/site/%s/zion_1.jpeg' % kind

    def test_rejects_an_unknown_kind(self) -> None:
        with pytest.raises(ValueError):
            bgt.derivative_path('/photos/a.jpeg', 'huge',
                                derivatives_dir='/site')

    def test_the_derivatives_are_written_inside_the_site_source(self) -> None:
        # The originals sit outside docs/ so Jekyll cannot publish them; the
        # derivatives have to be inside it, or the page has nothing to load.
        for kind in bgt.SIZES:
            assert bgt.derivative_path('/anywhere/a.jpeg', kind).startswith(
                os.path.join(bgt.ROOT, 'docs'))

    def test_originals_are_read_from_outside_the_site_source(self) -> None:
        assert not bgt.ORIGINALS.startswith(os.path.join(bgt.ROOT, 'docs'))


class TestIsStale:
    def test_a_missing_derivative_is_stale(self, tmp_path) -> None:
        original = tmp_path / 'a.jpeg'
        original.write_bytes(b'x')
        assert bgt.is_stale(str(original), str(tmp_path / 'nope.jpeg'))

    def test_an_older_derivative_is_stale(self, tmp_path) -> None:
        derivative = tmp_path / 'old.jpeg'
        derivative.write_bytes(b'x')
        original = tmp_path / 'new.jpeg'
        original.write_bytes(b'x')
        import os
        os.utime(str(derivative), (1, 1))
        assert bgt.is_stale(str(original), str(derivative))

    def test_a_newer_derivative_is_not_stale(self, tmp_path) -> None:
        original = tmp_path / 'a.jpeg'
        original.write_bytes(b'x')
        derivative = tmp_path / 'b.jpeg'
        derivative.write_bytes(b'x')
        import os
        os.utime(str(original), (1, 1))
        assert not bgt.is_stale(str(original), str(derivative))


class TestToHex:
    @pytest.mark.parametrize('rgb, text', [
        ((0, 0, 0), '#000000'),
        ((255, 255, 255), '#ffffff'),
        ((122.6, 104.4, 70.2), '#7b6846'),
    ])
    def test_formats_and_rounds(self, rgb, text: str) -> None:
        assert bgt.to_hex(rgb) == text

    def test_clamps_out_of_range_components(self) -> None:
        assert bgt.to_hex((-20, 300, 128)) == '#00ff80'


class TestCombineColours:
    def hue_of(self, rgb) -> float:
        return colorsys.rgb_to_hsv(*[c / 255.0 for c in rgb])[0] * 360

    def test_one_colour_survives_the_round_trip(self) -> None:
        combined = bgt.combine_colours([(122, 104, 70)])
        assert bgt.to_hex(combined) == '#7a6846'

    def test_similar_hues_average_between_them(self) -> None:
        # Two greens average to a green, not to something off in the blues.
        combined = bgt.combine_colours([(60, 140, 70), (70, 160, 60)])
        assert 90 <= self.hue_of(combined) <= 150

    def test_hue_wraps_around_the_circle(self) -> None:
        # Hues either side of red (about 350 and about 10) must average to red
        # near 0, not to cyan at 180 as a plain numeric mean would give.
        combined = bgt.combine_colours([(200, 40, 70), (200, 70, 40)])
        hue = self.hue_of(combined)
        assert hue < 30 or hue > 330

    def test_opposite_hues_do_not_produce_a_muddy_mean(self) -> None:
        # The reason this is not an RGB average: orange and blue would come
        # back grey, a colour neither photo contains. Averaging on the circle
        # keeps saturation instead.
        combined = bgt.combine_colours([(220, 120, 30), (30, 90, 200)])
        saturation = colorsys.rgb_to_hsv(*[c / 255.0 for c in combined])[1]
        assert saturation > 0.4

    def test_fully_grey_input_is_stable(self) -> None:
        combined = bgt.combine_colours([(128, 128, 128), (100, 100, 100)])
        red, green, blue = combined
        assert abs(red - green) < 1 and abs(green - blue) < 1

    def test_rejects_an_empty_list(self) -> None:
        with pytest.raises(ValueError):
            bgt.combine_colours([])


class TestAccent:
    def test_hue_is_never_altered(self) -> None:
        source = (30, 90, 200)
        before = colorsys.rgb_to_hsv(*[c / 255.0 for c in source])[0]
        result = bgt.accent(source, bgt.ACCENT_LIGHT)
        rgb = [int(result[i:i + 2], 16) for i in (1, 3, 5)]
        after = colorsys.rgb_to_hsv(*[c / 255.0 for c in rgb])[0]
        assert abs(before - after) < 0.01

    @pytest.mark.parametrize('bounds', [bgt.ACCENT_LIGHT, bgt.ACCENT_DARK])
    @pytest.mark.parametrize('source', [(0, 0, 0), (255, 255, 255),
                                        (23, 18, 11), (202, 183, 149)])
    def test_lightness_lands_inside_the_bounds(self, source, bounds) -> None:
        result = bgt.accent(source, bounds)
        rgb = [int(result[i:i + 2], 16) for i in (1, 3, 5)]
        value = colorsys.rgb_to_hsv(*[c / 255.0 for c in rgb])[2]
        assert bounds['min_val'] - 0.02 <= value <= bounds['max_val'] + 0.02

    def test_the_dark_variant_is_lighter_than_the_light_one(self) -> None:
        # Both are read against their own background; the dark theme needs the
        # lighter colour. Getting these the wrong way round is invisible until
        # someone switches theme.
        source = (29, 21, 14)
        light = bgt.accent(source, bgt.ACCENT_LIGHT)
        dark = bgt.accent(source, bgt.ACCENT_DARK)
        brightness = lambda h: sum(int(h[i:i + 2], 16) for i in (1, 3, 5))
        assert brightness(dark) > brightness(light)


class TestScoreCluster:
    def test_a_more_prominent_cluster_scores_higher(self) -> None:
        assert bgt.score_cluster(0.5, 0.4, 0.5) > bgt.score_cluster(0.1, 0.4, 0.5)

    def test_a_more_saturated_cluster_scores_higher(self) -> None:
        # This is the whole point of the weighting: a big grey region should
        # lose to a smaller region that actually carries the park's colour.
        assert bgt.score_cluster(0.3, 0.6, 0.5) > bgt.score_cluster(0.3, 0.1, 0.5)

    def test_a_grey_cluster_scores_near_zero(self) -> None:
        assert bgt.score_cluster(0.9, 0.0, 0.5) == 0
