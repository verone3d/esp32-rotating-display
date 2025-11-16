"""ESP32 rotating TFT display: Weather, HF, UTC time.

Slides rotate every 10 seconds:
- Weather for Jefferson Hills, PA 15025
- HF radio conditions (global)
- UTC time (HTTP-based)

Caching ensures we keep showing the last successful values
if a fetch fails.
"""

import time
from machine import SPI, Pin

# Display driver (assumes ili9341.Display like in your slideshow project)
from ili9341 import Display

import wifi_config
from data_sources import fetch_weather, fetch_hf, fetch_utc_http


# --- Display setup (adjust pins if needed) ---
TFT_MOSI = 13
TFT_MISO = 12
TFT_SCLK = 14
TFT_CS = 15
TFT_DC = 2
TFT_RST = -1
TFT_BL = 21


def init_backlight():
    bl = Pin(TFT_BL, Pin.OUT)
    bl.value(1)
    return bl


def init_display():
    spi = SPI(1, baudrate=60000000, sck=Pin(TFT_SCLK), mosi=Pin(TFT_MOSI), miso=Pin(TFT_MISO))
    disp = Display(spi, dc=Pin(TFT_DC), cs=Pin(TFT_CS), rst=None)
    return disp


# --- Simple text drawing helpers ---

WHITE = 0xFFFF
BLACK = 0x0000
YELLOW = 0xFFE0
CYAN = 0x07FF
GREEN = 0x07E0
RED = 0xF800

# Local time offset from UTC in hours (e.g., -5 for EST, -4 for EDT)
LOCAL_OFFSET_HOURS = -5

# Treat the logical canvas as 320x240 (landscape). We rotate logical
# coordinates into the physical 240x320 portrait display.
LOGICAL_WIDTH = 320
LOGICAL_HEIGHT = 240


_FONT_5X7 = {
    " ": (0x00, 0x00, 0x00, 0x00, 0x00),
    "-": (0x00, 0x08, 0x08, 0x08, 0x00),
    ":": (0x00, 0x14, 0x00, 0x14, 0x00),
    "0": (0x1E, 0x11, 0x13, 0x15, 0x1E),
    "1": (0x00, 0x12, 0x1F, 0x10, 0x00),
    "2": (0x12, 0x19, 0x15, 0x13, 0x00),
    "3": (0x11, 0x15, 0x15, 0x0A, 0x00),
    "4": (0x07, 0x04, 0x04, 0x1F, 0x00),
    "5": (0x17, 0x15, 0x15, 0x09, 0x00),
    "6": (0x0E, 0x15, 0x15, 0x08, 0x00),
    "7": (0x01, 0x01, 0x1D, 0x03, 0x00),
    "8": (0x0A, 0x15, 0x15, 0x0A, 0x00),
    "9": (0x02, 0x15, 0x15, 0x0E, 0x00),
    "A": (0x1E, 0x05, 0x05, 0x1E, 0x00),
    "B": (0x1F, 0x15, 0x15, 0x0A, 0x00),
    "C": (0x0E, 0x11, 0x11, 0x11, 0x00),
    "D": (0x1F, 0x11, 0x11, 0x0E, 0x00),
    "E": (0x1F, 0x15, 0x15, 0x11, 0x00),
    "F": (0x1F, 0x05, 0x05, 0x01, 0x00),
    "G": (0x0E, 0x11, 0x15, 0x1D, 0x00),
    "H": (0x1F, 0x04, 0x04, 0x1F, 0x00),
    "I": (0x11, 0x1F, 0x11, 0x00, 0x00),
    "J": (0x08, 0x10, 0x10, 0x0F, 0x00),
    "K": (0x1F, 0x04, 0x0A, 0x11, 0x00),
    "L": (0x1F, 0x10, 0x10, 0x10, 0x00),
    "M": (0x1F, 0x02, 0x04, 0x02, 0x1F),
    "N": (0x1F, 0x02, 0x04, 0x1F, 0x00),
    "O": (0x0E, 0x11, 0x11, 0x0E, 0x00),
    "P": (0x1F, 0x05, 0x05, 0x02, 0x00),
    "Q": (0x0E, 0x11, 0x19, 0x1E, 0x00),
    "R": (0x1F, 0x05, 0x0D, 0x12, 0x00),
    "S": (0x12, 0x15, 0x15, 0x09, 0x00),
    "T": (0x01, 0x1F, 0x01, 0x01, 0x00),
    "U": (0x0F, 0x10, 0x10, 0x0F, 0x00),
    "V": (0x07, 0x08, 0x10, 0x08, 0x07),
    "W": (0x1F, 0x08, 0x04, 0x08, 0x1F),
    "X": (0x1B, 0x04, 0x04, 0x1B, 0x00),
    "Y": (0x03, 0x04, 0x18, 0x04, 0x03),
    "Z": (0x19, 0x15, 0x13, 0x11, 0x00),
}


