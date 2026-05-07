"""Voltage domain 与 power switch cell 边界。"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Set

from .grid import Grid
from .types import PowerSwitchNetworkType, Rect, _name, _not_implemented

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
        grid.setDomain(self)
        self.grids.append(grid)

    def resetGrids(self) -> None:
        for grid in self.grids:
            grid.resetShapes()

    def clearGrids(self) -> None:
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
        if self.power is None and self.switched_power is None:
            raise ValueError(f"voltage domain {self.name!r} has no power net")
        if self.ground is None:
            raise ValueError(f"voltage domain {self.name!r} has no ground net")

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


