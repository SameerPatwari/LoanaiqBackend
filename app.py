from flask import Flask, request, jsonify, render_template
from werkzeug.utils import secure_filename
from main import process_multiple_pdfs_and_record_response
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

    files = request.files.getlist("pdf_file")  # Get all uploaded files
    if not files or all(file.filename == "" for file in files):
        return jsonify({"error": "No files selected for uploading."}), 400

    # Save uploaded files and collect their paths
    file_paths = []
    for file in files:
        if file and file.filename != "":
            filename = secure_filename(file.filename)
            file_path = os.path.join(app.config["UPLOAD_FOLDER"], filename)
            file.save(file_path)
            file_paths.append(file_path)

    # Get the prompt from the form
    prompt = request.form.get("prompt", "Please summarize the documents.")

    # Define the output path for the GPT response
    output_path = os.path.join(app.config["UPLOAD_FOLDER"], "gpt_response.txt")
    
    # Process the PDFs and record the response
    process_multiple_pdfs_and_record_response(file_paths, prompt, output_path)

    # Read the GPT response from the file and return it
    with open(output_path, 'r', encoding='utf-8') as file:
        response_text = file.read()

    return jsonify({"response": response_text, "filenames": [os.path.basename(path) for path in file_paths]})

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5100)