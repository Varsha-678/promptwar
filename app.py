import os
import json
import logging
from flask import Flask, request, jsonify, render_template

# Optional: Configure Gemini API if key is present
import google.generativeai as genai

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)

# Load event data
DATA_FILE = "event_data.json"
try:
    with open(DATA_FILE, "r") as f:
        event_data = json.load(f)
except Exception as e:
    app.logger.error(f"Error loading {DATA_FILE}: {e}")
    event_data = {"halls": {}, "sessions": [], "facilities": {}}

# Initialize Gemini if key exists
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)
    gemini_model = genai.GenerativeModel('gemini-1.5-flash')
else:
    gemini_model = None

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/api/info", methods=["GET"])
def get_info():
    """Returns basic event info for cards and sample questions."""
    sample_questions = [
        "Where is Hall A?",
        "Where is the help desk?",
        "Recommend an AI session",
        "Where can I find food?"
    ]
    
    return jsonify({
        "sample_questions": sample_questions,
        "event_data": event_data
    })

def handle_basic_intent(query):
    query = query.lower()
    
    # 1. Hall queries
    if "where is" in query and "hall" in query:
        for hall_name, desc in event_data.get("halls", {}).items():
            if hall_name.lower() in query:
                return f"{hall_name} is located at: {desc}"
        return "We have Halls A, B, C, and D. Which one are you looking for?"
        
    # 2. Facility queries
    if "help desk" in query or "help" in query:
        return f"Help Desk: {event_data.get('facilities', {}).get('help desk', 'Not found.')}"
        
    if "food" in query or "eat" in query or "hungry" in query:
        return f"Food options: {event_data.get('facilities', {}).get('food', 'Not found.')}"
        
    if "washroom" in query or "restroom" in query or "toilet" in query:
        return f"Washrooms: {event_data.get('facilities', {}).get('washrooms', 'Not found.')}"

    # 3. Recommendations
    if "recommend" in query or "next" in query or "session" in query:
        interests = ["ai", "startup", "design"]
        user_interest = None
        for interest in interests:
            if interest in query:
                user_interest = interest
                break
                
        if user_interest:
            # Find matching session
            matching = [s for s in event_data.get("sessions", []) if s.get("tag", "").lower() == user_interest]
            if matching:
                s = matching[0]
                return f"I recommend: '{s['title']}' at {s['time']} in {s['hall']}."
            else:
                return f"I couldn't find any sessions for {user_interest} right now."
        else:
            return "What are you interested in? (e.g., AI, Design, Startup) so I can recommend a session!"
            
    return None

@app.route("/chat", methods=["POST"])
def chat():
    data = request.get_json()
    if not data or "message" not in data:
        return jsonify({"error": "No message provided"}), 400
        
    user_message = data["message"]
    
    # Try local matching first
    local_answer = handle_basic_intent(user_message)
    if local_answer:
        return jsonify({"reply": local_answer})
        
    # Fallback to Gemini if configured
    if gemini_model:
        try:
            # Provide context to Gemini
            prompt = f"""
            You are Event Buddy AI, an assistant for a physical event.
            Here is the event data: {json.dumps(event_data)}
            Answer the user's question accurately based ONLY on the event data.
            Keep it brief and helpful.
            User: {user_message}
            """
            response = gemini_model.generate_content(prompt)
            return jsonify({"reply": response.text})
        except Exception as e:
            app.logger.error(f"Gemini error: {e}")
            return jsonify({"reply": "I'm having trouble connecting to my AI brain. Can you ask about a hall, food, or session recommendation?"})

    # Default fallback
    return jsonify({"reply": "I'm a simple bot right now. Try asking 'Where is Hall A?' or 'Recommend an AI session'."})

if __name__ == "__main__":
    # Use PORT environment variable for Cloud Run
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port, debug=True)
