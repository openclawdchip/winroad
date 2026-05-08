"""PDN debug renderer 占位边界。"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Sequence

from .grid import Grid
from .types import PdnIssue, _name, _not_implemented

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
        self.grids = []
        for grid in grids:
            self.addGrid(grid)

    def addGrid(self, grid: Grid) -> None:
        if grid is None:
            raise ValueError("renderer grid cannot be None")
        if grid not in self.grids:
            self.grids.append(grid)

    def removeGrid(self, grid: Grid) -> None:
        if grid in self.grids:
            self.grids.remove(grid)
        if grid in self.selected:
            self.selected.remove(grid)

    def select(self, item: Any) -> None:
        if item not in self.selected:
            self.selected.append(item)

    def clear(self) -> None:
        self.selected.clear()

    def selectionSnapshot(self) -> List[Dict[str, Any]]:
        return [{"type": type(item).__name__, "name": _name(item)} for item in self.selected]

    def collectSetupIssues(self, path: str = "renderer") -> List[PdnIssue]:
        issues: List[PdnIssue] = []
        if not self.enabled:
            return issues
        grid_names = {grid.getLongName() for grid in self.grids}
        for index, item in enumerate(self.selected):
            if isinstance(item, Grid) and item.getLongName() not in grid_names:
                issues.append(PdnIssue(f"{path}/selected[{index}]", f"selected grid {item.getLongName()!r} is not registered in renderer grids", severity="warning"))
        return issues

    def snapshot(self) -> Dict[str, Any]:
        return {
            "enabled": self.enabled,
            "block": _name(self.block) if self.block is not None else None,
            "grids": [grid.getLongName() for grid in self.grids],
            "selected": self.selectionSnapshot(),
        }

    def report(self) -> Dict[str, Any]:
        return {
            "enabled": self.enabled,
            "block": _name(self.block) if self.block is not None else None,
            "grids": [grid.getLongName() for grid in self.grids],
            "selected_count": len(self.selected),
            "selected": [_name(item) for item in self.selected],
            "selected_snapshot": self.selectionSnapshot(),
        }

    def redraw(self) -> None:
        _not_implemented("PDNRenderer::redraw")
