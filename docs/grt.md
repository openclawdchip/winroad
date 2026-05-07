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
  - `FastRouteCore` 的 grid/layer/capacity/net 注册、route 清理、debug、线程、拥塞参数接口
  - `GlobalRouter` 的配置入口、route 查询、连通性检查、资源更新转发、增量 dirty net 标记、debug 转发、grid/layer 查询接口

## 未实现

- FastRoute 主算法：
  - Steiner tree / rectilinear Steiner tree 构建
  - 2D/3D maze routing
  - layer assignment
  - overflow/congestion rip-up and reroute
  - capacity lower bound 与 edge graph 完整初始化
- OpenDB 真实 guide/wire 读写：
  - `readGuides()`
  - `loadGuidesFromDB()`
  - `saveGuides()`
  - `writeSegments()`
  - `readSegments()`
  - `updateVias()`
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
- CUGR 接入、RUDY/heatmap、拥塞图文件格式和报告输出仍待按 OpenROAD C++ 逐函数移植。

## 说明

- 当前实现保留 OpenROAD grt 的核心对象、入口类和关键函数边界。
- 尚未翻译的 C++ 主算法会显式抛出 `NotImplementedError`，避免生成估算 demo 或伪造布线结果。
- 字段和接口名尽量贴近 C++，同时保留详细中文注释，便于后续逐文件继续翻译。
