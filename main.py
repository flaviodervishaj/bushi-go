import json
import uvicorn
import requests
import os
from fastapi import FastAPI
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
# This looks for a variable named 'BUSHIGO_TOKEN' in your server settings
# When you host on Render/Railway, you will paste your token there.
GITHUB_TOKEN = os.getenv("BUSHIGO_TOKEN")
ENDPOINT = "https://models.inference.ai.azure.com/chat/completions"
MODEL_NAME = "Phi-4"

class EmailRequest(BaseModel):
    text: str
    mode: str

@app.post("/analyze")
async def analyze_email(request: EmailRequest):
    # Check if token exists to prevent 401 errors
    if not GITHUB_TOKEN:
        return {
            "refined_text": "FORGE ERROR: No Token found in server environment.",
            "honor": 0, "stealth": 0
        }

    stances = {
        "professional": (
            "STANCE: SHOGUN. Tone: High Diplomacy. "
            "Rule: Use 'Esteemed' or 'Respectfully.' Transform all complaints into requests for excellence. "
            "Honor: 95, Stealth: 20."
        ),
        "short": (
            "STANCE: NINJA. Tone: Tactical Brevity. "
            "Rule: Maximum TWO sentences. No greetings. No sign-offs. "
            "Structure: Sentence 1 identifies the issue. Sentence 2 gives the order. "
            "Honor: 40, Stealth: 98."
        ),
        "vibe": (
            "STANCE: KATANA. Tone: Aggressive Professionalism. "
            "Rule: Use 'As per my previous' or 'I trust this is clear.' "
            "Subtext: Your patience has reached its limit. "
            "Honor: 10, Stealth: 75."
        )
    }
    
    selected_rule = stances.get(request.mode, stances["professional"])

    payload = {
        "messages": [
            {
                "role": "system",
                "content": (
                    "You are a Samurai Master. Rewrite the input text. "
                    f"Instruction: {selected_rule}. "
                    "Respond ONLY with a JSON object: "
                    "{ \"refined_text\": \"string\", \"honor\": int, \"stealth\": int }"
                )
            },
            {"role": "user", "content": request.text}
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
        
        content = response.json()["choices"][0]["message"]["content"]
        clean_json = content.replace("```json", "").replace("```", "").strip()
        
        return json.loads(clean_json)

    except Exception as e:
        print(f"FORGE ERROR: {e}")
        return {
            "refined_text": "THE BLADE HAS SHATTERED. RE-LINK THE FORGE.",
            "honor": 0, "stealth": 0
        }

if __name__ == "__main__":
    # The host '0.0.0.0' is required for cloud hosting services
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)