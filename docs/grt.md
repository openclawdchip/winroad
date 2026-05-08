# grt

## Package 拆分

- `winroad/grt.py` 已拆为 `winroad/grt/` package，旧文件仅保留兼容转发。
- 拆分边界：
  - `types.py`：公共类型别名、枚举、`RoutePt` 和内部辅助函数。
  - `guide.py`：`GSegment`、`Guide`、`GuideFile`、guide 行/JSON/括号文本转换、`print_groute()`。
  - `congestion.py`：拥塞、容量调整和 region adjustment 数据结构。
  - `grid.py`：`Pin`、`Net`、`Grid`、`RoutingTracks` 等 pin/net/grid 边界对象。
  - `fast_route.py`：`DebugSetting`、`CostParams`、`Parent3D`、`FastRouteCore`。
  - `global_router.py`：`GlobalRouter`、`GRouteDbCbk`、`IncrementalGRoute` 和模块级便利入口。
  - `__init__.py`：重新导出原 `winroad.grt` 公共 API，保持 `from winroad.grt import ...` 兼容。

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
  - 第四轮新增 guide 文档对象和更完整 round-trip：`Guide`、`GuideFile`、`routes_to_guide_file()`、`GlobalRouter.writeGuides(format="json"|"guide")`；支持 WinRoad JSON、逐行 segment 文本、`net / ( ... )` guide 文本，层字段支持数字和末尾带数字的轻量层名。
  - region/layer adjustment 状态：`GlobalRouter.addLayerAdjustment()`、`addRegionAdjustment()`、`getLayerAdjustments()`、`getRegionAdjustments()`，并同步记录到 `FastRouteCore.addAdjustment()`
  - 第四轮新增 adjustment 管理：`GlobalRouter.clearAdjustments()`、`removeLayerAdjustment()`、`removeRegionAdjustment()`、`FastRouteCore.getAdjustments()`、`clearAdjustments()`，删除/清空会同步 GlobalRouter 与 FastRouteCore 状态。
  - net alpha/beta/gamma 参数：`Net.setAlpha()`、`getAlpha()`、`setBeta()`、`getBeta()`、`setGamma()`、`getGamma()`、`setCostParameters()`、`getCostParameters()`、`GlobalRouter.setNetAlphaBetaGamma()`、`getNetAlphaBetaGamma()`、`FastRouteCore.addNet(..., alpha, beta, gamma)`
  - tile congestion 与 resource snapshot：`FastRouteCore.buildTileCongestion()`、`getTileCongestion()`、`reportCongestionSummary()`、`createResourceSnapshot()`、`getResourceSnapshot()`、`GlobalRouter.getCongestionReport()`、`getResourceSnapshot()`
  - 第四轮新增可落盘报告：`FastRouteCore.createCongestionReport()`、`writeCongestionMap()`、`writeResourceReport()`、`saveCongestion()`、`GlobalRouter.createCongestionReport()`、`writeCongestionReport()`、`createResourceSnapshot()`、`writeResourceReport()`；报告使用 JSON 安全的 edge/tile records，不依赖 OpenDB。
  - 第四轮新增 route/core 状态管理：`GlobalRouter.setRoute()`、`getRoute()`、`clearRoute()`、`clearRoutes()`、`updateFastRouteGridsLayer()`、`toStateDict()`、`loadStateDict()`、`saveState()`、`loadState()`；`FastRouteCore` edge capacity/usage key 规范化为无向 grid edge，正反方向查询一致。
  - report 函数边界：`GlobalRouter.reportNetLayerWirelengths()`、`reportLayerWireLengths()`、`getLastLayerWirelengthReport()`、`reportNetWireLength()`、`createWLReportFile()`
