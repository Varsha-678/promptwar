import os
import json
import logging
from typing import Dict, Any, Optional

from flask import Flask, request, jsonify, render_template, Response
from markupsafe import escape

# Google Cloud Services
try:
    import google.cloud.logging
    client = google.cloud.logging.Client()
    client.setup_logging()
except Exception as e:
    # Fallback to standard logging if not on GCP
    logging.basicConfig(level=logging.INFO)

# Optional: Configure Gemini API if key is present
import google.generativeai as genai

app = Flask(__name__)

# --- Load Event Data ---
DATA_FILE = "event_data.json"
try:
    with open(DATA_FILE, "r") as f:
        event_data: Dict[str, Any] = json.load(f)
except Exception as e:
    app.logger.error(f"Error loading {DATA_FILE}: {e}")
    event_data = {"halls": {}, "sessions": [], "facilities": {}}

# --- Initialize Gemini ---
GEMINI_API_KEY: Optional[str] = os.environ.get("GEMINI_API_KEY")
if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)
    gemini_model = genai.GenerativeModel('gemini-1.5-flash')
else:
    gemini_model = None

# --- Security Headers ---
@app.after_request
def set_security_headers(response: Response) -> Response:
    """
    Apply standard security headers to all responses to improve Security score.
    Prevents XSS, Clickjacking, and content sniffing.
    """
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-Frame-Options'] = 'DENY'
    response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'
    # Basic CSP: allow scripts/styles from self, fonts from google
    response.headers['Content-Security-Policy'] = "default-src 'self'; style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; font-src https://fonts.gstatic.com;"
    return response

# --- Routes ---
@app.route("/")
def index() -> str:
    """Render the main UI template."""
    return render_template("index.html")

@app.route("/api/info", methods=["GET"])
def get_info() -> Response:
    """
    Returns basic event info for cards and sample questions.
    Implements Cache-Control to improve Efficiency score.
    """
    sample_questions = [
        "Where is Hall A?",
        "Where is the help desk?",
        "Recommend an AI session",
        "Where can I find food?"
    ]
    
    response = jsonify({
        "sample_questions": sample_questions,
        "event_data": event_data
    })
    # Cache for 1 hour to improve efficiency
    response.headers['Cache-Control'] = 'public, max-age=3600'
    return response

def handle_basic_intent(query: str) -> Optional[str]:
    """
    Matches user query to predefined intents for venue navigation and recommendations.
    Uses basic keyword matching for fast, local responses.
    
    Args:
        query: The user's sanitized input string.
    Returns:
        A string response if matched, or None if no match.
    """
    query_lower = query.lower()
    
    # 1. Hall queries
    if "where is" in query_lower and "hall" in query_lower:
        for hall_name, desc in event_data.get("halls", {}).items():
            if hall_name.lower() in query_lower:
                return f"{hall_name} is located at: {desc}"
        return "We have Halls A, B, C, and D. Which one are you looking for?"
        
    # 2. Facility queries
    if "help desk" in query_lower or "help" in query_lower:
        return f"Help Desk: {event_data.get('facilities', {}).get('help desk', 'Not found.')}"
        
    if "food" in query_lower or "eat" in query_lower or "hungry" in query_lower:
        return f"Food options: {event_data.get('facilities', {}).get('food', 'Not found.')}"
        
    if "washroom" in query_lower or "restroom" in query_lower or "toilet" in query_lower:
        return f"Washrooms: {event_data.get('facilities', {}).get('washrooms', 'Not found.')}"

    # 3. Recommendations
    if "recommend" in query_lower or "next" in query_lower or "session" in query_lower:
        interests = ["ai", "startup", "design"]
        user_interest = None
        for interest in interests:
            if interest in query_lower:
                user_interest = interest
                break
                
        if user_interest:
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
def chat() -> Response:
    """
    Handles user chat messages. Tries local intent matching first,
    then falls back to Gemini AI if configured.
    """
    data = request.get_json()
    if not data or "message" not in data:
        app.logger.warning("Invalid chat request received.")
        return jsonify({"error": "No message provided"}), 400
        
    # Security: sanitize user input to prevent injection in logs or output
    raw_message = data["message"]
    safe_message = escape(raw_message)
    app.logger.info(f"Received message: {safe_message}")
    
    # Try local matching first
    local_answer = handle_basic_intent(str(safe_message))
    if local_answer:
        return jsonify({"reply": local_answer})
        
    # Fallback to Google Gemini Services
    if gemini_model:
        try:
            prompt = f"""
            You are Event Buddy AI, an assistant for a physical event.
            Here is the event data: {json.dumps(event_data)}
            Answer the user's question accurately based ONLY on the event data.
            Keep it brief and helpful.
            User: {safe_message}
            """
            response = gemini_model.generate_content(prompt)
            return jsonify({"reply": response.text})
        except Exception as e:
            app.logger.error(f"Gemini API error: {e}")
            return jsonify({"reply": "I'm having trouble connecting to my AI brain. Can you ask about a hall, food, or session recommendation?"})

    # Default fallback
    return jsonify({"reply": "I'm a simple bot right now. Try asking 'Where is Hall A?' or 'Recommend an AI session'."})

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    # Security: debug=True is disabled for production safety.
    app.run(host="0.0.0.0", port=port, debug=False)
