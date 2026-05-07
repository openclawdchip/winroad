"""Pin access stage boundary."""

from __future__ import annotations

from typing import Any, Dict, Iterable, List, Optional

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

    def getGraphics(self) -> Any:
        return self.graphics_

    def setTargetInstances(self, insts: Iterable[Any]) -> None:
        self.target_insts_ = list(insts)

    def getTargetInstances(self) -> List[Any]:
        return self.target_insts_

    def setDistributed(self, remote_host: str, remote_port: int, shared_vol: str, cloud_sz: int) -> None:
        self.remote_host_ = remote_host
        self.remote_port_ = remote_port
        self.shared_vol_ = shared_vol
        self.cloud_sz_ = cloud_sz

    def getDistributedState(self) -> Dict[str, Any]:
        """返回 PA 分布式状态；不创建 worker，不写 access point。"""

        return {
            "remote_host": self.remote_host_,
            "remote_port": self.remote_port_,
            "shared_vol": self.shared_vol_,
            "cloud_sz": self.cloud_sz_,
        }

    def addInst(self, inst: Any) -> None:
        if inst not in self.target_insts_:
            self.target_insts_.append(inst)

    def deleteInst(self, inst: Any) -> None:
        if inst in self.target_insts_:
            self.target_insts_.remove(inst)

    def snapshot(self) -> Dict[str, Any]:
        """返回 PA 阶段状态快照；真实 access point 生成仍保留未实现入口。"""

        return {
            "target_insts": [getattr(inst, "getName", lambda: getattr(inst, "name", str(inst)))() for inst in self.target_insts_],
            "distributed": self.getDistributedState(),
            "has_graphics": self.graphics_ is not None,
        }

    def main(self) -> int:
        _unsupported("FlexPA::main")

    def init(self) -> None:
        _unsupported("FlexPA::init")

    def genAllAccessPoints(self) -> None:
        _unsupported("FlexPA::genAllAccessPoints")

__all__ = ["FlexPA"]
