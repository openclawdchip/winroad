"""Measurement-flow state and untranslated extraction boundaries."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional

from .common import _not_translated
from .rc_model import extDistRC, extRCModel

CoupleOptions = List[int]
CoupleAndCompute = Callable[[CoupleOptions, Any], None]

@dataclass
class CouplingState:
    """对应 `CouplingState`，记录 coupling flow 的计数状态。"""

    wire_count: int = 0
    not_ordered_count: int = 0
    empty_table_count: int = 0
    one_count_table: int = 0

    def reset(self) -> None:
        self.wire_count = 0
        self.not_ordered_count = 0
        self.empty_table_count = 0
        self.one_count_table = 0

    def updateTableCounts(self, hasEmptyTable: bool, hasOneCount: bool) -> None:
        if hasEmptyTable:
            self.empty_table_count += 1
        if hasOneCount:
            self.one_count_table += 1


@dataclass
class CouplingDimensionParams:
    """对应 `CouplingDimensionParams`，封装耦合搜索维度参数。"""

    direction: int = 0
    metal_level: int = 1
    max_distance: int = 0
    coupling_distance: int = 0
    track_limit: int = 10
    dbgFP: Any = None

    def withTrackLimit(self, new_limit: int) -> "CouplingDimensionParams":
        return CouplingDimensionParams(
            self.direction, self.metal_level, self.max_distance, self.coupling_distance, new_limit, self.dbgFP
        )

    def nextLevel(self) -> "CouplingDimensionParams":
        return CouplingDimensionParams(
            self.direction,
            self.metal_level + 1,
            self.max_distance,
            self.coupling_distance,
            self.track_limit,
            self.dbgFP,
        )

    def withDistances(self, maxDist: int, coupDist: int) -> "CouplingDimensionParams":
        return CouplingDimensionParams(self.direction, self.metal_level, maxDist, coupDist, self.track_limit, self.dbgFP)

    def isWithinDistance(self, distance: int) -> bool:
        return distance <= self.max_distance

    def toString(self) -> str:
        return (
            f"Dir: {self.direction} Level: {self.metal_level} "
            f"MaxDist: {self.max_distance} CoupDist: {self.coupling_distance} "
            f"TrackLimit: {self.track_limit}"
        )


@dataclass
class SegmentTables:
    """对应 `SegmentTables`，保留各方向 segment 表的生命周期边界。"""

    upTable: List[Any] = field(default_factory=list)
    downTable: List[Any] = field(default_factory=list)
    verticalUpTable: List[Any] = field(default_factory=list)
    verticalDownTable: List[Any] = field(default_factory=list)
    wireSegmentTable: List[Any] = field(default_factory=list)
    aboveTable: List[Any] = field(default_factory=list)
    belowTable: List[Any] = field(default_factory=list)
    whiteTable: List[Any] = field(default_factory=list)

    def resetAll(self) -> None:
        self.upTable.clear()
        self.downTable.clear()
        self.verticalUpTable.clear()
        self.verticalDownTable.clear()
        self.wireSegmentTable.clear()
        self.aboveTable.clear()
        self.belowTable.clear()
        self.whiteTable.clear()

    def releaseAll(self) -> None:
        self.resetAll()


@dataclass
class extMeasure:
    """对应 `extMeasure`，RC 测量基类。"""

    logger_: Any = None
    _block: Any = None
    _tech: Any = None
    _netSrcId: int = 0
    _netTgtId: int = 0
    _met: int = 0
    _underMet: int = 0
    _overMet: int = 0
    _len: int = 0
    _dist: int = 0
    _width: int = 0
    _dir: int = 0
    _diag: bool = False
    _over: bool = False
    _under: bool = False
    _overUnder: bool = False
    _res: bool = False
    _dbg: int = 0
    _rc: List[extDistRC] = field(default_factory=list)
    _rcModel: Optional[extRCModel] = None
    _topWidthR: float = 0.0
    _botWidthR: float = 0.0
    _teffR: float = 0.0
    _peffR: float = 0.0
    _skipResCalc: bool = False
    _search: Any = None

    @staticmethod
    def getMetIndexOverUnder(met: int, mUnder: int, mOver: int, layerCnt: int, maxCnt: int = 10000) -> int:
        """复刻 C++ 中 over/under 组合索引的边界。

        OpenROAD 用该索引在 over-under 表里折叠三维组合。这里保留稳定、
        可逆的编码方式，供 Python 数据表先行挂接。
        """

        if layerCnt <= 0:
            layerCnt = 1
        index = (met * layerCnt + max(mUnder, 0)) * layerCnt + max(mOver, 0)
        return min(index, maxCnt)

    def IsDebugNet1(self) -> bool:
        return False

    def measureRC(self, options: CoupleOptions) -> None:
        raise _not_translated("extMeasure::measureRC")

    def calcRes(self, *args: Any, **kwargs: Any) -> float:
        raise _not_translated("extMeasure::calcRes")

    def calcDiagRC(self, *args: Any, **kwargs: Any) -> None:
        raise _not_translated("extMeasure::calcDiagRC")

    def measureOverUnderCap(self, *args: Any, **kwargs: Any) -> None:
        raise _not_translated("extMeasure::measureOverUnderCap")

    def getFringe(self, *args: Any, **kwargs: Any) -> float:
        raise _not_translated("extMeasure::getFringe")

    def getCoupling(self, *args: Any, **kwargs: Any) -> float:
        raise _not_translated("extMeasure::getCoupling")


@dataclass
class extMeasureRC(extMeasure):
    """对应 `extMeasureRC`，耦合 flow 的 RC 测量实现类。"""

    _connect_wire_FP: Any = None
    _connect_FP: Any = None
    _trackLevelCnt: int = 32
    _lowTrackToExtract: List[List[int]] = field(default_factory=lambda: [[0] * 32, [0] * 32])
    _hiTrackToExtract: List[List[int]] = field(default_factory=lambda: [[0] * 32, [0] * 32])
    _lowTrackToFree: List[List[int]] = field(default_factory=lambda: [[0] * 32, [0] * 32])
    _hiTrackToFree: List[List[int]] = field(default_factory=lambda: [[0] * 32, [0] * 32])
    _lowTrackSearch: List[List[int]] = field(default_factory=lambda: [[0] * 32, [0] * 32])
    _hiTrackSearch: List[List[int]] = field(default_factory=lambda: [[0] * 32, [0] * 32])
    _currentSeg: Any = None
    _couplingState: CouplingState = field(default_factory=CouplingState)
    _segments: SegmentTables = field(default_factory=SegmentTables)
    _maxCapNodeCnt: int = 0
    _totCCcnt: int = 0
    _totSmallCCcnt: int = 0
    _totBigCCcnt: int = 0
    _newDiagFlow: bool = False
    _useWeighted: bool = False

    def resetTrackIndices(self, dir: int) -> None:
        for table in (
            self._lowTrackToExtract,
            self._hiTrackToExtract,
            self._lowTrackToFree,
            self._hiTrackToFree,
            self._lowTrackSearch,
            self._hiTrackSearch,
        ):
            table[dir] = [0] * self._trackLevelCnt

    def releaseAll(self, segments: SegmentTables) -> None:
        segments.releaseAll()

    def ConnectWires(self, dir: int, bounds: Any = None) -> int:
        raise _not_translated("extMeasureRC::ConnectWires")

    def FindCouplingNeighbors(self, dir: int, bounds: Any = None) -> int:
        raise _not_translated("extMeasureRC::FindCouplingNeighbors")

    def CouplingFlow(self, *args: Any, **kwargs: Any) -> int:
        raise _not_translated("extMeasureRC::CouplingFlow")

    def FindCouplingCaps(self, *args: Any, **kwargs: Any) -> int:
        raise _not_translated("extMeasureRC::FindCouplingCaps")

    def computeAndStoreRC(self, *args: Any, **kwargs: Any) -> None:
        raise _not_translated("extMeasureRC::computeAndStoreRC")

    def OverSubRC(self, *args: Any, **kwargs: Any) -> None:
        raise _not_translated("extMeasureRC::OverSubRC")