def _hf_quality(data):
    """Classify HF conditions as POOR/FAIR/GOOD based on SFI and K index.

    This is a simple heuristic:
      - POOR (red):   K >= 5 or SFI < 80
      - GOOD (green): K <= 2 and SFI >= 120
      - FAIR (yellow): everything in between
    """
    try:
        sfi = float(data.get("solarflux") or 0)
    except Exception:
        sfi = 0
    try:
        k = float(data.get("kindex") or 0)
    except Exception:
        k = 0

    if k >= 5 or sfi < 80:
        return "POOR", RED
    if k <= 2 and sfi >= 120:
        return "GOOD", GREEN
    return "FAIR", YELLOW


def _weather_desc_color(desc: str) -> int:
    """Map a weather description string to a color.

    We don't track real trends yet, so we approximate using severity:
      - Extreme / severe (thunderstorm, storm, freezing, blizzard, etc.) -> RED
      - Clearly bad (rain, showers, snow, heavy clouds, fog)            -> YELLOW
      - Mixed / partly cloudy / scattered clouds                        -> ORANGE (use YELLOW+RED mix)
      - Clear / sunny / few clouds                                     -> GREEN
      - Fallback                                                        -> WHITE
    """
    if not desc:
        return WHITE
    d = desc.strip().lower()

    # Extreme / severe
    extreme_keywords = [
        "thunderstorm",
        "tornado",
        "hurricane",
        "blizzard",
        "freezing",
        "ice",
        "sleet",
        "storm",
        "squall",
    ]
    if any(k in d for k in extreme_keywords):
        return RED

    # Clearly bad / worsening (use YELLOW)
    worse_keywords = [
        "heavy rain",
        "rain",
        "showers",
        "drizzle",
        "snow",
        "overcast",
        "fog",
        "mist",
        "haze",
        "smoke",
    ]
    if any(k in d for k in worse_keywords):
        return YELLOW

    # Mixed / partly cloudy / scattered clouds: treat as "worse" too
    # so they share the same YELLOW as general bad conditions.
    if "scattered" in d or "partly" in d or "few clouds" in d or "broken clouds" in d:
        return YELLOW

    # Clear / good
    if "clear" in d or "sun" in d or "fair" in d:
        return GREEN

    return WHITE


def _hf_band_color(label):
    """Map a band condition string (Poor/Fair/Good) to a color.

    HamQSL typically uses "Poor", "Fair", "Good" for band conditions.
    We map these as requested:
      - Poor  -> RED
      - Fair  -> BLUE
      - Good  -> GREEN
    Anything else falls back to WHITE.
    """
    if not label:
        return WHITE
    l = label.strip().lower()
    if l.startswith("poor"):
        return RED
    if l.startswith("fair"):
        # User request: use blue for "fair"
        return CYAN  # CYAN is closest to blue in our palette
    if l.startswith("good"):
        return GREEN
    return WHITE


def _draw_pixel(disp, x, y, color):
    # Bounds check in logical (landscape) coordinates
    if x < 0 or y < 0 or x >= LOGICAL_WIDTH or y >= LOGICAL_HEIGHT:
        return

    # Map logical landscape (320x240) into physical portrait (240x320).
    # Rotate 90 degrees clockwise:
    #   x_phys = y_logical
    #   y_phys = (disp.height - 1) - x_logical
    x_phys = y
    y_phys = (disp.height - 1) - x

    if x_phys < 0 or y_phys < 0 or x_phys >= disp.width or y_phys >= disp.height:
        return

    disp.set_window(x_phys, y_phys, x_phys, y_phys)
    buf = bytearray(2)
    buf[0] = (color >> 8) & 0xFF
    buf[1] = color & 0xFF
    disp.cs.value(0)
    disp.dc.value(1)
    disp.spi.write(buf)
    disp.cs.value(1)


