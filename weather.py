import os
import requests

BASE_URL = "https://api.openweathermap.org/data/2.5"


def _call_api(endpoint, city, units):
    """Returns (data, error). One of them is always None."""
    api_key = os.getenv("OWM_API_KEY")
    if not api_key:
        return None, "API key not found. Please set OWM_API_KEY."

    params = {"q": city, "appid": api_key, "units": units}

    try:
        response = requests.get(f"{BASE_URL}/{endpoint}", params=params, timeout=10)
    except requests.exceptions.RequestException:
        return None, "Could not connect. Please check your internet."

    if response.status_code == 200:
        return response.json(), None
    if response.status_code == 404:
        return None, "City not found. Please check the spelling."
    if response.status_code == 401:
        return None, "Invalid or not-yet-active API key."
    return None, f"Something went wrong (code {response.status_code})."


def get_weather(city, units="metric"):
    return _call_api("weather", city, units)


def get_forecast(city, units="metric"):
    return _call_api("forecast", city, units)