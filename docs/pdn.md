# pdn

## 翻译范围

- 本轮只改 `winroad/pdn.py`、`winroad/pdn/*` 和 `docs/pdn.md`。
- 参考本机 OpenROAD `src/pdn`：
  - `include/pdn/PdnGen.hh`
  - `src/domain.h`
  - `src/grid.h`
  - `src/grid_component.h`
  - `src/rings.h`
  - `src/straps.h`
  - `src/connect.h`
  - `src/via.h`
  - `src/sroute.h`
  - `src/renderer.h`
  - `src/power_cells.h`
  - `src/pdn.tcl`
- Python 侧只建立顶层对象、函数边界、参数保存和对象关系，不写 OpenDB，不生成示例几何。

## Package 拆分

- `winroad/pdn.py` 只保留兼容转发：`from .pdn import *`。
- `winroad/pdn/types.py`：枚举、`Rect`/`Halo`、`SplitCut`、`Shape` 和共享 helper。
- `winroad/pdn/via.py`：`Via`、db via wrapper、via generator、`Connect`。
- `winroad/pdn/component.py`：`GridComponent`、ring/strap/followpin/pad/repair channel。
- `winroad/pdn/grid.py`：`Grid`、`CoreGrid`、`InstanceGrid`、`BumpGrid`、`ExistingGrid`。
- `winroad/pdn/domain.py`：`VoltageDomain`、`PowerCell`、`GridSwitchedPower`。
- `winroad/pdn/sroute.py`：`SRoute`。
- `winroad/pdn/renderer.py`：`PDNRenderer`。
- `winroad/pdn/pdngen.py`：`PdnGen` 和 Tcl 风格顶层函数。
- `winroad/pdn/__init__.py` 聚合导出，`import winroad.pdn` 仍可直接访问原 `pdn.py` 中的公开类和函数。

## 已实现边界

- 枚举/基础类型
  - `ExtensionMode`
  - `StartsWith`
  - `PowerSwitchNetworkType`
  - `GridType`
  - `GridComponentType`
  - `ShapeType`
  - `FailedViaReason`
  - `SplitCut`
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
  - `getGridByName()`
  - `findGridForInstance()`
  - `findGridContainingRect()`
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
  - `addSrouteConnect()`
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
  - 已建立 `getNets()`、`addGrid()`、`resetGrids()`、`clearGrids()`、`removeGrid()`、`findGrid()`、`getGridByName()`、`report()`、`checkSetup()`

- Grid 对象层
  - `Grid`
  - `CoreGrid`
  - `InstanceGrid`
  - `BumpGrid`
  - `ExistingGrid`
  - 已保留 rings / straps / connect / pin layers / via / switched power cell 关系
  - 已建立 `addRing()`、`addStrap()`、`addConnect()`、`removeStrap()`、`getNets()`、`getGridComponents()`、`getShapes()`、`getVias()`、`findComponent()`、`findConnect()`、`build()`、`resetShapes()`、`ripup()`、`report()`、`checkSetup()`

- Grid component / shape
  - `GridComponent`
  - `Shape`
  - `RingLayer`
  - `Rings`
  - `Straps`
  - `FollowPins`
  - `PadDirectConnectionStraps`
  - `RepairChannelStraps`
  - 已保留 shape list、net 顺序、start-with-power、ring layer/offset/pad-offset、strap pitch/width/spacing/extend/snap/start/end、pad direct connection、repair channel area/repair nets 等字段
  - `GridComponent.build()` 保留 C++ build 顺序边界：layer check、make/refine/cut；实际几何仍在 `makeShapes()`/`cutShapes()` 抛 `NotImplementedError`
  - `Rings.report()`、`Straps.report()`、`PadDirectConnectionStraps.report()`、`RepairChannelStraps.report()` 会展开参数边界

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
  - 已保留 cut pitch、fixed vias、max rows/columns、ongrid、split cuts pitch/stagger、via list、failed via report 等边界字段
  - `Connect` 已建立 `getSplitCut()`、`getSplitCutPitch()`、`isSplitCutStaggered()`、`getVias()`、`addVia()`、`clearFailedVias()`、参数化 `report()`
  - `DbBaseVia.getViaReport()` 和 `DbGenerateStackedVia.getViaReport()` 已建立计数报告边界；真实 via 生成继续抛 `NotImplementedError`

- Power switch / sroute / renderer
  - `PowerCell`
  - `GridSwitchedPower`
  - `SRoute`
  - `PDNRenderer`
  - `SRoute.addSrouteConnect()`/`getSrouteConnects()` 只保存 `add_sroute_connect` 参数；`createSrouteWires()` 保留同名算法入口并抛 `NotImplementedError`
  - `PDNRenderer` 保存 enabled/block/logger/grids/selected，支持 `setBlock()`、`setLogger()`、`setGrids()`、`select()`、`clear()`、`report()`；`redraw()` 保留入口并抛 `NotImplementedError`

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
- 可安全构建 `PdnGen -> VoltageDomain -> Grid -> Ring/Strap/Connect` 对象树并调用 `report()`、domain/grid lookup、connect/component lookup、sroute 参数保存。
- 涉及真实 PDN 算法、数据库写入或物理几何生成的同名入口会显式抛 `NotImplementedError`，避免误把 demo 行为当作算法结果。

## 第二轮补充重点

- grid component build/write/check/report
  - `GridComponent.build()`、`Grid.build()` 建立 C++ 调用顺序边界，实际 `makeShapes()`/`makeVias()`/`writeToDb()` 不实现。
  - 组件和 grid report 展开 ring、strap、connect、pin layer、repair channel、shape/via count。
