"""Special route command 边界。"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List

from .types import PdnIssue, _name, _not_implemented

@dataclass
class SRoute:
    """对应 `pdn::SRoute`，仅保留 add_sroute_connect 的内部边界。"""

    pdngen: "PdnGen"
    connects: List[Dict[str, Any]] = field(default_factory=list)

    def addSrouteConnect(self, **params: Any) -> Dict[str, Any]:
        if not params:
            raise ValueError("addSrouteConnect requires at least one parameter")
        normalized = dict(params)
        if any(not str(key) for key in normalized):
            raise ValueError("addSrouteConnect parameter names must be non-empty")
        self.connects.append(normalized)
        return self.connects[-1]

    def getSrouteConnects(self) -> List[Dict[str, Any]]:
        return [dict(connect) for connect in self.connects]

    def clear(self) -> None:
        """清理 Tcl 参数缓存；不触发真实 special route ripup。"""

        self.connects.clear()

    def collectSetupIssues(self, path: str = "sroute") -> List[PdnIssue]:
        issues: List[PdnIssue] = []
        for index, connect in enumerate(self.connects):
            location = f"{path}/connect[{index}]"
            if not connect:
                issues.append(PdnIssue(location, "sroute connect has no parameters"))
                continue
            if not any(key in connect for key in ("net", "nets", "power", "ground")):
                issues.append(PdnIssue(location, "sroute connect has no net parameter", severity="warning"))
            if not any(key in connect for key in ("layer", "layers", "metal", "metal_layers")):
                issues.append(PdnIssue(location, "sroute connect has no layer parameter", severity="warning"))
            none_keys = [str(key) for key, value in connect.items() if value is None]
            if none_keys:
                issues.append(PdnIssue(location, f"sroute connect has None parameter values: {', '.join(none_keys)}", severity="warning"))
        return issues

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
        connects = []
        for connect in self.connects:
            connects.append({str(key): _name(value) if key in {"net", "power", "ground", "layer", "metal"} else value for key, value in connect.items()})
        return {**self.summary(), "connects": connects, "setup_issues": [issue.report() for issue in self.collectSetupIssues()]}
