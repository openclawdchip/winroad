"""PDN debug renderer 占位边界。"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Sequence

from .grid import Grid
from .types import _name, _not_implemented

@dataclass
class PDNRenderer:
    """对应 `pdn::PDNRenderer`，图形调试后端占位。"""

    enabled: bool = False
    block: Any = None
    logger: Any = None
    grids: List[Grid] = field(default_factory=list)
    selected: List[Any] = field(default_factory=list)

    def setBlock(self, block: Any) -> None:
        self.block = block

    def setLogger(self, logger: Any) -> None:
        self.logger = logger

    def setGrids(self, grids: Sequence[Grid]) -> None:
        self.grids = list(grids)

    def select(self, item: Any) -> None:
        self.selected.append(item)

    def clear(self) -> None:
        self.selected.clear()

    def report(self) -> Dict[str, Any]:
        return {
            "enabled": self.enabled,
            "block": _name(self.block) if self.block is not None else None,
            "grids": [grid.getLongName() for grid in self.grids],
            "selected_count": len(self.selected),
        }

    def redraw(self) -> None:
        _not_implemented("PDNRenderer::redraw")


