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
    target load map、input slew map、tie cell/port、resize slack、library analysis、
    debug graphics 等核心状态。
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
    long-wire/max-slew/max-cap/max-fanout counter、slew RC factor 等成员。
  - 新增 `RepairDesignLimits`、`RepairDesignViolationCounters`，用于记录
    long wire / max slew / max cap / max fanout 修复边界参数和统计。
  - `configureLimits()`、`limits()`、`recordRepair()`、`resetViolationCounters()`、
    `violationCounters()`、`reportViolationCounters()`、
    `insertedBufferCount()`、`setDebugGraphics()`、`getSlewRCFactor()` 等入口已建立。

- `OptoParams`、`RepairSetup`
  - 对应 `src/rsz/src/RepairSetup.hh`。
  - 保存 move sequence、endpoint pass 计数、rejected move、violator/move tracker
    等状态。
  - `setupMoveSequence()` 已按 skip flag 过滤 move 枚举，并映射到 Python 的
    `BaseMove` 派生对象序列；真实 move 算法仍保留同名入口并抛
    `NotImplementedError`。
  - `makeMoveTracker()`、`setMoveTracker()`、`beginEndpointRepair()`、
    `endpointRepairCount()`、`recordRejectedMove()`、`rejectedMovesForPin()`、
    `reportMoveSummary()` 补齐 endpoint / move tracker / report 边界。

- `RepairHold`
  - 对应 `src/rsz/src/RepairHold.hh`。
  - 保存 hold buffer / resize / cloned gate、setup margin、pass limit、
    buffer cell 等状态和入口边界。
  - `setHoldBuffer()`、`holdBuffer()`、`recordInsertedBuffer()`、`recordResize()`、
    `recordClonedGate()`、`reportHoldBuffer()`、`reportCounters()` 补齐 hold
    buffer 选择和计数边界；真实 hold buffer 插入仍未翻译。

- `RecoverPower`
  - 对应 `src/rsz/src/RecoverPower.hh`。
  - 保存 power recovery 的场景、bad vertices、面积、match-footprint 标志、
    swapped cell / recovered power 计数和迭代常量。
  - `configure()`、`recordSwap()`、`recordSizeDown()`、`markBadVertex()`、
    `isBadVertex()`、`recoveredPower()`、`sizeDownCount()`、`reportCounters()`
    补齐 swap / size down / bad vertex 统计边界；真实 cell swap/size down
    mutation 仍未翻译。

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

- `BufferMove`、`UnbufferMove`、`SizeUpMove`、`SizeUpMatchMove`、`SizeDownMove`、
  `SwapPinsMove`、`CloneMove`、`SplitLoadMove`、`VTSwapSpeedMove`
  - 对应 `src/rsz/src/*Move.hh` 的 setup repair 动作类边界。
  - 已建立 `name()`、`doMove()` 及各类私有/辅助入口的 Python 方法名。
  - 真实 rebuffer、buffer removal、gate sizing、pin swap、clone、split load、
    VT swap 算法依赖 STA/OpenDB mutation，当前均抛 `NotImplementedError`。

- `MoveTracker`、`PinInfo`、`MoveStateType`、`MoveStateData`
  - 对应 `src/rsz/src/MoveTracker.hh`。
  - 已实现 critical pin、violator、attempt/commit/reject move 的记录容器。
  - `currentEndpoint()`、`criticalPins()`、`violators()`、`pinInfo()`、`moves()`、
    `pendingMoves()`、`moveSummary()` 提供只读报告面。

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
- `Resizer.targetLoadCap()` 可返回已缓存的 `target_load_map_` 条目；未缓存时
  保持真实算法边界并抛未翻译错误
- `Resizer.dbuToMeters()` / `metersToDbu()`
- `Resizer.setClockBuffersList()` / `setClockBufferString()` /
  `setClockBufferFootprint()` / `resetClockBufferPattern()`
- `Resizer.hasClockBufferString()` / `hasClockBufferFootprint()` /
  `getClockBufferString()` / `getClockBufferFootprint()` / `getBufferUse()`
