from flask import Flask, request, jsonify
from main import process_pdf_and_record_response  # Importing from main.py
import os

app = Flask(__name__)

@app.route('/', methods=['GET'])
def home():
    return "Yo"

@app.route('/api/process_pdf', methods=['POST'])
def process_pdf():
    pdf_path = request.json.get("pdf_path")
    prompt = request.json.get("prompt")
    output_path = "gpt_response.txt"
    process_pdf_and_record_response(pdf_path, prompt, output_path)
    
    with open(output_path, 'r') as file:
        response_text = file.read()
    
    return jsonify({
        "response": response_text
    })

if __name__ == "__main__":
    app.run(debug=True)
