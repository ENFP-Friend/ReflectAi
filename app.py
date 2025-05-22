import google.generativeai as genai
import os
from dotenv import load_dotenv # To load environment variables for the API key

# Load environment variables from a .env file
load_dotenv()

# Configure the API key
# Option 1: Directly in code (NOT RECOMMENDED for production/shared code)
# genai.configure(api_key="YOUR_API_KEY")

# Option 2: From an environment variable (RECOMMENDED)
api_key = os.getenv("GEMINI_API_KEY")
if not api_key:
    raise ValueError("GEMINI_API_KEY not found. Please set it in your .env file or environment.")
genai.configure(api_key=api_key)

# Choose a model
# For text generation, 'gemini-1.5-flash' is a fast and versatile model.
# You can find other available models in the Google AI Studio documentation.
model = genai.GenerativeModel('gemini-1.5-flash')

def ask_gemini(prompt_text):
    """Sends a prompt to the Gemini API and returns the response."""
    try:
        response = model.generate_content(prompt_text)
        return response.text
    except Exception as e:
        return f"An error occurred: {e}"

if __name__ == "__main__":
    print("Welcome to your Gemini AI App!")
    print("---------------------------------")

    # Example: Simple text generation
    prompt = "Write a short story about a robot learning to paint."
    print(f"\nSending prompt: '{prompt}'")
    ai_response = ask_gemini(prompt)
    print("\nGemini's Response:")
    print(ai_response)

    print("\n---------------------------------")
    # Example: Ask a question
    prompt_question = "What is the capital of Australia, and what is a notable landmark there?"
    print(f"\nSending prompt: '{prompt_question}'")
    ai_response_question = ask_gemini(prompt_question)
    print("\nGemini's Response:")
    print(ai_response_question)