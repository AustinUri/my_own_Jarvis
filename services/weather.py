from __future__ import annotations

import json
import urllib.parse
import urllib.request
from dataclasses import dataclass, asdict


WEATHER_CODES = {
    0: 'Clear sky', 1: 'Mainly clear', 2: 'Partly cloudy', 3: 'Overcast',
    45: 'Fog', 48: 'Rime fog', 51: 'Light drizzle', 53: 'Drizzle', 55: 'Heavy drizzle',
    61: 'Light rain', 63: 'Rain', 65: 'Heavy rain', 71: 'Light snow', 73: 'Snow', 75: 'Heavy snow',
    80: 'Rain showers', 81: 'Rain showers', 82: 'Heavy showers', 95: 'Thunderstorm', 96: 'Thunderstorm with hail', 99: 'Thunderstorm with hail',
}


@dataclass
class WeatherSnapshot:
    location: str
    temperature_c: float | None
    feels_like_c: float | None
    condition: str
    wind_kmh: float | None
    precipitation_mm: float | None
    today_high_c: float | None
    today_low_c: float | None
    rain_probability_pct: float | None

    def to_dict(self):
        return asdict(self)


class WeatherService:
    def __init__(self, config):
        self.config = config

    @staticmethod
    def _json(url: str, timeout: float = 10.0):
        req = urllib.request.Request(url, headers={'User-Agent': 'JarvisLocalAssistant/25'})
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return json.loads(r.read().decode('utf-8', errors='replace'))

    def get(self, location: str | None = None) -> WeatherSnapshot:
        name = (location or getattr(self.config, 'weather_location', '') or '').strip()
        if not name:
            raise RuntimeError('Weather location is not configured. Set it once in JARVIS Settings.')
        geo = 'https://geocoding-api.open-meteo.com/v1/search?' + urllib.parse.urlencode({'name': name, 'count': 1, 'language': 'en', 'format': 'json'})
        data = self._json(geo)
        results = data.get('results') or []
        if not results:
            raise RuntimeError(f'Could not resolve weather location: {name}')
        place = results[0]
        lat, lon = place['latitude'], place['longitude']
        display = ', '.join(x for x in [str(place.get('name') or ''), str(place.get('admin1') or ''), str(place.get('country') or '')] if x)
        params = {
            'latitude': lat, 'longitude': lon, 'timezone': 'auto', 'forecast_days': 3,
            'current': 'temperature_2m,apparent_temperature,precipitation,weather_code,wind_speed_10m',
            'daily': 'temperature_2m_max,temperature_2m_min,precipitation_probability_max,weather_code',
        }
        forecast = self._json('https://api.open-meteo.com/v1/forecast?' + urllib.parse.urlencode(params))
        current = forecast.get('current') or {}
        daily = forecast.get('daily') or {}
        def first(key):
            value = daily.get(key)
            return value[0] if isinstance(value, list) and value else None
        code = int(current.get('weather_code') or first('weather_code') or 0)
        return WeatherSnapshot(
            location=display or name,
            temperature_c=current.get('temperature_2m'),
            feels_like_c=current.get('apparent_temperature'),
            condition=WEATHER_CODES.get(code, f'Weather code {code}'),
            wind_kmh=current.get('wind_speed_10m'),
            precipitation_mm=current.get('precipitation'),
            today_high_c=first('temperature_2m_max'),
            today_low_c=first('temperature_2m_min'),
            rain_probability_pct=first('precipitation_probability_max'),
        )
