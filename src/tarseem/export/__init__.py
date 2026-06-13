"""Export writers (raster/editable/source). One positioned IR, many writers (ADR-001).

PNG via Chromium (ADR-003). Editable writers (draw.io, PPTX) and source writers (Mermaid,
PlantUML) consume the same IR and each return a ``WriteResult`` (path + CapabilityReport).
"""
from __future__ import annotations

from tarseem.export.drawio import write_drawio
from tarseem.export.png import svg_to_png
from tarseem.export.result import WriteResult

__all__ = ["svg_to_png", "write_drawio", "WriteResult"]
