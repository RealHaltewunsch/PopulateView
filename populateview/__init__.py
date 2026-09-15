"""PopulateView: KiCad assembly drawings. Import core without registering in tests."""
import os

if os.environ.get("POPULATEVIEW_HEADLESS") != "1":
    from .plugin import PopulateViewPlugin
    PopulateViewPlugin().register()
