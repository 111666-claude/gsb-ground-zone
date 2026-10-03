"""持续地面区域：进入判定、周期结算、同类去重与到期清理。

缺陷：边界用严格小于、到期不清理、同一时刻重复结算、同类别区域重复累加、
每次结算扫描全部区域乘全部单位。
"""

import math


class Field:
    """地面效果场。"""

    def __init__(self, tick_ms):
        self.tick_ms = tick_ms
        self.zones = {}
        self.units = {}
        self.last_settle = None
        self.scanned = 0

    def add_zone(self, zone_id, x, y, radius, kind, damage, duration_ms, now_ms):
        self.zones[zone_id] = {"id": zone_id, "x": x, "y": y, "radius": radius,
                               "kind": kind, "damage": damage,
                               "until": now_ms + duration_ms}

    def add_unit(self, unit_id, x, y):
        self.units[unit_id] = {"id": unit_id, "x": x, "y": y}

    def move(self, unit_id, x, y):
        if unit_id in self.units:
            self.units[unit_id]["x"] = x
            self.units[unit_id]["y"] = y

    def tick(self, now_ms):
        """结算一次，返回 {单位: 本次伤害}。"""
        self.scanned += len(self.zones) * len(self.units)
        out = {}
        for zone in self.zones.values():
            for unit_id, unit in self.units.items():
                distance = math.hypot(unit["x"] - zone["x"], unit["y"] - zone["y"])
                if distance < zone["radius"]:
                    out[unit_id] = out.get(unit_id, 0) + zone["damage"]
        self.last_settle = now_ms
        return out

    def zone_count(self):
        return len(self.zones)

    def scanned_count(self):
        return self.scanned
