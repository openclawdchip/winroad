# pdn

## 翻译范围

- 本轮只改 `winroad/pdn.py` 和 `docs/pdn.md`。
- 参考本机 OpenROAD `src/pdn`：
  - `include/pdn/PdnGen.hh`
  - `src/domain.h`
  - `src/grid.h`
  - `src/grid_component.h`
  - `src/rings.h`
  - `src/straps.h`
  - `src/connect.h`
  - `src/via.h`
  - `src/power_cells.h`
  - `src/pdn.tcl`
- Python 侧只建立顶层对象、函数边界和对象关系，不写 OpenDB，不生成示例几何。

## 已实现边界

- 枚举/基础类型
  - `ExtensionMode`
  - `StartsWith`
  - `PowerSwitchNetworkType`
  - `GridType`
  - `GridComponentType`
  - `ShapeType`
  - `FailedViaReason`
  - `Rect`
  - `Halo`

- 顶层入口
  - `PdnGen`
  - `make_pdn_gen()`
  - `initPdnGen()`
  - `makePdnGen()`
  - `deletePdnGen()`
  - `pdngen()`
  - `report_power_grid()`
  - `check_power_grid()`
  - `repair_pdn_vias()`
  - `ripup_power_grid()`
  - `write_power_grid()`

- `PdnGen` 方法边界
  - `init()`
  - `reset()`
  - `resetShapes()`
  - `report()`
  - `findSwitchedPowerCell()`
  - `makeSwitchedPowerCell()`
  - `getDomains()`
  - `findDomain()`
  - `setCoreDomain()`
  - `makeRegionVoltageDomain()`
  - `buildGrids()`
  - `findGrid()`
  - `makeCoreGrid()`
  - `makeInstanceGrid()`
  - `makeExistingGrid()`
  - `makeRing()`
  - `makeFollowpin()`
  - `makeStrap()`
  - `makeConnect()`
  - `writeToDb()`
  - `ripUp()`
  - `setDebugRenderer()`
  - `rendererRedraw()`
  - `setAllowRepairChannels()`
  - `filterVias()`
  - `checkSetup()`
  - `repairVias()`
  - `createSrouteWires()`
  - `trimShapes()`
  - `updateVias()`
  - `cleanupVias()`
  - `checkDesign()`
  - `ensureCoreDomain()`
  - `updateRenderer()`
  - `importUPF()`

- Voltage domain
  - `VoltageDomain`
  - 已保留 power / switched power / always-on power / ground / secondary nets / region / grids 关系
  - 已建立 `getNets()`、`addGrid()`、`resetGrids()`、`clearGrids()`、`removeGrid()`、`report()`、`checkSetup()`

- Grid 对象层
  - `Grid`
  - `CoreGrid`
  - `InstanceGrid`
  - `BumpGrid`
  - `ExistingGrid`
  - 已保留 rings / straps / connect / pin layers / via / switched power cell 关系
  - 已建立 `addRing()`、`addStrap()`、`addConnect()`、`removeStrap()`、`getNets()`、`resetShapes()`、`ripup()`、`report()`、`checkSetup()`

- Grid component / shape
  - `GridComponent`
  - `Shape`
  - `RingLayer`
  - `Rings`
  - `Straps`
  - `FollowPins`
  - `PadDirectConnectionStraps`
  - `RepairChannelStraps`
  - 已保留 shape list、net 顺序、start-with-power、ring layer/offset、strap pitch/width/spacing/extend/snap 等字段

- Connect / via
  - `Connect`
  - `Via`
  - `Enclosure`
  - `DbVia`
  - `DbBaseVia`
  - `DbTechVia`
  - `DbGenerateVia`
  - `DbSplitCutVia`
  - `DbArrayVia`
  - `DbGenerateStackedVia`
  - `DbGenerateDummyVia`
  - `ViaGenerator`
  - `GenerateViaGenerator`
  - `TechViaGenerator`
  - 已保留 cut pitch、fixed vias、max rows/columns、ongrid、split cuts、failed via report 等边界字段

- Power switch / sroute / renderer
  - `PowerCell`
  - `GridSwitchedPower`
  - `SRoute`
  - `PDNRenderer`

## 未实现

- `PdnGen::buildGrids()` 的真实 PDN 图形生成、trim、via 更新、cleanup 流程
- `PdnGen::writeToDb()`、`Grid::writeToDb()`、`Shape::writeToDb()`、`Via::writeToDb()` 的 OpenDB 写入
- `Grid::makeShapes()`、`Grid::makeVias()`、`GridComponent::makeShapes()`、`Shape::cut()` 的几何生成/裁剪算法
- `Connect::makeVia()`、`ViaGenerator::build()`、`ViaGenerator::generate()` 及所有 db via wrapper 的真实 via 构造
- `RepairChannelStraps::repairGridChannels()`、`PdnGen::repairVias()` 的 repair channel / repair via 算法
- `SRoute::createSrouteWires()` 的 add_sroute_connect 实现
- `PowerCell::appliesToRow()`、`GridSwitchedPower::build()` 的 power switch 放置和控制网连接
- `ExistingGrid::populate()` 对已有 SPECIALNET 的读取
- `VoltageDomain::getDomainArea()`、`VoltageDomain::getRows()` 的 core/region 几何读取
- UPF 导入、debug renderer redraw、pad direct connection refine/cut 等细节

## 说明

- 当前 Python 层不依赖具体 `odb` 类型，所有 ODB 对象均以 `Any` 保存引用。
- 可安全构建 `PdnGen -> VoltageDomain -> Grid -> Ring/Strap/Connect` 对象树并调用 `report()`。
- 涉及真实 PDN 算法、数据库写入或物理几何生成的同名入口会显式抛 `NotImplementedError`，避免误把 demo 行为当作算法结果。