- 第六轮继续补齐可落地状态逻辑：
  - guide 批量读写：`GlobalRouter.readGuideFiles()`、`writeGuideFiles()`、`splitGuidesByNet()`，仍只处理 WinRoad 轻量 JSON/guide 文本，不触碰 OpenDB wire。
  - adjustment 查询删除：`findRegionAdjustments()`、`getRegionAdjustment()`、`removeAdjustments()`，可按 layer、region、layer-only 条件过滤，并同步 `FastRouteCore` adjustment 状态。
  - resource/congestion JSON schema：`FastRouteCore.getResourceSnapshotSchema()`、`getCongestionReportSchema()`，报告新增 `format`、`version`、`schema`，congestion tile record 新增 `overflow`。
  - `GlobalRouter` 状态差异与合并：`diffStateDict()`、`diffState()`、`mergeStateDict()`、`mergeState()`，支持 route replace/append/keep、adjustment replace/append/keep 以及 config/resources 合并开关。
  - Net route metrics：`getNetRouteMetrics()`、`getRouteMetrics()`，统计 segment、wirelength、layer wirelength、via、jumper、bbox、连通性和 pin 数。
- 第七轮继续补齐 OpenROAD FastRoute/GlobalRouter 边界的状态查询、校验和批处理 report：
  - `FastRouteCore.setEdgeUsage()`、`getEdgeUsage()`、`getEdgeResourceRecord()`、`iterEdgeResourceRecords()`、`applyEdgeResourceRecords()`，统一使用规范化无向 grid edge，便于 resource JSON round-trip。
  - `FastRouteCore.getTileCongestionRecord()`、`getResourceSummary()`、`validateResources()`，可查询单 tile 拥塞、资源摘要，并检查负数资源、非相邻 edge、usage-only edge。
  - `GlobalRouter.getSegmentStatus()`、`validateSegment()`，提供单 segment 的方向、端点、bbox、layer span、unit resource edges 和结构化校验问题。
  - `GlobalRouter.validateRoute()`、`validateRoutes()`、`getNetRouteStatus()`、`getRoutesStatus()`，补齐 net/route 级状态查询，覆盖 segment 几何、连通性、pin 覆盖和资源校验。
  - `GlobalRouter.createRouteReport()`、`writeRouteReport()`、`writeBatchReports()`、`getEdgeResourceRecord()`、`getEdgeResourceRecords()`、`applyEdgeResourceRecords()`，提供 route/resource/congestion/state/validation 批量 report 写出接口。
- 第八轮继续补齐导入导出、校验和批处理边界：
  - guide 显式导入导出别名：`GlobalRouter.importGuides()`、`exportGuides()`、`importGuideFiles()`、`exportGuideFiles()`，仍只处理 WinRoad JSON/guide 文本，不写 OpenDB wire。
  - guide 文件预检与报告：`inspectGuideFile()`、`validateGuideFile()`、`createGuideReport()`、`writeGuideReport()`，可在不污染当前 routes 的情况下检查磁盘 guide 文件。
  - resource snapshot round-trip：`FastRouteCore.applyResourceSnapshot()`、`readResourceReport()`、`importResourceSnapshot()`、`exportResourceSnapshot()`，以及 `GlobalRouter.applyResourceSnapshot()`、`importResourceSnapshot()`、`exportResourceSnapshot()` 转发。
  - congestion tile 批量查询：`FastRouteCore.iterTileCongestionRecords()`、`GlobalRouter.getTileCongestionRecords()`，支持按 layer 和 overflow-only 过滤。
  - `GlobalRouter.writeBatchReports()` 新增 `guide`、`resource_validation`、`congestion_tiles` report 类型；原 `route`、`resource`、`congestion`、`state`、`validation` 保持兼容。
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
  - 当前 `readGuides()`、`writeGuides()`、`loadGuidesFromDB()`、`saveGuides()`、`writeSegments()`、`readSegments()` 只实现 WinRoad Python 轻量文件或普通对象属性边界，不创建/修改 OpenDB guide/wire。
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

## 第六轮验证命令

