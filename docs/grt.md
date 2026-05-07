# grt

## 已实现

- 已建立 OpenROAD `src/grt` 顶层 Python 复刻骨架。
- 已补全全局布线基础类型：
  - `RoutePt`
  - `GSegment`
  - `GRoute`
  - `NetRouteMap`
  - `NetType`
  - `PinEdge`
- 已补全拥塞/容量相关数据结构：
  - `TileCongestion`
  - `TileInformation`
  - `CongestionInformation`
  - `CapacityReduction`
  - `RegionAdjustment`
  - `RoutePointPins`
- 已补全 pin/net/grid 边界对象：
  - `PinGridLocation`
  - `Pin`
  - `Net`
  - `Grid`
  - `RoutingTracks`
- 已补全 FastRoute 入口对象与配置边界：
  - `DebugSetting`
  - `CostParams`
  - `Parent3D`
  - `FastRouteCore`
- 已补全 grt 顶层入口与增量回调边界：
  - `GlobalRouter`
  - `GRouteDbCbk`
  - `IncrementalGRoute`
- 第三轮已继续深化 OpenROAD `src/grt` 边界，不触碰 `odb`：
  - guide/segment 轻量写回与读取：`GSegment.toDict()`、`GSegment.fromDict()`、`GSegment.toGuideLine()`、`GSegment.fromGuideTokens()`、`GlobalRouter.readGuides()`、`loadGuidesFromDB()`、`saveGuidesFromDB()`、`saveGuides()`、`writeSegments()`、`readSegments()`
  - region/layer adjustment 状态：`GlobalRouter.addLayerAdjustment()`、`addRegionAdjustment()`、`getLayerAdjustments()`、`getRegionAdjustments()`，并同步记录到 `FastRouteCore.addAdjustment()`
  - net alpha/beta/gamma 参数：`Net.setAlpha()`、`getAlpha()`、`setBeta()`、`getBeta()`、`setGamma()`、`getGamma()`、`setCostParameters()`、`getCostParameters()`、`GlobalRouter.setNetAlphaBetaGamma()`、`getNetAlphaBetaGamma()`、`FastRouteCore.addNet(..., alpha, beta, gamma)`
  - tile congestion 与 resource snapshot：`FastRouteCore.buildTileCongestion()`、`getTileCongestion()`、`reportCongestionSummary()`、`createResourceSnapshot()`、`getResourceSnapshot()`、`GlobalRouter.getCongestionReport()`、`getResourceSnapshot()`
  - report 函数边界：`GlobalRouter.reportNetLayerWirelengths()`、`reportLayerWireLengths()`、`getLastLayerWirelengthReport()`、`reportNetWireLength()`、`createWLReportFile()`
- 已提供基础便利函数：
  - `create_global_router()`
  - `print_groute()`
  - `getITermName()`
  - `getLayerName()`
- 已实现轻量状态与几何辅助接口：
  - `GSegment.isVia()`、`isJumper()`、`is3DRoute()`、`setIs3DRoute()`、`length()`、`endpoints()`
  - `Pin` 的 iterm/bterm 构造、名称、层、box、driver、on-grid 位置接口
  - `Net` 的 pin 管理、slack、segment parent、dirty/clock/merged 状态接口
  - `Grid` 的初始化、坐标/grid 互转、tile/blockage 边界辅助接口
  - `RoutingTracks` 的 layer/pitch/track 查询接口
  - `FastRouteCore` 的 grid/layer/capacity/net 注册、route 清理、debug、线程、拥塞参数、capacity/report 边界接口
  - `GlobalRouter` 的配置入口、guide/report 边界、route 查询、连通性检查、资源更新转发、增量 dirty net 标记、debug 转发、grid/layer 查询接口

## 未实现

- FastRoute 主算法：
  - Steiner tree / rectilinear Steiner tree 构建
  - 2D/3D maze routing
  - layer assignment
  - overflow/congestion rip-up and reroute
  - capacity lower bound 与 edge graph 完整初始化
