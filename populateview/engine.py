"""Generate only board-level documentation graphics, with explicit ownership.

All geometry is staged before mutation. Original footprints are never edited.
Bottom graphics are reflected about the board's vertical centre line; labels
are created after reflection so they remain readable in an unmirrored plot.
"""
from dataclasses import dataclass
from pathlib import Path
import re

import pcbnew as pcb


class PlanError(RuntimeError):
    pass


@dataclass
class Options:
    sides: tuple = ("front", "back")
    replace: bool = False
    mark_dnp: bool = True


NAMES = {"front": "PopulateView.Front", "back": "PopulateView.Back"}
GROUPS = {side: "PopulateView/v1/" + side for side in NAMES}


def uid(item):
    return item.m_Uuid.AsString()


def mm(value):
    return pcb.FromMM(value)


def point(x, y):
    return pcb.VECTOR2I(round(x), round(y))


def bounds(item):
    box = item.GetBoundingBox()
    return (box.GetX(), box.GetY(), box.GetRight(), box.GetBottom())


def overlap(a, b, gap=0):
    return (a[0] < b[2] + gap and a[2] > b[0] - gap
            and a[1] < b[3] + gap and a[3] > b[1] - gap)


def user_layers():
    # Layer IDs changed in KiCad 9. Never rely on numeric IDs or ranges.
    return [getattr(pcb, "User_" + str(n)) for n in range(1, 46)
            if hasattr(pcb, "User_" + str(n))]


def board_items(board):
    items = list(board.GetDrawings()) + list(board.GetTracks()) + list(board.Zones())
    for fp in board.GetFootprints():
        items += list(fp.GraphicalItems()) + list(fp.Pads()) + list(fp.Zones())
        items += [fp.Reference(), fp.Value()]
    return items


def layer_plan(board, sides, replace):
    """Reserve empty default-named user layers; never adopt foreign contents."""
    items = board_items(board)
    layers = user_layers()
    plans = {}
    reserved = set()
    for side in sides:
        groups = [g for g in board.Groups() if g.GetName() == GROUPS[side]]
        matches = [l for l in layers if board.GetLayerName(l) == NAMES[side]]
        if len(groups) > 1 or len(matches) > 1:
            raise PlanError("Ambiguous PopulateView groups or layers. Please resolve duplicates first.")
        group = groups[0] if groups else None
        owned = list(group.GetItems()) if group else []
        owned_ids = {uid(i) for i in owned}
        if group and not matches:
            raise PlanError("A PopulateView layer was renamed. Please restore its original name.")
        if matches:
            layer = matches[0]
            if any(not isinstance(i, (pcb.PCB_SHAPE, pcb.PCB_TEXT))
                   or i.GetLayer() != layer for i in owned):
                raise PlanError("The plugin group contains unrelated objects or objects moved to another layer.")
            foreign = [i for i in items if i.IsOnLayer(layer) and uid(i) not in owned_ids]
            if foreign:
                raise PlanError("Unrelated objects on " + NAMES[side] + ". Please move them to another layer.")
            if group and not replace:
                raise PlanError("An assembly drawing already exists. Enable the update / replace option.")
        else:
            available = [l for l in layers if l not in reserved
                         and board.GetLayerName(l) == board.GetStandardLayerName(l)
                         and not any(i.IsOnLayer(l) for i in items)]
            if not available:
                raise PlanError("No free user layer is available. Free up user layers for the selected sides.")
            layer = available[0]
        reserved.add(layer)
        plans[side] = (layer, group, owned)
    return plans


def clone_shape(source, board, layer, centre, mirror):
    shape = pcb.Cast_to_PCB_SHAPE(source.Duplicate())
    shape.SetParent(board)
    shape.SetParentGroup(None)
    if uid(shape) == uid(source):
        raise PlanError("KiCad did not assign a new object ID when copying a shape.")
    shape.SetLayer(layer)
    shape.SetLocked(False)
    if mirror:
        shape.Mirror(centre, pcb.FLIP_DIRECTION_LEFT_RIGHT)
    if shape.GetWidth() <= 0:
        shape.SetWidth(mm(0.15))
    return shape


