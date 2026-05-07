"""CTS characterization containers."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from typing import Any, Callable, Dict, Iterable, List, Optional, Tuple

from .options import CtsOptions
from .types import _not_translated


@dataclass
class TechCharSolutionData:
    """对应 `TechChar::SolutionData` 的外层数据载体。"""

    net_vector: List[Any] = field(default_factory=list)
    nodes_without_buf_vector: List[int] = field(default_factory=list)
    in_port: Any = None
    out_port: Any = None
    inst_vector: List[Any] = field(default_factory=list)
    topology_descriptor: List[str] = field(default_factory=list)
    is_pure_wire: bool = True


@dataclass
class TechCharResultData:
    """对应 `TechChar::ResultData` 的 LUT 编译输入记录。"""

    load: float = 0.0
    in_slew: float = 0.0
    wirelength: float = 0.0
    pin_slew: float = 0.0
    pin_arrival: float = 0.0
    totalcap: float = 0.0
    total_power: float = 0.0
    is_pure_wire: bool = True
    topology: List[str] = field(default_factory=list)


@dataclass(order=True, frozen=True)
class TechCharKey:
    """对应 `TechChar::CharKey`，用于 characterization 结果排序。"""

    load: float
    wirelength: float
    pin_slew: float
    totalcap: float


@dataclass
class TechChar:
    """对应 `TechChar`，保存 CTS characterization 的外层状态。"""

    options: Optional[CtsOptions] = None
    db: Any = None
    open_sta: Any = None
    db_network: Any = None
    delay_lut: Dict[Tuple[int, int, int], List[int]] = field(default_factory=dict)
    slew_lut: Dict[Tuple[int, int, int], List[int]] = field(default_factory=dict)
    wire_segments: List["WireSegment"] = field(default_factory=list)
    key_to_wire_segments: Dict[Tuple[int, int, int], List[int]] = field(default_factory=dict)
    length_unit: int = 0
    length_unit_ratio: int = 0
    min_segment_length: int = 0
    max_segment_length: int = 0
    min_capacitance: int = 0
    max_capacitance: int = 0
    min_slew: int = 0
    max_slew: int = 0
    actual_min_input_cap: int = 0
    res_per_dbu: float = 0.0
    cap_per_dbu: float = 0.0
    char_slew_step_size: float = 0.0
    char_cap_step_size: float = 0.0
    master_names: List[str] = field(default_factory=list)
    wirelengths_to_test: List[float] = field(default_factory=list)
    loads_to_test: List[float] = field(default_factory=list)
    slews_to_test: List[float] = field(default_factory=list)
    solution_map: Dict[Any, List[Any]] = field(default_factory=dict)
    result_data: List[TechCharResultData] = field(default_factory=list)
    solution_data: List[TechCharSolutionData] = field(default_factory=list)
    characterization_initialized: bool = False

    def characterize(self) -> None:
        _not_translated("TechChar::characterize")

    def create(self) -> None:
        _not_translated("TechChar::create")

    def report(self) -> Dict[str, Any]:
        """返回当前 LUT/segment 外层状态快照。"""

        validation = self.validateLut()
        return {
            "num_wire_segments": len(self.wire_segments),
            "num_lut_keys": len(self.key_to_wire_segments),
            "min_segment_length": self.min_segment_length,
            "max_segment_length": self.max_segment_length,
            "min_capacitance": self.min_capacitance,
            "max_capacitance": self.max_capacitance,
            "min_slew": self.min_slew,
            "max_slew": self.max_slew,
            "length_unit": self.length_unit,
            "num_delay_lut_keys": len(self.delay_lut),
            "num_slew_lut_keys": len(self.slew_lut),
            "num_results": len(self.result_data),
            "num_solutions": len(self.solution_data),
            "valid": not validation,
            "validation_errors": validation,
        }

    def reportSegment(self, key: Any) -> List[Dict[str, Any]]:
        """按 C++ key 或 `(length, load, slew)` key 返回 segment 摘要。"""

        tuple_key = self.decodeKey(key) if isinstance(key, int) else key
        return [
            self._segmentReport(idx, self.wire_segments[idx])
            for idx in self.key_to_wire_segments.get(tuple_key, [])
        ]

    def reportSegments(self, length: int, load: int, output_slew: int) -> List[Dict[str, Any]]:
        return self.reportSegment(self.makeKey(length, load, output_slew))

    def createWireSegment(self, length: float, cap: float = 0.0, res: float = 0.0) -> "WireSegment":
        """创建 wire segment 记录。"""

        segment = WireSegment(length=length, cap=cap, res=res)
        self.wire_segments.append(segment)
        return segment

    def addWireSegment(self, key: Tuple[int, int, int], segment: "WireSegment") -> int:
        idx = len(self.wire_segments)
        self.wire_segments.append(segment)
        self.key_to_wire_segments.setdefault(key, []).append(idx)
        self._updateBoundsFromSegment(key, segment)
        return idx

    def forEachWireSegment(self, func: Callable[..., None]) -> None:
        for idx, segment in enumerate(self.wire_segments):
            try:
                func(idx, segment)
            except TypeError:
                func(segment)

    def forEachWireSegmentByKey(
        self, key: Tuple[int, int, int], func: Callable[[int, "WireSegment"], None]
    ) -> None:
        for idx in self.key_to_wire_segments.get(key, []):
            func(idx, self.wire_segments[idx])

    def getWireSegment(self, idx: int) -> "WireSegment":
        return self.wire_segments[idx]

    def getMinSegmentLength(self) -> int:
        return self.min_segment_length

    def getMaxSegmentLength(self) -> int:
        return self.max_segment_length

    def getMaxCapacitance(self) -> int:
        return self.max_capacitance

    def getMinCapacitance(self) -> int:
        return self.min_capacitance

    def getMinSlew(self) -> int:
        return self.min_slew

    def getMaxSlew(self) -> int:
        return self.max_slew

    def setActualMinInputCap(self, cap: int) -> None:
        self.actual_min_input_cap = cap

    def getActualMinInputCap(self) -> int:
        return self.actual_min_input_cap

    def getLengthUnit(self) -> int:
        return self.length_unit

    def setLengthUnit(self, length: int) -> None:
        self.length_unit = length

    def createFakeEntries(self, length: int, fake_length: int) -> None:
        _not_translated("TechChar::createFakeEntries")

    def getCapPerDBU(self) -> float:
        return self.cap_per_dbu

    def getResPerDBU(self) -> float:
        return self.res_per_dbu

    def getLogger(self) -> Any:
        return self.options.getLogger() if self.options is not None else None

    def printCharacterization(self) -> Dict[str, Any]:
        return self.report()

    def printSolution(self) -> List[TechCharResultData]:
        return list(self.result_data)

    def compileLut(self, lut_solutions: Iterable[Any]) -> None:
        """编译已给定的结果对象到 Python LUT 容器。

        STA 求解、拓扑枚举和 Liberty 查表仍由未翻译的 C++ 算法负责；这里
        只接收外部结果并建立与 `TechChar` 相同的索引边界。
        """

        for raw in lut_solutions:
            result = raw if isinstance(raw, TechCharResultData) else TechCharResultData(
                load=float(getattr(raw, "load", 0.0)),
                in_slew=float(getattr(raw, "in_slew", getattr(raw, "inSlew", 0.0))),
                wirelength=float(getattr(raw, "wirelength", 0.0)),
                pin_slew=float(getattr(raw, "pin_slew", getattr(raw, "pinSlew", 0.0))),
                pin_arrival=float(getattr(raw, "pin_arrival", getattr(raw, "pinArrival", 0.0))),
                totalcap=float(getattr(raw, "totalcap", 0.0)),
                total_power=float(getattr(raw, "total_power", getattr(raw, "totalPower", 0.0))),
                is_pure_wire=bool(getattr(raw, "is_pure_wire", getattr(raw, "isPureWire", True))),
                topology=list(getattr(raw, "topology", [])),
            )
            self.result_data.append(result)
            length_key = self.toInternalLengthUnit(int(round(result.wirelength)))
            load_key = int(round(result.load))
            slew_key = int(round(result.pin_slew))
            key = self.makeKey(length_key, load_key, slew_key)
            segment = WireSegment(
                length=result.wirelength,
                power=result.total_power,
                segment_delay=int(round(result.pin_arrival)),
                cap=result.totalcap,
                slew=result.pin_slew,
                load=load_key,
                output_slew=slew_key,
            )
            for master in result.topology:
                segment.addBufferMaster(master)
            self.addWireSegment(key, segment)
            self.delay_lut.setdefault(key, []).append(segment.getDelay())
            self.slew_lut.setdefault(key, []).append(slew_key)
            self.solution_map.setdefault(TechCharKey(result.load, result.wirelength, result.pin_slew, result.totalcap), []).append(result)

    def addLutEntry(
        self,
        length: int,
        load: int,
        output_slew: int,
        delay: int,
        slew: Optional[int] = None,
        segment: Optional["WireSegment"] = None,
    ) -> int:
        """Add one precomputed characterization entry to the LUT containers."""

        key = self.makeKey(length, load, output_slew)
        stored = segment or WireSegment(
            length=length,
            segment_delay=delay,
            load=load,
            output_slew=output_slew,
            slew=float(output_slew if slew is None else slew),
        )
        idx = self.addWireSegment(key, stored)
        self.delay_lut.setdefault(key, []).append(delay)
        self.slew_lut.setdefault(key, []).append(output_slew if slew is None else slew)
        return idx

    def hasLutEntry(self, length: int, load: int, output_slew: int) -> bool:
        key = self.makeKey(length, load, output_slew)
        return key in self.delay_lut or key in self.slew_lut or key in self.key_to_wire_segments

    def getDelayLut(self) -> Dict[Tuple[int, int, int], List[int]]:
        return {key: list(values) for key, values in self.delay_lut.items()}

    def getSlewLut(self) -> Dict[Tuple[int, int, int], List[int]]:
        return {key: list(values) for key, values in self.slew_lut.items()}

    def getDelay(self, length: int, load: int, output_slew: int, idx: int = 0) -> int:
        return self.delay_lut[self.makeKey(length, load, output_slew)][idx]

    def getSlew(self, length: int, load: int, output_slew: int, idx: int = 0) -> int:
        return self.slew_lut[self.makeKey(length, load, output_slew)][idx]

    def getSegmentsForKey(self, length: int, load: int, output_slew: int) -> List["WireSegment"]:
        key = self.makeKey(length, load, output_slew)
        return [self.wire_segments[idx] for idx in self.key_to_wire_segments.get(key, [])]

    def computeKey(self, length: int, load: int, output_slew: int) -> int:
        return (length << 20) | (load << 10) | output_slew

    def decodeKey(self, key: int) -> Tuple[int, int, int]:
        return ((key >> 20) & 0xFFF, (key >> 10) & 0x3FF, key & 0x3FF)

    def makeKey(self, length: int, load: int, output_slew: int) -> Tuple[int, int, int]:
        return (length, load, output_slew)

    def initLengthUnits(self) -> None:
        _not_translated("TechChar::initLengthUnits")

    def reportCharacterizationBounds(self) -> Dict[str, int]:
        return {
            "min_segment_length": self.min_segment_length,
            "max_segment_length": self.max_segment_length,
            "min_capacitance": self.min_capacitance,
            "max_capacitance": self.max_capacitance,
            "min_slew": self.min_slew,
            "max_slew": self.max_slew,
        }

    def checkCharacterizationBounds(self) -> bool:
        return (
            self.min_segment_length <= self.max_segment_length
            and self.min_capacitance <= self.max_capacitance
            and self.min_slew <= self.max_slew
        )

    def toInternalLengthUnit(self, length: int) -> int:
        if self.length_unit <= 0:
            return length
        return int(round(length / self.length_unit))

    def reset(self) -> None:
        self.delay_lut.clear()
        self.slew_lut.clear()
        self.wire_segments.clear()
        self.key_to_wire_segments.clear()
        self.solution_map.clear()
        self.result_data.clear()
        self.solution_data.clear()
        self.characterization_initialized = False

    def initCharacterization(self) -> None:
        self.characterization_initialized = True

    def exportLut(self, path: Optional[str] = None) -> Dict[str, Any]:
        data = {
            "delay_lut": self._encodeLut(self.delay_lut),
            "slew_lut": self._encodeLut(self.slew_lut),
            "key_to_wire_segments": self._encodeLut(self.key_to_wire_segments),
            "wire_segments": [segment.toDict() for segment in self.wire_segments],
            "bounds": self.reportCharacterizationBounds(),
            "length_unit": self.length_unit,
            "length_unit_ratio": self.length_unit_ratio,
            "actual_min_input_cap": self.actual_min_input_cap,
            "res_per_dbu": self.res_per_dbu,
            "cap_per_dbu": self.cap_per_dbu,
            "char_slew_step_size": self.char_slew_step_size,
            "char_cap_step_size": self.char_cap_step_size,
            "master_names": list(self.master_names),
            "wirelengths_to_test": list(self.wirelengths_to_test),
            "loads_to_test": list(self.loads_to_test),
            "slews_to_test": list(self.slews_to_test),
            "result_data": [asdict(result) for result in self.result_data],
            "solution_data": [asdict(solution) for solution in self.solution_data],
            "characterization_initialized": self.characterization_initialized,
        }
        if path is not None:
            with open(path, "w", encoding="utf-8") as stream:
                json.dump(data, stream, indent=2, sort_keys=True)
        return data

    def importLut(self, data_or_path: Any, clear: bool = True) -> None:
        if isinstance(data_or_path, str):
            with open(data_or_path, "r", encoding="utf-8") as stream:
                data_or_path = json.load(stream)
        data = dict(data_or_path)
        if clear:
            self.reset()
        self.delay_lut.update(self._decodeLut(data.get("delay_lut", {})))
        self.slew_lut.update(self._decodeLut(data.get("slew_lut", {})))
        self.key_to_wire_segments.update(self._decodeLut(data.get("key_to_wire_segments", {})))
        self.wire_segments.extend(WireSegment.fromDict(item) for item in data.get("wire_segments", []))
        bounds = data.get("bounds", {})
        self.min_segment_length = int(bounds.get("min_segment_length", self.min_segment_length))
        self.max_segment_length = int(bounds.get("max_segment_length", self.max_segment_length))
        self.min_capacitance = int(bounds.get("min_capacitance", self.min_capacitance))
        self.max_capacitance = int(bounds.get("max_capacitance", self.max_capacitance))
        self.min_slew = int(bounds.get("min_slew", self.min_slew))
        self.max_slew = int(bounds.get("max_slew", self.max_slew))
        self.length_unit = int(data.get("length_unit", self.length_unit))
        self.length_unit_ratio = int(data.get("length_unit_ratio", self.length_unit_ratio))
        self.actual_min_input_cap = int(data.get("actual_min_input_cap", self.actual_min_input_cap))
        self.res_per_dbu = float(data.get("res_per_dbu", self.res_per_dbu))
        self.cap_per_dbu = float(data.get("cap_per_dbu", self.cap_per_dbu))
        self.char_slew_step_size = float(data.get("char_slew_step_size", self.char_slew_step_size))
        self.char_cap_step_size = float(data.get("char_cap_step_size", self.char_cap_step_size))
        self.master_names = list(data.get("master_names", self.master_names))
        self.wirelengths_to_test = list(data.get("wirelengths_to_test", self.wirelengths_to_test))
        self.loads_to_test = list(data.get("loads_to_test", self.loads_to_test))
        self.slews_to_test = list(data.get("slews_to_test", self.slews_to_test))
        self.result_data.extend(TechCharResultData(**item) for item in data.get("result_data", []))
        self.solution_data.extend(TechCharSolutionData(**item) for item in data.get("solution_data", []))
        self.characterization_initialized = bool(
            data.get("characterization_initialized", self.characterization_initialized)
        )

    def dumpLut(self, path: str) -> Dict[str, Any]:
        return self.exportLut(path)

    def loadLut(self, path: str) -> None:
        self.importLut(path)

    def validateLut(self) -> List[str]:
        """检查 LUT、key 到 segment 索引和 bounds 的一致性。

        这不是 characterization 正确性证明，只确认 Python 状态层没有
        悬空索引、反向边界或负延迟/负 slew 等明显损坏。
        """

        errors: List[str] = []
        all_keys = set(self.delay_lut) | set(self.slew_lut) | set(self.key_to_wire_segments)
        for key in all_keys:
            if len(key) != 3:
                errors.append(f"LUT key {key} 不是三元组")
                continue
            length, load, output_slew = key
            if length < 0 or load < 0 or output_slew < 0:
                errors.append(f"LUT key {key} 含负值")
            for value in self.delay_lut.get(key, []):
                if value < 0:
                    errors.append(f"delay_lut[{key}] 含负延迟 {value}")
            for value in self.slew_lut.get(key, []):
                if value < 0:
                    errors.append(f"slew_lut[{key}] 含负 slew {value}")
            for idx in self.key_to_wire_segments.get(key, []):
                if idx < 0 or idx >= len(self.wire_segments):
                    errors.append(f"key_to_wire_segments[{key}] 引用越界 segment {idx}")
        for idx, segment in enumerate(self.wire_segments):
            errors.extend(f"wire_segments[{idx}]: {error}" for error in segment.validate())
        if not self.checkCharacterizationBounds():
            errors.append("characterization bounds 最小值大于最大值")
        if self.length_unit < 0 or self.length_unit_ratio < 0:
            errors.append("length_unit/length_unit_ratio 不能为负数")
        if self.res_per_dbu < 0.0 or self.cap_per_dbu < 0.0:
            errors.append("res_per_dbu/cap_per_dbu 不能为负数")
        return errors

    def finalizeRootSinkBuffers(self) -> None:
        _not_translated("TechChar::finalizeRootSinkBuffers")

    def trimSortBufferList(self, buffers: List[str]) -> None:
        buffers[:] = sorted({buf for buf in buffers if buf})

    def getMaxCapLimit(self, buf: str) -> float:
        _not_translated("TechChar::getMaxCapLimit")

    def collectSlewsLoadsFromTableAxis(self, *args: Any, **kwargs: Any) -> None:
        _not_translated("TechChar::collectSlewsLoadsFromTableAxis")

    def sortAndUniquify(self, values: List[float], name: str = "") -> None:
        values[:] = sorted(set(values))

    def reduceOrExpand(self, values: List[float], limit: int) -> None:
        _not_translated("TechChar::reduceOrExpand")

    def smallestDiffIter(self, values: List[float]) -> int:
        _not_translated("TechChar::smallestDiffIter")

    def largestDiffIter(self, values: List[float]) -> int:
        _not_translated("TechChar::largestDiffIter")

    def createPatterns(self, setup_wirelength: int) -> List[TechCharSolutionData]:
        _not_translated("TechChar::createPatterns")

    def createStaInstance(self) -> None:
        _not_translated("TechChar::createStaInstance")

    def setParasitics(self, *args: Any, **kwargs: Any) -> None:
        _not_translated("TechChar::setParasitics")

    def computeTopologyResults(self, *args: Any, **kwargs: Any) -> TechCharResultData:
        _not_translated("TechChar::computeTopologyResults")

    def updateBufferTopologies(self, solution: TechCharSolutionData) -> None:
        _not_translated("TechChar::updateBufferTopologies")

    def updateBufferTopologiesOld(self, solution: TechCharSolutionData) -> None:
        _not_translated("TechChar::updateBufferTopologiesOld")

    def cellNameToID(self, master_name: str) -> int:
        _not_translated("TechChar::cellNameToID")

    def getCurrConfig(self, solution: TechCharSolutionData) -> List[int]:
        _not_translated("TechChar::getCurrConfig")

    def getNextConfig(self, curr_config: List[int]) -> List[int]:
        _not_translated("TechChar::getNextConfig")

    def getMasterFromConfig(self, next_config: List[int], idx: int = 0) -> Any:
        _not_translated("TechChar::getMasterFromConfig")

    def swapTopologyBuffer(self, solution: TechCharSolutionData, *args: Any) -> None:
        _not_translated("TechChar::swapTopologyBuffer")

    def _segmentReport(self, idx: int, segment: "WireSegment") -> Dict[str, Any]:
        return {
            "idx": idx,
            "length": segment.getLength(),
            "load": segment.getLoad(),
            "output_slew": segment.getOutputSlew(),
            "delay": segment.getDelay(),
            "power": segment.getPower(),
            "buffer_masters": segment.getBufferMasters(),
            "buffer_locations": segment.getBufferLocations(),
        }

    def _updateBoundsFromSegment(self, key: Tuple[int, int, int], segment: "WireSegment") -> None:
        length, load, output_slew = key
        values = {
            "min_segment_length": length,
            "max_segment_length": length,
            "min_capacitance": load,
            "max_capacitance": load,
            "min_slew": output_slew,
            "max_slew": output_slew,
        }
        for attr, value in values.items():
            current = getattr(self, attr)
            if current == 0 and len(self.wire_segments) == 1:
                setattr(self, attr, value)
            elif attr.startswith("min_"):
                setattr(self, attr, min(current, value))
            else:
                setattr(self, attr, max(current, value))

    def _encodeLut(self, lut: Dict[Tuple[int, int, int], List[int]]) -> Dict[str, List[int]]:
        return {self._keyToString(key): list(values) for key, values in lut.items()}

    def _decodeLut(self, lut: Dict[str, List[int]]) -> Dict[Tuple[int, int, int], List[int]]:
        return {self._stringToKey(key): list(values) for key, values in lut.items()}

    def _keyToString(self, key: Tuple[int, int, int]) -> str:
        return ",".join(str(part) for part in key)

    def _stringToKey(self, key: str) -> Tuple[int, int, int]:
        parts = [int(part) for part in key.split(",")]
        if len(parts) != 3:
            raise ValueError(f"无效 TechChar LUT key: {key}")
        return (parts[0], parts[1], parts[2])


@dataclass
class WireSegment:
    """对应 `TechChar.h` 中用于特征化的 wire segment。"""

    length: float
    power: float = 0.0
    segment_delay: int = 0
    input_cap: int = 0
    input_slew: int = 0
    load: int = 0
    output_slew: int = 0
    cap: float = 0.0
    res: float = 0.0
    delay: float = 0.0
    slew: float = 0.0
    buffer_locations: List[float] = field(default_factory=list)
    buffer_masters: List[str] = field(default_factory=list)
    wl2_first_buffer: int = 0
    last_wl: int = 0

    def addBuffer(self, location: float) -> None:
        self.buffer_locations.append(location)

    def addBufferMaster(self, name: str) -> None:
        self.buffer_masters.append(name)

    def setWl2FirstBuffer(self, wl: int) -> None:
        self.wl2_first_buffer = wl

    def setLastWl(self, wl: int) -> None:
        self.last_wl = wl

    def getPower(self) -> float:
        return self.power

    def getDelay(self) -> int:
        return self.segment_delay

    def getInputCap(self) -> int:
        return self.input_cap

    def getInputSlew(self) -> int:
        return self.input_slew

    def getLength(self) -> int:
        return int(round(self.length))

    def getLoad(self) -> int:
        return self.load

    def getOutputSlew(self) -> int:
        return self.output_slew

    def getWl2FirstBuffer(self) -> int:
        return self.wl2_first_buffer

    def getLastWl(self) -> int:
        return self.last_wl

    def isBuffered(self) -> bool:
        return bool(self.buffer_locations)

    def getNumBuffers(self) -> int:
        return len(self.buffer_locations)

    def getBufferLocations(self) -> List[float]:
        return list(self.buffer_locations)

    def getBufferMasters(self) -> List[str]:
        return list(self.buffer_masters)

    def getBufferLocation(self, idx: int) -> float:
        return self.buffer_locations[idx]

    def getBufferMaster(self, idx: int) -> str:
        return self.buffer_masters[idx]

    def toDict(self) -> Dict[str, Any]:
        return {
            "length": self.length,
            "power": self.power,
            "segment_delay": self.segment_delay,
            "input_cap": self.input_cap,
            "input_slew": self.input_slew,
            "load": self.load,
            "output_slew": self.output_slew,
            "cap": self.cap,
            "res": self.res,
            "delay": self.delay,
            "slew": self.slew,
            "buffer_locations": list(self.buffer_locations),
            "buffer_masters": list(self.buffer_masters),
            "wl2_first_buffer": self.wl2_first_buffer,
            "last_wl": self.last_wl,
        }

    def validate(self) -> List[str]:
        """检查 wire segment 数据是否可被 LUT 容器安全引用。"""

        errors: List[str] = []
        if self.length < 0.0:
            errors.append("length 不能为负数")
        if self.power < 0.0:
            errors.append("power 不能为负数")
        if self.segment_delay < 0:
            errors.append("segment_delay 不能为负数")
        if self.input_cap < 0 or self.input_slew < 0:
            errors.append("input_cap/input_slew 不能为负数")
        if self.load < 0 or self.output_slew < 0:
            errors.append("load/output_slew 不能为负数")
        if self.cap < 0.0 or self.res < 0.0:
            errors.append("cap/res 不能为负数")
        if len(self.buffer_masters) not in {0, len(self.buffer_locations)}:
            errors.append("buffer_masters 数量需要为 0 或与 buffer_locations 一致")
        return errors

    @classmethod
    def fromDict(cls, data: Dict[str, Any]) -> "WireSegment":
        return cls(
            length=float(data.get("length", 0.0)),
            power=float(data.get("power", 0.0)),
            segment_delay=int(data.get("segment_delay", 0)),
            input_cap=int(data.get("input_cap", 0)),
            input_slew=int(data.get("input_slew", 0)),
            load=int(data.get("load", 0)),
            output_slew=int(data.get("output_slew", 0)),
            cap=float(data.get("cap", 0.0)),
            res=float(data.get("res", 0.0)),
            delay=float(data.get("delay", 0.0)),
            slew=float(data.get("slew", 0.0)),
            buffer_locations=list(data.get("buffer_locations", [])),
            buffer_masters=list(data.get("buffer_masters", [])),
            wl2_first_buffer=int(data.get("wl2_first_buffer", 0)),
            last_wl=int(data.get("last_wl", 0)),
        )
