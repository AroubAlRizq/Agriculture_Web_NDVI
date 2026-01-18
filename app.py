import requests
from flask import Flask, render_template, request, jsonify
from datetime import datetime

app = Flask(__name__)

# --- Configuration: Saudi Cities ---
SAUDI_CITIES = {
    "riyadh": {"lat": 24.7136, "lon": 46.6753},
    "jeddah": {"lat": 21.5433, "lon": 39.1728},
    "dammam": {"lat": 26.4207, "lon": 50.0888},
    "al_hassa": {"lat": 25.3800, "lon": 49.5888},
    "qatif": {"lat": 26.5652, "lon": 50.0121},
    "taif": {"lat": 21.2854, "lon": 40.4222},
    "madinah": {"lat": 24.5247, "lon": 39.5692},
    "buraidah": {"lat": 26.3592, "lon": 43.9818},
    "abha": {"lat": 18.2068, "lon": 42.5109},
    "hail": {"lat": 27.5114, "lon": 41.7208},
    "jazan": {"lat": 16.8894, "lon": 42.5706},
    "najran": {"lat": 17.4917, "lon": 44.1322},
    "tabuk": {"lat": 28.3835, "lon": 36.5662},
    "jouf": {"lat": 29.9539, "lon": 40.1970}
}

@app.route('/')
def index():
    return render_template('index.html', cities=SAUDI_CITIES)

@app.route('/assess', methods=['POST'])
def assess_risk():
    try:
        data = request.json
        city_key = data.get('city')
        
        # Defaults
        today = datetime.now()
        month = today.month
        
        if city_key not in SAUDI_CITIES: return jsonify({'error': "Invalid City"})
        
        coords = SAUDI_CITIES[city_key]
        
        # --- FAILSAFE WEATHER FETCHING ---
        weather = get_weather_primary(coords['lat'], coords['lon'])
        
        if not weather:
            print(f"Primary API failed for {city_key}. Switching to Backup...")
            weather = get_weather_backup(coords['lat'], coords['lon'])
            
        if not weather: 
            return jsonify({'error': "Both Primary and Backup Weather Services are unavailable."})

        # --- SAFETY EXTRACTION ---
        temp = weather.get('temp') or 25.0
        humidity = weather.get('humidity') or 40.0
        rain = weather.get('rain') or 0.0
        wind = weather.get('wind') or 5.0
        dew_point = weather.get('dew_point') or 10.0
        pressure = weather.get('pressure') or 1013.0
        vis = weather.get('visibility') or 10000.0 

        # Derived Logic
        dew_spread = temp - dew_point
        dew_forming = dew_spread < 2.5
        is_dusty = (vis < 5000) and (humidity < 50)
        
        findings = []

        # --- 1. Graphiola Leaf Spot ---
        g_level = "Low"
        g_reason = f"Humidity ({humidity}%) is insufficient."
        if dew_forming or rain > 0.5:
            if 20 <= temp <= 35:
                g_level = "Critical"
                g_reason = f"Dew detected (Spread {round(dew_spread,1)}°C) + Optimal Temp."
            else:
                g_level = "Moderate"
                g_reason = "Moisture present, but temp is non-optimal."
        elif humidity > 75:
            g_level = "High"
            g_reason = "High atmospheric humidity favors growth."
        findings.append({"name": "Graphiola Leaf Spot", "level": g_level, "reason": g_reason})

        # --- 2. White Scale ---
        ws_level = "Low"
        ws_reason = "Conditions stable."
        if 28 <= temp <= 36:
            ws_level = "High"
            ws_reason = f"Temp ({temp}°C) is optimal for breeding."
            if is_dusty:
                ws_level = "Very High"
                ws_reason = "Dust storm protects pests from predators."
        elif temp > 38:
            ws_level = "Low"
            ws_reason = "High heat causes pest mortality."
        findings.append({"name": "White Scale", "level": ws_level, "reason": ws_reason})

        # --- 3. Red Palm Weevil ---
        rpw_level = "Low"
        rpw_reason = "Dormant."
        if 18 <= temp <= 40:
            rpw_level = "High"
            rpw_reason = "Active flight temperature range."
            if wind > 20:
                rpw_level = "Moderate"
                rpw_reason = f"Flight reduced by High Wind ({wind} km/h)."
            if is_dusty:
                rpw_level = "Low"
                rpw_reason = "Grounded by low visibility/dust."
        findings.append({"name": "Red Palm Weevil", "level": rpw_level, "reason": rpw_reason})

        # --- 4. Khamedj Disease ---
        k_level = "Low"
        is_season = month in [2, 3, 4]
        if is_season:
            if pressure < 1008:
                k_level = "High"
                k_reason = f"Storm Alert (Pressure {pressure} hPa)."
            elif rain > 2.0:
                k_level = "High"
                k_reason = "Rain detected during Spathe Season."
            else:
                k_level = "Moderate"
                k_reason = "Spathe season active."
        else:
            k_level = "Low"
            k_reason = "Not Spathe emergence season (Spring)."
        findings.append({"name": "Khamedj Disease", "level": k_level, "reason": k_reason})

        # --- 5. Al Wijam ---
        aw_level = "Low"
        aw_reason = "Not a known vector zone."
        if city_key in ["al_hassa", "qatif", "hofuf"]:
            if 25 <= temp <= 35:
                aw_level = "High"
                aw_reason = "Endemic Zone + Vector Active."
            else:
                aw_level = "Moderate"
                aw_reason = "Endemic Zone (Vector dormant)."
        findings.append({"name": "Al Wijam", "level": aw_level, "reason": aw_reason})

        # --- HTML Generator ---
        html_output = "<ul class='risk-list'>"
        for item in findings:
            css_class = "risk-low"
            if "Moderate" in item['level']: css_class = "risk-mod"
            if "High" in item['level'] or "Critical" in item['level']: css_class = "risk-high"
            
            html_output += f"""
            <li class='{css_class}'>
                <div class='risk-header'>
                    <strong>{item['name']}</strong>
                    <span class='badge'>{item['level']}</span>
                </div>
                <span class='reason'>{item['reason']}</span>
            </li>
            """
        html_output += "</ul>"

        summary = {
            "temp": temp, "rh": humidity, "dew": dew_point,
            "vis": round(vis/1000, 1), "pressure": pressure, "wind": wind
        }
        
        return jsonify({'result': html_output, 'weather_summary': summary})

    except Exception as e:
        print(f"SERVER ERROR: {e}")
        return jsonify({'error': f"Server Error: {str(e)}"})


