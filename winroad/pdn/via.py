"""Via、via generator 与 connect 规则边界。"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Iterable, List, Mapping, Optional, Set, Tuple

from .types import FailedViaReason, Rect, Shape, SplitCut, _name, _not_implemented, _validate_non_negative, _validate_rect

@dataclass
class Via:
    """对应 `pdn::Via`，记录上下形状交点与失败状态。"""

    connect: "Connect"
    net: Any
    area: Rect
    lower: Optional[Shape]
    upper: Optional[Shape]
    failed: bool = False
    failed_reason: Optional[FailedViaReason] = None

    def __post_init__(self) -> None:
        if self.connect is None:
            raise ValueError("via requires a connect")
        self.area = _validate_rect(self.area, "via area")
        if self.lower is not None:
            self.lower.addVia(self)
        if self.upper is not None:
            self.upper.addVia(self)

    def getNet(self) -> Any:
        return self.net

    def getArea(self) -> Rect:
        return self.area

    def getLowerShape(self) -> Optional[Shape]:
        return self.lower

    def getUpperShape(self) -> Optional[Shape]:
        return self.upper

    def getConnect(self) -> "Connect":
        return self.connect

    def getGrid(self) -> "Grid":
        return self.connect.getGrid()

    def markFailed(self, reason: FailedViaReason) -> None:
        self.failed = True
        self.failed_reason = reason

    def report(self) -> Dict[str, Any]:
        return {
            "grid": self.getGrid().getLongName(),
            "net": _name(self.net) if self.net is not None else None,
            "area": self.area,
            "layers": [
                _name(self.lower.layer) if self.lower is not None else None,
                _name(self.upper.layer) if self.upper is not None else None,
            ],
            "failed": self.failed,
            "failed_reason": self.failed_reason.value if self.failed_reason is not None else None,
        }

    def writeToDb(self, wire: Any, block: Any, obstructions: Any) -> None:
        _not_implemented("Via::writeToDb")


@dataclass
class Enclosure:
    """对应 `pdn::Enclosure`，保留 via enclosure 检查所需字段。"""

    x: int = 0
    y: int = 0
    allow_swap: bool = False

    def check(self, x: int, y: int) -> bool:
        return x >= self.x and y >= self.y

    def snap(self, tech: Any) -> None:
        _not_implemented("Enclosure::snap")


@dataclass
class DbVia:
    """对应 `pdn::DbVia`，所有 OpenDB via 构造留待后续翻译。"""

    generator: Optional["ViaGenerator"] = None

    def generate(self, block: Any, wire: Any, wire_type: Any, x: int, y: int, ongrid: Iterable[Any], logger: Any) -> Any:
        _not_implemented("DbVia::generate")

    def requiresPatch(self) -> bool:
        return False

    def getViaReport(self) -> Dict[str, int]:
        _not_implemented("DbVia::getViaReport")


@dataclass
class DbBaseVia(DbVia):
    """对应 `pdn::DbBaseVia`，TechVia/GenerateVia 的公共计数层。"""

    count: int = 0

    def getName(self) -> str:
        _not_implemented("DbBaseVia::getName")

    def getViaRect(self, include_enclosure: bool, include_via_shape: bool, include_bottom: bool = True, include_top: bool = True) -> Rect:
        _not_implemented("DbBaseVia::getViaRect")

    def getCount(self) -> int:
        return self.count

    def incrementCount(self, count: int = 1) -> None:
        count = _validate_non_negative(count, "via count increment")
        self.count += count

    def getViaReport(self) -> Dict[str, int]:
        try:
            name = self.getName()
        except NotImplementedError:
            name = type(self).__name__
        return {name: self.count}


@dataclass
class DbTechVia(DbBaseVia):
    """对应 `pdn::DbTechVia`，封装固定 dbTechVia 或 via array。"""

    via: Any = None
    rows: int = 1
    row_pitch: int = 0
    cols: int = 1
    col_pitch: int = 0
    required_bottom_enc: Optional[Enclosure] = None
    required_top_enc: Optional[Enclosure] = None

    def requiresPatch(self) -> bool:
        return self.rows > 1 or self.cols > 1


@dataclass
class DbGenerateVia(DbBaseVia):
    """对应 `pdn::DbGenerateVia`，封装 LEF/tech generate via rule。"""

    rect: Rect = (0, 0, 0, 0)
    rule: Any = None
    rows: int = 1
    columns: int = 1
    cut_pitch_x: int = 0
    cut_pitch_y: int = 0
    bottom_enclosure_x: int = 0
    bottom_enclosure_y: int = 0
    top_enclosure_x: int = 0
    top_enclosure_y: int = 0
    bottom: Any = None
    cut: Any = None
    top: Any = None


@dataclass
class DbSplitCutVia(DbVia):
    """对应 `pdn::DbSplitCutVia`，处理 split cut array 组合。"""

    via: Optional[DbBaseVia] = None
    rows: int = 1
    row_pitch: int = 0
    cols: int = 1
    col_pitch: int = 0
    bottom: Any = None
    top: Any = None


@dataclass
class DbArrayVia(DbVia):
    """对应 `pdn::DbArrayVia`，处理 ARRAYSPACING 规则下的 via array。"""

    core_via: Optional[DbBaseVia] = None
    end_of_row: Optional[DbBaseVia] = None
    end_of_column: Optional[DbBaseVia] = None
    end_of_row_column: Optional[DbBaseVia] = None
    rows: int = 1
    columns: int = 1
    array_spacing_x: int = 0
    array_spacing_y: int = 0

    def requiresPatch(self) -> bool:
        return True


@dataclass
class DbGenerateStackedVia(DbVia):
    """对应 `pdn::DbGenerateStackedVia`，封装多层 stacked via。"""

    vias: List[DbVia] = field(default_factory=list)
    bottom: Any = None
    block: Any = None

    def requiresPatch(self) -> bool:
        return any(via.requiresPatch() for via in self.vias)

    def getViaReport(self) -> Dict[str, int]:
        report: Dict[str, int] = {}
        for via in self.vias:
            for name, count in via.getViaReport().items():
                report[name] = report.get(name, 0) + count
        return report


@dataclass
class DbGenerateDummyVia(DbVia):
    """对应 `pdn::DbGenerateDummyVia`，用于记录无法生成 via 的位置。"""

    connect: Optional["Connect"] = None
    shape: Rect = (0, 0, 0, 0)
    bottom: Any = None
    top: Any = None
    add_report: bool = True

    def getViaReport(self) -> Dict[str, int]:
        return {}


@dataclass
class ViaGenerator:
    """对应 `pdn::ViaGenerator`，只保存约束与 cut/via 数组参数。"""

    logger: Any
    lower_rect: Rect
    lower_constraint: Mapping[str, bool]
    upper_rect: Rect
    upper_constraint: Mapping[str, bool]
    cut_pitch_x: int = 0
    cut_pitch_y: int = 0
    max_rows: int = 0
    max_columns: int = 0

    def build(self, bottom_is_internal_layer: bool, top_is_internal_layer: bool) -> bool:
        _not_implemented("ViaGenerator::build")

    def generate(self, block: Any) -> DbVia:
        _not_implemented("ViaGenerator::generate")


@dataclass
class GenerateViaGenerator(ViaGenerator):
    """对应 `pdn::GenerateViaGenerator`。"""

    rule: Any = None


@dataclass
class TechViaGenerator(ViaGenerator):
    """对应 `pdn::TechViaGenerator`。"""

    via: Any = None



@dataclass
class Connect:
    """对应 `pdn::Connect`，描述两层或多层之间 via 连接规则。"""

    grid: "Grid"
    layer0: Any
    layer1: Any
    fixed_generate_vias: List[Any] = field(default_factory=list)
    fixed_tech_vias: List[Any] = field(default_factory=list)
    cut_pitch_x: int = 0
    cut_pitch_y: int = 0
    max_rows: int = 0
    max_columns: int = 0
    ongrid: Set[Any] = field(default_factory=set)
    split_cuts: Dict[Any, SplitCut] = field(default_factory=dict)
    vias: List[Via] = field(default_factory=list)
    failed_vias: Dict[FailedViaReason, List[Tuple[Any, Rect]]] = field(default_factory=dict)

    def __post_init__(self) -> None:
        self.setSplitCuts(self.split_cuts)
        self.setCutPitch(self.cut_pitch_x, self.cut_pitch_y)
        self.setMaxRows(self.max_rows)
        self.setMaxColumns(self.max_columns)

    def addFixedVia(self, via: Any) -> None:
        if via not in self.fixed_generate_vias:
            self.fixed_generate_vias.append(via)

    def addFixedTechVia(self, via: Any) -> None:
        if via not in self.fixed_tech_vias:
            self.fixed_tech_vias.append(via)

    def setCutPitch(self, x: int, y: int) -> None:
        self.cut_pitch_x = _validate_non_negative(x, "cut_pitch_x")
        self.cut_pitch_y = _validate_non_negative(y, "cut_pitch_y")

    def setMaxRows(self, rows: int) -> None:
        self.max_rows = _validate_non_negative(rows, "max_rows")

    def setMaxColumns(self, cols: int) -> None:
        self.max_columns = _validate_non_negative(cols, "max_columns")

    def setOnGrid(self, layers: Sequence[Any]) -> None:
        self.ongrid = set(layers)

    def setSplitCuts(self, splits: Mapping[Any, Any]) -> None:
        self.split_cuts = {layer: self._normalize_split_cut(value) for layer, value in splits.items()}

    def getSplitCut(self, layer: Any) -> SplitCut:
        return self.split_cuts.get(layer, SplitCut())

    def getSplitCutPitch(self, layer: Any) -> int:
        return self.getSplitCut(layer).pitch

    def isSplitCutStaggered(self, layer: Any) -> bool:
        return self.getSplitCut(layer).stagger

    def getLowerLayer(self) -> Any:
        return self.layer0

    def getUpperLayer(self) -> Any:
        return self.layer1

    def isSingleLayerVia(self) -> bool:
        return self.layer0 == self.layer1

    def isMultiLayerVia(self) -> bool:
        return not self.isSingleLayerVia()

    def hasCutPitch(self) -> bool:
        return self.cut_pitch_x != 0 or self.cut_pitch_y != 0

    def setGrid(self, grid: "Grid") -> None:
        if grid is None:
            raise ValueError("connect requires a grid")
        self.grid = grid

    def getGrid(self) -> "Grid":
        return self.grid

    def clearShapes(self) -> None:
        for via in self.vias:
            if via.lower is not None:
                via.lower.removeVia(via)
            if via.upper is not None:
                via.upper.removeVia(via)
        self.vias.clear()

    def getVias(self) -> List[Via]:
        return list(self.vias)

    def addVia(self, via: Via) -> None:
        if via.connect is not self:
            raise ValueError("via is attached to a different connect")
        if via not in self.vias:
            self.vias.append(via)

    def makeVia(self, wire: Any, lower: Shape, upper: Shape, wire_type: Any, via_shapes: Any) -> None:
        _not_implemented("Connect::makeVia")

    def filterVias(self, filter_text: str) -> None:
        if not filter_text:
            return
        blocked = {token.strip() for token in filter_text.replace(",", " ").split() if token.strip()}
        self.fixed_generate_vias = [via for via in self.fixed_generate_vias if _name(via) not in blocked]
        self.fixed_tech_vias = [via for via in self.fixed_tech_vias if _name(via) not in blocked]

    def addFailedVia(self, reason: FailedViaReason, rect: Rect, net: Any) -> None:
        if not isinstance(reason, FailedViaReason):
            reason = FailedViaReason[str(reason).upper()]
        self.failed_vias.setdefault(reason, []).append((net, _validate_rect(rect, "failed via rect")))

    def clearFailedVias(self) -> None:
        self.failed_vias.clear()

    def printViaReport(self) -> Dict[str, int]:
        return {reason.value: len(items) for reason, items in self.failed_vias.items()}

    def failedViaReport(self, include_locations: bool = True) -> Dict[str, Any]:
        by_reason = self.printViaReport()
        failures: List[Dict[str, Any]] = []
        if include_locations:
            for reason, items in self.failed_vias.items():
                for net, rect in items:
                    failures.append({"reason": reason.value, "net": _name(net) if net is not None else None, "rect": rect})
        return {
            "grid": self.grid.getLongName(),
            "layers": [_name(self.layer0), _name(self.layer1)],
            "total": sum(by_reason.values()),
            "by_reason": by_reason,
            "failures": failures,
        }

    def report(self) -> Dict[str, Any]:
        return {
            "grid": self.grid.getName(),
            "layers": [_name(self.layer0), _name(self.layer1)],
            "fixed_generate_vias": [_name(via) for via in self.fixed_generate_vias],
            "fixed_tech_vias": [_name(via) for via in self.fixed_tech_vias],
            "cut_pitch": (self.cut_pitch_x, self.cut_pitch_y),
            "max_rows": self.max_rows,
            "max_columns": self.max_columns,
            "ongrid": [_name(layer) for layer in self.ongrid],
            "split_cuts": {
                _name(layer): {"pitch": split.pitch, "stagger": split.stagger}
                for layer, split in self.split_cuts.items()
            },
            "via_count": len(self.vias),
            "vias": [via.report() for via in self.vias],
            "failed_vias": self.printViaReport(),
            "failed_via_report": self.failedViaReport(include_locations=True),
        }

    @staticmethod
    def _normalize_split_cut(value: Any) -> SplitCut:
        if isinstance(value, SplitCut):
            return value
        if isinstance(value, Mapping):
            return SplitCut(_validate_non_negative(int(value.get("pitch", 0)), "split cut pitch"), bool(value.get("stagger", False)))
        if isinstance(value, tuple):
            pitch = int(value[0]) if len(value) > 0 else 0
            stagger = bool(value[1]) if len(value) > 1 else False
            return SplitCut(_validate_non_negative(pitch, "split cut pitch"), stagger)
        return SplitCut(_validate_non_negative(int(value), "split cut pitch"), False)
