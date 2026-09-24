"""wordlist_manager — curate local wordlists for the cracking backends.

Wordlist handling for quickdic/hashcat is manual and ad-hoc. This inventories the wordlists in
a directory (size + line count), de-duplicates them (order-preserving), merges several into one
deduped list, and can fetch new lists from configured URLs. It supports authorized cracking of
your own captures — it is not itself a cracker.

Options (main.plugins.wordlist_manager.*):
    enabled      = true
    wordlist_dir = "/root/wordlists"
    extensions   = ["txt","lst","dic","dict"]
    sources      = []          # URLs to fetch on demand
    position     = "0,0"

Requires: none (Python standard library; fetching uses urllib).
"""
import glob
import logging
import os
import urllib.request

import pwnagotchi.plugins as plugins
import pwnagotchi.ui.fonts as fonts
from pwnagotchi.ui.components import LabeledValue
from pwnagotchi.ui.view import BLACK


def dedupe_lines(lines):
    """Order-preserving de-duplication of an iterable of strings."""
    seen = set()
    out = []
    for line in lines:
        if line not in seen:
            seen.add(line)
            out.append(line)
    return out


def file_stats(path):
    lines = 0
    try:
        with open(path, "rt", errors="ignore") as fp:
            for _ in fp:
                lines += 1
    except Exception:
        return None
    return {"lines": lines, "bytes": os.path.getsize(path)}


class WordlistManager(plugins.Plugin):
    __author__ = "patrickato"
    __version__ = "0.1.0"
    __license__ = "GPL3"
    __description__ = "Inventory, dedupe, merge and fetch cracking wordlists."

    def __init__(self):
        self.options = dict()

    def on_loaded(self):
        self._dir = self.options.get("wordlist_dir", "/root/wordlists")
        self._exts = [e.lstrip(".") for e in self.options.get("extensions",
                      ["txt", "lst", "dic", "dict"])]
        self._sources = list(self.options.get("sources", []) or [])
        logging.info("[wordlist_manager] loaded (dir=%s)", self._dir)

    # -- core --------------------------------------------------------------------------
    def list_wordlists(self):
        files = []
        for ext in self._exts:
            files.extend(glob.glob(os.path.join(self._dir, "*." + ext)))
        out = []
        for f in sorted(set(files)):
            st = file_stats(f)
            if st:
                out.append({"name": os.path.basename(f), "path": f, **st})
        return out

    def dedupe_file(self, path):
        try:
            with open(path, "rt", errors="ignore") as fp:
                lines = fp.read().splitlines()
        except Exception:
            return 0
        unique = dedupe_lines(lines)
        removed = len(lines) - len(unique)
        if removed:
            try:
                with open(path, "wt") as fp:
                    fp.write("\n".join(unique) + ("\n" if unique else ""))
            except Exception as e:
                logging.debug("[wordlist_manager] rewrite failed: %s", e)
                return 0
        return removed

    def dedupe_all(self):
        return {wl["name"]: self.dedupe_file(wl["path"]) for wl in self.list_wordlists()}

    def merge(self, paths, out_path):
        collected = []
        for p in paths:
            try:
                with open(p, "rt", errors="ignore") as fp:
                    collected.extend(fp.read().splitlines())
            except Exception:
                continue
        unique = dedupe_lines(collected)
        try:
            os.makedirs(os.path.dirname(out_path), exist_ok=True)
            with open(out_path, "wt") as fp:
                fp.write("\n".join(unique) + ("\n" if unique else ""))
        except Exception as e:
            logging.debug("[wordlist_manager] merge write failed: %s", e)
            return 0
        return len(unique)

    def fetch(self, url):
        try:
            os.makedirs(self._dir, exist_ok=True)
            name = os.path.basename(url.split("?")[0]) or "downloaded.txt"
            dest = os.path.join(self._dir, name)
            with urllib.request.urlopen(url, timeout=30) as resp, open(dest, "wb") as fp:
                fp.write(resp.read())
            logging.info("[wordlist_manager] fetched %s", dest)
            return dest
        except Exception as e:
            logging.warning("[wordlist_manager] fetch failed %s: %s", url, e)
            return None

    # -- UI ----------------------------------------------------------------------------
    def on_ui_setup(self, ui):
        try:
            pos = tuple(int(x) for x in str(self.options.get("position", "0,0")).split(","))
        except Exception:
            pos = (0, 0)
        ui.add_element("wordlists", LabeledValue(color=BLACK, label="wl:", value="-",
                       position=pos, label_font=fonts.Small, text_font=fonts.Small))

    def on_ui_update(self, ui):
        with ui._lock:
            ui.set("wordlists", str(len(self.list_wordlists())))

    def on_unload(self, ui):
        with ui._lock:
            if ui.has_element("wordlists"):
                ui.remove_element("wordlists")

    # -- web ---------------------------------------------------------------------------
    def on_webhook(self, path, request):
        try:
            if request is not None and request.args.get("action") == "dedupe_all":
                self.dedupe_all()
        except Exception:
            pass
        rows = "".join(
            "<tr><td>{name}</td><td>{lines}</td><td>{bytes}</td></tr>".format(**wl)
            for wl in self.list_wordlists()
        ) or "<tr><td colspan=3>no wordlists</td></tr>"
        return ("<html><body><h1>Wordlist Manager</h1>"
                "<p><a href='?action=dedupe_all'>dedupe all</a></p>"
                "<table border=1><tr><th>name</th><th>lines</th><th>bytes</th></tr>{}"
                "</table></body></html>").format(rows)
