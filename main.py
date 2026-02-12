import json
import uvicorn
import requests
import os
import re
import time
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv

# 1. This loads variables from a .env file (for local testing)
load_dotenv()

app = FastAPI()

# THE BRIDGE: Allows your HTML to talk to this Python server
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- CONFIGURATION ---
GITHUB_TOKEN = os.getenv("BUSHIGO_TOKEN")
ENDPOINT = "https://models.inference.ai.azure.com/chat/completions"
MODEL_NAME = "Phi-4"

# --- RATE LIMIT STORAGE ---
# Dictionary to store { "ip_address": [timestamp1, timestamp2, ...] }
user_history = {}
LIMIT_COUNT = 5
LIMIT_WINDOW = 3 * 60 * 60  # 3 hours in seconds

class EmailRequest(BaseModel):
    text: str
    mode: str

@app.post("/analyze")
async def analyze_email(request_data: EmailRequest, request: Request):
    # 1. Identify User by IP
    client_ip = request.client.host
    current_time = time.time()

    # 2. Initialize or clean history for this IP
    if client_ip not in user_history:
        user_history[client_ip] = []
    
    # Remove timestamps older than the 3-hour window
    user_history[client_ip] = [t for t in user_history[client_ip] if current_time - t < LIMIT_WINDOW]

    # 3. Check Limit: If user has 5 strikes in last 3 hours, block them
    if len(user_history[client_ip]) >= LIMIT_COUNT:
        return {
            "refined_text": "PATIENCE, BUSHI. You have reached the limit of 5 strikes per 3 hours. Your spirit must rest before the forge can be relit.",
            "honor": 0, "stealth": 0
        }

    # Check if token exists to prevent 401 errors
    if not GITHUB_TOKEN:
        return {
            "refined_text": "FORGE ERROR: No Token found in server environment.",
            "honor": 0, "stealth": 0
        }

    # Refined Stances: Samurai Spirit, Professional Output
    stances = {
        "professional": (
            "Persona: The Shogun. Tone: High Executive Diplomacy. "
            "Instruction: Use sophisticated, respectful language. Transform frustration into an authoritative request for excellence. "
            "Constraint: No heavy warrior jargon in the output. Keep it office-safe. "
            "Honor: 95, Stealth: 25."
        ),
        "short": (
            "Persona: The Ninja. Tone: Tactical Brevity. "
            "Instruction: Maximum TWO sentences. Eliminate all greetings, pleasantries, and sign-offs. Focus strictly on action. "
            "Honor: 45, Stealth: 98."
        ),
        "vibe": (
            "Persona: The Katana. Tone: Assertive Professionalism. "
            "Instruction: Be sharp and direct. Use phrases like 'As per my previous' or 'I trust this clarifies.' "
            "Subtext: Professional patience has reached its limit. "
            "Honor: 15, Stealth: 80."
        )
    }
    
    selected_rule = stances.get(request_data.mode, stances["professional"])

    payload = {
        "messages": [
            {
                "role": "system",
                "content": (
                    "You are a master of communication with a disciplined Samurai philosophy. "
                    f"STANCE SETTINGS: {selected_rule}. "
                    "Rewrite the user's input. The result must be professional and ready to send in a corporate environment. "
                    "Respond ONLY with a valid JSON object: "
                    "{ \"refined_text\": \"string\", \"honor\": int, \"stealth\": int }"
                )
            },
            {"role": "user", "content": request_data.text}
        ],
        "model": MODEL_NAME,
        "temperature": 0.7,
        "response_format": { "type": "json_object" }
    }

    headers = {
        "Authorization": f"Bearer {GITHUB_TOKEN}",
        "Content-Type": "application/json"
    }

    try:
        response = requests.post(ENDPOINT, headers=headers, json=payload)
        response.raise_for_status()
        
        raw_content = response.json()["choices"][0]["message"]["content"]
        
        # Robust JSON cleaning: Finds the first '{' and last '}' to ignore extra AI chatter
        json_match = re.search(r'\{.*\}', raw_content, re.DOTALL)
        if json_match:
            clean_json = json_match.group(0)
            
            # LOG SUCCESSFUL STRIKE: Only count it if the API call succeeded
            user_history[client_ip].append(current_time)
            
            return json.loads(clean_json)
        else:
            raise ValueError("No valid JSON found in response")

    except Exception as e:
        print(f"FORGE ERROR: {e}")
        return {
            "refined_text": "THE BLADE HAS SHATTERED. THE FORGE IS DISCONNECTED.",
            "honor": 0, "stealth": 0
        }

if __name__ == "__main__":
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)