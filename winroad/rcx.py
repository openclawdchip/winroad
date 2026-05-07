"""OpenROAD rcx 顶层对象的 Python 翻译骨架。

本文件按 OpenROAD `src/rcx` 的核心边界继续翻译：

- `rcx::Ext` 是 Tcl/应用层看到的顶层入口，持有 `extMain`。
- `extMain` 是寄生参数提取主控，负责 corner、模型、SPEF、抽取流程调度。
- `extMeasure` / `extMeasureRC` 是耦合电容与电阻测量流的工作对象。
- `extDistRC` / `ext*RCTable` / `extRCModel` 保存工艺 RC 模型表。

这里不做估算 demo，也不发明新架构。尚未翻译的物理提取算法会保留
清晰的函数边界并抛出 `NotImplementedError`，让后续可以继续逐 C++ 文件落地。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Dict, Iterable, List, Optional


CoupleOptions = List[int]
CoupleAndCompute = Callable[[CoupleOptions, Any], None]


def _not_translated(name: str) -> NotImplementedError:
    """统一说明某个 C++ 函数边界尚未落地。"""

    return NotImplementedError(f"OpenROAD rcx::{name} 尚未翻译为 Python 实现")


def _parse_number_list(text: Optional[str]) -> List[float]:
    """解析 rcx Tcl 选项里常见的空格/逗号分隔数值表。"""

    if not text:
        return []
    values: List[float] = []
    for word in text.replace(",", " ").split():
        values.append(float(word))
    return values


@dataclass
class BenchWiresOptions:
    """对应 OpenROAD `BenchWiresOptions`。"""

    block: str = "blk"
    over_dist: int = 100
    under_dist: int = 100
    met_cnt: int = 1000
    met: int = -1
    over_met: int = -1
    under_met: int = -1
    len: int = 200
    cnt: int = 5
    w: str = "1"
    s: str = "1"
    th: str = "1"
    d: str = "0.0"
    w_list: str = "1"
    s_list: str = "1 2 2.5 3 3.5 4 4.5 5 6 8 10 12"
    th_list: str = "0 1 2 2.5 3 3.5 4 4.5 5 6 8 10 12"
    grid_list: str = ""
    default_lef_rules: bool = False
    nondefault_lef_rules: bool = False
    dir: str = "./Bench"
    Over: bool = False
    db_only: bool = False
    v1: bool = False
    ddd: bool = False
    multiple_widths: bool = False
    diag: bool = False
    over_under: bool = False
    gen_def_patterns: bool = False
    resPatterns: bool = False


@dataclass
class ExtractOptions:
    """对应 OpenROAD `ExtractOptions`。"""

    debug_net: Optional[str] = None
    ext_model_file: Optional[str] = None
    net: Optional[str] = None
    cc_up: int = 2
    corner_cnt: int = 1
    max_res: float = 50.0
    no_merge_via_res: bool = False
    corner: int = -1
    coupling_threshold: float = 0.1
    context_depth: int = 5
    cc_model: int = 10
    signal_table: int = 3
    over_cell: bool = False
    skip_via_wires: bool = False
    lef_rc: bool = False
    lef_res: bool = False
    rlog: bool = False
    _v2: bool = False
    _version: float = 2.2
    _wire_extracted_progress_count: int = 50000
    _dbg: int = 0


@dataclass
class SpefOptions:
    """对应 OpenROAD `SpefOptions`。"""

    nets: Optional[str] = None
    net_id: int = 0
    ext_corner_name: Optional[str] = None
    corner: int = -1
    debug: int = 0
    parallel: bool = False
    init: bool = False
    end: bool = False
    use_ids: bool = False
    no_name_map: bool = False
    N: Optional[str] = None
    term_junction_xy: bool = False
    single_pi: bool = False
    file: Optional[str] = None
    gz: bool = False
    stop_after_map: bool = False
    w_clock: bool = False
    w_conn: bool = False
    w_cap: bool = False
    w_cc_cap: bool = False
    w_res: bool = False
    no_c_num: bool = False
    no_backslash: bool = False
    cap_units: str = "PF"
    res_units: str = "OHM"
    coordinates: bool = False


@dataclass
class ReadSpefOpts:
    """对应 OpenROAD `ReadSpefOpts`。"""

    file: Optional[str] = None
    net: Optional[str] = None
    force: bool = False
    use_ids: bool = False
    keep_loaded_corner: bool = False
    stamp_wire: bool = False
    test_parsing: int = 0
    N: Optional[str] = None
    r_conn: bool = False
    r_cap: bool = False
    r_cc_cap: bool = False
    r_res: bool = False
    cc_threshold: float = -0.5
    cc_ground_factor: float = 0.0
    app_print_limit: int = 0
    corner: int = -1
    db_corner_name: Optional[str] = None
    calibrate_base_corner: Optional[str] = None
    spef_corner: int = -1
    m_map: bool = False
    more_to_read: bool = False
    length_unit: float = 1.0
    fix_loop: int = 0
    no_cap_num_collapse: bool = False
    cap_node_map_file: Optional[str] = None
    log: bool = False


@dataclass
class DiffOptions:
    """对应 OpenROAD `DiffOptions`。"""

    net: Optional[str] = None
    use_ids: bool = False
    test_parsing: bool = False
    file: Optional[str] = None
    db_corner_name: Optional[str] = None
    spef_corner: int = -1
    exclude_net_subword: Optional[str] = None
    net_subword: Optional[str] = None
    rc_stats_file: Optional[str] = None
    r_conn: bool = False
    r_cap: bool = False
    r_cc_cap: bool = False
    r_res: bool = False
    ext_corner: int = -1
    low_guard: float = 1.0
    upper_guard: float = -1.0
    m_map: bool = False
    log: bool = False


@dataclass
class PatternOptions:
    """对应 OpenROAD `PatternOptions`。"""

    name: str = "blk"
    over_dist: int = 1000
    under_dist: int = 1000
    met_cnt: int = 1000
    met: int = -1
    over_met: int = -1
    under_met: int = -1
    width: Optional[str] = None
    spacing: Optional[str] = None
    couple_width: Optional[str] = None
    couple_spacing: Optional[str] = None
    far_width: str = "1"
    far_spacing: str = "1"
    over_width: Optional[str] = None
    over_spacing: Optional[str] = None
    over2_width: Optional[str] = None
    over2_spacing: Optional[str] = None
    under_width: Optional[str] = None
    under_spacing: Optional[str] = None
    under2_width: Optional[str] = None
    under2_spacing: Optional[str] = None
    dbg: int = 0
    wire_cnt: int = 0
    mlist: Optional[str] = None
    len: int = 0
    offset_over: Optional[str] = None
    offset_under: Optional[str] = None
    grid_list: str = ""
    default_lef_rules: bool = False
    nondefault_lef_rules: bool = False
    dir: str = "./Bench"
    over: bool = False
    ddd: bool = False
    diag: bool = False
    over_under: bool = False
    under: bool = False


@dataclass
class extDistRC:
    """对应 `extDistRC`，保存单个距离点的 RC 数据。"""

    sep_: int = 0
    coupling_: float = 0.0
    fringe_: float = 0.0
    fringeW_: float = 0.0
    diag_: float = 0.0
    res_: float = 0.0
    logger_: Any = None

    def Reset(self) -> None:
        self.sep_ = 0
        self.coupling_ = 0.0
        self.fringe_ = 0.0
        self.fringeW_ = 0.0
        self.diag_ = 0.0
        self.res_ = 0.0

    def setLogger(self, logger: Any) -> None:
        self.logger_ = logger

    def set(self, d: int, cc: float, fr: float, a: float, r: float) -> None:
        self.sep_ = d
        self.coupling_ = cc
        self.fringe_ = fr
        self.diag_ = a
        self.res_ = r

    def getFringe(self) -> float:
        return self.fringe_

    def getFringeW(self) -> float:
        return self.fringeW_

    def getCoupling(self) -> float:
        return self.coupling_

    def getDiag(self) -> float:
        return self.diag_

    def getRes(self) -> float:
        return self.res_

    def getSep(self) -> int:
        return self.sep_

    def getTotalCap(self) -> float:
        return self.coupling_ + self.fringe_ + self.diag_

    def setCoupling(self, coupling: float) -> None:
        self.coupling_ = coupling

    def setFringe(self, fringe: float) -> None:
        self.fringe_ = fringe

    def setFringeW(self, fringew: float) -> None:
        self.fringeW_ = fringew

    def setRes(self, res: float) -> None:
        self.res_ = res

    def addRC(self, rcUnit: "extDistRC", len: int, addCC: bool) -> None:
        """累加已给定的 RC 单元。

        C++ 中该函数用于把表中单位 RC 按线段长度加到当前对象。这里仅做
        对已有数值的确定性累加，不生成或估算任何工艺数据。
        """

        if addCC:
            self.coupling_ += rcUnit.coupling_ * len
        self.fringe_ += rcUnit.fringe_ * len
        self.fringeW_ += rcUnit.fringeW_ * len
        self.diag_ += rcUnit.diag_ * len
        self.res_ += rcUnit.res_ * len


@dataclass
class extDistRCTable:
    """对应 `extDistRCTable`，按 spacing/distance 保存 `extDistRC`。"""

    distCnt_: int = 0
    measureTable_: List[extDistRC] = field(default_factory=list)
    computeTable_: List[extDistRC] = field(default_factory=list)
    maxDist_: int = 0
    unit_: int = 1
    logger_: Any = None

    def addMeasureRC(self, rc: extDistRC) -> int:
        self.measureTable_.append(rc)
        return len(self.measureTable_) - 1

    def getLastRC(self) -> Optional[extDistRC]:
        if not self.measureTable_:
            return None
        return self.measureTable_[-1]

    def getRC_index(self, n: int) -> Optional[extDistRC]:
        if 0 <= n < len(self.measureTable_):
            return self.measureTable_[n]
        return None

    def getRC(self, s: int, compute: bool = False) -> Optional[extDistRC]:
        table = self.computeTable_ if compute else self.measureTable_
        for rc in table:
            if rc.sep_ == s:
                return rc
        return None

    def getComputeRC(self, dist: int | float) -> Optional[extDistRC]:
        return self.getRC(int(dist), compute=True)

    def getComputeRC_maxDist(self) -> int:
        return self.maxDist_

    def makeComputeTable(self, maxDist: int, distUnit: int) -> None:
        self.maxDist_ = maxDist
        self.unit_ = distUnit
        self.computeTable_ = list(self.measureTable_)

    def findRes(self, dist1: int, dist2: int, compute: bool = False) -> Optional[extDistRC]:
        """按 C++ 边界保留双距离电阻查找；当前只在已加载表中精确匹配。"""

        return self.getRC(dist1, compute) or self.getRC(dist2, compute)

    def readRules(self, *args: Any, **kwargs: Any) -> int:
        raise _not_translated("extDistRCTable::readRules")

    def readRules_res2(self, *args: Any, **kwargs: Any) -> int:
        raise _not_translated("extDistRCTable::readRules_res2")

    def writeRules(self, *args: Any, **kwargs: Any) -> int:
        raise _not_translated("extDistRCTable::writeRules")

    def interpolate(self, *args: Any, **kwargs: Any) -> int:
        raise _not_translated("extDistRCTable::interpolate")


@dataclass
class extDistWidthRCTable:
    """对应 `extDistWidthRCTable`，以 width -> dist table 建模。"""

    _over: bool = False
    _layerCnt: int = 0
    _met: int = 0
    _widthTable: List[int] = field(default_factory=list)
    _diagWidthTable: Dict[int, List[int]] = field(default_factory=dict)
    _diagDistTable: Dict[int, List[int]] = field(default_factory=dict)
    _metCnt: int = 0
    _widthCnt: int = 0
    _diagWidthCnt: int = 0
    _diagDistCnt: int = 0
    _rcDistTable: Dict[tuple[int, int], extDistRCTable] = field(default_factory=dict)

    def addRCw(self, n: int, w: int, rc: extDistRC) -> None:
        table = self._rcDistTable.setdefault((n, w), extDistRCTable())
        table.addMeasureRC(rc)
        if w not in self._widthTable:
            self._widthTable.append(w)

    def getWidthIndex(self, w: int) -> int:
        try:
            return self._widthTable.index(w)
        except ValueError:
            return -1

    def getRC(self, mou: int, w: int, s: int) -> Optional[extDistRC]:
        table = self._rcDistTable.get((mou, w))
        if table is None:
            return None
        return table.getRC(s)

    def getRuleTable(self, mou: int, w: int) -> Optional[extDistRCTable]:
        return self._rcDistTable.get((mou, w))

    def setDiagUnderTables(
        self,
        met: int,
        diagWidthTable: Optional[Iterable[float]] = None,
        diagDistTable: Optional[Iterable[float]] = None,
        dbFactor: float = 1.0,
    ) -> None:
        self._diagWidthTable[met] = [int(w * dbFactor) for w in (diagWidthTable or [])]
        self._diagDistTable[met] = [int(s * dbFactor) for s in (diagDistTable or [])]
        self._diagWidthCnt = max(self._diagWidthCnt, len(self._diagWidthTable[met]))
        self._diagDistCnt = max(self._diagDistCnt, len(self._diagDistTable[met]))

    def getDiagWidthIndex(self, m: int, w: int) -> int:
        try:
            return self._diagWidthTable.get(m, []).index(w)
        except ValueError:
            return -1

    def getDiagDistIndex(self, m: int, s: int) -> int:
        try:
            return self._diagDistTable.get(m, []).index(s)
        except ValueError:
            return -1

    def getMetIndexUnder(self, mOver: int) -> int:
        return mOver

    def readRulesOver(self, *args: Any, **kwargs: Any) -> int:
        raise _not_translated("extDistWidthRCTable::readRulesOver")

    def readRulesUnder(self, *args: Any, **kwargs: Any) -> int:
        raise _not_translated("extDistWidthRCTable::readRulesUnder")

    def readRulesDiagUnder(self, *args: Any, **kwargs: Any) -> int:
        raise _not_translated("extDistWidthRCTable::readRulesDiagUnder")

    def readRulesOverUnder(self, *args: Any, **kwargs: Any) -> int:
        raise _not_translated("extDistWidthRCTable::readRulesOverUnder")


@dataclass
class extMetRCTable:
    """对应 `extMetRCTable`，保存某个模型内各金属层 RC 表。"""

    _layerCnt: int = 0
    logger_: Any = None
    _capOver: Dict[int, extDistWidthRCTable] = field(default_factory=dict)
    _capUnder: Dict[int, extDistWidthRCTable] = field(default_factory=dict)
    _capOverUnder: Dict[int, extDistWidthRCTable] = field(default_factory=dict)
    _wireCnt: int = 0
    _name: str = ""
    _rate: float = 0.0
    _capOver_open: Dict[tuple[int, bool], extDistWidthRCTable] = field(default_factory=dict)
    _capUnder_open: Dict[tuple[int, bool], extDistWidthRCTable] = field(default_factory=dict)
    _capOverUnder_open: Dict[tuple[int, bool], extDistWidthRCTable] = field(default_factory=dict)
    _capDiagUnder: Dict[int, extDistWidthRCTable] = field(default_factory=dict)
    _resOver: Dict[int, extDistWidthRCTable] = field(default_factory=dict)
    _viaModel: List["extViaModel"] = field(default_factory=list)
    _viaModelHash: Dict[str, "extViaModel"] = field(default_factory=dict)

    def allocOverTable(self, met: int, wTable: Optional[List[float]] = None, dbFactor: float = 1.0) -> None:
        table = extDistWidthRCTable(_over=True, _layerCnt=self._layerCnt, _met=met)
        table._widthTable = [int(w * dbFactor) for w in (wTable or [])]
        self._capOver[met] = table

    def allocUnderTable(self, met: int, wTable: Optional[List[float]] = None, dbFactor: float = 1.0) -> None:
        table = extDistWidthRCTable(_over=False, _layerCnt=self._layerCnt, _met=met)
        table._widthTable = [int(w * dbFactor) for w in (wTable or [])]
        self._capUnder[met] = table

    def allocOverUnderTable(self, met: int, wTable: Optional[List[float]] = None, dbFactor: float = 1.0) -> None:
        table = extDistWidthRCTable(_over=True, _layerCnt=self._layerCnt, _met=met)
        table._widthTable = [int(w * dbFactor) for w in (wTable or [])]
        self._capOverUnder[met] = table

    def allocDiagUnderTable(
        self,
        met: int,
        wTable: Optional[List[float]] = None,
        diagWidthCnt: int = 0,
        diagDistCnt: int = 0,
        dbFactor: float = 1.0,
    ) -> None:
        table = extDistWidthRCTable(_over=False, _layerCnt=self._layerCnt, _met=met)
        table._widthTable = [int(w * dbFactor) for w in (wTable or [])]
        self._capDiagUnder[met] = table

    def addCapOver(self, met: int, metUnder: int, rc: extDistRC) -> int:
        table = self._capOver.setdefault(met, extDistWidthRCTable(_over=True, _layerCnt=self._layerCnt, _met=met))
        table.addRCw(metUnder, 0, rc)
        return len(table._rcDistTable)

    def addCapUnder(self, met: int, metOver: int, rc: extDistRC) -> int:
        table = self._capUnder.setdefault(met, extDistWidthRCTable(_over=False, _layerCnt=self._layerCnt, _met=met))
        table.addRCw(metOver, 0, rc)
        return len(table._rcDistTable)

    def getCapOver(self, met: int, metUnder: int) -> Optional[extDistRC]:
        table = self._capOver.get(met)
        return None if table is None else table.getRC(metUnder, 0, 0)

    def getCapUnder(self, met: int, metOver: int) -> Optional[extDistRC]:
        table = self._capUnder.get(met)
        return None if table is None else table.getRC(metOver, 0, 0)

    def addViaModel(
        self,
        name: str,
        R: float,
        cCnt: int,
        dx: int,
        dy: int,
        top: int,
        bot: int,
    ) -> "extViaModel":
        model = extViaModel(name=name, R=R, cCnt=cCnt, dx=dx, dy=dy, top=top, bot=bot)
        self._viaModel.append(model)
        self._viaModelHash[name] = model
        return model

    def getViaModel(self, name: str) -> Optional["extViaModel"]:
        return self._viaModelHash.get(name)

    def GetViaRes(self, *args: Any, **kwargs: Any) -> bool:
        raise _not_translated("extMetRCTable::GetViaRes")

    def ReadRules(self, *args: Any, **kwargs: Any) -> bool:
        raise _not_translated("extMetRCTable::ReadRules")

    def writeViaRes(self, *args: Any, **kwargs: Any) -> None:
        raise _not_translated("extMetRCTable::writeViaRes")


@dataclass
class extViaModel:
    """对应 `extViaModel` 的轻量配置边界，保存 via 电阻模型元数据。"""

    name: str = ""
    R: float = 0.0
    cCnt: int = 0
    dx: int = 0
    dy: int = 0
    top: int = 0
    bot: int = 0


@dataclass
class extRCTable:
    """对应 `extRCTable`，早期 over/under 简化表的 Python 边界。"""

    _over: bool = True
    _layerCnt: int = 0
    _inTable: Dict[tuple[int, int], List[extDistRC]] = field(default_factory=dict)

    def addCapOver(self, met: int, metUnder: int, rc: extDistRC) -> int:
        table = self._inTable.setdefault((met, metUnder), [])
        table.append(rc)
        return len(table) - 1

    def getCapOver(self, met: int, metUnder: int) -> Optional[extDistRC]:
        table = self._inTable.get((met, metUnder), [])
        return table[-1] if table else None


@dataclass
class extCorner:
    """对应 `extCorner`，描述 process corner 和派生缩放 corner。"""

    _name: str = ""
    _model: int = -1
    _extDbIndex: int = -1
    _scaledCornerIdx: int = -1
    _resFactor: float = 1.0
    _ccFactor: float = 1.0
    _gndcFactor: float = 1.0


@dataclass
class extMainOptions:
    """对应 `extMainOptions`，bench/model pattern 生成的内部选项。"""

    _overDist: int = 100
    _underDist: int = 100
    _met_cnt: int = 1000
    _met: int = -1
    _underMet: int = -1
    _overMet: int = -1
    _wireCnt: int = 5
    _topDir: Optional[str] = None
    _name: str = "blk"
    _wTable: str = "1"
    _sTable: str = "1"
    _thTable: str = "1"
    _dTable: str = "0.0"
    _listsFlag: bool = False
    _thListFlag: bool = False
    _wsListFlag: bool = False
    _default_lef_rules: bool = False
    _nondefault_lef_rules: bool = False
    _multiple_widths: bool = False
    _varFlag: bool = False
    _over: bool = False
    _overUnder: bool = False
    _diag: int = 0
    _db_only: bool = False
    _gen_def_patterns: bool = False
    _res_patterns: bool = False
    _tech: Any = None
    _block: Any = None
    _widthTable: List[float] = field(default_factory=list)
    _spaceTable: List[float] = field(default_factory=list)
    _densityTable: List[float] = field(default_factory=list)
    _thicknessTable: List[float] = field(default_factory=list)
    _gridTable: List[float] = field(default_factory=list)
    _ll: List[int] = field(default_factory=lambda: [0, 0])
    _ur: List[int] = field(default_factory=lambda: [0, 0])
    _len: int = 0
    _dist: int = 0
    _width: int = 0
    _dir: int = 0
    _rcModel: Optional["extRCModel"] = None
    _layerCnt: int = 0
    _v1: bool = False


@dataclass
class extRCModel:
    """对应 `extRCModel`，保存多 corner / 多金属层 RC 模型。"""

    _name: str = ""
    _layerCnt: int = 0
    _metRCTable: List[extMetRCTable] = field(default_factory=list)
    _cornerTable: List[extCorner] = field(default_factory=list)
    _modelMap: List[int] = field(default_factory=list)
    _rulesFile: Optional[str] = None
    _rulesFileBinary: bool = False
    _resistanceTable: Dict[tuple[int, int], float] = field(default_factory=dict)
    _capacitanceTable: Dict[tuple[int, int], float] = field(default_factory=dict)
    _minWidthTable: Dict[int, float] = field(default_factory=dict)
    _minDistTable: Dict[int, int] = field(default_factory=dict)
    _v2_flow: bool = False

    def addMetRCTable(self, table: extMetRCTable) -> int:
        self._metRCTable.append(table)
        return len(self._metRCTable) - 1

    def getMetRCTable(self, corner: int = 0) -> Optional[extMetRCTable]:
        if 0 <= corner < len(self._metRCTable):
            return self._metRCTable[corner]
        return None

    def getUnderRC(self, met: int, overMet: int, width: int, dist: int) -> Optional[extDistRC]:
        table = self.getMetRCTable()
        if table is None:
            return None
        width_table = table._capUnder.get(met)
        return None if width_table is None else width_table.getRC(overMet, width, dist)

    def getOverUnderRC(self, met: int, underMet: int, overMet: int, width: int, dist: int) -> Optional[extDistRC]:
        table = self.getMetRCTable()
        if table is None:
            return None
        width_table = table._capOverUnder.get(met)
        key = extMeasure.getMetIndexOverUnder(met, underMet, overMet, max(self._layerCnt, 1))
        return None if width_table is None else width_table.getRC(key, width, dist)

    def createModelProcessTable(self, rulesFileModelCnt: int, cornerCnt: int) -> bool:
        self._modelMap = list(range(min(rulesFileModelCnt, cornerCnt)))
        while len(self._modelMap) < cornerCnt:
            self._modelMap.append(-1)
        return True

    def isRulesFile_v2(self, name: str, bin: bool = False) -> bool:
        self._rulesFile = name
        self._rulesFileBinary = bin
        raise _not_translated("extRCModel::isRulesFile_v2")

    def readRules_v2(self, *args: Any, **kwargs: Any) -> bool:
        raise _not_translated("extRCModel::readRules_v2")

    def spotModelsInRules(self, *args: Any, **kwargs: Any) -> bool:
        raise _not_translated("extRCModel::spotModelsInRules")

    def DefWires(self, opt: extMainOptions) -> int:
        raise _not_translated("extRCModel::DefWires")

    def OverRulePat(self, *args: Any, **kwargs: Any) -> int:
        raise _not_translated("extRCModel::OverRulePat")

    def UnderRulePat(self, *args: Any, **kwargs: Any) -> int:
        raise _not_translated("extRCModel::UnderRulePat")

    def DiagUnderRulePat(self, *args: Any, **kwargs: Any) -> int:
        raise _not_translated("extRCModel::DiagUnderRulePat")

    def OverUnderRulePat(self, *args: Any, **kwargs: Any) -> int:
        raise _not_translated("extRCModel::OverUnderRulePat")

    def ViaRulePat(self, *args: Any, **kwargs: Any) -> int:
        raise _not_translated("extRCModel::ViaRulePat")


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


@dataclass
class extSpef:
    """对应 `extSpef` 的占位边界。

    真实 SPEF parser/writer 后续应继续从 `extSpef.h/.cpp` 翻译；当前仅让
    `extMain` 能持有同名对象，不输出伪 SPEF。
    """

    logger_: Any = None
    _tech: Any = None
    _block: Any = None
    _version: Optional[str] = None
    _ext: Any = None
    _design: Optional[str] = None
    _inFile: Optional[str] = None
    _outFile: Optional[str] = None
    _gzipFlag: bool = False
    _writeNameMap: bool = True
    _noNameMap: bool = False
    _singleP: bool = False
    _preserveCapValues: bool = False
    _cornerCnt: int = 0
    _dbCorner: int = -1
    _active_corner_cnt: int = 0
    _active_corner_number: List[int] = field(default_factory=list)
    _rRun: int = 0
    _moreToRead: bool = False
    _termJxy: bool = False
    _noCapNumCollapse: bool = False
    _last_written_nets: List[Any] = field(default_factory=list)
    _last_read_nets: List[Any] = field(default_factory=list)
    options: Optional[SpefOptions] = None

    def reinit(self) -> None:
        self._rRun = 0
        self._last_written_nets.clear()
        self._last_read_nets.clear()

    def setOutSpef(self, filename: str) -> bool:
        self._outFile = filename
        return bool(filename)

    def setInSpef(self, filename: str, onlyOpen: bool = False) -> bool:
        self._inFile = filename
        return bool(filename)

    def stopWrite(self) -> None:
        raise _not_translated("extSpef::stopWrite")

    def set_single_pi(self, v: bool) -> None:
        self._singleP = v

    def preserveFlag(self, v: bool) -> None:
        self._preserveCapValues = v

    def getWriteCorner(self, corner: int, name: Optional[str] = None) -> int:
        if corner >= 0:
            return corner
        if name and self._ext is not None and hasattr(self._ext, "get_ext_db_corner"):
            return self._ext.get_ext_db_corner(name)
        return -1

    def setUseIdsFlag(self, diff: bool = False, calib: bool = False) -> None:
        self._noNameMap = True

    def setGzipFlag(self, gzFlag: bool) -> None:
        self._gzipFlag = gzFlag

    def setDesign(self, name: str) -> None:
        self._design = name

    def setCornerCnt(self, n: int) -> None:
        self._cornerCnt = n
        self._active_corner_cnt = n
        self._active_corner_number = list(range(n))

    def incr_rRun(self) -> None:
        self._rRun += 1

    def writeBlock(self, options: SpefOptions) -> None:
        self.options = options
        self.setGzipFlag(options.gz)
        self.set_single_pi(options.single_pi)
        self._termJxy = options.term_junction_xy
        self._noNameMap = options.no_name_map
        if options.file:
            self.setOutSpef(options.file)
        self._dbCorner = self.getWriteCorner(options.corner, options.ext_corner_name)
        raise _not_translated("extSpef::writeBlock")

    def readBlock(self, options: ReadSpefOpts) -> None:
        self._moreToRead = options.more_to_read
        self._noCapNumCollapse = options.no_cap_num_collapse
        if options.file:
            self.setInSpef(options.file)
        self._dbCorner = options.corner
        raise _not_translated("extSpef::readBlock")

    def readBlockIncr(self, debug: int = 0) -> int:
        raise _not_translated("extSpef::readBlockIncr")

    def write_spef_nets(self, flatten: bool, parallel: bool) -> None:
        raise _not_translated("extSpef::write_spef_nets")

    def writeNet(self, *args: Any, **kwargs: Any) -> None:
        raise _not_translated("extSpef::writeNet")

    def setCalibLimit(self, upperLimit: float, lowerLimit: float) -> None:
        self._upperCalibLimit = upperLimit
        self._lowerCalibLimit = lowerLimit


@dataclass
class extMain:
    """对应 OpenROAD `extMain`，rcx 的核心入口类。"""

    db: Any = None
    logger_: Any = None
    spef_version_: Optional[str] = None
    _tech: Any = None
    _block: Any = None
    _spef: extSpef = field(default_factory=extSpef)
    _modelTable: List[extRCModel] = field(default_factory=list)
    _modelMap: List[int] = field(default_factory=list)
    _metRCTable: List[extMetRCTable] = field(default_factory=list)
    _resistanceTable: Dict[tuple[int, int], float] = field(default_factory=dict)
    _capacitanceTable: Dict[tuple[int, int], float] = field(default_factory=dict)
    _minWidthTable: Dict[int, float] = field(default_factory=dict)
    _minDistTable: Dict[int, int] = field(default_factory=dict)
    _processCornerTable: List[extCorner] = field(default_factory=list)
    _scaledCornerTable: List[extCorner] = field(default_factory=list)
    _cornerCnt: int = 0
    _extDbCnt: int = 0
    _extracted: bool = False
    _allNet: bool = False
    _ccUp: int = 0
    _couplingFlag: int = 0
    _mergeResBound: float = 0.0
    _mergeViaRes: bool = False
    _mergeParallelCC: bool = False
    _reportNetNoWire: bool = False
    _netNoWireCnt: int = 0
    _resFactor: float = 1.0
    _resModify: bool = False
    _ccFactor: float = 1.0
    _ccModify: bool = False
    _gndcFactor: float = 1.0
    _gndcModify: bool = False
    _coupleThreshold: float = 0.1
    _dgContextDepth: int = 0
    _dgContextPlanes: int = 0
    _dgContextTracks: int = 0
    _ccContextPlanes: int = 0
    _extRun: int = 0
    _prevControl: Any = None
    _foreign: bool = False
    _rsegCoord: bool = False
    _diagFlow: bool = False
    _noModelRC: bool = False
    _currentModel: Optional[extRCModel] = None
    _lef_res: bool = False
    _wireInfra: bool = False
    _extMaxRect: Any = None
    _tmpLenStats: str = ""
    _last_node_xy: List[int] = field(default_factory=lambda: [0, 0])
    _minCapTable: Dict[tuple[int, int], float] = field(default_factory=dict)
    _maxCapTable: Dict[tuple[int, int], float] = field(default_factory=dict)
    _minResTable: Dict[tuple[int, int], float] = field(default_factory=dict)
    _maxResTable: Dict[tuple[int, int], float] = field(default_factory=dict)
    _last_extract_options: Optional[ExtractOptions] = None
    _last_spef_options: Optional[SpefOptions] = None
    _last_read_spef_options: Optional[ReadSpefOpts] = None
    _last_bench_options: Optional[extMainOptions] = None

    def __post_init__(self) -> None:
        self._spef.logger_ = self.logger_
        self._spef._tech = self._tech
        self._spef._block = self._block
        self._spef._version = self.spef_version_
        self._spef._ext = self

    def setLogger(self, logger: Any) -> None:
        self.logger_ = logger
        self._spef.logger_ = logger

    def addRCModel(self, model: extRCModel) -> int:
        self._modelTable.append(model)
        return len(self._modelTable) - 1

    def getRCModel(self, index: int = 0) -> Optional[extRCModel]:
        if 0 <= index < len(self._modelTable):
            return self._modelTable[index]
        return None

    def define_process_corner(self, ext_model_index: int, name: str) -> None:
        corner = extCorner(_name=name, _model=ext_model_index, _extDbIndex=len(self._processCornerTable))
        self._processCornerTable.append(corner)
        self._cornerCnt = len(self._processCornerTable) + len(self._scaledCornerTable)
        self._extDbCnt = max(self._extDbCnt, corner._extDbIndex + 1)

    def define_derived_corner(
        self,
        name: str,
        process_corner_name: str,
        res_factor: float,
        cc_factor: float,
        gndc_factor: float,
    ) -> None:
        process_index = self._find_corner_index(process_corner_name, self._processCornerTable)
        corner = extCorner(
            _name=name,
            _model=process_index,
            _extDbIndex=len(self._processCornerTable) + len(self._scaledCornerTable),
            _scaledCornerIdx=process_index,
            _resFactor=res_factor,
            _ccFactor=cc_factor,
            _gndcFactor=gndc_factor,
        )
        self._scaledCornerTable.append(corner)
        self._cornerCnt = len(self._processCornerTable) + len(self._scaledCornerTable)
        self._extDbCnt = max(self._extDbCnt, corner._extDbIndex + 1)

    def get_ext_db_corner(self, name: str) -> int:
        for corner in self._processCornerTable + self._scaledCornerTable:
            if corner._name == name:
                return corner._extDbIndex
        return -1

    def get_corners(self) -> List[str]:
        return [corner._name for corner in self._processCornerTable + self._scaledCornerTable]

    def delete_corners(self) -> None:
        self._processCornerTable.clear()
        self._scaledCornerTable.clear()
        self._cornerCnt = 0
        self._extDbCnt = 0

    def adjust_rc(self, res_factor: float, cc_factor: float, gndc_factor: float) -> None:
        self._resFactor = res_factor
        self._ccFactor = cc_factor
        self._gndcFactor = gndc_factor
        self._resModify = res_factor != 1.0
        self._ccModify = cc_factor != 1.0
        self._gndcModify = gndc_factor != 1.0

    def setExtractionOptions_v2(self, options: ExtractOptions) -> None:
        self._last_extract_options = options
        self._ccUp = options.cc_up
        self._cornerCnt = options.corner_cnt
        self._mergeResBound = options.max_res
        self._mergeViaRes = not options.no_merge_via_res
        self._coupleThreshold = options.coupling_threshold
        self._dgContextDepth = options.context_depth
        self._lef_res = options.lef_res
        self._diagFlow = options.cc_model >= 10

    def setupMappingTables(self, *args: Any, **kwargs: Any) -> None:
        raise _not_translated("extMain::setupMappingTables")

    def makeBlockRCsegs_v2(self, netNames: Optional[str], extRules: Optional[str]) -> None:
        raise _not_translated("extMain::makeBlockRCsegs_v2")

    def makeRCNetwork_v2(self) -> bool:
        raise _not_translated("extMain::makeRCNetwork_v2")

    def makeNetRCsegs(self, *args: Any, **kwargs: Any) -> int:
        raise _not_translated("extMain::makeNetRCsegs")

    def couplingFlow(self, *args: Any, **kwargs: Any) -> int:
        raise _not_translated("extMain::couplingFlow")

    def computeCapacitance(self, *args: Any, **kwargs: Any) -> None:
        raise _not_translated("extMain::computeCapacitance")

    def getRseg(self, *args: Any, **kwargs: Any) -> Any:
        raise _not_translated("extMain::getRseg")

    def extract(self, options: ExtractOptions) -> None:
        self.setExtractionOptions_v2(options)
        raise _not_translated("extMain::extract")

    def write_spef(self, options: SpefOptions) -> None:
        self._last_spef_options = options
        self._spef.writeBlock(options)

    def read_spef(self, opt: ReadSpefOpts) -> None:
        self._last_read_spef_options = opt
        self._spef.readBlock(opt)

    def diff_spef(self, opt: DiffOptions) -> None:
        raise _not_translated("extMain::diff_spef")

    def benchPatternsGen(self, opt: PatternOptions) -> int:
        self._last_bench_options = self._pattern_to_main_options(opt)
        raise _not_translated("extMain::benchPatternsGen")

    def bench_wires(self, bwo: BenchWiresOptions) -> None:
        self._last_bench_options = self._bench_to_main_options(bwo)
        raise _not_translated("extMain::bench_wires")

    def benchVerilog(self, file: str) -> None:
        raise _not_translated("extMain::benchVerilog")

    def overPatterns(self, opt: PatternOptions, *args: Any, **kwargs: Any) -> int:
        raise _not_translated("extMain::overPatterns")

    def UnderPatterns(self, opt: PatternOptions, *args: Any, **kwargs: Any) -> int:
        raise _not_translated("extMain::UnderPatterns")

    def OverUnderPatterns(self, opt: PatternOptions, *args: Any, **kwargs: Any) -> int:
        raise _not_translated("extMain::OverUnderPatterns")

    def write_spef_nets(self, flatten: bool, parallel: bool) -> None:
        self._spef.write_spef_nets(flatten, parallel)

    def getSpef(self) -> extSpef:
        return self._spef

    def setMinRC(self, ii: int, jj: int, rc: extDistRC) -> None:
        self._minCapTable[(ii, jj)] = rc.getTotalCap()
        self._minResTable[(ii, jj)] = rc.getRes()

    def setMaxRC(self, ii: int, jj: int, rc: extDistRC) -> None:
        self._maxCapTable[(ii, jj)] = rc.getTotalCap()
        self._maxResTable[(ii, jj)] = rc.getRes()

    def _find_corner_index(self, name: str, table: List[extCorner]) -> int:
        for idx, corner in enumerate(table):
            if corner._name == name:
                return idx
        return -1

    def _bench_to_main_options(self, bwo: BenchWiresOptions) -> extMainOptions:
        opt = extMainOptions(
            _overDist=bwo.over_dist,
            _underDist=bwo.under_dist,
            _met_cnt=bwo.met_cnt,
            _met=bwo.met,
            _underMet=bwo.under_met,
            _overMet=bwo.over_met,
            _wireCnt=bwo.cnt,
            _topDir=bwo.dir,
            _name=bwo.block,
            _wTable=bwo.w_list if bwo.multiple_widths else bwo.w,
            _sTable=bwo.s_list,
            _thTable=bwo.th_list if bwo.ddd else bwo.th,
            _dTable=bwo.d,
            _default_lef_rules=bwo.default_lef_rules,
            _nondefault_lef_rules=bwo.nondefault_lef_rules,
            _multiple_widths=bwo.multiple_widths,
            _over=bwo.Over,
            _overUnder=bwo.over_under,
            _diag=1 if bwo.diag else 0,
            _db_only=bwo.db_only,
            _gen_def_patterns=bwo.gen_def_patterns,
            _res_patterns=bwo.resPatterns,
            _len=bwo.len,
            _tech=self._tech,
            _block=self._block,
            _rcModel=self.getRCModel(),
            _layerCnt=bwo.met_cnt,
            _v1=bwo.v1,
        )
        opt._widthTable = _parse_number_list(opt._wTable)
        opt._spaceTable = _parse_number_list(opt._sTable)
        opt._thicknessTable = _parse_number_list(opt._thTable)
        opt._densityTable = _parse_number_list(opt._dTable)
        opt._gridTable = _parse_number_list(bwo.grid_list)
        return opt

    def _pattern_to_main_options(self, po: PatternOptions) -> extMainOptions:
        opt = extMainOptions(
            _overDist=po.over_dist,
            _underDist=po.under_dist,
            _met_cnt=po.met_cnt,
            _met=po.met,
            _underMet=po.under_met,
            _overMet=po.over_met,
            _wireCnt=po.wire_cnt,
            _topDir=po.dir,
            _name=po.name,
            _wTable=po.width or "1",
            _sTable=po.spacing or "1",
            _default_lef_rules=po.default_lef_rules,
            _nondefault_lef_rules=po.nondefault_lef_rules,
            _over=po.over,
            _overUnder=po.over_under,
            _diag=1 if po.diag else 0,
            _len=po.len,
            _tech=self._tech,
            _block=self._block,
            _rcModel=self.getRCModel(),
            _layerCnt=po.met_cnt,
        )
        opt._widthTable = _parse_number_list(opt._wTable)
        opt._spaceTable = _parse_number_list(opt._sTable)
        opt._gridTable = _parse_number_list(po.grid_list)
        return opt


class Ext:
    """对应 `rcx::Ext`，OpenRCX 对外入口包装类。"""

    def __init__(self, db: Any = None, logger: Any = None, spef_version: Optional[str] = None) -> None:
        self._db = db
        self.logger_ = logger
        self.spef_version_ = spef_version
        self._ext = extMain(db=db, logger_=logger, spef_version_=spef_version)

    def setLogger(self, logger: Any) -> None:
        self.logger_ = logger
        self._ext.setLogger(logger)

    def bench_wires_gen(self, opt: PatternOptions) -> None:
        self._ext.benchPatternsGen(opt)

    def gen_rcx_model(
        self,
        spef_file_list: str,
        corner_list: str,
        out_file: str,
        comment: str,
        version: str,
        pattern: int,
    ) -> bool:
        raise _not_translated("Ext::gen_rcx_model")

    def define_rcx_corners(self, corner_list: str) -> bool:
        names = [name for name in corner_list.replace(",", " ").split() if name]
        for index, name in enumerate(names):
            self._ext.define_process_corner(index, name)
        return bool(names)

    @staticmethod
    def get_model_corners(ext_model_file: str, logger: Any = None) -> bool:
        raise _not_translated("Ext::get_model_corners")

    def rc_estimate(self, ext_model_file: str, out_file_prefix: str) -> bool:
        raise _not_translated("Ext::rc_estimate")

    def gen_solver_patterns(
        self,
        process_file: str,
        process_name: str,
        version: int,
        wire_cnt: int,
        len: int,
        over_dist: int,
        under_dist: int,
        w_list: str,
        s_list: str,
    ) -> bool:
        raise _not_translated("Ext::gen_solver_patterns")

    def init_rcx_model(self, corner_names: str, metal_cnt: int) -> bool:
        model = extRCModel(_name=corner_names, _layerCnt=metal_cnt)
        for _ in [name for name in corner_names.replace(",", " ").split() if name] or [""]:
            model.addMetRCTable(extMetRCTable(_layerCnt=metal_cnt, logger_=self.logger_))
        self._ext.addRCModel(model)
        return True

    def read_rcx_tables(
        self,
        corner: str,
        filename: str,
        wire: int,
        over: bool,
        under: bool,
        over_under: bool,
        diag: bool,
    ) -> bool:
        raise _not_translated("Ext::read_rcx_tables")

    def write_rcx_model(self, filename: str) -> bool:
        raise _not_translated("Ext::write_rcx_model")

    def write_rules(self, name: str, file: str) -> None:
        raise _not_translated("Ext::write_rules")

    def bench_verilog(self, file: str) -> None:
        self._ext.benchVerilog(file)

    def bench_wires(self, bwo: BenchWiresOptions) -> None:
        self._ext.bench_wires(bwo)

    def write_spef_nets(self, block: Any, flatten: bool, parallel: bool, corner: int) -> None:
        self._ext._block = block
        self._ext._spef._block = block
        self._ext._spef._dbCorner = corner
        self._ext.write_spef_nets(flatten, parallel)

    def extract(self, options: ExtractOptions) -> None:
        self._ext.extract(options)

    def define_process_corner(self, ext_model_index: int, name: str) -> None:
        self._ext.define_process_corner(ext_model_index, name)

    def define_derived_corner(
        self,
        name: str,
        process_corner_name: str,
        res_factor: float,
        cc_factor: float,
        gndc_factor: float,
    ) -> None:
        self._ext.define_derived_corner(name, process_corner_name, res_factor, cc_factor, gndc_factor)

    def get_ext_db_corner(self, name: str) -> int:
        return self._ext.get_ext_db_corner(name)

    def get_corners(self) -> List[str]:
        return self._ext.get_corners()

    def delete_corners(self) -> None:
        self._ext.delete_corners()

    def adjust_rc(self, res_factor: float, cc_factor: float, gndc_factor: float) -> None:
        self._ext.adjust_rc(res_factor, cc_factor, gndc_factor)

    def write_spef(self, options: SpefOptions) -> None:
        self._ext.write_spef(options)

    def read_spef(self, opt: ReadSpefOpts) -> None:
        self._ext.read_spef(opt)

    def diff_spef(self, opt: DiffOptions) -> None:
        self._ext.diff_spef(opt)

    def calibrate(
        self,
        spef_file: str,
        db_corner_name: str,
        corner: int,
        spef_corner: int,
        m_map: bool,
        upper_limit: float,
        lower_limit: float,
    ) -> None:
        raise _not_translated("Ext::calibrate")


OpenRCX = Ext


__all__ = [
    "BenchWiresOptions",
    "ExtractOptions",
    "SpefOptions",
    "ReadSpefOpts",
    "DiffOptions",
    "PatternOptions",
    "CoupleOptions",
    "CoupleAndCompute",
    "extDistRC",
    "extDistRCTable",
    "extDistWidthRCTable",
    "extMetRCTable",
    "extViaModel",
    "extRCTable",
    "extCorner",
    "extMainOptions",
    "extRCModel",
    "CouplingState",
    "CouplingDimensionParams",
    "SegmentTables",
    "extMeasure",
    "extMeasureRC",
    "extSpef",
    "extMain",
    "Ext",
    "OpenRCX",
]
