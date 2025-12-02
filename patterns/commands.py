from abc import ABC, abstractmethod


#clase base
class AlertCommand(ABC):
    @abstractmethod
    def execute(self, context):
        """Debe retornar dict con {score:int, alerts:[...] }"""
        pass


#Evaluacion clima
class WeatherRiskCommand(AlertCommand):
    def execute(self, ctx):

        weather = ctx.get("weather", {})
        main = weather.get("weather", [{}])[0].get("main", "").lower()
        temp = weather.get("main", {}).get("temp", None)
        visibility = weather.get("visibility", 10000)
        wind_speed = weather.get("wind", {}).get("speed", 0)

        alerts = []
        score = 0  
        if main in ["rain", "snow", "thunderstorm"]:
            alerts.append(f" Clima peligroso: {main}")
            score += 12

        if visibility < 3000:
            alerts.append("Baja visibilidad")
            score += 8

        if temp is not None and temp < 5:
            alerts.append("Riesgo de hielo")
            score += 5

        if temp is not None and temp > 33:
            alerts.append(" Calor extremo — riesgo de fatiga")
            score += 5

        if wind_speed > 30:
            alerts.append(" Viento fuerte — riesgo para motos/ciclistas")
            score += 8

        return {"score": min(score, 30), "alerts": alerts}


#evaluacion trafico
class TrafficRiskCommand(AlertCommand):
    def execute(self, ctx):

        traffic = ctx.get("traffic", {})
        speed = traffic.get("speed")
        limit = traffic.get("free_speed")
        jam = traffic.get("jam_factor", None)
        confidence = traffic.get("confidence", 1)

        if speed is None or limit is None:
            return {"score": 0, "alerts": [" Sin datos confiables de tráfico"]}

        alerts = []

        score = int(min(jam or 0, 10) * 5)  
        if jam is not None:
            if jam >= 8:
                alerts.append(" Congestión severa")
            elif jam >= 5:
                alerts.append(" Tráfico pesado")
            elif jam >= 3:
                alerts.append("Circulación lenta")

        # Datos poco confiable
        if confidence < 0.50:
            alerts.append(" Datos poco confiables — verifique tráfico real")
            score += 5

        return {"score": min(score, 50), "alerts": alerts}
