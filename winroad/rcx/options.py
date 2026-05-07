"""Public option dataclasses and internal option state for rcx."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, List, Optional

@dataclass
class BenchWiresOptions:
    """对应 OpenROAD `BenchWiresOptions`。"""

    block: str = "blk"
    over_dist: int = 100
    under_dist: int = 100
    met_cnt: int = 1000
    met: int = -1
    over_met: int = -1
    under_met: int = -1
    len: int = 200
    cnt: int = 5
    w: str = "1"
    s: str = "1"
    th: str = "1"
    d: str = "0.0"
    w_list: str = "1"
    s_list: str = "1 2 2.5 3 3.5 4 4.5 5 6 8 10 12"
    th_list: str = "0 1 2 2.5 3 3.5 4 4.5 5 6 8 10 12"
    grid_list: str = ""
    default_lef_rules: bool = False
    nondefault_lef_rules: bool = False
    dir: str = "./Bench"
    Over: bool = False
    db_only: bool = False
    v1: bool = False
    ddd: bool = False
    multiple_widths: bool = False
    diag: bool = False
    over_under: bool = False
    gen_def_patterns: bool = False
    resPatterns: bool = False


@dataclass
class ExtractOptions:
    """对应 OpenROAD `ExtractOptions`。"""

    debug_net: Optional[str] = None
    ext_model_file: Optional[str] = None
    net: Optional[str] = None
    cc_up: int = 2
    corner_cnt: int = 1
    max_res: float = 50.0
    no_merge_via_res: bool = False
    corner: int = -1
    coupling_threshold: float = 0.1
    context_depth: int = 5
    cc_model: int = 10
    signal_table: int = 3
    over_cell: bool = False
    skip_via_wires: bool = False
    lef_rc: bool = False
    lef_res: bool = False
    rlog: bool = False
    _v2: bool = False
    _version: float = 2.2
    _wire_extracted_progress_count: int = 50000
    _dbg: int = 0


@dataclass
class SpefOptions:
    """对应 OpenROAD `SpefOptions`。"""

    nets: Optional[str] = None
    net_id: int = 0
    ext_corner_name: Optional[str] = None
    corner: int = -1
    debug: int = 0
    parallel: bool = False
    init: bool = False
    end: bool = False
    use_ids: bool = False
    no_name_map: bool = False
    N: Optional[str] = None
    term_junction_xy: bool = False
    single_pi: bool = False
    file: Optional[str] = None
    gz: bool = False
    stop_after_map: bool = False
    w_clock: bool = False
    w_conn: bool = False
    w_cap: bool = False
    w_cc_cap: bool = False
    w_res: bool = False
    no_c_num: bool = False
    no_backslash: bool = False
    cap_units: str = "PF"
    res_units: str = "OHM"
    coordinates: bool = False


@dataclass
class ReadSpefOpts:
    """对应 OpenROAD `ReadSpefOpts`。"""

    file: Optional[str] = None
    net: Optional[str] = None
    force: bool = False
    use_ids: bool = False
    keep_loaded_corner: bool = False
    stamp_wire: bool = False
    test_parsing: int = 0
    N: Optional[str] = None
    r_conn: bool = False
    r_cap: bool = False
    r_cc_cap: bool = False
    r_res: bool = False
    cc_threshold: float = -0.5
    cc_ground_factor: float = 0.0
    app_print_limit: int = 0
    corner: int = -1
    db_corner_name: Optional[str] = None
    calibrate_base_corner: Optional[str] = None
    spef_corner: int = -1
    m_map: bool = False
    more_to_read: bool = False
    length_unit: float = 1.0
    fix_loop: int = 0
    no_cap_num_collapse: bool = False
    cap_node_map_file: Optional[str] = None
    log: bool = False


@dataclass
class DiffOptions:
    """对应 OpenROAD `DiffOptions`。"""

    net: Optional[str] = None
    use_ids: bool = False
    test_parsing: bool = False
    file: Optional[str] = None
    db_corner_name: Optional[str] = None
    spef_corner: int = -1
    exclude_net_subword: Optional[str] = None
    net_subword: Optional[str] = None
    rc_stats_file: Optional[str] = None
    r_conn: bool = False
    r_cap: bool = False
    r_cc_cap: bool = False
    r_res: bool = False
    ext_corner: int = -1
    low_guard: float = 1.0
    upper_guard: float = -1.0
    m_map: bool = False
    log: bool = False


@dataclass
class PatternOptions:
    """对应 OpenROAD `PatternOptions`。"""

    name: str = "blk"
    over_dist: int = 1000
    under_dist: int = 1000
    met_cnt: int = 1000
    met: int = -1
    over_met: int = -1
    under_met: int = -1
    width: Optional[str] = None
    spacing: Optional[str] = None
    couple_width: Optional[str] = None
    couple_spacing: Optional[str] = None
    far_width: str = "1"
    far_spacing: str = "1"
    over_width: Optional[str] = None
    over_spacing: Optional[str] = None
    over2_width: Optional[str] = None
    over2_spacing: Optional[str] = None
    under_width: Optional[str] = None
    under_spacing: Optional[str] = None
    under2_width: Optional[str] = None
    under2_spacing: Optional[str] = None
    dbg: int = 0
    wire_cnt: int = 0
    mlist: Optional[str] = None
    len: int = 0
    offset_over: Optional[str] = None
    offset_under: Optional[str] = None
    grid_list: str = ""
    default_lef_rules: bool = False
    nondefault_lef_rules: bool = False
    dir: str = "./Bench"
    over: bool = False
    ddd: bool = False
    diag: bool = False
    over_under: bool = False
    under: bool = False


@dataclass
class extMainOptions:
    """对应 `extMainOptions`，bench/model pattern 生成的内部选项。"""

    _overDist: int = 100
    _underDist: int = 100
    _met_cnt: int = 1000
    _met: int = -1
    _underMet: int = -1
    _overMet: int = -1
    _wireCnt: int = 5
    _topDir: Optional[str] = None
    _name: str = "blk"
    _wTable: str = "1"
    _sTable: str = "1"
    _thTable: str = "1"
    _dTable: str = "0.0"
    _listsFlag: bool = False
    _thListFlag: bool = False
    _wsListFlag: bool = False
    _default_lef_rules: bool = False
    _nondefault_lef_rules: bool = False
    _multiple_widths: bool = False
    _varFlag: bool = False
    _over: bool = False
    _overUnder: bool = False
    _diag: int = 0
    _db_only: bool = False
    _gen_def_patterns: bool = False
    _res_patterns: bool = False
    _tech: Any = None
    _block: Any = None
    _widthTable: List[float] = field(default_factory=list)
    _spaceTable: List[float] = field(default_factory=list)
    _densityTable: List[float] = field(default_factory=list)
    _thicknessTable: List[float] = field(default_factory=list)
    _gridTable: List[float] = field(default_factory=list)
    _ll: List[int] = field(default_factory=lambda: [0, 0])
    _ur: List[int] = field(default_factory=lambda: [0, 0])
    _len: int = 0
    _dist: int = 0
    _width: int = 0
    _dir: int = 0
    _rcModel: Optional["extRCModel"] = None
    _layerCnt: int = 0
    _v1: bool = False


