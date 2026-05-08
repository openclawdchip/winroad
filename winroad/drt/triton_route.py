"""Top-level TritonRoute compatibility boundary."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

from .flex_dr import FlexDR, FlexDRViaData
from .flex_gr import FlexGR
from .flex_pa import FlexPA
from .fr import frDesign, frMarker
from .types import ParamStruct, Rect, RouterConfiguration, frDebugSettings, _unsupported

class TritonRoute:
    """对应 ``include/triton_route/TritonRoute.h`` 的 drt 顶层模块。"""

    def __init__(self):
        self.design_: Optional[frDesign] = None
        self.debug_ = frDebugSettings()
        self.router_cfg_ = RouterConfiguration()
        self.db_: Optional[Any] = None
        self.logger_: Optional[Any] = None
        self.dist_: Optional[Any] = None
        self.stt_builder_: Optional[Any] = None
        self.num_drvs_: int = -1
        self.distributed_: bool = False
        self.dist_ip_: str = ""
        self.dist_port_: int = 0
        self.shared_volume_: str = ""
        self.workers_results_: List[Tuple[int, str]] = []
        self.results_sz_: int = 0
        self.cloud_sz_: int = 0
        self.dr_: Optional[FlexDR] = None
        self.pa_: Optional[FlexPA] = None
        self.graphics_factory_: Optional[Any] = None

    def init(self, db: Any = None, logger: Any = None, dist: Any = None, stt_builder: Any = None, graphics_factory: Any = None) -> None:
        """初始化顶层指针并创建空 frDesign；不从 odb 导入数据。"""

        self.db_ = db
        self.logger_ = logger
        self.dist_ = dist
        self.stt_builder_ = stt_builder
        self.graphics_factory_ = graphics_factory
        self.design_ = frDesign(logger, self.router_cfg_)

    def getDesign(self) -> Optional[frDesign]:
        return self.design_

    def getLogger(self) -> Any:
        return self.logger_

    def getRouterConfiguration(self) -> RouterConfiguration:
        return self.router_cfg_

    def getRouterConfigurationState(self) -> dict[str, Any]:
        return self.router_cfg_.to_dict()

    def updateRouterConfiguration(self, **values: Any) -> None:
        """按字段名更新 RouterConfiguration；未知字段会显式报错。"""

        self.router_cfg_.update(**values)

    def resolveRouterLayerNames(self) -> None:
        """把已加载 tech 中的 routing layer 名称解析到配置层号；找不到则保留原值。

        该入口只同步 Python 配置状态，不解析 LEF/DEF，也不修改 tech。
        """

        if self.design_ is None:
            return
        name_to_field = {
            "BOTTOM_ROUTING_LAYER_NAME": "BOTTOM_ROUTING_LAYER",
            "TOP_ROUTING_LAYER_NAME": "TOP_ROUTING_LAYER",
            "VIAINPIN_BOTTOMLAYER_NAME": "VIAINPIN_BOTTOMLAYERNUM",
            "VIAINPIN_TOPLAYER_NAME": "VIAINPIN_TOPLAYERNUM",
            "VIA_ACCESS_LAYER_NAME": "VIA_ACCESS_LAYERNUM",
            "REPAIR_PDN_LAYER_NAME": "REPAIR_PDN_LAYER_NUM",
        }
        for name_field, num_field in name_to_field.items():
            layer_name = getattr(self.router_cfg_, name_field)
            if not layer_name:
                continue
            layer_num = self.design_.resolveLayerNum(layer_name)
            if layer_num:
                setattr(self.router_cfg_, num_field, layer_num)

    def getDb(self) -> Any:
        return self.db_

    def getDebugSettings(self) -> frDebugSettings:
        return self.debug_

    def getDebugSettingsState(self) -> dict[str, Any]:
        return self.debug_.to_dict()

    def setParams(self, params: ParamStruct) -> None:
        """按 C++ setParams 的职责写入 RouterConfiguration。"""

        self.router_cfg_.OUT_MAZE_FILE = params.outputMazeFile
        self.router_cfg_.DRC_RPT_FILE = params.outputDrcFile
        self.router_cfg_.DRC_RPT_ITER_STEP = params.drcReportIterStep
        self.router_cfg_.CMAP_FILE = params.outputCmapFile
        self.router_cfg_.GUIDE_REPORT_FILE = params.outputGuideCoverageFile
        self.router_cfg_.DBPROCESSNODE = params.dbProcessNode
        self.router_cfg_.ENABLE_VIA_GEN = params.enableViaGen
        if params.drouteEndIter >= 0:
            self.router_cfg_.END_ITERATION = params.drouteEndIter
        self.router_cfg_.VIAINPIN_BOTTOMLAYER_NAME = params.viaInPinBottomLayer
        self.router_cfg_.VIAINPIN_TOPLAYER_NAME = params.viaInPinTopLayer
        self.router_cfg_.VIA_ACCESS_LAYER_NAME = params.viaAccessLayer
        self.router_cfg_.OR_SEED = params.orSeed
        self.router_cfg_.OR_K = params.orK
        self.router_cfg_.BOTTOM_ROUTING_LAYER_NAME = params.bottomRoutingLayer
        self.router_cfg_.TOP_ROUTING_LAYER_NAME = params.topRoutingLayer
        self.router_cfg_.VERBOSE = params.verbose
        self.router_cfg_.CLEAN_PATCHES = params.cleanPatches
        self.router_cfg_.DO_PA = params.doPa
        self.router_cfg_.SINGLE_STEP_DR = params.singleStepDR
        self.router_cfg_.SAVE_GUIDE_UPDATES = params.saveGuideUpdates
        self.router_cfg_.REPAIR_PDN_LAYER_NAME = params.repairPDNLayerName
        self.router_cfg_.MAX_THREADS = max(1, params.num_threads)
        if params.minAccessPoints >= 0:
            self.router_cfg_.MINNUMACCESSPOINT_MACROCELLPIN = params.minAccessPoints
            self.router_cfg_.MINNUMACCESSPOINT_STDCELLPIN = params.minAccessPoints

    def addUserSelectedVia(self, via_name: str) -> None:
        if self.design_ is None:
            self.design_ = frDesign(self.logger_, self.router_cfg_)
        self.design_.addUserSelectedVia(via_name)

    def setUnidirectionalLayer(self, layer_name: str) -> None:
        if self.design_ is None:
            return
        for layer in self.design_.getTech().getLayers():
            if layer.getName() == layer_name:
                layer.unidirectional = True
                return

    def setDebugDR(self, on: bool = True) -> None:
        self.debug_.debugDR = on

    def setDebugDumpDR(self, on: bool, dumpDir: str) -> None:
        self.debug_.debugDumpDR = on
        self.debug_.dumpDir = dumpDir

    def setDebugSnapshotDir(self, snapshotDir: str) -> None:
        self.debug_.snapshotDir = snapshotDir

    def setDebugMaze(self, on: bool = True) -> None:
        self.debug_.debugMaze = on

    def setDebugPA(self, on: bool = True) -> None:
        self.debug_.debugPA = on

    def setDebugTA(self, on: bool = True) -> None:
        self.debug_.debugTA = on

    def setDebugWriteNetTracks(self, on: bool = True) -> None:
        self.debug_.writeNetTracks = on

    def setDebugNetName(self, name: str) -> None:
        self.debug_.netName = name

    def setDebugPinName(self, name: str) -> None:
        self.debug_.pinName = name

    def setDebugBox(self, x1: int, y1: int, x2: int, y2: int) -> None:
        self.debug_.box = (x1, y1, x2, y2)

    def setDebugIter(self, iter_num: int) -> None:
        self.debug_.iter = iter_num

    def setDebugPaMarkers(self, on: bool = True) -> None:
        self.debug_.paMarkers = on

    def setDebugPaEdge(self, on: bool = True) -> None:
        self.debug_.paEdge = on

    def setDebugPaCommit(self, on: bool = True) -> None:
        self.debug_.paCommit = on

    def setDumpLastWorker(self, on: bool = True) -> None:
        self.debug_.dumpLastWorker = on

    def setDebugWorkerParams(
        self,
        mazeEndIter: int,
        drcCost: int,
        markerCost: int,
        fixedShapeCost: int,
        markerDecay: float,
        ripupMode: int,
        followGuide: int,
    ) -> None:
        self.debug_.mazeEndIter = mazeEndIter
        self.debug_.drcCost = drcCost
        self.debug_.markerCost = markerCost
        self.debug_.fixedShapeCost = fixedShapeCost
        self.debug_.markerDecay = markerDecay
        self.debug_.ripupMode = ripupMode
        self.debug_.followGuide = followGuide

    def setDistributed(self, on: bool = True) -> None:
        self.distributed_ = on

    def setWorkerIpPort(self, ip: str, port: int) -> None:
        self.dist_ip_ = ip
        self.dist_port_ = port

    def setSharedVolume(self, volume: str) -> None:
        self.shared_volume_ = volume
        if self.shared_volume_ and not self.shared_volume_.endswith("/"):
            self.shared_volume_ += "/"

    def setCloudSize(self, cloud_sz: int) -> None:
        self.cloud_sz_ = cloud_sz

    def getCloudSize(self) -> int:
        return self.cloud_sz_

    def isDistributed(self) -> bool:
        return self.distributed_

    def getDistributedState(self) -> Dict[str, Any]:
        """返回分布式配置状态；不发送设计或 global updates。"""

        return {
            "enabled": self.distributed_,
            "ip": self.dist_ip_,
            "port": self.dist_port_,
            "shared_volume": self.shared_volume_,
            "cloud_size": self.cloud_sz_,
        }

    def getNumDRVs(self) -> int:
        if self.num_drvs_ < 0:
            raise RuntimeError("Detailed routing has not been run yet.")
        return self.num_drvs_

    def addWorkerResults(self, results: Sequence[Tuple[int, str]]) -> None:
        self.workers_results_.extend(results)
        self.results_sz_ = len(self.workers_results_)

    def getWorkerResults(self) -> List[Tuple[int, str]]:
        results = list(self.workers_results_)
        self.workers_results_.clear()
        self.results_sz_ = 0
        return results

    def getWorkerResultsSize(self) -> int:
        return self.results_sz_

    def clearDesign(self) -> None:
        self.design_ = None
        self.dr_ = None
        self.pa_ = None
        self.num_drvs_ = -1

    def ensureDR(self) -> FlexDR:
        """创建或返回 DR 阶段对象；不会调用 FlexDR::init/main。"""

        if self.design_ is None:
            self.design_ = frDesign(self.logger_, self.router_cfg_)
        if self.dr_ is None:
            self.dr_ = FlexDR(self, self.design_, self.logger_, self.db_, self.router_cfg_)
        return self.dr_

    def ensurePA(self) -> FlexPA:
        """创建或返回 PA 阶段对象；不会生成 access point。"""

        if self.design_ is None:
            self.design_ = frDesign(self.logger_, self.router_cfg_)
        if self.pa_ is None:
            self.pa_ = FlexPA(self.design_, self.logger_, self.dist_, self.router_cfg_)
        return self.pa_

    def makeGR(self) -> FlexGR:
        """创建轻量 GR 阶段对象；调用方若执行 main 仍会得到 NotImplementedError。"""

        if self.design_ is None:
            self.design_ = frDesign(self.logger_, self.router_cfg_)
        return FlexGR(self.design_, self.logger_, self.stt_builder_, self.router_cfg_)

    def collectMarkers(self) -> List[frMarker]:
        """收集当前 top block 中已有 marker；不运行 checkDRC。"""

        if self.design_ is None or self.design_.getTopBlock() is None:
            return []
        return list(self.design_.getTopBlock().getMarkers())

    def getMarkerSummary(self) -> Dict[str, Any]:
        """返回 marker 摘要，供 report/snapshot 使用。"""

        if self.design_ is None:
            return {"count": 0, "by_layer": {}}
        return self.design_.getMarkerSummary()

    def getMarkerRows(self) -> List[Dict[str, Any]]:
        """展开当前已有 marker，供 UI/测试读取；不调用 checkDRC。"""

        rows: List[Dict[str, Any]] = []
        for idx, marker in enumerate(self.collectMarkers(), start=1):
            bbox = marker.getBBox()
            rows.append(
                {
                    "idx": idx,
                    "layer": marker.getLayerNum(),
                    "bbox": bbox,
                    "constraint": getattr(marker.getConstraint(), "getName", lambda: getattr(marker.getConstraint(), "name", ""))(),
                    "sources": len(marker.getSrcs()),
                }
            )
        return rows

    def getRouteGuideSummary(self) -> List[Dict[str, Any]]:
        """返回 net guide 摘要；只统计已有 guide，不估算覆盖或修补 guide。"""

        if self.design_ is None:
            return []
        return self.design_.getGuideSummary()

    def validateConfiguration(self) -> List[str]:
        """检查 drt 配置状态中的明显错误；不补默认值、不读 ODB。"""

        errors: List[str] = []
        if self.router_cfg_.MAX_THREADS < 1:
            errors.append("MAX_THREADS must be >= 1")
        if self.router_cfg_.BOTTOM_ROUTING_LAYER > self.router_cfg_.TOP_ROUTING_LAYER:
            errors.append("BOTTOM_ROUTING_LAYER is above TOP_ROUTING_LAYER")
        if self.router_cfg_.END_ITERATION < 0:
            errors.append("END_ITERATION must be >= 0")
        if self.router_cfg_.BATCHSIZE < 1 or self.router_cfg_.BATCHSIZETA < 1:
            errors.append("BATCHSIZE and BATCHSIZETA must be >= 1")
        return errors

    def validateRouteGuides(self) -> List[str]:
        """检查 route guide 容器关系；不计算覆盖率，不生成 guide。"""

        if self.design_ is None or self.design_.getTopBlock() is None:
            return []
        errors: List[str] = []
        for net in self.design_.getTopBlock().getNets():
            errors.extend(net.validateGuides())
        return errors

    def validateMarkers(self) -> List[str]:
        """检查现有 marker 的 bbox/layer/owner；不运行 DRC。"""

        if self.design_ is None or self.design_.getTopBlock() is None:
            return []
        errors: List[str] = []
        for idx, marker in enumerate(self.design_.getTopBlock().getMarkers()):
            for error in marker.validate():
                errors.append(f"marker[{idx}]: {error}")
            if marker.getOwner() is not self.design_.getTopBlock():
                errors.append(f"marker[{idx}] owner mismatch")
        return errors

    def validateState(self) -> List[str]:
        """汇总 Python 接口层状态校验；所有真实 routing/DRC 仍由未实现入口承担。"""

        errors = self.validateConfiguration()
        if self.design_ is not None:
            errors.extend(self.design_.validate())
        return errors

    def snapshot(self) -> Dict[str, Any]:
        """返回 TritonRoute 顶层状态；真实 drt/ODB 处理仍由未实现入口承载。"""

        return {
            "has_design": self.design_ is not None,
            "num_drvs": self.num_drvs_,
            "distributed": self.getDistributedState(),
            "worker_results_size": self.results_sz_,
            "router_cfg": self.router_cfg_.to_dict(),
            "debug": self.debug_.to_dict(),
            "markers": self.getMarkerSummary(),
            "marker_rows": self.getMarkerRows(),
            "route_guides": self.getRouteGuideSummary(),
            "validation_errors": self.validateState(),
            "design": self.design_.snapshot() if self.design_ is not None else None,
            "dr": self.dr_.snapshot() if self.dr_ is not None else None,
            "pa": self.pa_.snapshot() if self.pa_ is not None else None,
        }

    def writeSnapshot(self, file_name: str) -> None:
        """把当前 Python 接口层状态写成 JSON；不写 DEF/ODB。"""

        Path(file_name).write_text(json.dumps(self.snapshot(), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    def initGuide(self) -> bool:
        _unsupported("TritonRoute::initGuide")

    def prep(self) -> None:
        _unsupported("TritonRoute::prep")

    def main(self) -> int:
        _unsupported("TritonRoute::main")

    def endFR(self) -> None:
        _unsupported("TritonRoute::endFR")

    def pinAccess(self, target_insts: Optional[Sequence[Any]] = None) -> None:
        _unsupported("TritonRoute::pinAccess")

    def stepDR(
        self,
        size: int,
        offset: int,
        mazeEndIter: int,
        workerDRCCost: int,
        workerMarkerCost: int,
        workerFixedShapeCost: int,
        workerMarkerDecay: float,
        ripupMode: int,
        followGuide: bool,
    ) -> None:
        _unsupported("TritonRoute::stepDR")

    def gr(self) -> None:
        _unsupported("TritonRoute::gr")

    def ta(self) -> None:
        _unsupported("TritonRoute::ta")

    def dr(self) -> None:
        _unsupported("TritonRoute::dr")

    def checkDRC(self, filename: str, x1: int, y1: int, x2: int, y2: int, marker_name: str, num_threads: int) -> None:
        _unsupported("TritonRoute::checkDRC")

    def reportDRC(
        self,
        file_name: str,
        markers: Sequence[frMarker],
        marker_name: str,
        drcBox: Rect = (0, 0, 0, 0),
    ) -> None:
        lines = [
            f"# DRC report: {marker_name}",
            f"# box: {drcBox[0]} {drcBox[1]} {drcBox[2]} {drcBox[3]}",
            f"# markers: {len(markers)}",
        ]
        for idx, marker in enumerate(markers, start=1):
            bbox = marker.getBBox()
            constraint = marker.getConstraint()
            constraint_name = getattr(constraint, "name", None) or getattr(constraint, "getName", lambda: "")()
            lines.append(
                " ".join(
                    [
                        str(idx),
                        marker_name,
                        f"layer={marker.getLayerNum()}",
                        f"bbox={bbox[0]},{bbox[1]},{bbox[2]},{bbox[3]}",
                        f"constraint={constraint_name}",
                        f"sources={len(marker.getSrcs())}",
                    ]
                )
            )
        report = "\n".join(lines) + "\n"
        target = file_name or self.router_cfg_.DRC_RPT_FILE
        if target:
            Path(target).write_text(report, encoding="utf-8")
        elif self.logger_ is not None and hasattr(self.logger_, "info"):
            self.logger_.info(report.rstrip())

    def reportMarkers(self, file_name: str = "") -> None:
        """报告当前已有 marker；不调用 GC，也不创建新的 violation。"""

        self.reportDRC(file_name, self.collectMarkers(), "DRT_MARKER")

    def writeRouteGuideReport(self, file_name: str = "") -> None:
        """写出已有 route guide 摘要；不读取 guide 文件，也不修补 guide。"""

        rows = ["net,guides,orig_guides,route_objs,modified,guide_layers"]
        for row in self.getRouteGuideSummary():
            guide_layers = ";".join(f"{layer}:{count}" for layer, count in sorted(row["guide_layers"].items()))
            rows.append(
                ",".join(
                    [
                        str(row["net"]),
                        str(row["guides"]),
                        str(row["orig_guides"]),
                        str(row["route_objs"]),
                        str(int(row["modified"])),
                        guide_layers,
                    ]
                )
            )
        report = "\n".join(rows) + "\n"
        target = file_name or self.router_cfg_.GUIDE_REPORT_FILE
        if target:
            Path(target).write_text(report, encoding="utf-8")
        elif self.logger_ is not None and hasattr(self.logger_, "info"):
            self.logger_.info(report.rstrip())

    def reportConstraints(self) -> None:
        if self.design_ is None:
            return
        lines: List[str] = ["# drt constraints"]
        for layer in self.design_.getTech().getLayers():
            lines.append(f"{layer.getName()} {layer.getLayerNum()} constraints={len(layer.getConstraints())}")
        report = "\n".join(lines)
        if self.logger_ is not None and hasattr(self.logger_, "info"):
            self.logger_.info(report)

    def routeLayerLengths(self, wire: Any) -> List[int]:
        _unsupported("TritonRoute::routeLayerLengths")

    def runDRWorker(self, workerStr: str, viaData: Optional[FlexDRViaData] = None) -> str:
        _unsupported("TritonRoute::runDRWorker")

    def debugSingleWorker(self, dumpDir: str, drcRpt: str) -> None:
        _unsupported("TritonRoute::debugSingleWorker")

    def updateGlobals(self, file_name: str) -> None:
        _unsupported("TritonRoute::updateGlobals")

    def resetDb(self, file_name: str) -> None:
        _unsupported("TritonRoute::resetDb")

    def updateDesign(self, updates_or_path: Any, num_threads: int) -> None:
        _unsupported("TritonRoute::updateDesign")

    def sendDesignDist(self) -> None:
        _unsupported("TritonRoute::sendDesignDist")

    def writeGlobals(self, name: str) -> bool:
        _unsupported("TritonRoute::writeGlobals")

    def sendDesignUpdates(self, router_cfg_path: str, num_threads: int) -> None:
        _unsupported("TritonRoute::sendDesignUpdates")

    def sendGlobalsUpdates(self, router_cfg_path: str, serializedViaData: str) -> None:
        _unsupported("TritonRoute::sendGlobalsUpdates")

    def fixMaxSpacing(self, num_threads: int) -> None:
        _unsupported("TritonRoute::fixMaxSpacing")

    def deleteInstancePAData(self, inst: Any) -> None:
        _unsupported("TritonRoute::deleteInstancePAData")

    def addInstancePAData(self, inst: Any) -> None:
        _unsupported("TritonRoute::addInstancePAData")


def create_triton_route() -> TritonRoute:
    """创建 drt 顶层入口对象，类似 C++ MakeTritonRoute 工厂。"""

    return TritonRoute()

__all__ = ["TritonRoute", "create_triton_route"]