def line(board, layer, start, end):
    shape = pcb.PCB_SHAPE(board)
    shape.SetShape(pcb.SHAPE_T_SEGMENT)
    shape.SetStart(start)
    shape.SetEnd(end)
    shape.SetWidth(mm(0.15))
    shape.SetLayer(layer)
    return shape


def text(board, layer, value, position, height=1.0):
    item = pcb.PCB_TEXT(board)
    item.SetText(value)
    item.SetPosition(position)
    item.SetTextSize(point(mm(height), mm(height)))
    item.SetTextThickness(mm(0.15))
    item.SetTextAngle(pcb.EDA_ANGLE(0, pcb.DEGREES_T))
    item.SetMirrored(False)
    item.SetLayer(layer)
    item.SetVisible(True)
    item.SetHorizJustify(pcb.GR_TEXT_H_ALIGN_CENTER)
    item.SetVertJustify(pcb.GR_TEXT_V_ALIGN_CENTER)
    return item


def simplify_conflicting_details(shapes, label, anchor, angle):
    """Remove interior decoration only inside a verified rectangular outline.

    Work on detached documentation copies in footprint coordinates. Recognize
    native rectangles and complete rectangles assembled from line segments.
    On conflict remove the whole interior decoration, avoiding partial symbols.
    Unknown/open contours are kept intact rather than guessed from their bbox.
    """
    local = []
    for source in shapes:
        shape = pcb.Cast_to_PCB_SHAPE(source.Duplicate())
        shape.Rotate(anchor, pcb.EDA_ANGLE(-angle, pcb.DEGREES_T))
        local.append(shape)
    text_copy = pcb.Cast_to_PCB_TEXT(label.Duplicate())
    text_copy.Rotate(anchor, pcb.EDA_ANGLE(-angle, pcb.DEGREES_T))
    label_box = bounds(text_copy)
    rectangles = []
    segments = []
    tolerance = 10  # 10 nm: only compensate for integer rotation rounding.
    for shape in local:
        if shape.GetShape() == pcb.SHAPE_T_RECT:
            a, b = shape.GetStart(), shape.GetEnd()
            rectangles.append((min(a.x, b.x), min(a.y, b.y), max(a.x, b.x), max(a.y, b.y)))
        elif shape.GetShape() == pcb.SHAPE_T_SEGMENT:
            segments.append((shape.GetStart(), shape.GetEnd()))
    if segments:
        left = min(min(a.x, b.x) for a, b in segments)
        right = max(max(a.x, b.x) for a, b in segments)
        top = min(min(a.y, b.y) for a, b in segments)
        bottom = max(max(a.y, b.y) for a, b in segments)

        def covered(axis, fixed, start, end):
            intervals = []
            for a, b in segments:
                av, bv = (a.x, b.x) if axis == "x" else (a.y, b.y)
                if abs(av - fixed) <= tolerance and abs(bv - fixed) <= tolerance:
                    u, v = (a.y, b.y) if axis == "x" else (a.x, b.x)
                    intervals.append((min(u, v), max(u, v)))
            cursor = start
            for u, v in sorted(intervals):
                if u > cursor + tolerance:
                    return False
                cursor = max(cursor, v)
            return cursor >= end - tolerance

        if (right > left and bottom > top
                and covered("x", left, top, bottom) and covered("x", right, top, bottom)
                and covered("y", top, left, right) and covered("y", bottom, left, right)):
            rectangles.append((left, top, right, bottom))
    removable = set()
    for rect in rectangles:
        interior = []
        for index, shape in enumerate(local):
            bb = bounds(shape)
            if (bb[0] > rect[0] + tolerance and bb[1] > rect[1] + tolerance
                    and bb[2] < rect[2] - tolerance and bb[3] < rect[3] - tolerance):
                interior.append(index)
        if any(overlap(bounds(local[index]), label_box) for index in interior):
            removable.update(interior)
    return [shape for index, shape in enumerate(shapes) if index not in removable]