```powershell
python -m py_compile D:\winroad_py\winroad\grt\types.py D:\winroad_py\winroad\grt\guide.py D:\winroad_py\winroad\grt\congestion.py D:\winroad_py\winroad\grt\grid.py D:\winroad_py\winroad\grt\fast_route.py D:\winroad_py\winroad\grt\global_router.py D:\winroad_py\winroad\grt\__init__.py
@'
from pathlib import Path
from winroad.grt import GSegment, GlobalRouter, Net

base = Path("D:/winroad_py")
r = GlobalRouter()
r.grid.init((0, 0, 100, 100), 10, 10, 10, True, True, 3)
r.fastroute().setGridsAndLayers(2, 2, 3)
r.fastroute().setEdgeCapacity(0, 0, 1, 0, 1, 1)

n1 = "n1"
n2 = "n2"
r.db_net_map[n1] = Net(n1)
r.setRoute(n1, [GSegment(0, 0, 1, 2, 0, 1), GSegment(2, 0, 1, 2, 0, 3)])
r.setRoute(n2, [GSegment(0, 1, 2, 1, 1, 2, is_jumper=True)])
r.updateResources(1, 0, 0, 0, 1, 2, n1)

r.addLayerAdjustment(2, 0.5)
r.addRegionAdjustment(0, 0, 10, 10, 3, 0.7)
assert r.getRegionAdjustment(0, 0, 10, 10, 3) == 0.7
assert len(r.findRegionAdjustments(layer=2)) == 1
assert r.removeAdjustments(layer=2, layer_only=True) == 1

assert r.getNetRouteMetrics(n1)["via_count"] == 2
assert r.getRouteMetrics()["net_count"] == 2
assert r.createCongestionReport()["format"] == "winroad-grt-congestion"
assert r.createResourceSnapshot()["format"] == "winroad-grt-resource"

json1 = base / ".grt_batch_n1.json"
json2 = base / ".grt_batch_n2.json"
split_dir = base / ".grt_split_guides"
r.writeGuideFiles({str(json1): [n1], str(json2): [n2]})
r2 = GlobalRouter()
r2.readGuideFiles([str(json1), str(json2)])
assert len(r2.getRoute(n1)) == 2
assert len(r2.getRoute(n2)) == 1
assert "n1" in r.splitGuidesByNet(str(split_dir))

state1 = r.toStateDict()
r.setRoute(n1, [GSegment(0, 0, 1, 1, 0, 1)])
assert "n1" in r.diffStateDict(state1)["routes_changed"]
r.mergeStateDict(state1, routes="replace", adjustments="replace")
assert len(r.getRoute(n1)) == 2

for call in (r.fastroute().run, r.globalRoute):
    try:
        call()
    except NotImplementedError:
        pass
    else:
        raise AssertionError("routing algorithms must stay unsupported")

for path in (json1, json2):
    path.unlink(missing_ok=True)
for path in split_dir.glob("*"):
    path.unlink()
split_dir.rmdir()
print("smoke ok")
'@ | python -
```

## 第七轮验证命令

```powershell
python -m py_compile D:\winroad_py\winroad\grt\types.py D:\winroad_py\winroad\grt\guide.py D:\winroad_py\winroad\grt\congestion.py D:\winroad_py\winroad\grt\grid.py D:\winroad_py\winroad\grt\fast_route.py D:\winroad_py\winroad\grt\global_router.py D:\winroad_py\winroad\grt\__init__.py
@'
from pathlib import Path
from winroad.grt import GSegment, GlobalRouter, Net, Pin

base = Path("D:/winroad_py")
r = GlobalRouter()
r.grid.init((0, 0, 100, 100), 10, 10, 10, True, True, 4)
r.fastroute().setGridsAndLayers(4, 4, 4)
r.fastroute().setEdgeCapacity(0, 0, 1, 0, 1, 2)
r.fastroute().setEdgeUsage(0, 0, 1, 0, 1, 1)

net = "n1"
wr_net = Net(net)
wr_net.addPin(Pin(position=(0, 0), on_grid_position=(0, 0), layers=[1], connection_layer=1))
r.db_net_map[net] = wr_net
r.setRoute(net, [GSegment(0, 0, 1, 2, 0, 1), GSegment(2, 0, 1, 2, 0, 3)])
r.updateResources(0, 0, 1, 0, 1, 2, net)

seg_status = r.getSegmentStatus(r.getRoute(net)[0], net=net, index=0)
assert seg_status["orientation"] == "horizontal"
assert len(seg_status["resource_edges"]) == 2
assert r.validateSegment(r.getRoute(net)[0])["valid"]
assert r.validateRoute(net)["valid"]

records = r.getEdgeResourceRecords()
r2 = GlobalRouter()
assert r2.applyEdgeResourceRecords(records, clear=True) == len(records)
assert r2.getEdgeResourceRecord(1, 0, 0, 0, 1)["usage"] == r.getEdgeResourceRecord(0, 0, 1, 0, 1)["usage"]

report = r.createRouteReport()
assert report["format"] == "winroad-grt-route-report"
assert report["validation"]["valid"]
assert r.fastroute().getTileCongestionRecord(0, 0, 1)["overflow"] >= 0
assert r.fastroute().validateResources()["valid"]

route_report = base / ".grt_route_report.json"
validation_report = base / ".grt_validation_report.json"
written = r.writeBatchReports({"route": str(route_report), "validation": str(validation_report)})
assert set(written) == {"route", "validation"}
for path in (route_report, validation_report):
    assert path.exists()
    path.unlink()

for call in (r.fastroute().run, r.globalRoute):
    try:
        call()
    except NotImplementedError:
        pass
    else:
        raise AssertionError("routing algorithms must stay unsupported")
print("smoke ok")
'@ | python -
```

