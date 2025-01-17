from flask import Flask, request, jsonify, send_file, render_template
from werkzeug.utils import secure_filename
from main import process_multiple_pdfs_and_record_response
import os

# Import generate_document from export_pdf
from export_pdf import generate_document

app = Flask(__name__)

UPLOAD_FOLDER = "uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER

@app.route('/')
def home():
    return render_template("index.html")

@app.route('/api/analyze', methods=['POST'])
def analyze():
    csv_file = request.files.get('csv_file')
    borrower_profile = request.files.get('borrower_profile')
    prompt = """You are an AI financial analyst at a bank tasked with generating insights based on the historical and projected financial data of a borrower. These insights will be reviewed by bank officials to check if the borrower has good performing financials relevant to that bank to provide a loan.

                The data provided includes key financial metrics, such as sales, cost of sales, other expenses, and profitability ratios, for multiple years, so consider the nature of the business, the borrower's profile while generating insights. The file includes key details about the borrower.

                The financial data spans multiple years, with actual figures for prior years and projections for the current and future years. Follow these rules to generate the insights:
                1. Be concise and directly address the key points without additional context or elaboration. Focus on specific figures and events that impact the financial metrics.
                2. Include specific details, such as exact dates and figures to provide a clearer picture of the financial situation.
                3. Follow a narrative structure that ties specific events directly to financial outcomes, making the cause-and-effect relationship more pronounced.
                4. Slight changes in the metrics year over year (under 7.5%) can be ignored if there are no serious changes made in the operations.
                5. If there is not enough context about some insight, don't comment about it.

                Instructions for Formatting:
                6. Don't have sub points for the key insights. Each individual insight will have only one paragraph
                7. Don't take the projections to the face value. Have a balanced view of confidence and skepticism.

                Provide insights into the following areas:
                1. Sales: Provide a brief analysis of sales growth, focusing on specific percentage changes and figures from official documents like tax filings. Highlight any significant sales achievements.
                2. Cost of Sales: Summarize the key components of the cost of sales and any notable changes. Mention specific negotiations or events that have impacted or are expected to impact cost efficiency.
                3. Other Expenses: List the main categories of other expenses and note any significant changes or projections. Keep the focus on specific factors driving these changes.
                4. Depreciation: Provide a concise explanation of changes in depreciation, linking them to specific capital expenditures or events.
                5. Profitability: Briefly analyze periods of high change in profitability, focusing on specific reasons such as client negotiations or payment delays.
            """
    print(prompt)

    if not csv_file or not borrower_profile:
        return jsonify({"error": "Both files are required."}), 400

    csv_path = os.path.join(app.config["UPLOAD_FOLDER"], secure_filename(csv_file.filename))
    borrower_path = os.path.join(app.config["UPLOAD_FOLDER"], secure_filename(borrower_profile.filename))

    csv_file.save(csv_path)
    borrower_profile.save(borrower_path)

    # Combine prompt with extracted data
    combined_prompt = f"{prompt}\nCSV Data: {csv_path}\nBorrower Profile: {borrower_path}"

    output_path = os.path.join(app.config["UPLOAD_FOLDER"], "gpt_response.txt")
    process_multiple_pdfs_and_record_response([csv_path, borrower_path], combined_prompt, output_path)

    with open(output_path, 'r', encoding='utf-8') as file:
        response = file.read()

    return jsonify({"response": response})

@app.route('/api/download', methods=['GET'])
def download():
    try:
        generate_document()  # Call the function to generate the document
        doc_path = 'output.docx'
        return send_file(doc_path, as_attachment=True)
    except Exception as e:
        return jsonify({"error": f"Error generating or downloading document: {str(e)}"}), 500

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5100)
