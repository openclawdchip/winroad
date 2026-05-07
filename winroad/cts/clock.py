"""Clock network data model for CTS."""

from __future__ import annotations

import json
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

    def toDict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "master": self.master,
            "type": self.type.value,
            "x": self.x,
            "y": self.y,
            "input_cap": self.input_cap,
            "insertion_delay": self.insertion_delay,
            "output_cap": self.output_cap,
            "ideal_output_cap": self.ideal_output_cap,
        }

    @classmethod
    def fromDict(cls, data: Dict[str, Any]) -> "ClockInst":
        return cls(
            name=str(data.get("name", "")),
            master=str(data.get("master", "")),
            type=InstType(data.get("type", InstType.CLOCK_SINK.value)),
            x=int(data.get("x", 0)),
            y=int(data.get("y", 0)),
            input_cap=float(data.get("input_cap", 0.0)),
            insertion_delay=float(data.get("insertion_delay", 0.0)),
            output_cap=float(data.get("output_cap", 0.0)),
            ideal_output_cap=float(data.get("ideal_output_cap", 0.0)),
        )


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

    def report(self) -> Dict[str, Any]:
        driver = self.instances[0].getName() if self.instances else None
        return {
            "name": self.name,
            "driver": driver,
            "leaf_level": self.leaf_level,
            "num_sinks": self.getNumSinks(),
            "sinks": [inst.getName() for inst in self.getSinks()],
            "instances": [inst.getName() for inst in self.instances],
        }

    def toDict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "leaf_level": self.leaf_level,
            "instances": [inst.getName() for inst in self.instances],
        }


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

    def report(self) -> Dict[str, Any]:
        return {
            "name": self.getName(),
            "sdc_name": self.getSdcName(),
            "clock_pin": self.clock_pin,
            "clock_pin_location": self.getClockPinLocation(),
            "num_sinks": len(self.sinks),
            "num_buffers": len(self.clock_buffers),
            "num_subnets": len(self.sub_nets),
            "buffers": [inst.toDict() for inst in self.clock_buffers],
            "sinks": [inst.toDict() for inst in self.sinks],
            "subnets": [subnet.report() for subnet in self.sub_nets],
        }

    def toDict(self) -> Dict[str, Any]:
        return {
            "net_name": self.net_name,
            "clock_pin": self.clock_pin,
            "sdc_clock_name": self.sdc_clock_name,
            "clock_pin_x": self.clock_pin_x,
            "clock_pin_y": self.clock_pin_y,
            "clock_buffers": [inst.toDict() for inst in self.clock_buffers],
            "sinks": [inst.toDict() for inst in self.sinks],
            "sub_nets": [subnet.toDict() for subnet in self.sub_nets],
        }

    @classmethod
    def fromDict(cls, data: Dict[str, Any]) -> "Clock":
        clock = cls(
            net_name=str(data.get("net_name", "")),
            clock_pin=str(data.get("clock_pin", "")),
            sdc_clock_name=str(data.get("sdc_clock_name", "")),
            clock_pin_x=int(data.get("clock_pin_x", 0)),
            clock_pin_y=int(data.get("clock_pin_y", 0)),
        )
        for inst_data in data.get("clock_buffers", []):
            inst = ClockInst.fromDict(inst_data)
            clock.clock_buffers.append(inst)
            clock.name_to_inst[inst.getName()] = inst
        for inst_data in data.get("sinks", []):
            inst = ClockInst.fromDict(inst_data)
            clock.sinks.append(inst)
            clock.name_to_inst[inst.getName()] = inst
        for subnet_data in data.get("sub_nets", []):
            subnet = ClockSubNet(str(subnet_data.get("name", "")))
            subnet.setLeafLevel(bool(subnet_data.get("leaf_level", False)))
            for inst_name in subnet_data.get("instances", []):
                inst = clock.findClockByName(str(inst_name))
                if inst is not None:
                    subnet.addInst(inst)
            clock.addSubNetObj(subnet)
        return clock

    def serialize(self, path: Optional[str] = None) -> Dict[str, Any]:
        data = self.toDict()
        if path is not None:
            with open(path, "w", encoding="utf-8") as stream:
                json.dump(data, stream, indent=2, sort_keys=True)
        return data

    @classmethod
    def deserialize(cls, data_or_path: Any) -> "Clock":
        if isinstance(data_or_path, str):
            with open(data_or_path, "r", encoding="utf-8") as stream:
                data_or_path = json.load(stream)
        return cls.fromDict(data_or_path)
