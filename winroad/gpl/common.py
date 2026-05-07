"""Shared helpers for the WinRoad gpl package."""

from __future__ import annotations

from typing import Any, List, Optional, Tuple

from ..odb import DbDatabase, DbInst, DbNet

Rect = Tuple[int, int, int, int]
Cluster = List[DbInst]
Clusters = List[Cluster]

def _area(rect: Rect) -> int:
    """矩形面积工具，坐标顺序与 OpenDB Rect 一致：lx, ly, ux, uy。"""

    lx, ly, ux, uy = rect
    return max(0, ux - lx) * max(0, uy - ly)


def _center(rect: Rect) -> Tuple[int, int]:
    """返回矩形中心。"""

    lx, ly, ux, uy = rect
    return (lx + ux) // 2, (ly + uy) // 2


def _get_block(db: Optional[DbDatabase]) -> Any:
    """兼容当前 WinRoad ODB 骨架，取得顶层 block。"""

    if db is None or db.chip is None:
        return None
    if hasattr(db.chip, "get_top_block"):
        return db.chip.get_top_block()
    top = getattr(db.chip, "top", None)
    return getattr(db.chip, "blocks", {}).get(top) if top is not None else None


def _iter_block_insts(block: Any) -> List[DbInst]:
    """以 OpenDB `block->getInsts()` 的语义遍历实例。"""

    if block is None:
        return []
    insts = getattr(block, "insts", {})
    if isinstance(insts, dict):
        return list(insts.values())
    return list(insts)


def _iter_block_nets(block: Any) -> List[DbNet]:
    """以 OpenDB `block->getNets()` 的语义遍历线网。"""

    if block is None:
        return []
    nets = getattr(block, "nets", {})
    if isinstance(nets, dict):
        return list(nets.values())
    return list(nets)


def _inst_rect(inst: DbInst) -> Rect:
    """从 DbInst 取得实例矩形；没有 bbox 时退化到原点零面积。"""

    if getattr(inst, "bbox", None) is not None:
        return inst.bbox  # type: ignore[return-value]
    return (inst.x, inst.y, inst.x, inst.y)


def _db_inst_set_origin(inst: DbInst, x: int, y: int) -> None:
    """兼容 DbInst 的 set_origin，同时保持 bbox 平移。"""

    old_x, old_y = inst.x, inst.y
    if getattr(inst, "bbox", None) is not None:
        lx, ly, ux, uy = inst.bbox  # type: ignore[misc]
        inst.bbox = (x, y, x + (ux - lx), y + (uy - ly))
    if hasattr(inst, "set_origin"):
        inst.set_origin(x, y)
    else:
        inst.x = x
        inst.y = y
    if getattr(inst, "bbox", None) is None and (old_x, old_y) != (x, y):
        inst.x = x
        inst.y = y


