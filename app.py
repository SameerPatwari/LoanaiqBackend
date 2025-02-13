from fastapi import FastAPI, UploadFile, HTTPException
from fastapi.responses import JSONResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv
from openai import OpenAI
import boto3
import json
import os
from docx import Document
from docx.shared import Inches, Pt
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
import PyPDF2
import glob

# Load environment variables
load_dotenv()

app = FastAPI()

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize AWS S3 client
s3 = boto3.client(
    's3',
    aws_access_key_id=os.getenv('AWS_ACCESS_KEY'),
    aws_secret_access_key=os.getenv('AWS_SECRET_KEY')
)

# Initialize OpenAI client
openai_client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))

# Create necessary directories if they don't exist
UPLOADS_DIR = "uploads"
OUTPUT_DIR = "output"
os.makedirs(UPLOADS_DIR, exist_ok=True)
os.makedirs(OUTPUT_DIR, exist_ok=True)

class UserIdRequest(BaseModel):
    user_id: str

class NoteRequest(BaseModel):
    user_id: str

@app.post("/load-data")
async def load_data(request: UserIdRequest):
    try:
        # Construct filename
        filename = f"{request.user_id}.json"
        
        # Download file from S3
        local_file_path = os.path.join(UPLOADS_DIR, filename)
        s3.download_file(
            os.getenv('S3_BUCKET_NAME'),
            filename,
            local_file_path
        )
        
        return JSONResponse(content={"status": "success", "message": "Data loaded successfully"})
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/upload-profile")
async def upload_profile(file: UploadFile):
    try:
        # Save file locally
        file_path = os.path.join(UPLOADS_DIR, file.filename)
        with open(file_path, "wb") as buffer:
            content = await file.read()
            buffer.write(content)
        
        return JSONResponse(content={"status": "success", "message": "Profile uploaded successfully"})
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

def extract_text_from_document(file_path):
    if file_path.endswith('.docx'):
        doc = Document(file_path)
        return ' '.join([paragraph.text for paragraph in doc.paragraphs])
    elif file_path.endswith('.pdf'):
        with open(file_path, 'rb') as file:
            pdf_reader = PyPDF2.PdfReader(file)
            return ' '.join([page.extract_text() for page in pdf_reader.pages])
    return ""

def filter_data_for_prompt(data, prompt_type):
    # Load ratios configuration
    with open('ratios.json', 'r') as f:
        ratio_config = json.load(f)
    
    # Filter data based on prompt type and ratio configuration
    filtered_data = {}
    if prompt_type in ratio_config:
        config = ratio_config[prompt_type]
        for category in config:
            if category in data:
                filtered_data[category] = {
                    k: v for k, v in data[category].items()
                    if k in config[category]
                }
    
    return filtered_data

def filter_data_for_table(data, prompt_type):
    # Load ratios configuration
    with open('tables.json', 'r') as f:
        ratio_config = json.load(f)
    
    # Filter data based on prompt type and ratio configuration
    filtered_data = {}
    if prompt_type in ratio_config:
        config = ratio_config[prompt_type]
        for category in config:
            if category in data:
                filtered_data[category] = {
                    k: v for k, v in data[category].items()
                    if k in config[category]
                }
    
    return filtered_data

