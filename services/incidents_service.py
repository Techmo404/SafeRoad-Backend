import requests

class IncidentService:

    def get_incidents(self, lat, lng):
        url = f"https://api.tomtom.com/traffic/services/5/incidentDetails"
        params = {
            "bbox": f"{lng-0.1},{lat-0.1},{lng+0.1},{lat+0.1}",
            "fields": "id,geometry,properties,type,severity",
            "key": "TU_TOMTOM_KEY"
        }
        return requests.get(url, params=params).json()
