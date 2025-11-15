# ESP32 Rotating TFT Display

Simple MicroPython firmware for an ESP32 + ILI9341 TFT that rotates
through three slides every 10 seconds:

1. **Weather** for Jefferson Hills, PA 15025 (OpenWeatherMap)
2. **HF propagation summary** (solar flux, K and A indices from HamQSL)
3. **UTC time** (synced via HTTP)

The last successful values are cached so if an API call fails, the
screen continues to show the previous data instead of going blank.

## Setup

1. Create this project folder on your PC:

   ```
   Z:\windsurf\esp32-rotating-display
   ```

2. Edit `wifi_config.py` and set:

   ```python
   WIFI_SSID = "YourWiFiName"
   WIFI_PASSWORD = "YourWiFiPassword"

   OWM_API_KEY = "YOUR_OPENWEATHERMAP_API_KEY"
   OWM_ZIP = "15025"
   OWM_COUNTRY = "US"
   LOCATION_NAME = "Jefferson Hills, PA"
   ```

3. Flash MicroPython to your ESP32 (as in your slideshow project).

4. Copy the following files to the ESP32 filesystem:

   - `main.py`
   - `wifi_config.py`
   - `data_sources.py`
   - `ili9341.py` (display driver, reused from your slideshow project)

   For example, using `ampy`:

   ```bash
   venv\Scripts\ampy.exe --port COM5 put ili9341.py
   venv\Scripts\ampy.exe --port COM5 put wifi_config.py
   venv\Scripts\ampy.exe --port COM5 put data_sources.py
   venv\Scripts\ampy.exe --port COM5 put main.py
   ```

5. Press RESET on the ESP32.

The display should connect to WiFi and start rotating slides between
weather, HF conditions, and UTC time every 10 seconds.
