"""Global detailed routing stage boundary."""

from __future__ import annotations

from typing import Any, Dict, Optional

from .fr import frDesign, frRegionQuery, frTechObject
from .types import RouterConfiguration, _unsupported

class FlexGR:
    """对应 ``gr/FlexGR.h`` 的 global detailed routing 阶段。"""

    def __init__(
        self,
        design: frDesign,
        logger: Any = None,
        stt_builder: Any = None,
        router_cfg: Optional[RouterConfiguration] = None,
    ):
        self.db_: Optional[Any] = None
        self.design_ = design
        self.cmap_: Optional[Any] = None
        self.cmap2D_: Optional[Any] = None
        self.logger_ = logger
        self.stt_builder_ = stt_builder
        self.router_cfg_ = router_cfg or RouterConfiguration()

    def getTech(self) -> frTechObject:
        return self.design_.getTech()

    def getDesign(self) -> frDesign:
        return self.design_

    def getRegionQuery(self) -> frRegionQuery:
        return self.design_.getRegionQuery()

    def getCMap(self, is2DCMap: bool) -> Any:
        return self.cmap2D_ if is2DCMap else self.cmap_

    def setCMap(self, cmap: Any, is2DCMap: bool = False) -> None:
        """保存 congestion map 指针；不计算拥塞或写 guide。"""

        if is2DCMap:
            self.cmap2D_ = cmap
        else:
            self.cmap_ = cmap

    def snapshot(self) -> Dict[str, Any]:
        """返回 GR 阶段状态快照；真实 GR search/layer assign 仍未实现。"""

        block = self.design_.getTopBlock()
        return {
            "has_cmap": self.cmap_ is not None,
            "has_cmap2d": self.cmap2D_ is not None,
            "nets": len(block.getNets()) if block is not None else 0,
            "markers": len(block.getMarkers()) if block is not None else 0,
        }

    def main(self, db: Any = None) -> None:
        _unsupported("FlexGR::main")

    def init(self) -> None:
        _unsupported("FlexGR::init")

    def searchRepair(self, *args: Any, **kwargs: Any) -> None:
        _unsupported("FlexGR::searchRepair")

    def layerAssign(self) -> None:
        _unsupported("FlexGR::layerAssign")

    def writeToGuide(self) -> None:
        _unsupported("FlexGR::writeToGuide")

    def updateDb(self) -> None:
        _unsupported("FlexGR::updateDb")

__all__ = ["FlexGR"]
