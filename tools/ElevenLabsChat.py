import os
import sys
import time
import argparse
import json # For potential future config
import base64 # Added for voice preview decoding
import random # For selecting random sample text
from dotenv import load_dotenv, set_key, find_dotenv

# Attempt to import necessary libraries for voice I/O and AI
try:
    import whisper
    import sounddevice as sd
    from scipy.io.wavfile import write as write_wav
    import tempfile
    VOICE_INPUT_AVAILABLE = True
except ImportError:
    VOICE_INPUT_AVAILABLE = False
    whisper = None
    sd = None
    write_wav = None
    tempfile = None
    print("Warning: Libraries for voice input (whisper, sounddevice, scipy) not fully available. Voice input will be disabled.", file=sys.stderr)

try:
    import elevenlabs
    from elevenlabs.client import ElevenLabs as ElevenLabsClient
    ELEVENLABS_AVAILABLE = True
except ImportError:
    ELEVENLABS_AVAILABLE = False
    elevenlabs = None
    ElevenLabsClient = None
    print("Warning: ElevenLabs library not found. Voice output will be disabled.", file=sys.stderr)

try:
    import google.generativeai as genai
    GEMINI_AVAILABLE = True
except ImportError:
    GEMINI_AVAILABLE = False
    genai = None
    print("Warning: Google Generative AI library not found. GPT-like responses will be disabled.", file=sys.stderr)

try:
    import colorama
    colorama.init(autoreset=True)
except ImportError:
    class DummyColorama: # Fallback if colorama is not installed
        class Fore:
            MAGENTA = ''; BLUE = ''; CYAN = ''; GREEN = ''; YELLOW = ''; RED = ''; LIGHTBLACK_EX = ''; RESET = ''
        class Style:
            RESET_ALL = ''; BRIGHT = ''
    colorama = DummyColorama()
    print("Warning: colorama library not found. Colored output will be disabled.", file=sys.stderr)

# --- Global Configuration & Constants ---
DOTENV_PATH = find_dotenv(usecwd=True) # Finds .env in CWD, or creates if not found by set_key
if not DOTENV_PATH: # If find_dotenv returns empty (doesn't exist and not created yet)
    DOTENV_PATH = os.path.join(os.getcwd(), ".env") # Default to creating in CWD

PREVIEW_SAMPLE_TEXTS = [
    "The quick brown fox jumps over the lazy dog, and then wonders why the dog was so lazy in the first place.",
    "In a world of digital echoes, a unique voice can be a beacon of clarity, guiding thoughts through the noise.",
    "Consider the curious case of the cat that could code in Python, but only when no one was watching its screen.",
    "To be, or not to be, that is the question which philosophers have pondered for centuries, often over a good cup of tea.",
    "She sells seashells by the seashore, but the market for seashells isn't what it used to be, thanks to e-commerce."
]

DEFAULT_ELEVENLABS_VOICE_ID = "21m00Tcm4TlvDq8ikWAM" # Default "Rachel" voice
DEFAULT_GEMINI_MODEL = "gemini-1.5-flash-latest" # Default model for conversation
MIC_DURATION = 5 # Default recording duration
SAMPLERATE = 16000 # Default samplerate for recording

# --- Helper Functions ---

def load_env_vars():
    """Loads environment variables and ensures API keys are present."""
    load_dotenv(DOTENV_PATH)
    gemini_api_key = os.getenv("GEMINI_API_KEY")
    elevenlabs_api_key = os.getenv("ELEVENLABS_API_KEY")

    if not gemini_api_key and GEMINI_AVAILABLE:
        print(f"{colorama.Fore.RED}Error: GEMINI_API_KEY not found in .env file or environment variables.{colorama.Style.RESET_ALL}")
    if not elevenlabs_api_key and ELEVENLABS_AVAILABLE:
        print(f"{colorama.Fore.RED}Error: ELEVENLABS_API_KEY not found in .env file or environment variables.{colorama.Style.RESET_ALL}")

    if GEMINI_AVAILABLE and gemini_api_key:
        try:
            genai.configure(api_key=gemini_api_key)
        except Exception as e:
            print(f"{colorama.Fore.RED}Error configuring Gemini API: {e}{colorama.Style.RESET_ALL}")
    return gemini_api_key, elevenlabs_api_key


