import os
import google.generativeai as genai
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), '..', '..', '.env'))

# Configure the Gemini API key
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
if not GEMINI_API_KEY:
    alt_env_path = os.path.join(os.path.dirname(__file__), '.env')
    if os.path.exists(alt_env_path):
        load_dotenv(dotenv_path=alt_env_path)
        GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

if not GEMINI_API_KEY:
    raise ValueError("GEMINI_API_KEY not found. Ensure it's in your project's .env file.")

genai.configure(api_key=GEMINI_API_KEY)

def process_text(text: str, model_name: str = 'gemini-1.5-flash-latest', verbosity_level: int = 0) -> str:
    """
    Simplifies the input text using the Gemini API.
    Uses the specified model_name.
    verbosity_level controls internal diagnostic prints.
    """
    try:
        model = genai.GenerativeModel(model_name)
    except Exception as e:
        if verbosity_level >= 1: # Print errors only if verbosity is 1 or higher
            # This error print is important for diagnostics if the model fails to load
            print(f"--- [TextSimplifierAgent] Failed to initialize Gemini model '{model_name}': {e} ---")
        return f"{text} (Error: Could not initialize TextSimplifierAgent model {model_name} - {e})"

    prompt = f"Rewrite the following text to be more concise and easier to understand, while preserving its full meaning and any humorous elements. Provide only the rewritten text. Original text: '{text}'"
    
    try:
        response = model.generate_content(prompt)
        simplified_text = response.text
        return simplified_text.strip()
    except Exception as e:
        if verbosity_level >= 1: # Print errors only if verbosity is 1 or higher
            # This error print is important
            print(f"--- [TextSimplifierAgent] Error calling Gemini API ({model_name}): {e} ---")
        return f"{text} (Error: Could not connect to Gemini ({model_name}) for text simplification - {e})"

if __name__ == '__main__':
    # Example usage for direct testing
    test_input = "The meteorological conditions experienced throughout the diurnal period have been characterized by a notable deficit in thermal energy."
    print(f"Original: {test_input}")
    
    simplified = process_text(test_input, verbosity_level=2) # Test with high verbosity
    print(f"Simplified (default model, verbose): {simplified}")

    simplified_pro = process_text(test_input, model_name='gemini-1.5-pro-latest', verbosity_level=2)
    print(f"Simplified (gemini-1.5-pro-latest, verbose): {simplified_pro}")

    simplified_quiet = process_text("This is a quiet test.", verbosity_level=0)
    print(f"Simplified (quiet test): {simplified_quiet}")
