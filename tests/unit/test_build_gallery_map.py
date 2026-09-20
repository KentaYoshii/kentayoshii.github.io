"""Unit tests for scripts/build_gallery_map.py.

The projection is the part worth testing hardest, because a wrong constant
there produces a map that still looks like a map. Its real check lives in
tests/integration/test_gallery_map_data.py, which puts every park inside its
own state polygon; these cover the pieces underneath it.
"""

import math

import pytest

import build_gallery_map as bgm


class TestConicEqualArea:
    def projection(self):
        return bgm.albers_usa()['lower48']

    def test_the_centre_lands_on_the_translate(self) -> None:
        # center is fed to the raw projection unrotated, so the point that
        # should land on the translate is the rotation applied in reverse.
        project = self.projection()
        x, y = project(-0.6 - 96.0, 38.7)
        assert x == pytest.approx(bgm.TRANSLATE[0], abs=0.01)
        assert y == pytest.approx(bgm.TRANSLATE[1], abs=0.01)

    def test_north_is_up(self) -> None:
        project = self.projection()
        _, north = project(-98.0, 45.0)
        _, south = project(-98.0, 30.0)
        assert north < south

    def test_east_is_right(self) -> None:
        project = self.projection()
        west, _ = project(-120.0, 40.0)
        east, _ = project(-80.0, 40.0)
        assert west < east

    def test_the_contiguous_states_land_on_the_canvas(self) -> None:
        project = self.projection()
        corners = [(-124.7, 48.4), (-66.9, 44.8), (-124.4, 32.5), (-80.0, 25.1)]
        for lon, lat in corners:
            x, y = project(lon, lat)
            assert 0 <= x <= bgm.VIEW_WIDTH
            assert 0 <= y <= bgm.VIEW_HEIGHT

    def test_rejects_degenerate_parallels(self) -> None:
        with pytest.raises(ValueError):
            bgm.ConicEqualArea([30.0, -30.0], 0.0, (0.0, 0.0), 1000, (0, 0))


class TestAlbersUsa:
    def test_hawaii_is_moved_in_beside_the_mainland(self) -> None:
        # Projected on the lower-48 conic, Maui would be far off the left of
        # the canvas; the inset is what brings it back. That is the whole
        # reason albersUsa exists rather than a single conic.
        projections = bgm.albers_usa()
        off_canvas = projections['lower48'](-156.2, 20.7)[0]
        inset = projections['hawaii'](-156.2, 20.7)[0]
        assert off_canvas < 0
        assert 0 < inset < bgm.VIEW_WIDTH

    def test_alaska_is_drawn_smaller_than_life(self) -> None:
        assert bgm.albers_usa()['alaska'].scale < bgm.albers_usa()['lower48'].scale

    @pytest.mark.parametrize('fips, expected', [
        ('02', 'alaska'), ('15', 'hawaii'), ('53', 'lower48'), ('48', 'lower48'),
    ])
    def test_states_route_to_the_right_projection(self, fips, expected) -> None:
        projections = bgm.albers_usa()
        assert bgm.projection_for(fips, projections) is projections[expected]


class TestDecodeArcs:
    def test_undoes_delta_encoding_and_quantisation(self) -> None:
        topology = {
            'transform': {'scale': [0.5, 0.25], 'translate': [-100.0, 40.0]},
            'arcs': [[[0, 0], [2, 4], [2, -4]]],
        }
        assert bgm.decode_arcs(topology) == [[
            (-100.0, 40.0), (-99.0, 41.0), (-98.0, 40.0),
        ]]

    def test_an_untransformed_topology_passes_through(self) -> None:
        topology = {'arcs': [[[1, 2], [3, 4]]]}
        assert bgm.decode_arcs(topology) == [[(1.0, 2.0), (4.0, 6.0)]]


class TestStitch:
    ARCS = [
        [(0, 0), (1, 1)],
        [(1, 1), (2, 0)],
        [(2, 0), (0, 0)],
    ]

    def test_joins_arcs_without_repeating_the_shared_point(self) -> None:
        assert bgm.stitch([0, 1, 2], self.ARCS) == [
            (0, 0), (1, 1), (2, 0), (0, 0),
        ]

    def test_a_negative_index_reverses_that_arc(self) -> None:
        # ~(-1) is 0, so -1 means arc 0 backwards. Reading it as index -1
        # (the last arc) is the classic way to get a self-crossing polygon.
        assert bgm.stitch([-1], self.ARCS) == [(1, 1), (0, 0)]

    def test_a_single_arc_is_returned_whole(self) -> None:
        assert bgm.stitch([1], self.ARCS) == [(1, 1), (2, 0)]


