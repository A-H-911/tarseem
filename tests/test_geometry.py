"""Unit tests for tarseem.geometry — the shared chrome box-math (one source of truth for the
SVG renderers + the draw.io/PPTX writers). Values are pinned so a future change to a shared
function is caught here, not only by the corpus/visual guards.
"""
from __future__ import annotations

from tarseem import geometry as g
from tarseem.model.ir import Label, LaneBand, PhaseBand, PositionedDiagram


def _band(x, y, w, h) -> LaneBand:
    return LaneBand(id="L", label=Label(text="lane"), x=x, y=y, width=w, height=h, hue={})


def _diagram(lanes, *, width=900.0, height=300.0, phases=(), lane_groups=()) -> PositionedDiagram:
    return PositionedDiagram(
        width=width, height=height, nodes=(), edges=(), diagram_type="swimlane",
        lanes=tuple(lanes), phases=tuple(phases), lane_groups=tuple(lane_groups),
    )


# --- chip_rect ------------------------------------------------------------------------------
def test_chip_rect_horizontal_ltr():
    # w = LABEL_W - 2*CHIP_INSET = 144; x = band.x + CHIP_INSET; y centred on the band; h = CHIP_H
    got = g.chip_rect(_band(20, 100, 800, 120), rtl=False, vertical=False)
    assert got == (28.0, 132.0, 144.0, 56.0)


def test_chip_rect_horizontal_rtl_flips_to_right():
    # x = band.x + band.width - w - CHIP_INSET = 20 + 800 - 144 - 8 = 668
    got = g.chip_rect(_band(20, 100, 800, 120), rtl=True, vertical=False)
    assert got == (668.0, 132.0, 144.0, 56.0)


def test_chip_rect_vertical():
    # w = band.width - 2*CHIP_INSET = 134; y = band.y + (V_HEADER - V_CHIP_H)/2 = 58; h = V_CHIP_H
    got = g.chip_rect(_band(20, 50, 150, 400), rtl=False, vertical=True)
    assert got == (28.0, 58.0, 134.0, 48.0)


# --- title_bar_box --------------------------------------------------------------------------
def test_title_bar_box_no_phases_stops_at_first_lane():
    d = _diagram([_band(20, 100, 800, 120)], height=300.0)
    # x=20; w=800; top=height-(y+h)=80; bottom=lanes[0].y=100 -> h=20
    assert g.title_bar_box(d) == (20.0, 80.0, 800.0, 20.0)


def test_title_bar_box_with_phases_stops_at_phase_top():
    phase = PhaseBand(id="p", label=Label(text="P"), x=180, y=92, width=600, height=34)
    d = _diagram([_band(20, 100, 800, 120)], height=300.0, phases=[phase])
    # bottom = phases[0].y = 92 -> h = 92 - 80 = 12
    assert g.title_bar_box(d) == (20.0, 80.0, 800.0, 12.0)


# --- swimlane_chrome ------------------------------------------------------------------------
def test_swimlane_chrome_horizontal_ltr():
    d = _diagram([_band(20, 100, 800, 120)], width=900.0)
    c = g.swimlane_chrome(d, rtl=False, vertical=False)
    # sep_x = lanes[0].x + LABEL_W = 180; spans lane top..bottom
    assert (c.lane_top, c.lane_bottom) == (100.0, 220.0)
    assert c.actor_p1 == (180.0, 100.0) and c.actor_p2 == (180.0, 220.0)


def test_swimlane_chrome_horizontal_rtl():
    d = _diagram([_band(20, 100, 800, 120)], width=900.0)
    c = g.swimlane_chrome(d, rtl=True, vertical=False)
    # sep_x = width - lanes[0].x - LABEL_W = 900 - 20 - 160 = 720
    assert c.actor_p1 == (720.0, 100.0) and c.actor_p2 == (720.0, 220.0)


def test_swimlane_chrome_vertical_actor_separator_is_horizontal():
    c = g.swimlane_chrome(_diagram([_band(20, 50, 150, 400)]), rtl=False, vertical=True)
    # sep_y = lanes[0].y + V_HEADER = 114; runs left..right across the columns
    assert c.actor_p1 == (20.0, 114.0) and c.actor_p2 == (170.0, 114.0)
