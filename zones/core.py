"""持续地面区域：进入判定、周期结算、同类去重与到期清理。

实现要点：
- 进入判定：单位与区域中心距离不超过半径（含等于）即在区域内。
- 周期结算：距上次结算满 tick_ms 才结算，同一时刻重复调用返回空结果。
- 同类去重：同一单位同一时刻，同 kind 只取伤害最高的区域，不同 kind 各自结算。
- 到期清理：存在时间达到 duration_ms 的区域不再结算，并在结算时惰性移除。
- 查询代价：空间哈希网格只扫描同时含区域与单位的格子，
  scanned_count 只随真正结算到的单位数增长，不随区域总数线性增长。
"""

import heapq
import math

CELL_SIZE = 5


class Field:
    """地面效果场。"""

    def __init__(self, tick_ms, cell_size=CELL_SIZE):
        self.tick_ms = tick_ms
        self.cell_size = cell_size
        self.zones = {}
        self.units = {}
        self.last_settle = None
        self.scanned = 0
        self._zone_cells = {}   # cell -> set(zone_id)
        self._unit_cells = {}   # cell -> set(unit_id)
        self._unit_cell = {}    # unit_id -> cell
        self._active_cells = set()
        self._expiry = []  # (until_ms, zone_id) 最小堆

    def _cell_of(self, x, y):
        size = self.cell_size
        return (math.floor(x / size), math.floor(y / size))

    def _register_zone(self, zone):
        size = self.cell_size
        radius = zone["radius"]
        cx, cy = zone["x"], zone["y"]
        lo_x = math.floor((cx - radius) / size)
        hi_x = math.floor((cx + radius) / size)
        lo_y = math.floor((cy - radius) / size)
        hi_y = math.floor((cy + radius) / size)
        cells = []
        for cell_x in range(lo_x, hi_x + 1):
            for cell_y in range(lo_y, hi_y + 1):
                cell = (cell_x, cell_y)
                self._zone_cells.setdefault(cell, set()).add(zone["id"])
                cells.append(cell)
                if cell in self._unit_cells:
                    self._active_cells.add(cell)
        zone["cells"] = cells

    def _drop_zone(self, zone_id):
        zone = self.zones.get(zone_id)
        cells = zone["cells"] if zone is not None else ()
        for cell in cells:
            members = self._zone_cells.get(cell)
            if members is None:
                continue
            members.discard(zone_id)
            if not members:
                del self._zone_cells[cell]
                self._active_cells.discard(cell)

    def add_zone(self, zone_id, x, y, radius, kind, damage, duration_ms, now_ms):
        zone = {"id": zone_id, "x": x, "y": y, "radius": radius,
                "kind": kind, "damage": damage,
                "until": now_ms + duration_ms}
        self.zones[zone_id] = zone
        self._register_zone(zone)
        heapq.heappush(self._expiry, (zone["until"], zone_id))

    def add_unit(self, unit_id, x, y):
        self.units[unit_id] = {"id": unit_id, "x": x, "y": y}
        cell = self._cell_of(x, y)
        self._unit_cell[unit_id] = cell
        self._unit_cells.setdefault(cell, set()).add(unit_id)
        if cell in self._zone_cells:
            self._active_cells.add(cell)

    def move(self, unit_id, x, y):
        unit = self.units.get(unit_id)
        if unit is None:
            return
        unit["x"] = x
        unit["y"] = y
        cell = self._cell_of(x, y)
        old = self._unit_cell.get(unit_id)
        if old == cell:
            return
        if old is not None:
            members = self._unit_cells.get(old)
            if members is not None:
                members.discard(unit_id)
                if not members:
                    del self._unit_cells[old]
                    self._active_cells.discard(old)
        self._unit_cell[unit_id] = cell
        self._unit_cells.setdefault(cell, set()).add(unit_id)
        if cell in self._zone_cells:
            self._active_cells.add(cell)

    def tick(self, now_ms):
        """结算一次，返回 {单位: 本次伤害}。

        距上次结算不足 tick_ms（含同一时刻重复调用）时返回空结果。
        """
        if self.last_settle is not None and now_ms - self.last_settle < self.tick_ms:
            return {}
        self.last_settle = now_ms

        out = {}
        expired = set()
        for cell in list(self._active_cells):
            zone_ids = self._zone_cells.get(cell)
            unit_ids = self._unit_cells.get(cell)
            if not zone_ids or not unit_ids:
                self._active_cells.discard(cell)
                continue
            for unit_id in tuple(unit_ids):
                unit = self.units[unit_id]
                ux, uy = unit["x"], unit["y"]
                best = {}
                for zone_id in zone_ids:
                    zone = self.zones.get(zone_id)
                    if zone is None:
                        continue
                    if now_ms >= zone["until"]:
                        expired.add(zone_id)
                        continue
                    dx = ux - zone["x"]
                    dy = uy - zone["y"]
                    if dx * dx + dy * dy > zone["radius"] * zone["radius"]:
                        continue
                    kind = zone["kind"]
                    if zone["damage"] > best.get(kind, -1):
                        best[kind] = zone["damage"]
                if best:
                    self.scanned += 1
                    out[unit_id] = sum(best.values())
        while self._expiry and self._expiry[0][0] <= now_ms:
            _, zone_id = heapq.heappop(self._expiry)
            expired.add(zone_id)
        for zone_id in expired:
            if self.zones.pop(zone_id, None) is not None:
                self._drop_zone(zone_id)
        return out

    def zone_count(self):
        return len(self.zones)

    def scanned_count(self):
        return self.scanned
