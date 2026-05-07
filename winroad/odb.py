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
from typing import Dict, List, Optional


class SigType(str, Enum):
    """对应 OpenDB 的 dbSigType::Value。"""

    SIGNAL = "signal"
    POWER = "power"
    GROUND = "ground"
    CLOCK = "clock"
    ANALOG = "analog"
    OTHER = "other"


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