## 第八轮验证命令

```powershell
python -m py_compile D:\winroad_py\winroad\grt\types.py D:\winroad_py\winroad\grt\guide.py D:\winroad_py\winroad\grt\congestion.py D:\winroad_py\winroad\grt\grid.py D:\winroad_py\winroad\grt\fast_route.py D:\winroad_py\winroad\grt\global_router.py D:\winroad_py\winroad\grt\__init__.py
@'
from pathlib import Path
from winroad.grt import GSegment, GlobalRouter, Net, Pin

base = Path("D:/winroad_py")
r = GlobalRouter()
r.grid.init((0, 0, 100, 100), 10, 10, 10, True, True, 4)
r.fastroute().setGridsAndLayers(4, 4, 4)
r.fastroute().setEdgeCapacity(0, 0, 1, 0, 1, 2)
r.fastroute().setEdgeUsage(0, 0, 1, 0, 1, 3)

net = "n8"
wr_net = Net(net)
wr_net.addPin(Pin(position=(0, 0), on_grid_position=(0, 0), layers=[1], connection_layer=1))
r.db_net_map[net] = wr_net
r.setRoute(net, [GSegment(0, 0, 1, 1, 0, 1), GSegment(1, 0, 1, 1, 0, 2)])

guide_file = base / ".grt_round8.guide.json"
guide_report = base / ".grt_round8_guide_report.json"
res_file = base / ".grt_round8_resource.json"
tiles_file = base / ".grt_round8_tiles.json"

r.exportGuides(str(guide_file))
assert r.inspectGuideFile(str(guide_file))["net_count"] == 1
assert r.validateGuideFile(str(guide_file))["valid"]

r2 = GlobalRouter()
r2.grid.init((0, 0, 100, 100), 10, 10, 10, True, True, 4)
import_result = r2.importGuideFiles([str(guide_file)], clear=True)
assert import_result["valid"]
assert len(r2.getRoute(net)) == 2

r.exportResourceSnapshot(str(res_file))
r3 = GlobalRouter()
restored = r3.importResourceSnapshot(str(res_file), clear=True)
assert restored["edge_record_count"] == 2
assert r3.getEdgeResourceRecord(1, 0, 0, 0, 1)["usage"] == 3

tiles = r.getTileCongestionRecords(overflow_only=True)
assert tiles and tiles[0]["overflow"] == 1
written = r.writeBatchReports({"guide": str(guide_report), "congestion_tiles": str(tiles_file)})
assert set(written) == {"guide", "congestion_tiles"}

for call in (r.fastroute().run, r.globalRoute):
    try:
        call()
    except NotImplementedError:
        pass
    else:
        raise AssertionError("routing algorithms must stay unsupported")

for path in (guide_file, guide_report, res_file, tiles_file):
    path.unlink(missing_ok=True)
print("round8 smoke ok")
'@ | python -
```

