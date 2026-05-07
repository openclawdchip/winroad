"""Special route command 边界。"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List

from .types import _not_implemented

@dataclass
class SRoute:
    """对应 `pdn::SRoute`，仅保留 add_sroute_connect 的内部边界。"""

    pdngen: "PdnGen"
    connects: List[Dict[str, Any]] = field(default_factory=list)

    def addSrouteConnect(self, **params: Any) -> Dict[str, Any]:
        if not params:
            raise ValueError("addSrouteConnect requires at least one parameter")
        self.connects.append(dict(params))
        return self.connects[-1]

    def getSrouteConnects(self) -> List[Dict[str, Any]]:
        return [dict(connect) for connect in self.connects]

    def summary(self) -> Dict[str, Any]:
        net_count = 0
        layer_count = 0
        for connect in self.connects:
            net_count += int(any(key in connect for key in ("net", "nets", "power", "ground")))
            layer_count += int(any(key in connect for key in ("layer", "layers", "metal", "metal_layers")))
        return {
            "connect_count": len(self.connects),
            "connects_with_nets": net_count,
            "connects_with_layers": layer_count,
            "parameter_keys": sorted({key for connect in self.connects for key in connect.keys()}),
        }

    def createSrouteWires(self, *args: Any, **kwargs: Any) -> None:
        _not_implemented("SRoute::createSrouteWires")

    def report(self) -> Dict[str, Any]:
        return {**self.summary(), "connects": self.getSrouteConnects()}
