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
URL = f"https://api.openweathermap.org/data/2.5/weather?lat={LAT}&lon={LON}&appid={API_KEY}&units=imperial"

# Commute Config
COMMUTE_MILES = 50 
GAS_PRICE = 4.65 
BASE_MPG = 25 

# --- MODULE: THE CRATE (Spotify Links) ---
DJ_CRATE = {
    "Chill": [
        ("Lofi Beats to Commute To", "https://open.spotify.com/playlist/37i9dQZF1DWWQRwui0ExPn"),
        ("Morning Acoustic", "https://open.spotify.com/playlist/37i9dQZF1DXdd3gw5Q7bvv"),
        ("Your Daily Drive", "https://open.spotify.com/playlist/37i9dQZF1EfWEQC7LgXhBq"),
        ("Classic Road Trip", "https://open.spotify.com/playlist/37i9dQZF1DX9wC1M4rUs0Y"),
        ("Calm Vibes", "https://open.spotify.com/playlist/37i9dQZF1DX1s9ktjPgPIV")
    ],
    "Medium": [
        ("Stuff You Should Know", "https://open.spotify.com/show/0ofXAdFIQQRsCYj9754UFx"),
        ("The Daily (News)", "https://open.spotify.com/show/3IM0elm96lSVz0OaOF1dM4"),
        ("Up First (NPR)", "https://open.spotify.com/show/230114"),
        ("SmartLess", "https://open.spotify.com/show/0Yq6GFJH2YgeJb0AD9U7Sj"),
        ("00s Rock Anthems", "https://open.spotify.com/playlist/37i9dQZF1DX3oM43CtKnRV")
    ],
    "Rage": [
        ("Limp Bizkit - Break Stuff", "https://open.spotify.com/track/5cZqsjVs6MevCnAkasbEOX"),
        ("Rage Against The Machine", "https://open.spotify.com/artist/2d0hyoQ5ynDBnkvAbDygOu"),
        ("High Octane Drift Phonk", "https://open.spotify.com/playlist/37i9dQZF1DXdOEFt9ZX0dh"),
        ("Doom Eternal Soundtrack", "https://open.spotify.com/album/53X6hMhdFsllCo77jPV28p"),
        ("Dan Carlin's Hardcore History", "https://open.spotify.com/show/72qiPaoDRf8HkGKEChvG5q")
    ]
}

# --- MODULE: GAS COST ---
def calculate_gas(misery_score):
    mpg_penalty = 1.0
    if misery_score >= 20: mpg_penalty = 0.6 
    elif misery_score >= 10: mpg_penalty = 0.8 
    real_mpg = BASE_MPG * mpg_penalty
    gallons = COMMUTE_MILES / real_mpg
    cost = gallons * GAS_PRICE
    return round(cost, 2)

# --- MODULE: DJ SELECTOR ---
def recommend_audio(misery_score):
    # Pick a category based on pain level
    if misery_score >= 20:
        category = "Rage"
    elif misery_score >= 10:
        category = "Medium"
    else:
        category = "Chill"
    
    # Pick a RANDOM item from that list
    selection = random.choice(DJ_CRATE[category])
    return selection # Returns ("Title", "URL")

@app.route('/scan', methods=['POST'])
def scan():
    try:
        data = request.json
        incident_count = len(data.get('incidents', []))

        # Weather
        response = requests.get(URL)
        weather_data = response.json()
        weather_main = weather_data.get('weather', [{}])[0].get('main', '')
        temp = weather_data.get('main', {}).get('temp', 0)
        wind_speed = weather_data.get('wind', {}).get('speed', 0)
        
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
        
        # DJ Selection (returns Title and Link)
        audio_title, audio_link = recommend_audio(misery_score)
        
        verdict = "Smooth"
        if misery_score > 10: verdict = "Annoying"
        if misery_score > 20: verdict = "DOOMED"

        return jsonify({
            "program": "Tardy Tracker v2.5",
            "verdict": verdict,
            "misery_score": misery_score,
            "reasons": reasons,
            "weather": weather_main,
            "gas_cost": f"${gas_cost}",
            "audio_title": audio_title,
            "audio_link": audio_link
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 500

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
