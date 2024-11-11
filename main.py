import fitz  # PyMuPDF
import pytesseract
from PIL import Image
from io import BytesIO
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

    # Open the PDF file
    with fitz.open(pdf_path) as pdf:
        for page_num in range(len(pdf)):
            page = pdf[page_num]

            # Extract pure text from the page
            text = page.get_text("text")
            if text:
                full_text += text

            # Extract images and apply OCR
            for img in page.get_images(full=True):
                xref = img[0]
                base_image = pdf.extract_image(xref)
                image_bytes = base_image["image"]
                img = Image.open(BytesIO(image_bytes))

                # Apply OCR on the image to extract text
                text = pytesseract.image_to_string(img)
                full_text += text

    return full_text

def send_prompt_to_gpt(prompt, extracted_text):
    """
    Sends the extracted text and a prompt to the GPT API and returns the response.
    """
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
                messages=[
                    {"role": "system", 
                     "content": "You are an assistant that only responds based on the provided content from a document. "
                                "Your response must be grounded entirely in the content of the document provided. "
                                "If the answer is not explicitly in the document, you should say: 'The information required to answer this question is not present in the document.'"
                    },
                    {"role": "user", 
                     "content": f"{prompt}\n\nThe content from the document is as follows:\n{extracted_text}"
                    }
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
        with open(output_path, "w", encoding="utf-8") as file:
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
