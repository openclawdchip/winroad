# GPL 全局布局模块 README 中文翻译

来源：`C:\Users\yh-PC-003\Desktop\codex\OpenROAD\src\gpl\README.md`

翻译日期：2026-05-08

用途：作为 WinRoad 复刻 OpenROAD `gpl` 模块时的中文参考资料。本文只翻译原 README 的功能、命令、参数和参考信息，不改变 WinRoad 当前实现状态。

## 全局布局

OpenROAD 中的全局布局模块 `gpl` 基于开源 RePlAce 工具，来源论文为 “Advancing Solution Quality and Routability Validation in Global Placement”。

功能特性：

- 解析式、非线性布局算法。使用 Nesterov 方法求解静电力方程。
- 已使用 OpenDB 在多种商业工艺和研究工艺上验证，包括 7/14/16/28/45/55/65nm。
- 已验证在多种编译器和操作系统下能够生成确定性结果。
- 支持混合尺寸布局模式。

原 README 中包含两个可视化示例：

- ISPD 2006 contest 的 `adaptec2.inf`。
- 真实设计 Coyote，工艺为 TSMC16 7.5T。

## 命令

说明：

- 方括号中的参数，例如 `[-param param]`，表示可选参数。
- 没有方括号的参数，例如 `-param2 param2`，表示必需参数。

## Global Placement

使用 `-timing_driven` 标志时，`gpl` 会执行一次虚拟的 `repair_design`，用于查找 slack，并对低 slack 的线网加权。它会对最差 slack 进行调整，调整范围由 `-timing_driven_nets_percentage` 修改，权重倍数由 `-timing_driven_net_weight_max` 修改。这个倍数会从最差 slack 处的完整值，逐渐缩放到 `timing_driven_nets_percentage` 所在位置的 1.0。需要使用 `set_wire_rc` 命令设置时序估计线长所用的电阻和电容。

Timing-driven 迭代由一组 overflow 阈值触发。每当布局执行到这些 overflow 值时，resizer 会被执行。这个过程可能消耗较多运行时间。重新计算权重所用的 overflow 值可以通过 `-timing_driven_net_reweight_overflow` 修改；例如，可以使用更少的 overflow 阈值来减少运行时间。

也可以为 `keep_resize_below_overflow` 设置一个 overflow 值。当 overflow 低于该值时，`rsz` 工具所做的修改会被保留，也就是执行非虚拟的 `repair_design`。

启用 routability-driven 选项时，每次迭代都会执行 RUDY 来估计布线拥塞。拥塞 tile 中逻辑单元的面积会被膨胀，以减少布线拥塞。迭代会通过比较每次迭代后的最终 RC，也就是 routing congestion，尝试达到目标 RC。如果 routability-driven 执行时间过长，可以考虑提高目标 RC 值 `-routability_target_rc_metric`，以放宽约束。最终 RC 值基于权重系数计算。如果 RC 连续三次迭代没有下降，算法会停止。

Routability-driven 参数：

- 参数以 `-routability` 开头。
- 包括 `-routability_target_rc_metric`、`-routability_check_overflow`、`-routability_max_density`、`-routability_max_inflation_iter`、`-routability_inflation_ratio_coef`、`-routability_max_inflation_ratio`、`-routability_rc_coefficients`。

Timing-driven 参数：

- 参数以 `-timing_driven` 开头。
- 包括 `-timing_driven_net_reweight_overflow`、`-timing_driven_net_weight_max`、`-timing_driven_nets_percentage`、`keep_resize_below_overflow`。

命令格式：

```tcl
global_placement
    [-timing_driven]
    [-routability_driven]
    [-disable_timing_driven]
    [-disable_routability_driven]
    [-skip_initial_place]
    [-incremental]
    [-bin_grid_count grid_count]
    [-density target_density]
    [-init_density_penalty init_density_penalty]
    [-init_wirelength_coef init_wirelength_coef]
    [-min_phi_coef min_phi_conef]
    [-max_phi_coef max_phi_coef]
    [-reference_hpwl reference_hpwl]
    [-overflow overflow]
    [-initial_place_max_iter initial_place_max_iter]
    [-initial_place_max_fanout initial_place_max_fanout]
    [-pad_left pad_left]
    [-pad_right pad_right]
    [-skip_io]
    [-skip_nesterov_place]
    [-routability_use_grt]
    [-routability_target_rc_metric routability_target_rc_metric]
    [-routability_check_overflow routability_check_overflow]
    [-routability_max_density routability_max_density]
    [-routability_max_inflation_iter routability_max_inflation_iter]
    [-routability_inflation_ratio_coef routability_inflation_ratio_coef]
    [-routability_max_inflation_ratio routability_max_inflation_ratio]
    [-routability_rc_coefficients routability_rc_coefficients]
    [-timing_driven_net_reweight_overflow]
    [-timing_driven_net_weight_max]
    [-timing_driven_nets_percentage]
    [-keep_resize_below_overflow]
    [-disable_revert_if_diverge]
    [-enable_routing_congestion]
```

