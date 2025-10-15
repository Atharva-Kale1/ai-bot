# app.py - Part 1: Setup and Configuration
import os
import json
import uuid
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables first
load_dotenv()

from flask import Flask, request, jsonify
from flask_sqlalchemy import SQLAlchemy
# 🚨 New Import for Google GenAI 🚨
from google import genai 
from google.genai import types

# 1. Initialize App and DB (No Change from previous plan)
app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///site.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.secret_key = os.getenv('FLASK_SECRET_KEY', 'default-secret-key') 
db = SQLAlchemy(app)

# 2. LLM Client Initialization
# 🚨 Use GEMINI_API_KEY from .env 🚨
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
if not GEMINI_API_KEY:
    # Gracefully handle missing API key in development: log and set client to None
    print("WARNING: GEMINI_API_KEY is not set. LLM calls will be disabled. Set GEMINI_API_KEY in your .env to enable Gemini calls.")
    client = None
else:
    client = genai.Client(api_key=GEMINI_API_KEY)

MODEL_NAME = "gemini-2.5-flash"


# Load FAQs for system prompt (file or URL)
FAQS_SOURCE = os.getenv('FAQS_SOURCE', 'data/faqs.json')
FAQS_DATA = []

def load_faqs(source):
    try:
        if source.startswith('http://') or source.startswith('https://'):
            import requests
            r = requests.get(source, timeout=5)
            r.raise_for_status()
            return r.json()
        else:
            with open(source, 'r', encoding='utf-8') as f:
                return json.load(f)
    except Exception as e:
        print(f"WARNING: Failed to load FAQs from {source}: {e}")
        return []

FAQS_DATA = load_faqs(FAQS_SOURCE)
FAQS_CONTEXT = "\n".join([f"Q: {item.get('question','')}\nA: {item.get('answer','')}" for item in FAQS_DATA])

SYSTEM_PROMPT = (
    "You are an AI Customer Support Agent. Use the provided FAQs to answer questions first. "
    "If the FAQ contains the answer, respond concisely and cite the FAQ when appropriate. "
    "If the answer is not explicitly in the FAQs, attempt to provide a helpful, accurate answer using general knowledge and reasonable assumptions. "
    "If you are uncertain, say 'I don't know for sure, but here's what I recommend' and provide suggested next actions. "
    "Only escalate to a human agent when the situation is clearly outside the bot's authority, requires access to private data, or would be unsafe to answer; in that case output exactly: 'I will now escalate this to a human agent'. "
    "Keep responses professional, concise, and include suggested next actions when appropriate. Available FAQs:\n" + FAQS_CONTEXT
)
# app.py - Part 2: Database Models
class ConversationSession(db.Model):
    __tablename__ = 'sessions'
    id = db.Column(db.String, primary_key=True)  # Session ID (UUID)
    start_time = db.Column(db.DateTime, default=datetime.utcnow)
    escalated = db.Column(db.Boolean, default=False)

