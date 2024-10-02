from flask import Flask, request, jsonify, render_template
from pymongo import MongoClient
import openai
import os
from dotenv import load_dotenv
from flask_wtf.csrf import CSRFProtect
from flask_cors import CORS

# Load environment variables from the .env file
load_dotenv()

app = Flask(__name__)

# Set up OpenAI API Key and MongoDB URI from .env
openai.api_key = os.getenv('OPENAI_API_KEY')
mongo_uri = os.getenv('MONGO_URI')

# Secret key for CSRF protection (you can generate a random key)
app.config['SECRET_KEY'] = 'supersecretkey'

# Initialize CSRF protection
csrf = CSRFProtect(app)
# CORS(app, resources={r"/ask": {"origins": "http://62.72.7.64/"}})

# Enable CORS (Cross-Origin Resource Sharing)
# CORS(app)


class StockChatbot:
    def __init__(self, mongo_uri):
        self.client = MongoClient(mongo_uri)
        self.db = self.client['test']
        self.collection = self.db['screenertickers']

    def get_data_from_mongo(self, query):
        investors_data = []
        documents = self.collection.find({"investors.name": {"$regex": query, "$options": "i"}})

        for doc in documents:
            investors_data.append(doc.get('investors', {}))
        return investors_data

    def ask_gpt4o(self, user_input, mongo_data):
        prompt = f"The user asked: {user_input}. Here is the relevant data from the database: {mongo_data}. Provide an informative response."

        response = openai.ChatCompletion.create(
            model="gpt-4o",  # GPT-4o model
            messages=[
                {"role": "system",
                 "content": "You are a helpful assistant that provides insights based on user input and database content."},
                {"role": "user", "content": prompt},
            ],
            max_tokens=300,
            temperature=0.7
        )
        return response['choices'][0]['message']['content']


chatbot = StockChatbot(mongo_uri)


# Route for the home page
@app.route('/')
def index():
    return render_template('index.html')


# API route to handle user queries
@app.route('/ask', methods=['POST'])
def ask():
    try:
        user_input = request.json.get("user_input", "")
        if not user_input:
            return jsonify({"error": "User input is required"}), 400

        # Check if user wants to exit
        if user_input.lower() == "exit":
            return jsonify({"response": "Goodbye!"}), 200

        # Fetch data from MongoDB
        mongo_data = chatbot.get_data_from_mongo(user_input)

        # Get GPT-4's response using MongoDB data
        response = chatbot.ask_gpt4o(user_input, mongo_data)
        return jsonify({"response": response}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == '__main__':
    app.run(debug=True, port=4000)