def get_current_voice_id() -> str:
    """Gets the current ElevenLabs Voice ID from .env or returns default."""
    load_dotenv(DOTENV_PATH, override=True) # Ensure we have the latest from .env
    return os.getenv("ELEVENLABS_VOICE_ID", DEFAULT_ELEVENLABS_VOICE_ID)

def update_voice_id_in_env(new_voice_id: str):
    """Updates the ELEVENLABS_VOICE_ID in the .env file."""
    try:
        # Ensure .env file exists before trying to set a key in it
        if not os.path.exists(DOTENV_PATH):
            with open(DOTENV_PATH, 'w') as f: # Create empty .env if it doesn't exist
                pass 
            print(f"{colorama.Fore.YELLOW}Created .env file at {DOTENV_PATH}{colorama.Style.RESET_ALL}")

        set_key(DOTENV_PATH, "ELEVENLABS_VOICE_ID", new_voice_id, quote_mode="never")
        load_dotenv(DOTENV_PATH, override=True) # Reload .env to reflect changes immediately
        print(f"{colorama.Fore.GREEN}Voice ID updated to: {new_voice_id} in {DOTENV_PATH}{colorama.Style.RESET_ALL}")
        return True
    except Exception as e:
        print(f"{colorama.Fore.RED}Error updating .env file: {e}{colorama.Style.RESET_ALL}")
        return False

def record_audio_chat(duration=MIC_DURATION, samplerate=SAMPLERATE):
    """Records audio from the microphone for chat."""
    if not VOICE_INPUT_AVAILABLE: return None
    print(f"{colorama.Fore.YELLOW}Listening for {duration} seconds...{colorama.Style.RESET_ALL}")
    try:
        recording = sd.rec(int(duration * samplerate), samplerate=samplerate, channels=1, dtype='int16')
        sd.wait()
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.wav')
        write_wav(temp_file.name, samplerate, recording)
        print(f"{colorama.Fore.GREEN}Recording finished.{colorama.Style.RESET_ALL}")
        return temp_file.name
    except Exception as e:
        print(f"{colorama.Fore.RED}Error during recording: {e}{colorama.Style.RESET_ALL}")
        return None

def transcribe_audio_chat(audio_path):
    """Transcribes audio using Whisper for chat."""
    if not VOICE_INPUT_AVAILABLE or not whisper: return None
    print(f"{colorama.Fore.YELLOW}Transcribing...{colorama.Style.RESET_ALL}")
    try:
        model = whisper.load_model("base")
        result = model.transcribe(audio_path, fp16=False, verbose=False) # verbose=False for less Whisper output
        transcribed_text = result["text"]
        print(f"{colorama.Fore.GREEN}Transcription complete.{colorama.Style.RESET_ALL}")
        return transcribed_text
    except Exception as e:
        print(f"{colorama.Fore.RED}Error during transcription: {e}{colorama.Style.RESET_ALL}")
        return None
    finally:
        if audio_path and os.path.exists(audio_path):
            try: os.remove(audio_path)
            except Exception: pass