class TestRingsOf:
    ARCS = [[(0, 0), (1, 1), (2, 0), (0, 0)]]

    def test_reads_a_polygon(self) -> None:
        rings = bgm.rings_of({'type': 'Polygon', 'arcs': [[0]]}, self.ARCS)
        assert len(rings) == 1

    def test_reads_every_ring_of_a_multipolygon(self) -> None:
        geometry = {'type': 'MultiPolygon', 'arcs': [[[0]], [[0]]]}
        assert len(bgm.rings_of(geometry, self.ARCS)) == 2

    def test_a_null_geometry_contributes_nothing(self) -> None:
        assert bgm.rings_of({'type': None}, self.ARCS) == []

    def test_rejects_an_unexpected_type(self) -> None:
        with pytest.raises(ValueError):
            bgm.rings_of({'type': 'LineString', 'arcs': [0]}, self.ARCS)


class TestSimplify:
    def test_collinear_points_are_dropped(self) -> None:
        line = [(0, 0), (1, 0), (2, 0), (3, 0), (4, 0)]
        assert bgm.simplify(line, 0.5) == [(0, 0), (4, 0)]

    def test_the_endpoints_always_survive(self) -> None:
        points = [(0, 0), (1, 5), (2, -5), (3, 0)]
        simplified = bgm.simplify(points, 0.5)
        assert simplified[0] == (0, 0)
        assert simplified[-1] == (3, 0)

    def test_a_deviation_above_the_tolerance_is_kept(self) -> None:
        assert (1, 3) in bgm.simplify([(0, 0), (1, 3), (2, 0)], 1.0)

    def test_a_deviation_below_the_tolerance_is_dropped(self) -> None:
        assert bgm.simplify([(0, 0), (1, 0.1), (2, 0)], 1.0) == [(0, 0), (2, 0)]

    def test_shorter_than_three_points_is_untouched(self) -> None:
        assert bgm.simplify([(0, 0), (1, 1)], 5.0) == [(0, 0), (1, 1)]

    def test_output_is_never_longer_than_input(self) -> None:
        points = [(i, math.sin(i / 3.0) * 10) for i in range(200)]
        assert len(bgm.simplify(points, 1.0)) <= len(points)

    def test_a_ring_the_size_of_a_real_coastline_is_reduced(self) -> None:
        # The longest ring in the committed geometry is about 2000 points.
        # A near-circle at that resolution is mostly redundant detail.
        circle = [(math.cos(i / 2000.0 * math.tau) * 300,
                   math.sin(i / 2000.0 * math.tau) * 300) for i in range(2000)]
        simplified = bgm.simplify(circle, bgm.TOLERANCE)
        assert 3 <= len(simplified) < len(circle) / 4

    def test_every_kept_point_came_from_the_input(self) -> None:
        # Simplification selects points; it must never interpolate new ones,
        # or the outline would drift away from the coastline it describes.
        points = [(i, math.sin(i / 3.0) * 10) for i in range(200)]
        assert set(bgm.simplify(points, 1.0)) <= set(points)

    def test_a_larger_tolerance_never_keeps_more(self) -> None:
        points = [(i, math.sin(i / 5.0) * 8) for i in range(300)]
        counts = [len(bgm.simplify(points, t)) for t in (0.2, 1.0, 5.0, 20.0)]
        assert counts == sorted(counts, reverse=True)


class TestPerpendicularDistance:
    def test_measures_off_the_line(self) -> None:
        assert bgm.perpendicular_distance((1, 3), (0, 0), (2, 0)) == 3

    def test_a_point_on_the_line_is_zero(self) -> None:
        assert bgm.perpendicular_distance((1, 0), (0, 0), (2, 0)) == 0

    def test_a_zero_length_segment_falls_back_to_point_distance(self) -> None:
        assert bgm.perpendicular_distance((3, 4), (0, 0), (0, 0)) == 5


class TestToPath:
    def test_writes_a_closed_subpath_per_ring(self) -> None:
        path = bgm.to_path([[(0, 0), (1, 0), (1, 1)]])
        assert path == 'M0.0,0.0L1.0,0.0L1.0,1.0Z'

    def test_rings_too_small_to_enclose_area_are_dropped(self) -> None:
        assert bgm.to_path([[(0, 0), (1, 1)]]) == ''

    def test_coordinates_are_rounded(self) -> None:
        assert bgm.to_path([[(0.123456, 0), (1, 0), (1, 1)]],
                           places=1).startswith('M0.1,0.0')


class TestParkTable:
    def test_every_park_has_a_plausible_coordinate(self) -> None:
        for name, (lat, lon, fips) in bgm.PARKS.items():
            assert 15 < lat < 72, name
            assert -180 < lon < -60, name
            assert len(fips) == 2 and fips.isdigit(), name

    def test_no_park_sits_in_a_dropped_territory(self) -> None:
        for name, (_, _, fips) in bgm.PARKS.items():
            assert fips not in bgm.TERRITORY_FIPS, name
