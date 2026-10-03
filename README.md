# ground-zone

持续地面区域：进入判定、周期结算、同类去重与到期清理，只用 Python 标准库。

```
python3 -m zones.cli --sample edge
python3 -m zones.cli --sample expire
python3 -m zones.cli --sample idem
python3 -m zones.cli --sample overlap
python3 -m zones.cli --sample scan
python3 -m unittest discover -s tests -v
```

## 口径（README 为准）

- **进入判定**：单位与区域中心的距离不超过半径就算站在区域里，正好等于半径算进入。
- **周期结算**：`tick(now_ms)` 只在距上次结算满 `tick_ms` 时结算一次；
  同一时刻重复调用返回空结果。
- **同类去重**：同一单位在同一时刻被多个区域覆盖时，不同 `kind` 各结算一次，
  同一个 `kind` 只取伤害最高的那个区域，不累加。
- **到期清理**：区域存在时间达到 `duration_ms` 后不再结算。
- **不变量**：结算结果里每个单位每种类别的伤害不超过该类别的最大区域伤害；
  同一串移动与结算序列重复执行结果相同。
- **查询代价**：结算不许扫描全部区域乘全部单位，`scanned_count`
  不随区域数线性增长。
- **规模**：1 万个区域、1 万个单位、每秒 10 万次结算，单次摊还 O(覆盖到的单位数)。

## 输出契约（不改格式）

```
damage=..
second=..
scanned=..
```

## 目录

```
zones/core.py   进入、周期、去重与到期
zones/cli.py    命令行入口
tests/          unittest 用例
```
