"""Native wxPython dialog hosted by KiCad's PCB editor."""
import traceback
import pcbnew
import wx

from .engine import Options, PlanError, generate


class PlanDialog(wx.Dialog):
    def __init__(self, parent):
        super().__init__(parent, title="PopulateView · Bestückungsplan")
        layout = wx.BoxSizer(wx.VERTICAL)
        self.side = wx.RadioBox(self, label="Seiten", choices=["Oberseite", "Unterseite", "Beide Seiten"],
                                majorDimension=1, style=wx.RA_SPECIFY_COLS)
        self.side.SetSelection(2)
        layout.Add(self.side, 0, wx.EXPAND | wx.ALL, 14)
        self.replace = wx.CheckBox(self, label="Vorhandene PopulateView-Pläne aktualisieren / ersetzen")
        self.dnp = wx.CheckBox(self, label="DNP-Bauteile mit [DNP] kennzeichnen")
        self.dnp.SetValue(True)
        for control in (self.replace, self.dnp):
            layout.Add(control, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM, 14)
        note = wx.StaticText(self, label="Schriftgröße und Strichstärke passen sich dem Bauteil an.\n"
                             "Lange Referenzen und DNP werden vollständig eingepasst.\n"
                             "Sehr kleine Beschriftungen benötigen Zoom / Vergrößerung.\n"
                             "Unterseite: gespiegelte Bauteilansicht mit lesbarer Schrift.\n"
                             "Export: nur den jeweiligen PopulateView-Layer wählen,\n"
                             "ohne zusätzliche Spiegelung und ohne Edge.Cuts-Überlagerung.\n"
                             "Geänderte Pläne nach der Erzeugung speichern.")
        layout.Add(note, 0, wx.ALL, 14)
        buttons = self.CreateButtonSizer(wx.OK | wx.CANCEL)
        self.FindWindowById(wx.ID_OK).SetLabel("Bestückungsplan erzeugen")
        layout.Add(buttons, 0, wx.EXPAND | wx.ALL, 14)
        self.SetSizerAndFit(layout)
        self.CentreOnParent()


class PopulateViewPlugin(pcbnew.ActionPlugin):
    def defaults(self):
        self.name = "PopulateView – Bestückungspläne"
        self.category = "Documentation"
        self.description = "Bestückungspläne für Ober- und Unterseite auf separaten User-Layern"
        self.show_toolbar_button = False

    def Run(self):
        parent = wx.GetTopLevelParent(wx.GetActiveWindow()) if wx.GetActiveWindow() else None
        dialog = PlanDialog(parent)
        try:
            if dialog.ShowModal() != wx.ID_OK:
                return
            sides = (("front",), ("back",), ("front", "back"))[dialog.side.GetSelection()]
            options = Options(sides, dialog.replace.GetValue(), dialog.dnp.GetValue())
            if options.replace and wx.MessageBox(
                    "Vorhandene PopulateView-Objekte der gewählten Seiten werden ersetzt.\n"
                    "Auch manuelle Änderungen an diesen Objekten gehen verloren. Fortfahren?",
                    "PopulateView", wx.YES_NO | wx.NO_DEFAULT | wx.ICON_QUESTION, parent) != wx.YES:
                return
            result = generate(pcbnew.GetBoard(), options)
            pcbnew.Refresh()
            summary = "\n".join(("Oberseite" if s == "front" else "Unterseite")
                                + ": " + str(r["footprints"]) + " Bauteile, "
                                + str(r["small_labels"]) + " Beschriftungen unter 0,5 mm" for s, r in result.items())
            wx.MessageBox(summary + "\n\nPläne erzeugt. Bitte prüfen und Platine speichern.",
                          "PopulateView", wx.OK | wx.ICON_INFORMATION, parent)
        except PlanError as exc:
            wx.MessageBox(str(exc), "PopulateView", wx.OK | wx.ICON_WARNING, parent)
        except Exception:
            wx.MessageBox("Erzeugung fehlgeschlagen.\n\n" + traceback.format_exc(),
                          "PopulateView", wx.OK | wx.ICON_ERROR, parent)
        finally:
            dialog.Destroy()
