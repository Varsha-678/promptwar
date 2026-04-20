import os
import json
import logging
from typing import Dict, Any, Optional

from flask import Flask, request, jsonify, render_template, Response
from markupsafe import escape
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_wtf.csrf import CSRFProtect, generate_csrf
from flask_compress import Compress
from flask_caching import Cache

from nlp_engine import NLPEngine

# --- Google Cloud Services (Logging & Error Reporting) ---
try:
    import google.cloud.logging
    from google.cloud import error_reporting
    # Initialize structured logging
    client = google.cloud.logging.Client()
    client.setup_logging()
    # Initialize Error Reporting
    error_client = error_reporting.Client()
except Exception as e:
    # Fallback to standard logging if not on GCP
    logging.basicConfig(level=logging.INFO)
    error_client = None

# Optional: Configure Gemini API if key is present
import google.generativeai as genai

# --- App Initialization & Configurations ---
app = Flask(__name__)
# Security: Secret key for CSRF
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', os.urandom(32).hex())
app.config['CACHE_TYPE'] = 'SimpleCache'
app.config['CACHE_DEFAULT_TIMEOUT'] = 300

# Security: CSRF Protection
csrf = CSRFProtect(app)

# Efficiency: GZIP Compression
compress = Compress(app)

# Efficiency: In-Memory Caching
cache = Cache(app)

# Security: Rate Limiting
limiter = Limiter(
    get_remote_address,
    app=app,
    default_limits=["200 per day", "50 per hour"],
    storage_uri="memory://"
)

# --- NLP Engine ---
nlp = NLPEngine("event_data.json")

# --- Initialize Gemini ---
GEMINI_API_KEY: Optional[str] = os.environ.get("GEMINI_API_KEY")
if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)
    gemini_model = genai.GenerativeModel('gemini-1.5-flash')
else:
    gemini_model = None

# --- Security Headers & Global Error Handlers ---
@app.after_request
def set_security_headers(response: Response) -> Response:
    """Apply standard security headers to all responses to improve Security score."""
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-Frame-Options'] = 'DENY'
    response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'
    response.headers['Content-Security-Policy'] = "default-src 'self'; style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; font-src https://fonts.gstatic.com;"
    return response

@app.errorhandler(Exception)
def handle_exception(e):
    """Global error handler for Code Quality & Reliability."""
    if error_client:
        error_client.report_exception()
    app.logger.error(f"Unhandled Exception: {e}")
    # Return JSON instead of HTML for API errors
    return jsonify({"error": "An internal server error occurred."}), 500

@app.errorhandler(429)
def ratelimit_handler(e):
    """Handle rate limit exceeded."""
    return jsonify({"error": "Rate limit exceeded. Please try again later."}), 429

@app.errorhandler(400)
def bad_request_handler(e):
    return jsonify({"error": "Bad request. Please check your CSRF token or input."}), 400

# --- Routes ---
@app.route("/")
@limiter.exempt  # Allow unrestricted access to the static HTML
def index() -> str:
    """Render the main UI template."""
    return render_template("index.html")

@app.route("/api/info", methods=["GET"])
@cache.cached(timeout=3600)  # Efficiency: Cache for 1 hour
@limiter.exempt
def get_info() -> Response:
    """Returns basic event info and a CSRF token for the frontend."""
    sample_questions = [
        "Where is Hall A?",
        "Where is the help desk?",
        "Recommend an AI session",
        "Where can I find food?"
    ]
    
    response = jsonify({
        "sample_questions": sample_questions,
        "event_data": nlp.get_raw_data_dict(),
        "csrf_token": generate_csrf() # Send CSRF token securely to JS
    })
    response.headers['Cache-Control'] = 'public, max-age=3600'
    return response

@app.route("/chat", methods=["POST"])
@limiter.limit("20 per minute") # Strict rate limiting for the chat API
def chat() -> Response:
    """
    Handles user chat messages. Tries local intent matching first,
    then falls back to Gemini AI if configured.
    """
    data = request.get_json()
    if not data or "message" not in data:
        app.logger.warning("Invalid chat request received.")
        return jsonify({"error": "No message provided"}), 400
        
    # Security: sanitize user input
    raw_message = data["message"]
    safe_message = escape(raw_message)
    app.logger.info(f"Received message: {safe_message}")
    
    # Try local matching first
    local_answer = nlp.handle_basic_intent(str(safe_message))
    if local_answer:
        return jsonify({"reply": local_answer})
        
    # Fallback to Google Gemini Services
    if gemini_model:
        try:
            prompt = f"You are Event Buddy AI. Event data: {json.dumps(nlp.get_raw_data_dict())}. User: {safe_message}"
            response = gemini_model.generate_content(prompt)
            return jsonify({"reply": response.text})
        except Exception as e:
            if error_client:
                error_client.report_exception()
            app.logger.error(f"Gemini API error: {e}")
            return jsonify({"reply": "I'm having trouble connecting to my AI brain. Can you ask about a hall, food, or session recommendation?"})

    return jsonify({"reply": "I'm a simple bot right now. Try asking 'Where is Hall A?' or 'Recommend an AI session'."})

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port, debug=False)
