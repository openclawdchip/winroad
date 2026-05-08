# GPL 测试对照计划

来源：`C:\Users\yh-PC-003\Desktop\codex\OpenROAD\src\gpl\test`

建立日期：2026-05-08

用途：WinRoad 在复刻 OpenROAD GPL 时，完成某一段源码翻译后，必须对照 GPL 原测试目录补齐并运行对应测试。以后 GPL 的“完成”不能只看代码是否能 import，还要看是否能通过这里记录的对照测试。

## 总规则

- GPL 主线每完成一个源码责任区，必须同步检查 `OpenROAD/src/gpl/test` 中对应测试。
- 能直接移植为 Python 的测试，放入 WinRoad 的 `tests/gpl/`。
- 依赖完整 OpenROAD Tcl、LEF/DEF、OpenDB、STA、FastRoute 的测试，先建立同名 Python 测试壳和差距说明，等依赖模块补齐后再打开完整断言。
- 不允许用随机 demo 替代 OpenROAD 原测试目标；测试应尽量复用原 `.py/.tcl/.ok/.defok` 中的输入、命令和黄金结果。
- 每轮 GPL 代码提交前至少运行：
  - `python -m py_compile` 覆盖 `winroad/gpl`
  - 已移植的 `tests/gpl` Python 测试
  - 与本轮改动源码对应的 OpenROAD GPL test 子集

## OpenROAD 原测试入口

原 `CMakeLists.txt` 中登记的集成测试如下：

| 测试名 | 主要覆盖方向 | WinRoad 对照状态 |
| --- | --- | --- |
| `ar01` | skip initial place 的基础 global placement | 待移植 |
| `ar02` | 基础 global placement 变体 | 待移植 |
| `clust01` | cluster flops / cluster 入口 | 待移植 |
| `clust02` | cluster flops 变体 | 待移植 |
| `clust03` | cluster flops 变体 | 待移植 |
| `cluster_place01` | placement cluster 命令 | 待移植 |
| `convergence01` | 收敛行为、SDC/timing 输入 | 待移植 |
| `core01` | core 级基础 global placement | 待移植 |
| `density01` | density 参数与结果 | 待移植 |
| `diverge01` | divergence/revert 行为 | 待移植 |
| `error01` | 错误路径和参数校验 | 待移植 |
| `incremental01` | incremental global placement | 待移植 |
| `incremental02` | 大规模 incremental global placement | 待移植 |
| `nograd01` | no-gradient 或特殊梯度路径 | 待移植 |
| `simple01` | 基础 simple design global placement | 待移植 |
| `simple01-obs` | obstruction 场景 | 待移植 |
| `simple01-rd` | routability-driven 场景 | 待移植 |
| `simple01-ref` | reference/global placement 基准 | 待移植 |
| `simple01-skip-io` | skip IO 线长计算 | 待移植 |
| `simple01-td` | timing-driven 场景 | 待移植 |
| `simple01-td-tune` | timing-driven 参数调节 | 待移植 |
| `simple01-uniform` | uniform target density | 待移植 |
| `simple02` | simple design 变体 | 待移植 |
| `simple02-rd` | routability-driven 变体 | 待移植 |
| `simple03` | simple design 变体 | 待移植 |
| `simple03-rd` | routability-driven 变体 | 待移植 |
| `simple04` | simple design 变体 | 待移植 |
| `simple04-rd` | routability-driven 变体 | 待移植 |
| `simple05` | 小规模 DEF 场景 | 待移植 |
| `simple06` | 小规模 DEF 场景 | 待移植 |
| `simple07` | 小规模 DEF 场景 | 待移植 |
| `simple08` | 小规模 DEF 场景 | 待移植 |
| `simple09` | 小规模 DEF 场景 | 待移植 |
| `simple10` | 中等 simple 场景 | 待移植 |

被原 CMake 暂时跳过的检查：

| 测试名 | 说明 | WinRoad 对照状态 |
| --- | --- | --- |
| `gpl_man_tcl_check` | Tcl manpage / 命令文档检查 | 待移植 |
| `gpl_readme_msgs_check` | README 与消息检查 | 待移植 |

额外 GTest：

| 测试名 | 原文件 | 主要覆盖方向 | WinRoad 对照状态 |
| --- | --- | --- | --- |
| `fft_test` | `fft_test.cc` | `FFT::updateDensity()`、`FFT::doFFT()`、`getElectroForce()`、`getElectroPhi()` 数值黄金表 | 优先移植 |

## 测试资产分类

`OpenROAD/src/gpl/test` 中的资产类型：

- `.tcl`：OpenROAD Tcl 流程入口。
- `.py`：OpenROAD Python binding 流程入口。
- `.def`：测试输入版图。
- `.defok`：期望 DEF 输出。
- `.ok`：期望日志或报告输出。
- `.lef/.lib/.sdc`：测试所需工艺、库和时序约束。
- `gpl_aux.py`、`helpers.py`、`helpers.tcl`：OpenROAD 测试辅助脚本。
- 子目录如 `Nangate45`、`sky130hd`、`asap7`、`design`、`library`：测试依赖数据。