def fit_label(board, layer, value, shapes, anchor, angle):
    """Fit measured stroke text in the footprint-oriented outline envelope.

    Measure in footprint coordinates, not the enlarged world-axis bounding box
    of a rotated component. Both text length and stroke width participate.
    """
    local = []
    for shape in shapes:
        copy = pcb.Cast_to_PCB_SHAPE(shape.Duplicate())
        copy.Rotate(anchor, pcb.EDA_ANGLE(-angle, pcb.DEGREES_T))
        local.append(bounds(copy))
    body = (min(b[0] for b in local), min(b[1] for b in local),
            max(b[2] for b in local), max(b[3] for b in local))
    margin = max(s.GetWidth() for s in shapes) + round(
        .08 * min(body[2] - body[0], body[3] - body[1]))
    inner = (body[0] + margin, body[1] + margin,
             body[2] - margin, body[3] - margin)
    if inner[2] <= inner[0] or inner[3] <= inner[1]:
        raise PlanError("No usable interior area for label: " + value)
    centre = point((inner[0] + inner[2]) / 2, (inner[1] + inner[3]) / 2)
    item = text(board, layer, value, centre)
    # Along either footprint axis, choose the largest size (up to 5 mm).
    best = None
    for direction in (0, 90):
        # Normalize final orientation to upright before measuring.
        final_angle = (angle + direction + 90) % 180 - 90
        local_angle = final_angle - angle
        item.SetTextAngle(pcb.EDA_ANGLE(local_angle, pcb.DEGREES_T))
        low, high = 1, mm(5)
        winner = 0
        while low <= high:
            height = (low + high) // 2
            item.SetTextSize(point(height, height))
            item.SetTextThickness(max(1, round(height * .12)))
            bb = bounds(item)
            if bb[2] - bb[0] <= inner[2] - inner[0] - 4 and bb[3] - bb[1] <= inner[3] - inner[1] - 4:
                winner = height
                low = height + 1
            else:
                high = height - 1
        if best is None or winner > best[0]:
            best = (winner, local_angle)
    height, local_angle = best
    if not height:
        raise PlanError("Text does not fit even at the smallest size: " + value)
    item.SetTextSize(point(height, height))
    item.SetTextThickness(max(1, round(height * .12)))
    item.SetTextAngle(pcb.EDA_ANGLE(local_angle, pcb.DEGREES_T))
    bb = bounds(item)
    item.SetPosition(point(centre.x + centre.x - (bb[0] + bb[2]) / 2,
                           centre.y + centre.y - (bb[1] + bb[3]) / 2))
    item.Rotate(anchor, pcb.EDA_ANGLE(angle, pcb.DEGREES_T))
    return item


def stage_side(board, side, layer, edges, mark_dnp):
    box = board.GetBoardEdgesBoundingBox()
    centre = box.GetCenter()
    mirror = side == "back"
    items = [clone_shape(s, board, layer, centre, mirror) for s in edges]
    footprints = [fp for fp in board.GetFootprints() if fp.IsFlipped() == mirror]
    footprints.sort(key=lambda f: f.GetReference())
    bodies = []
    records = []
    for fp in footprints:
        candidates = list(fp.GraphicalItems())
        outlines = []
        # Fabrication outlines describe the body. Courtyard/silk are fallbacks.
        for source_layer in ((pcb.B_Fab if mirror else pcb.F_Fab),
                             (pcb.B_CrtYd if mirror else pcb.F_CrtYd),
                             (pcb.B_SilkS if mirror else pcb.F_SilkS)):
            outlines = [s for s in candidates if isinstance(s, pcb.PCB_SHAPE)
                        and s.GetLayer() == source_layer]
            if outlines:
                break
        shapes = [clone_shape(s, board, layer, centre, mirror) for s in outlines]
        if not shapes:
            # No library outline: document the physical extent, excluding fields.
            bb = fp.GetBoundingBox(False, False)
            shape = pcb.PCB_SHAPE(board)
            shape.SetShape(pcb.SHAPE_T_RECT)
            shape.SetStart(bb.GetOrigin())
            shape.SetEnd(bb.GetEnd())
            shape.SetWidth(mm(0.15))
            shape.SetLayer(layer)
            if mirror:
                shape.Mirror(centre, pcb.FLIP_DIRECTION_LEFT_RIGHT)
            shapes = [shape]
        boxes = [bounds(s) for s in shapes]
        body = (min(b[0] for b in boxes), min(b[1] for b in boxes),
                max(b[2] for b in boxes), max(b[3] for b in boxes))
        bodies.append(body)
        pos = fp.GetPosition()
        anchor = point(2 * centre.x - pos.x if mirror else pos.x, pos.y)
        label = fp.GetReference() or "?"
        if mark_dnp and fp.IsDNP():
            label += " [DNP]"
        angle = fp.GetOrientationDegrees() * (-1 if mirror else 1)
        records.append((label, anchor, shapes, angle))

    occupied = []
    small_labels = 0
    for label, anchor, shapes, angle in records:
        item = fit_label(board, layer, label, shapes, anchor, angle)
        simplified = simplify_conflicting_details(shapes, item, anchor, angle)
        if len(simplified) != len(shapes):
            item = fit_label(board, layer, label, simplified, anchor, angle)
        items.extend(simplified)
        small_labels += item.GetTextHeight() < mm(.5)
        occupied.append(bounds(item))
        items.append(item)
    title_y = min([box.GetY()] + [b[1] for b in occupied + bodies]) - mm(3)
    items.append(text(board, layer,
                      "PopulateView - " + ("BOTTOM (component view)" if mirror else "TOP"),
                      point(centre.x, title_y), 1.2))
    return items, len(footprints), small_labels


