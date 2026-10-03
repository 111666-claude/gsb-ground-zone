import unittest

from zones.core import Field


def field(tick_ms=1000):
    return Field(tick_ms=tick_ms)


class BoundaryTest(unittest.TestCase):
    def test_unit_exactly_on_radius_is_inside(self):
        world = field()
        world.add_zone("z1", 0, 0, 10, "fire", 5, 10000, 0)
        world.add_unit("u1", 10, 0)
        self.assertEqual(world.tick(1000), {"u1": 5})

    def test_unit_just_outside_radius_gets_nothing(self):
        world = field()
        world.add_zone("z1", 0, 0, 10, "fire", 5, 10000, 0)
        world.add_unit("u1", 11, 0)
        self.assertEqual(world.tick(1000), {})

    def test_diagonal_distance_on_radius_is_inside(self):
        world = field()
        world.add_zone("z1", 0, 0, 5, "fire", 7, 10000, 0)
        world.add_unit("u1", 3, 4)
        self.assertEqual(world.tick(1000), {"u1": 7})

    def test_move_onto_boundary_enters_zone(self):
        world = field()
        world.add_zone("z1", 0, 0, 10, "fire", 5, 10000, 0)
        world.add_unit("u1", 20, 0)
        self.assertEqual(world.tick(1000), {})
        world.move("u1", 10, 0)
        self.assertEqual(world.tick(2000), {"u1": 5})


class PeriodTest(unittest.TestCase):
    def test_repeat_call_same_instant_returns_empty(self):
        world = field()
        world.add_zone("z1", 0, 0, 10, "fire", 5, 10000, 0)
        world.add_unit("u1", 0, 0)
        self.assertEqual(world.tick(1000), {"u1": 5})
        self.assertEqual(world.tick(1000), {})

    def test_no_settle_before_full_tick_elapsed(self):
        world = field()
        world.add_zone("z1", 0, 0, 10, "fire", 5, 10000, 0)
        world.add_unit("u1", 0, 0)
        world.tick(1000)
        self.assertEqual(world.tick(1999), {})

    def test_settles_once_full_tick_elapsed(self):
        world = field()
        world.add_zone("z1", 0, 0, 10, "fire", 5, 10000, 0)
        world.add_unit("u1", 0, 0)
        world.tick(1000)
        self.assertEqual(world.tick(2000), {"u1": 5})

    def test_long_gap_still_settles_only_once(self):
        world = field()
        world.add_zone("z1", 0, 0, 10, "fire", 5, 100000, 0)
        world.add_unit("u1", 0, 0)
        world.tick(1000)
        self.assertEqual(world.tick(50000), {"u1": 5})
        self.assertEqual(world.tick(50000), {})


class DedupTest(unittest.TestCase):
    def test_same_kind_takes_max_not_sum(self):
        world = field()
        world.add_zone("z1", 0, 0, 10, "fire", 5, 10000, 0)
        world.add_zone("z2", 0, 0, 10, "fire", 8, 10000, 0)
        world.add_unit("u1", 0, 0)
        self.assertEqual(world.tick(1000), {"u1": 8})

    def test_same_kind_max_regardless_of_add_order(self):
        world = field()
        world.add_zone("z1", 0, 0, 10, "fire", 8, 10000, 0)
        world.add_zone("z2", 0, 0, 10, "fire", 5, 10000, 0)
        world.add_unit("u1", 0, 0)
        self.assertEqual(world.tick(1000), {"u1": 8})

    def test_different_kinds_each_settle_once(self):
        world = field()
        world.add_zone("z1", 0, 0, 10, "fire", 5, 10000, 0)
        world.add_zone("z2", 0, 0, 10, "ice", 3, 10000, 0)
        world.add_unit("u1", 0, 0)
        self.assertEqual(world.tick(1000), {"u1": 8})

    def test_mixed_kinds_dedup_per_kind(self):
        world = field()
        world.add_zone("z1", 0, 0, 10, "fire", 5, 10000, 0)
        world.add_zone("z2", 0, 0, 10, "fire", 8, 10000, 0)
        world.add_zone("z3", 0, 0, 10, "ice", 3, 10000, 0)
        world.add_zone("z4", 0, 0, 10, "ice", 2, 10000, 0)
        world.add_unit("u1", 0, 0)
        self.assertEqual(world.tick(1000), {"u1": 11})


