"""Top-level OpenRCX facade and extMain orchestration state."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from .bench import bench_to_main_options, pattern_to_main_options
from .common import _not_translated
from .corner import extCorner
from .measure import CouplingDimensionParams, CouplingState, SegmentTables, extMeasure, extMeasureRC
from .options import BenchWiresOptions, DiffOptions, ExtractOptions, PatternOptions, ReadSpefOpts, SpefOptions, extMainOptions
from .rc_model import extDistRC, extMetRCTable, extRCModel
from .spef import extSpef

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
    _extractCornerCnt: int = 0
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
        self._sync_spef_state()

    def setLogger(self, logger: Any) -> None:
        self.logger_ = logger
        self._spef.logger_ = logger

    def configure(self, **kwargs: Any) -> None:
        """Apply rcx runtime configuration that has a concrete Python state."""

        allowed = {"tech", "block", "spef_version", "logger", "current_model"}
        unknown = sorted(set(kwargs) - allowed)
        if unknown:
            raise ValueError(f"未知 rcx 配置项: {', '.join(unknown)}")
        if "tech" in kwargs:
            self._tech = kwargs["tech"]
        if "block" in kwargs:
            self._block = kwargs["block"]
        if "spef_version" in kwargs:
            self.spef_version_ = kwargs["spef_version"]
        if "logger" in kwargs:
            self.setLogger(kwargs["logger"])
        if "current_model" in kwargs:
            self._currentModel = kwargs["current_model"]
        self._sync_spef_state()

    def _sync_spef_state(self) -> None:
        self._spef.logger_ = self.logger_
        self._spef._tech = self._tech
        self._spef._block = self._block
        self._spef._version = self.spef_version_
        self._spef._ext = self

    def addRCModel(self, model: extRCModel) -> int:
        self._modelTable.append(model)
        if self._currentModel is None:
            self._currentModel = model
        return len(self._modelTable) - 1

    def getRCModel(self, index: int = 0) -> Optional[extRCModel]:
        if 0 <= index < len(self._modelTable):
            return self._modelTable[index]
        return None

    def define_process_corner(self, ext_model_index: int, name: str) -> None:
        if self.get_ext_db_corner(name) >= 0:
            raise ValueError(f"rcx corner 已存在: {name}")
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
        if self.get_ext_db_corner(name) >= 0:
            raise ValueError(f"rcx corner 已存在: {name}")
        process_index = self._find_corner_index(process_corner_name, self._processCornerTable)
        if process_index < 0:
            raise ValueError(f"未知 process corner: {process_corner_name}")
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
        self._extractCornerCnt = options.corner_cnt
        self._mergeResBound = options.max_res
        self._mergeViaRes = not options.no_merge_via_res
        self._coupleThreshold = options.coupling_threshold
        self._dgContextDepth = options.context_depth
        self._lef_res = options.lef_res
        self._diagFlow = options.cc_model >= 10

    def get_config(self) -> Dict[str, Any]:
        return {
            "spef_version": self.spef_version_,
            "tech_set": self._tech is not None,
            "block_set": self._block is not None,
            "model_count": len(self._modelTable),
            "current_model": None if self._currentModel is None else self._currentModel._name,
            "corners": self.get_corners(),
            "rc_factors": {
                "res": self._resFactor,
                "cc": self._ccFactor,
                "gndc": self._gndcFactor,
            },
            "extraction": None if self._last_extract_options is None else dict(self._last_extract_options.__dict__),
            "last_spef": None if self._last_spef_options is None else dict(self._last_spef_options.__dict__),
            "last_read_spef": None if self._last_read_spef_options is None else dict(self._last_read_spef_options.__dict__),
            "last_bench": None if self._last_bench_options is None else dict(self._last_bench_options.__dict__),
        }

    def get_status(self) -> Dict[str, Any]:
        return {
            "extracted": self._extracted,
            "extract_runs": self._extRun,
            "corner_count": len(self._processCornerTable) + len(self._scaledCornerTable),
            "extract_corner_count": self._extractCornerCnt,
            "ext_db_count": self._extDbCnt,
            "process_corner_count": len(self._processCornerTable),
            "scaled_corner_count": len(self._scaledCornerTable),
            "model_count": len(self._modelTable),
            "spef_in": self._spef._inFile,
            "spef_out": self._spef._outFile,
            "spef_corner": self._spef._dbCorner,
            "net_no_wire_count": self._netNoWireCnt,
            "min_rc_count": len(self._minCapTable),
            "max_rc_count": len(self._maxCapTable),
            "unimplemented_boundaries": [
                "extract",
                "read_spef",
                "write_spef",
                "diff_spef",
                "bench_wires",
            ],
        }

    def report(self) -> str:
        status = self.get_status()
        cfg = self.get_config()
        lines = [
            "rcx status",
            f"  models: {status['model_count']}",
            f"  corners: {status['corner_count']} ({', '.join(cfg['corners']) or 'none'})",
            f"  extracted: {status['extracted']}",
            f"  spef: in={status['spef_in'] or '-'} out={status['spef_out'] or '-'} corner={status['spef_corner']}",
            (
                "  rc factors: "
                f"res={cfg['rc_factors']['res']} cc={cfg['rc_factors']['cc']} "
                f"gndc={cfg['rc_factors']['gndc']}"
            ),
            f"  tech/block: tech_set={cfg['tech_set']} block_set={cfg['block_set']}",
            "  real extraction/SPEF parser/writer: not implemented",
        ]
        return "\n".join(lines)

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
        return bench_to_main_options(self, bwo)

    def _pattern_to_main_options(self, po: PatternOptions) -> extMainOptions:
        return pattern_to_main_options(self, po)


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

    def configure(self, **kwargs: Any) -> None:
        if "logger" in kwargs:
            self.logger_ = kwargs["logger"]
        self._ext.configure(**kwargs)

    def get_config(self) -> Dict[str, Any]:
        return self._ext.get_config()

    def get_status(self) -> Dict[str, Any]:
        return self._ext.get_status()

    def report(self) -> str:
        return self._ext.report()

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


