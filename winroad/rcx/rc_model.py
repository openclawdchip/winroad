"""RC model and rule-table boundaries for WinRoad rcx."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Iterable, List, Optional

from .common import _not_translated

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


