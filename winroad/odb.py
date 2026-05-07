"""OpenDB 核心对象的 Python 复刻骨架。

这里先把 OpenROAD / OpenDB 最核心的对象树翻成 Python：
dbDatabase -> dbChip -> dbBlock -> dbNet / dbInst

说明：
1. 这里不是 demo 口径，而是按 OpenDB 的对象边界建立等价的数据模型。
2. 字段命名尽量贴近 C++ 源码，方便后续继续逐文件对照翻译。
3. 先把对象、关系和基础操作夯实，再逐步补更多 OpenDB 细类。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


class SigType(str, Enum):
    """对应 OpenDB 的 dbSigType::Value。"""

    SIGNAL = "signal"
    POWER = "power"
    GROUND = "ground"
    CLOCK = "clock"
    ANALOG = "analog"
    OTHER = "other"


class IoType(str, Enum):
    """对应 OpenDB 的 dbIoType::Value。"""

    INPUT = "input"
    OUTPUT = "output"
    INOUT = "inout"
    FEEDTHRU = "feedthru"
    UNKNOWN = "unknown"


class WireType(str, Enum):
    """对应 OpenDB 的 dbWireType::Value。"""

    SIGNAL = "signal"
    SPECIAL = "special"
    NONE = "none"


class SourceType(str, Enum):
    """对应 OpenDB 的 dbSourceType::Value。"""

    NETLIST = "netlist"
    TEST = "test"
    USER = "user"
    TIMING = "timing"
    ROUTING = "routing"
    OTHER = "other"


class OrientType(str, Enum):
    """对应 OpenDB 的 dbOrientType::Value。"""

    N = "N"
    S = "S"
    E = "E"
    W = "W"
    FN = "FN"
    FS = "FS"
    FE = "FE"
    FW = "FW"


class PlacementStatus(str, Enum):
    """对应 OpenDB 的 dbPlacementStatus::Value。"""

    NONE = "none"
    UNPLACED = "unplaced"
    PLACED = "placed"
    FIXED = "fixed"
    COVER = "cover"
    LOCKED = "locked"


class RowDir(str, Enum):
    """对应 OpenDB 的 dbRowDir::Value。"""

    HORIZONTAL = "horizontal"
    VERTICAL = "vertical"


class PropertyType(str, Enum):
    """对应 OpenDB 的 PropTypeEnum。"""

    STRING = "string"
    BOOL = "bool"
    INT = "int"
    DOUBLE = "double"


@dataclass
class DbNet:
    """复刻 _dbNet 的 Python 版本。

    这里只保留 OpenDB 核心语义字段：
    - 名称
    - 线网类型
    - 来源
    - iterm/bterm/guide/group 关系
    - 线网权重、xtalk、cc 相关参数
    """

    name: str
    sig_type: SigType = SigType.SIGNAL
    wire_type: WireType = WireType.SIGNAL
    source: SourceType = SourceType.NETLIST
    special: bool = False
    wild_connect: bool = False
    wire_ordered: bool = False
    disconnected: bool = False
    spef: bool = False
    select: bool = False
    mark: bool = False
    extracted: bool = False
    rc_graph: bool = False
    set_io: bool = False
    io: bool = False
    dont_touch: bool = False
    fixed_bump: bool = False
    rc_disconnected: bool = False
    block_rule: bool = False
    has_jumpers: bool = False
    non_default_rule: Optional[str] = None
    iterms: List[str] = field(default_factory=list)
    bterms: List[str] = field(default_factory=list)
    groups: List[str] = field(default_factory=list)
    guides: List[str] = field(default_factory=list)
    tracks: List[str] = field(default_factory=list)
    weight: int = 0
    xtalk: int = 0
    cc_adjust_factor: float = 1.0
    cc_adjust_order: int = 0
    driving_iterm: int = -1


@dataclass
class DbInst:
    """复刻 _dbInst 的 Python 版本。"""

    name: str
    orient: OrientType = OrientType.N
    status: PlacementStatus = PlacementStatus.UNPLACED
    x: int = 0
    y: int = 0
    weight: int = 0
    physical_only: bool = False
    dont_touch: bool = False
    source: SourceType = SourceType.NETLIST
    eco_create: bool = False
    eco_destroy: bool = False
    eco_modify: bool = False
    level: int = 0
    inst_hdr: Optional[str] = None
    bbox: Optional[tuple[int, int, int, int]] = None
    region: Optional[str] = None
    module: Optional[str] = None
    group: Optional[str] = None
    hierarchy: Optional[str] = None
    iterms: List[str] = field(default_factory=list)
    halo: Optional[tuple[int, int, int, int]] = None
    pin_access_idx: int = 0

    def set_origin(self, x: int, y: int) -> None:
        """对应 OpenDB 里实例原点设置的行为。"""

        self.x = x
        self.y = y


@dataclass
class DbBox:
    """复刻 _dbBox 的 Python 版本。

    OpenDB 里的 box 既可能是普通矩形，也可能是 octilinear 形状，
    这里先用通用形状字段保存。
    """

    owner_type: str = "unknown"
    is_tech_via: bool = False
    is_block_via: bool = False
    visited: bool = False
    octilinear: bool = False
    layer_id: int = 0
    via_id: int = 0
    layer_mask: int = 0
    rect: Optional[tuple[int, int, int, int]] = None
    oct: Optional[list[tuple[int, int]]] = None
    owner: int = 0
    next_box: int = 0
    design_rule_width: int = -1

    def is_oct(self) -> bool:
        """判断当前 box 是否为 octilinear。"""

        return self.octilinear

    def get_type(self) -> str:
        """对应 OpenDB 的 getType()。"""

        if self.is_tech_via:
            return "tech_via"
        if self.is_block_via:
            return "block_via"
        return "box"


@dataclass
class DbMaster:
    """复刻 _dbMaster 的 Python 版本。"""

    name: str
    master_id: int = 0
    x: int = 0
    y: int = 0
    width: int = 0
    height: int = 0
    type: str = "core"
    frozen: bool = False
    x_symmetry: bool = False
    y_symmetry: bool = False
    r90_symmetry: bool = False
    mark: bool = False
    sequential: bool = False
    special_power: bool = False
    site: Optional[str] = None
    lib_for_site: Optional[str] = None
    next_entry: Optional[str] = None
    leq: Optional[str] = None
    eeq: Optional[str] = None
    obstructions: List[DbBox] = field(default_factory=list)
    poly_obstructions: List[list[tuple[int, int]]] = field(default_factory=list)
    mterms: List[str] = field(default_factory=list)
    mpins: List[str] = field(default_factory=list)


@dataclass
class DbLib:
    """复刻 _dbLib 的 Python 版本。"""

    name: str
    lef_units: int = 0
    dbu_per_micron: int = 0
    hier_delimiter: str = "/"
    left_bus_delimiter: str = "["
    right_bus_delimiter: str = "]"
    tech: Optional[str] = None
    masters: Dict[str, DbMaster] = field(default_factory=dict)
    sites: Dict[str, str] = field(default_factory=dict)

    def add_master(self, master: DbMaster) -> DbMaster:
        """添加 master。"""

        self.masters[master.name] = master
        return master


@dataclass
class DbTech:
    """复刻 _dbTech 的 Python 版本。"""

    name: str = ""
    version: float = 0.0
    via_cnt: int = 0
    layer_cnt: int = 0
    rlayer_cnt: int = 0
    lef_units: int = 0
    dbu_per_micron: int = 0
    mfgrid: int = 0
    namecase: bool = False
    haswireext: bool = False
    nowireext: bool = False
    hasclmeas: bool = False
    clmeas: str = "unknown"
    hasminspobs: bool = False
    minspobs: bool = False
    hasminsppin: bool = False
    minsppin: bool = False
    bottom_layer: Optional[str] = None
    top_layer: Optional[str] = None
    non_default_rules: List[str] = field(default_factory=list)
    samenet_rules: List[str] = field(default_factory=list)
    via_hash: Dict[str, str] = field(default_factory=dict)
    layers: Dict[str, dict] = field(default_factory=dict)
    vias: Dict[str, dict] = field(default_factory=dict)

    def add_layer(self, name: str, data: Optional[dict] = None) -> dict:
        """添加工艺层。"""

        layer = data or {}
        self.layers[name] = layer
        return layer

    def add_via(self, name: str, data: Optional[dict] = None) -> dict:
        """添加工艺 via。"""

        via = data or {}
        self.vias[name] = via
        return via


@dataclass
class DbTechLayer:
    """复刻 _dbTechLayer 的 Python 版本。"""

    name: str
    type: str = "routing"
    direction: str = "none"
    minstep_type: str = "none"
    has_max_width: bool = False
    has_thickness: bool = False
    has_area: bool = False
    has_protrusion: bool = False
    has_alias: bool = False
    has_xy_pitch: bool = False
    has_xy_offset: bool = False
    rect_only: bool = False
    right_way_on_grid_only: bool = False
    right_way_on_grid_only_check_mask: bool = False
    rect_only_except_non_core_pins: bool = False
    lef58_type: int = 0
    wrong_way_width: int = 0
    layer_adjustment: float = 0.0
    orth_spacing_tbl: List[tuple[int, int]] = field(default_factory=list)
    pitch_x: int = 0
    pitch_y: int = 0
    offset_x: int = 0
    offset_y: int = 0
    width: int = 0
    spacing: int = 0
    resistance: float = 0.0
    capacitance: float = 0.0
    edge_capacitance: float = 0.0
    wire_extension: int = 0
    number: int = 0
    rlevel: int = 0
    area: float = 0.0
    thickness: int = 0
    max_width: int = 0
    min_width: int = 0
    min_step: int = 0
    min_step_max_length: int = 0
    min_step_max_edges: int = 0
    first_last_pitch: int = 0
    upper: Optional[str] = None
    lower: Optional[str] = None
    spacing_rules: List[dict] = field(default_factory=list)
    min_cut_rules: List[dict] = field(default_factory=list)
    min_enc_rules: List[dict] = field(default_factory=list)
    antenna_rules: List[dict] = field(default_factory=list)
    v55sp_length_idx: List[int] = field(default_factory=list)
    v55sp_width_idx: List[int] = field(default_factory=list)
    v55sp_spacing: List[List[int]] = field(default_factory=list)
    two_widths_sp_idx: List[int] = field(default_factory=list)
    two_widths_sp_prl: List[int] = field(default_factory=list)
    two_widths_sp_spacing: List[List[int]] = field(default_factory=list)
    oxide1: Optional[str] = None
    oxide2: Optional[str] = None


@dataclass
class DbWire:
    """复刻 _dbWire 的 Python 版本。"""

    is_global: bool = False
    data: List[int] = field(default_factory=list)
    opcodes: List[int] = field(default_factory=list)
    net: Optional[str] = None

    def length(self) -> int:
        """对应 OpenDB 的 length()。"""

        return len(self.opcodes)


@dataclass
class DbVia:
    """复刻 _dbVia 的 Python 版本。"""

    name: str
    pattern: Optional[str] = None
    is_rotated: bool = False
    is_tech_via: bool = False
    has_params: bool = False
    orient: OrientType = OrientType.N
    default: bool = False
    bbox: Optional[str] = None
    boxes: Optional[str] = None
    top: Optional[str] = None
    bottom: Optional[str] = None
    generate_rule: Optional[str] = None
    rotated_via_id: int = 0
    via_params: dict = field(default_factory=dict)


@dataclass
class DbMTerm:
    """复刻 _dbMTerm 的 Python 版本。"""

    name: str
    order_id: int = 0
    io_type: str = "input"
    sig_type: str = "signal"
    shape_type: str = "none"
    mark: bool = False
    pins: List[str] = field(default_factory=list)
    targets: List[str] = field(default_factory=list)
    oxide1: Optional[str] = None
    oxide2: Optional[str] = None
    par_met_area: List[object] = field(default_factory=list)
    par_met_sidearea: List[object] = field(default_factory=list)
    par_cut_area: List[object] = field(default_factory=list)
    diffarea: List[object] = field(default_factory=list)


@dataclass
class DbITerm:
    """复刻 _dbITerm 的 Python 版本。"""

    mterm_idx: int = 0
    ext_id: int = 0
    clocked: bool = False
    mark: bool = False
    spef: bool = False
    special: bool = False
    connected: bool = False
    net: Optional[str] = None
    mnet: Optional[str] = None
    inst: Optional[str] = None
    next_net_iterm: Optional[str] = None
    prev_net_iterm: Optional[str] = None
    next_modnet_iterm: Optional[str] = None
    prev_modnet_iterm: Optional[str] = None
    sta_vertex_id: int = 0
    aps: Dict[str, str] = field(default_factory=dict)

    def get_mterm(self) -> Optional[str]:
        """返回关联的 mterm 名称占位。"""

        return None

    def get_inst(self) -> Optional[str]:
        """返回关联的 inst 名称占位。"""

        return self.inst


@dataclass
class DbProperty:
    """复刻 _dbProperty 的 Python 版本。

    OpenDB 里 property 是挂到任意 dbObject 上的名字和值，值类型由
    PropTypeEnum 标识。这里用 owner_type/owner 保存归属对象边界。
    """

    name: str
    value: str | bool | int | float = ""
    type: PropertyType = PropertyType.STRING
    owner_type: str = "unknown"
    owner: Optional[str] = None
    next: Optional[str] = None

    def set_value(self, value: str | bool | int | float) -> None:
        """设置属性值，并按 Python 值推断 OpenDB property 类型。"""

        self.value = value
        if isinstance(value, bool):
            self.type = PropertyType.BOOL
        elif isinstance(value, int):
            self.type = PropertyType.INT
        elif isinstance(value, float):
            self.type = PropertyType.DOUBLE
        else:
            self.type = PropertyType.STRING

    def get_value(self) -> str | bool | int | float:
        """返回 property 保存的 variant 值。"""

        return self.value


@dataclass
class DbRow:
    """复刻 _dbRow 的 Python 版本。

    Row 是 floorplan site 阵列的基础对象，保存 site、原点、方向、
    site 数量和间距。
    """

    name: str
    orient: OrientType = OrientType.N
    direction: RowDir = RowDir.HORIZONTAL
    lib: Optional[str] = None
    site: Optional[str] = None
    x: int = 0
    y: int = 0
    site_cnt: int = 0
    spacing: int = 0

    def get_origin(self) -> tuple[int, int]:
        """返回 row 原点。"""

        return (self.x, self.y)

    def get_site_count(self) -> int:
        """返回 row 中 site 个数。"""

        return self.site_cnt


@dataclass
class DbBPin:
    """复刻 _dbBPin 的 Python 版本。

    BPin 是 block terminal 的物理 pin 形状集合，主要连接到 bterm，
    持有 box 链、access point 列表和 DEF 5.6 的 spacing/width 扩展。
    """

    name: str
    bterm: Optional[str] = None
    status: PlacementStatus = PlacementStatus.NONE
    boxes: List[DbBox] = field(default_factory=list)
    next_bpin: Optional[str] = None
    has_min_spacing: bool = False
    has_effective_width: bool = False
    min_spacing: int = 0
    effective_width: int = 0
    aps: List[str] = field(default_factory=list)

    def add_box(self, box: DbBox) -> DbBox:
        """把一个 dbBox 挂到该 bpin。"""

        box.owner_type = "bpin"
        box.owner = self.name
        self.boxes.append(box)
        return box

    def set_placement_status(self, status: PlacementStatus) -> None:
        """对应 dbBPin::setPlacementStatus()。"""

        self.status = status

    def set_min_spacing(self, width: int) -> None:
        """对应 dbBPin::setMinSpacing()。"""

        self.has_min_spacing = True
        self.min_spacing = width

    def set_effective_width(self, width: int) -> None:
        """对应 dbBPin::setEffectiveWidth()。"""

        self.has_effective_width = True
        self.effective_width = width

    def get_bterm(self) -> Optional[str]:
        """返回所属 bterm 名称占位。"""

        return self.bterm

    def get_boxes(self) -> List[DbBox]:
        """返回 pin 的 box 列表。"""

        return self.boxes


@dataclass
class DbBTerm:
    """复刻 _dbBTerm 的 Python 版本。

    BTerm 是 block 端口对象，保存 io/sig 类型、net/modnet 链接、bpin 链、
    层级父对象以及镜像/约束区域等 OpenDB 字段。
    """

    name: str
    io_type: IoType = IoType.UNKNOWN
    sig_type: SigType = SigType.SIGNAL
    ext_id: int = 0
    spef: bool = False
    special: bool = False
    mark: bool = False
    net: Optional[str] = None
    mnet: Optional[str] = None
    next_entry: Optional[str] = None
    next_bterm: Optional[str] = None
    prev_bterm: Optional[str] = None
    next_modnet_bterm: Optional[str] = None
    prev_modnet_bterm: Optional[str] = None
    parent_block: Optional[str] = None
    parent_iterm: Optional[str] = None
    bpins: List[str] = field(default_factory=list)
    ground_pin: Optional[str] = None
    supply_pin: Optional[str] = None
    sta_vertex_id: int = 0
    constraint_region: Optional[tuple[int, int, int, int]] = None
    mirrored_bterm: Optional[str] = None
    is_mirrored: bool = False
    chip_region: Optional[str] = None
    chip_bump: Optional[str] = None

    def connect(self, net: Optional[str]) -> None:
        """把 bterm 接到 flat net；传 None 时保持空连接。"""

        if net is None:
            return
        self.net = net

    def disconnect(self) -> None:
        """断开 flat net/modnet 连接。"""

        self.net = None
        self.mnet = None
        self.next_bterm = None
        self.prev_bterm = None
        self.next_modnet_bterm = None
        self.prev_modnet_bterm = None

    def connect_modnet(self, modnet: Optional[str]) -> None:
        """把 bterm 接到 module net。"""

        if modnet is not None:
            self.mnet = modnet

    def add_bpin(self, bpin: DbBPin) -> DbBPin:
        """挂接一个 bpin 到该 bterm。"""

        bpin.bterm = self.name
        if bpin.name not in self.bpins:
            self.bpins.append(bpin.name)
        return bpin

    def set_io_type(self, io_type: IoType) -> None:
        """对应 dbBTerm::setIoType()。"""

        self.io_type = io_type

    def set_sig_type(self, sig_type: SigType) -> None:
        """对应 dbBTerm::setSigType()。"""

        self.sig_type = sig_type

    def set_mirrored_constraint_region(
        self, region: tuple[int, int, int, int], mirrored_bterm: Optional[str] = None
    ) -> None:
        """保存 mirrored bterm 约束区域。"""

        self.constraint_region = region
        self.mirrored_bterm = mirrored_bterm
        self.is_mirrored = mirrored_bterm is not None


@dataclass
class DbGuide:
    """复刻 _dbGuide 的 Python 版本。

    Guide 是 global routing guide，挂到 net，保存矩形、routing layer、
    optional via layer 和拥塞/跳线/端口连接标志。
    """

    name: str
    net: Optional[str] = None
    box: Optional[tuple[int, int, int, int]] = None
    layer: Optional[str] = None
    via_layer: Optional[str] = None
    guide_next: Optional[str] = None
    is_congested: bool = False
    is_jumper: bool = False
    is_connect_to_term: bool = False

    def set_box(self, box: tuple[int, int, int, int]) -> None:
        """设置 guide 矩形。"""

        self.box = box


@dataclass
class DbGroup:
    """复刻 _dbGroup 的 Python 版本。

    Group 保存实例/子 group 关系、region 链接以及 power/ground net 列表。
    """

    name: str
    type: str = "physical_cluster"
    next_entry: Optional[str] = None
    group_next: Optional[str] = None
    parent_group: Optional[str] = None
    insts: List[str] = field(default_factory=list)
    modinsts: List[str] = field(default_factory=list)
    groups: List[str] = field(default_factory=list)
    power_nets: List[str] = field(default_factory=list)
    ground_nets: List[str] = field(default_factory=list)
    region_next: Optional[str] = None
    region_prev: Optional[str] = None
    region: Optional[str] = None

    def add_inst(self, inst_name: str) -> None:
        """把 inst 挂到 group。"""

        if inst_name not in self.insts:
            self.insts.append(inst_name)

    def add_group(self, group_name: str) -> None:
        """把子 group 挂到 group。"""

        if group_name not in self.groups:
            self.groups.append(group_name)

    def add_power_net(self, net_name: str) -> None:
        """添加 power net。"""

        if net_name not in self.power_nets:
            self.power_nets.append(net_name)

    def add_ground_net(self, net_name: str) -> None:
        """添加 ground net。"""

        if net_name not in self.ground_nets:
            self.ground_nets.append(net_name)


@dataclass
class DbBlock:
    """复刻 _dbBlock 的 Python 版本。

    这里先把 block 的对象关系建起来：
    - tech / chip / parent
    - net / inst / module / bterm 容器
    - die area / bbox / 层范围 / 约束信息
    """

    name: str
    delimiter: str = "/"
    hier_delimiter: str = "/"
    left_bus_delimiter: str = "["
    right_bus_delimiter: str = "]"
    def_units: int = 1000
    dbu_per_micron: int = 1000
    die_area: Optional[tuple[int, int, int, int]] = None
    bbox: Optional[tuple[int, int, int, int]] = None
    tech: Optional[str] = None
    chip: Optional[str] = None
    parent: Optional[str] = None
    parent_block: Optional[str] = None
    parent_inst: Optional[str] = None
    top_module: Optional[str] = None
    min_routing_layer: int = 0
    max_routing_layer: int = 0
    min_layer_for_clock: int = 0
    max_layer_for_clock: int = 0
    nets: Dict[str, DbNet] = field(default_factory=dict)
    insts: Dict[str, DbInst] = field(default_factory=dict)
    rows: Dict[str, DbRow] = field(default_factory=dict)
    bterms: Dict[str, DbBTerm] = field(default_factory=dict)
    bpins: Dict[str, DbBPin] = field(default_factory=dict)
    guides: Dict[str, DbGuide] = field(default_factory=dict)
    groups: Dict[str, DbGroup] = field(default_factory=dict)
    properties: Dict[str, DbProperty] = field(default_factory=dict)
    blocked_regions_for_pins: List[tuple[int, int, int, int]] = field(default_factory=list)
    children: List[str] = field(default_factory=list)

    def add_net(self, net: DbNet) -> DbNet:
        """添加线网，名字作为唯一键。"""

        self.nets[net.name] = net
        return net

    def add_inst(self, inst: DbInst) -> DbInst:
        """添加实例，名字作为唯一键。"""

        self.insts[inst.name] = inst
        return inst

    def add_row(self, row: DbRow) -> DbRow:
        """添加 floorplan row。"""

        self.rows[row.name] = row
        return row

    def add_bterm(self, bterm: DbBTerm) -> DbBTerm:
        """添加 block terminal，并同步到 net 的 bterm 列表。"""

        bterm.parent_block = self.name
        self.bterms[bterm.name] = bterm
        if bterm.net and bterm.net in self.nets:
            net_bterms = self.nets[bterm.net].bterms
            if bterm.name not in net_bterms:
                net_bterms.append(bterm.name)
        return bterm

    def add_bpin(self, bpin: DbBPin) -> DbBPin:
        """添加 block pin，并同步到所属 bterm。"""

        self.bpins[bpin.name] = bpin
        if bpin.bterm and bpin.bterm in self.bterms:
            self.bterms[bpin.bterm].add_bpin(bpin)
        return bpin

    def add_guide(self, guide: DbGuide) -> DbGuide:
        """添加 global routing guide，并同步到 net 的 guide 列表。"""

        self.guides[guide.name] = guide
        if guide.net and guide.net in self.nets:
            net_guides = self.nets[guide.net].guides
            if guide.name not in net_guides:
                net_guides.append(guide.name)
        return guide

    def add_group(self, group: DbGroup) -> DbGroup:
        """添加 group，并同步 parent group/inst 的轻量关系。"""

        self.groups[group.name] = group
        if group.parent_group and group.parent_group in self.groups:
            self.groups[group.parent_group].add_group(group.name)
        for inst_name in group.insts:
            if inst_name in self.insts:
                self.insts[inst_name].group = group.name
        for net_name in group.power_nets + group.ground_nets:
            if net_name in self.nets and group.name not in self.nets[net_name].groups:
                self.nets[net_name].groups.append(group.name)
        return group

    def add_property(self, prop: DbProperty) -> DbProperty:
        """添加 block 作用域 property。"""

        self.properties[prop.name] = prop
        return prop

    def create_row(
        self,
        name: str,
        site: Optional[str] = None,
        x: int = 0,
        y: int = 0,
        orient: OrientType = OrientType.N,
        direction: RowDir = RowDir.HORIZONTAL,
        site_cnt: int = 0,
        spacing: int = 0,
    ) -> DbRow:
        """创建 row 并挂到 block。"""

        row = DbRow(
            name=name,
            site=site,
            x=x,
            y=y,
            orient=orient,
            direction=direction,
            site_cnt=site_cnt,
            spacing=spacing,
        )
        return self.add_row(row)

    def create_bterm(
        self,
        name: str,
        net: Optional[str] = None,
        io_type: IoType = IoType.UNKNOWN,
        sig_type: SigType = SigType.SIGNAL,
    ) -> DbBTerm:
        """创建 bterm 并挂到 block。"""

        bterm = DbBTerm(name=name, net=net, io_type=io_type, sig_type=sig_type)
        return self.add_bterm(bterm)

    def create_bpin(
        self, name: str, bterm: Optional[str] = None, status: PlacementStatus = PlacementStatus.NONE
    ) -> DbBPin:
        """创建 bpin 并挂到 block。"""

        bpin = DbBPin(name=name, bterm=bterm, status=status)
        return self.add_bpin(bpin)

    def create_guide(
        self,
        name: str,
        net: Optional[str] = None,
        box: Optional[tuple[int, int, int, int]] = None,
        layer: Optional[str] = None,
        via_layer: Optional[str] = None,
    ) -> DbGuide:
        """创建 guide 并挂到 block。"""

        guide = DbGuide(name=name, net=net, box=box, layer=layer, via_layer=via_layer)
        return self.add_guide(guide)

    def create_group(self, name: str, parent_group: Optional[str] = None) -> DbGroup:
        """创建 group 并挂到 block。"""

        group = DbGroup(name=name, parent_group=parent_group)
        return self.add_group(group)

    def create_property(
        self,
        name: str,
        value: str | bool | int | float = "",
        owner_type: str = "block",
        owner: Optional[str] = None,
    ) -> DbProperty:
        """创建 property 并挂到 block。"""

        prop = DbProperty(name=name, owner_type=owner_type, owner=owner or self.name)
        prop.set_value(value)
        return self.add_property(prop)


@dataclass
class DbChip:
    """复刻 _dbChip 的 Python 版本。"""

    top: Optional[str] = None
    blocks: Dict[str, DbBlock] = field(default_factory=dict)

    def add_block(self, block: DbBlock) -> DbBlock:
        """添加一个 block，并在需要时把它设成 top。"""

        self.blocks[block.name] = block
        if self.top is None:
            self.top = block.name
        return block

    def get_top_block(self) -> Optional[DbBlock]:
        """返回顶层 block。"""

        if self.top is None:
            return None
        return self.blocks.get(self.top)


@dataclass
class DbDatabase:
    """复刻 _dbDatabase 的 Python 版本。"""

    schema_major: int = 0
    schema_minor: int = 111
    master_id: int = 0
    chip: Optional[DbChip] = None
    tech: Optional[DbTech] = None
    libs: Dict[str, DbLib] = field(default_factory=dict)
    tech_layers: Dict[str, DbTechLayer] = field(default_factory=dict)
    wires: Dict[str, DbWire] = field(default_factory=dict)
    vias: Dict[str, DbVia] = field(default_factory=dict)
    mterms: Dict[str, DbMTerm] = field(default_factory=dict)
    iterms: Dict[str, DbITerm] = field(default_factory=dict)
    properties: Dict[str, DbProperty] = field(default_factory=dict)

    def ensure_chip(self) -> DbChip:
        """没有 chip 时自动创建。"""

        if self.chip is None:
            self.chip = DbChip()
        return self.chip

    def create_block(self, name: str) -> DbBlock:
        """创建 block 并挂到 chip 下。"""

        chip = self.ensure_chip()
        block = DbBlock(name=name)
        chip.add_block(block)
        return block

    def create_tech(self, name: str = "") -> DbTech:
        """创建工艺数据库对象。"""

        self.tech = DbTech(name=name)
        return self.tech

    def create_lib(self, name: str) -> DbLib:
        """创建 LEF/DEF 库对象。"""

        lib = DbLib(name=name)
        self.libs[name] = lib
        return lib

    def create_tech_layer(self, name: str) -> DbTechLayer:
        """创建工艺层对象。"""

        layer = DbTechLayer(name=name)
        self.tech_layers[name] = layer
        return layer

    def create_wire(self, name: str) -> DbWire:
        """创建 wire 对象。"""

        wire = DbWire()
        self.wires[name] = wire
        return wire

    def create_via(self, name: str) -> DbVia:
        """创建 via 对象。"""

        via = DbVia(name=name)
        self.vias[name] = via
        return via

    def create_mterm(self, name: str) -> DbMTerm:
        """创建 master terminal。"""

        mterm = DbMTerm(name=name)
        self.mterms[name] = mterm
        return mterm

    def create_iterm(self, name: str) -> DbITerm:
        """创建 instance terminal。"""

        iterm = DbITerm(inst=name)
        self.iterms[name] = iterm
        return iterm

    def create_property(
        self,
        name: str,
        value: str | bool | int | float = "",
        owner_type: str = "database",
        owner: Optional[str] = None,
    ) -> DbProperty:
        """创建数据库作用域 property。"""

        prop = DbProperty(name=name, owner_type=owner_type, owner=owner)
        prop.set_value(value)
        self.properties[name] = prop
        return prop

    def is_schema(self, rev: int) -> bool:
        """对应 OpenDB 的 isSchema(rev)。"""

        return self.schema_minor >= rev

    def is_less_than_schema(self, rev: int) -> bool:
        """对应 OpenDB 的 isLessThanSchema(rev)。"""

        return self.schema_minor < rev


def create_database() -> DbDatabase:
    """创建一个新的数据库对象。"""

    return DbDatabase()


def create_chip(db: DbDatabase) -> DbChip:
    """确保数据库里存在 chip。"""

    return db.ensure_chip()


def create_block(db: DbDatabase, name: str) -> DbBlock:
    """创建并返回 block。"""

    return db.create_block(name)


def create_tech(db: DbDatabase, name: str = "") -> DbTech:
    """创建并返回 tech。"""

    return db.create_tech(name)


def create_lib(db: DbDatabase, name: str) -> DbLib:
    """创建并返回 lib。"""

    return db.create_lib(name)


def create_tech_layer(db: DbDatabase, name: str) -> DbTechLayer:
    """创建并返回 tech layer。"""

    return db.create_tech_layer(name)


def create_wire(db: DbDatabase, name: str) -> DbWire:
    """创建并返回 wire。"""

    return db.create_wire(name)


def create_via(db: DbDatabase, name: str) -> DbVia:
    """创建并返回 via。"""

    return db.create_via(name)


def create_mterm(db: DbDatabase, name: str) -> DbMTerm:
    """创建并返回 mterm。"""

    return db.create_mterm(name)


def create_iterm(db: DbDatabase, name: str) -> DbITerm:
    """创建并返回 iterm。"""

    return db.create_iterm(name)


def create_row(block: DbBlock, name: str, **kwargs: Any) -> DbRow:
    """创建并返回 row。"""

    return block.create_row(name, **kwargs)


def create_bterm(block: DbBlock, name: str, **kwargs: Any) -> DbBTerm:
    """创建并返回 bterm。"""

    return block.create_bterm(name, **kwargs)


def create_bpin(block: DbBlock, name: str, **kwargs: Any) -> DbBPin:
    """创建并返回 bpin。"""

    return block.create_bpin(name, **kwargs)


def create_guide(block: DbBlock, name: str, **kwargs: Any) -> DbGuide:
    """创建并返回 guide。"""

    return block.create_guide(name, **kwargs)


def create_group(block: DbBlock, name: str, **kwargs: Any) -> DbGroup:
    """创建并返回 group。"""

    return block.create_group(name, **kwargs)


def create_property(
    owner: DbDatabase | DbBlock,
    name: str,
    value: str | bool | int | float = "",
    **kwargs: Any,
) -> DbProperty:
    """创建并返回 property。"""

    return owner.create_property(name, value, **kwargs)
