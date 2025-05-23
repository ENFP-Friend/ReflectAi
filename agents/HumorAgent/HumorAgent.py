import os
import google.generativeai as genai
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), '..', '..', '.env'))

# Configure the Gemini API key
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
if not GEMINI_API_KEY:
    # Try to get it from the script's directory if not found from project root .env
    # This might be useful if agents are run independently with their own .env
    # For this project structure, the above load_dotenv should work.
    alt_env_path = os.path.join(os.path.dirname(__file__), '.env')
    if os.path.exists(alt_env_path):
        load_dotenv(dotenv_path=alt_env_path)
        GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

if not GEMINI_API_KEY:
    raise ValueError("GEMINI_API_KEY not found. Ensure it's in your project's .env file.")

genai.configure(api_key=GEMINI_API_KEY)

# Model will be initialized dynamically in process_text

def process_text(text: str, model_name: str = 'gemini-1.5-flash-latest', verbosity_level: int = 0) -> str:
    """
    Makes the input text funny using the Gemini API.
    Uses the specified model_name.
    verbosity_level controls internal diagnostic prints.
    """
    try:
        model = genai.GenerativeModel(model_name)
    except Exception as e:
        if verbosity_level >= 1: # Print errors only if verbosity is 1 or higher
            error_message = f"--- [HumorAgent] Failed to initialize Gemini model '{model_name}': {e} ---"
            print(error_message)
        return f"{text} (Error: Could not initialize model {model_name} - {e})"

    prompt = f"Given the original text: '{text}'. Append a short, humorous, and witty remark that directly relates to or continues the original text. The output should be the original text followed by your humorous addition. For example, if the original text is 'It is raining', a good response would be 'It is raining. Cats and dogs.' Do not add any introductory phrases."
    
    # Removed print statements for API attempt and prompt

    try:
        response = model.generate_content(prompt)
        funny_text = response.text
        # Ensure the response is a simple string, not a list or complex object.
        # The prompt already requests a single rewrite.
        # Print statement removed, will be handled by run_pipeline.py
        return funny_text.strip()
    except Exception as e:
        if verbosity_level >= 1: # Print errors only if verbosity is 1 or higher
            error_message = f"--- [HumorAgent] Error calling Gemini API ({model_name}): {e} ---"
            print(error_message)
        return f"{text} (Error: Could not connect to Gemini ({model_name}) for humor - {e})"

if __name__ == '__main__':
    # Example usage for direct testing
    test_input = "The meeting was long and covered many topics."
    print(f"Original: {test_input}")
    # Test with default model (verbosity 0 by default for direct test)
    processed_default = process_text(test_input, verbosity_level=2) # Test with high verbosity
    print(f"Funny (default model, verbose): {processed_default}")
    # Test with a specific model
    processed_specific = process_text(test_input, model_name='gemini-1.5-pro-latest', verbosity_level=2)
    print(f"Funny (gemini-1.5-pro-latest, verbose): {processed_specific}")
    
    processed_quiet = process_text("This is a quiet test.", verbosity_level=0)
    print(f"Funny (quiet test): {processed_quiet}")
