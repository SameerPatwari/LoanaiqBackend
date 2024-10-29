from flask import Flask, request, jsonify, render_template
from werkzeug.utils import secure_filename
from main import process_pdf_and_record_response
import os

app = Flask(__name__)

# Define the folder to store uploaded PDFs
UPLOAD_FOLDER = "uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER

@app.route('/', methods=['GET'])
def home():
    return render_template("index.html")

@app.route('/api/process_pdf', methods=['POST'])
def process_pdf():
    # Handling file upload from the form
    if "pdf_file" not in request.files:
        return jsonify({"error": "No file part in the request."}), 400

    file = request.files["pdf_file"]
    if file.filename == "":
        return jsonify({"error": "No file selected for uploading."}), 400

    if file:
        # Save the uploaded file
        filename = secure_filename(file.filename)
        file_path = os.path.join(app.config["UPLOAD_FOLDER"], filename)
        file.save(file_path)

        # Get the prompt from the form
        prompt = request.form.get("prompt", "Please summarize this document.")

        # Process the PDF and get the GPT response
        output_path = os.path.join(app.config["UPLOAD_FOLDER"], "gpt_response.txt")
        process_pdf_and_record_response(file_path, prompt, output_path)

        # Read the GPT response from the file and return it
        with open(output_path, 'r') as file:
            response_text = file.read()

        return jsonify({"response": response_text})

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5100)