class ConversationHistory(db.Model):
    __tablename__ = 'history'
    id = db.Column(db.Integer, primary_key=True)
    session_id = db.Column(db.String, db.ForeignKey('sessions.id'), nullable=False)
    speaker = db.Column(db.String, nullable=False)  # 'user' or 'bot'
    message = db.Column(db.Text, nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

# app.py - Part 3: Helper Functions
def get_conversation_history(session_id):
    """Retrieves conversation history and formats it for the Gemini API."""
    history = ConversationHistory.query.filter_by(session_id=session_id).order_by(ConversationHistory.timestamp).all()

    # Return a simple, SDK-agnostic representation so we don't call SDK helpers at import-time
    contents = []
    for item in history:
        role = 'user' if item.speaker == 'user' else 'model'  # Gemini uses 'model' for the bot
        contents.append({
            'role': role,
            'message': item.message,
            'timestamp': item.timestamp.isoformat() if item.timestamp else None,
        })

    return contents

def store_message(session_id, speaker, message):
    """Stores a single message in the database."""
    new_message = ConversationHistory(
        session_id=session_id,
        speaker=speaker,
        message=message
    )
    db.session.add(new_message)
    db.session.commit()    
# app.py - Part 4: REST API Endpoint

# app.py - Part 4: REST API Endpoint (Modified LLM Call)

@app.route('/chat', methods=['POST'])
def chat():
    data = request.get_json()
    if not data:
        return jsonify({"error": "Invalid or missing JSON body"}), 400
    user_query = data.get('user_query')
    session_id = data.get('session_id')

    if not user_query or not isinstance(user_query, str):
        return jsonify({"error": "Missing or invalid 'user_query' field"}), 400
    
    # ... (Session Initialization/Retrieval - No change) ...
    if not session_id:
        session_id = str(uuid.uuid4())
        new_session = ConversationSession(id=session_id)
        db.session.add(new_session)
        db.session.commit()
    
    current_session = ConversationSession.query.get(session_id)
    if not current_session or current_session.escalated:
        # (Handling for not found or already escalated session - No change)
        return jsonify({
            "session_id": session_id,
            "bot_response": "This session is already escalated to a human agent.",
            "escalation_status": True,
            "suggested_next_actions": ["End chat"]
        })

    # 1. Contextual Memory & Message Storage
    store_message(session_id, 'user', user_query)
    
    # Get history as SDK-agnostic dicts
    history_contents = get_conversation_history(session_id)

    # Append the current user query to the contents list (dict form)
    history_contents.append({
        'role': 'user',
        'message': user_query,
    })

    # 2. LLM Interaction (Using Gemini)
    # If client is not configured, return a helpful error instead of attempting an LLM call
    if client is None:
        bot_response = (
            "The AI service is not configured (GEMINI_API_KEY missing). "
            "Please set GEMINI_API_KEY in your .env and restart the server."
        )
        # Don't mark as escalated automatically; let the client decide how to proceed
        return jsonify({
            "session_id": session_id,
            "bot_response": bot_response,
            "escalation_status": False,
            "suggested_next_actions": ["Set GEMINI_API_KEY and retry", "Contact support"]
        }), 503

    # Convert dict-form history into SDK `types.Content` objects
    # Build a simple list of message strings (SDK accepts plain strings). This is more robust
    # across SDK versions than constructing nested Content/Part objects by hand.
    contents_strings = [c['message'] for c in history_contents if c.get('message')]

    try:
        response = client.models.generate_content(
            model=MODEL_NAME,
            contents=contents_strings,
            config=types.GenerateContentConfig(
                # Pass the core persona/rules as a System Instruction
                system_instruction=SYSTEM_PROMPT,
            )
        )
        # response may expose text in different ways; prefer .text or str(response)
        bot_response = getattr(response, 'text', None) or str(response)
    except Exception as e:
        bot_response = f"I apologize, a technical error occurred while contacting the AI. Error: {e}"
        print(f"Gemini Error: {e}")
        current_session.escalated = True # Auto-escalate on AI failure
        db.session.commit()
        return jsonify({
            "session_id": session_id,
            "bot_response": bot_response,
            "escalation_status": True,
            "suggested_next_actions": ["End chat"]
        })

    # 3. Escalation Simulation/Check — match the exact escalation sentence case-insensitively
    is_escalated = bot_response.strip().lower() == "i will now escalate this to a human agent"
    
    if is_escalated and not current_session.escalated:
        current_session.escalated = True
        db.session.commit()
        suggested_actions = ["Provide contact information", "End chat"]
    else:
        suggested_actions = ["Ask another question", "Request human agent"]

    # 4. Store Bot Response
    store_message(session_id, 'bot', bot_response)

    # 5. Return REST Response
    return jsonify({
        "session_id": session_id,
        "bot_response": bot_response,
        "escalation_status": current_session.escalated,
        "suggested_next_actions": suggested_actions
    })
@app.route('/health', methods=['GET'])
def health():
    return jsonify({"status": "ok", "db": os.path.exists('site.db')}), 200


@app.route('/', methods=['GET'])
def index():
    # Serve the static frontend index
    return app.send_static_file('index.html')


@app.route('/summarize', methods=['POST'])
def summarize():
    data = request.get_json() or {}
    session_id = data.get('session_id')

    if not session_id:
        return jsonify({"error": "session_id is required for summarization"}), 400

    # Gather conversation for that session
    history = ConversationHistory.query.filter_by(session_id=session_id).order_by(ConversationHistory.timestamp).all()
    text = "\n".join([f"{h.speaker}: {h.message}" for h in history])

    if not text:
        return jsonify({"summary": "No conversation to summarize."}), 200


    if client is None:
        # fallback: simple summary (first 5 messages)
        parts = text.split('\n')[:5]
        return jsonify({"summary": " ".join(parts)}), 200

    try:
        prompt = SYSTEM_PROMPT + "\n\nSummarize the conversation below in 3 concise bullet points:\n" + text
        response = client.models.generate_content(
            model=MODEL_NAME,
            contents=[prompt],
            config=types.GenerateContentConfig(system_instruction=SYSTEM_PROMPT)
        )
        summary = getattr(response, 'text', None) or str(response)
        return jsonify({"summary": summary}), 200
    except Exception as e:
        return jsonify({"error": f"Failed to summarize: {e}"}), 500


# app.py - Part 5: Run Application

if __name__ == '__main__':
    with app.app_context():
        # This creates the database file (site.db) and all tables if they don't exist
        db.create_all()
    app.run(debug=True)