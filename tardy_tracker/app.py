import os
import requests
import random
from flask import Flask, jsonify, request, send_file
from staticmap import StaticMap, CircleMarker

app = Flask(__name__)

# --- CONFIGURATION ---
API_KEY = os.environ.get('OPENWEATHER_API_KEY', 'YOUR_KEY_HERE')
LAT = 34.1815
LON = -117.3229
# Using 5-Day Forecast API to get future times
URL = f"https://api.openweathermap.org/data/2.5/forecast?lat={LAT}&lon={LON}&appid={API_KEY}&units=imperial"

# Commute Config
COMMUTE_MILES = 56 
GAS_PRICE = 4.75 
BASE_MPG = 24 

# --- MODULE: THE DJ CRATE (Restored) ---
DJ_CRATE = {
    "Chill": [
        ("Lofi Beats to Commute To", "https://open.spotify.com/playlist/37i9dQZF1DWWQRwui0ExPn"),
        ("Morning Acoustic", "https://open.spotify.com/playlist/37i9dQZF1DXdd3gw5Q7bvv"),
        ("Your Daily Drive", "https://open.spotify.com/playlist/37i9dQZF1E34Ucml4hhx1w"),
        ("Calm Vibes", "https://open.spotify.com/playlist/37i9dQZF1DX1s9ktjP51O3")
    ],
    "Medium": [
        ("Stuff You Should Know", "https://open.spotify.com/show/0ofXAdFIQQRsCYj9754UFx"),
        ("The Daily (News)", "https://open.spotify.com/show/3IM0jmZmpBS5qkhmX5I7H2"),
        ("Up First (NPR)", "https://open.spotify.com/show/230f4YrW9Y0yKgXF8qB9pZ"),
        ("00s Rock Anthems", "https://open.spotify.com/playlist/37i9dQZF1DX3oM43CtKnRV")
    ],
    "Rage": [
        ("Limp Bizkit - Break Stuff", "https://open.spotify.com/track/5n0CTysih20NYdT2S0Wpe8"),
        ("Rage Against The Machine", "https://open.spotify.com/artist/2d0hyoQ5ynDBnkvAbDygOu"),
        ("High Octane Drift Phonk", "https://open.spotify.com/playlist/37i9dQZF1DXdOEFt9ZX0dh"),
        ("Doom Eternal Soundtrack", "https://open.spotify.com/album/53X6hMhdFsllCo77jPV28p"),
        ("Dan Carlin's Hardcore History", "https://open.spotify.com/show/72qiPaoDRf8HkG65cqqVIl")
    ]
}

# --- MODULE: TIME TRAVELER (Fixed Formatting) ---
def get_forecast_timeline(data):
    timeline_str = []
    # We look for these exact timestamps in the API response
    target_times = {
        "09:00:00": "9:00 AM",
        "12:00:00": "12:00 PM",
        "15:00:00": "3:00 PM"
    }
    
    # Loop through the forecast list
    for item in data.get('list', []):
        dt_txt = item.get('dt_txt', '') # e.g. "2025-12-02 09:00:00"
        time_part = dt_txt.split(' ')[1] 
        
        if time_part in target_times:
            temp = int(item['main']['temp'])
            condition = item['weather'][0]['main']
            
            # Icon Logic
            icon = "☁️"
            if "Clear" in condition: icon = "☀️"
            if "Rain" in condition: icon = "🌧️"
            
            # Format: "9:00 AM: ☀️ 75°F"
            nice_time = target_times[time_part]
            timeline_str.append(f"{nice_time}: {icon} {temp}°F")
            
            # Stop if we have found all 3
            if len(timeline_str) >= 3:
                break
                
    return " | ".join(timeline_str)

# --- MODULE: CALCULATIONS ---
def calculate_gas(misery_score):
    mpg_penalty = 1.0
    if misery_score >= 20: mpg_penalty = 0.6 
    elif misery_score >= 10: mpg_penalty = 0.8 
    real_mpg = BASE_MPG * mpg_penalty
    gallons = COMMUTE_MILES / real_mpg
    cost = gallons * GAS_PRICE
    return round(cost, 2)

def recommend_audio(misery_score):
    if misery_score >= 20: category = "Rage"
    elif misery_score >= 10: category = "Medium"
    else: category = "Chill"
    
    return random.choice(DJ_CRATE[category])

# --- MAIN ENDPOINT ---
@app.route('/scan', methods=['POST'])
def scan():
    try:
        data = request.json
        incident_count = len(data.get('incidents', []))

        # 1. Call Forecast API
        response = requests.get(URL)
        response.raise_for_status()
        weather_data = response.json()
        
        # Current Weather (First Item)
        current = weather_data['list'][0]
        weather_main = current['weather'][0]['main']
        temp = current['main']['temp']
        wind_speed = current['wind']['speed']
        
        # 2. Get Future Forecast (9am, 12pm, 3pm)
        forecast_string = get_forecast_timeline(weather_data)
        
        misery_score = 0
        reasons = []

        if wind_speed > 20:
            misery_score += 10
            reasons.append("High Wind")
        if 'Rain' in weather_main:
            misery_score += 10
            reasons.append("Rain")
        if temp > 90:
            misery_score += 10
            reasons.append("Heat")
        if incident_count > 5:
            misery_score += 20
            reasons.append(f"Traffic ({incident_count} accidents)")

        gas_cost = calculate_gas(misery_score)
        
        # DJ Selection returns (Title, Link)
        audio_title, audio_link = recommend_audio(misery_score)

        verdict = "Smooth"
        if misery_score > 10: verdict = "Annoying"
        if misery_score > 20: verdict = "DOOMED"

        return jsonify({
            "program": "Tardy Tracker v4.0",
            "verdict": verdict,
            "misery_score": misery_score,
            "reasons": reasons,
            "current_weather": weather_main,
            "future_forecast": forecast_string,
            "gas_cost": f"${gas_cost}",
            "audio_title": audio_title,
            "audio_link": audio_link
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 500

# --- MAP ENDPOINT ---
@app.route('/draw_map', methods=['POST'])
def draw_map():
    try:
        data = request.json
        incidents = data.get('incidents', [])
        m = StaticMap(800, 600)
        for incident in incidents:
            if 'clean_latitude' in incident and 'clean_longitude' in incident:
                lat = float(incident['clean_latitude'])
                lon = float(incident['clean_longitude'])
                marker = CircleMarker((lon, lat), 'red', 10)
                m.add_marker(marker)
        image = m.render()
        image.save('traffic_map.png')
        return send_file('traffic_map.png', mimetype='image/png')
    except Exception as e:
        return jsonify({"error": str(e)})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5001)