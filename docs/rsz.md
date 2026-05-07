# rsz

`winroad.rsz` 对照 OpenROAD `src/rsz` 翻译。当前目标不是做估算 demo，
而是先把顶层对象、入口类和关键函数边界搬到 Python，后续再逐函数补真实
STA / parasitics / placement 算法。

代码已从单文件拆为 `winroad.rsz` package：公共 enum/dataclass 在
`common.py`，顶层入口在 `resizer.py`，buffer tree 在 `buffered_net.py`，
setup move 边界在 `moves.py`，各修复流程分别在 `repair_design.py`、
`repair_setup.py`、`repair_hold.py`、`recover_power.py`。旧
`winroad/rsz.py` 保留为兼容转发层。

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
    `loadCount()`、`nodeCount()`、`totalWireLength()`、`depth()`、`metrics()`、
    `fitsEnvelope()`、`reportTree()`。
  - 纯数据树行为补齐：`children()`、`setRef()`、`setRef2()`、`setRefs()`、
    `childLength()`、`preorder()`、`postorder()`、`as_dict()`、`serialize()`、
    `to_json()`、`report()`；不访问 STA/DB。

- `LoadRegion`
  - 对应 `RepairDesign.hh` 中 fanout pin 分区区域。

- `RepairDesign`
  - 对应 `src/rsz/src/RepairDesign.hh`。
  - 保存 pre-check、buffer size、margin、violation counter、debug graphics、
    long-wire/max-slew/max-cap/max-fanout counter、slew RC factor 等成员。
  - 新增 `RepairDesignLimits`、`RepairDesignViolationCounters`，用于记录
    long wire / max slew / max cap / max fanout 修复边界参数和统计。
  - `configureLimits()` 采用合并式更新，`resetLimits()` 回到默认限制。
  - `configureLimits()`、`limits()`、`recordRepair()`、`resetViolationCounters()`、
    `violationCounters()`、`reportViolationCounters()`、
    `reportLimits()`、`insertedBufferCount()`、`resizedDriverCount()`、
    `repairedNetCount()`、`setDebugGraphics()`、`getSlewRCFactor()` 等入口已建立。

- `OptoParams`、`RepairSetup`
  - 对应 `src/rsz/src/RepairSetup.hh`。
  - 保存 move sequence、endpoint pass 计数、rejected move、violator/move tracker
    等状态。
  - 新增 `RepairSetupConfig`，用于保存 setup slack margin、skip flags、pass
    repair limit 和筛选后的 move sequence。
  - `setupMoveSequence()` 已按 skip flag 过滤 move 枚举，并映射到 Python 的
    `BaseMove` 派生对象序列；真实 move 算法仍保留同名入口并抛
    `NotImplementedError`。
  - `configure()` 采用合并式更新，`resetConfig()` 清空 setup 配置和 move
    sequence。
  - `configure()`、`config()`、`reportConfig()`、`makeMoveTracker()`、
    `setMoveTracker()`、`beginEndpointRepair()`、`recordRemovedBuffer()`、
    `resetCounters()`、`reportCounters()`、
    `endpointRepairCount()`、`recordRejectedMove()`、`rejectedMovesForPin()`、
    `reportMoveSummary()` 补齐 endpoint / move tracker / report 边界。

- `RepairHold`
  - 对应 `src/rsz/src/RepairHold.hh`。
  - 保存 hold buffer / resize / cloned gate、setup margin、pass limit、
    buffer cell 等状态和入口边界。
  - 新增 `RepairHoldConfig`，保存 hold buffer、pass limit、每 pass repair
    limit、是否允许 setup violation 和 setup slack margin。
  - `configure()` 采用合并式更新，`resetConfig()` 回到默认 hold 配置。
  - `configure()`、`config()`、`reportConfig()`、`setHoldBuffer()`、
    `holdBuffer()`、`recordInsertedBuffer()`、`recordResize()`、
    `recordClonedGate()`、`resetCounters()`、`reportHoldBuffer()`、
    `reportCounters()`、`statistics()`、`to_json()` 补齐 hold buffer 选择、
    计数和 JSON-safe 导出边界；真实 hold buffer 插入仍未翻译。

- `RecoverPower`
  - 对应 `src/rsz/src/RecoverPower.hh`。
  - 保存 power recovery 的场景、bad vertices、面积、match-footprint 标志、
    swapped cell / recovered power 计数和迭代常量。
  - 新增 `RecoverPowerConfig`，保存 recover power percent、match footprint、
    verbose、scene 和 setup slack margin。
  - `configure()` 采用合并式更新，`resetConfig()` 回到默认 recover power 配置。
  - `configure()`、`config()`、`reportConfig()`、`recordSwap()`、
    `recordSizeDown()`、`recordResize()`、`resetCounters()`、`markBadVertex()`、
    `isBadVertex()`、`recoveredPower()`、`sizeDownCount()`、`reportCounters()`、
    `statistics()`、`to_json()` 补齐 swap / size down / bad vertex 统计和
    JSON-safe 导出边界；真实 cell swap/size down mutation 仍未翻译。

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
    `pendingMoves()`、`trackMoveAttempt()`、`trackMoveCommit()`、
    `trackMoveReject()`、`clearPendingMoves()`、`moveSummary()`、
    `moveSummaryByType()`、`as_dict()`、`to_json()`、`report()` 提供只读报告面。

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
- `BaseMove.moveCounters()`
- `RepairSetup.setupMoveSequence()` / `allMoves()` 建立 move 类型到派生对象的
  C++ 边界映射
