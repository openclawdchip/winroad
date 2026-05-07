"""PDN grid 类型与 grid 级对象关系。"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Mapping, Optional, Sequence, Set

from .component import GridComponent, RepairChannelStraps, Rings, Straps
from .types import GridComponentType, GridType, Halo, PdnIssue, Rect, Shape, _name, _not_implemented, _validate_halo, _validate_rect
from .via import Connect, Via

@dataclass
class Grid:
    """对应 `pdn::Grid`，负责持有 ring/strap/connect 组件。"""

    domain: "VoltageDomain"
    name: str
    starts_with_power: bool = True
    generate_obstructions: List[Any] = field(default_factory=list)
    rings: List[Rings] = field(default_factory=list)
    straps: List[Straps] = field(default_factory=list)
    connect: List[Connect] = field(default_factory=list)
    pin_layers: Set[Any] = field(default_factory=set)
    allow_repair_channels: bool = False
    vias: List[Via] = field(default_factory=list)
    switched_power_cell: Optional["GridSwitchedPower"] = None

    def __post_init__(self) -> None:
        if self.domain is None:
            raise ValueError("grid requires a voltage domain")
        if not self.name:
            raise ValueError("grid name is required")

    def getName(self) -> str:
        return self.name

    def getLongName(self) -> str:
        return self.getName()

    def getDomain(self) -> "VoltageDomain":
        return self.domain

    def setDomain(self, domain: "VoltageDomain") -> None:
        if domain is None:
            raise ValueError("grid domain is required")
        self.domain = domain

    def type(self) -> GridType:
        raise NotImplementedError

    def addRing(self, ring: Rings) -> None:
        ring.setGrid(self)
        if ring not in self.rings:
            self.rings.append(ring)

    def addStrap(self, strap: Straps) -> None:
        strap.setGrid(self)
        if strap not in self.straps:
            self.straps.append(strap)

    def addConnect(self, connect: Connect) -> None:
        connect.setGrid(self)
        if connect not in self.connect:
            self.connect.append(connect)

    def removeStrap(self, strap: Straps) -> None:
        if strap in self.straps:
            self.straps.remove(strap)

    def setPinLayers(self, layers: Sequence[Any]) -> None:
        self.pin_layers = set(layers)

    def getPinLayers(self) -> Set[Any]:
        return set(self.pin_layers)

    def setAllowRepairChannels(self, allow: bool) -> None:
        self.allow_repair_channels = allow

    def getNets(self, starts_with_power: Optional[bool] = None) -> List[Any]:
        return self.domain.getNets(self.starts_with_power if starts_with_power is None else starts_with_power)

    def getRings(self) -> List[Rings]:
        return list(self.rings)

    def getStraps(self) -> List[Straps]:
        return list(self.straps)

    def getConnect(self) -> List[Connect]:
        return list(self.connect)

    def getGridComponents(self) -> List[GridComponent]:
        return [*self.rings, *self.straps]

    def getShapes(self) -> List[Shape]:
        return [shape for component in self.getGridComponents() for shape in component.getShapes()]

    def getVias(self) -> List[Via]:
        vias = list(self.vias)
        for connect in self.connect:
            for via in connect.getVias():
                if via not in vias:
                    vias.append(via)
        return vias

    def findComponent(self, component_type: Optional[GridComponentType] = None, layer: Any = None) -> List[GridComponent]:
        components = self.getGridComponents()
        if component_type is not None:
            components = [component for component in components if component.type() == component_type]
        if layer is not None:
            components = [
                component
                for component in components
                if (isinstance(component, Rings) and layer in component.getLayers())
                or (isinstance(component, Straps) and component.layer == layer)
            ]
        return components

    def findConnect(self, layer0: Any = None, layer1: Any = None) -> List[Connect]:
        result = self.connect
        if layer0 is not None and layer1 is None:
            result = [connect for connect in result if connect.layer0 == layer0 or connect.layer1 == layer0]
        if layer1 is not None:
            if layer0 is None:
                result = [connect for connect in result if connect.layer0 == layer1 or connect.layer1 == layer1]
            else:
                result = [connect for connect in result if {connect.layer0, connect.layer1} == {layer0, layer1}]
        return list(result)

    def findShapeContainingRect(self, rect: Rect) -> List[Shape]:
        """按已有 runtime shape 查找覆盖给定矩形的纯状态对象。

        这里不触发几何生成，只检查导入或测试手工挂上的 shape，等价于 C++ 查询
        已生成网格后的只读视图。
        """

        lx, ly, ux, uy = _validate_rect(rect, "query rect")
        return [
            shape
            for shape in self.getShapes()
            if shape.rect[0] <= lx and shape.rect[1] <= ly and shape.rect[2] >= ux and shape.rect[3] >= uy
        ]

    def makeShapes(self, global_shapes: Any, obstructions: Any) -> None:
        _not_implemented("Grid::makeShapes")

    def makeVias(self, global_shapes: Any, obstructions: Any, local_obstructions: Any = None) -> None:
        _not_implemented("Grid::makeVias")

    def build(self, global_shapes: Any = None, obstructions: Any = None, local_obstructions: Any = None) -> None:
        self.checkSetup()
        self.makeShapes(global_shapes, obstructions)
        self.makeVias(global_shapes, obstructions, local_obstructions)

    def writeToDb(self, net_map: Mapping[Any, Any], do_pins: bool, obstructions: Any) -> Dict[Shape, List[Any]]:
        _not_implemented("Grid::writeToDb")

    def resetShapes(self) -> None:
        for component in [*self.rings, *self.straps]:
            component.clearShapes()
        for connect in self.connect:
            connect.clearShapes()
        self.vias.clear()

    def ripup(self) -> None:
        self.resetShapes()

    def checkSetup(self) -> None:
        issues = self.collectSetupIssues()
        if issues:
            raise ValueError("; ".join(f"{issue.path}: {issue.message}" for issue in issues))

    def collectSetupIssues(self, path: str = "") -> List[PdnIssue]:
        issues: List[PdnIssue] = []
        base = path or f"grid:{self.getLongName()}"
        if self.domain is None:
            issues.append(PdnIssue(base, f"grid {self.name!r} has no voltage domain"))
        for index, component in enumerate(self.getGridComponents()):
            component_path = f"{base}/component[{index}]/{component.type().value}"
            if component.getGrid() is not self:
                issues.append(PdnIssue(component_path, f"component {component.type().value} is attached to the wrong grid"))
            issues.extend(component.collectSetupIssues(component_path))
        for index, connect in enumerate(self.connect):
            connect_path = f"{base}/connect[{index}]"
            if connect.getGrid() is not self:
                issues.append(PdnIssue(connect_path, f"connect {_name(connect.layer0)}->{_name(connect.layer1)} is attached to the wrong grid"))
            if connect.layer0 is None or connect.layer1 is None:
                issues.append(PdnIssue(connect_path, "connect requires both lower and upper layers"))
        return issues

    def report(self) -> Dict[str, Any]:
        return {
            "name": self.getLongName(),
            "type": self.type().value,
            "domain": self.domain.getName(),
            "starts_with_power": self.starts_with_power,
            "generate_obstructions": [_name(layer) for layer in self.generate_obstructions],
            "pin_layers": [_name(layer) for layer in self.pin_layers],
            "allow_repair_channels": self.allow_repair_channels,
            "rings": [ring.report() for ring in self.rings],
            "straps": [strap.report() for strap in self.straps],
            "connect": [connect.report() for connect in self.connect],
            "shape_count": len(self.getShapes()),
            "via_count": len(self.getVias()),
            "switched_power_cell": self.switched_power_cell.report() if self.switched_power_cell is not None else None,
        }

    def summary(self) -> Dict[str, Any]:
        failures = self.viaFailureReport(include_locations=False)
        return {
            "name": self.getLongName(),
            "type": self.type().value,
            "domain": self.domain.getName(),
            "ring_count": len(self.rings),
            "strap_count": len(self.straps),
            "connect_count": len(self.connect),
            "shape_count": len(self.getShapes()),
            "via_count": len(self.getVias()),
            "failed_via_count": failures["total"],
            "failed_vias_by_reason": failures["by_reason"],
            "component_count_by_type": {
                component_type.value: len(self.findComponent(component_type))
                for component_type in GridComponentType
            },
        }

    def viaFailureReport(self, include_locations: bool = True) -> Dict[str, Any]:
        reports = [connect.failedViaReport(include_locations=include_locations) for connect in self.connect]
        by_reason: Dict[str, int] = {}
        for report in reports:
            for reason, count in report["by_reason"].items():
                by_reason[reason] = by_reason.get(reason, 0) + count
        return {
            "grid": self.getLongName(),
            "total": sum(by_reason.values()),
            "by_reason": by_reason,
            "connects": reports,
        }


@dataclass
class CoreGrid(Grid):
    """对应 `pdn::CoreGrid`。"""

    def type(self) -> GridType:
        return GridType.CORE

    def setupDirectConnect(self, connect_pad_layers: Sequence[Any]) -> None:
        _not_implemented("CoreGrid::setupDirectConnect")


@dataclass
class InstanceGrid(Grid):
    """对应 `pdn::InstanceGrid`，服务 macro/bump/instance grid。"""

    inst: Any = None
    halos: Halo = (0, 0, 0, 0)
    grid_to_boundary: bool = False
    replaceable: bool = False

    def __post_init__(self) -> None:
        super().__post_init__()
        self.halos = _validate_halo(self.halos, "instance grid halo")

    def getLongName(self) -> str:
        return f"{self.name}:{_name(self.inst)}"

    def type(self) -> GridType:
        return GridType.INSTANCE

    def getInstance(self) -> Any:
        return self.inst

    def addHalo(self, halos: Halo) -> None:
        self.halos = _validate_halo(halos, "instance grid halo")

    def setGridToBoundary(self, value: bool) -> None:
        self.grid_to_boundary = value

    def setReplaceable(self, replaceable: bool) -> None:
        self.replaceable = replaceable

    def isReplaceable(self) -> bool:
        return self.replaceable

    def isValid(self) -> bool:
        return self.inst is not None

    def report(self) -> Dict[str, Any]:
        data = super().report()
        data.update(
            {
                "instance": _name(self.inst) if self.inst is not None else None,
                "halo": self.halos,
                "grid_to_boundary": self.grid_to_boundary,
                "replaceable": self.replaceable,
                "valid": self.isValid(),
            }
        )
        return data


@dataclass
class BumpGrid(InstanceGrid):
    """对应 `pdn::BumpGrid`。"""

    def isValid(self) -> bool:
        _not_implemented("BumpGrid::isValid")


@dataclass
class ExistingGrid(Grid):
    """对应 `pdn::ExistingGrid`，用于读取已有 SPECIALNET 作为 grid。"""

    pdngen: Optional["PdnGen"] = None
    block: Any = None
    logger: Any = None
    shapes: List[Shape] = field(default_factory=list)

    def type(self) -> GridType:
        return GridType.EXISTING

    def populate(self) -> None:
        _not_implemented("ExistingGrid::populate")

    def getShapes(self) -> List[Shape]:
        return [*self.shapes, *super().getShapes()]

    def report(self) -> Dict[str, Any]:
        data = super().report()
        data.update({"existing_shape_count": len(self.shapes)})
        return data
