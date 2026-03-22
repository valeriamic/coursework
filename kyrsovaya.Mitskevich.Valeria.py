import requests
from datetime import datetime, timedelta

YANDEX_API_KEY = "f506b896-96e3-4439-b2cf-f72b18aace32"

def get_coords(city_name):
    clean_name = city_name.split(',')[0].strip()
    
    url = "https://geocoding-api.open-meteo.com/v1/search"
    params = {
        "name": clean_name,
        "count": 1,
        "language": "ru",
        "format": "json"
    }
    try:
        res = requests.get(url, params=params).json()
        if "results" in res:
            result = res["results"][0]
            return result["latitude"], result["longitude"], result.get("timezone", "UTC")
    except Exception as e:
        print(f"Ошибка геокодинга ({clean_name}): {e}")
    return None, None, "UTC"

def get_weather(lat, lon, target_dt_str, timezone):
    url = "https://api.open-meteo.com/v1/forecast"
    
    dt = datetime.fromisoformat(target_dt_str).replace(minute=0, second=0, microsecond=0)
    target_hour = dt.strftime("%Y-%m-%dT%H:%M")

    params = {
        "latitude": lat,
        "longitude": lon,
        "hourly": "temperature_2m,precipitation,windspeed_10m,visibility",
        "windspeed_unit": "ms",
        "timezone": timezone
    }
    
    try:
        res = requests.get(url, params=params).json()
        times = res['hourly']['time']
        if target_hour in times:
            idx = times.index(target_hour)
            return {
                "temp": res['hourly']['temperature_2m'][idx],
                "wind": res['hourly']['windspeed_10m'][idx],
                "prec": res['hourly']['precipitation'][idx],
                "vis": res['hourly']['visibility'][idx]
            }
    except:
        return None

tomorrow = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")

yandex_params = {
    "from": "c65",   
    "to": "c213",    
    "lang": "ru_RU",
    "date": tomorrow, 
    "apikey": YANDEX_API_KEY,
    "limit": 5
}

print(f"Запрос рейсов на {tomorrow}...")
resp = requests.get("https://api.rasp.yandex-net.ru/v3.0/search/", params=yandex_params)

if resp.status_code == 200:
    data = resp.json()
    segments = data.get('segments', [])
    
    city_from_name = data.get('search', {}).get('from', {}).get('title', 'Неизвестный город')
    
    lat, lon, tz = get_coords(city_from_name)
    
    if not segments:
        print(f"Рейсов из '{city_from_name}' не найдено.")
    elif not lat:
        print(f"Не удалось найти координаты для города: {city_from_name}")
    else:
        print(f"\nСинхронизация: {city_from_name} ({lat}, {lon}) ---")
        
        for i, seg in enumerate(segments, 1):
            title = seg['thread']['title']
            dep_time = seg['departure']
            t_type = seg['thread'].get('transport_type')

            weather = get_weather(lat, lon, dep_time, tz)

            print(f"\n{i}. {title} [{t_type}]")
            print(f"   Отправление: {dep_time}")
            
            if weather:
                w_str = f"{weather['temp']}°C, ветер {weather['wind']}м/с, вид. {weather['vis']}м"
                print(f"   Погода в момент старта: {w_str}")

                risks = []
                if t_type == 'plane' and weather['vis'] < 1000:
                    risks.append("НИЗКАЯ ВИДИМОСТЬ (Риск задержки вылета)")
                if t_type == 'bus' and weather['wind'] > 15:
                    risks.append("СИЛЬНЫЙ ВЕТЕР (Опасно для движения по трассе)")
                if weather['prec'] > 2:
                    risks.append("СИЛЬНЫЕ ОСАДКИ (Риск пробок/гололеда)")
                
                if risks:
                    print(f"   ⚠️  АНАЛИЗ: {'; '.join(risks)}")
                else:
                    print("   ✅ Условия благоприятные")
            else:
                print("   [!] Прогноз погоды недоступен")
else:
    print(f"Ошибка Яндекс.API: {resp.status_code} - {resp.text}")