### 选项

| 开关名 | 说明 |
| --- | --- |
| `-timing_driven` | 启用 timing-driven 模式。时序相关参数见 timing-driven 参数章节。 |
| `-routability_driven` | 启用 routability-driven 模式。可布线性相关参数见 routability-driven 参数章节。 |
| `-skip_initial_place` | 跳过 Nesterov 布局前的初始布局，也就是 BiCGSTAB 求解。初始布局在大设计上通常可以改善约 5% HPWL。等价于 `-initial_place_max_iter 0`。 |
| `-incremental` | 启用增量全局布局。用户需要基于已有布局结果调节其他参数，例如 `init_density_penalty`。 |
| `-bin_grid_count` | 设置 bin grid 数量。默认值由内部启发式算法决定。允许值为整数 `[64,128,256,512,...]`。 |
| `-density` | 设置目标密度。默认值为 `0.7`，即 70%。允许值为浮点数 `[0, 1]`。 |
| `-init_density_penalty` | 设置初始密度惩罚。默认值为 `8e-5`。允许值为浮点数 `[1e-6, 1e6]`。 |
| `-init_wirelength_coef` | 设置初始线长系数。默认值为 `0.25`。允许值为浮点数。 |
| `-min_phi_coef` | 设置 `pcof_min`，即 $\mu_k$ 下界。默认值为 `0.95`。允许值为浮点数 `[0.95, 1.05]`。 |
| `-max_phi_coef` | 设置 `pcof_max`，即 $\mu_k$ 上界。默认值为 `1.05`。允许值为浮点数 `[1.00, 1.20]`。 |
| `-overflow` | 设置终止条件使用的目标 overflow。默认值为 `0.1`。允许值为浮点数 `[0, 1]`。 |
| `-initial_place_max_iter` | 设置初始布局最大迭代次数。默认值为 20。允许值为整数 `[0, MAX_INT]`。 |
| `-initial_place_max_fanout` | 设置初始布局中的线网跳过条件，当 $fanout \geq initial\_place\_max\_fanout$ 时跳过。默认值为 200。允许值为整数 `[1, MAX_INT]`。 |
| `-pad_left` | 设置左侧 padding，单位为 site 数。默认值为 0，允许值为整数 `[1, MAX_INT]`。 |
| `-pad_right` | 设置右侧 padding，单位为 site 数。默认值为 0，允许值为整数 `[1, MAX_INT]`。 |
| `-skip_io` | 计算布局线长时忽略 IO port。默认值为 False，允许值为布尔值。 |
| `-disable_revert_if_diverge` | 使 `gpl` 在迭代中保存布局状态；如果检测到发散，则回退到快照状态。默认禁用。 |
| `-enable_routing_congestion` | 在全局布局后运行全局布线，以启用 Routing Congestion Heatmap。 |

### Routability-Driven 参数

| 开关名 | 说明 |
| --- | --- |
| `-routability_use_grt` | 使用该标志时，通过 `grt` 的 FastRoute 执行可布线性分析，拥塞结果更精确，但运行时间成本较高。默认 routability 模式使用更快的 RUDY。 |
| `-routability_target_rc_metric` | 设置 routability 模式的目标 RC metric。算法会尝试达到该 RC 值。默认值为 `1.01`，允许值为浮点数。 |
| `-routability_check_overflow` | 设置 routability 模式的 overflow 检查阈值。默认值为 `0.3`，允许值为浮点数 `[0, 1]`。 |
| `-routability_max_density` | 设置 routability 模式的密度阈值。默认值为 `0.99`，允许值为浮点数 `[0, 1]`。 |
| `-routability_max_inflation_iter` | 设置 routability 模式的 inflation 迭代阈值。默认值为 `4`，允许值为整数 `[1, MAX_INT]`。 |
| `-routability_inflation_ratio_coef` | 设置 routability 模式的 inflation ratio 系数。默认值为 `3`，允许值为浮点数。 |
| `-routability_max_inflation_ratio` | 设置 routability 模式的 inflation ratio 阈值，用于避免调整过于激进。默认值为 `6`，允许值为浮点数。 |
| `-routability_rc_coefficients` | 设置计算最终 RC 时使用的 routability RC 系数。它们对应最拥塞的 0.5%、1%、2%、5% tile。输入形式为 Tcl list `{k1, k2, k3, k4}`。各系数默认值分别为 `{1.0, 1.0, 0.0, 0.0}`，允许值为浮点数。 |