- `Resizer.parseMove()` / `parseMoveSequence()`
- `Resizer.resizeSlackPreamble()` / `resizeWorstSlackNets()` / `resizeNetSlack()`
- `BaseMove.countMove()` / `commitMoves()` / `undoMoves()` and counters
- `RepairSetup.setupMoveSequence()` / `allMoves()` 建立 move 类型到派生对象的
  C++ 边界映射
- `RepairDesign.configureLimits()` / `recordRepair()` /
  `reportViolationCounters()` 和 `Resizer.repairDesignViolationCounters()`
- `RepairSetup.makeMoveTracker()` / `beginEndpointRepair()` /
  `reportMoveSummary()` 和 `Resizer.reportSetupMoves()`
- `RepairHold.setHoldBuffer()` / `recordInsertedBuffer()` / `resizeCount()` /
  `clonedGateCount()` / `reportCounters()` 和 `Resizer.reportHoldCounters()`
- `RecoverPower.configure()` / `recordSwap()` / `recordSizeDown()` /
  `resizeCount()` / `swappedCellCount()` / `sizeDownCount()` /
  `reportCounters()` 和 `Resizer.reportRecoverPowerCounters()`
- `MoveTracker.trackCriticalPins()` / `trackViolator()` /
  `trackViolatorWithInfo()` / `trackMove()` / `commitMoves()` / `rejectMoves()` /
  `moveSummary()`

## 未翻译的真实算法

以下函数边界已经保留，但因为依赖 OpenSTA graph、Liberty timing model、
OpenDB netlist mutation、estimated parasitics、global router 或 OpenDP，不做假实现。
调用时会抛出 `NotImplementedError`：

- buffer 插入/删除：`insertBufferAfterDriver()`、`insertBufferBeforeLoad()`、
  `insertBufferBeforeLoads()`、`removeBuffers()`、`unbufferNet()`、`bufferInputs()`、
  `bufferOutputs()`
- setup 修复：`RepairSetup.repairSetup()`、`repairEndpoint()`、`repairPins()`、
  `reportSwappablePins()`；`BufferMove`、`UnbufferMove`、`SizeUpMove`、
  `SizeUpMatchMove`、`SizeDownMove`、`SwapPinsMove`、`CloneMove`、
  `SplitLoadMove`、`VTSwapSpeedMove` 的 `doMove()` 和辅助函数
- hold 修复：`RepairHold.repairHold()`
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

## 第三轮验证命令

```powershell
python -m py_compile D:\winroad_py\winroad\rsz.py
```

```powershell
@'
from winroad.rsz import Resizer, MoveStateType, MoveType
r = Resizer()
rd = r.repair_design_
rd.configureLimits(max_wire_length=100.0, max_slew=2.0, max_cap=3.0, max_fanout=8)
rd.recordRepair(long_wire=1, max_slew=2, max_cap=3, max_fanout=4, inserted_buffers=5, resized_drivers=6, repaired_nets=7)
assert r.repairDesignViolationCounters()["long_wire"] == 1
rs = r.repair_setup_
tracker = rs.makeMoveTracker()
rs.setupMoveSequence([MoveType.BUFFER, MoveType.SWAP, MoveType.SIZEDOWN], False, False, True, False, False, False)
assert rs.moveSequenceTypes() == [MoveType.BUFFER, MoveType.SWAP]
assert rs.beginEndpointRepair("end") == 1
tracker.trackMove("pin", "buffer", MoveStateType.ATTEMPT)
tracker.commitMoves()
assert tracker.moveSummary()["attempt_commit"] == 1
rh = r.repair_hold_
rh.setHoldBuffer("BUF_X1")
rh.recordInsertedBuffer(2)
assert rh.reportCounters()["inserted_buffers"] == 2
rp = r.recover_power_
rp.configure(match_cell_footprint=True)
rp.recordSwap(1, 0.25)
rp.recordSizeDown(2, 0.5)
assert rp.reportCounters()["sizedown_cells"] == 2
try:
    r.repairDesign()
except NotImplementedError:
    pass
else:
    raise AssertionError("repairDesign should remain untranslated")
print("ok")
'@ | python -
```
