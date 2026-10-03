"""持续地面区域：进入判定、周期结算、同类去重与到期清理。

实现要点：
- 进入判定：单位与区域中心距离 <= 半径（正好等于半径算进入）。
- 周期结算：距上次结算满 tick_ms 才结算一次，否则返回空结果。
- 同类去重：同一单位同一 kind 只取伤害最高的区域，不同 kind 各算一次。
- 到期清理：now_ms >= until 的区域不再结算，结算时按到期堆惰性清除。
- 查询代价：区域按包围盒、单位按位置挂进同一张空间网格
  （格子边长 >= 最大区域半径，保证覆盖单位的区域一定落在单位所在格），
  结算只遍历“既有区域又有单位”的活跃格与刚移动过的单位；
  无变化时直接复用上次结果，单次摊还 O(覆盖到的单位数)，
  scanned_count 只统计真正发生的距离判定次数。
"""

import heapq
import math


class Field:
    """地面效果场。"""

    def __init__(self, tick_ms):
        self.tick_ms = tick_ms
        self.zones = {}
        self.units = {}
        self.last_settle = None
        self.scanned = 0
        self._cell = 1.0
        self._grid = {}
        self._zone_cells = {}
        self._unit_cells = {}
        self._unit_cell_of = {}
        self._expiry = []
        self._generation = 0
        self._cover = {}
        self._values = {}
        self._out = {}
        self._changed = set()
        self._full_dirty = True
        self._dirty = True

    def add_zone(self, zone_id, x, y, radius, kind, damage, duration_ms, now_ms):
        if zone_id in self.zones:
            self._remove_zone(zone_id)
        zone = {"id": zone_id, "x": x, "y": y, "radius": radius,
                "kind": kind, "damage": damage,
                "until": now_ms + duration_ms}
        self.zones[zone_id] = zone
        if radius > self._cell:
            self._cell = float(radius)
            self._rebuild_grid()
        self._insert_zone(zone)
        heapq.heappush(self._expiry, (zone["until"], zone_id))
        self._generation += 1
        self._full_dirty = True
        self._dirty = True

    def add_unit(self, unit_id, x, y):
        if unit_id in self.units:
            self._unplace_unit(unit_id)
        self.units[unit_id] = {"id": unit_id, "x": x, "y": y}
        self._place_unit(unit_id, x, y)
        self._changed.add(unit_id)
        self._dirty = True

    def move(self, unit_id, x, y):
        unit = self.units.get(unit_id)
        if unit is None:
            return
        if unit["x"] == x and unit["y"] == y:
            return
        self._unplace_unit(unit_id)
        unit["x"] = x
        unit["y"] = y
        self._place_unit(unit_id, x, y)
        self._changed.add(unit_id)
        self._dirty = True

    def tick(self, now_ms):
        """结算一次，返回 {单位: 本次伤害}；未到周期返回空结果。"""
        if self.last_settle is not None and now_ms - self.last_settle < self.tick_ms:
            return {}
        self.last_settle = now_ms
        self._purge(now_ms)
        if not self._dirty:
            return self._out
        if self._full_dirty:
            self._changed.clear()
            cells = set(self._grid)
            for unit_id in self._values:
                key = self._unit_cell_of.get(unit_id)
                if key is not None:
                    cells.add(key)
            self._settle_cells(cells)
        else:
            changed = self._changed
            self._changed = set()
            for unit_id in changed:
                self._settle_unit(unit_id)
            cells = set()
            for unit_id in changed:
                key = self._unit_cell_of.get(unit_id)
                if key is not None and key in self._grid:
                    cells.add(key)
            self._settle_cells(cells, skip=changed)
        self._full_dirty = False
        self._dirty = False
        return self._out

    def zone_count(self):
        return len(self.zones)

    def scanned_count(self):
        return self.scanned

    def _settle_cells(self, cells, skip=()):
        for key in cells:
            for unit_id in self._unit_cells.get(key, ()):
                if unit_id not in skip:
                    self._settle_unit(unit_id)

    def _settle_unit(self, unit_id):
        unit = self.units.get(unit_id)
        if unit is None:
            self._values.pop(unit_id, None)
            self._out.pop(unit_id, None)
            return
        per_kind = {}
        for zone_id in self._covering(unit_id, unit):
            zone = self.zones.get(zone_id)
            if zone is None:
                continue
            kind = zone["kind"]
            damage = zone["damage"]
            if kind not in per_kind or damage > per_kind[kind]:
                per_kind[kind] = damage
        if per_kind:
            value = sum(per_kind.values())
            self._values[unit_id] = value
            self._out[unit_id] = value
        else:
            self._values.pop(unit_id, None)
            self._out.pop(unit_id, None)

    def _covering(self, unit_id, unit):
        cache = self._cover.get(unit_id)
        if (cache is not None and cache[0] == unit["x"]
                and cache[1] == unit["y"] and cache[2] == self._generation):
            return cache[3]
        key = (int(math.floor(unit["x"] / self._cell)),
               int(math.floor(unit["y"] / self._cell)))
        covering = []
        for zone_id in self._grid.get(key, ()):
            zone = self.zones.get(zone_id)
            if zone is None:
                continue
            self.scanned += 1
            distance = math.hypot(unit["x"] - zone["x"], unit["y"] - zone["y"])
            if distance <= zone["radius"]:
                covering.append(zone_id)
        self._cover[unit_id] = (unit["x"], unit["y"], self._generation, covering)
        return covering

    def _rebuild_grid(self):
        self._grid = {}
        self._zone_cells = {}
        for zone in self.zones.values():
            self._insert_zone(zone)
        self._unit_cells = {}
        self._unit_cell_of = {}
        for unit_id, unit in self.units.items():
            self._place_unit(unit_id, unit["x"], unit["y"])

    def _insert_zone(self, zone):
        cell = self._cell
        radius = zone["radius"]
        x0 = int(math.floor((zone["x"] - radius) / cell))
        x1 = int(math.floor((zone["x"] + radius) / cell))
        y0 = int(math.floor((zone["y"] - radius) / cell))
        y1 = int(math.floor((zone["y"] + radius) / cell))
        cells = [(cx, cy) for cx in range(x0, x1 + 1) for cy in range(y0, y1 + 1)]
        for key in cells:
            bucket = self._grid.get(key)
            if bucket is None:
                bucket = set()
                self._grid[key] = bucket
            bucket.add(zone["id"])
        self._zone_cells[zone["id"]] = cells

    def _remove_zone(self, zone_id):
        if zone_id not in self.zones:
            return
        del self.zones[zone_id]
        for key in self._zone_cells.pop(zone_id, ()):
            bucket = self._grid.get(key)
            if bucket is not None:
                bucket.discard(zone_id)
                if not bucket:
                    del self._grid[key]

    def _place_unit(self, unit_id, x, y):
        key = (int(math.floor(x / self._cell)),
               int(math.floor(y / self._cell)))
        bucket = self._unit_cells.get(key)
        if bucket is None:
            bucket = set()
            self._unit_cells[key] = bucket
        bucket.add(unit_id)
        self._unit_cell_of[unit_id] = key

    def _unplace_unit(self, unit_id):
        key = self._unit_cell_of.pop(unit_id, None)
        if key is None:
            return
        bucket = self._unit_cells.get(key)
        if bucket is not None:
            bucket.discard(unit_id)
            if not bucket:
                del self._unit_cells[key]

    def _purge(self, now_ms):
        while self._expiry and self._expiry[0][0] <= now_ms:
            _, zone_id = heapq.heappop(self._expiry)
            zone = self.zones.get(zone_id)
            if zone is not None and zone["until"] <= now_ms:
                self._remove_zone(zone_id)
                self._generation += 1
                self._full_dirty = True
                self._dirty = True
