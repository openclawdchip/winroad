"""Corner state for rcx process and scaled corners."""

from __future__ import annotations

from dataclasses import dataclass

@dataclass
class extCorner:
    """对应 `extCorner`，描述 process corner 和派生缩放 corner。"""

    _name: str = ""
    _model: int = -1
    _extDbIndex: int = -1
    _scaledCornerIdx: int = -1
    _resFactor: float = 1.0
    _ccFactor: float = 1.0
    _gndcFactor: float = 1.0

