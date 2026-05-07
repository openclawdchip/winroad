"""Pin access stage boundary."""

from __future__ import annotations

from typing import Any, Iterable, List, Optional

from .fr import frDesign
from .types import RouterConfiguration, _unsupported

class FlexPA:
    """对应 ``pa/FlexPA.h`` 的 pin access 阶段。"""

    def __init__(self, design: frDesign, logger: Any = None, dist: Any = None, router_cfg: Optional[RouterConfiguration] = None):
        self.design_ = design
        self.logger_ = logger
        self.dist_ = dist
        self.router_cfg_ = router_cfg or RouterConfiguration()
        self.graphics_: Optional[Any] = None
        self.target_insts_: List[Any] = []
        self.remote_host_: str = ""
        self.remote_port_: int = -1
        self.shared_vol_: str = ""
        self.cloud_sz_: int = -1

    def setDebug(self, pa_graphics: Any) -> None:
        self.graphics_ = pa_graphics

    def setTargetInstances(self, insts: Iterable[Any]) -> None:
        self.target_insts_ = list(insts)

    def setDistributed(self, remote_host: str, remote_port: int, shared_vol: str, cloud_sz: int) -> None:
        self.remote_host_ = remote_host
        self.remote_port_ = remote_port
        self.shared_vol_ = shared_vol
        self.cloud_sz_ = cloud_sz

    def addInst(self, inst: Any) -> None:
        if inst not in self.target_insts_:
            self.target_insts_.append(inst)

    def deleteInst(self, inst: Any) -> None:
        if inst in self.target_insts_:
            self.target_insts_.remove(inst)

    def main(self) -> int:
        _unsupported("FlexPA::main")

    def init(self) -> None:
        _unsupported("FlexPA::init")

    def genAllAccessPoints(self) -> None:
        _unsupported("FlexPA::genAllAccessPoints")

__all__ = ["FlexPA"]