- `RepairDesign.configureLimits()` / `recordRepair()` /
  `reportViolationCounters()` / `reportLimits()` 和
  `Resizer.configureRepairDesign()` / `repairDesignViolationCounters()` /
  `reportRepairDesignLimits()` / `resetRepairDesignLimits()`
- `RepairSetup.makeMoveTracker()` / `beginEndpointRepair()` /
  `recordRemovedBuffer()` / `reportCounters()` / `reportMoveSummary()` 和
  `Resizer.configureRepairSetup()` / `reportRepairSetupConfig()` /
  `reportRepairSetupCounters()` / `reportSetupMoves()` /
  `resetRepairSetupConfig()`
- `RepairHold.setHoldBuffer()` / `recordInsertedBuffer()` / `resizeCount()` /
  `clonedGateCount()` / `reportCounters()` 和 `Resizer.configureRepairHold()` /
  `reportRepairHoldConfig()` / `reportHoldCounters()` /
  `reportRepairHoldStats()` / `resetRepairHoldConfig()`
- `RecoverPower.configure()` / `recordSwap()` / `recordSizeDown()` /
  `resizeCount()` / `swappedCellCount()` / `sizeDownCount()` /
  `reportCounters()` 和 `Resizer.configureRecoverPower()` /
  `reportRecoverPowerConfig()` / `reportRecoverPowerCounters()` /
  `reportRecoverPowerStats()` / `resetRecoverPowerConfig()`
- `MoveTracker.trackCriticalPins()` / `trackViolator()` /
  `trackViolatorWithInfo()` / `trackMove()` / `commitMoves()` / `rejectMoves()` /
  `moveSummary()` / `moveSummaryByType()` / `as_dict()` / `to_json()` / `report()`

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

## 第六轮验证命令

```powershell
python -m py_compile D:\winroad_py\winroad\rsz\__init__.py D:\winroad_py\winroad\rsz\buffered_net.py D:\winroad_py\winroad\rsz\common.py D:\winroad_py\winroad\rsz\moves.py D:\winroad_py\winroad\rsz\repair_design.py D:\winroad_py\winroad\rsz\repair_setup.py D:\winroad_py\winroad\rsz\repair_hold.py D:\winroad_py\winroad\rsz\recover_power.py D:\winroad_py\winroad\rsz\resizer.py
```

```powershell
$env:PYTHONPATH='D:\winroad_py'
@'
from winroad.rsz import BufferedNet, BufferedNetType, FixedDelay, MoveType, Resizer

r = Resizer()

root = BufferedNet(BufferedNetType.JUNCTION, (0, 0))
load = BufferedNet(BufferedNetType.LOAD, (10, 5), load_pin_=object())
buf = BufferedNet(BufferedNetType.BUFFER, (5, 0), buffer_cell_="BUF_X1")
buf.setRef(load)
root.setRef(buf)
root.setSlack(FixedDelay.from_fs(12))
assert root.serialize()["node_count"] == 3
assert "children" in root.to_json()

rd = r.repair_design_
rd.configureLimits(max_wire_length=100.0, slew_margin=0.1, buffer_cells=["B1"])
rd.configureLimits(max_slew=0.2)
assert rd.reportLimits()["max_wire_length"] == 100.0
rd.resetLimits()
assert rd.reportLimits()["max_wire_length"] is None

rs = r.repair_setup_
tracker = rs.makeMoveTracker()
tracker.setCurrentEndpoint("EP")
tracker.trackMoveAttempt("pin", "BufferMove")
tracker.commitMoves()
assert tracker.moveSummary()["attempt_commit"] == 1
assert "moves" in tracker.to_json()
rs.configure(setup_slack_margin=0.01, skip_size_down=True)
rs.configure(max_repairs_per_pass=7)
assert rs.reportConfig()["setup_slack_margin"] == 0.01
rs.setupMoveSequence([MoveType.BUFFER, MoveType.SWAP, MoveType.SIZEDOWN], False, False, True, False, False, False)
assert rs.moveSequenceTypes() == [MoveType.BUFFER, MoveType.SWAP]

rh = r.repair_hold_
rh.configure(buffer_cell="BUF_X1", max_passes=2)
rh.recordInsertedBuffer(2)
assert rh.statistics()["inserted_buffers"] == 2

rp = r.recover_power_
rp.configure(recover_power_percent=10.0, scene="slow")
rp.configure(verbose=True)
rp.recordSwap(1, 0.25)
rp.recordSizeDown(2, 0.5)
assert rp.statistics()["config"]["scene"] == "slow"

try:
    r.repairDesign()
except NotImplementedError:
    pass
else:
    raise AssertionError("repairDesign should remain untranslated")
print("ok")
'@ | python -
```