def _draw_char(disp, ch, x, y, color=WHITE, scale=1):
    pattern = _FONT_5X7.get(ch.upper())
    if pattern is None:
        return 6 * scale
    for col in range(5):
        col_bits = pattern[col]
        for row in range(7):
            if col_bits & (1 << row):
                for dx in range(scale):
                    for dy in range(scale):
                        _draw_pixel(disp, x + col * scale + dx, y + row * scale + dy, color)
    return 6 * scale


def draw_text(disp, text, x, y, color=WHITE, scale=1):
    cx = x
    for ch in text:
        cx += _draw_char(disp, ch, cx, y, color=color, scale=scale)


def clear_screen(disp, color=BLACK):
    disp.fill(color)


def draw_centered_text(disp, text, y, color=WHITE, scale=1):
    # Basic centering assuming 8x8 font per char * scale
    char_w = 8 * scale
    x = max(0, (LOGICAL_WIDTH - len(text) * char_w) // 2)
    draw_text(disp, text, x, y, color=color, scale=scale)


# --- Slide renderers ---

state = {
    "weather": {"data": None, "last_fetch": 0},
    "hf": {"data": None, "last_fetch": 0},
    # For UTC we only track whether we've successfully synced and when.
    # Actual time comes from the RTC via time.gmtime() after NTP sync.
    "utc": {"ts": None, "last_sync": 0},
}


def update_weather(now):
    last = state["weather"]["last_fetch"]
    # Perform an initial fetch when last_fetch == 0, then every 10 minutes
    if last != 0 and (now - last) < 600:
        return
    data = fetch_weather()
    if data is not None:
        state["weather"]["data"] = data
    state["weather"]["last_fetch"] = now


def update_hf(now):
    last = state["hf"]["last_fetch"]
    # Perform an initial fetch when last_fetch == 0, then every 30 minutes
    if last != 0 and (now - last) < 1800:
        return
    data = fetch_hf()
    if data is not None:
        state["hf"]["data"] = data
    state["hf"]["last_fetch"] = now


def update_utc(now):
    # When we have no time yet, try to sync but back off on errors.
    # After we have a time, resync at most once per hour.
    last = state["utc"]["last_sync"]
    ts_current = state["utc"]["ts"]

    # If we already have a timestamp and it's been less than an hour, skip.
    if ts_current is not None and (now - last) <= 3600:
        return

    # If we have no timestamp yet, retry at most every 30 seconds.
    if ts_current is None and last != 0 and (now - last) < 30:
        return

    new_ts = fetch_utc_http()
    # Always update last_sync so we honor the backoff even on errors.
    state["utc"]["last_sync"] = now
    if new_ts is not None:
        state["utc"]["ts"] = new_ts


def tick_utc(delta):
    # No-op now that we rely on RTC time from time.gmtime().
    # Kept for compatibility in case it's referenced.
    return


def draw_weather_slide(disp):
    clear_screen(disp)
    data = state["weather"]["data"]
    if data is None:
        draw_centered_text(disp, "WEATHER LOADING...", 120, color=YELLOW, scale=3)
        return

    temp = data.get("temp")
    desc = data.get("description", "") or ""
    # MicroPython strings don't support .title(); do a simple first-letter upper
    if desc:
        desc = desc[0].upper() + desc[1:]

    # Use uppercase for description for better readability
    desc = desc.upper()

    # Top: location
    draw_centered_text(disp, wifi_config.LOCATION_NAME.upper(), 20, color=CYAN, scale=2)

    # Middle: large temperature
    if temp is not None:
        text = "%.0f F" % temp
    else:
        text = "N/A"
    draw_centered_text(disp, text, 100, color=WHITE, scale=5)

    # Bottom: description with color based on severity/condition
    color = _weather_desc_color(desc)
    draw_centered_text(disp, desc, 180, color=color, scale=2)


def draw_hf_slide(disp):
    clear_screen(disp)
    data = state["hf"]["data"]
    draw_centered_text(disp, "HF CONDITIONS", 20, color=CYAN, scale=2)

    if data is None:
        # If we've already attempted a fetch (last_fetch != 0) but still have no data,
        # show a clearer message that HF data is unavailable.
        if state["hf"]["last_fetch"]:
            draw_centered_text(disp, "HF UNAVAILABLE", 120, color=YELLOW, scale=3)
        else:
            draw_centered_text(disp, "HF LOADING...", 120, color=YELLOW, scale=3)
        return

    # Middle: SFI
    draw_centered_text(disp, "SFI %s" % data.get("solarflux", ""), 70, color=WHITE, scale=4)
    k = data.get("kindex", "")
    a = data.get("aindex", "")
    # K and A indices
    draw_centered_text(disp, "K %s   A %s" % (k, a), 135, color=WHITE, scale=3)

    # Overall HF quality (used as fallback color when band-specific data is missing)
    overall_label, overall_color = _hf_quality(data)

    # Bottom: band-specific HF conditions for 10m, 20m, 40m
    band_10 = data.get("10m", "")
    band_20 = data.get("20m", "")
    band_40 = data.get("40m", "")

    color_10 = _hf_band_color(band_10) if band_10 else overall_color
    color_20 = _hf_band_color(band_20) if band_20 else overall_color
    color_40 = _hf_band_color(band_40) if band_40 else overall_color

    # Draw band labels spaced across the bottom. Using scale=3 for good readability.
    y = 190
    draw_text(disp, "10M", 40, y, color=color_10, scale=3)
    draw_text(disp, "20M", 140, y, color=color_20, scale=3)
    draw_text(disp, "40M", 240, y, color=color_40, scale=3)


def draw_utc_slide(disp):
    clear_screen(disp)
    draw_centered_text(disp, "UTC / LOCAL", 10, color=CYAN, scale=2)

    # If we've never successfully synced, show a syncing message.
    if state["utc"]["ts"] is None:
        draw_centered_text(disp, "SYNCING...", 120, color=YELLOW, scale=3)
        return

    # Read current UTC from RTC
    t_utc = time.gmtime()
    utc_hh = t_utc[3]
    utc_mm = t_utc[4]
    utc_ss = t_utc[5]
    utc_time_str = "%02d:%02d:%02d" % (utc_hh, utc_mm, utc_ss)
    utc_date_str = "%04d-%02d-%02d" % (t_utc[0], t_utc[1], t_utc[2])

    # Compute local time using a fixed offset from UTC
    try:
        offset_sec = int(LOCAL_OFFSET_HOURS * 3600)
        t_local = time.gmtime(time.time() + offset_sec)
        loc_hh = t_local[3]
        loc_mm = t_local[4]
        loc_ss = t_local[5]
        local_time_str = "%02d:%02d:%02d" % (loc_hh, loc_mm, loc_ss)
    except Exception:
        local_time_str = "--:--:--"

    # UTC time large, date smaller below
    draw_centered_text(disp, utc_time_str, 60, color=WHITE, scale=4)
    draw_centered_text(disp, utc_date_str, 110, color=GREEN, scale=2)

    # Local time at the bottom
    draw_centered_text(disp, "LOCAL %s" % local_time_str, 170, color=WHITE, scale=3)


# --- Main loop ---

SLIDES = ["weather", "hf", "utc"]
SLIDE_DURATION = 10  # seconds


def connect_wifi():
    import network

    wlan = network.WLAN(network.STA_IF)
    if not wlan.active():
        wlan.active(True)

    if not wlan.isconnected():
        print("Connecting to WiFi... (%s)" % wifi_config.WIFI_SSID)
        wlan.connect(wifi_config.WIFI_SSID, wifi_config.WIFI_PASSWORD)
        t0 = time.time()
        while not wlan.isconnected() and time.time() - t0 < 20:
            time.sleep(0.5)
            print("  waiting...")

    if wlan.isconnected():
        print("WiFi connected, IP:", wlan.ifconfig()[0])
    else:
        print("WiFi connect failed")


def main():
    print("ESP32 Rotating Display starting...")
    init_backlight()
    disp = init_display()

    connect_wifi()

    current_index = 0
    last_slide_change = time.time()

    # Initial draw
    draw_weather_slide(disp)

    while True:
        now = time.time()

        # Data refresh
        update_weather(now)
        update_hf(now)
        update_utc(now)

        # Slide change
        if now - last_slide_change >= SLIDE_DURATION:
            current_index = (current_index + 1) % len(SLIDES)
            slide = SLIDES[current_index]

            if slide == "weather":
                draw_weather_slide(disp)
            elif slide == "hf":
                draw_hf_slide(disp)
            elif slide == "utc":
                draw_utc_slide(disp)

            last_slide_change = now

        time.sleep(0.2)


if __name__ == "__main__":
    main()