## 按源码责任区的测试要求

### `fft.cpp/.h`, `fftsg.cpp`, `fftsg2d.cpp`

必须移植并运行：

- `fft_test.cc` 对应的 Python 数值黄金测试。

最低断言：

- 4x4 输入密度表与原 GTest 一致。
- `electroForceX/electroForceY/electroPhi` 与原黄金表逐点比较。
- 比较容差必须明确记录；如果 Python 浮点与 C++ float 存在差异，容差不得掩盖算法错误。

### `initialPlace.cpp/.h`, `solver.cpp/.h`

必须对照：

- `simple01.py`
- `simple02.py`
- `simple05.py`
- `ar01.py`
- `core01.py`

最低断言：

- 初始布局入口执行路径与 OpenROAD 测试参数一致。
- B2B sparse matrix stamping 的矩阵维度、非零项、RHS、残差记录可检查。
- 当 DEF/LEF/OpenDB 尚未完全复刻时，测试必须标出缺失依赖，而不是伪造 DEF 输出。

### `nesterovBase.cpp/.h`, `nesterovPlace.cpp/.h`

必须对照：

- `simple01.py`
- `simple01-uniform.py`
- `density01.tcl`
- `convergence01.py`
- `diverge01.tcl`
- `nograd01.py`

最低断言：

- bin grid、density、overflow、wirelength coefficient、phi coefficient、snapshot/revert 状态可检查。
- Nesterov 主循环每轮关键指标可报告。
- 收敛和发散测试必须分别覆盖 stop 与 revert 路径。

### `routeBase.cpp/.h`

必须对照：

- `simple01-rd.tcl`
- `simple02-rd.tcl`
- `simple03-rd.tcl`
- `simple04-rd.tcl`
- `route01.tcl`
- `route02.tcl`

最低断言：

- RUDY tile demand/capacity/overflow 可复现。
- routability inflation 和 target RC 迭代记录可检查。
- FastRoute/GRT adapter 未接入时，测试必须显式标出缺失 adapter。

### `timingBase.cpp/.h`

必须对照：

- `simple01-td.py`
- `simple01-td-tune.py`
- `convergence01.py`
- `convergence01.sdc`

最低断言：

- timing-driven overflow checkpoint 触发顺序可检查。
- timing net weight max、timing net percentage、keep-resize-below-overflow 行为可检查。
- STA/resizer 未接入时，测试必须显式标出缺失 hook。

### `replace.cpp`, `Replace.h`, `replace.i`, `replace-py.i`, `replace.tcl`

必须对照：

- 所有 `global_placement` Tcl/Python 入口测试。
- `gpl_man_tcl_check.py`
- `gpl_readme_msgs_check.py`

最低断言：

- 所有 Tcl/Python 参数名、默认值、范围校验与 OpenROAD README/Replace.h 对齐。
- `get_global_placement_uniform_density` 对应行为要有单独测试。
- 错误信息和失败路径要能稳定检查。

### `mbff.cpp/.h`

必须对照：

- `clust01.tcl`
- `clust02.tcl`
- `clust03.tcl`
- `cluster_place01.tcl`
- 子目录 `SingleBit`、`TwoBitTray`、`2BitTrayH2`、`4BitTrayH2W2`、`4BitTrayH4`

最低断言：

- cluster 参数 `tray_weight`、`timing_weight`、`max_split_size`、`num_paths` 可检查。
- 不允许伪造 MBFF cluster 结果；没有 Liberty/STA/DB 支撑时，测试必须停在明确缺失边界。

## 当前执行命令模板

Windows PowerShell 下的基础检查：

```powershell
Set-Location D:\winroad_py
python -m py_compile (Get-ChildItem .\winroad\gpl -Recurse -Filter *.py | ForEach-Object { $_.FullName })
$env:PYTHONPATH='D:\winroad_py'; python -c "import winroad.gpl; from winroad.gpl import FFT; print('gpl import ok')"
git diff --check
```

后续新增 Python 测试后，统一使用：

```powershell
Set-Location D:\winroad_py
$env:PYTHONPATH='D:\winroad_py'
python -m pytest tests\gpl
```

如果本机暂时没有 `pytest`，优先用标准库 `unittest` 保留可运行测试入口：

```powershell
Set-Location D:\winroad_py
$env:PYTHONPATH='D:\winroad_py'
python -m unittest discover -s tests\gpl -p "test_*.py"
```

## 当前状态

- OpenROAD GPL test 目录已经登记到 WinRoad 项目文档。
- 已新增 `tests/gpl/test_fft.py`，作为 `fft_test.cc` 的 Python 对照测试。
- `fft_test.cc` 是第一批已可落地的数值测试，因为它不依赖完整 OpenDB/Tcl 流程，直接验证已经翻译的 `FFT` 数值核心。
- 其余集成测试需要随着 ODB/LEF/DEF/Tcl/STA/GRT 支撑逐步打开完整 golden diff。
