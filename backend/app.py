from flask import Flask, request, jsonify
from flask_cors import CORS
import os
from openai import OpenAI
from predictor import predict_game
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
CORS(app)

# Use Mistral AI instead of OpenAI
client = OpenAI(
    api_key=os.getenv('MISTRAL_API_KEY'),
    base_url="https://api.mistral.ai/v1"
)

@app.route('/api/predict', methods=['POST'])
def predict():
    data = request.json
    teamA = data.get('teamA')
    teamB = data.get('teamB')
    
    if not teamA or not teamB:
        return jsonify({'error': 'Missing team names'}), 400
    
    try:
        result = predict_game(teamA, teamB, verbose=False)
        if result is None:
            return jsonify({'error': 'Could not find team data'}), 404
        return jsonify(result)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/chat', methods=['POST'])
def chat():
    data = request.json
    message = data.get('message')
    
    if not message:
        return jsonify({'error': 'Missing message'}), 400
    
    try:
        # Using Mistral's mistral-large-latest model (free tier available)
        response = client.chat.completions.create(
            model="mistral-large-latest",  # or "mistral-medium-latest" for faster responses
            messages=[
                {
                    "role": "system", 
                    "content": """You are an NFL expert assistant. You help users with general NFL questions, 
                    team analysis, betting advice, and game insights. Be concise and helpful. If asked about 
                    specific score predictions, remind users to use 'Predict [TEAM] vs [TEAM]'."""
                },
                {"role": "user", "content": message}
            ],
            temperature=0.7,
            max_tokens=500
        )
        
        return jsonify({'response': response.choices[0].message.content})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5001)