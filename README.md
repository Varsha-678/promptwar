# Event Buddy AI 🌟

A lightweight, mobile-friendly AI assistant for physical events. Built for the PromptWars **"Physical Event Experience"** challenge.

## Problem Statement
Navigating large physical events can be overwhelming. Attendees often struggle to find specific halls, help desks, or food courts, and deciding which session to attend next based on their interests can be confusing.

## Challenge Chosen
**Physical Event Experience** - Improving how attendees interact with a physical venue.

## Features
- **Venue Navigation:** Ask where halls, washrooms, or food courts are located.
- **Smart Recommendations:** Suggests the next session based on interest (e.g., "AI", "Startup", "Design").
- **Interactive UI:** Clean, responsive, glassmorphism-inspired dark mode interface.
- **Quick Actions:** Clickable sample questions for faster interaction.
- **Event Info Cards:** Dynamic dashboard showing upcoming sessions and key venue info.

## Tech Stack
- **Backend:** Python, Flask, Gunicorn
- **Frontend:** HTML5, CSS3 (Vanilla), JavaScript (Vanilla)
- **Data:** Local JSON (`event_data.json`)
- **Deployment:** Docker, Google Cloud Run
- **Optional AI:** Google Gemini API integration

## How it works
The Flask backend loads event data from a local JSON file. When a user asks a question via the chat UI, the backend performs intent matching (checking for keywords like "hall", "food", "recommend"). If a match is found, it serves the answer from the local JSON. If no local match is found and a `GEMINI_API_KEY` is provided, it falls back to Gemini for generative answers.

## How to Run Locally

1. **Clone the repository** and navigate to the folder.
2. **Create a virtual environment:**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```
3. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```
4. **(Optional) Set Gemini API Key:**
   ```bash
   export GEMINI_API_KEY="your-api-key"
   ```
5. **Run the app:**
   ```bash
   python app.py
   ```
6. **Open in browser:** Visit `http://localhost:8080` (or the port shown in console).

## How to Deploy on Google Cloud Run

This app is fully containerized and ready for Cloud Run.

1. **Authenticate with Google Cloud:**
   ```bash
   gcloud auth login
   gcloud config set project YOUR_PROJECT_ID
   ```
2. **Submit build and deploy:**
   ```bash
   gcloud run deploy event-buddy-ai \
     --source . \
     --region us-central1 \
     --allow-unauthenticated
   ```
3. *(Optional)* Pass Gemini API key during deployment:
   ```bash
   gcloud run deploy event-buddy-ai \
     --source . \
     --region us-central1 \
     --allow-unauthenticated \
     --set-env-vars GEMINI_API_KEY="your-api-key"
   ```

## Assumptions Made
- The app operates primarily on static schedule data for a single day event.
- Users will type simple intents (e.g., "Where is Hall A", "Recommend AI session").
- The Cloud Run environment will automatically inject the `PORT` environment variable.