- via repair
  - `PdnGen.repairVias()` 先执行 setup 检查，再保留同名算法入口并抛 `NotImplementedError`。
  - `Connect` 增加 failed via 清理和 split cut pitch/stagger 查询。
- sroute
- `PdnGen.addSrouteConnect()` 和 `SRoute.addSrouteConnect()` 只记录 Tcl 参数映射，`createSrouteWires()` 不生成线。
- renderer
  - `PDNRenderer` 增加状态保存和报告，`redraw()` 不绘制。
- domain/grid lookup
  - `VoltageDomain.findGrid()`、`getGridByName()`；`PdnGen.getGridByName()`、`findGridForInstance()`、`findGridContainingRect()`。
- connect/ring/strap 参数边界
  - ring report 包含 layer width/spacing、offset、pad offset、extend、allow out-of-die。
  - strap report 包含 layer、width、pitch、spacing、count、offset、snap、extend、start/end、direction。
  - connect report 包含 fixed vias、tech vias、cut pitch、max rows/columns、ongrid、split cuts、via/failure count。

## 第三轮补充重点

- 参数校验
  - 新增共享 rect/halo/正数/非负数校验 helper；`Shape`、ring offset、instance halo、repair channel area、via area、failed via rect 会做基础合法性检查。
  - ring layer 要求真实 layer 下 width 为正、spacing 非负；strap/followpin/connect 会检查 layer、width、pitch、spacing、cut pitch、max rows/columns 等纯参数。
  - domain/grid/cell/sroute 增加空对象、空名、重复 grid/domain/power switch cell、空 sroute 参数等检查。
- 状态管理
  - component、shape、via、connect 之间维护纯数据回链；重复 add 会去重，clear/reset 会断开 shape/via 关系。
  - grid/domain 添加对象时会校正归属关系并避免重复插入；`PdnGen.reset()` 同步清理 renderer 并按初始化状态重建 sroute 容器。
  - `Connect.filterVias()` 现在只在已指定固定 via 列表中按名称过滤，不触发真实 via 构造。
- report / lookup
  - `PdnGen.report()` 增加 domain/grid 计数；component report 展开 shape report；connect report 展开 via report；renderer report 展开 selected 名称。
  - `InstanceGrid.report()` 展开 instance、halo、boundary、replaceable、valid；`ExistingGrid.report()` 展开已有 shape 计数。
  - `Shape.report()`、`Via.report()`、`SRoute.report()` 提供纯数据报告。

## 验证

- `python -m py_compile` 已覆盖 `winroad/pdn.py` 和 `winroad/pdn/*.py`。
- smoke 覆盖 `PdnGen -> VoltageDomain -> CoreGrid -> Ring/Strap/Connect -> Shape/Via` 对象树、lookup、report、sroute 参数保存、renderer 状态，并确认 `buildGrids()` 仍抛 `NotImplementedError`。

## 第六轮补充重点

- PdnGen config/state export-import
  - `PdnGen.exportConfig()` 导出可复建的纯配置字典：domain、grid、ring/strap/followpin/repair/pad component、connect、sroute、renderer 开关与选择快照。
  - `PdnGen.importConfig()` 从上述配置复建 Python 对象树；引用对象默认按名称字符串保存，可传入 resolver 将名称恢复成本地对象。
  - `PdnGen.exportState()` 在 config 外追加 runtime 状态：component shapes、connect vias、failed vias、summary。
  - `PdnGen.importState()` 先导入配置，再恢复 shape/via/failure runtime 状态；不触发几何生成和 OpenDB 写回。
  - 增加 Tcl/Python 便捷包装：`export_power_grid_config()`、`import_power_grid_config()`、`export_power_grid_state()`、`import_power_grid_state()`。
- report 汇总
  - `PdnGen.reportSummary()` 汇总 domain/grid/shape/via/failed-via/sroute/renderer。
  - `VoltageDomain.summary()`、`Grid.summary()` 提供 domain/grid 级聚合。
  - `PdnGen.report()` 增加 `summary`、结构化 `sroute` 报告和 renderer snapshot。
  - 增加 `report_power_grid_summary()`。
- via failure report
  - `Connect.failedViaReport()` 展开 reason/net/rect 明细。
  - `Grid.viaFailureReport()` 和 `PdnGen.viaFailureReport()` 按层级聚合 failure 总数和 reason 计数。
  - 增加 `report_pdn_via_failures()`。
- renderer selection snapshot
  - `PDNRenderer.selectionSnapshot()` 保存 selected item 的类型和名称。
  - `PDNRenderer.snapshot()` 保存 enabled/block/grids/selected，供 config/state 导出。
- sroute summary
  - `SRoute.summary()` 汇总 connect 数量、包含 net/layer 参数的 connect 数量和参数 key 集。
  - `SRoute.report()` 保留原始参数列表并追加 summary 字段。
- 真实算法边界
  - `buildGrids()`、`writeToDb()`、`repairVias()`、`createSrouteWires()`、renderer `redraw()`、真实 via/shape/db 构造继续显式抛 `NotImplementedError`。

## 第六轮验证

- `python -m py_compile` 已覆盖 `winroad/pdn/*.py`。
- smoke 覆盖 config/state export-import round trip、shape/via/failure 恢复、summary、via failure report、sroute summary、renderer selection snapshot，并确认 `buildGrids()` 仍抛 `NotImplementedError`。