def generate(board, options):
    """Return counts after an all-or-nothing update of selected document layers."""
    version = re.match(r"(\d+)", pcb.Version())
    if not version or int(version.group(1)) not in (9, 10):
        raise PlanError("PopulateView requires KiCad 9 or 10 with Python Action Plugins.")
    if board is None or not board.GetFileName() or not Path(board.GetFileName()).is_file():
        raise PlanError("Please save the board as a .kicad_pcb file first.")
    if not options.sides or len(set(options.sides)) != len(options.sides) or any(s not in NAMES for s in options.sides):
        raise PlanError("Invalid side selection.")
    edges = [s for s in board.GetDrawings() if isinstance(s, pcb.PCB_SHAPE)
             and s.GetLayer() == pcb.Edge_Cuts]
    for fp in board.GetFootprints():
        edges.extend(s for s in fp.GraphicalItems()
                     if isinstance(s, pcb.PCB_SHAPE) and s.GetLayer() == pcb.Edge_Cuts)
    if not edges:
        raise PlanError("No board outline found on Edge.Cuts.")
    plans = layer_plan(board, options.sides, options.replace)
    staged = {s: stage_side(board, s, plans[s][0], edges, options.mark_dnp) for s in options.sides}
    enabled = pcb.LSET(board.GetEnabledLayers())
    visible = pcb.LSET(board.GetVisibleLayers())
    names = {l: board.GetLayerName(l) for l, _, _ in plans.values()}
    added, removed, detached = [], [], []
    try:
        new_enabled, new_visible = pcb.LSET(enabled), pcb.LSET(visible)
        for layer, _, _ in plans.values():
            new_enabled.addLayer(layer)
            new_visible.addLayer(layer)
        board.SetEnabledLayers(new_enabled)
        board.SetVisibleLayers(new_visible)
        for side, (layer, old_group, old_items) in plans.items():
            if not board.SetLayerName(layer, NAMES[side]):
                raise PlanError("Could not name the documentation layer.")
            if old_group:
                for item in old_items:
                    old_group.RemoveItem(item)
                    detached.append((old_group, item))
                    board.Remove(item)
                    removed.append(item)
                board.Remove(old_group)
                removed.append(old_group)
            group = pcb.PCB_GROUP(board)
            group.SetName(GROUPS[side])
            board.Add(group)
            added.append(group)
            for item in staged[side][0]:
                board.Add(item)
                added.append(item)
                group.AddItem(item)
        board.SetModified()
    except Exception:
        for item in reversed(added):
            parent = item.GetParentGroup()
            if parent:
                parent.RemoveItem(item)
            board.Remove(item)
        for item in reversed(removed):
            board.Add(item)
        for group, item in detached:
            group.AddItem(item)
        for layer, name in names.items():
            board.SetLayerName(layer, name)
        board.SetEnabledLayers(enabled)
        board.SetVisibleLayers(visible)
        raise
    return {s: {"layer": plans[s][0], "footprints": staged[s][1],
                "small_labels": staged[s][2]} for s in options.sides}
