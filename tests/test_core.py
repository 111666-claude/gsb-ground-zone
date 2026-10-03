import unittest

from zones.core import Field


def field():
    return Field(tick_ms=1000)


class BasicTest(unittest.TestCase):
    def test_empty_field_settles_nothing(self):
        self.assertEqual(field().tick(1000), {})

    def test_zone_count_starts_at_zero(self):
        self.assertEqual(field().zone_count(), 0)

    def test_zone_is_registered(self):
        world = field()
        world.add_zone("z1", 0, 0, 10, "fire", 5, 10000, 0)
        self.assertEqual(world.zone_count(), 1)

    def test_unknown_unit_is_ignored_by_move(self):
        world = field()
        world.move("ghost", 1, 1)
        self.assertEqual(world.units, {})

    def test_scanned_starts_at_zero(self):
        self.assertEqual(field().scanned_count(), 0)


if __name__ == "__main__":
    unittest.main()


class EdgeTest(unittest.TestCase):
    def test_unit_exactly_on_radius_is_inside(self):
        world = field()
        world.add_zone("z1", 0, 0, 10, "fire", 5, 10000, 0)
        world.add_unit("u1", 10, 0)
        self.assertEqual(world.tick(1000), {"u1": 5})

    def test_unit_just_outside_radius_gets_nothing(self):
        world = field()
        world.add_zone("z1", 0, 0, 10, "fire", 5, 10000, 0)
        world.add_unit("u1", 10.000001, 0)
        self.assertEqual(world.tick(1000), {})

    def test_diagonal_edge_is_inside(self):
        world = field()
        world.add_zone("z1", 0, 0, 10, "fire", 5, 10000, 0)
        world.add_unit("u1", 6, 8)
        self.assertEqual(world.tick(1000), {"u1": 5})


class PeriodTest(unittest.TestCase):
    def test_same_moment_settles_once(self):
        world = field()
        world.add_zone("z1", 0, 0, 10, "fire", 5, 10000, 0)
        world.add_unit("u1", 0, 0)
        self.assertEqual(world.tick(1000), {"u1": 5})
        self.assertEqual(world.tick(1000), {})

    def test_partial_period_returns_empty(self):
        world = field()
        world.add_zone("z1", 0, 0, 10, "fire", 5, 10000, 0)
        world.add_unit("u1", 0, 0)
        world.tick(1000)
        self.assertEqual(world.tick(1999), {})
        self.assertEqual(world.tick(2000), {"u1": 5})

    def test_first_tick_always_settles(self):
        world = field()
        world.add_zone("z1", 0, 0, 10, "fire", 5, 10000, 0)
        world.add_unit("u1", 0, 0)
        self.assertEqual(world.tick(0), {"u1": 5})


class OverlapTest(unittest.TestCase):
    def test_same_kind_takes_highest_only(self):
        world = field()
        world.add_zone("z1", 0, 0, 10, "fire", 5, 10000, 0)
        world.add_zone("z2", 0, 0, 10, "fire", 8, 10000, 0)
        world.add_unit("u1", 0, 0)
        self.assertEqual(world.tick(1000), {"u1": 8})

    def test_different_kinds_each_settle(self):
        world = field()
        world.add_zone("z1", 0, 0, 10, "fire", 5, 10000, 0)
        world.add_zone("z2", 0, 0, 10, "poison", 3, 10000, 0)
        world.add_unit("u1", 0, 0)
        self.assertEqual(world.tick(1000), {"u1": 8})

    def test_per_unit_damage_never_exceeds_kind_maximum(self):
        world = field()
        for index in range(50):
            world.add_zone("z%d" % index, 0, 0, 10, "fire", index + 1, 10000, 0)
        world.add_unit("u1", 0, 0)
        self.assertEqual(world.tick(1000), {"u1": 50})


class ExpireTest(unittest.TestCase):
    def test_zone_stops_settling_at_duration(self):
        world = field()
        world.add_zone("z1", 0, 0, 10, "fire", 5, 500, 0)
        world.add_unit("u1", 0, 0)
        self.assertEqual(world.tick(500), {})

    def test_zone_settles_before_duration(self):
        world = field()
        world.add_zone("z1", 0, 0, 10, "fire", 5, 500, 0)
        world.add_unit("u1", 0, 0)
        self.assertEqual(world.tick(499), {"u1": 5})

    def test_expired_zone_is_removed(self):
        world = field()
        world.add_zone("z1", 0, 0, 10, "fire", 5, 500, 0)
        world.add_unit("u1", 0, 0)
        world.tick(500)
        self.assertEqual(world.zone_count(), 0)

    def test_expired_zone_far_from_units_is_removed(self):
        world = field()
        world.add_zone("z1", 1000, 1000, 10, "fire", 5, 500, 0)
        world.add_unit("u1", 0, 0)
        world.tick(500)
        self.assertEqual(world.zone_count(), 0)


class DeterminismTest(unittest.TestCase):
    def test_same_sequence_repeats_identically(self):
        def run():
            world = field()
            world.add_zone("z1", 0, 0, 10, "fire", 5, 3000, 0)
            world.add_zone("z2", 3, 4, 10, "poison", 7, 3000, 0)
            world.add_unit("u1", 0, 0)
            world.add_unit("u2", 30, 0)
            results = []
            for now in (1000, 1000, 2000, 2500, 3000, 4000):
                world.move("u1", now / 1000.0, 0)
                results.append(world.tick(now))
            return results

        self.assertEqual(run(), run())


class ScanCostTest(unittest.TestCase):
    def test_scanned_does_not_grow_with_zone_count(self):
        world = Field(tick_ms=1)
        for index in range(3000):
            world.add_zone("z-%d" % index, index, 0, 5, "fire", 1, 100000, 0)
        world.add_unit("u1", 0, 0)
        for index in range(3000):
            world.tick(1000 + index)
        self.assertLessEqual(world.scanned_count(), 6000)

    def test_scanned_ignores_idle_ticks(self):
        world = field()
        world.add_zone("z1", 0, 0, 10, "fire", 5, 10000, 0)
        world.add_unit("u1", 0, 0)
        world.tick(1000)
        for _ in range(100):
            world.tick(1000)
        self.assertEqual(world.scanned_count(), 1)
