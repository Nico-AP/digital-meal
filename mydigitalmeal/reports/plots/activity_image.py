import random
import xml.etree.ElementTree as ET

_CELL_W = 13
_CELL_H = 16
_PADDING = 13
_BORDER = 0
_ANIM_BASE_DELAY = 0.6
_ANIM_DAY_STEP = 0.04
_ANIM_HOUR_STEP = 0.005

_GRADIENT_SETS = [
    ["#89F8C3", "#FFE2A5", "#FF9BBA"],
    ["#FF9BBA", "#FFE2A5", "#89F8C3"],
    ["#46286B", "#FFE3A5", "#FFAAC0"],
    ["#FFAAC0", "#FFAAC0", "#46286B"],
    ["#270167", "#FFE9A7", "#7DFFCB"],
    ["#7DFFCB", "#270167", "#FFE9A7"],
]


def _cell_size(
    hour_idx: int,
    day_idx: int,
    hours: int,
    days: int,
) -> tuple[int, int]:
    w = _CELL_W + (0 if hour_idx == hours - 1 else 1)
    h = _CELL_H + (-1 if day_idx == days - 1 else 1)
    return w, h


def _anim_begin(day_idx: int, hour_idx: int, *, base: float = 0.0) -> str:
    delay = base + day_idx * _ANIM_DAY_STEP + hour_idx * _ANIM_HOUR_STEP
    return f"{delay}s"


def _add_fade(
    parent: ET.Element,
    *,
    from_: str | int,
    to: str | int,
    begin: str,
) -> None:
    ET.SubElement(
        parent,
        "animate",
        {
            "attributeName": "opacity",
            "from": str(from_),
            "to": str(to),
            "dur": "0.1s",
            "begin": begin,
            "fill": "freeze",
        },
    )


def generate_activity_image_svg(  # noqa: C901
    activity_data: list[list[int]],
    *,
    highlight_days: bool = False,
    animated: bool = True,
    color_set: int | None = None,
) -> str:
    """
    Generate an SVG image of activity data.

    Args:
        activity_data: A list of 30 rows (days), each with 24 values (hours).
            1 = activity (black), 0 = no activity (white).
        highlight_days: If True, colors the day rows with activity.
        animated: If True, adds animations.
        color_set: Which color set to use. None picks one at random.

    Returns:
        SVG string.
    """
    days = len(activity_data)
    hours = len(activity_data[0])

    grid_w = hours * _CELL_W
    grid_h = days * _CELL_H
    total_w = grid_w + 2 * _PADDING + 2 * _BORDER
    total_h = grid_h + 2 * _PADDING + 2 * _BORDER

    svg = ET.Element(
        "svg",
        {
            "xmlns": "http://www.w3.org/2000/svg",
            "width": str(total_w),
            "height": str(total_h),
            "viewBox": f"0 0 {total_w} {total_h}",
            "shape-rendering": "crispEdges",
        },
    )

    defs = ET.SubElement(svg, "defs")

    idx = (
        color_set % len(_GRADIENT_SETS)
        if color_set is not None
        else random.randrange(len(_GRADIENT_SETS))  # noqa: S311
    )
    gradient_colors = _GRADIENT_SETS[idx]

    def _add_gradient(grad_id: str, stops: list[str]) -> None:
        grad = ET.SubElement(
            defs,
            "linearGradient",
            {"id": grad_id, "x1": "0", "y1": "0", "x2": "1", "y2": "0.6"},
        )
        for offset, color in zip(("0%", "65%", "100%"), stops, strict=False):
            ET.SubElement(grad, "stop", {"offset": offset, "stop-color": color})

    _add_gradient("cellGradient", gradient_colors)
    _add_gradient("borderGradient", list(reversed(gradient_colors)))

    grid_x = _PADDING + _BORDER
    grid_y = _PADDING + _BORDER

    ET.SubElement(
        svg,
        "rect",
        {
            "x": "0",
            "y": "0",
            "width": str(total_w),
            "height": str(total_h),
            "fill": "url(#cellGradient)",
        },
    )
    ET.SubElement(
        svg,
        "rect",
        {
            "x": str(grid_x),
            "y": str(grid_y),
            "width": str(grid_w),
            "height": str(grid_h),
            "fill": "url(#borderGradient)" if highlight_days else "white",
        },
    )

    # Pass 1: active (black) cells
    for day_idx, day_row in enumerate(activity_data[:days]):
        for hour_idx, activity in enumerate(day_row[:hours]):
            if activity <= 0:
                continue

            x = grid_x + hour_idx * _CELL_W
            y = grid_y + day_idx * _CELL_H
            w, h = _cell_size(hour_idx, day_idx, hours, days)
            show_immediately = not animated or highlight_days

            rect = ET.SubElement(
                svg,
                "rect",
                {
                    "x": str(x),
                    "y": str(y),
                    "width": str(w),
                    "height": str(h),
                    "fill": "black",
                    "opacity": "1" if show_immediately else "0",
                },
            )

            if not show_immediately:
                _add_fade(
                    rect,
                    from_=0,
                    to=1,
                    begin=_anim_begin(day_idx, hour_idx, base=_ANIM_BASE_DELAY),
                )

    # Pass 2: inactive (white) cells on top
    for day_idx, day_row in enumerate(activity_data[:days]):
        row_has_activity = any(v > 0 for v in day_row)
        color_inactive = highlight_days and row_has_activity

        for hour_idx, activity in enumerate(day_row[:hours]):
            if activity > 0:
                continue

            x = grid_x + hour_idx * _CELL_W
            y = grid_y + day_idx * _CELL_H
            w, h = _cell_size(hour_idx, day_idx, hours, days)

            rect = ET.SubElement(
                svg,
                "rect",
                {
                    "x": str(x),
                    "y": str(y),
                    "width": str(w),
                    "height": str(h),
                    "fill": "white",
                },
            )

            if color_inactive and animated:
                _add_fade(
                    rect,
                    from_=1,
                    to=0,
                    begin=_anim_begin(day_idx, hour_idx),
                )

    return ET.tostring(svg, encoding="unicode", xml_declaration=False)