# --- API 1: OPEN-METEO (Primary) ---
def get_weather_primary(lat, lon):
    try:
        url = "https://api.open-meteo.com/v1/forecast"
        params = {
            "latitude": lat, "longitude": lon,
            "current": "temperature_2m,relative_humidity_2m,rain,wind_speed_10m,dew_point_2m,surface_pressure,visibility",
            "timezone": "auto"
        }
        response = requests.get(url, params=params, timeout=3) # Short timeout
        data = response.json()
        curr = data.get('current', {})
        
        # Verify we actually got data, otherwise return None to trigger backup
        if not curr.get('temperature_2m'): return None

        return {
            "temp": curr.get('temperature_2m'),
            "humidity": curr.get('relative_humidity_2m'),
            "rain": curr.get('rain'),
            "wind": curr.get('wind_speed_10m'),
            "dew_point": curr.get('dew_point_2m'),
            "pressure": curr.get('surface_pressure'),
            "visibility": curr.get('visibility')
        }
    except Exception as e:
        print(f"Primary API Error: {e}")
        return None


# --- API 2: MET.NO / YR (Backup) ---
def get_weather_backup(lat, lon):
    try:
        # Met.no requires a User-Agent header
        url = "https://api.met.no/weatherapi/locationforecast/2.0/compact"
        headers = {"User-Agent": "NakheelGuard/1.0 github.com/AroubAlRizq"}
        params = {"lat": lat, "lon": lon}
        
        response = requests.get(url, headers=headers, params=params, timeout=5)
        data = response.json()
        
        # Parse the complex Met.no structure
        timeseries = data['properties']['timeseries'][0]
        curr = timeseries['data']['instant']['details']
        
        # Try to find rain in the 'next 1 hour' block
        rain_val = 0.0
        try:
            rain_val = timeseries['data']['next_1_hours']['details']['precipitation_amount']
        except:
            rain_val = 0.0

        return {
            "temp": curr.get('air_temperature'),
            "humidity": curr.get('relative_humidity'),
            "rain": rain_val,
            "wind": curr.get('wind_speed'),
            "dew_point": curr.get('dew_point_temperature'),
            "pressure": curr.get('air_pressure_at_sea_level'),
            # Met.no compact doesn't usually send visibility, default to 10km (Clear)
            "visibility": 10000.0 
        }
    except Exception as e:
        print(f"Backup API Error: {e}")
        return None

if __name__ == '__main__':
    app.run(debug=True, port=5001)
