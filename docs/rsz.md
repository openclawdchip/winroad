# rsz

`winroad.rsz` 对照 OpenROAD `src/rsz` 翻译。当前目标不是做估算 demo，
而是先把顶层对象、入口类和关键函数边界搬到 Python，后续再逐函数补真实
STA / parasitics / placement 算法。

## 已翻译对象边界

- `Resizer`
  - 对应 `include/rsz/Resizer.hh` 的顶层入口类。
  - 保存 `logger/db/sta/stt_builder/global_router/opendp/estimate_parasitics`
    等 C++ 构造依赖。
  - 建立 dont-use、dont-touch、buffer list、clock buffer pattern、
    resize slack、library analysis、debug graphics 等核心状态。
  - `repairDesign`、`repairSetup`、`repairHold`、`recoverPower` 按 C++
    边界委托到对应子类。

- `BufferUse`、`MoveType`、`VTCategory`、`VTLeakageStats`、`LibraryAnalysisData`
  - 对应 `Resizer.hh` 中的 enum / struct。
  - `LibraryAnalysisData.sort_vt_categories()` 已按平均 leakage 排序。

- `FixedDelay`、`BufferedNetType`、`BufferedNet`、`BufferedNetMetrics`
  - 对应 `src/rsz/src/BufferedNet.hh`。
  - 保留 femtosecond 定点 delay、buffer tree 节点类型、cap/fanout/slew/slack/
    arrival delay 注解。
  - 已实现树形统计：`length()`、`maxLoadWireLength()`、`bufferCount()`、
    `loadCount()`、`metrics()`、`fitsEnvelope()`、`reportTree()`。

- `LoadRegion`
  - 对应 `RepairDesign.hh` 中 fanout pin 分区区域。

- `RepairDesign`
  - 对应 `src/rsz/src/RepairDesign.hh`。
  - 保存 pre-check、buffer size、margin、violation counter、debug graphics、
    slew RC factor 等成员。
  - `insertedBufferCount()`、`setDebugGraphics()`、`getSlewRCFactor()` 等入口已建立。

- `OptoParams`、`RepairSetup`
  - 对应 `src/rsz/src/RepairSetup.hh`。
  - 保存 move sequence、endpoint pass 计数、rejected move、violator/move tracker
    等状态。
  - `setupMoveSequence()` 已按 skip flag 过滤 move 枚举，但具体 `BaseMove`
    派生动作尚未翻译。

- `RepairHold`
  - 对应 `src/rsz/src/RepairHold.hh`。
  - 保存 hold buffer / resize / cloned gate 计数和入口边界。

- `RecoverPower`
  - 对应 `src/rsz/src/RecoverPower.hh`。
  - 保存 power recovery 的场景、bad vertices、面积和迭代常量。

- `PreChecks`
  - 对应 `src/rsz/src/PreChecks.hh`。
  - 保存 slew/cap limit 检查缓存字段。

- `ResizerObserver`
  - 对应 `src/rsz/src/ResizerObserver.hh`。
  - 保留图形调试回调：`setNet()`、`subdivideStart()`、`repairNetStart()`、
    `makeBuffer()` 等。

- `BaseMove`、`SlackEstimatorParams`
  - 对应 `src/rsz/src/BaseMove.hh`。
  - 已实现 move 计数、pending/accepted/rejected 集合、`commitMoves()`、
    `undoMoves()` 等通用状态逻辑。

- `MoveTracker`、`PinInfo`、`MoveStateType`、`MoveStateData`
  - 对应 `src/rsz/src/MoveTracker.hh`。
  - 已实现 critical pin、violator、attempt/commit/reject move 的记录容器。

- `SwapArithModules`
  - 对应 `src/rsz/src/SwapArithModules.hh` 的抽象接口。

- `initResizer()`
  - 对应 `include/rsz/MakeResizer.hh` 的入口函数。
  - Python 版本返回 `Resizer()`，后续可接入 Tcl/命令注册层。

## 已实现的轻量接口

- `Resizer.setDontUse()` / `resetDontUse()` / `dontUse()` / `reportDontUse()`
- `Resizer.setDontTouch()` / `dontTouch()` / `reportDontTouch()`
- `Resizer.setMaxUtilization()` / `coreArea()` / `utilization()` / `maxArea()`
- `Resizer.designArea()` / `designAreaIncr()` / `initDesignArea()`
- `Resizer.dbuToMeters()` / `metersToDbu()`
- `Resizer.setClockBuffersList()` / `setClockBufferString()` /
  `setClockBufferFootprint()` / `resetClockBufferPattern()`
- `Resizer.hasClockBufferString()` / `hasClockBufferFootprint()` /
  `getClockBufferString()` / `getClockBufferFootprint()` / `getBufferUse()`
- `Resizer.parseMove()` / `parseMoveSequence()`
- `Resizer.resizeSlackPreamble()` / `resizeWorstSlackNets()` / `resizeNetSlack()`
- `BaseMove.countMove()` / `commitMoves()` / `undoMoves()` and counters
- `MoveTracker.trackCriticalPins()` / `trackViolator()` /
  `trackViolatorWithInfo()` / `trackMove()` / `commitMoves()` / `rejectMoves()`

## 未翻译的真实算法

以下函数边界已经保留，但因为依赖 OpenSTA graph、Liberty timing model、
OpenDB netlist mutation、estimated parasitics、global router 或 OpenDP，不做假实现。
调用时会抛出 `NotImplementedError`：

- buffer 插入/删除：`insertBufferAfterDriver()`、`insertBufferBeforeLoad()`、
  `insertBufferBeforeLoads()`、`removeBuffers()`、`unbufferNet()`、`bufferInputs()`、
  `bufferOutputs()`
- setup 修复：`RepairSetup.repairSetup()`、`repairEndpoint()`、`repairPins()`、
  `reportSwappablePins()`
- hold 修复：`RepairHold.repairHold()`、`reportHoldBuffer()`
- design 修复：`RepairDesign.repairDesign()`、`repairNet()`、`repairClkNets()`、
  `repairClkInverters()`、`computeSlewRCFactor()`
- power recovery：`RecoverPower.recoverPower()`
- parasitics / slew / delay：`BufferedNet.wireRC()`、`viaResistance()`、
  `Resizer.bufferWireDelay()`、`findDriverSlewForLoad()`、
  `computeNewDelaysSlews()`、`estimateSlewsAfterBufferRemoval()`、
  `estimateSlewsInTree()`
- timing-driven placement / logic resynthesis：
  `findResizeSlacks()`、`findFaninFanouts()`、`findFanins()`
- arithmetic module swap：`SwapArithModules` 的抽象方法和
  `Resizer.swapArithModules()`

## 继续翻译建议

1. 先补 OpenSTA / dbSta 的最小 Python 对象边界，否则 `RepairSetup` 和
   `RepairHold` 无法访问 vertex、path、slack、Liberty arc。
2. 再补 `BufferedNet.wireRC()` / `viaResistance()`，因为 `RepairDesign`、
   `RecoverPower`、`Rebuffer` 都依赖这棵树的 RC 和 slack 注解。
3. 然后从 `RepairDesign::repairDesign` 的 long wire / max fanout 流程开始，
   逐步接入 OpenDB net/buffer mutation。
4. `BaseMove` 派生类建议按 C++ 文件逐个翻译：buffer、unbuffer、size up/down、
   clone、split load、pin swap、VT swap。
