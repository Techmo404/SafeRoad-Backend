import requests
import os

class TrafficService:

    BASE_URL = "https://api.tomtom.com/traffic/services/4/flowSegmentData/absolute/10/json"

    # Límites esperados según tipo de calle
    ROAD_LIMITS = {
        "MOTORWAY": 120,
        "TRUNK": 100,
        "PRIMARY": 80,
        "SECONDARY": 60,
        "TERTIARY": 50,
        "RESIDENTIAL": 30,
        "SERVICE": 20,
        "LOCAL": 25,
        "UNKNOWN": 50
    }

    def get_traffic(self, lat, lng):
        key = os.getenv("TOMTOM_API_KEY")

        if not key:
            return {"error": "API KEY missing in .env", "source": "error"}

        params = {
            "point": f"{lat},{lng}",
            "unit": "KMPH",
            "key": key,
        }

        try:
            response = requests.get(self.BASE_URL, params=params)
            data = response.json()

            if "flowSegmentData" not in data:
                return {"error": data, "source": "tomtom"}

            segment = data["flowSegmentData"]

            speed = segment.get("currentSpeed")
            road_type = segment.get("roadType", "UNKNOWN").upper()
            expected_limit = self.ROAD_LIMITS.get(road_type, 50)

            # 🧠 Corrección: si TomTom reporta 100+ en zonas residenciales → ajustar
            if speed and speed > expected_limit:
                speed = expected_limit

            # Si no viene jamFactor → calcularlo manualmente
            jam_factor = segment.get("jamFactor")
            if jam_factor is None and speed and expected_limit:
                jam_factor = round((1 - (speed / expected_limit)) * 10, 2)

            status = (
                "🔴 Congestión grave" if jam_factor and jam_factor > 7 else
                "🟠 Tráfico moderado" if jam_factor and jam_factor > 4 else
                "🟢 Fluido"
            )

            return {
                "speed": speed,
                "free_speed": expected_limit,
                "road_type": road_type,
                "jam_factor": jam_factor,
                "confidence": segment.get("confidence"),
                "status": status,
                "source": "tomtom"
            }

        except Exception as e:
            return {"error": str(e), "source": "exception"}