def generate_and_play_audio_chat(text_to_speak: str, voice_id: str, elevenlabs_api_key: str):
    """Generates audio from text using ElevenLabs API and plays it for chat."""
    if not ELEVENLABS_AVAILABLE or not ElevenLabsClient or not elevenlabs_api_key:
        print(f"{colorama.Fore.RED}ElevenLabs not available or API key missing.{colorama.Style.RESET_ALL}")
        return
    
    try:
        client = ElevenLabsClient(api_key=elevenlabs_api_key)
        print(f"{colorama.Fore.CYAN}Generating audio with voice: {voice_id}...{colorama.Style.RESET_ALL}")
        
        # Default voice settings for chat; can be made configurable later
        audio_data = client.text_to_speech.convert(
            text=text_to_speak,
            voice_id=voice_id,
            # model_id="eleven_multilingual_v2", # Example model
            # voice_settings=elevenlabs.VoiceSettings(stability=0.7, similarity_boost=0.75) # Example settings
        )
        if audio_data:
            print(f"{colorama.Fore.CYAN}Playing audio...{colorama.Style.RESET_ALL}")
            elevenlabs.play(audio_data)
        else:
            print(f"{colorama.Fore.RED}Failed to generate audio data.{colorama.Style.RESET_ALL}")
    except Exception as e:
        print(f"{colorama.Fore.RED}Error during ElevenLabs operation: {e}{colorama.Style.RESET_ALL}")

def get_gpt_response(user_text: str, model_name: str = DEFAULT_GEMINI_MODEL) -> str:
    """Gets a conversational response from Gemini."""
    if not GEMINI_AVAILABLE or not genai:
        return "Sorry, I can't process that right now (Gemini not available)."
    try:
        model = genai.GenerativeModel(model_name)
        # Simple chat prompt, can be made more sophisticated
        response = model.generate_content(f"User: {user_text}\nAI:") 
        return response.text.strip()
    except Exception as e:
        print(f"{colorama.Fore.RED}Error getting GPT response: {e}{colorama.Style.RESET_ALL}")
        return "Sorry, I encountered an error."

def handle_voice_design_process(user_voice_description: str, current_voice_id: str, elevenlabs_api_key: str, client: ElevenLabsClient) -> str | None:
    """
    Handles the process of generating voice previews, letting user select,
    creating the voice, and updating the .env file.
    Returns the new permanent voice ID if successful, else None.
    """
    if not ELEVENLABS_AVAILABLE or not client:
        print(f"{colorama.Fore.RED}ElevenLabs client not available for voice design.{colorama.Style.RESET_ALL}")
        return None

    sample_text_for_preview = random.choice(PREVIEW_SAMPLE_TEXTS)
    print(f"{colorama.Fore.CYAN}Generating voice previews for: '{user_voice_description}' with sample text: '{sample_text_for_preview}'{colorama.Style.RESET_ALL}")

    try:
        preview_response = client.text_to_voice.create_previews(
            voice_description=user_voice_description,
            text=sample_text_for_preview
        )
        
        if not preview_response.previews:
            generate_and_play_audio_chat("Sorry, I couldn't generate any voice previews for that description.", current_voice_id, elevenlabs_api_key)
            return None

        generated_voice_ids = []
        for i, preview in enumerate(preview_response.previews):
            generated_voice_ids.append(preview.generated_voice_id)
            audio_buffer = base64.b64decode(preview.audio_base_64)
            
            # Announce in current voice
            announcement = f"Playing preview number {i + 1}."
            print(f"{colorama.Fore.MAGENTA}Agent: {announcement}{colorama.Style.RESET_ALL}")
            generate_and_play_audio_chat(announcement, current_voice_id, elevenlabs_api_key)
            time.sleep(0.5) # Small pause
            
            print(f"{colorama.Fore.CYAN}Playing preview audio {i+1}... (ID: {preview.generated_voice_id}){colorama.Style.RESET_ALL}")
            elevenlabs.play(audio_buffer)
            time.sleep(1) # Pause after preview

        selection_prompt = "Which preview did you like best? Please say the number, for example, 'preview one' or 'number two'."
        print(f"{colorama.Fore.MAGENTA}Agent: {selection_prompt}{colorama.Style.RESET_ALL}")
        generate_and_play_audio_chat(selection_prompt, current_voice_id, elevenlabs_api_key)

        print(f"{colorama.Fore.YELLOW}Listening for your selection...{colorama.Style.RESET_ALL}")
        selection_audio_file = record_audio_chat(duration=5)
        if not selection_audio_file:
            generate_and_play_audio_chat("I didn't catch your selection.", current_voice_id, elevenlabs_api_key)
            return None
        
        selection_text = transcribe_audio_chat(selection_audio_file)
        if not selection_text:
            generate_and_play_audio_chat("Sorry, I couldn't understand your selection.", current_voice_id, elevenlabs_api_key)
            return None
        
        print(f"{colorama.Fore.GREEN}Heard selection: {selection_text}{colorama.Style.RESET_ALL}")

        # Attempt to parse selection (very basic, can be improved)
        selected_index = -1
        words = selection_text.lower().split()
        for i, word in enumerate(words):
            if word.isdigit():
                selected_index = int(word) - 1
                break
            # Add more sophisticated parsing for "one", "two", etc. if needed
            elif word == "one": selected_index = 0; break
            elif word == "two": selected_index = 1; break
            elif word == "three": selected_index = 2; break
            # ... and so on for more previews

        if not (0 <= selected_index < len(generated_voice_ids)):
            generate_and_play_audio_chat(f"Sorry, that's not a valid selection. Please try changing the voice again.", current_voice_id, elevenlabs_api_key)
            return None

        chosen_preview_id = generated_voice_ids[selected_index]
        voice_name = f"CustomVoice-{int(time.time())}" # Unique name

        print(f"{colorama.Fore.CYAN}Creating voice '{voice_name}' from preview ID: {chosen_preview_id}...{colorama.Style.RESET_ALL}")
        
        new_voice = client.text_to_voice.create_voice_from_preview(
            voice_name=voice_name,
            voice_description=user_voice_description, # Use the original user description
            generated_voice_id=chosen_preview_id
        )
        
        new_permanent_voice_id = new_voice.voice_id
        print(f"{colorama.Fore.GREEN}New voice created with ID: {new_permanent_voice_id}{colorama.Style.RESET_ALL}")
        
        if update_voice_id_in_env(new_permanent_voice_id):
            return new_permanent_voice_id
        else:
            generate_and_play_audio_chat("I created the voice, but there was an issue saving it as the new default.", current_voice_id, elevenlabs_api_key)
            return None # Or return new_permanent_voice_id and let the loop handle it

    except Exception as e:
        print(f"{colorama.Fore.RED}Error during voice design process: {e}{colorama.Style.RESET_ALL}")
        generate_and_play_audio_chat("Sorry, something went wrong while trying to design the new voice.", current_voice_id, elevenlabs_api_key)
        return None


