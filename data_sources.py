"""Data source helpers for ESP32 rotating display.

Provides functions to fetch:
- Current weather (OpenWeatherMap)
- HF conditions (HamQSL)
- UTC time (via HTTP)

All functions are written for MicroPython using urequests.
"""

import time
import ujson as json

try:
    import urequests as requests
except ImportError:  # allow CPython testing
    import requests

from wifi_config import OWM_API_KEY, OWM_ZIP, OWM_COUNTRY


def fetch_weather():
    """Fetch current weather data.

    Returns a dict with at least:
        {
            "temp": float or None,
            "description": str,
        }
    On error, returns None.
    """
    if not OWM_API_KEY:
        print("[weather] No OWM_API_KEY configured")
        return None

    try:
        url = (
            "https://api.openweathermap.org/data/2.5/weather?zip=%s,%s&units=imperial&appid=%s"
            % (OWM_ZIP, OWM_COUNTRY, OWM_API_KEY)
        )
        print("[weather] GET", url)
        resp = requests.get(url)
        try:
            print("[weather] status:", resp.status_code)
            if resp.status_code != 200:
                return None
            data = resp.json()
        finally:
            resp.close()

        main = data.get("main", {})
        weather_list = data.get("weather", [])
        desc = weather_list[0].get("description", "") if weather_list else ""

        result = {
            "temp": main.get("temp"),
            "description": desc,
        }
        print("[weather] parsed:", result)
        return result
    except Exception as e:
        print("[weather] error:", e)
        return None


def fetch_hf():
    """Fetch HF propagation data from HamQSL.

    Returns a dict with keys like:
        {
            "solarflux": str,
            "kindex": str,
            "aindex": str,
        }
    On error, returns None.
    """
    try:
        # Use the XML endpoint; JSON endpoint can return 404 depending on server config.
        url = "http://www.hamqsl.com/solarxml.php"
        print("[hf] GET", url)
        resp = requests.get(url)
        try:
            print("[hf] status:", resp.status_code)
            if resp.status_code != 200:
                return None
            text = resp.text
        finally:
            resp.close()

        def _extract(tag):
            start_tag = "<%s>" % tag
            end_tag = "</%s>" % tag
            i = text.find(start_tag)
            if i == -1:
                return ""
            i += len(start_tag)
            j = text.find(end_tag, i)
            if j == -1:
                return ""
            return text[i:j].strip()

        result = {
            "solarflux": _extract("solarflux"),
            "kindex": _extract("kindex"),
            "aindex": _extract("aindex"),
        }
        print("[hf] parsed:", result)
        return result
    except Exception as e:
        print("[hf] error:", e)
        return None


def fetch_utc_http():
    """Fetch current UTC time using NTP.

    Uses MicroPython's ntptime module to set the RTC, then returns
    the current Unix timestamp from time.time(). On failure, returns None.
    """
    try:
        import ntptime

        print("[utc] NTP sync...")
        # ntptime sets the system RTC to UTC
        ntptime.settime()

        # After settime(), time.time() should reflect current UTC seconds
        ts = int(time.time())
        print("[utc] ntp unixtime:", ts)
        return ts
    except Exception as e:
        print("[utc] error:", e)
        return None
