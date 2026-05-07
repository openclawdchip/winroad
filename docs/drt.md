# drt

## 第二轮翻译补位

- 已按本机 OpenROAD `src/drt` C++ 源码边界建立 Python 顶层骨架。
- `winroad.drt` 已从历史单文件拆分为 package；`winroad/drt.py` 仅保留兼容转发。
- 本轮不触碰 `odb`。
- 目标是补齐可落地的数据关系、状态容器、marker/guide/report 与 grid graph
  容器行为，不实现 demo detailed routing。

## Package 结构

- `winroad/drt/__init__.py`：保留原 `winroad.drt` 的公共导出面。
- `winroad/drt/types.py`：基础类型、enum、配置、debug 和共享 helper。
- `winroad/drt/fr.py`：drt 私有设计数据库对象，包括 tech/block/net/via/guide/marker/region query/design。
- `winroad/drt/grid_graph.py`：`FlexMazeIdx`、`FlexGridGraphNode`、`FlexGridGraph`。
- `winroad/drt/flex_dr.py`：`FlexDR`、`FlexDRViaData`、`FlexDRSearchRepairArgs`。
- `winroad/drt/flex_gr.py`：`FlexGR`。
- `winroad/drt/flex_pa.py`：`FlexPA`。
- `winroad/drt/gc.py`：`FlexGCWorker`。
- `winroad/drt/triton_route.py`：`TritonRoute` 与 `create_triton_route()`。

## 已实现对象边界

- 顶层入口与工厂：
  - `TritonRoute`
  - `create_triton_route()`
- 顶层配置与 debug：
  - `ParamStruct`
  - `RouterConfiguration`
  - `frDebugSettings`
  - `RipUpMode`
- 基础类型与 enum：
  - `Point`
  - `Rect`
  - `frCoord`
  - `frLayerNum`
  - `frUInt4`
  - `frDirEnum`
  - `frBlockObjectEnum`
  - `dbTechLayerDir`
  - `dbTechLayerType`
- drt 私有设计数据库对象：
  - `frDesign`
  - `frTechObject`
  - `frBlock`
  - `frNet`
  - `frNode`
  - `frShape`
  - `frGuide`
  - `frMarker`
  - `frViaDef`
  - `frVia`
  - `frLayer`
  - `frRegionQuery`
- routing/PA/GC 顶层阶段：
  - `FlexGR`
  - `FlexDR`
  - `FlexDRViaData`
  - `FlexDRSearchRepairArgs`
  - `FlexGridGraph`
  - `FlexGridGraphNode`
  - `FlexMazeIdx`
  - `FlexPA`
  - `FlexGCWorker`

## 已实现轻量行为

- `TritonRoute`：
  - `init()` 建立空 `frDesign`，保存 logger/dist/stt/graphics 指针。
  - `setParams()` 将 `ParamStruct` 写入 `RouterConfiguration`。
  - debug/distributed/worker result/user selected via 等状态接口已补齐。
  - `clearDesign()`、`getDesign()`、`getRouterConfiguration()`、`getDebugSettings()` 等查询入口可用。
- `frDesign` / `frBlock` / `frTechObject`：
  - 支持 tech layer、via def、top block、net、marker、master、update、version 的轻量管理。
  - 支持 preferred/non-preferred track 查询边界。
  - `setTopBlock()` 会建立 block 到 design 的 owner 关系；`frBlock.addNet()` 会维护 net owner，
    同名 net 后加覆盖旧对象。
  - `frTechObject.addLayer()` 按层号排序并替换同名/同层对象；`addViaDef()` 维护 via def owner，
    并把 default/secondary via def 挂回底层 routing layer。
  - `frRegionQuery` 已提供线性容器索引：`init()` 收集 top block 中 shape/via/patch
    wire/guide/marker，`query()` 按 bbox 与 layer 返回相交对象，`add()`/`remove()` 可增删索引对象。
