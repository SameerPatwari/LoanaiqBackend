from openai import OpenAI
import os
import fitz  # PyMuPDF for PDF text extraction
from secret_key import openai_key

# Set your OpenAI API key
os.environ["OPENAI_API_KEY"] = openai_key
client = OpenAI()

def extract_text_from_pdf(pdf_path):
    """
    Extracts text from a PDF file using PyMuPDF (fitz).
    """
    text = ""
    with fitz.open(pdf_path) as pdf:
        for page_num in range(len(pdf)):
            page = pdf[page_num]
            text += page.get_text("text")  # Extract text in text format
    return text

def send_prompt_to_gpt(prompt, extracted_text):
    """
    Sends the extracted text and a prompt to the GPT API and returns the response.
    """
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": "You are an assistant that reads and analyzes PDF content."},
            {"role": "user", "content": f"{prompt}\n\nHere is the extracted text:\n{extracted_text}"}
        ]
    )
    return response.choices[0].message.content

def save_response_to_file(response_text, output_path="gpt_response.txt"):
    """
    Saves the GPT response to a text file.
    """
    with open(output_path, "w") as file:
        file.write(response_text)
    print(f"Response saved to {output_path}")

def track_api_usage():
    """
    Tracks and updates the API usage count.
    """
    count_file = "api_usage_count.txt"
    try:
        with open(count_file, "r") as file:
            count = int(file.read())
    except FileNotFoundError:
        count = 0

    count += 1

    with open(count_file, "w") as file:
        file.write(str(count))

    print(f"API has been used {count} times.")

def process_pdf_and_record_response(pdf_path, prompt, output_path="gpt_response.txt"):
    """
    Full process of extracting text from PDF, displaying it, sending it to GPT, and saving the response.
    """
    # Track API usage
    track_api_usage()
    
    # Extract text from the PDF
    extracted_text = extract_text_from_pdf(pdf_path)
    print("PDF text extracted successfully.")
    
    # Display the extracted text
    print("Extracted Text:\n", extracted_text)  # Display the extracted text

    # Step 2: Send prompt and extracted text to GPT
    response = send_prompt_to_gpt(prompt, extracted_text)
    if response:
        print("Received response from GPT.")
        # Step 3: Save the response to a file
        save_response_to_file(response, output_path)
    else:
        print("Failed to receive a response.")


if __name__ == "__main__":
    # Define your PDF path and prompt
    pdf_path = r"C:\pdftoText\Salt - Business Credit Loan.pdf"
    prompt = "Please summarize the following document and highlight key points."

    # Run the process
    process_pdf_and_record_response(pdf_path, prompt)
