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
        self.connects.append(dict(params))
        return self.connects[-1]

    def getSrouteConnects(self) -> List[Dict[str, Any]]:
        return [dict(connect) for connect in self.connects]

    def createSrouteWires(self, *args: Any, **kwargs: Any) -> None:
        _not_implemented("SRoute::createSrouteWires")


