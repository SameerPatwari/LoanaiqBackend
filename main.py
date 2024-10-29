import fitz  # PyMuPDF
from openai import OpenAI
import os
from dotenv import load_dotenv

load_dotenv()
client = OpenAI()

def extract_text_from_pdf(pdf_path):
    """
    Extracts text from a PDF file using PyMuPDF.
    """
    text = ""
    try:
        with fitz.open(pdf_path) as pdf:
            for page_num in range(len(pdf)):
                page = pdf[page_num]
                text += page.get_text("text")
    except Exception as e:
        raise ValueError(f"Error extracting text from PDF: {str(e)}")
    return text

def send_prompt_to_gpt(prompt, extracted_text):
    """
    Sends the extracted text and a prompt to the GPT API and returns the response.
    """
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "You are a financial analysis assistant specializing in summarizing and extracting insights from PDF documents."},
                    {"role": "user", "content": f"{prompt}\n\nThe extracted content from the financial document is as follows:\n{extracted_text}"}
                ]
        )
        return response.choices[0].message.content
    except Exception as e:
        raise ValueError(f"Error communicating with GPT API: {str(e)}")

def save_response_to_file(response_text, output_path="gpt_response.txt"):
    """
    Saves the GPT response to a text file.
    """
    try:
        with open(output_path, "w") as file:
            file.write(response_text)
    except Exception as e:
        raise ValueError(f"Error saving response to file: {str(e)}")

def process_pdf_and_record_response(pdf_path, prompt, output_path="gpt_response.txt"):
    """
    Full process of extracting text from PDF, sending it to GPT, and saving the response.
    """
    extracted_text = extract_text_from_pdf(pdf_path)
    response = send_prompt_to_gpt(prompt, extracted_text)
    save_response_to_file(response, output_path)
