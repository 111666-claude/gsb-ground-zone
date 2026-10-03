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
