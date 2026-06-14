"""Export writers (raster/editable/source). One positioned IR, many writers (ADR-001).

PNG + PDF via Chromium (ADR-003) — thin renders of the canonical SVG. Editable writers
(draw.io, PPTX) and source writers (Mermaid, PlantUML) consume the same IR and each return a
``WriteResult`` (path + CapabilityReport).
"""
from __future__ import annotations

from tarseem.export.drawio import write_drawio
from tarseem.export.pdf import svg_to_pdf
from tarseem.export.png import svg_to_png
from tarseem.export.pptx import write_pptx
from tarseem.export.result import WriteResult

__all__ = ["svg_to_png", "svg_to_pdf", "write_drawio", "write_pptx", "WriteResult"]
