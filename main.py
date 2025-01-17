from docx import Document
import fitz  # PyMuPDF
import pytesseract
from PIL import Image
from io import BytesIO
import pandas as pd
from openai import OpenAI
import os
from dotenv import load_dotenv

load_dotenv()
client = OpenAI()

def extract_text_from_pdf(pdf_path):
    """
    Extracts text from a PDF file using PyMuPDF and applies OCR on images within the PDF.
    """
    full_text = ""
    with fitz.open(pdf_path) as pdf:
        for page_num in range(len(pdf)):
            page = pdf[page_num]
            full_text += f"\n--- Page {page_num + 1} ---\n"
            text = page.get_text("text")
            if text:
                full_text += text
            for img in page.get_images(full=True):
                xref = img[0]
                base_image = pdf.extract_image(xref)
                image_bytes = base_image["image"]
                img = Image.open(BytesIO(image_bytes))
                text = pytesseract.image_to_string(img)
                full_text += text
    return full_text

def extract_text_from_csv(csv_path):
    """
    Extracts text from a CSV file by converting it into a structured string format.
    """
    try:
        df = pd.read_csv(csv_path)
        print(df.to_string(index=False))
        return df.to_string(index=False)
    except Exception as e:
        raise ValueError(f"Error processing CSV file: {str(e)}")

def extract_text_from_docx(docx_path):
    """
    Extracts text from a DOCX file.
    """
    try:
        doc = Document(docx_path)
        full_text = "\n".join([para.text for para in doc.paragraphs if para.text.strip()])
        print(full_text)
        return full_text
    except Exception as e:
        raise ValueError(f"Error processing DOCX file: {str(e)}")

def send_prompt_to_gpt(prompt, extracted_text):
    """
    Sends the combined text and a prompt to the GPT API and returns the response.
    """
    try:
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system",
                 "content": "You are an assistant that responds based on content provided from multiple documents. "
                            "Respond based on the document sections referenced in the prompt. If information is missing, "
                            "say: 'The information required to answer this question is not present in the document.'"},
                {"role": "user",
                 "content": f"{prompt}\n\nThe content from the documents is as follows:\n{extracted_text}"}
            ],
            top_p=0.1
        )
        return response.choices[0].message.content
    except Exception as e:
        raise ValueError(f"Error communicating with GPT API: {str(e)}")

def save_response_to_file(response_text, output_path="gpt_response.txt"):
    """
    Saves the GPT response to a text file.
    """
    try:
        with open(output_path, "w", encoding="utf-8") as file:
            file.write(response_text)
    except Exception as e:
        raise ValueError(f"Error saving response to file: {str(e)}")

def process_multiple_pdfs_and_record_response(file_paths, prompt, output_path="gpt_response.txt"):
    """
    Extracts text from multiple files (PDF, CSV, DOCX), combines the text, sends it to GPT, and saves the response.
    """
    combined_text = ""

    for file_path in file_paths:
        if file_path.endswith('.pdf'):
            extracted_text = extract_text_from_pdf(file_path)
        elif file_path.endswith('.csv'):
            extracted_text = extract_text_from_csv(file_path)
        elif file_path.endswith('.docx'):
            extracted_text = extract_text_from_docx(file_path)
        else:
            raise ValueError(f"Unsupported file type: {file_path}")

        combined_text += f"\n\n--- Start of {os.path.basename(file_path)} ---\n{extracted_text}\n--- End of {os.path.basename(file_path)} ---\n"

    response = send_prompt_to_gpt(prompt, combined_text)
    save_response_to_file(response, output_path)
