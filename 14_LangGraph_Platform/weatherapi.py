import requests
import os
import dotenv

dotenv.load_dotenv()

class WeatherClient:
    def __init__(self, api_key: str = None):
        self.api_key = api_key or os.getenv("WEATHERAPI_API_KEY")
        self.base_url = "https://api.weatherapi.com/v1"

    def get_current_weather(self, location: str) -> str:
        url = f"{self.base_url}/current.json"
        params = {"key": self.api_key, "q": location}
        response = requests.get(url, params=params)
        response.raise_for_status()
        data = response.json()

        location_info = data["location"]
        current = data["current"]

        return (
            f"{location_info['name']}, {location_info['region']} ({location_info['country']}): "
            f"{current['temp_f']}°F, {current['condition']['text']}"
        )
