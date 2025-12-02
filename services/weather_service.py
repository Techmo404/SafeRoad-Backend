import requests
import os

class WeatherService:
    BASE_URL = "https://api.openweathermap.org/data/2.5/weather"

    def get_weather(self, lat, lng):
        params = {
            "lat": lat,
            "lon": lng,
            "appid": os.getenv("WEATHER_API_KEY"),
            "units": "metric"
        }
        return requests.get(self.BASE_URL, params=params).json()
