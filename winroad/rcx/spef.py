"""SPEF reader/writer state for rcx.

The real parser and writer are intentionally still untranslated and keep raising
``NotImplementedError`` from their OpenROAD boundary methods.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, List, Optional

from .common import _not_translated
from .options import ReadSpefOpts, SpefOptions

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


