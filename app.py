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
from docx.shared import Inches, Pt, RGBColor
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
        heading = doc.add_heading('About the Company', level=1)
        heading.style.font.size = Pt(16)
        heading.style.font.bold = True
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
    
    # Add some space after header
    doc.add_paragraph().paragraph_format.space_after = Pt(12)

    # Add ratios table
    heading = doc.add_heading('', level=1)
    run = heading.add_run('Ratios')
    run.font.size = Pt(16)
    run.font.bold = True
    
    # Get years and ratios data
    years = user_data['ratios']['years']
    ratios_data = user_data['ratios']
    
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
    for category, items in ratios_data.items():
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
    
    # Add space after table
    doc.add_paragraph().paragraph_format.space_after = Pt(12)

    # Process and format the response text
    lines = response_text.strip().split('\n')
    current_section = None
    
    for line in lines:
        line = line.strip()
        if not line:
            continue
            
        if line == "Ratios Analysis:":
            # Main heading
            heading = doc.add_heading('', level=1)
            run = heading.add_run(line.strip(':'))
            run.font.size = Pt(16)
            run.font.bold = True
        elif line.startswith("Analysis of"):
            # Subheading
            heading = doc.add_heading('', level=2)
            run = heading.add_run(line)
            run.font.size = Pt(14)
            run.font.bold = True
            run.font.color.rgb = RGBColor(0x1F, 0x49, 0x7D)  # Dark blue color
        elif line.startswith("Financial Risk:"):
            # Get the risk content (everything after "Financial Risk:")
            risk_content = line[len("Financial Risk:"):].strip()
            
            # Create bullet point for financial risk
            paragraph = doc.add_paragraph()
            paragraph.style.font.size = Pt(11)
            # Add bullet point formatting
            paragraph.paragraph_format.left_indent = Inches(0.25)
            paragraph.paragraph_format.first_line_indent = Inches(-0.25)
            
            # Add bullet point
            bullet_run = paragraph.add_run('• ')
            bullet_run.font.size = Pt(11)
            
            # Add "Financial Risk:" in red
            risk_label = paragraph.add_run("Financial Risk: ")
            risk_label.font.size = Pt(11)
            risk_label.font.bold = True
            risk_label.font.color.rgb = RGBColor(0xC0, 0x00, 0x00)  # Dark red color
            
            # Add the risk content
            content_run = paragraph.add_run(risk_content)
            content_run.font.size = Pt(11)
            
            # Add spacing after paragraph
            paragraph.paragraph_format.space_after = Pt(6)
        else:
            # Content bullet points
            if line.startswith('- '):
                line = line[2:]  # Remove the bullet point
            if line.startswith('**') and line.endswith('**'):
                line = line[2:-2]  # Remove asterisks
            
            paragraph = doc.add_paragraph()
            paragraph.style.font.size = Pt(11)
            # Add a custom bullet point
            paragraph.paragraph_format.left_indent = Inches(0.25)
            paragraph.paragraph_format.first_line_indent = Inches(-0.25)
            bullet_run = paragraph.add_run('• ')
            bullet_run.font.size = Pt(11)
            # Add the content
            content_run = paragraph.add_run(line)
            content_run.font.size = Pt(11)
            
            # Add spacing between bullet points
            paragraph.paragraph_format.space_after = Pt(6)
    
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
        # Check if user data exists, if not try to load it
        user_data_path = os.path.join(UPLOADS_DIR, f"{request.user_id}.json")
        if not os.path.exists(user_data_path):
            try:
                # Try to download from S3
                s3.download_file(
                    os.getenv('S3_BUCKET_NAME'),
                    f"{request.user_id}.json",
                    user_data_path
                )
            except Exception as s3_error:
                raise HTTPException(
                    status_code=404,
                    detail=f"User data not found. Please ensure data is loaded first. Error: {str(s3_error)}"
                )

        # Load user data for document generation
        try:
            with open(user_data_path, 'r', encoding='utf-8') as f:
                user_data = json.load(f)
        except json.JSONDecodeError as json_error:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid JSON data format. Error: {str(json_error)}"
            )
        except Exception as read_error:
            raise HTTPException(
                status_code=500,
                detail=f"Error reading user data: {str(read_error)}"
            )

        # Initialize list to store all analyses
        all_analyses = ["Ratios Analysis:"]  # Start with main heading

        # Process each field in the ratios table
        ratios_data = user_data.get('ratios')
        if not ratios_data:
            raise HTTPException(
                status_code=400,
                detail="No ratios data found in the user data"
            )

        print("Available categories in ratios:", list(ratios_data.keys()))

        for category, fields in ratios_data.items():
            if category == 'years':  # Skip the years array
                continue
            
            print(f"\nProcessing category: {category}")
            print(f"Fields in {category}:", list(fields.keys()))
            
            for field in fields.keys():
                # Construct prompt filename
                prompt_file = f"ratios_{category}_{field}.txt"
                prompt_path = os.path.join("prompt_library", prompt_file)
                
                print(f"Looking for prompt file: {prompt_path}")
                
                if os.path.exists(prompt_path):
                    print(f"Found prompt file for {field}")
                    # Load prompt
                    with open(prompt_path, 'r', encoding='utf-8') as f:
                        prompt_content = f.read()
                    
                    # Get field data
                    years = ratios_data['years']
                    values = ratios_data[category][field]
                    
                    # Create data string
                    data_str = "Years             " + "   ".join(years) + "\n\n"
                    data_str += f"{field}\t   " + "\t   ".join(str(val) for val in values)
                    
                    print(f"Data for {field}:")
                    print(data_str)
                    
                    # Replace placeholder in prompt with actual data
                    final_prompt = prompt_content.replace("DATA:", f"DATA:\n{data_str}")
                    
                    try:
                        # Get GPT analysis
                        response = openai_client.chat.completions.create(
                            model="gpt-4o",
                            messages=[
                                {"role": "system", "content": final_prompt},
                                {"role": "user", "content": f"""Please analyze the data provided in the prompt and format your response exactly as follows:

Analysis of {field}:
- [First insight following the format: The change 'X' in parameter 'Y' maybe caused by 'Z' and affects 'A']
- [Second insight following the format: The change 'X' in parameter 'Y' maybe caused by 'Z' and affects 'A']
- [Third insight following the format: The change 'X' in parameter 'Y' maybe caused by 'Z' and affects 'A']
- Financial Risk: [One comprehensive risk statement]"""}
                            ],
                            temperature=0,
                            top_p=0.1
                        )
                        
                        # Add analysis to list
                        analysis_text = response.choices[0].message.content.strip()
                        if not analysis_text.startswith("Analysis of"):
                            analysis_text = f"Analysis of {field}:\n" + analysis_text
                        all_analyses.append(analysis_text)
                        print(f"Successfully generated analysis for {field}")
                    except Exception as gpt_error:
                        print(f"Error getting GPT analysis for {field}: {str(gpt_error)}")
                        continue  # Skip this field and continue with others
                else:
                    print(f"No prompt file found for {field}")
        
        print(f"\nTotal analyses generated: {len(all_analyses) - 1}")  # -1 for the heading
        
        if len(all_analyses) <= 1:  # Only contains the heading
            raise HTTPException(
                status_code=500,
                detail="No analyses were generated. Please check the prompt library and GPT service."
            )

        # Combine all analyses with proper spacing
        combined_analysis = "\n\n".join(all_analyses)
        
        # Save combined analysis
        response_path = os.path.join(OUTPUT_DIR, f"{request.user_id}_response.json")
        with open(response_path, 'w', encoding='utf-8') as f:
            json.dump({"financial_position": combined_analysis}, f)
        
        # Generate document
        doc_path = generate_document(user_data, combined_analysis, request.user_id)
        
        # After sending response, clean up files
        cleanup_user_files(request.user_id)
        
        return FileResponse(
            doc_path, 
            filename=f"analysis_{request.user_id}.docx",
            media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        )
        
    except Exception as e:
        print(f"Error in generate_note: {str(e)}")  # Add this for debugging
        # Clean up any partial files that might have been created
        cleanup_user_files(request.user_id)
        raise HTTPException(status_code=400, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)