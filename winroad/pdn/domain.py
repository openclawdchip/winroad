"""Voltage domain 与 power switch cell 边界。"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set

from .grid import Grid
from .types import PdnIssue, PowerSwitchNetworkType, Rect, _name, _normalize_power_switch_network, _not_implemented

@dataclass
class VoltageDomain:
    """对应 `pdn::VoltageDomain`，维护 power/ground/secondary 与 grids。"""

    pdngen: "PdnGen"
    name: str
    block: Any = None
    power: Any = None
    ground: Any = None
    secondary: List[Any] = field(default_factory=list)
    region: Any = None
    logger: Any = None
    switched_power: Any = None
    grids: List[Grid] = field(default_factory=list)

    def __post_init__(self) -> None:
        if not self.name:
            raise ValueError("voltage domain name is required")

    def getName(self) -> str:
        return self.name

    def getPower(self) -> Any:
        return self.switched_power if self.switched_power is not None else self.power

    def getGround(self) -> Any:
        return self.ground

    def getAlwaysOnPower(self) -> Any:
        return self.power

    def getSwitchedPower(self) -> Any:
        return self.switched_power

    def setSwitchedPower(self, switched_power: Any) -> None:
        self.switched_power = switched_power

    def hasSwitchedPower(self) -> bool:
        return self.switched_power is not None

    def hasRegion(self) -> bool:
        return self.region is not None

    def getNets(self, start_with_power: bool = True) -> List[Any]:
        power_nets = [net for net in [self.getPower(), *self.secondary] if net is not None]
        ground_nets = [self.ground] if self.ground is not None else []
        return [*power_nets, *ground_nets] if start_with_power else [*ground_nets, *power_nets]

    def addGrid(self, grid: Grid) -> None:
        if grid is None:
            raise ValueError("cannot add an empty grid")
        duplicate = self.getGridByName(grid.getLongName()) or self.getGridByName(grid.getName())
        if duplicate is not None and duplicate is not grid:
            raise ValueError(f"grid {grid.getLongName()!r} already exists in voltage domain {self.name!r}")
        grid.setDomain(self)
        if grid not in self.grids:
            self.grids.append(grid)

    def resetGrids(self) -> None:
        for grid in self.grids:
            grid.resetShapes()

    def clearGrids(self) -> None:
        for grid in self.grids:
            grid.resetShapes()
        self.grids.clear()

    def removeGrid(self, grid: Grid) -> None:
        if grid in self.grids:
            self.grids.remove(grid)

    def getGrids(self) -> List[Grid]:
        return list(self.grids)

    def findGrid(self, name: str) -> List[Grid]:
        return [grid for grid in self.grids if grid.getName() == name or grid.getLongName() == name]

    def getGridByName(self, name: str) -> Optional[Grid]:
        matches = self.findGrid(name)
        return matches[0] if matches else None

    def getDomainArea(self) -> Rect:
        _not_implemented("VoltageDomain::getDomainArea")

    def getRows(self) -> List[Any]:
        _not_implemented("VoltageDomain::getRows")

    def checkSetup(self) -> None:
        issues = [issue for issue in self.collectSetupIssues() if issue.severity == "error"]
        if issues:
            raise ValueError("; ".join(f"{issue.path}: {issue.message}" for issue in issues))

    def collectSetupIssues(self, path: str = "") -> List[PdnIssue]:
        issues: List[PdnIssue] = []
        base = path or f"domain:{self.name}"
        if self.power is None and self.switched_power is None:
            issues.append(PdnIssue(base, f"voltage domain {self.name!r} has no power net"))
        if self.ground is None:
            issues.append(PdnIssue(base, f"voltage domain {self.name!r} has no ground net"))
        seen_grids: Set[str] = set()
        for index, grid in enumerate(self.grids):
            grid_path = f"{base}/grid[{index}]/{grid.getLongName()}"
            if grid.getLongName() in seen_grids:
                issues.append(PdnIssue(grid_path, f"duplicate grid {grid.getLongName()!r} in voltage domain {self.name!r}"))
            seen_grids.add(grid.getLongName())
            if grid.getDomain() is not self:
                issues.append(PdnIssue(grid_path, f"grid {grid.getLongName()!r} is attached to the wrong voltage domain"))
            issues.extend(grid.collectSetupIssues(grid_path))
        return issues

    def report(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "power": _name(self.power),
            "switched_power": _name(self.switched_power) if self.switched_power is not None else None,
            "ground": _name(self.ground),
            "secondary": [_name(net) for net in self.secondary],
            "region": _name(self.region) if self.region is not None else None,
            "grids": [grid.report() for grid in self.grids],
        }

    def summary(self) -> Dict[str, Any]:
        grid_summaries = [grid.summary() for grid in self.grids]
        failed_by_reason: Dict[str, int] = {}
        for grid in grid_summaries:
            for reason, count in grid["failed_vias_by_reason"].items():
                failed_by_reason[reason] = failed_by_reason.get(reason, 0) + count
        return {
            "name": self.name,
            "grid_count": len(self.grids),
            "shape_count": sum(grid["shape_count"] for grid in grid_summaries),
            "via_count": sum(grid["via_count"] for grid in grid_summaries),
            "failed_via_count": sum(grid["failed_via_count"] for grid in grid_summaries),
            "failed_vias_by_reason": failed_by_reason,
            "grids": grid_summaries,
        }


@dataclass
class PowerCell:
    """对应 `pdn::PowerCell`，保存 power switch cell 的 master/pin 映射。"""

    logger: Any
    master: Any
    control: Any
    acknowledge: Any
    switched_power: Any
    alwayson_power: Any
    ground: Any
    alwayson_power_positions: Set[int] = field(default_factory=set)

    def getName(self) -> str:
        return _name(self.master)

    def hasAcknowledge(self) -> bool:
        return self.acknowledge is not None

    def collectSetupIssues(self, path: str = "") -> List[PdnIssue]:
        issues: List[PdnIssue] = []
        base = path or f"power_cell:{self.getName()}"
        if self.master is None:
            issues.append(PdnIssue(base, "power switch cell master is required"))
        for field_name, value in (
            ("control", self.control),
            ("switched_power", self.switched_power),
            ("alwayson_power", self.alwayson_power),
            ("ground", self.ground),
        ):
            if value is None:
                issues.append(PdnIssue(base, f"power switch cell {field_name} pin/net is required"))
        return issues

    def appliesToRow(self, row: Any) -> bool:
        _not_implemented("PowerCell::appliesToRow")

    def populateAlwaysOnPinPositions(self, site_width: int) -> None:
        _not_implemented("PowerCell::populateAlwaysOnPinPositions")

    def report(self) -> Dict[str, Any]:
        return {
            "name": self.getName(),
            "control": _name(self.control),
            "acknowledge": _name(self.acknowledge) if self.acknowledge is not None else None,
            "switched_power": _name(self.switched_power),
            "alwayson_power": _name(self.alwayson_power),
            "ground": _name(self.ground),
        }


@dataclass
class GridSwitchedPower:
    """对应 `pdn::GridSwitchedPower`。"""

    grid: Grid
    cell: PowerCell
    control: Any
    network: PowerSwitchNetworkType

    def __post_init__(self) -> None:
        if self.grid is None:
            raise ValueError("switched power grid requires a grid")
        if self.cell is None:
            raise ValueError("switched power grid requires a power cell")
        self.network = _normalize_power_switch_network(self.network)

    def build(self) -> None:
        _not_implemented("GridSwitchedPower::build")

    def ripup(self) -> None:
        _not_implemented("GridSwitchedPower::ripup")

    def report(self) -> Dict[str, Any]:
        return {
            "grid": self.grid.getName(),
            "cell": self.cell.getName(),
            "control": _name(self.control),
            "network": self.network.value,
        }

    def collectSetupIssues(self, path: str = "") -> List[PdnIssue]:
        issues: List[PdnIssue] = []
        base = path or f"switched_power:{self.grid.getLongName()}"
        if self.grid is None:
            issues.append(PdnIssue(base, "switched power object has no grid"))
        if self.cell is None:
            issues.append(PdnIssue(base, "switched power object has no power cell"))
        elif self.control is None:
            issues.append(PdnIssue(base, "switched power control net is required"))
        return issues
