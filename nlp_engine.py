import json
import logging
from typing import Dict, List, Optional
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

# --- Pydantic Data Models (Code Quality: Strict Typing) ---
class Session(BaseModel):
    title: str
    time: str
    hall: str
    tag: str

class EventData(BaseModel):
    halls: Dict[str, str] = Field(default_factory=dict)
    sessions: List[Session] = Field(default_factory=list)
    facilities: Dict[str, str] = Field(default_factory=dict)

# --- NLP Engine Class (Code Quality: Modularization) ---
class NLPEngine:
    def __init__(self, data_file: str):
        self.data_file = data_file
        self.event_data = self._load_data()

    def _load_data(self) -> EventData:
        try:
            with open(self.data_file, "r") as f:
                raw_data = json.load(f)
            return EventData(**raw_data)
        except Exception as e:
            logger.error(f"Error loading {self.data_file}: {e}")
            return EventData()

    def get_raw_data_dict(self) -> dict:
        """Returns the dictionary representation for API responses."""
        return self.event_data.model_dump()

    def handle_basic_intent(self, query: str) -> Optional[str]:
        """
        Matches user query to predefined intents for venue navigation and recommendations.
        
        Args:
            query: The user's sanitized input string.
        Returns:
            A string response if matched, or None if no match.
        """
        query_lower = query.lower()
        
        # 1. Hall queries
        if "where is" in query_lower and "hall" in query_lower:
            for hall_name, desc in self.event_data.halls.items():
                if hall_name.lower() in query_lower:
                    return f"{hall_name} is located at: {desc}"
            return "We have Halls A, B, C, and D. Which one are you looking for?"
            
        # 2. Facility queries
        if "help desk" in query_lower or "help" in query_lower:
            return f"Help Desk: {self.event_data.facilities.get('help desk', 'Not found.')}"
            
        if "food" in query_lower or "eat" in query_lower or "hungry" in query_lower:
            return f"Food options: {self.event_data.facilities.get('food', 'Not found.')}"
            
        if "washroom" in query_lower or "restroom" in query_lower or "toilet" in query_lower:
            return f"Washrooms: {self.event_data.facilities.get('washrooms', 'Not found.')}"

        # 3. Recommendations
        if "recommend" in query_lower or "next" in query_lower or "session" in query_lower:
            interests = ["ai", "startup", "design"]
            user_interest = next((i for i in interests if i in query_lower), None)
                    
            if user_interest:
                matching = [s for s in self.event_data.sessions if s.tag.lower() == user_interest]
                if matching:
                    s = matching[0]
                    return f"I recommend: '{s.title}' at {s.time} in {s.hall}."
                else:
                    return f"I couldn't find any sessions for {user_interest} right now."
            else:
                return "What are you interested in? (e.g., AI, Design, Startup) so I can recommend a session!"
                
        return None