- OpenDB 真实 guide/wire 读写：
  - `updateVias()`
  - 当前 `readGuides()`、`loadGuidesFromDB()`、`saveGuides()`、`writeSegments()`、`readSegments()` 只实现 WinRoad Python 轻量文件或普通对象属性边界，不创建/修改 OpenDB guide/wire。
- pin access 与 pin coverage 的完整 OpenDB/DRT 联动：
  - `ensurePinsPositions()`
  - `findCoveredAccessPoint()`
  - `updateUncoveredPinsPositions()`
  - `findPinAccessPointPositions()`
- antenna repair、jumper/diode 插入与 STA/RC 估算：
  - `repairAntennas()`
  - `estimatePathResistance()`
  - `getLayerResistance()`
  - `getViaResistance()`
- CUGR 接入、RUDY/heatmap、拥塞图文件格式和 detailed-route 报告输出仍待按 OpenROAD C++ 逐函数移植。
- 第二轮已继续补齐的边界包括：
  - `FastRouteCore` 的 `getDbNetLayerEdgeCost()`、`initEdgesCapacityPerLayer()`、`setNumAdjustments()`、`addAdjustment()`、`saveResourcesBeforeAdjustments()`、`initAuxVar()`、`getCongestionGrid()`、`getCongestionNets()`、`getOriginalResources()`、`getTotalCapacityPerLayer()`、`getTotalUsagePerLayer()`、`getTotalOverflowPerLayer()`、`getMaxHorizontalOverflows()`、`getMaxVerticalOverflows()`、`clearNDRnets()` 等状态与报告入口
  - `GlobalRouter` 的 guide/report/resistance 入口名和增量辅助方法边界

## 第三轮验证命令

```powershell
python -m py_compile D:\winroad_py\winroad\grt.py
@'
from io import StringIO
from pathlib import Path
from winroad.grt import GSegment, GlobalRouter, Net

r = GlobalRouter()
net = "n1"
r.routes[net] = [GSegment(0, 0, 1, 2, 0, 1)]
r.db_net_map[net] = Net(net)
r.setNetAlphaBetaGamma(net, 0.2, 0.3, 0.4)
assert r.getNetAlphaBetaGamma(net) == (0.2, 0.3, 0.4)

r.addLayerAdjustment(2, 0.5)
r.addRegionAdjustment(0, 0, 10, 10, 3, 0.7)
assert r.getLayerAdjustments()[2] == 0.5
assert len(r.getRegionAdjustments()) == 2

tmp = Path("D:/winroad_py/.grt_segments.json")
r.writeSegments(str(tmp))
r2 = GlobalRouter()
r2.readSegments(str(tmp))
assert len(r2.routes[net]) == 1
tmp.unlink()

buf = StringIO()
r.reportNetLayerWirelengths(net, buf)
assert "layer 1: 2" in buf.getvalue()
r.createWLReportFile("D:/winroad_py/.grt_wl.rpt", verbose=True)
Path("D:/winroad_py/.grt_wl.rpt").unlink()

r.fastroute().setGridsAndLayers(2, 2, 2)
r.fastroute().setEdgeCapacity(0, 0, 1, 0, 1, 1)
r.updateResources(0, 0, 1, 0, 1, 2, net)
assert r.getCongestionReport()["congested_tile_count"] == 1
r.fastroute().saveResourcesBeforeAdjustments()
assert r.getResourceSnapshot()["total_usage_per_layer"][1] == 2
'@ | python -
```

## 说明

- 当前实现保留 OpenROAD grt 的核心对象、入口类和关键函数边界。
- 尚未翻译的 C++ 主算法会显式抛出 `NotImplementedError`，避免生成估算 demo 或伪造布线结果。
- 字段和接口名尽量贴近 C++，同时保留详细中文注释，便于后续逐文件继续翻译。