### Timing-Driven 参数

| 开关名 | 说明 |
| --- | --- |
| `-timing_driven_net_reweight_overflow` | 设置 timing-driven 线网重加权的 overflow 阈值。允许值为 Tcl list，其中每个整数范围为 `[0, 100]`。默认值为 `[79, 64, 49, 29, 21, 15]`。 |
| `-timing_driven_net_weight_max` | 设置最关键时序线网的最大权重倍数。默认值为 `5`，允许值为浮点数。 |
| `-timing_driven_nets_percentage` | 设置 timing-driven 模式下被重加权的线网百分比。默认值为 10。允许值为浮点数 `[0, 100]`。 |
| `-keep_resize_below_overflow` | 当 overflow 低于设定值时，timing-driven 迭代会保留 resizer 的修改，而不是回滚。默认值为 0.3。允许值为浮点数 `[0, 1]`。 |

## Cluster Flops

该命令根据参数执行 flop 聚类。

```tcl
cluster_flops
    [-tray_weight tray_weight]\
    [-timing_weight timing_weight]\
    [-max_split_size max_split_size]\
    [-num_paths num_paths]
```

选项：

| 开关名 | 说明 |
| --- | --- |
| `-tray_weight` | tray 权重，默认值为 32.0，类型为 `float`。 |
| `-timing_weight` | timing 权重，默认值为 0.1，类型为 `float`。 |
| `-max_split_size` | 最大拆分尺寸，默认值为 500，`-1` 表示不分解，类型为 `int`。 |
| `-num_paths` | KIV，默认值为 0，类型为 `int`。 |

## Placement Clusters

该命令定义应作为单个 cluster 进行布局的实例。它主要用于小规模门级 cluster。

```tcl
placement_cluster
    instance_patterns
```

## Debug Mode

`global_placement_debug` 命令会启动 debug 模式，在版图上实时可视化算法进展。应在执行 `global_placement` 前使用该命令，例如在 ORFS 的 `flow/scripts/global_place.tcl` 脚本中使用。

```tcl
global_placement_debug
    [-pause]
    [-update]
    [-inst]
    [-draw_bins]
    [-initial]
    [-start_iter]
    [-generate_images]
```

选项：

| 开关名 | 说明 |
| --- | --- |
| `-pause` | debug 期间每隔多少次迭代暂停一次，用于可视化当前状态。适合仔细观察布局算法进展。允许值为整数，默认值为 10。 |
| `-update` | 定义工具刷新版图输出的频率，单位为迭代次数，用于显示最新状态。允许值为整数，默认值为 10。 |
| `-inst` | 指定一个实例名作为 debug 关注目标。允许值为字符串；默认行为是不聚焦任何特定实例。 |
| `-draw_bins` | 启用 placement bin 可视化，显示 bin 密度和作用在 bin 上的力。密度用白色深浅表示，力方向用红色表示。默认禁用。 |
| `-initial` | 在初始布局阶段暂停 debug 流程。默认禁用。 |
| `-start_iter` | 从指定迭代开始 debug 模式。 |
| `-generate_images` | 生成显示布局进展的 GIF 动画；并在每次 routability 和 timing-driven 迭代结束时生成快照图片，包括 heatmap。 |

示例：

```tcl
global_placement_debug -pause 100 -update 1 -initial -draw_bins -inst _614_
```

该命令配置 debugger 每 100 次迭代暂停一次，版图每次迭代都更新；同时启用初始布局阶段可视化、bin 绘制，并特别高亮实例 `_614_`。

