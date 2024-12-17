from flask import Flask, render_template, request, jsonify, session, url_for, redirect, send_file
import requests
import os
from gtts import gTTS
import spacy
from flask_session import Session
from io import BytesIO

app = Flask(__name__)
app.secret_key = 'your_secret_key'  # Replace with a secure secret key

# Configure session to use filesystem
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# Google Maps API Key (replace with your actual key)
GMAPS_API_KEY = 'Your google map API_KEY'

# Load spaCy language model
nlp = spacy.load("en_core_web_sm")

# List of destinations with coordinates
DESTINATIONS = {
    "Tech Park": {"lat": 12.824555, "lon": 80.045098},
    "HI-Tech": {"lat": 12.820791, "lon": 80.038933},
    "UB": {"lat": 12.823216, "lon": 80.042685},
    "T.P Ganesan Auditorium": {"lat": 12.824415, "lon": 80.046464},
    "University Building (UB)": {"lat": 12.823216, "lon": 80.042685},
    "NRI Hostel": {"lat": 12.823929, "lon": 80.042698},
    "JAVA canteen": {"lat": 12.823179, "lon": 80.044736},
    "BEL LAB": {"lat": 12.823258, "lon": 80.043577},
    "Car Parking - 1": {"lat": 12.824232, "lon": 80.043160},
    "Architecture Block": {"lat": 12.824164, "lon": 80.044258},
    "Bio Tech Block": {"lat": 12.824723, "lon": 80.044285},
    "C.V. Raman": {"lat": 12.825151, "lon": 80.044339},
    "T.P. Ground": {"lat": 12.824400, "lon": 80.045734},
    "SRM Hospital": {"lat": 12.822887, "lon": 80.047675},
    "SRM Medical College": {"lat": 12.821244, "lon": 80.047606},
    "Medical Canteen": {"lat": 12.821710, "lon": 80.047649},
    "M Block - Girls Hostel": {"lat": 12.821372, "lon": 80.045935},
    "SRM Hotel Management College": {"lat": 12.822674, "lon": 80.042557},
    "Science and Humanities Block": {"lat": 12.825100, "lon": 80.047296},
    "SRM Dental College": {"lat": 12.825090, "lon": 80.048219},
    "Dental Grounds": {"lat": 12.825372, "lon": 80.048907},
    "Mosque and Prayer Hall": {"lat": 12.821953, "lon": 80.044597},
    "Boys Hostel": {"lat": 12.822832, "lon": 80.043502},
    "SRM Hotel": {"lat": 12.823579, "lon": 80.041129},
    "SRM Potheri Police Station": {"lat": 12.821921, "lon": 80.038449},
    "CRC Block": {"lat": 12.820400, "lon": 80.037889},
    "SRM Valliammai": {"lat": 12.825225, "lon": 80.042670},
    "SRM Arts and Science": {"lat": 12.825175, "lon": 80.043155},
    "Estancia": {"lat": 12.827670, "lon": 80.048611},
    "Abode Valley": {"lat": 12.817325, "lon": 80.040313},
    "Potheri Railway Station": {"lat": 12.820806, "lon": 80.037140},
    "Vendhar Square": {"lat": 12.823094, "lon": 80.045208}
}

@app.route('/')
def index():
    # Clear session for a new chat
    session.clear()
    return render_template('chat.html')

@app.route('/get_response', methods=['POST'])
def get_response():
    user_message = request.json.get("message", "")
    print("Received message:", user_message)  # Debugging print

    # Step 1: Send Greeting and Initial Destination Options
    if 'origin' not in session:
        response_text = (
            "Hello! Welcome to the GPS Chatbot. Would you like to use your current location as the starting point? "
            "Or, please choose a destination below."
        )
        return jsonify({
            "response": response_text,
            "destinations": list(DESTINATIONS.keys()), 
            "show_location_button": True
        })

    # Step 2: Set Destination
    if 'destination' not in session:
        destination_name, destination_coords = extract_destination(user_message)
        if destination_coords:
            session['destination'] = destination_name
            session['destination_coords'] = destination_coords
            return jsonify({
                "response": f"You chose {destination_name}. Redirecting to the directions page...",
                "redirect": True
            })
        else:
            response_text = "I couldn't recognize the destination. Please select from the options below."
            return jsonify({
                "response": response_text,
                "destinations": list(DESTINATIONS.keys())
            })

    return jsonify({"response": "I'm sorry, I didn't understand that. Please try again."})

@app.route('/tts')
def tts():
    text = request.args.get("text", "")
    tts = gTTS(text=text, lang='en')
    audio_io = BytesIO()
    tts.save(audio_io)
    audio_io.seek(0)
    return send_file(audio_io, mimetype="audio/mpeg")

def extract_destination(message):
    """Extract destination name by finding partial, case-insensitive matches."""
    doc = nlp(message.lower())  # Parse message in lowercase
    user_words = [token.text for token in doc]  # Tokenize the message
    
    for name, coords in DESTINATIONS.items():
        name_lower = name.lower()  # Convert destination name to lowercase
        # Check if any word from the user's message is in the destination name
        if any(word in name_lower for word in user_words):
            return name, coords
    
    return None, None

@app.route('/set_origin', methods=['POST'])
def set_origin():
    # Set the origin as the current location provided by the user
    origin_lat = request.json.get("lat")
    origin_lon = request.json.get("lon")
    if origin_lat and origin_lon:  # Ensure lat and lon are provided
        session['origin'] = f"{origin_lat},{origin_lon}"
        return jsonify({
            "response": "Location set! Now, please tell me where you want to go.",
            "destinations": list(DESTINATIONS.keys())  # Send destinations in the response
        })
    return jsonify({"response": "Failed to set location. Please try again."}), 400

@app.route('/directions')
def directions():
    # Set default mode as walking
    mode = request.args.get("mode", "walking")
    session['mode'] = mode  # Store mode in session to retain selection on reload

    # Check if origin and destination are in session
    if 'origin' in session and 'destination' in session:
        origin = session['origin']
        destination_name = session['destination']
        destination_coords = session['destination_coords']

        # Generate Google Maps Directions API request
        directions_url = (
            f"https://maps.googleapis.com/maps/api/directions/json"
            f"?origin={origin}&destination={destination_coords['lat']},{destination_coords['lon']}"
            f"&mode={mode}&key={GMAPS_API_KEY}"
        )

        response = requests.get(directions_url)
        directions_data = response.json()

        # Extract steps from the directions API response
        if directions_data['status'] == 'OK':
            steps = [
                step['html_instructions'] for leg in directions_data['routes'][0]['legs']
                for step in leg['steps']
            ]
        else:
            steps = ["Directions could not be retrieved. Please try again."]

        # Generate TTS for audio directions
        directions_text = f"Directions to {destination_name} from your current location."
        tts = gTTS(text=directions_text, lang='en')
        audio_path = os.path.join("static/audio", "directions.mp3")
        tts.save(audio_path)

        # Generate Google Maps Embed URL for the selected mode
        embed_url = f"https://www.google.com/maps/embed/v1/directions?key={GMAPS_API_KEY}&origin={origin}&destination={destination_coords['lat']},{destination_coords['lon']}&mode={mode}"
        maps_url = f"https://www.google.com/maps/dir/?api=1&origin={origin}&destination={destination_coords['lat']},{destination_coords['lon']}&travelmode={mode}"

        return render_template(
            'directions.html',
            embed_url=embed_url,
            maps_url=maps_url,
            steps=steps,
            mode=mode
        )

    return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(debug=True, port=8000)
