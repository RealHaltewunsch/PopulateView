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
            raise PlanError("Mehrdeutige PopulateView-Gruppen oder Layer. Bitte zuerst bereinigen.")
        group = groups[0] if groups else None
        owned = list(group.GetItems()) if group else []
        owned_ids = {uid(i) for i in owned}
        if group and not matches:
            raise PlanError("Ein PopulateView-Layer wurde umbenannt. Originalnamen wiederherstellen.")
        if matches:
            layer = matches[0]
            if any(not isinstance(i, (pcb.PCB_SHAPE, pcb.PCB_TEXT))
                   or i.GetLayer() != layer for i in owned):
                raise PlanError("Die Plugin-Gruppe enthält fremde oder verschobene Objekte.")
            foreign = [i for i in items if i.IsOnLayer(layer) and uid(i) not in owned_ids]
            if foreign:
                raise PlanError("Fremde Objekte auf " + NAMES[side] + ". Bitte auf einen anderen Layer verschieben.")
            if group and not replace:
                raise PlanError("Bestückungsplan existiert bereits. Aktualisieren aktivieren.")
        else:
            available = [l for l in layers if l not in reserved
                         and board.GetLayerName(l) == board.GetStandardLayerName(l)
                         and not any(i.IsOnLayer(l) for i in items)]
            if not available:
                raise PlanError("Kein freier User-Layer verfügbar. Zwei User-Layer freigeben.")
            layer = available[0]
        reserved.add(layer)
        plans[side] = (layer, group, owned)
    return plans


def clone_shape(source, board, layer, centre, mirror):
    shape = pcb.Cast_to_PCB_SHAPE(source.Duplicate())
    shape.SetParent(board)
    shape.SetParentGroup(None)
    if uid(shape) == uid(source):
        raise PlanError("KiCad hat beim Kopieren keine neue Objekt-ID erzeugt.")
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
        items.extend(shapes)
        boxes = [bounds(s) for s in shapes]
        body = (min(b[0] for b in boxes), min(b[1] for b in boxes),
                max(b[2] for b in boxes), max(b[3] for b in boxes))
        bodies.append(body)
        pos = fp.GetPosition()
        anchor = point(2 * centre.x - pos.x if mirror else pos.x, pos.y)
        label = fp.GetReference() or "?"
        if mark_dnp and fp.IsDNP():
            label += " [DNP]"
        records.append((label, anchor, body))

    occupied = []
    bank_y = box.GetY()
    callouts = 0
    for index, (label, anchor, body) in enumerate(records):
        item = text(board, layer, label, anchor)
        # Try body centre, then nearby positions. Test actual KiCad text bounds.
        cx, cy = (body[0] + body[2]) / 2, (body[1] + body[3]) / 2
        positions = [point(cx, cy), point(cx, body[1] - mm(1)),
                     point(cx, body[3] + mm(1))]
        placed = False
        for candidate_index, candidate in enumerate(positions):
            item.SetPosition(candidate)
            bb = bounds(item)
            if candidate_index == 0 and not (bb[0] > body[0] + mm(.2)
                    and bb[2] < body[2] - mm(.2)
                    and bb[1] > body[1] + mm(.2) and bb[3] < body[3] - mm(.2)):
                continue
            obstacles = [b for j, b in enumerate(bodies) if j != index]
            if candidate_index:
                obstacles.append(body)
            if not any(overlap(bb, b, mm(.35)) for b in occupied + obstacles):
                placed = True
                break
        if not placed:
            # Dense layouts get a readable callout column, without shrinking text.
            width = bounds(item)[2] - bounds(item)[0]
            bank_x = max([box.GetRight()] + [b[2] for b in bodies]) + mm(5) + width / 2
            while True:
                item.SetPosition(point(bank_x, bank_y))
                bb = bounds(item)
                if not any(overlap(bb, b, mm(.4)) for b in occupied + bodies):
                    break
                bank_y += mm(2)
            bank_y = bb[3] + mm(2)
            items.append(line(board, layer, anchor, point(bb[0] - mm(.4), item.GetPosition().y)))
            callouts += 1
        occupied.append(bounds(item))
        items.append(item)
    title_y = min([box.GetY()] + [b[1] for b in occupied + bodies]) - mm(3)
    items.append(text(board, layer,
                      "PopulateView - " + ("BOTTOM (component view)" if mirror else "TOP"),
                      point(centre.x, title_y), 1.2))
    return items, len(footprints), callouts


def generate(board, options):
    """Return counts after an all-or-nothing update of selected document layers."""
    version = re.match(r"(\d+)", pcb.Version())
    if not version or int(version.group(1)) not in (9, 10):
        raise PlanError("PopulateView benötigt KiCad 9 oder 10 mit Python-Action-Plugins.")
    if board is None or not board.GetFileName() or not Path(board.GetFileName()).is_file():
        raise PlanError("Bitte die Platine zuerst als .kicad_pcb speichern.")
    if not options.sides or len(set(options.sides)) != len(options.sides) or any(s not in NAMES for s in options.sides):
        raise PlanError("Ungültige Seitenauswahl.")
    edges = [s for s in board.GetDrawings() if isinstance(s, pcb.PCB_SHAPE)
             and s.GetLayer() == pcb.Edge_Cuts]
    for fp in board.GetFootprints():
        edges.extend(s for s in fp.GraphicalItems()
                     if isinstance(s, pcb.PCB_SHAPE) and s.GetLayer() == pcb.Edge_Cuts)
    if not edges:
        raise PlanError("Keine Platinenkontur auf Edge.Cuts gefunden.")
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
                raise PlanError("Dokumentationslayer konnte nicht benannt werden.")
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
                "callouts": staged[s][2]} for s in options.sides}
