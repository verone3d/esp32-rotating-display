"""WiFi and API configuration for ESP32 rotating display.

Edit WIFI_SSID, WIFI_PASSWORD, and API keys below before flashing to the board.
This file is safe to commit when it only contains placeholder/example values,
but do not commit your real WiFi password or API key to a public repo.
"""

# WiFi credentials
WIFI_SSID = "YourWiFiName"
WIFI_PASSWORD = "YourWiFiPassword"

# OpenWeatherMap settings (create a free account at https://openweathermap.org)
# Generate an API key and paste it below.
OWM_API_KEY = "YOUR_OPENWEATHERMAP_API_KEY"

# Your location (ZIP + country code) for weather
OWM_ZIP = "15025"      # Jefferson Hills example
OWM_COUNTRY = "US"      # two-letter country code

# Location name shown at the top of the weather slide
LOCATION_NAME = "Jefferson Hills, PA"
