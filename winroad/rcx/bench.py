"""Bench and pattern configuration helpers for rcx."""

from __future__ import annotations

from .common import _parse_number_list
from .options import BenchWiresOptions, PatternOptions, extMainOptions


def bench_to_main_options(owner: object, bwo: BenchWiresOptions) -> extMainOptions:
    opt = extMainOptions(
        _overDist=bwo.over_dist,
        _underDist=bwo.under_dist,
        _met_cnt=bwo.met_cnt,
        _met=bwo.met,
        _underMet=bwo.under_met,
        _overMet=bwo.over_met,
        _wireCnt=bwo.cnt,
        _topDir=bwo.dir,
        _name=bwo.block,
        _wTable=bwo.w_list if bwo.multiple_widths else bwo.w,
        _sTable=bwo.s_list,
        _thTable=bwo.th_list if bwo.ddd else bwo.th,
        _dTable=bwo.d,
        _default_lef_rules=bwo.default_lef_rules,
        _nondefault_lef_rules=bwo.nondefault_lef_rules,
        _multiple_widths=bwo.multiple_widths,
        _over=bwo.Over,
        _overUnder=bwo.over_under,
        _diag=1 if bwo.diag else 0,
        _db_only=bwo.db_only,
        _gen_def_patterns=bwo.gen_def_patterns,
        _res_patterns=bwo.resPatterns,
        _len=bwo.len,
        _tech=getattr(owner, "_tech", None),
        _block=getattr(owner, "_block", None),
        _rcModel=owner.getRCModel() if hasattr(owner, "getRCModel") else None,
        _layerCnt=bwo.met_cnt,
        _v1=bwo.v1,
    )
    opt._widthTable = _parse_number_list(opt._wTable)
    opt._spaceTable = _parse_number_list(opt._sTable)
    opt._thicknessTable = _parse_number_list(opt._thTable)
    opt._densityTable = _parse_number_list(opt._dTable)
    opt._gridTable = _parse_number_list(bwo.grid_list)
    return opt


def pattern_to_main_options(owner: object, po: PatternOptions) -> extMainOptions:
    opt = extMainOptions(
        _overDist=po.over_dist,
        _underDist=po.under_dist,
        _met_cnt=po.met_cnt,
        _met=po.met,
        _underMet=po.under_met,
        _overMet=po.over_met,
        _wireCnt=po.wire_cnt,
        _topDir=po.dir,
        _name=po.name,
        _wTable=po.width or "1",
        _sTable=po.spacing or "1",
        _default_lef_rules=po.default_lef_rules,
        _nondefault_lef_rules=po.nondefault_lef_rules,
        _over=po.over,
        _overUnder=po.over_under,
        _diag=1 if po.diag else 0,
        _len=po.len,
        _tech=getattr(owner, "_tech", None),
        _block=getattr(owner, "_block", None),
        _rcModel=owner.getRCModel() if hasattr(owner, "getRCModel") else None,
        _layerCnt=po.met_cnt,
    )
    opt._widthTable = _parse_number_list(opt._wTable)
    opt._spaceTable = _parse_number_list(opt._sTable)
    opt._gridTable = _parse_number_list(po.grid_list)
    return opt