# --- Main Application Logic ---
def conversation_loop():
    """Main loop for the conversational agent."""
    print(f"{colorama.Fore.CYAN}Starting ElevenLabs Chat Agent... (Press Ctrl+C to exit){colorama.Style.RESET_ALL}")
    
    _, elevenlabs_api_key = load_env_vars() # Load and get API key
    if not elevenlabs_api_key and ELEVENLABS_AVAILABLE:
        print(f"{colorama.Fore.RED}ElevenLabs API key not found. Voice output will be limited.{colorama.Style.RESET_ALL}")
        # Decide if to exit or continue without voice output

    current_voice = get_current_voice_id()
    print(f"{colorama.Fore.CYAN}Using voice ID: {current_voice}{colorama.Style.RESET_ALL}")

    try:
        while True:
            # Removed "Press Enter" prompt and input() call
            # The loop will now proceed directly to recording.
            # A small delay can be added if needed, or a "Listening..." message.
            print(f"\n{colorama.Fore.CYAN}Agent is listening...{colorama.Style.RESET_ALL}") # Indicate listening state

            audio_file = record_audio_chat()
            if not audio_file:
                continue

            user_text = transcribe_audio_chat(audio_file)
            if not user_text:
                generate_and_play_audio_chat("Sorry, I didn't catch that.", current_voice, elevenlabs_api_key)
                continue
            
            print(f"{colorama.Fore.GREEN}You said: {user_text}{colorama.Style.RESET_ALL}")

            # Check for exit command first
            if "goodbye agent" in user_text.lower() or "exit chat" in user_text.lower():
                print(f"{colorama.Fore.YELLOW}Exit command received. Shutting down...{colorama.Style.RESET_ALL}")
                generate_and_play_audio_chat("Goodbye!", current_voice, elevenlabs_api_key)
                break

            # Voice change detection
            voice_change_keywords = ["change your voice", "new voice", "different voice", "don't like your voice", "sound different"]
            if any(keyword in user_text.lower() for keyword in voice_change_keywords):
                response_text = "Sure, I can try to change my voice. What kind of voice are you thinking of? Please describe it for me."
                print(f"{colorama.Fore.MAGENTA}Agent: {response_text}{colorama.Style.RESET_ALL}")
                generate_and_play_audio_chat(response_text, current_voice, elevenlabs_api_key)
                
                print(f"{colorama.Fore.YELLOW}Listening for voice description...{colorama.Style.RESET_ALL}")
                description_audio_file = record_audio_chat(duration=10) # Longer duration for description
                if description_audio_file:
                    voice_description_text = transcribe_audio_chat(description_audio_file)
                    if voice_description_text:
                        print(f"{colorama.Fore.GREEN}Heard description: {voice_description_text}{colorama.Style.RESET_ALL}")
                        
                        # Initialize ElevenLabs client instance once for the process
                        client = None
                        if ELEVENLABS_AVAILABLE and elevenlabs_api_key:
                            client = ElevenLabsClient(api_key=elevenlabs_api_key)

                        if client:
                            new_permanent_voice_id = handle_voice_design_process(voice_description_text, current_voice, elevenlabs_api_key, client)
                            if new_permanent_voice_id:
                                current_voice = new_permanent_voice_id # Update current voice for the session
                                confirmation_text = f"Alright, I've switched to a new voice based on your description. How do I sound now?"
                                print(f"{colorama.Fore.MAGENTA}Agent: {confirmation_text}{colorama.Style.RESET_ALL}")
                                generate_and_play_audio_chat(confirmation_text, current_voice, elevenlabs_api_key)
                            else:
                                error_text = "Sorry, I couldn't create or set the new voice."
                                print(f"{colorama.Fore.MAGENTA}Agent: {error_text}{colorama.Style.RESET_ALL}")
                                generate_and_play_audio_chat(error_text, current_voice, elevenlabs_api_key)
                        else:
                            error_text = "ElevenLabs client could not be initialized. Cannot design voice."
                            print(f"{colorama.Fore.RED}{error_text}{colorama.Style.RESET_ALL}")
                            generate_and_play_audio_chat(error_text, current_voice, elevenlabs_api_key)
                    else:
                         generate_and_play_audio_chat("I didn't catch the voice description.", current_voice, elevenlabs_api_key)
                continue # Skip GPT response for this turn

            gpt_response_text = get_gpt_response(user_text)
            print(f"{colorama.Fore.MAGENTA}Agent: {gpt_response_text}{colorama.Style.RESET_ALL}")
            generate_and_play_audio_chat(gpt_response_text, current_voice, elevenlabs_api_key)

    except KeyboardInterrupt:
        print(f"\n{colorama.Fore.YELLOW}Exiting chat agent...{colorama.Style.RESET_ALL}")
    except Exception as e:
        print(f"{colorama.Fore.RED}An unexpected error occurred: {e}{colorama.Style.RESET_ALL}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Conversational AI with ElevenLabs TTS and dynamic voice changing.")
    # parser.add_argument("--mic-duration", type=int, default=MIC_DURATION, help="Duration for voice recording in seconds.")
    args = parser.parse_args()
    # MIC_DURATION = args.mic_duration # If we add the arg back

    if not all([VOICE_INPUT_AVAILABLE, ELEVENLABS_AVAILABLE, GEMINI_AVAILABLE]):
        print(f"{colorama.Fore.RED}One or more critical libraries (Whisper/SoundDevice, ElevenLabs, Gemini) are missing. Some features might be disabled or the script may not run correctly. Please check warnings above.{colorama.Style.RESET_ALL}")
        # Decide if to exit or allow running with limited functionality
        # sys.exit(1) 
        
    load_env_vars()
    conversation_loop()
