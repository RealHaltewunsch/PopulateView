"""Native wxPython dialog hosted by KiCad's PCB editor."""
import traceback
import pcbnew
import wx

from .engine import Options, PlanError, generate


def show_message(message, title, style, parent):
    """Keep plugin button labels in English regardless of KiCad's locale."""
    dialog = wx.MessageDialog(parent, message, title, style)
    try:
        if style & wx.YES_NO:
            dialog.SetYesNoLabels("Yes", "No")
        else:
            dialog.SetOKLabel("OK")
        return dialog.ShowModal()
    finally:
        dialog.Destroy()


class PlanDialog(wx.Dialog):
    def __init__(self, parent):
        super().__init__(parent, title="PopulateView · Assembly drawing")
        layout = wx.BoxSizer(wx.VERTICAL)
        self.side = wx.RadioBox(self, label="Sides", choices=["Top", "Bottom", "Both sides"],
                                majorDimension=1, style=wx.RA_SPECIFY_COLS)
        self.side.SetSelection(2)
        layout.Add(self.side, 0, wx.EXPAND | wx.ALL, 14)
        self.replace = wx.CheckBox(self, label="Update / replace existing PopulateView drawings")
        self.dnp = wx.CheckBox(self, label="Mark unpopulated components with [DNP]")
        self.dnp.SetValue(True)
        for control in (self.replace, self.dnp):
            layout.Add(control, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM, 14)
        note = wx.StaticText(self, label="Font size and stroke width adapt to each component.\n"
                             "Long references and DNP labels are fitted in full.\n"
                             "Conflicting internal graphics may be omitted in drawings.\n"
                             "Very small labels may require zoom or an enlarged printout.\n"
                             "Bottom: mirrored component view with readable text.\n"
                             "Export only the relevant PopulateView layer,\n"
                             "without extra mirroring or an Edge.Cuts overlay.\n"
                             "Save the board after generating the drawings.")
        layout.Add(note, 0, wx.ALL, 14)
        buttons = self.CreateButtonSizer(wx.OK | wx.CANCEL)
        self.FindWindowById(wx.ID_OK).SetLabel("Generate assembly drawing")
        self.FindWindowById(wx.ID_CANCEL).SetLabel("Cancel")
        layout.Add(buttons, 0, wx.EXPAND | wx.ALL, 14)
        self.SetSizerAndFit(layout)
        self.CentreOnParent()


class PopulateViewPlugin(pcbnew.ActionPlugin):
    def defaults(self):
        self.name = "PopulateView – Assembly drawings"
        self.category = "Documentation"
        self.description = "Top and bottom assembly drawings on separate user layers"
        self.show_toolbar_button = False

    def Run(self):
        parent = wx.GetTopLevelParent(wx.GetActiveWindow()) if wx.GetActiveWindow() else None
        dialog = PlanDialog(parent)
        try:
            if dialog.ShowModal() != wx.ID_OK:
                return
            sides = (("front",), ("back",), ("front", "back"))[dialog.side.GetSelection()]
            options = Options(sides, dialog.replace.GetValue(), dialog.dnp.GetValue())
            if options.replace and show_message(
                    "Existing PopulateView objects on the selected sides will be replaced.\n"
                    "Manual edits to these objects will also be lost. Continue?",
                    "PopulateView", wx.YES_NO | wx.NO_DEFAULT | wx.ICON_QUESTION, parent) != wx.ID_YES:
                return
            result = generate(pcbnew.GetBoard(), options)
            pcbnew.Refresh()
            summary = "\n".join(("Top" if s == "front" else "Bottom")
                                + ": " + str(r["footprints"]) + " components, "
                                + str(r["small_labels"]) + " labels below 0.5 mm" for s, r in result.items())
            show_message(summary + "\n\nDrawings generated. Please review and save the board.",
                          "PopulateView", wx.OK | wx.ICON_INFORMATION, parent)
        except PlanError as exc:
            show_message(str(exc), "PopulateView", wx.OK | wx.ICON_WARNING, parent)
        except Exception:
            show_message("Generation failed.\n\n" + traceback.format_exc(),
                          "PopulateView", wx.OK | wx.ICON_ERROR, parent)
        finally:
            dialog.Destroy()
