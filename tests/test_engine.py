"""Integration tests using real pcbnew objects, serialization and Gerber plotting."""
import os
os.environ["POPULATEVIEW_HEADLESS"] = "1"
import tempfile
import unittest
from pathlib import Path

import wx
APP = wx.App(False)
import pcbnew as p
from populateview.engine import (Options, PlanError, generate, mm, point, NAMES,
                                uid, fit_label, bounds, simplify_conflicting_details)


def fixture(path):
    board = p.BOARD()
    board.SetFileName(str(path))
    edge = p.PCB_SHAPE(board)
    edge.SetShape(p.SHAPE_T_RECT)
    edge.SetStart(point(mm(10), mm(10)))
    edge.SetEnd(point(mm(60), mm(40)))
    edge.SetLayer(p.Edge_Cuts)
    edge.SetWidth(mm(.05))
    board.Add(edge)
    for ref, x, y, back, dnp, outline in [
            ("R1", 20, 20, False, False, True),
            ("U1", 30, 25, False, True, True),
            ("C1", 20, 20, True, False, True),
            ("R2", 30, 25, True, True, True),
            ("J1", 40, 30, False, False, False)]:
        fp = p.FOOTPRINT(board)
        fp.SetReference(ref)
        fp.SetPosition(point(mm(x), mm(y)))
        fp.SetDNP(dnp)
        board.Add(fp)
        pad = p.PAD(fp)
        pad.SetSize(point(mm(1), mm(1)))
        pad.SetPosition(fp.GetPosition())
        fp.Add(pad)
        if outline:
            shape = p.PCB_SHAPE(fp)
            shape.SetShape(p.SHAPE_T_RECT)
            shape.SetStart(point(mm(x-2), mm(y-1.5)))
            shape.SetEnd(point(mm(x+2), mm(y+1.5)))
            shape.SetLayer(p.F_Fab)
            shape.SetWidth(mm(.1))
            fp.Add(shape)
            if ref == "R1":
                # Internal diode-like symbol on Fab and real silkscreen.
                for source_layer in (p.F_Fab, p.F_SilkS):
                    for start, end in [((-1, -.7), (1, 0)), ((1, 0), (-1, .7)),
                                       ((-1, .7), (-1, -.7)), ((1, -.7), (1, .7))]:
                        detail = p.PCB_SHAPE(fp)
                        detail.SetShape(p.SHAPE_T_SEGMENT)
                        detail.SetStart(point(mm(x + start[0]), mm(y + start[1])))
                        detail.SetEnd(point(mm(x + end[0]), mm(y + end[1])))
                        detail.SetLayer(source_layer)
                        detail.SetWidth(mm(.1))
                        fp.Add(detail)
        silk = p.PCB_SHAPE(fp)
        silk.SetShape(p.SHAPE_T_CIRCLE)
        silk.SetCenter(fp.GetPosition())
        silk.SetEnd(point(mm(x+2), mm(y)))
        silk.SetLayer(p.F_SilkS)
        silk.SetWidth(mm(.12))
        if outline:
            fp.Add(silk)
        if back:
            fp.Flip(fp.GetPosition(), p.FLIP_DIRECTION_LEFT_RIGHT)
    track = p.PCB_TRACK(board)
    track.SetStart(point(mm(20), mm(20)))
    track.SetEnd(point(mm(25), mm(20)))
    track.SetWidth(mm(.25))
    track.SetLayer(p.F_Cu)
    board.Add(track)
    p.SaveBoard(str(path), board)
    return board


class EngineTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.path = Path(self.temp.name) / "fixture.kicad_pcb"
        self.board = fixture(self.path)

    def tearDown(self):
        self.temp.cleanup()

    def test_generate_update_reload_plot(self):
        original = self.path.read_text()
        result = generate(self.board, Options())
        self.assertEqual(result["front"]["footprints"], 3)
        self.assertEqual(result["back"]["footprints"], 2)
        count = len(list(self.board.GetDrawings()))
        with self.assertRaises(PlanError):
            generate(self.board, Options())
        generate(self.board, Options(replace=True))
        self.assertEqual(count, len(list(self.board.GetDrawings())))
        labels = [i for i in self.board.GetDrawings() if isinstance(i, p.PCB_TEXT)]
        self.assertEqual(sum("[DNP]" in i.GetText() for i in labels), 2)
        self.assertTrue(all(not i.IsMirrored() for i in labels))
        back_c = next(i for i in labels if i.GetText() == "C1")
        self.assertAlmostEqual(p.ToMM(back_c.GetPosition().x), 50, places=2)
        p.SaveBoard(str(self.path), self.board)
        reloaded = p.LoadBoard(str(self.path))
        generate(reloaded, Options(replace=True))
        for side, info in result.items():
            plot = p.PLOT_CONTROLLER(reloaded)
            opts = plot.GetPlotOptions()
            opts.SetOutputDirectory(self.temp.name)
            opts.SetMirror(False)
            opts.SetPlotFrameRef(False)
            plot.SetLayer(info["layer"])
            self.assertTrue(plot.OpenPlotfile(side, p.PLOT_FORMAT_GERBER, "PopulateView"))
            self.assertTrue(plot.PlotLayer())
            plot.ClosePlot()
        gerbers = list(Path(self.temp.name).glob("*.gbr"))
        self.assertEqual(len(gerbers), 2)
        self.assertTrue(all("M02*" in f.read_text() and "D01*" in f.read_text() for f in gerbers))
        # Remove precisely the added groups/graphics and restore layer settings:
        # the entire original serialized layout must then be byte identical.
        for group in list(self.board.Groups()):
            for item in list(group.GetItems()):
                group.RemoveItem(item)
                self.board.Remove(item)
            self.board.Remove(group)
        for info in result.values():
            self.board.SetLayerName(info["layer"], self.board.GetStandardLayerName(info["layer"]))
        p.SaveBoard(str(self.path), self.board)
        self.assertEqual(original, self.path.read_text())

    def test_foreign_objects_are_preserved(self):
        result = generate(self.board, Options())
        item = p.PCB_TEXT(self.board)
        item.SetText("User notes")
        item.SetLayer(result["front"]["layer"])
        self.board.Add(item)
        before = {uid(i) for i in self.board.GetDrawings()}
        with self.assertRaises(PlanError):
            generate(self.board, Options(replace=True))
        self.assertEqual(before, {uid(i) for i in self.board.GetDrawings()})

    def test_single_side_dnp_off(self):
        generate(self.board, Options(("back",), mark_dnp=False))
        self.assertEqual(len(list(self.board.Groups())), 1)
        self.assertFalse(any("DNP" in i.GetText() for i in self.board.GetDrawings() if isinstance(i, p.PCB_TEXT)))

    def test_unsaved_and_missing_edges(self):
        with self.assertRaises(PlanError):
            generate(p.BOARD(), Options())
        for shape in list(self.board.GetDrawings()):
            self.board.Remove(shape)
        with self.assertRaises(PlanError):
            generate(self.board, Options())

    def test_cancelled_staging_does_not_mutate(self):
        from unittest.mock import patch
        with patch("populateview.engine.stage_side", side_effect=RuntimeError("injected")):
            with self.assertRaises(RuntimeError):
                generate(self.board, Options())
        p.SaveBoard(str(self.path), self.board)
        self.assertEqual(len(list(self.board.Groups())), 0)

    def test_transaction_rollback(self):
        from unittest.mock import patch
        generate(self.board, Options())
        p.SaveBoard(str(self.path), self.board)
        before = self.path.read_text()
        original_add = p.BOARD.Add
        calls = [0]

        def fail_once(board, item, *args):
            calls[0] += 1
            if calls[0] == 4:
                raise RuntimeError("injected during commit")
            return original_add(board, item, *args)

        with patch.object(p.BOARD, "Add", fail_once):
            with self.assertRaises(RuntimeError):
                generate(self.board, Options(replace=True))
        p.SaveBoard(str(self.path), self.board)
        self.assertEqual(before, self.path.read_text())

    def test_dialog_to_generation(self):
        from unittest.mock import patch
        from populateview.plugin import PopulateViewPlugin, PlanDialog
        with patch.object(PlanDialog, "ShowModal", return_value=wx.ID_OK), \
                patch("pcbnew.GetBoard", return_value=self.board), \
                patch("pcbnew.Refresh"), patch("populateview.plugin.show_message") as message:
            plugin = PopulateViewPlugin()
            plugin.Run()
        self.assertEqual(len(list(self.board.Groups())), 2)
        self.assertIn("Drawings generated", message.call_args[0][0])

    def test_front_update_preserves_back(self):
        generate(self.board, Options())
        back = next(g for g in self.board.Groups() if g.GetName().endswith("/back"))
        ids = {uid(i) for i in back.GetItems()}
        generate(self.board, Options(("front",), replace=True))
        self.assertEqual(ids, {uid(i) for i in back.GetItems()})

    def fitted(self, value, width, height, angle=0):
        anchor = point(mm(20), mm(20))
        shape = p.PCB_SHAPE(self.board)
        shape.SetShape(p.SHAPE_T_RECT)
        shape.SetStart(point(anchor.x - mm(width / 2), anchor.y - mm(height / 2)))
        shape.SetEnd(point(anchor.x + mm(width / 2), anchor.y + mm(height / 2)))
        shape.SetWidth(mm(.01))
        shape.Rotate(anchor, p.EDA_ANGLE(angle, p.DEGREES_T))
        label = fit_label(self.board, p.User_1, value, [shape], anchor, angle)
        # Inverse transform the real rendered text to check the physical body.
        local = p.Cast_to_PCB_TEXT(label.Duplicate())
        local.Rotate(anchor, p.EDA_ANGLE(-angle, p.DEGREES_T))
        bb = bounds(local)
        self.assertGreater(bb[0], anchor.x - mm(width / 2))
        self.assertLess(bb[2], anchor.x + mm(width / 2))
        self.assertGreater(bb[1], anchor.y - mm(height / 2))
        self.assertLess(bb[3], anchor.y + mm(height / 2))
        self.assertFalse(label.IsMirrored())
        return label

    def test_tiny_and_rotated_labels_stay_inside(self):
        for size in ((.6, .3), (.2, .1), (20, 10)):
            for angle in (0, 45, 90, -37, 180):
                for value in ("R1", "R12345678", "R12345678 [DNP]"):
                    with self.subTest(size=size, angle=angle, value=value):
                        self.fitted(value, *size, angle)

    def test_size_depends_on_body_and_text_length(self):
        small = self.fitted("R1", .6, .3)
        large = self.fitted("R1", 20, 10)
        long = self.fitted("R12345678 [DNP]", .6, .3)
        self.assertGreater(large.GetTextHeight(), small.GetTextHeight())
        self.assertLess(long.GetTextHeight(), small.GetTextHeight())
        self.assertLess(long.GetTextThickness(), small.GetTextThickness())

    def test_adaptive_sizes_survive_save_and_gerber(self):
        label = self.fitted("R12345678 [DNP]", .6, .3, -37)
        self.board.Add(label)
        p.SaveBoard(str(self.path), self.board)
        board = p.LoadBoard(str(self.path))
        saved = next(i for i in board.GetDrawings() if isinstance(i, p.PCB_TEXT))
        self.assertEqual(label.GetTextSize(), saved.GetTextSize())
        self.assertEqual(label.GetTextThickness(), saved.GetTextThickness())
        plot = p.PLOT_CONTROLLER(board)
        plot.GetPlotOptions().SetOutputDirectory(self.temp.name)
        plot.SetLayer(p.User_1)
        self.assertTrue(plot.OpenPlotfile("tiny", p.PLOT_FORMAT_GERBER, "Adaptive text"))
        self.assertTrue(plot.PlotLayer())
        plot.ClosePlot()
        self.assertIn("D01*", next(Path(self.temp.name).glob("*.gbr")).read_text())

    def test_internal_symbol_removed_from_generated_plan_only(self):
        fp = next(f for f in self.board.GetFootprints() if f.GetReference() == "R1")
        source_ids = {uid(s) for s in fp.GraphicalItems()}
        result = generate(self.board, Options())
        generated = [s for s in self.board.GetDrawings() if isinstance(s, p.PCB_SHAPE)
                     and s.GetLayer() == result["front"]["layer"]
                     and bounds(s)[0] > mm(17) and bounds(s)[2] < mm(23)
                     and bounds(s)[1] > mm(18) and bounds(s)[3] < mm(22)]
        self.assertEqual(len(generated), 1)
        self.assertEqual(generated[0].GetShape(), p.SHAPE_T_RECT)
        self.assertEqual(source_ids, {uid(s) for s in fp.GraphicalItems()})

    def test_segment_outline_rotation_and_mirroring(self):
        anchor = point(mm(20), mm(20))
        for angle in (0, 37, 90, 180):
            for mirror in (False, True):
                with self.subTest(angle=angle, mirror=mirror):
                    shapes = []
                    for start, end in [((-2, -1), (2, -1)), ((2, -1), (2, 1)),
                                       ((2, 1), (-2, 1)), ((-2, 1), (-2, -1)),
                                       ((-.6, -.5), (.6, 0)), ((.6, 0), (-.6, .5)),
                                       ((-.6, .5), (-.6, -.5)), ((.6, -.5), (.6, .5))]:
                        shape = p.PCB_SHAPE(self.board)
                        shape.SetShape(p.SHAPE_T_SEGMENT)
                        shape.SetStart(point(anchor.x + mm(start[0]), anchor.y + mm(start[1])))
                        shape.SetEnd(point(anchor.x + mm(end[0]), anchor.y + mm(end[1])))
                        shape.SetWidth(mm(.05))
                        shape.Rotate(anchor, p.EDA_ANGLE(angle, p.DEGREES_T))
                        if mirror:
                            shape.Mirror(anchor, p.FLIP_DIRECTION_LEFT_RIGHT)
                        shapes.append(shape)
                    orientation = -angle if mirror else angle
                    label = fit_label(self.board, p.User_1, "D3", shapes, anchor, orientation)
                    kept = simplify_conflicting_details(shapes, label, anchor, orientation)
                    self.assertEqual([uid(s) for s in kept], [uid(s) for s in shapes[:4]])
                    # An open outline is not sufficient evidence to delete details.
                    open_shapes = shapes[1:]
                    self.assertEqual(len(simplify_conflicting_details(
                        open_shapes, label, anchor, orientation)), len(open_shapes))


if __name__ == "__main__":
    unittest.main()
