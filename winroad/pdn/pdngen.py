"""PdnGen 顶层入口和 Tcl 风格兼容函数。"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence, Set

from .component import FollowPins, RingLayer, Rings, Straps
from .domain import GridSwitchedPower, PowerCell, VoltageDomain
from .grid import BumpGrid, CoreGrid, ExistingGrid, Grid, InstanceGrid
from .renderer import PDNRenderer
from .sroute import SRoute
from .types import ExtensionMode, Halo, PowerSwitchNetworkType, Rect, StartsWith, _normalize_power_switch_network, _not_implemented, _rect_intersects, _starts_with_power
from .via import Connect

@dataclass
class PdnGen:
    """对应 `pdn::PdnGen` 顶层入口。"""

    db: Any = None
    logger: Any = None
    sroute: Optional[SRoute] = None
    debug_renderer: Optional[PDNRenderer] = None
    core_domain: Optional[VoltageDomain] = None
    domains: List[VoltageDomain] = field(default_factory=list)
    switched_power_cells: List[PowerCell] = field(default_factory=list)
    allow_repair_channels: bool = False

    def init(self, db: Any, logger: Any = None) -> None:
        self.db = db
        self.logger = logger
        self.sroute = SRoute(self)

    def reset(self) -> None:
        self.core_domain = None
        self.domains.clear()
        self.switched_power_cells.clear()
        self.sroute = SRoute(self) if self.db is not None else None
        self.debug_renderer = None

    def resetShapes(self) -> None:
        for domain in self.getDomains():
            domain.resetGrids()

    def report(self) -> Dict[str, Any]:
        return {
            "domains": [domain.report() for domain in self.getDomains()],
            "switched_power_cells": [cell.report() for cell in self.switched_power_cells],
            "allow_repair_channels": self.allow_repair_channels,
            "domain_count": len(self.getDomains()),
            "grid_count": sum(len(domain.getGrids()) for domain in self.getDomains()),
            "sroute_connects": self.sroute.getSrouteConnects() if self.sroute is not None else [],
            "debug_renderer": self.debug_renderer.report() if self.debug_renderer is not None else None,
        }

    def findSwitchedPowerCell(self, name: str) -> Optional[PowerCell]:
        return next((cell for cell in self.switched_power_cells if cell.getName() == name), None)

    def makeSwitchedPowerCell(self, master: Any, control: Any, acknowledge: Any, switched_power: Any, alwayson_power: Any, ground: Any) -> PowerCell:
        if master is None:
            raise ValueError("power switch cell master is required")
        cell = PowerCell(self.logger, master, control, acknowledge, switched_power, alwayson_power, ground)
        if self.findSwitchedPowerCell(cell.getName()) is not None:
            raise ValueError(f"power switch cell {cell.getName()!r} already exists")
        self.switched_power_cells.append(cell)
        return cell

    def getDomains(self) -> List[VoltageDomain]:
        domains: List[VoltageDomain] = []
        if self.core_domain is not None:
            domains.append(self.core_domain)
        domains.extend(self.domains)
        return domains

    def findDomain(self, name: str) -> Optional[VoltageDomain]:
        return next((domain for domain in self.getDomains() if domain.getName() == name), None)

    def setCoreDomain(self, power: Any, switched_power: Any, ground: Any, secondary: Sequence[Any] = ()) -> VoltageDomain:
        if any(domain.getName() == "Core" for domain in self.domains):
            raise ValueError("region voltage domain named 'Core' conflicts with core domain")
        domain = VoltageDomain(
            pdngen=self,
            name="Core",
            block=self._get_block(),
            power=power,
            ground=ground,
            secondary=list(secondary),
            logger=self.logger,
            switched_power=switched_power,
        )
        self.core_domain = domain
        return domain

    def makeRegionVoltageDomain(self, name: str, power: Any, switched_power: Any, ground: Any, secondary_nets: Sequence[Any], region: Any) -> VoltageDomain:
        if self.findDomain(name) is not None:
            raise ValueError(f"voltage domain {name!r} already exists")
        domain = VoltageDomain(
            pdngen=self,
            name=name,
            block=self._get_block(),
            power=power,
            ground=ground,
            secondary=list(secondary_nets),
            region=region,
            logger=self.logger,
            switched_power=switched_power,
        )
        self.domains.append(domain)
        return domain

    def buildGrids(self, trim: bool = True) -> None:
        self.checkSetup()
        for domain in self.getDomains():
            for grid in domain.getGrids():
                grid.checkSetup()
        _not_implemented("PdnGen::buildGrids")

    def findGrid(self, name: str) -> List[Grid]:
        return [
            grid
            for domain in self.getDomains()
            for grid in domain.getGrids()
            if grid.getName() == name or grid.getLongName() == name
        ]

    def getGridByName(self, name: str, domain: Optional[VoltageDomain | str] = None) -> Optional[Grid]:
        if isinstance(domain, str):
            domain = self.findDomain(domain)
        domains = [domain] if domain is not None else self.getDomains()
        for voltage_domain in domains:
            if voltage_domain is None:
                continue
            grid = voltage_domain.getGridByName(name)
            if grid is not None:
                return grid
        return None

    def findGridForInstance(self, inst: Any) -> Optional[InstanceGrid]:
        for domain in self.getDomains():
            for grid in domain.getGrids():
                if isinstance(grid, InstanceGrid) and grid.getInstance() is inst:
                    return grid
        return None

    def findGridContainingRect(self, rect: Rect) -> List[Grid]:
        matches: List[Grid] = []
        for domain in self.getDomains():
            for grid in domain.getGrids():
                if any(_rect_intersects(shape.getRect(), rect) for shape in grid.getShapes()):
                    matches.append(grid)
        return matches

    def makeCoreGrid(
        self,
        domain: VoltageDomain,
        name: str,
        starts_with: StartsWith | str | bool = StartsWith.POWER,
        pin_layers: Sequence[Any] = (),
        generate_obstructions: Sequence[Any] = (),
        powercell: Optional[PowerCell] = None,
        powercontrol: Any = None,
        powercontrolnetwork: Optional[str] = None,
    ) -> CoreGrid:
        grid = CoreGrid(domain, name, _starts_with_power(starts_with), list(generate_obstructions))
        grid.setPinLayers(pin_layers)
        if powercell is not None:
            network = _normalize_power_switch_network(powercontrolnetwork or PowerSwitchNetworkType.STAR)
            grid.switched_power_cell = GridSwitchedPower(grid, powercell, powercontrol, network)
        domain.addGrid(grid)
        return grid

    def makeInstanceGrid(
        self,
        domain: VoltageDomain,
        name: str,
        starts_with: StartsWith | str | bool,
        inst: Any,
        halo: Halo = (0, 0, 0, 0),
        pg_pins_to_boundary: bool = False,
        default_grid: bool = False,
        generate_obstructions: Sequence[Any] = (),
        is_bump: bool = False,
    ) -> InstanceGrid:
        cls = BumpGrid if is_bump else InstanceGrid
        grid = cls(domain, name, _starts_with_power(starts_with), list(generate_obstructions), inst=inst)
        grid.addHalo(halo)
        grid.setGridToBoundary(pg_pins_to_boundary)
        grid.setReplaceable(default_grid)
        domain.addGrid(grid)
        return grid

    def makeExistingGrid(self, name: str, generate_obstructions: Sequence[Any] = ()) -> ExistingGrid:
        if self.getGridByName(name) is not None:
            raise ValueError(f"grid {name!r} already exists")
        domain = VoltageDomain(self, f"{name}_domain", self._get_block(), logger=self.logger)
        grid = ExistingGrid(domain, name, True, list(generate_obstructions), pdngen=self, block=self._get_block(), logger=self.logger)
        domain.addGrid(grid)
        self.domains.append(domain)
        return grid

    def makeRing(
        self,
        grid: Grid,
        layer0: Any,
        width0: int,
        spacing0: int,
        layer1: Any,
        width1: int,
        spacing1: int,
        starts_with: StartsWith | str | bool = StartsWith.GRID,
        offset: Halo = (0, 0, 0, 0),
        pad_offset: Halo = (0, 0, 0, 0),
        extend: bool = False,
        pad_pin_layers: Sequence[Any] = (),
        nets: Sequence[Any] = (),
        allow_out_of_die: bool = False,
    ) -> Rings:
        if grid is None:
            raise ValueError("ring grid is required")
        ring = Rings(
            grid=grid,
            starts_with_power=_starts_with_power(starts_with),
            nets=list(nets),
            layers=(RingLayer(layer0, width0, spacing0), RingLayer(layer1, width1, spacing1)),
            offset=offset,
            pad_offset=pad_offset,
            extend_to_boundary=extend,
            allow_outside_die=allow_out_of_die,
        )
        grid.addRing(ring)
        if pad_pin_layers:
            _not_implemented("PdnGen::makeRing pad direct connection")
        return ring

    def makeFollowpin(self, grid: Grid, layer: Any, width: int = 0, extend: ExtensionMode = ExtensionMode.CORE) -> FollowPins:
        if grid is None:
            raise ValueError("followpin grid is required")
        followpin = FollowPins(grid=grid, layer=layer, width=width, pitch=0, extend_mode=extend)
        grid.addStrap(followpin)
        return followpin

    def makeStrap(
        self,
        grid: Grid,
        layer: Any,
        width: int,
        spacing: int,
        pitch: int,
        offset: int,
        number_of_straps: int,
        snap: bool,
        starts_with: StartsWith | str | bool,
        extend: ExtensionMode,
        nets: Sequence[Any] = (),
    ) -> Straps:
        if grid is None:
            raise ValueError("strap grid is required")
        strap = Straps(
            grid=grid,
            starts_with_power=_starts_with_power(starts_with),
            nets=list(nets),
            layer=layer,
            width=width,
            pitch=pitch,
            spacing=spacing,
            number_of_straps=number_of_straps,
            offset=offset,
            snap=snap,
            extend_mode=extend,
        )
        grid.addStrap(strap)
        return strap

    def makeConnect(
        self,
        grid: Grid,
        layer0: Any,
        layer1: Any,
        cut_pitch_x: int = 0,
        cut_pitch_y: int = 0,
        vias: Sequence[Any] = (),
        techvias: Sequence[Any] = (),
        max_rows: int = 0,
        max_columns: int = 0,
        ongrid: Sequence[Any] = (),
        split_cuts: Optional[Mapping[Any, Any]] = None,
        dont_use_vias: str = "",
    ) -> Connect:
        if grid is None:
            raise ValueError("connect grid is required")
        connect = Connect(grid, layer0, layer1, list(vias), list(techvias), cut_pitch_x, cut_pitch_y, max_rows, max_columns, set(ongrid), dict(split_cuts or {}))
        grid.addConnect(connect)
        if dont_use_vias:
            connect.filterVias(dont_use_vias)
        return connect

    def writeToDb(self, add_pins: bool, report_file: str = "") -> None:
        self.checkSetup()
        _not_implemented("PdnGen::writeToDb")

    def ripUp(self, net: Any) -> None:
        _not_implemented("PdnGen::ripUp")

    def setDebugRenderer(self, on: bool) -> None:
        self.debug_renderer = PDNRenderer(on, block=self._get_block(), logger=self.logger) if on else None
        if self.debug_renderer is not None:
            self.debug_renderer.setGrids([grid for domain in self.getDomains() for grid in domain.getGrids()])

    def rendererRedraw(self) -> None:
        if self.debug_renderer is not None:
            self.debug_renderer.redraw()

    def setAllowRepairChannels(self, allow: bool) -> None:
        self.allow_repair_channels = allow
        for domain in self.getDomains():
            for grid in domain.getGrids():
                grid.setAllowRepairChannels(allow)

    def filterVias(self, filter_text: str) -> None:
        for domain in self.getDomains():
            for grid in domain.getGrids():
                for connect in grid.getConnect():
                    connect.filterVias(filter_text)

    def checkSetup(self) -> None:
        if self.db is None:
            raise ValueError("PdnGen has not been initialized with db")
        if not self.getDomains():
            raise ValueError("PdnGen has no voltage domains")
        for domain in self.getDomains():
            domain.checkSetup()

    def repairVias(self, nets: Set[Any]) -> None:
        self.checkSetup()
        _not_implemented("PdnGen::repairVias")

    def addSrouteConnect(self, **params: Any) -> Dict[str, Any]:
        if self.sroute is None:
            self.sroute = SRoute(self)
        return self.sroute.addSrouteConnect(**params)

    def createSrouteWires(self, *args: Any, **kwargs: Any) -> None:
        if self.sroute is None:
            self.sroute = SRoute(self)
        self.sroute.createSrouteWires(*args, **kwargs)

    def trimShapes(self) -> None:
        _not_implemented("PdnGen::trimShapes")

    def updateVias(self) -> None:
        _not_implemented("PdnGen::updateVias")

    def cleanupVias(self) -> None:
        _not_implemented("PdnGen::cleanupVias")

    def checkDesign(self, block: Any) -> None:
        _not_implemented("PdnGen::checkDesign")

    def ensureCoreDomain(self) -> VoltageDomain:
        if self.core_domain is None:
            _not_implemented("PdnGen::ensureCoreDomain")
        return self.core_domain

    def updateRenderer(self) -> None:
        if self.debug_renderer is not None:
            self.debug_renderer.redraw()

    def importUPF(self, target: Any, network_type: Optional[PowerSwitchNetworkType] = None) -> bool:
        _not_implemented("PdnGen::importUPF")

    def _get_block(self) -> Any:
        if self.db is None:
            return None
        chip = getattr(self.db, "chip", None)
        if chip is not None and hasattr(chip, "get_top_block"):
            return chip.get_top_block()
        if chip is not None:
            top = getattr(chip, "top", None)
            return getattr(chip, "blocks", {}).get(top) if top is not None else None
        return getattr(self.db, "block", None)


def make_pdn_gen(db: Any = None, logger: Any = None) -> PdnGen:
    """对应 `makePdnGen/initPdnGen` 的 Python 便捷入口。"""

    pdngen = PdnGen()
    pdngen.init(db, logger)
    return pdngen


def initPdnGen(pdngen: PdnGen, db: Any, logger: Any = None) -> None:
    """对应 `ord::initPdnGen`。"""

    pdngen.init(db, logger)


def makePdnGen() -> PdnGen:
    """对应 `ord::makePdnGen`。"""

    return PdnGen()


def deletePdnGen(pdngen: PdnGen) -> None:
    """对应 `ord::deletePdnGen`；Python 由 GC 管理，这里清空状态。"""

    pdngen.reset()


def pdngen(pdngen_obj: PdnGen, skip_trim: bool = False, dont_add_pins: bool = False, reset: bool = False, ripup: bool = False, report_only: bool = False, failed_via_report: str = "") -> Any:
    """对应 Tcl `pdngen` 命令。"""

    if reset:
        pdngen_obj.resetShapes()
    if report_only:
        return pdngen_obj.report()
    if ripup:
        _not_implemented("pdngen -ripup")
    pdngen_obj.buildGrids(trim=not skip_trim)
    pdngen_obj.writeToDb(add_pins=not dont_add_pins, report_file=failed_via_report)
    return None


def report_power_grid(pdngen_obj: PdnGen) -> Dict[str, Any]:
    """报告当前 Python PDN 对象树；不读取或写入 ODB。"""

    return pdngen_obj.report()


def check_power_grid(pdngen_obj: PdnGen) -> None:
    """对应 setup/check 边界，只检查已建对象必要关系。"""

    pdngen_obj.checkSetup()


def repair_pdn_vias(pdngen_obj: PdnGen, nets: Iterable[Any]) -> None:
    """对应 Tcl `repair_pdn_vias`。"""

    pdngen_obj.repairVias(set(nets))


def ripup_power_grid(pdngen_obj: PdnGen, net: Any) -> None:
    """对应 Tcl ripup 边界。"""

    pdngen_obj.ripUp(net)


def write_power_grid(pdngen_obj: PdnGen, add_pins: bool = True, report_file: str = "") -> None:
    """对应写库边界；真实 OpenDB 写入后续翻译。"""

    pdngen_obj.writeToDb(add_pins=add_pins, report_file=report_file)
