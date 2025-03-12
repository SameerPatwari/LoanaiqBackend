import os
import json
from openai import OpenAI
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Initialize OpenAI client
openai_client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))

class PromptProcessor:
    def __init__(self):
        self.prompt_dir = "prompt_library"
        self.response_data = self._load_response_data()
        self.analysis_file = "analysis.txt"
        
    def _load_response_data(self):
        """Load the response.json file containing all financial data"""
        with open('response.json', 'r', encoding='utf-8') as f:
            return json.load(f)
    
    def _get_field_data(self, table_name, category, field):
        """Extract specific field data from response.json"""
        try:
            # Get years
            years = self.response_data[table_name]['years']
            
            # Get field values
            if category:
                values = self.response_data[table_name][category][field]
            else:
                values = self.response_data[table_name][field]
            
            # Create data string
            data_str = "Years             " + "   ".join(years) + "\n\n"
            data_str += f"{field}\t   " + "\t   ".join(str(val) for val in values)
            
            return data_str
        except KeyError as e:
            print(f"Error accessing data: {e}")
            return None
    
    def _load_prompt(self, prompt_file):
        """Load a prompt from the prompt library"""
        try:
            with open(os.path.join(self.prompt_dir, prompt_file), 'r', encoding='utf-8') as f:
                return f.read()
        except FileNotFoundError:
            print(f"Prompt file not found: {prompt_file}")
            return None
    
    def _append_to_analysis(self, content):
        """Append analysis to the analysis.txt file"""
        with open(self.analysis_file, 'a', encoding='utf-8') as f:
            f.write(content + "\n\n")
    
    def process_field(self, prompt_file, table_name, category, field):
        """Process a single field: load prompt, get data, get GPT analysis"""
        # Load the prompt
        prompt_content = self._load_prompt(prompt_file)
        if not prompt_content:
            return False
        
        # Get the field data
        field_data = self._get_field_data(table_name, category, field)
        if not field_data:
            return False
        
        # Replace placeholder in prompt with actual data
        final_prompt = prompt_content.replace("DATA:", f"DATA:\n{field_data}")
        
        # Get GPT analysis
        try:
            response = openai_client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": final_prompt},
                    {"role": "user", "content": """Please analyze the data provided in the prompt and format your response exactly as follows:

Analysis of {field}:
- [First insight following the format: The change 'X' in parameter 'Y' maybe caused by 'Z' and affects 'A']
- [Second insight following the same format]
- [Third insight following the same format]

**Financial Risk:**
- [One comprehensive risk statement]""".format(field=field)}
                ],
                temperature=0,
                top_p=0.1
            )
            
            # Append the analysis
            self._append_to_analysis(response.choices[0].message.content)
            return True
            
        except Exception as e:
            print(f"Error getting GPT analysis: {e}")
            return False
    
    def process_all_fields(self):
        """Process all fields based on prompt files in the prompt library"""
        # Clear existing analysis file
        open(self.analysis_file, 'w').close()
        
        # Get all prompt files
        prompt_files = [f for f in os.listdir(self.prompt_dir) if f.endswith('.txt')]
        
        # Process each prompt file
        for prompt_file in prompt_files:
            # Extract table, category, and field from filename
            # Assuming filename format: table_category_field.txt
            parts = prompt_file[:-4].split('_')
            if len(parts) >= 3:
                table = parts[0]
                field = parts[-1]
                category = '_'.join(parts[1:-1])
                
                print(f"Processing {prompt_file}...")
                self.process_field(prompt_file, table, category, field)
            else:
                print(f"Invalid prompt filename format: {prompt_file}")
        
        print("Analysis complete. Check analysis.txt for results.")

if __name__ == "__main__":
    processor = PromptProcessor()
    processor.process_all_fields() 