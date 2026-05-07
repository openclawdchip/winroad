"""Grid component、ring、strap 与 followpin 边界。"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence, Set, Tuple

from .types import ExtensionMode, GridComponentType, Halo, Rect, Shape, _name, _normalize_extension_mode, _not_implemented, _validate_halo, _validate_non_negative, _validate_positive, _validate_rect

@dataclass
class GridComponent:
    """对应 `pdn::GridComponent`，ring/strap/followpin 的公共基类。"""

    grid: "Grid"
    starts_with_power: bool = True
    nets: List[Any] = field(default_factory=list)
    shapes: List[Shape] = field(default_factory=list)

    def __post_init__(self) -> None:
        if self.grid is None:
            raise ValueError("grid component requires a grid")

    def getGrid(self) -> "Grid":
        return self.grid

    def setGrid(self, grid: "Grid") -> None:
        self.grid = grid

    def getDomain(self) -> "VoltageDomain":
        return self.grid.getDomain()

    def getShapes(self) -> List[Shape]:
        return list(self.shapes)

    def addShape(self, shape: Shape) -> None:
        shape.grid_component = self
        if shape not in self.shapes:
            self.shapes.append(shape)

    def clearShapes(self) -> None:
        for shape in self.shapes:
            shape.grid_component = None
        self.shapes.clear()

    def getShapeCount(self) -> int:
        return len(self.shapes)

    def setStartWithPower(self, value: bool) -> None:
        self.starts_with_power = value

    def getStartsWithPower(self) -> bool:
        return self.starts_with_power

    def setNets(self, nets: Sequence[Any]) -> None:
        self.nets = list(nets)

    def getNets(self) -> List[Any]:
        if self.nets:
            return list(self.nets)
        return self.grid.getNets(self.starts_with_power)

    def makeShapes(self, other_shapes: Any) -> None:
        _not_implemented(f"{type(self).__name__}::makeShapes")

    def build(self, other_shapes: Any = None, obstructions: Any = None) -> None:
        self.checkLayerSpecifications()
        self.makeShapes(other_shapes)
        self.refineShapes(other_shapes, obstructions)
        if obstructions is not None:
            self.cutShapes(obstructions)

    def refineShapes(self, all_shapes: Any, all_obstructions: Any) -> bool:
        return False

    def cutShapes(self, obstructions: Any) -> None:
        _not_implemented(f"{type(self).__name__}::cutShapes")

    def writeToDb(self, net_map: Mapping[Any, Any], add_pins: bool, convert_layer_to_pin: Iterable[Any]) -> Dict[Shape, List[Any]]:
        _not_implemented("GridComponent::writeToDb")

    def report(self) -> Dict[str, Any]:
        return {
            "type": self.type().value,
            "grid": self.grid.getName(),
            "nets": [_name(net) for net in self.getNets()],
            "shape_count": len(self.shapes),
            "shapes": [shape.report() for shape in self.shapes],
        }

    def type(self) -> GridComponentType:
        raise NotImplementedError

    def checkLayerSpecifications(self) -> None:
        if self.grid is None:
            raise ValueError(f"{type(self).__name__} is not attached to a grid")


@dataclass
class RingLayer:
    """对应 `pdn::Rings::Layer`。"""

    layer: Any = None
    width: int = 0
    spacing: int = 0

    def __post_init__(self) -> None:
        if self.layer is None:
            self.width = _validate_non_negative(self.width, "ring width")
            self.spacing = _validate_non_negative(self.spacing, "ring spacing")
            return
        self.width = _validate_positive(self.width, "ring width")
        self.spacing = _validate_non_negative(self.spacing, "ring spacing")


@dataclass
class Rings(GridComponent):
    """对应 `pdn::Rings`。"""

    layers: Tuple[RingLayer, RingLayer] = field(default_factory=lambda: (RingLayer(), RingLayer()))
    offset: Halo = (0, 0, 0, 0)
    pad_offset: Halo = (0, 0, 0, 0)
    extend_to_boundary: bool = False
    allow_outside_die: bool = False

    def __post_init__(self) -> None:
        super().__post_init__()
        self.offset = _validate_halo(self.offset, "ring offset")
        self.pad_offset = _validate_halo(self.pad_offset, "ring pad_offset")

    def setOffset(self, offset: Halo) -> None:
        self.offset = _validate_halo(offset, "ring offset")

    def getOffset(self) -> Halo:
        return self.offset

    def setPadOffset(self, offset: Halo) -> None:
        self.pad_offset = _validate_halo(offset, "ring pad_offset")

    def setExtendToBoundary(self, value: bool) -> None:
        self.extend_to_boundary = value

    def setAllowOutsideDieArea(self) -> None:
        self.allow_outside_die = True

    def getLayers(self) -> List[Any]:
        return [layer.layer for layer in self.layers if layer.layer is not None]

    def report(self) -> Dict[str, Any]:
        data = super().report()
        data.update(
            {
                "layers": [
                    {"layer": _name(layer.layer), "width": layer.width, "spacing": layer.spacing}
                    for layer in self.layers
                ],
                "offset": self.offset,
                "pad_offset": self.pad_offset,
                "extend_to_boundary": self.extend_to_boundary,
                "allow_outside_die": self.allow_outside_die,
            }
        )
        return data

    def type(self) -> GridComponentType:
        return GridComponentType.RING

    def checkLayerSpecifications(self) -> None:
        super().checkLayerSpecifications()
        if len(self.layers) != 2:
            raise ValueError("rings require exactly two layer specifications")
        for layer in self.layers:
            if layer.layer is None:
                raise ValueError("ring layer is required")
            _validate_positive(layer.width, "ring width")
            _validate_non_negative(layer.spacing, "ring spacing")


@dataclass
class Straps(GridComponent):
    """对应 `pdn::Straps`，也作为 stripe 的 Python 边界。"""

    layer: Any = None
    width: int = 0
    pitch: int = 0
    spacing: int = 0
    number_of_straps: int = 0
    offset: int = 0
    snap: bool = False
    extend_mode: ExtensionMode = ExtensionMode.CORE
    strap_start: int = 0
    strap_end: int = 0
    direction: Any = None

    def __post_init__(self) -> None:
        super().__post_init__()
        self.setExtend(self.extend_mode)
        self.width = _validate_non_negative(self.width, "strap width")
        self.pitch = _validate_non_negative(self.pitch, "strap pitch")
        self.spacing = _validate_non_negative(self.spacing, "strap spacing")
        self.number_of_straps = _validate_non_negative(self.number_of_straps, "number_of_straps")
        self.offset = _validate_non_negative(self.offset, "strap offset")
        self.strap_start = int(self.strap_start)
        self.strap_end = int(self.strap_end)

    def setOffset(self, offset: int) -> None:
        self.offset = _validate_non_negative(offset, "strap offset")

    def setSnapToGrid(self, snap: bool) -> None:
        self.snap = snap

    def setExtend(self, mode: ExtensionMode) -> None:
        self.extend_mode = _normalize_extension_mode(mode)

    def setStrapStartEnd(self, start: int, end: int) -> None:
        start = int(start)
        end = int(end)
        if start and end and start > end:
            raise ValueError("strap start must be <= strap end")
        self.strap_start = start
        self.strap_end = end

    def getStrapGroupWidth(self) -> int:
        if self.number_of_straps <= 1:
            return self.width
        return self.number_of_straps * self.width + (self.number_of_straps - 1) * self.spacing

    def report(self) -> Dict[str, Any]:
        data = super().report()
        data.update(
            {
                "layer": _name(self.layer),
                "width": self.width,
                "pitch": self.pitch,
                "spacing": self.spacing,
                "number_of_straps": self.number_of_straps,
                "offset": self.offset,
                "snap": self.snap,
                "extend_mode": self.extend_mode.value,
                "strap_start": self.strap_start,
                "strap_end": self.strap_end,
                "direction": _name(self.direction) if self.direction is not None else None,
            }
        )
        return data

    def type(self) -> GridComponentType:
        return GridComponentType.STRAP

    def checkLayerSpecifications(self) -> None:
        super().checkLayerSpecifications()
        if self.layer is None:
            raise ValueError(f"{type(self).__name__} layer is required")
        _validate_non_negative(self.width, "strap width")
        if not isinstance(self, FollowPins):
            _validate_positive(self.width, "strap width")
            _validate_positive(self.pitch, "strap pitch")
        _validate_non_negative(self.spacing, "strap spacing")
        _validate_non_negative(self.number_of_straps, "number_of_straps")


@dataclass
class FollowPins(Straps):
    """对应 `pdn::FollowPins`。"""

    def type(self) -> GridComponentType:
        return GridComponentType.FOLLOWPIN

    def determineWidth(self) -> None:
        _not_implemented("FollowPins::determineWidth")


@dataclass
class PadDirectConnectionStraps(Straps):
    """对应 `pdn::PadDirectConnectionStraps`。"""

    iterm: Any = None
    connect_pad_layers: List[Any] = field(default_factory=list)

    def canConnect(self) -> bool:
        _not_implemented("PadDirectConnectionStraps::canConnect")

    def report(self) -> Dict[str, Any]:
        data = super().report()
        data.update({"iterm": _name(self.iterm), "connect_pad_layers": [_name(layer) for layer in self.connect_pad_layers]})
        return data

    def type(self) -> GridComponentType:
        return GridComponentType.PAD_CONNECT


@dataclass
class RepairChannelStraps(Straps):
    """对应 `pdn::RepairChannelStraps`。"""

    target: Optional[Straps] = None
    connect_to: Any = None
    area: Rect = (0, 0, 0, 0)
    available_area: Rect = (0, 0, 0, 0)
    obs_check_area: Rect = (0, 0, 0, 0)
    repair_nets: Set[Any] = field(default_factory=set)
    invalid: bool = False

    def __post_init__(self) -> None:
        super().__post_init__()
        self.area = _validate_rect(self.area, "repair area")
        self.available_area = _validate_rect(self.available_area, "repair available_area")
        self.obs_check_area = _validate_rect(self.obs_check_area, "repair obs_check_area")

    def type(self) -> GridComponentType:
        return GridComponentType.REPAIR_CHANNEL

    def isRepairValid(self) -> bool:
        return not self.invalid

    def continueRepairs(self, other_shapes: Any) -> None:
        _not_implemented("RepairChannelStraps::continueRepairs")

    def report(self) -> Dict[str, Any]:
        data = super().report()
        data.update(
            {
                "target": _name(self.target.layer) if self.target is not None else None,
                "connect_to": _name(self.connect_to),
                "area": self.area,
                "available_area": self.available_area,
                "obs_check_area": self.obs_check_area,
                "repair_nets": [_name(net) for net in self.repair_nets],
                "valid": self.isRepairValid(),
            }
        )
        return data

    @staticmethod
    def repairGridChannels(grid: "Grid", global_shapes: Any, obstructions: Any, allow: bool, renderer: Any = None) -> None:
        _not_implemented("RepairChannelStraps::repairGridChannels")
