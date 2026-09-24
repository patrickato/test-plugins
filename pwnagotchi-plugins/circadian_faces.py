"""circadian_faces — shift the face by the real day cycle.

Picks a face for the current phase of the day (night / dawn / day / dusk). If you configure
a latitude/longitude it computes real sunrise/sunset (NOAA sunrise equation, in UTC);
otherwise it falls back to a simple local-time schedule. No fake data — just the clock and,
optionally, your location.

Options (main.plugins.circadian_faces.*):
    enabled       = true
    latitude      = 51.5            # optional; enables real sun times
    longitude     = -0.13           # optional
    twilight_min  = 30              # dawn/dusk window half-width, minutes
    override_face = true            # actually set the face (else compute only)
    day_start     = 7               # fallback schedule (local hour) when no lat/lon
    night_start   = 20              # fallback schedule (local hour)
    faces.day   = "(◕‿‿◕)"
    faces.night = "(-_-)zzz"
    faces.dawn  = "(◕ᴗ◕)"
    faces.dusk  = "(⇀‿‿↼)"
"""
import logging
import math
import time

import pwnagotchi.plugins as plugins

_DEFAULT_FACES = {
    "day": "(◕‿‿◕)",
    "night": "(-_-)zzz",
    "dawn": "(◕ᴗ◕)",
    "dusk": "(⇀‿‿↼)",
}


def compute_sun_times(y, m, d, lat, lon):
    """Return (sunrise_utc_hours, sunset_utc_hours), or 'polar-day' / 'polar-night'."""
    a = (14 - m) // 12
    yy = y + 4800 - a
    mm = m + 12 * a - 3
    jdn = d + (153 * mm + 2) // 5 + 365 * yy + yy // 4 - yy // 100 + yy // 400 - 32045
    n = jdn - 2451545.0 + 0.0008
    j_star = n - lon / 360.0
    M = (357.5291 + 0.98560028 * j_star) % 360.0
    mr = math.radians(M)
    C = 1.9148 * math.sin(mr) + 0.0200 * math.sin(2 * mr) + 0.0003 * math.sin(3 * mr)
    lam = (M + C + 180.0 + 102.9372) % 360.0
    lamr = math.radians(lam)
    j_transit = 2451545.0 + j_star + 0.0053 * math.sin(mr) - 0.0069 * math.sin(2 * lamr)
    sin_delta = math.sin(lamr) * math.sin(math.radians(23.44))
    delta = math.asin(sin_delta)
    latr = math.radians(lat)
    cos_h = (math.sin(math.radians(-0.833)) - math.sin(latr) * sin_delta) / (
        math.cos(latr) * math.cos(delta))
    if cos_h > 1:
        return "polar-night"
    if cos_h < -1:
        return "polar-day"
    H = math.degrees(math.acos(cos_h))
    j_rise = j_transit - H / 360.0
    j_set = j_transit + H / 360.0
    ut = lambda J: ((J + 0.5) % 1.0) * 24.0
    return (ut(j_rise), ut(j_set))


def phase_from_sun(now_h, sun, margin_h):
    """Classify now (UTC hours) given compute_sun_times() output."""
    if sun == "polar-day":
        return "day"
    if sun == "polar-night":
        return "night"
    rise, sset = sun
    if now_h < rise - margin_h or now_h >= sset + margin_h:
        return "night"
    if rise - margin_h <= now_h < rise + margin_h:
        return "dawn"
    if sset - margin_h <= now_h < sset + margin_h:
        return "dusk"
    return "day"


def phase_from_schedule(local_hour, day_start, night_start):
    return "day" if day_start <= local_hour < night_start else "night"


class CircadianFaces(plugins.Plugin):
    __author__ = "patrickato"
    __version__ = "0.1.0"
    __license__ = "GPL3"
    __description__ = "Set the face by the real phase of the day (sunrise/sunset or schedule)."

    def __init__(self):
        self.options = dict()

    def on_loaded(self):
        self._lat = self.options.get("latitude")
        self._lon = self.options.get("longitude")
        self._margin_h = float(self.options.get("twilight_min", 30)) / 60.0
        self._override = bool(self.options.get("override_face", True))
        self._day_start = int(self.options.get("day_start", 7))
        self._night_start = int(self.options.get("night_start", 20))
        self._faces = dict(_DEFAULT_FACES)
        self._faces.update(self.options.get("faces", {}) or {})
        logging.info("[circadian_faces] loaded (sun=%s)",
                     "on" if self._lat is not None and self._lon is not None else "schedule")

    def face_for(self, phase):
        return self._faces.get(phase, self._faces["day"])

    def current_phase(self):
        if self._lat is not None and self._lon is not None:
            g = time.gmtime()
            now_h = g.tm_hour + g.tm_min / 60.0 + g.tm_sec / 3600.0
            try:
                sun = compute_sun_times(g.tm_year, g.tm_mon, g.tm_mday,
                                        float(self._lat), float(self._lon))
                return phase_from_sun(now_h, sun, self._margin_h)
            except Exception as e:
                logging.debug("[circadian_faces] sun calc failed: %s", e)
        return phase_from_schedule(time.localtime().tm_hour, self._day_start, self._night_start)

    def on_ui_update(self, ui):
        if not self._override:
            return
        phase = self.current_phase()
        with ui._lock:
            ui.set("face", self.face_for(phase))

    def on_webhook(self, path, request):
        phase = self.current_phase()
        return ("<html><body><h1>Circadian Faces</h1>"
                "<p>Current phase: <b>{}</b> → face {}</p></body></html>").format(
                    phase, self.face_for(phase))