## 第四轮验证命令

```powershell
python -m py_compile D:\winroad_py\winroad\grt.py D:\winroad_py\winroad\grt\types.py D:\winroad_py\winroad\grt\guide.py D:\winroad_py\winroad\grt\congestion.py D:\winroad_py\winroad\grt\grid.py D:\winroad_py\winroad\grt\fast_route.py D:\winroad_py\winroad\grt\global_router.py D:\winroad_py\winroad\grt\__init__.py
@'
from pathlib import Path
from winroad.grt import GSegment, GlobalRouter, GuideFile, Net

base = Path("D:/winroad_py")
r = GlobalRouter()
net = "n1"
r.setRoute(net, [GSegment(0, 0, 1, 2, 0, 1), GSegment(2, 0, 1, 2, 0, 3)])
r.db_net_map[net] = Net(net)
r.setNetAlphaBetaGamma(net, 0.2, 0.3, 0.4)
assert r.getNetAlphaBetaGamma(net) == (0.2, 0.3, 0.4)

r.addLayerAdjustment(2, 0.5)
r.addRegionAdjustment(0, 0, 10, 10, 3, 0.7)
r.removeLayerAdjustment(2)
assert len(r.fastroute().getAdjustments()) == 1

json_guides = base / ".grt_guides.json"
text_guides = base / ".grt_guides.guide"
r.writeGuides(str(json_guides))
r.writeGuides(str(text_guides), format="guide")
r2 = GlobalRouter()
r2.readGuides(str(json_guides))
assert len(r2.routes[net]) == 2
assert GuideFile.fromText(text_guides.read_text()).guides[0].net == net

r.fastroute().setGridsAndLayers(2, 2, 3)
r.fastroute().setEdgeCapacity(0, 0, 1, 0, 1, 1)
r.updateResources(1, 0, 0, 0, 1, 2, net)
assert r.getCongestionReport()["congested_tile_count"] == 1

congestion = base / ".grt_congestion.json"
resource = base / ".grt_resource.json"
state = base / ".grt_state.json"
r.writeCongestionReport(str(congestion))
r.writeResourceReport(str(resource))
r.grid.init((0, 0, 100, 100), 10, 10, 10, True, True, 3)
r.saveState(str(state))
r3 = GlobalRouter()
r3.loadState(str(state))
assert len(r3.routes[net]) == 2
assert r3.getGridSize() == (10, 10)

for path in (json_guides, text_guides, congestion, resource, state):
    path.unlink(missing_ok=True)

for call in (r.fastroute().run, r.globalRoute):
    try:
        call()
    except NotImplementedError:
        pass
    else:
        raise AssertionError("routing algorithms must stay unsupported")
print("smoke ok")
'@ | python -
```

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

## Package 拆分验证命令

```powershell
python -m py_compile D:\winroad_py\winroad\grt.py D:\winroad_py\winroad\grt\types.py D:\winroad_py\winroad\grt\guide.py D:\winroad_py\winroad\grt\congestion.py D:\winroad_py\winroad\grt\grid.py D:\winroad_py\winroad\grt\fast_route.py D:\winroad_py\winroad\grt\global_router.py D:\winroad_py\winroad\grt\__init__.py
@'
from winroad.grt import GSegment, GlobalRouter, Net

r = GlobalRouter()
net = "n1"
r.routes[net] = [GSegment(0, 0, 1, 2, 0, 1)]
r.db_net_map[net] = Net(net)
r.setNetAlphaBetaGamma(net, 0.2, 0.3, 0.4)
assert r.getNetAlphaBetaGamma(net) == (0.2, 0.3, 0.4)
print("smoke ok")
'@ | python -
```

## 说明

- 当前实现保留 OpenROAD grt 的核心对象、入口类和关键函数边界。
- 尚未翻译的 C++ 主算法会显式抛出 `NotImplementedError`，避免生成估算 demo 或伪造布线结果。
- 字段和接口名尽量贴近 C++，同时保留详细中文注释，便于后续逐文件继续翻译。