Debug 模式需要 GUI。在 ORFS 中，一种在全局布局步骤显示 GUI 的方式是运行 `make global_place_issue`，然后编辑生成的 `run-me.sh` 文件，在调用 OpenROAD 时加入 `-gui` 标志。

## 对开发者有用的命令

开发者可能会用到以下命令。更多细节可以查看原源码 `src/replace.cpp` 或 SWIG 文件 `src/replace.i`。

```tcl
# adds padding and gets global placement uniform target density
get_global_placement_uniform_density -pad_left -pad_right
```

在 `core01` 示例设计上运行 `gpl` 的示例脚本如下：

```shell
./test/core01.tcl
```

## 回归测试

`./test` 中包含一组回归测试。更多信息可查看 OpenROAD 根 README 中的 regression tests 章节。

运行方式：

```shell
./test/regression
```

## 限制

原 README 此章节未列出具体内容。

## 使用 gpl 的 Python 接口

该 API 尽量贴近 C++ 类 `Replace` 中定义的 API。该类位于 `include/gpl/Replace.h`。

初始化设计时，一组 Python 命令可能如下：

```python
from openroad import Design, Tech
tech = Tech()
tech.readLef(...)
design = Design(tech)
design.readDef(...)
gpl = design.getReplace()
```

下面是给全局布局器设置部分选项或配置的示例。完整列表应查看 `include/gpl/Replace.h`。

```python
gpl.setInitialPlaceMaxIter(iter)
gpl.setSkipIoMode(skip_io)
gpl.setTimingDrivenMode(timing_driven)
gpl.setTimingNetWeightMax(weight)
```

`test/grt_aux.py` 中有一些有用的 Python 函数，但这些函数不被视为最终 API 的一部分，未来可能变化。

## FAQ

关于该工具，可以查看 OpenROAD GitHub discussion 中 Q&A 分类下标题包含 `replace` 的讨论。

## 参考文献

- C.-K. Cheng, A. B. Kahng, I. Kang and L. Wang, “RePlAce: Advancing Solution Quality and Routability Validation in Global Placement”, IEEE Transactions on Computer-Aided Design of Integrated Circuits and Systems, 38(9) (2019), pp. 1717-1730.
- J. Lu, P. Chen, C.-C. Chang, L. Sha, D. J.-H. Huang, C.-C. Teng and C.-K. Cheng, “ePlace: Electrostatics based Placement using Fast Fourier Transform and Nesterov's Method”, ACM TODAES 20(2) (2015), article 17.
- J. Lu, H. Zhuang, P. Chen, H. Chang, C.-C. Chang, Y.-C. Wong, L. Sha, D. J.-H. Huang, Y. Luo, C.-C. Teng and C.-K. Cheng, “ePlace-MS: Electrostatics based Placement for Mixed-Size Circuits”, IEEE TCAD 34(5) (2015), pp. 685-698.
- A. B. Kahng, J. Li and L. Wang, “Improved Flop Tray-Based Design Implementation for Power Reduction”, IEEE/ACM ICCAD, 2016, pp. 20:1-20:8.
- A. B. Kahng, S. Kundu, S. Thumathy, “Scalable Flip-Flop Clustering Using Divide and Conquer For Capacitated K-Means”, ACM GLSVLSI, 2024, pp. 177-184.
- Timing-driven 模式由 Mingyu Woo 实现，原 README 注明只在 legacy repo 的 standalone branch 中可用。
- Routability-driven 模式由 Mingyu Woo 实现。
- 当前 clean-code 结构中的 timing-driven 模式重实现仍在进行中。
- RUDY: Spindler, Peter, and Frank M. Johannes. “Fast and accurate routing demand estimation for efficient routability-driven placement. In 2007 Design, Automation & Test in Europe Conference & Exhibition.” (2007): 1-6.

## 作者

- 2020 年 1 月以来的作者/维护者：Mingyu Woo，博士导师为 Andrew B. Kahng。
- RePlAce 最初开源于 2018 年 8 月，作者包括 Ilgweon Kang，博士导师 Chung-Kuan Cheng；Lutong Wang，博士导师 Andrew B. Kahng；以及 Mingyu Woo，博士导师 Andrew B. Kahng。
- 同时感谢 Dr. Jingwei Lu 开源此前的 ePlace-MS/ePlace 项目代码。

## 许可证

BSD 3-Clause License。详见 OpenROAD 的 `LICENSE` 文件。
