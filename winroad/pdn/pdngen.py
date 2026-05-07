"""PdnGen 顶层入口和 Tcl 风格兼容函数。"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence, Set

from .component import FollowPins, PadDirectConnectionStraps, RepairChannelStraps, RingLayer, Rings, Straps
from .domain import GridSwitchedPower, PowerCell, VoltageDomain
from .grid import BumpGrid, CoreGrid, ExistingGrid, Grid, InstanceGrid
from .renderer import PDNRenderer
from .sroute import SRoute
from .types import ExtensionMode, FailedViaReason, GridComponentType, GridType, Halo, PdnIssue, PowerSwitchNetworkType, Rect, Shape, ShapeType, SplitCut, StartsWith, _name, _normalize_extension_mode, _normalize_power_switch_network, _not_implemented, _rect_intersects, _starts_with_power, _validate_optional_rect, _validate_rect
from .via import Connect, Via

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
            "summary": self.reportSummary(),
            "sroute": self.sroute.report() if self.sroute is not None else None,
            "sroute_connects": self.sroute.getSrouteConnects() if self.sroute is not None else [],
            "debug_renderer": self.debug_renderer.report() if self.debug_renderer is not None else None,
            "setup_issues": self.reportSetupIssues(),
        }

    def reportSummary(self) -> Dict[str, Any]:
        domain_summaries = [domain.summary() for domain in self.getDomains()]
        failed_by_reason: Dict[str, int] = {}
        for domain in domain_summaries:
            for reason, count in domain["failed_vias_by_reason"].items():
                failed_by_reason[reason] = failed_by_reason.get(reason, 0) + count
        return {
            "domain_count": len(domain_summaries),
            "grid_count": sum(domain["grid_count"] for domain in domain_summaries),
            "shape_count": sum(domain["shape_count"] for domain in domain_summaries),
            "via_count": sum(domain["via_count"] for domain in domain_summaries),
            "failed_via_count": sum(domain["failed_via_count"] for domain in domain_summaries),
            "failed_vias_by_reason": failed_by_reason,
            "allow_repair_channels": self.allow_repair_channels,
            "sroute": self.sroute.summary() if self.sroute is not None else None,
            "renderer": self.debug_renderer.snapshot() if self.debug_renderer is not None else None,
            "setup_issue_count": len(self.collectSetupIssues()),
            "domains": domain_summaries,
        }

    def viaFailureReport(self, include_locations: bool = True) -> Dict[str, Any]:
        grids = [
            grid.viaFailureReport(include_locations=include_locations)
            for domain in self.getDomains()
            for grid in domain.getGrids()
        ]
        by_reason: Dict[str, int] = {}
        for grid in grids:
            for reason, count in grid["by_reason"].items():
                by_reason[reason] = by_reason.get(reason, 0) + count
        return {"total": sum(by_reason.values()), "by_reason": by_reason, "grids": grids}

    def rendererSelectionSnapshot(self) -> Optional[Dict[str, Any]]:
        return self.debug_renderer.snapshot() if self.debug_renderer is not None else None

    def srouteSummary(self) -> Dict[str, Any]:
        return self.sroute.summary() if self.sroute is not None else {"connect_count": 0, "connects_with_nets": 0, "connects_with_layers": 0, "parameter_keys": []}

    def exportConfig(self) -> Dict[str, Any]:
        return {
            "version": 1,
            "allow_repair_channels": self.allow_repair_channels,
            "domains": [self._export_domain_config(domain, domain is self.core_domain) for domain in self.getDomains()],
            "switched_power_cells": [cell.report() for cell in self.switched_power_cells],
            "sroute": self.sroute.report() if self.sroute is not None else None,
            "renderer": self.debug_renderer.snapshot() if self.debug_renderer is not None else None,
        }

    def exportState(self) -> Dict[str, Any]:
        return {
            "version": 1,
            "config": self.exportConfig(),
            "runtime": {
                "domains": [self._export_domain_state(domain) for domain in self.getDomains()],
                "summary": self.reportSummary(),
                "via_failure_report": self.viaFailureReport(include_locations=True),
            },
        }

    def importConfig(self, data: Mapping[str, Any], resolver: Any = None) -> "PdnGen":
        self._check_version(data)
        db = self.db
        logger = self.logger
        self.reset()
        self.db = db
        self.logger = logger
        self.sroute = SRoute(self)
        self.allow_repair_channels = bool(data.get("allow_repair_channels", False))
        for cell_data in data.get("switched_power_cells", []):
            self.switched_power_cells.append(
                PowerCell(
                    self.logger,
                    self._resolve_ref(cell_data.get("name"), resolver),
                    self._resolve_ref(cell_data.get("control"), resolver),
                    self._resolve_ref(cell_data.get("acknowledge"), resolver),
                    self._resolve_ref(cell_data.get("switched_power"), resolver),
                    self._resolve_ref(cell_data.get("alwayson_power"), resolver),
                    self._resolve_ref(cell_data.get("ground"), resolver),
                )
            )
        seen_domains: Set[str] = set()
        for domain_data in data.get("domains", []):
            domain_name = str(domain_data["name"])
            if domain_name in seen_domains:
                raise ValueError(f"duplicate voltage domain in config: {domain_name!r}")
            seen_domains.add(domain_name)
            domain = VoltageDomain(
                pdngen=self,
                name=domain_name,
                block=self._get_block(),
                power=self._resolve_ref(domain_data.get("power"), resolver),
                ground=self._resolve_ref(domain_data.get("ground"), resolver),
                secondary=[self._resolve_ref(net, resolver) for net in domain_data.get("secondary", [])],
                region=self._resolve_ref(domain_data.get("region"), resolver),
                logger=self.logger,
                switched_power=self._resolve_ref(domain_data.get("switched_power"), resolver),
            )
            if domain_data.get("core", False):
                if self.core_domain is not None:
                    raise ValueError("config contains more than one core voltage domain")
                self.core_domain = domain
            else:
                self.domains.append(domain)
            for grid_data in domain_data.get("grids", []):
                grid = self._import_grid_config(domain, grid_data, resolver)
                domain.addGrid(grid)
        if data.get("sroute"):
            for connect in data["sroute"].get("connects", []):
                self.sroute.addSrouteConnect(**connect)
        if data.get("renderer"):
            renderer_data = data["renderer"]
            self.debug_renderer = PDNRenderer(bool(renderer_data.get("enabled", False)), block=self._get_block(), logger=self.logger)
            self.debug_renderer.setGrids([grid for domain in self.getDomains() for grid in domain.getGrids()])
            for selected in renderer_data.get("selected", []):
                self.debug_renderer.select(selected.get("name", selected))
        self.setAllowRepairChannels(self.allow_repair_channels)
        return self

    def importState(self, data: Mapping[str, Any], resolver: Any = None) -> "PdnGen":
        self._check_version(data)
        config = data.get("config", data)
        self.importConfig(config, resolver=resolver)
        runtime = data.get("runtime", {})
        for domain_data in runtime.get("domains", []):
            domain = self.findDomain(str(domain_data.get("name", "")))
            if domain is None:
                continue
            for grid_data in domain_data.get("grids", []):
                grid = domain.getGridByName(str(grid_data.get("name", "")))
                if grid is None:
                    continue
                self._import_grid_state(grid, grid_data, resolver)
        return self

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
        issues = self.collectSetupIssues()
        if issues:
            raise ValueError("; ".join(f"{issue.path}: {issue.message}" for issue in issues))

    def collectSetupIssues(self) -> List[PdnIssue]:
        issues: List[PdnIssue] = []
        if self.db is None:
            issues.append(PdnIssue("pdngen", "PdnGen has not been initialized with db"))
        domains = self.getDomains()
        if not domains:
            issues.append(PdnIssue("pdngen", "PdnGen has no voltage domains"))
        seen_domains: Set[str] = set()
        for index, domain in enumerate(domains):
            domain_path = f"pdngen/domain[{index}]/{domain.getName()}"
            if domain.getName() in seen_domains:
                issues.append(PdnIssue(domain_path, f"duplicate voltage domain {domain.getName()!r}"))
            seen_domains.add(domain.getName())
            if domain.pdngen is not self:
                issues.append(PdnIssue(domain_path, f"voltage domain {domain.getName()!r} is attached to the wrong PdnGen"))
            issues.extend(domain.collectSetupIssues(domain_path))
        return issues

    def reportSetupIssues(self) -> List[Dict[str, str]]:
        return [issue.report() for issue in self.collectSetupIssues()]

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

    def _export_domain_config(self, domain: VoltageDomain, is_core: bool) -> Dict[str, Any]:
        return {
            "name": domain.getName(),
            "core": is_core,
            "power": self._ref(domain.power),
            "switched_power": self._ref(domain.switched_power),
            "ground": self._ref(domain.ground),
            "secondary": [self._ref(net) for net in domain.secondary],
            "region": self._ref(domain.region),
            "grids": [self._export_grid_config(grid) for grid in domain.getGrids()],
        }

    def _export_grid_config(self, grid: Grid) -> Dict[str, Any]:
        return {
            "name": grid.getName(),
            "long_name": grid.getLongName(),
            "type": grid.type().value,
            "is_bump": isinstance(grid, BumpGrid),
            "starts_with_power": grid.starts_with_power,
            "generate_obstructions": [self._ref(layer) for layer in grid.generate_obstructions],
            "pin_layers": [self._ref(layer) for layer in grid.getPinLayers()],
            "allow_repair_channels": grid.allow_repair_channels,
            "instance": self._ref(grid.inst) if isinstance(grid, InstanceGrid) else None,
            "halo": grid.halos if isinstance(grid, InstanceGrid) else None,
            "grid_to_boundary": grid.grid_to_boundary if isinstance(grid, InstanceGrid) else None,
            "replaceable": grid.replaceable if isinstance(grid, InstanceGrid) else None,
            "rings": [self._export_component_config(ring) for ring in grid.getRings()],
            "straps": [self._export_component_config(strap) for strap in grid.getStraps()],
            "connect": [self._export_connect_config(connect) for connect in grid.getConnect()],
        }

    def _export_component_config(self, component: Any) -> Dict[str, Any]:
        data = {
            "type": component.type().value,
            "starts_with_power": component.getStartsWithPower(),
            "nets": [self._ref(net) for net in component.nets],
        }
        if isinstance(component, Rings):
            data.update(
                {
                    "layers": [
                        {"layer": self._ref(layer.layer), "width": layer.width, "spacing": layer.spacing}
                        for layer in component.layers
                    ],
                    "offset": component.offset,
                    "pad_offset": component.pad_offset,
                    "extend_to_boundary": component.extend_to_boundary,
                    "allow_outside_die": component.allow_outside_die,
                }
            )
        elif isinstance(component, Straps):
            data.update(
                {
                    "layer": self._ref(component.layer),
                    "width": component.width,
                    "pitch": component.pitch,
                    "spacing": component.spacing,
                    "number_of_straps": component.number_of_straps,
                    "offset": component.offset,
                    "snap": component.snap,
                    "extend_mode": component.extend_mode.value,
                    "strap_start": component.strap_start,
                    "strap_end": component.strap_end,
                    "direction": self._ref(component.direction),
                }
            )
            if isinstance(component, PadDirectConnectionStraps):
                data.update({"iterm": self._ref(component.iterm), "connect_pad_layers": [self._ref(layer) for layer in component.connect_pad_layers]})
            if isinstance(component, RepairChannelStraps):
                data.update(
                    {
                        "target": component.getGrid().getStraps().index(component.target) if component.target in component.getGrid().getStraps() else None,
                        "connect_to": self._ref(component.connect_to),
                        "area": component.area,
                        "available_area": component.available_area,
                        "obs_check_area": component.obs_check_area,
                        "repair_nets": [self._ref(net) for net in component.repair_nets],
                        "invalid": component.invalid,
                    }
                )
        return data

    def _export_connect_config(self, connect: Connect) -> Dict[str, Any]:
        return {
            "layer0": self._ref(connect.layer0),
            "layer1": self._ref(connect.layer1),
            "fixed_generate_vias": [self._ref(via) for via in connect.fixed_generate_vias],
            "fixed_tech_vias": [self._ref(via) for via in connect.fixed_tech_vias],
            "cut_pitch_x": connect.cut_pitch_x,
            "cut_pitch_y": connect.cut_pitch_y,
            "max_rows": connect.max_rows,
            "max_columns": connect.max_columns,
            "ongrid": [self._ref(layer) for layer in connect.ongrid],
            "split_cuts": {
                self._ref(layer): {"pitch": split.pitch, "stagger": split.stagger}
                for layer, split in connect.split_cuts.items()
            },
        }

    def _export_domain_state(self, domain: VoltageDomain) -> Dict[str, Any]:
        return {"name": domain.getName(), "grids": [self._export_grid_state(grid) for grid in domain.getGrids()]}

    def _export_grid_state(self, grid: Grid) -> Dict[str, Any]:
        components = grid.getGridComponents()
        component_state = []
        for index, component in enumerate(components):
            component_state.append(
                {
                    "index": index,
                    "type": component.type().value,
                    "shapes": [self._export_shape_state(shape) for shape in component.getShapes()],
                }
            )
        shape_index = {id(shape): (component_index, shape_index) for component_index, component in enumerate(components) for shape_index, shape in enumerate(component.getShapes())}
        return {
            "name": grid.getName(),
            "components": component_state,
            "connect": [self._export_connect_state(connect, shape_index) for connect in grid.getConnect()],
            "summary": grid.summary(),
        }

    def _export_shape_state(self, shape: Shape) -> Dict[str, Any]:
        return {
            "layer": self._ref(shape.layer),
            "net": self._ref(shape.net),
            "rect": shape.rect,
            "wire_type": self._ref(shape.wire_type),
            "shape_type": shape.shape_type.value,
            "locked": shape.locked,
            "obstruction": shape.obstruction,
            "iterm_connections": list(shape.iterm_connections),
            "bterm_connections": list(shape.bterm_connections),
        }

    def _export_connect_state(self, connect: Connect, shape_index: Mapping[int, Any]) -> Dict[str, Any]:
        return {
            "layers": [self._ref(connect.layer0), self._ref(connect.layer1)],
            "vias": [
                {
                    "net": self._ref(via.net),
                    "area": via.area,
                    "lower": shape_index.get(id(via.lower)) if via.lower is not None else None,
                    "upper": shape_index.get(id(via.upper)) if via.upper is not None else None,
                    "failed": via.failed,
                    "failed_reason": via.failed_reason.value if via.failed_reason is not None else None,
                }
                for via in connect.getVias()
            ],
            "failed_vias": [
                {"reason": reason.value, "net": self._ref(net), "rect": rect}
                for reason, items in connect.failed_vias.items()
                for net, rect in items
            ],
        }

    def _import_grid_config(self, domain: VoltageDomain, data: Mapping[str, Any], resolver: Any) -> Grid:
        grid_type = data.get("type")
        starts = bool(data.get("starts_with_power", True))
        obstructions = [self._resolve_ref(layer, resolver) for layer in data.get("generate_obstructions", [])]
        if grid_type == GridType.EXISTING.value:
            grid: Grid = ExistingGrid(domain, str(data["name"]), starts, obstructions, pdngen=self, block=self._get_block(), logger=self.logger)
        elif grid_type == GridType.INSTANCE.value:
            cls = BumpGrid if data.get("is_bump", False) else InstanceGrid
            grid = cls(domain, str(data["name"]), starts, obstructions, inst=self._resolve_ref(data.get("instance"), resolver))
            grid.addHalo(tuple(data.get("halo") or (0, 0, 0, 0)))  # type: ignore[arg-type]
            grid.setGridToBoundary(bool(data.get("grid_to_boundary", False)))
            grid.setReplaceable(bool(data.get("replaceable", False)))
        else:
            grid = CoreGrid(domain, str(data["name"]), starts, obstructions)
        grid.setPinLayers([self._resolve_ref(layer, resolver) for layer in data.get("pin_layers", [])])
        grid.setAllowRepairChannels(bool(data.get("allow_repair_channels", False)))
        for ring_data in data.get("rings", []):
            grid.addRing(self._import_ring_config(grid, ring_data, resolver))
        for strap_data in data.get("straps", []):
            grid.addStrap(self._import_strap_config(grid, strap_data, resolver))
        for connect_data in data.get("connect", []):
            grid.addConnect(self._import_connect_config(grid, connect_data, resolver))
        return grid

    def _import_ring_config(self, grid: Grid, data: Mapping[str, Any], resolver: Any) -> Rings:
        layers = data.get("layers", [])
        ring_layers = tuple(RingLayer(self._resolve_ref(layer.get("layer"), resolver), layer.get("width", 0), layer.get("spacing", 0)) for layer in layers)
        if len(ring_layers) != 2:
            raise ValueError("ring config requires exactly two layers")
        return Rings(
            grid=grid,
            starts_with_power=bool(data.get("starts_with_power", True)),
            nets=[self._resolve_ref(net, resolver) for net in data.get("nets", [])],
            layers=ring_layers,  # type: ignore[arg-type]
            offset=tuple(data.get("offset", (0, 0, 0, 0))),  # type: ignore[arg-type]
            pad_offset=tuple(data.get("pad_offset", (0, 0, 0, 0))),  # type: ignore[arg-type]
            extend_to_boundary=bool(data.get("extend_to_boundary", False)),
            allow_outside_die=bool(data.get("allow_outside_die", False)),
        )

    def _import_strap_config(self, grid: Grid, data: Mapping[str, Any], resolver: Any) -> Straps:
        component_type = data.get("type")
        cls: Any = Straps
        if component_type == GridComponentType.FOLLOWPIN.value:
            cls = FollowPins
        elif component_type == GridComponentType.PAD_CONNECT.value:
            cls = PadDirectConnectionStraps
        elif component_type == GridComponentType.REPAIR_CHANNEL.value:
            cls = RepairChannelStraps
        strap = cls(
            grid=grid,
            starts_with_power=bool(data.get("starts_with_power", True)),
            nets=[self._resolve_ref(net, resolver) for net in data.get("nets", [])],
            layer=self._resolve_ref(data.get("layer"), resolver),
            width=data.get("width", 0),
            pitch=data.get("pitch", 0),
            spacing=data.get("spacing", 0),
            number_of_straps=data.get("number_of_straps", 0),
            offset=data.get("offset", 0),
            snap=bool(data.get("snap", False)),
            extend_mode=_normalize_extension_mode(data.get("extend_mode", ExtensionMode.CORE)),
            strap_start=data.get("strap_start", 0),
            strap_end=data.get("strap_end", 0),
            direction=self._resolve_ref(data.get("direction"), resolver),
        )
        if isinstance(strap, PadDirectConnectionStraps):
            strap.iterm = self._resolve_ref(data.get("iterm"), resolver)
            strap.connect_pad_layers = [self._resolve_ref(layer, resolver) for layer in data.get("connect_pad_layers", [])]
        if isinstance(strap, RepairChannelStraps):
            strap.connect_to = self._resolve_ref(data.get("connect_to"), resolver)
            strap.area = _validate_rect(tuple(data.get("area", (0, 0, 0, 0))), "repair area")  # type: ignore[arg-type]
            strap.available_area = _validate_rect(tuple(data.get("available_area", (0, 0, 0, 0))), "repair available_area")  # type: ignore[arg-type]
            strap.obs_check_area = _validate_rect(tuple(data.get("obs_check_area", (0, 0, 0, 0))), "repair obs_check_area")  # type: ignore[arg-type]
            strap.repair_nets = {self._resolve_ref(net, resolver) for net in data.get("repair_nets", [])}
            strap.invalid = bool(data.get("invalid", False))
            target_index = data.get("target")
            if target_index is not None:
                straps = grid.getStraps()
                target_index = int(target_index)
                if 0 <= target_index < len(straps):
                    strap.target = straps[target_index]
        return strap

    def _import_connect_config(self, grid: Grid, data: Mapping[str, Any], resolver: Any) -> Connect:
        split_cuts = {
            self._resolve_ref(layer, resolver): SplitCut(value.get("pitch", 0), bool(value.get("stagger", False)))
            for layer, value in data.get("split_cuts", {}).items()
        }
        return Connect(
            grid,
            self._resolve_ref(data.get("layer0"), resolver),
            self._resolve_ref(data.get("layer1"), resolver),
            [self._resolve_ref(via, resolver) for via in data.get("fixed_generate_vias", [])],
            [self._resolve_ref(via, resolver) for via in data.get("fixed_tech_vias", [])],
            data.get("cut_pitch_x", 0),
            data.get("cut_pitch_y", 0),
            data.get("max_rows", 0),
            data.get("max_columns", 0),
            {self._resolve_ref(layer, resolver) for layer in data.get("ongrid", [])},
            split_cuts,
        )

    def _import_grid_state(self, grid: Grid, data: Mapping[str, Any], resolver: Any) -> None:
        components = grid.getGridComponents()
        shapes_by_ref: Dict[Any, Shape] = {}
        # Runtime state 是“已生成/导入”的瞬时状态；重新导入前必须清理旧 shape/via，
        # 否则同一份 state round trip 多次会把 via 回链重复挂在 Shape 上。
        grid.resetShapes()
        for component_data in data.get("components", []):
            index = int(component_data.get("index", -1))
            if index < 0 or index >= len(components):
                continue
            component = components[index]
            for shape_index, shape_data in enumerate(component_data.get("shapes", [])):
                shape = Shape(
                    layer=self._resolve_ref(shape_data.get("layer"), resolver),
                    net=self._resolve_ref(shape_data.get("net"), resolver),
                    rect=tuple(shape_data.get("rect", (0, 0, 0, 0))),  # type: ignore[arg-type]
                    wire_type=self._resolve_ref(shape_data.get("wire_type"), resolver),
                    shape_type=ShapeType(shape_data.get("shape_type", ShapeType.SHAPE.value)),
                    locked=bool(shape_data.get("locked", False)),
                    obstruction=_validate_optional_rect(tuple(shape_data["obstruction"]), "shape obstruction") if shape_data.get("obstruction") is not None else None,
                )
                for rect in shape_data.get("iterm_connections", []):
                    shape.addITermConnection(tuple(rect))  # type: ignore[arg-type]
                for rect in shape_data.get("bterm_connections", []):
                    shape.addBTermConnection(tuple(rect))  # type: ignore[arg-type]
                component.addShape(shape)
                shapes_by_ref[(index, shape_index)] = shape
        for connect_index, connect_data in enumerate(data.get("connect", [])):
            if connect_index >= len(grid.getConnect()):
                continue
            connect = grid.getConnect()[connect_index]
            connect.clearShapes()
            connect.clearFailedVias()
            for via_data in connect_data.get("vias", []):
                via = Via(
                    connect=connect,
                    net=self._resolve_ref(via_data.get("net"), resolver),
                    area=tuple(via_data.get("area", (0, 0, 0, 0))),  # type: ignore[arg-type]
                    lower=shapes_by_ref.get(tuple(via_data["lower"])) if via_data.get("lower") is not None else None,
                    upper=shapes_by_ref.get(tuple(via_data["upper"])) if via_data.get("upper") is not None else None,
                    failed=bool(via_data.get("failed", False)),
                    failed_reason=FailedViaReason(via_data["failed_reason"]) if via_data.get("failed_reason") else None,
                )
                connect.addVia(via)
            for failure in connect_data.get("failed_vias", []):
                connect.addFailedVia(FailedViaReason(failure.get("reason", FailedViaReason.OTHER.value)), _validate_rect(tuple(failure.get("rect", (0, 0, 0, 0))), "failed via rect"), self._resolve_ref(failure.get("net"), resolver))  # type: ignore[arg-type]

    def _check_version(self, data: Mapping[str, Any]) -> None:
        version = int(data.get("version", 1))
        if version != 1:
            raise ValueError(f"unsupported PDN export version: {version}")

    def _ref(self, value: Any) -> Any:
        return None if value is None else _name(value)

    def _resolve_ref(self, value: Any, resolver: Any = None) -> Any:
        if value is None:
            return None
        if resolver is None:
            return value
        return resolver(value)

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


def report_power_grid_summary(pdngen_obj: PdnGen) -> Dict[str, Any]:
    """报告 domain/grid/component/via/sroute/renderer 聚合摘要。"""

    return pdngen_obj.reportSummary()


def report_pdn_via_failures(pdngen_obj: PdnGen, include_locations: bool = True) -> Dict[str, Any]:
    """报告当前 Python PDN 对象树记录的 failed via。"""

    return pdngen_obj.viaFailureReport(include_locations=include_locations)


def report_pdn_setup_issues(pdngen_obj: PdnGen) -> List[Dict[str, str]]:
    """聚合报告 Python 接口层 setup/参数错误，不触发真实 PDN 算法。"""

    return pdngen_obj.reportSetupIssues()


def export_power_grid_config(pdngen_obj: PdnGen) -> Dict[str, Any]:
    """导出可复建的 PDN 配置状态，不包含 runtime shapes/vias。"""

    return pdngen_obj.exportConfig()


def import_power_grid_config(pdngen_obj: PdnGen, data: Mapping[str, Any], resolver: Any = None) -> PdnGen:
    """导入 `export_power_grid_config()` 生成的配置字典。"""

    return pdngen_obj.importConfig(data, resolver=resolver)


def export_power_grid_state(pdngen_obj: PdnGen) -> Dict[str, Any]:
    """导出 PDN 配置和 runtime shape/via/failure 状态。"""

    return pdngen_obj.exportState()


def import_power_grid_state(pdngen_obj: PdnGen, data: Mapping[str, Any], resolver: Any = None) -> PdnGen:
    """导入 `export_power_grid_state()` 生成的状态字典。"""

    return pdngen_obj.importState(data, resolver=resolver)


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
