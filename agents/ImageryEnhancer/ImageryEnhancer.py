import os
import google.generativeai as genai
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Configure the Gemini API key
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
if not GEMINI_API_KEY:
    raise ValueError("GEMINI_API_KEY not found in .env file or environment variables.")
genai.configure(api_key=GEMINI_API_KEY)

# Create the model instance
# The model name from pipeline_config.json could be passed here if the script was more dynamic,
# but for this test, we'll hardcode it based on your current config.
model = genai.GenerativeModel('gemini-1.5-flash-latest')

def process_text(text: str) -> str:
    """
    Enriches text using the Gemini API (gemini-1.5-flash-latest).
    """
    prompt = f"Enhance the following text with concrete sensory descriptions (sight, sound, texture, motion) to make it more vivid. Original text: '{text}'"
    
    print(f"\n--- [ImageryEnhancer] Attempting to call Gemini API with model: gemini-1.5-flash-latest ---")
    print(f"--- [ImageryEnhancer] Prompt: {prompt[:200]}... ---") # Print a snippet of the prompt

    try:
        response = model.generate_content(prompt)
        enhanced_text = response.text
        print(f"--- [ImageryEnhancer] Gemini API Response (raw text): {enhanced_text[:200]}... ---")
        return enhanced_text
    except Exception as e:
        error_message = f"--- [ImageryEnhancer] Error calling Gemini API: {e} ---"
        print(error_message)
        # Fallback to a simple message if API call fails
        return f"{text} (Error: Could not connect to Gemini for enhancement - {e})"

if __name__ == '__main__':
    # Example usage for direct testing of this script
    # Ensure your .env file has GEMINI_API_KEY set
    test_input = "A lone figure walked through the ancient forest."
    print(f"Original: {test_input}")
    processed = process_text(test_input)
    print(f"Enhanced: {processed}")
