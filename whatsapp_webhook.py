"""
WhatsApp bot webhook — receives farmer photos, analyzes with Gemini, replies.
Run alongside Streamlit: python whatsapp_webhook.py
Make it public with: ngrok http 8000
Then paste the ngrok URL into Twilio WhatsApp Sandbox webhook settings.
"""
import os, io, warnings
warnings.filterwarnings("ignore")

from dotenv import load_dotenv
load_dotenv()

from flask import Flask, request
from twilio.twiml.messaging_response import MessagingResponse
from google import genai
from google.genai import types as genai_types
import requests

app = Flask(__name__)

GEMINI_KEY = os.getenv("GEMINI_API_KEY")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-flash-latest")
TWILIO_SID = os.getenv("TWILIO_SID")
TWILIO_TOKEN = os.getenv("TWILIO_TOKEN")
TWILIO_WHATSAPP = os.getenv("TWILIO_WHATSAPP", "+14637242528")

gemini_client = genai.Client(api_key=GEMINI_KEY) if GEMINI_KEY else None


@app.route("/whatsapp", methods=["POST"])
def whatsapp():
    msg = request.values.get("Body", "").strip()
    media_url = request.values.get("MediaUrl0", "")
    sender = request.values.get("From", "")
    resp = MessagingResponse()

    if media_url:
        # Download the image
        img_data = requests.get(media_url, auth=(TWILIO_SID, TWILIO_TOKEN)).content
        result = analyze_image(img_data)
        resp.message(result)
    else:
        resp.message("Mworozi AI 🌱\n\nSend a photo of your crop and I'll analyze it for diseases. "
                      "I'll tell you what's wrong and how to fix it.\n\n"
                      "Commands:\n- 'help' — show this\n- 'list' — recent diagnoses")

    return str(resp)


def analyze_image(image_bytes):
    if not gemini_client:
        return "Gemini API not configured. Contact your extension officer."

    prompt = """You are Mworozi, an AI crop health assistant for East African farmers. Analyze this crop photo.

Keep your response SHORT (WhatsApp-length):
1. Crop: (what plant is this?)
2. Issue: (one line — disease, pest, or healthy?)
3. Severity: Mild / Moderate / Severe
4. Treatment: (2-3 actionable steps, short sentences)
5. Prevention: (1-2 tips)

If healthy: say "Healthy crop! Continue regular care." and skip 4-5."""

    try:
        response = gemini_client.models.generate_content(
            model=GEMINI_MODEL,
            contents=[prompt, genai_types.Part.from_bytes(data=image_bytes, mime_type="image/jpeg")],
            config={"temperature": 0.3, "max_output_tokens": 500},
        )
        text = response.text[:1600]
        return f"🌱 *Mworozi AI Diagnosis*\n\n{text}"
    except Exception as e:
        return f"Sorry, analysis failed. Please try again with a clearer photo.\n\nError: {e}"


if __name__ == "__main__":
    print("Mworozi WhatsApp Webhook running on port 8000")
    print("Expose with: ngrok http 8000")
    print("Paste ngrok URL into Twilio Sandbox webhook: https://console.twilio.com → WhatsApp → Sandbox")
    app.run(host="0.0.0.0", port=8000, debug=False)
