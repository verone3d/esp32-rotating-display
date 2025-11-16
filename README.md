# ESP32 Rotating TFT Display

MicroPython firmware for the **AITRIP ESP32-2432S028R** 2.8" TFT module
that rotates through three slides every 10 seconds:

1. **Weather** for your location (OpenWeatherMap)
2. **HF propagation summary** (solar flux, K and A indices from HamQSL)
3. **UTC time**

The last successful values are cached so if an API call fails, the
screen continues to show the previous data instead of going blank.

This README is written so a friend with a brand new board can get it
running in a few minutes using **Thonny** on Windows.

---

## 1. Hardware and software you need

- **Board**:
  - AITRIP "ESP32-2432S028R" 2.8" 240×320 smart display TFT module
    (ESP32 + ILI9341 TFT on one board)
- **USB cable**: micro‑USB data cable
- **PC**: Windows 10/11

On the PC:

- **Thonny** (Python IDE with MicroPython support) – https://thonny.org/
- **MicroPython firmware** for ESP32:
  - Tested with: `ESP32_GENERIC-20250911-v1.26.1.bin`
  - Download from official MicroPython site:
    https://micropython.org/download/ESP32_GENERIC/

---

## 2. Flash MicroPython onto the ESP32-2432S028R

You only need to do this once per board.

1. Install **Thonny** and start it.
2. Plug the ESP32-2432S028R into your PC via USB.
3. In Thonny, go to:

   - **Tools → Options → Interpreter**
   - Interpreter: choose **MicroPython (ESP32)**
   - Port: select the COM port that appears when you plug the board in
     (e.g. `COM3`, `COM4`).

4. Click **Install or update MicroPython** (button in the Interpreter
   settings dialog).

5. In the dialog:

   - Select **ESP32**.
   - Browse to the downloaded
     `ESP32_GENERIC-20250911-v1.26.1.bin` file.
   - Click **Install** and wait until it finishes.

When done, click **OK**. In the Thonny **Shell** you should see a
`>>>` MicroPython prompt after the board resets.

---

## 3. Get this project

Either:

- **Clone with git**:

  ```bash
  git clone git@github.com:verone3d/esp32-rotating-display.git
  ```

  or

- **Download ZIP** from GitHub and extract it, so you have a folder
  like:

  ```
  C:\Users\you\Documents\esp32-rotating-display
  ```

The important files in that folder are:

- `main.py` – main program and slides
- `data_sources.py` – fetches weather, HF, and UTC
- `ili9341.py` – ILI9341 display driver for this board
- `wifi_config.py` – WiFi + API configuration (you edit this)

---

## 4. Configure WiFi and weather (wifi_config.py)

Open `wifi_config.py` in Thonny or your editor. It looks like:

```python
WIFI_SSID = "YourWiFiName"
WIFI_PASSWORD = "YourWiFiPassword"

OWM_API_KEY = "YOUR_OPENWEATHERMAP_API_KEY"
OWM_ZIP = "15025"      # Jefferson Hills example
OWM_COUNTRY = "US"

LOCATION_NAME = "Jefferson Hills, PA"
```

Edit the values:

- **WIFI_SSID / WIFI_PASSWORD**
  - Your home WiFi network name and password.
- **OWM_API_KEY**
  - Create a free account at https://openweathermap.org
  - Generate an API key and paste it here as a string.
- **OWM_ZIP / OWM_COUNTRY**
  - Set to your ZIP/postcode and 2‑letter country code.
- **LOCATION_NAME**
  - Any text you want shown at the top of the weather slide.

Save `wifi_config.py` after editing.

> **Note:** Do not commit your real WiFi password or API key to a
> public repo. Use this file locally; the version in GitHub should
> contain only placeholders.

---

## 5. Upload the firmware files via Thonny

Now we copy the four Python files onto the ESP32’s internal
filesystem.

1. In Thonny, make sure the interpreter is still set to
   **MicroPython (ESP32)** and shows a `>>>` prompt.

2. Enable the **Files** view:

   - **View → Files**

3. In the **Files** pane you’ll see two panels:

   - **This computer** – your PC files
   - **MicroPython device** – files on the ESP32

4. In **This computer**, navigate to your
   `esp32-rotating-display` folder.

5. Upload these files to the root of the device ("/"):

   - Right‑click `ili9341.py` → **Upload to /**
   - Right‑click `wifi_config.py` → **Upload to /**
   - Right‑click `data_sources.py` → **Upload to /**
   - Right‑click `main.py` → **Upload to /**

   If asked to overwrite, choose **Yes**.

6. Reset the board:

   - Press the **RESET** button on the ESP32-2432S028R, or
   - In the Thonny Shell, press `Ctrl+D` to soft‑reboot.

The board will boot, run `main.py`, connect to WiFi, and start
rotating slides.

---

## 6. What you should see on the display

The display uses a 240×320 ILI9341 in portrait orientation. Slides
rotate every **10 seconds**.

### Weather slide

- Top: your `LOCATION_NAME` in cyan.
- Middle: large temperature, e.g. `72 F`.
- Bottom: a description like `CLEAR SKY`, `BROKEN CLOUDS`.
  - Color indicates severity:
    - Green – clear/sunny/fair
    - Yellow – rain/snow/overcast/fog/partly/mixed clouds
    - Red – severe/extreme (thunderstorms, storms, freezing, etc.)

### HF slide

- Top: `HF CONDITIONS` in cyan.
- Middle: `SFI xxx` (solar flux). Larger font.
- Next line: `K x   A y` (K and A indices).
- Bottom: band labels `10M  20M  40M`:
  - Each label’s color reflects overall HF quality (and per‑band
    conditions when available):
    - Red – Poor
    - Blue (cyan) – Fair
    - Green – Good

### UTC slide

- Top: `UTC / LOCAL`.
- Large center: current **UTC time**.
- Below: UTC date (`YYYY‑MM‑DD`).
- Bottom: `LOCAL hh:mm:ss` using a fixed offset from UTC (set in
  `LOCAL_OFFSET_HOURS` inside `main.py` if needed).

---

## 7. Tweaking behavior

Inside `main.py` you can adjust a few simple settings:

- `SLIDES = ["weather", "hf", "utc"]`
  - Order of slides.
- `SLIDE_DURATION = 10`
  - Seconds each slide stays on screen.
- `LOCAL_OFFSET_HOURS = -5`
  - Local time offset from UTC (e.g. `-5` for EST, `-4` for EDT).

After changing any of these in `main.py`:

1. Re‑upload `main.py` to the ESP32 via Thonny.
2. Reset the board (`Ctrl+D` in Thonny or press RESET).

---

## 8. Troubleshooting

- **Display stays blank**
  - Check that MicroPython is installed (do you see `>>>` in Thonny
    when you connect?).
  - Make sure `main.py` and `ili9341.py` exist on the MicroPython
    device.

- **WiFi never connects**
  - Double‑check `WIFI_SSID` and `WIFI_PASSWORD` in `wifi_config.py`.

- **Weather shows `N/A` or `WEATHER LOADING...` for a long time**
  - Make sure your `OWM_API_KEY`, `OWM_ZIP`, and `OWM_COUNTRY` are
    correct.
  - Check that the board has internet access on your network.

- **HF slide says `HF UNAVAILABLE`**
  - HamQSL may be temporarily unreachable; the device caches the last
    good values and retries periodically.

If you get stuck, capture the output from the Thonny Shell (errors
printed there) and include it when asking for help.