- `frNet`：
  - 支持 inst term/bterm、shape、via、patch wire、guide、node、GR shape/via 的容器管理。
  - 支持 modified/fake/fixed/clock/NDR/jumper/special 等状态位。
  - 支持 NDR/clock absolute priority 的基础配置映射。
  - route/guide 添加接口会维护对象 owner；`clearRoutes()`、`clearGuides()` 会清理反向 owner。
  - 新增 route/guide/orig guide/node/GR 对象 getter，以及 shape/via 移除接口。
- `frLayer` / `frVia` / `frGuide` / `frMarker`：
  - 支持名称、层号、方向、宽度、pitch、via def、bbox、owner 等不依赖 odb 的访问器。
  - `frGuide` 支持 begin/end layer 查询；`frMarker` 支持 constraint、source 列表、owner 与 type id。
- `FlexGridGraph`：
  - 支持坐标设置、维度、bbox、maze index、layer index、edge/block 状态查询。
  - `setCoords()` 会去重排序并初始化节点、z height 与 layer preferred direction。
  - 新增 node/x/y/z 坐标 getter、edge/block/grid cost/special via 的设置与查询、reset/clear、
    index 边界检查。
  - W/S/D 查询映射到相邻节点的 E/N/U 边状态，便于把 grid graph 当三维容器使用。
- 报告与配置：
  - `RouterConfiguration` 新增 `update()`、`to_dict()`、`copy()`；`TritonRoute.getRouterConfigurationState()`
    返回当前配置快照。
  - `TritonRoute.reportDRC()` 可把已有 marker 序列写成文本报告；不运行 DRC。
  - `TritonRoute.reportConstraints()` 可汇总当前 tech layer 约束数量到 logger。
  - `FlexDR.reportGuideCoverage()` 可将现有 net guide 数量写入 `GUIDE_REPORT_FILE` 或 logger；不检查真实覆盖。
- `FlexDR` / `FlexGR` / `FlexPA` / `FlexGCWorker`：
  - 支持构造、设计/tech/region query 获取、debug/distributed/target 状态设置。

## 显式未实现

以下入口保留 C++ 同名边界并抛 `NotImplementedError`：

- `TritonRoute`：
  - `main()`
  - `prep()`
  - `initGuide()`
  - `pinAccess()`
  - `stepDR()`
  - `gr()`
  - `ta()`
  - `dr()`
  - `endFR()`
  - `checkDRC()`
  - `routeLayerLengths()`
  - `runDRWorker()`
  - `debugSingleWorker()`
  - `updateGlobals()`
  - `resetDb()`
  - `updateDesign()`
  - `sendDesignDist()`
  - `writeGlobals()`
  - `sendDesignUpdates()`
  - `sendGlobalsUpdates()`
  - `fixMaxSpacing()`
  - `deleteInstancePAData()`
  - `addInstancePAData()`
- `FlexGR`：
  - `main()`
  - `init()`
  - `searchRepair()`
  - `layerAssign()`
  - `writeToGuide()`
  - `updateDb()`
- `FlexDR`：
  - `init()`
  - `main()`
  - `searchRepair()`
  - `end()`
  - `fixMaxSpacing()`
- `FlexGridGraph`：
  - `init()`
  - `search()`
  - `traceBackPath()`
  - `updatePrevNodeCost()`
- `FlexPA`：
  - `main()`
  - `init()`
  - `genAllAccessPoints()`
- `FlexGCWorker`：
  - `init()`
  - `main()`
  - `updateDRNet()`
## 说明

- 本轮严格保留 OpenROAD `src/drt` 的顶层模块边界：PA、GR、TA、DR、GC、
  grid graph、设计对象、tech layer、net/via/guide/marker。
- 真实 detailed routing、DRC、search/maze、worker 并行、分布式通信、
  guide/DEF/ODB 读写均未实现，避免伪造布线结果。已实现的 DRC/guide report 只汇总
  传入或已有对象，不创建 marker、不判定违规、不修改布线。
- 后续轮次可沿 `NotImplementedError` 的入口逐文件翻译 C++ 实现。
