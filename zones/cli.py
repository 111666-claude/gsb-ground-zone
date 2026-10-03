"""命令行入口：跑地面区域样例。"""

import argparse

from .core import Field


def build_parser():
    parser = argparse.ArgumentParser(prog="ground-zone", description="持续地面区域")
    parser.add_argument("--sample", default="edge",
                        help="edge / expire / idem / overlap / scan")
    return parser


def main(argv=None):
    args = build_parser().parse_args(argv)
    if args.sample == "edge":
        field = Field(tick_ms=1000)
        field.add_zone("z1", 0, 0, 10, "fire", 5, 10000, 0)
        field.add_unit("u1", 10, 0)
        print("damage=%d" % field.tick(1000).get("u1", 0))
    elif args.sample == "expire":
        field = Field(tick_ms=1000)
        field.add_zone("z1", 0, 0, 10, "fire", 5, 500, 0)
        field.add_unit("u1", 0, 0)
        print("damage=%d" % field.tick(2000).get("u1", 0))
    elif args.sample == "idem":
        field = Field(tick_ms=1000)
        field.add_zone("z1", 0, 0, 10, "fire", 5, 10000, 0)
        field.add_unit("u1", 0, 0)
        field.tick(1000)
        print("second=%d" % field.tick(1000).get("u1", 0))
    elif args.sample == "overlap":
        field = Field(tick_ms=1000)
        field.add_zone("z1", 0, 0, 10, "fire", 5, 10000, 0)
        field.add_zone("z2", 0, 0, 10, "fire", 8, 10000, 0)
        field.add_unit("u1", 0, 0)
        print("damage=%d" % field.tick(1000).get("u1", 0))
    elif args.sample == "scan":
        field = Field(tick_ms=1)
        for index in range(3000):
            field.add_zone("z-%d" % index, index, 0, 5, "fire", 1, 100000, 0)
        field.add_unit("u1", 0, 0)
        for index in range(3000):
            field.tick(1000 + index)
        print("scanned=%d" % field.scanned_count())
    else:
        raise SystemExit("需要 --sample edge|expire|idem|overlap|scan")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
