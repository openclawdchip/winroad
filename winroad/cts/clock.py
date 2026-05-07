"""Clock network data model for CTS."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Dict, Iterable, Iterator, List, Optional, Tuple

from .types import InstType


@dataclass
class ClockInst:
    """对应 `ClockInst`，表示 CTS 内部的 buffer 或 sink。"""

    name: str
    master: str
    type: InstType
    x: int
    y: int
    input_pin_obj: Any = None
    input_cap: float = 0.0
    insertion_delay: float = 0.0
    output_cap: float = 0.0
    ideal_output_cap: float = 0.0
    inst_obj: Any = None

    def __hash__(self) -> int:
        return id(self)

    def getName(self) -> str:
        return self.name

    def getMaster(self) -> str:
        return self.master

    def getX(self) -> int:
        return self.x

    def getY(self) -> int:
        return self.y

    def getLocation(self) -> Tuple[int, int]:
        return (self.x, self.y)

    def isClockBuffer(self) -> bool:
        return self.type is InstType.CLOCK_BUFFER


@dataclass
class ClockSubNet:
    """对应 `ClockSubNet`，第一个实例为 driver，后续实例为 sink。"""

    name: str
    instances: List[ClockInst] = field(default_factory=list)
    leaf_level: bool = False

    def setLeafLevel(self, is_leaf: bool) -> None:
        self.leaf_level = is_leaf

    def isLeafLevel(self) -> bool:
        return self.leaf_level

    def addInst(self, inst: ClockInst) -> None:
        self.instances.append(inst)

    def setDriver(self, inst: ClockInst) -> None:
        if self.instances:
            self.instances[0] = inst
        else:
            self.instances.append(inst)

    def getName(self) -> str:
        return self.name

    def getInsts(self) -> List[ClockInst]:
        return list(self.instances)

    def getSinks(self) -> List[ClockInst]:
        return list(self.instances[1:])

    def getNumSinks(self) -> int:
        return max(0, len(self.instances) - 1)

    def getDriver(self) -> ClockInst:
        if not self.instances:
            raise IndexError("ClockSubNet 没有 driver")
        return self.instances[0]

    def forEachSink(self, func: Callable[[ClockInst], None]) -> None:
        for inst in self.instances[1:]:
            func(inst)

    def forEachInst(self, func: Callable[[ClockInst], None]) -> None:
        for inst in self.instances:
            func(inst)

    def __iter__(self) -> Iterator[ClockInst]:
        return iter(self.instances)


@dataclass
class Clock:
    """对应 `Clock`，保存一个 CTS clock network。"""

    net_name: str
    clock_pin: str
    sdc_clock_name: str
    clock_pin_x: int
    clock_pin_y: int
    clock_buffers: List[ClockInst] = field(default_factory=list)
    sinks: List[ClockInst] = field(default_factory=list)
    sub_nets: List[ClockSubNet] = field(default_factory=list)
    name_to_inst: Dict[str, ClockInst] = field(default_factory=dict)

    def addClockBuffer(self, name: str, master: str, x: int, y: int) -> ClockInst:
        full_name = f"{name}_{self.getName()}"
        inst = ClockInst(full_name, master, InstType.CLOCK_BUFFER, x, y)
        self.clock_buffers.append(inst)
        self.name_to_inst[full_name] = inst
        return inst

    def findClockByName(self, name: str) -> Optional[ClockInst]:
        return self.name_to_inst.get(name)

    def addSubNet(self, name: str) -> ClockSubNet:
        subnet = ClockSubNet(f"{name}_{self.getName()}")
        self.sub_nets.append(subnet)
        return subnet

    def addSubNetObj(self, subnet: ClockSubNet) -> None:
        self.sub_nets.append(subnet)

    def addSink(
        self,
        name: str,
        x: int,
        y: int,
        pin_obj: Any = None,
        input_cap: float = 0.0,
        ins_delay: float = 0.0,
    ) -> ClockInst:
        sink = ClockInst(
            name,
            "",
            InstType.CLOCK_SINK,
            x,
            y,
            pin_obj,
            input_cap,
            ins_delay,
        )
        self.sinks.append(sink)
        self.name_to_inst[name] = sink
        return sink

    def getName(self) -> str:
        return self.net_name

    def getSdcName(self) -> str:
        return self.sdc_clock_name

    def getNumSinks(self) -> int:
        return len(self.sinks)

    def getClockPin(self) -> str:
        return self.clock_pin

    def getClockPinLocation(self) -> Tuple[int, int]:
        return (self.clock_pin_x, self.clock_pin_y)

    def getClockBuffers(self) -> List[ClockInst]:
        return list(self.clock_buffers)

    def getSinks(self) -> List[ClockInst]:
        return list(self.sinks)

    def getSubNets(self) -> List[ClockSubNet]:
        return list(self.sub_nets)

    def setSubNets(self, subnets: Iterable[ClockSubNet]) -> None:
        self.sub_nets = list(subnets)

    def forEachClockBuffer(self, func: Callable[[ClockInst], None]) -> None:
        for inst in self.clock_buffers:
            func(inst)

    def forEachSink(self, func: Callable[[ClockInst], None]) -> None:
        for sink in self.sinks:
            func(sink)

    def forEachSubNet(self, func: Callable[[ClockSubNet], None]) -> None:
        for subnet in self.sub_nets:
            func(subnet)