def generate_document(user_data, response_text, user_id):
    # Set default prompt type
    prompt_type = "financial_position"
    
    # Load prompt
    with open('prompts.json', 'r') as f:
        prompts = json.load(f)
        prompt = prompts.get(prompt_type)
    
    # Load user data
    user_data_path = os.path.join(UPLOADS_DIR, f"{user_id}.json")
    with open(user_data_path, 'r') as f:
        user_data = json.load(f)
    
    # Filter relevant data
    filtered_data = filter_data_for_table(user_data, prompt_type)

    doc = Document()
    
    # Set narrow margins (0.5 inch on all sides)
    sections = doc.sections
    for section in sections:
        section.left_margin = int(Inches(0.5))
        section.right_margin = int(Inches(0.5))
        section.top_margin = int(Inches(0.5))
        section.bottom_margin = int(Inches(0.5))
    
    # Add company metadata
    about_company = user_data.get('metadata', {}).get('about_company', '')
    if about_company:
        doc.add_heading('About the Company', level=1)
        doc.add_paragraph(about_company)

    # Add header
    header = doc.sections[0].header
    header_table = header.add_table(rows=1, cols=2, width=Inches(7.5))
    header_table.autofit = False

    # Set column widths
    header_table.columns[0].width = int(Inches(2.5))
    header_table.columns[1].width = int(Inches(5.0))

    # Add logo
    logo_cell = header_table.cell(0, 0)
    logo_run = logo_cell.paragraphs[0].add_run()
    logo_run.add_picture('static/images/logo.png', width=Inches(2.0))
    logo_cell.vertical_alignment = WD_ALIGN_PARAGRAPH.CENTER

    # Add business name and details to the right
    text_cell = header_table.cell(0, 1)
    text_cell.paragraphs[0].alignment = WD_ALIGN_PARAGRAPH.RIGHT
    text = text_cell.paragraphs[0].add_run("JANAKALYAN SAHAKARI BANK LTD.\nCredit Department\nNote To BLSC")
    text.bold = True
    text.font.size = Pt(12)
    text_cell.vertical_alignment = WD_ALIGN_PARAGRAPH.CENTER
    
    # Minimize cell padding
    for cell in header_table.rows[0].cells:
        for paragraph in cell.paragraphs:
            paragraph.paragraph_format.space_before = Pt(0)
            paragraph.paragraph_format.space_after = Pt(0)
    
    # Add some space after header
    doc.add_paragraph().paragraph_format.space_after = Pt(12)

    # Add balance sheet table
    doc.add_heading('Profit & Loss', level=1) 
    
    # Get years and balance sheet data
    years = user_data['profit_loss']['years']
    profit_loss_data = user_data['profit_loss']
    
    # Create table with years as columns
    table = doc.add_table(rows=1, cols=len(years) + 1)
    table.style = 'Table Grid'
    table.allow_autofit = False
    
    # Calculate available width (8.5 inches - 1 inch total margins = 7.5 inches)
    available_width = int(Inches(7.5))
    
    # Set column widths
    first_col_width = int(Inches(3.0))  # Financial Term column
    remaining_width = available_width - first_col_width
    year_col_width = int(remaining_width / len(years))
    
    # Apply column widths
    table.columns[0].width = first_col_width
    for i in range(1, len(table.columns)):
        table.columns[i].width = year_col_width
    
    # Add header row with formatting
    header_cells = table.rows[0].cells
    header_cells[0].text = 'Financial Term'
    for idx, year in enumerate(years):
        header_cells[idx + 1].text = year
    
    # Format header row
    for cell in header_cells:
        cell.paragraphs[0].alignment = WD_ALIGN_PARAGRAPH.CENTER
        run = cell.paragraphs[0].runs[0] if cell.paragraphs[0].runs else cell.paragraphs[0].add_run()
        run.font.bold = True
        run.font.size = Pt(9)  # Reduced font size
        cell.vertical_alignment = WD_ALIGN_PARAGRAPH.CENTER
    
    # Add data rows
    for category, items in profit_loss_data.items():
        if category != 'years':  # Skip the years array
            for item_name, values in items.items():
                row_cells = table.add_row().cells
                
                # Format financial term cell
                row_cells[0].text = item_name
                row_cells[0].paragraphs[0].alignment = WD_ALIGN_PARAGRAPH.LEFT
                
                # Add and format values for each year
                for idx, value in enumerate(values):
                    cell = row_cells[idx + 1]
                    cell.text = str(value)
                    cell.paragraphs[0].alignment = WD_ALIGN_PARAGRAPH.RIGHT
    
    # Apply consistent formatting to all cells
    for row in table.rows:
        row.height = int(Inches(0.25))  # Reduced row height
        for cell in row.cells:
            cell.vertical_alignment = WD_ALIGN_PARAGRAPH.CENTER
            # Minimize cell padding
            for paragraph in cell.paragraphs:
                paragraph.paragraph_format.space_before = Pt(0)
                paragraph.paragraph_format.space_after = Pt(0)
                for run in paragraph.runs:
                    run.font.size = Pt(8)  # Smaller font size
    
    # Add analysis text
    doc.add_heading('Analysis', level=1)
    doc.add_paragraph(response_text)
    
    # Save document
    output_path = os.path.join(OUTPUT_DIR, f'analysis_{user_id}.docx')
    doc.save(output_path)
    return output_path

def cleanup_user_files(userid):
    """Delete all files related to the userid from uploads and output folders"""
    # Clean uploads folder
    upload_pattern = os.path.join(UPLOADS_DIR, f"{userid}*")
    for file in glob.glob(upload_pattern):
        os.remove(file)
    
    # Clean output folder
    output_pattern = os.path.join(OUTPUT_DIR, f"{userid}*")
    for file in glob.glob(output_pattern):
        os.remove(file)

@app.post("/generate-note")
async def generate_note(request: NoteRequest):
    try:
        # Set default prompt type
        prompt_type = "financial_position"
        
        # Load prompt
        with open('prompts.json', 'r') as f:
            prompts = json.load(f)
            prompt = prompts.get(prompt_type)

        if not prompt:
            raise HTTPException(status_code=400, detail="Invalid prompt type")
        
        # Load user data
        user_data_path = os.path.join(UPLOADS_DIR, f"{request.user_id}.json")
        with open(user_data_path, 'r') as f:
            user_data = json.load(f)
        
        # Filter relevant data
        filtered_data = filter_data_for_prompt(user_data, prompt_type)
        
        # Add profile document content if exists
        profile_content = ""
        profile_files = [f for f in os.listdir(UPLOADS_DIR) if f.endswith(('.docx', '.pdf'))]
        if profile_files:
            profile_path = os.path.join(UPLOADS_DIR, profile_files[0])
            profile_content = extract_text_from_document(profile_path)
        
        # Prepare final prompt
        final_prompt = prompt.replace("<Borrower Profile>", profile_content)
        
        # Get GPT-4 response
        response = openai_client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": final_prompt},
                {"role": "user", "content": json.dumps(filtered_data)}
            ]
        )
        
        # Save response
        response_text = response.choices[0].message.content
        response_path = os.path.join(OUTPUT_DIR, f"{request.user_id}_response.json")
        with open(response_path, 'w') as f:
            json.dump({prompt_type: response_text}, f)
        
        # Generate document
        doc_path = generate_document(user_data, response_text, request.user_id)
        
        # After sending response, clean up files
        cleanup_user_files(request.user_id)
        
        return FileResponse(
            doc_path, 
            filename=f"analysis_{request.user_id}.docx",
            media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        )
        
    except Exception as e:
        print(f"Error in generate_note: {str(e)}")  # Add this for debugging
        raise HTTPException(status_code=400, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)