class ExpireTest(unittest.TestCase):
    def test_expired_zone_deals_no_damage(self):
        world = field()
        world.add_zone("z1", 0, 0, 10, "fire", 5, 500, 0)
        world.add_unit("u1", 0, 0)
        self.assertEqual(world.tick(2000), {})

    def test_zone_inactive_once_duration_reached(self):
        world = field(tick_ms=500)
        world.add_zone("z1", 0, 0, 10, "fire", 5, 1000, 0)
        world.add_unit("u1", 0, 0)
        self.assertEqual(world.tick(500), {"u1": 5})
        self.assertEqual(world.tick(1000), {})

    def test_expired_zone_is_cleaned_up(self):
        world = field()
        world.add_zone("z1", 0, 0, 10, "fire", 5, 500, 0)
        world.tick(1000)
        self.assertEqual(world.zone_count(), 0)

    def test_live_zone_unaffected_by_expired_sibling(self):
        world = field(tick_ms=500)
        world.add_zone("z1", 0, 0, 10, "fire", 5, 500, 0)
        world.add_zone("z2", 0, 0, 10, "fire", 8, 10000, 0)
        world.add_unit("u1", 0, 0)
        self.assertEqual(world.tick(500), {"u1": 8})
        self.assertEqual(world.tick(1000), {"u1": 8})
        self.assertEqual(world.zone_count(), 1)


class InvariantTest(unittest.TestCase):
    def test_per_unit_damage_never_exceeds_kind_maximum(self):
        world = field()
        for index, damage in enumerate((5, 8, 3, 6)):
            world.add_zone("z%d" % index, index, 0, 10, "fire", damage, 10000, 0)
        world.add_unit("u1", 0, 0)
        result = world.tick(1000)
        self.assertLessEqual(result["u1"], 8)
        self.assertEqual(result["u1"], 8)

    def test_same_sequence_replayed_gives_same_results(self):
        def run():
            world = Field(tick_ms=100)
            world.add_zone("z1", 0, 0, 10, "fire", 5, 1000, 0)
            world.add_zone("z2", 3, 0, 10, "fire", 8, 1000, 0)
            world.add_zone("z3", 0, 0, 5, "ice", 4, 1000, 0)
            world.add_unit("u1", 0, 0)
            world.add_unit("u2", 20, 0)
            results = []
            for now in range(0, 2000, 50):
                world.move("u1", now / 1000.0, 0)
                results.append(world.tick(now))
            return results

        self.assertEqual(run(), run())

    def test_idle_settles_repeat_same_result_without_rescan(self):
        world = field(tick_ms=1)
        world.add_zone("z1", 0, 0, 10, "fire", 5, 100000, 0)
        world.add_unit("u1", 0, 0)
        self.assertEqual(world.tick(0), {"u1": 5})
        scanned_after_first = world.scanned_count()
        for now in range(1, 100):
            self.assertEqual(world.tick(now), {"u1": 5})
        self.assertEqual(world.scanned_count(), scanned_after_first)


class ScanCostTest(unittest.TestCase):
    def test_scanned_does_not_grow_with_zone_count(self):
        world = Field(tick_ms=1)
        for index in range(3000):
            world.add_zone("z-%d" % index, index, 0, 5, "fire", 1, 100000, 0)
        world.add_unit("u1", 0, 0)
        for index in range(3000):
            world.tick(1000 + index)
        self.assertLessEqual(world.scanned_count(), 6000)

    def test_scanned_not_proportional_to_zone_times_unit(self):
        world = Field(tick_ms=1)
        for index in range(1000):
            world.add_zone("z-%d" % index, 10000 + index * 10, 0, 5, "fire", 1, 100000, 0)
        for index in range(100):
            world.add_unit("u-%d" % index, 0, index * 10)
        world.tick(1000)
        self.assertLess(world.scanned_count(), 1000 * 100)


if __name__ == "__main__":
    unittest.main()
