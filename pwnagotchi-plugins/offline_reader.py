"""offline_reader — read ZIM libraries (Kiwix) on the device.

No offline-library plugin exists. This makes .zim files (Wikipedia, manuals, wikis) browsable
from the plugin web page — a genuinely useful field-computer feature. Article rendering uses
`libzim`; the plugin degrades to a plain file listing when the library isn't installed.

Options (main.plugins.offline_reader.*):
    enabled  = true
    zim_dir  = "/root/zim"
    position = "0,0"

Requires: pip `libzim` (or the `kiwix-tools` package) to render articles, plus one or more
`.zim` files in zim_dir. Without libzim it still lists the files.
"""
import glob
import html
import logging
import os

import pwnagotchi.plugins as plugins
import pwnagotchi.ui.fonts as fonts
from pwnagotchi.ui.components import LabeledValue
from pwnagotchi.ui.view import BLACK


def list_zims(zim_dir):
    try:
        return sorted(glob.glob(os.path.join(zim_dir, "*.zim")))
    except Exception:
        return []


class ZimReader:
    """Thin, guarded wrapper over libzim."""
    def __init__(self):
        self.available = False
        self._archive_cls = None
        self._cache = {}
        try:
            from libzim.reader import Archive
            self._archive_cls = Archive
            self.available = True
        except Exception:
            pass

    def _archive(self, path):
        a = self._cache.get(path)
        if a is None:
            a = self._archive_cls(path)
            self._cache[path] = a
        return a

    def article(self, zim_path, article_path=None):
        if not self.available:
            return None
        try:
            a = self._archive(zim_path)
            entry = a.get_entry_by_path(article_path) if article_path else a.main_entry
            item = entry.get_item()
            return bytes(item.content).decode("utf-8", "ignore")
        except Exception as e:
            logging.debug("[offline_reader] article read failed: %s", e)
            return None


class OfflineReader(plugins.Plugin):
    __author__ = "patrickato"
    __version__ = "0.1.0"
    __license__ = "GPL3"
    __description__ = "Browse offline ZIM libraries (Kiwix) from the web UI."

    def __init__(self):
        self.options = dict()
        self._reader = None

    def on_loaded(self):
        self._zim_dir = self.options.get("zim_dir", "/root/zim")
        self._reader = ZimReader()
        logging.info("[offline_reader] loaded (libzim=%s)", self._reader.available)

    # -- UI ----------------------------------------------------------------------------
    def on_ui_setup(self, ui):
        try:
            pos = tuple(int(x) for x in str(self.options.get("position", "0,0")).split(","))
        except Exception:
            pos = (0, 0)
        ui.add_element("zim", LabeledValue(color=BLACK, label="zim:", value="-",
                       position=pos, label_font=fonts.Small, text_font=fonts.Small))

    def on_ui_update(self, ui):
        with ui._lock:
            ui.set("zim", str(len(list_zims(self._zim_dir))))

    def on_unload(self, ui):
        with ui._lock:
            if ui.has_element("zim"):
                ui.remove_element("zim")

    # -- web ---------------------------------------------------------------------------
    def _library_html(self, zims):
        if not zims:
            return "<p>No .zim files in %s</p>" % html.escape(self._zim_dir)
        items = "".join(
            "<li><a href='?zim={0}'>{1}</a></li>".format(
                html.escape(os.path.basename(z)), html.escape(os.path.basename(z)))
            for z in zims)
        note = "" if self._reader.available else \
            "<p><em>Install libzim to read article content; listing only.</em></p>"
        return note + "<ul>" + items + "</ul>"

    def on_webhook(self, path, request):
        zims = list_zims(self._zim_dir)
        zim_name = None
        article_path = None
        try:
            if request is not None:
                zim_name = request.args.get("zim")
                article_path = request.args.get("path")
        except Exception:
            pass

        body = self._library_html(zims)
        if zim_name:
            full = os.path.join(self._zim_dir, os.path.basename(zim_name))  # basename: no traversal
            if os.path.exists(full) and self._reader.available:
                content = self._reader.article(full, article_path)
                body = content if content else "<p>Could not read that article.</p>"
            elif not self._reader.available:
                body = "<p>libzim not installed — cannot render %s.</p>" % html.escape(zim_name) + body

        return "<html><body><h1>Offline Reader</h1>{}</body></html>".format(body)
