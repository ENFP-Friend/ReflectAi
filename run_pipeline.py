import json
import importlib.util
import os
import argparse
import sys # Added for platform check
from dotenv import load_dotenv # Added for .env loading
import time # For voice input countdown

# Imports for Whisper and audio recording
try:
    import whisper
    import sounddevice as sd
    from scipy.io.wavfile import write as write_wav
    import tempfile
    VOICE_INPUT_AVAILABLE = True
except ImportError as e:
    VOICE_INPUT_AVAILABLE = False
    print(f"Warning: Libraries for voice input (whisper, sounddevice, scipy) not fully available. Voice input disabled. Error: {e}", file=sys.stderr)
    whisper = None
    sd = None
    write_wav = None
    tempfile = None

try:
    import colorama
    colorama.init(autoreset=True)
except ImportError:
    print("Warning: colorama library not found. ANSI escape codes will be used directly for colors, which may not display correctly on all terminals (especially Windows).", file=sys.stderr)
    class DummyColorama:
        class Fore:
            MAGENTA = '\033[95m'
            BLUE = '\033[94m'
            CYAN = '\033[96m'
            GREEN = '\033[92m'
            YELLOW = '\033[93m'
            RED = '\033[91m'
            LIGHTBLACK_EX = '\033[90m'
            RESET = '\033[39m' # Default foreground color
        class Style:
            RESET_ALL = '\033[0m'
            BRIGHT = '\033[1m'
    colorama = DummyColorama()

AGENT_NAME_COLORS = [
    colorama.Fore.GREEN,
    colorama.Fore.YELLOW,
    colorama.Fore.BLUE, # Already used for general agent prefix, but can be distinct here
    colorama.Fore.MAGENTA, # Already used for "Input:", but can be distinct here
    colorama.Fore.RED, 
    # Add more colors if you have more than 5 agents in a typical pipeline
    # Or it will cycle. Using a different set from CYAN for text and MAGENTA for Input:
    colorama.Fore.LIGHTGREEN_EX if hasattr(colorama.Fore, 'LIGHTGREEN_EX') else colorama.Fore.GREEN,
    colorama.Fore.LIGHTYELLOW_EX if hasattr(colorama.Fore, 'LIGHTYELLOW_EX') else colorama.Fore.YELLOW,
]

# Attempt to import elevenlabs and set a flag
try:
    import elevenlabs # Keep this for top-level functions if needed
    from elevenlabs.client import ElevenLabs as ElevenLabsClient
    ELEVENLABS_AVAILABLE = True
except ImportError:
    ELEVENLABS_AVAILABLE = False
    elevenlabs = None # So checks for elevenlabs don't break
    ElevenLabsClient = None
    # We'll print a warning later if the user tries to use --audio without the library

# --- Voice Input Functions ---
def record_audio(duration=5, samplerate=16000, verbosity=1):
    """Records audio from the microphone for a specified duration."""
    if not VOICE_INPUT_AVAILABLE or sd is None or write_wav is None or tempfile is None:
        print(f"{colorama.Fore.RED}Error: Sound recording libraries not available. Cannot record audio.{colorama.Style.RESET_ALL}")
        return None
    
    if verbosity >= 1:
        print(f"{colorama.Fore.YELLOW}--- [Audio Input] Recording for {duration} seconds... Speak now! ---{colorama.Style.RESET_ALL}")
    if verbosity >= 2: # Countdown only for higher verbosity
        for i in range(duration, 0, -1):
            print(f"{colorama.Fore.YELLOW}Recording in {i}...{colorama.Style.RESET_ALL}", end='\\r')
            time.sleep(1)
        print(" " * 40, end='\\r') # Clear countdown line

    try:
        recording = sd.rec(int(duration * samplerate), samplerate=samplerate, channels=1, dtype='int16')
        sd.wait()  # Wait until recording is finished
        
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.wav')
        write_wav(temp_file.name, samplerate, recording)
        if verbosity >= 1:
            print(f"{colorama.Fore.GREEN}--- [Audio Input] Recording finished. Saved to {temp_file.name} ---{colorama.Style.RESET_ALL}")
        return temp_file.name
    except Exception as e:
        print(f"{colorama.Fore.RED}--- [Audio Input] Error during recording: {e} ---{colorama.Style.RESET_ALL}")
        return None

def transcribe_audio_with_whisper(audio_path, verbosity=1):
    """Transcribes audio using Whisper."""
    if not VOICE_INPUT_AVAILABLE or whisper is None:
        print(f"{colorama.Fore.RED}Error: Whisper library not available. Cannot transcribe audio.{colorama.Style.RESET_ALL}")
        if audio_path and os.path.exists(audio_path):
             try: os.remove(audio_path)
             except Exception: pass # Best effort to clean up
        return None

    if verbosity >= 2:
        print(f"{colorama.Fore.YELLOW}--- [Whisper] Loading Whisper model (base)... ---{colorama.Style.RESET_ALL}")
    transcribed_text = None
    try:
        model = whisper.load_model("base")
        if verbosity >= 1:
            print(f"{colorama.Fore.YELLOW}--- [Whisper] Transcribing audio at {audio_path}... ---{colorama.Style.RESET_ALL}")
        
        # Whisper's own verbose=None shows progress, verbose=False hides it.
        # We can tie this to our verbosity.
        whisper_verbose_setting = None if verbosity >= 1 else False 
        result = model.transcribe(audio_path, fp16=False, verbose=whisper_verbose_setting)
        transcribed_text = result["text"]
        if verbosity >= 2: # Only print explicit completion for highest verbosity
            print(f"{colorama.Fore.GREEN}--- [Whisper] Transcription complete. ---{colorama.Style.RESET_ALL}")
    except Exception as e:
        print(f"{colorama.Fore.RED}--- [Whisper] Error during transcription: {e} ---{colorama.Style.RESET_ALL}")
    finally:
        if audio_path and os.path.exists(audio_path): # Clean up temporary audio file
            try:
                os.remove(audio_path)
            except Exception as e_rem:
                print(f"{colorama.Fore.YELLOW}Warning: Could not remove temporary audio file {audio_path}: {e_rem}{colorama.Style.RESET_ALL}")
    return transcribed_text
# --- End Voice Input Functions ---

def generate_and_play_audio(
    text_to_speak: str, 
    api_key: str, 
    voice_id: str, # Now required, will be fetched from env or default in main
    model_id: str = None,
    stability: float = None,
    similarity_boost: float = None,
    style: float = None,
    use_speaker_boost: bool = None
):
    """Generates audio from text using ElevenLabs API and plays it, with configurable settings."""
    if not ELEVENLABS_AVAILABLE or ElevenLabsClient is None or elevenlabs is None:
        print(f"{colorama.Fore.RED}Error: ElevenLabs library not found or failed to import correctly. Please install it using 'pip install elevenlabs' to use audio features.{colorama.Style.RESET_ALL}")
        return
    if not api_key:
        print(f"{colorama.Fore.RED}Error: ELEVENLABS_API_KEY not found in .env file.{colorama.Style.RESET_ALL}")
        return

    try:
        print(f"{colorama.Fore.CYAN}--- [Audio] Initializing ElevenLabs client... ---{colorama.Style.RESET_ALL}")
        # The client itself is the main entry point for v2+
        client = ElevenLabsClient(api_key=api_key) 
        
        print(f"{colorama.Fore.CYAN}--- [Audio] Generating audio with ElevenLabs ---{colorama.Style.RESET_ALL}")
        print(f"{colorama.Fore.LIGHTBLACK_EX}      Voice ID: {voice_id}{colorama.Style.RESET_ALL}")
        if model_id:
            print(f"{colorama.Fore.LIGHTBLACK_EX}      Model ID: {model_id}{colorama.Style.RESET_ALL}")

        voice_settings_args = {}
        if stability is not None:
            voice_settings_args['stability'] = stability
            print(f"{colorama.Fore.LIGHTBLACK_EX}      Stability: {stability}{colorama.Style.RESET_ALL}")
        if similarity_boost is not None:
            voice_settings_args['similarity_boost'] = similarity_boost
            print(f"{colorama.Fore.LIGHTBLACK_EX}      Similarity Boost: {similarity_boost}{colorama.Style.RESET_ALL}")
        if style is not None:
            voice_settings_args['style'] = style
            print(f"{colorama.Fore.LIGHTBLACK_EX}      Style: {style}{colorama.Style.RESET_ALL}")
        if use_speaker_boost is not None:
            voice_settings_args['use_speaker_boost'] = use_speaker_boost
            print(f"{colorama.Fore.LIGHTBLACK_EX}      Use Speaker Boost: {use_speaker_boost}{colorama.Style.RESET_ALL}")

        tts_payload = {
            "text": text_to_speak,
            "voice_id": voice_id
        }
        if model_id:
            tts_payload["model_id"] = model_id
        
        if voice_settings_args:
            # elevenlabs.VoiceSettings is needed if the SDK version requires it
            # For newer SDKs, these might be direct params to convert or part of a Voice object.
            # Assuming client.text_to_speech.convert can take voice_settings dict directly or specific params
            # Let's try passing them directly if the SDK supports it, or construct VoiceSettings if needed.
            # For now, let's assume they can be part of the main call for simplicity,
            # or that VoiceSettings can be constructed.
            # The `elevenlabs.VoiceSettings` class is the typical way.
            if voice_settings_args: # Only try to use VoiceSettings if there are args for it
                try:
                    from elevenlabs import VoiceSettings # Attempt import here
                    tts_payload["voice_settings"] = VoiceSettings(**voice_settings_args)
                except ImportError:
                    print(f"{colorama.Fore.YELLOW}Warning: 'elevenlabs.VoiceSettings' could not be imported. " +
                          "Advanced voice settings (stability, similarity, etc.) might be ignored. " +
                          "Ensure your ElevenLabs SDK version supports VoiceSettings or pass parameters differently.{colorama.Style.RESET_ALL}")
                    # If VoiceSettings is not available, these specific args are not added to tts_payload
                    # beyond model_id, unless the SDK's convert() method takes them directly (less common).

        audio_data = client.text_to_speech.convert(**tts_payload)

        # The .convert() method typically returns the audio bytes directly.
        if audio_data:
            print(f"{colorama.Fore.CYAN}--- [Audio] Playing audio... ---{colorama.Style.RESET_ALL}")
            elevenlabs.play(audio_data) # elevenlabs.play is a top-level function
            print(f"{colorama.Fore.GREEN}--- [Audio] Playback finished. ---{colorama.Style.RESET_ALL}")
        else:
            print(f"{colorama.Fore.RED}--- [Audio] Failed to generate audio data (empty response). ---{colorama.Style.RESET_ALL}")
    except AttributeError as ae:
        # Specific check for the 'generate' attribute error
        if 'ElevenLabs' in str(ae) and 'generate' in str(ae):
             print(f"{colorama.Fore.RED}--- [Audio] Error: The 'ElevenLabs' client object does not have a 'generate' method in the current version/environment. This is unexpected. Please check library documentation for the correct text-to-speech method. ---{colorama.Style.RESET_ALL}")
        else:
            print(f"{colorama.Fore.RED}--- [Audio] Attribute Error during ElevenLabs operation: {ae} ---{colorama.Style.RESET_ALL}")
    except Exception as e:
        print(f"{colorama.Fore.RED}--- [Audio] Error during ElevenLabs operation: {e} ---{colorama.Style.RESET_ALL}")


def load_agent_function(agent_path: str):
    """Dynamically loads the process_text function from an agent's Python file."""
    if not os.path.exists(agent_path):
        raise FileNotFoundError(f"Agent script not found: {agent_path}")
    
    module_name = os.path.splitext(os.path.basename(agent_path))[0]
    spec = importlib.util.spec_from_file_location(module_name, agent_path)
    if spec is None or spec.loader is None:
        raise ImportError(f"Could not load spec for module at {agent_path}")
    
    agent_module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(agent_module)
    
    if not hasattr(agent_module, 'process_text'):
        raise AttributeError(f"Agent script {agent_path} does not have a 'process_text' function.")
        
    return agent_module.process_text

def main():
    """Runs the agent pipeline based on the configuration file."""
    load_dotenv() # Load .env file for GOOGLE_GEMINI_MODEL_NAME

    try:
        with open('pipeline_config.json', 'r') as f:
            config = json.load(f)
    except FileNotFoundError:
        print(f"{colorama.Fore.RED}Error: pipeline_config.json not found.{colorama.Style.RESET_ALL}")
        return
    except json.JSONDecodeError:
        print(f"{colorama.Fore.RED}Error: Could not decode pipeline_config.json. Please check its format.{colorama.Style.RESET_ALL}")
        return

    agents_map = {agent['name']: agent for agent in config.get('agents', [])}
    execution_order = config.get('execution_order', [])

    if not execution_order:
        print(f"{colorama.Fore.YELLOW}No execution order defined in pipeline_config.json.{colorama.Style.RESET_ALL}")
        return
    
    if not agents_map:
        print(f"{colorama.Fore.YELLOW}No agents defined in pipeline_config.json.{colorama.Style.RESET_ALL}")
        return

    parser = argparse.ArgumentParser(description="Run the GPT agent pipeline.")
    parser.add_argument("input_text", type=str, nargs='?', default=None, help="The initial text to process. If not provided, will prompt for voice input.")
    parser.add_argument("-a", "--audio", action="store_true", help="Generate and play audio output using ElevenLabs for the final text.")
    parser.add_argument("--mic-duration", type=int, default=5, help="Duration in seconds for microphone recording if no text input is provided (default: 5).")
    parser.add_argument("-v", "--verbose", action="store_true", help="Enable verbose output, including API call details and other internal logs.")
    args = parser.parse_args()
    
    if args.verbose:
        print(f"DEBUG: Parsed arguments: {args}")

    initial_input_text = args.input_text

    # Voice input verbosity tied to the main verbose flag
    voice_input_verbosity = 2 if args.verbose else 0 # 2 for verbose, 0 for minimal status
    if initial_input_text is None:
        if VOICE_INPUT_AVAILABLE:
            if args.verbose: # Only print this if verbose
                print(f"{colorama.Fore.MAGENTA}No text input provided. Initializing voice input...{colorama.Style.RESET_ALL}")
            audio_file_path = record_audio(duration=args.mic_duration, verbosity=voice_input_verbosity)
            if audio_file_path:
                initial_input_text = transcribe_audio_with_whisper(audio_file_path, verbosity=voice_input_verbosity)
                if initial_input_text:
                    if args.verbose: # Only print this if verbose
                        print(f"{colorama.Fore.MAGENTA}Transcribed text:{colorama.Style.RESET_ALL} {colorama.Fore.CYAN}{initial_input_text}{colorama.Style.RESET_ALL}")
                else:
                    print(f"{colorama.Fore.RED}Could not transcribe audio. Exiting.{colorama.Style.RESET_ALL}")
                    return
            else:
                print(f"{colorama.Fore.RED}Could not record audio. Exiting.{colorama.Style.RESET_ALL}")
                return
        else:
            print(f"{colorama.Fore.RED}Voice input libraries not available and no text input provided. Exiting.{colorama.Style.RESET_ALL}")
            return

    if not initial_input_text:
        print(f"{colorama.Fore.RED}No input text available (either not provided or voice input failed). Exiting.{colorama.Style.RESET_ALL}")
        return

    current_text = initial_input_text
    # Default output (non-verbose) starts here
    print(f"{colorama.Fore.MAGENTA}Input: {colorama.Fore.CYAN}\"{current_text}\"{colorama.Style.RESET_ALL}\n")

    pipeline_run_history = []
    
    # Check if MarkdownLogger is the last agent and handle it separately
    markdown_logger_details = None
    agents_to_run_in_loop = list(execution_order) # Make a mutable copy

    if "MarkdownLogger" in agents_map and "MarkdownLogger" in agents_to_run_in_loop:
        # Verify it's intended to be last, or at least configured
        if agents_to_run_in_loop[-1] == "MarkdownLogger":
            markdown_logger_details = agents_map["MarkdownLogger"]
            agents_to_run_in_loop.pop() # Remove from normal processing
        else:
            if args.verbose:
                 print(f"{colorama.Fore.YELLOW}Warning: MarkdownLogger is configured but not as the last agent. It might not function as a full logger.{colorama.Style.RESET_ALL}")


    for i, agent_name in enumerate(agents_to_run_in_loop):
        if agent_name not in agents_map:
            if args.verbose:
                print(f"{colorama.Fore.YELLOW}Warning: Agent '{agent_name}' in execution_order not found in agents definition. Skipping.{colorama.Style.RESET_ALL}")
            continue
        
        agent_details = agents_map[agent_name]
        agent_path = agent_details.get('path')
        
        if not agent_path:
            if args.verbose:
                print(f"{colorama.Fore.YELLOW}Warning: Path not defined for agent '{agent_name}'. Skipping.{colorama.Style.RESET_ALL}")
            continue
        
        if args.verbose:
            print(f"{colorama.Fore.BLUE}--- Running Agent: {colorama.Style.BRIGHT}{agent_name}{colorama.Style.RESET_ALL}{colorama.Fore.BLUE} ---{colorama.Style.RESET_ALL}")

        text_before_agent_processing = current_text

        try:
            process_text_func = load_agent_function(agent_path)
            
            config_model_name = agent_details.get('gpt_version')
            env_model_name = os.getenv("GOOGLE_GEMINI_MODEL_NAME")
            
            model_to_use_for_agent = None
            source_of_model = "agent's internal default" # For verbose logging

            if config_model_name and config_model_name.strip() and config_model_name.lower() != "n/a":
                model_to_use_for_agent = config_model_name
                source_of_model = f"pipeline_config.json for {agent_name}"
            elif env_model_name and env_model_name.strip():
                model_to_use_for_agent = env_model_name
                source_of_model = ".env (GOOGLE_GEMINI_MODEL_NAME)"
            
            import inspect
            sig = inspect.signature(process_text_func)
            
            configured_params = agent_details.get('params', {})
            accepted_params_by_agent_func = {}
            for p_name, param_obj in sig.parameters.items():
                if p_name not in ['text', 'model_name', 'verbosity_level'] and p_name in configured_params:
                    accepted_params_by_agent_func[p_name] = configured_params[p_name]
                elif param_obj.kind == inspect.Parameter.VAR_KEYWORD: 
                    for k, v in configured_params.items():
                         if k not in sig.parameters and k not in ['text', 'model_name', 'verbosity_level']:
                            accepted_params_by_agent_func[k] = v
            
            call_args = {"text": text_before_agent_processing}
            agent_verbosity_level = 2 if args.verbose else 0 # Pass high verbosity to agent if pipeline is verbose

            if 'model_name' in sig.parameters:
                if model_to_use_for_agent:
                    if args.verbose:
                        print(f"{colorama.Fore.LIGHTBLACK_EX}--- [Pipeline] Using model: {model_to_use_for_agent} (from {source_of_model}) for {agent_name} ---{colorama.Style.RESET_ALL}")
                    call_args['model_name'] = model_to_use_for_agent
                elif args.verbose:
                     print(f"{colorama.Fore.LIGHTBLACK_EX}--- [Pipeline] Letting {agent_name} use its internal default model ---{colorama.Style.RESET_ALL}")
            elif model_to_use_for_agent and args.verbose:
                 print(f"{colorama.Fore.YELLOW}--- [Pipeline] Warning: Agent {agent_name} has gpt_version '{model_to_use_for_agent}' (from {source_of_model}) but its process_text function does not accept 'model_name'. Calling without it. ---{colorama.Style.RESET_ALL}")

            if 'verbosity_level' in sig.parameters:
                call_args['verbosity_level'] = agent_verbosity_level
            
            call_args.update(accepted_params_by_agent_func)
            processed_text_by_actual_agent = process_text_func(**call_args)
            
            current_text = processed_text_by_actual_agent 
            pipeline_run_history.append({'agent_name': agent_name, 'output_text': current_text})
            
            agent_color = AGENT_NAME_COLORS[i % len(AGENT_NAME_COLORS)]
            print(f"{agent_color}{colorama.Style.BRIGHT}[{agent_name}] {colorama.Fore.CYAN}{current_text}{colorama.Style.RESET_ALL}\n")

        except FileNotFoundError as e:
            print(f"{colorama.Fore.RED}Error loading agent {agent_name}: {e}{colorama.Style.RESET_ALL}")
            print(f"{colorama.Fore.RED}Pipeline execution halted.{colorama.Style.RESET_ALL}")
            return
        except (ImportError, AttributeError) as e:
            print(f"{colorama.Fore.RED}Error with agent {agent_name} module ({agent_path}): {e}{colorama.Style.RESET_ALL}")
            print(f"{colorama.Fore.RED}Pipeline execution halted.{colorama.Style.RESET_ALL}")
            return
        except Exception as e:
            print(f"{colorama.Fore.RED}An unexpected error occurred while running agent {agent_name}: {e}{colorama.Style.RESET_ALL}")
            print(f"{colorama.Fore.RED}Pipeline execution halted.{colorama.Style.RESET_ALL}")
            return
            
    if args.verbose:
        print(f"{colorama.Fore.GREEN}--- Pipeline Finished ---{colorama.Style.RESET_ALL}")
        final_text_before_logging = current_text # Already assigned
        print(f"{colorama.Fore.GREEN}Final text processed by agents:{colorama.Style.RESET_ALL} {colorama.Fore.CYAN}{final_text_before_logging}{colorama.Style.RESET_ALL}")
    else:
        final_text_before_logging = current_text


    # Audio generation if -a flag is used (prints remain for this feature as it's distinct, could be tied to verbose too)
    if args.audio:
        if ELEVENLABS_AVAILABLE:
            elevenlabs_api_key = os.getenv("ELEVENLABS_API_KEY")
            if not elevenlabs_api_key:
                print(f"{colorama.Fore.RED}Error: ELEVENLABS_API_KEY not found in .env. Cannot generate audio.{colorama.Style.RESET_ALL}")
            else:
                # Get ElevenLabs settings from environment variables or use defaults
                default_voice_id = "21m00Tcm4TlvDq8ikWAM" # Default if not in .env
                env_voice_id = os.getenv("ELEVENLABS_VOICE_ID")
                voice_id_to_use = env_voice_id if env_voice_id else default_voice_id
                
                model_id_to_use = os.getenv("ELEVENLABS_MODEL_ID")

                stability_to_use = None
                try:
                    env_stability = os.getenv("ELEVENLABS_STABILITY")
                    if env_stability is not None: stability_to_use = float(env_stability)
                except ValueError:
                    if args.verbose: print(f"{colorama.Fore.YELLOW}Warning: Invalid ELEVENLABS_STABILITY value. Using default.{colorama.Style.RESET_ALL}")

                similarity_boost_to_use = None
                try:
                    env_similarity = os.getenv("ELEVENLABS_SIMILARITY_BOOST")
                    if env_similarity is not None: similarity_boost_to_use = float(env_similarity)
                except ValueError:
                    if args.verbose: print(f"{colorama.Fore.YELLOW}Warning: Invalid ELEVENLABS_SIMILARITY_BOOST value. Using default.{colorama.Style.RESET_ALL}")

                style_to_use = None
                try:
                    env_style = os.getenv("ELEVENLABS_STYLE")
                    if env_style is not None: style_to_use = float(env_style)
                except ValueError:
                     if args.verbose: print(f"{colorama.Fore.YELLOW}Warning: Invalid ELEVENLABS_STYLE value. Using default.{colorama.Style.RESET_ALL}")
                
                use_speaker_boost_to_use = None
                env_speaker_boost = os.getenv("ELEVENLABS_USE_SPEAKER_BOOST")
                if env_speaker_boost is not None:
                    if env_speaker_boost.lower() == 'true':
                        use_speaker_boost_to_use = True
                    elif env_speaker_boost.lower() == 'false':
                        use_speaker_boost_to_use = False
                    elif args.verbose: 
                        print(f"{colorama.Fore.YELLOW}Warning: Invalid ELEVENLABS_USE_SPEAKER_BOOST value (should be true or false). Using default.{colorama.Style.RESET_ALL}")
                
                # Consider making generate_and_play_audio also accept verbosity
                generate_and_play_audio( 
                    text_to_speak=final_text_before_logging, 
                    api_key=elevenlabs_api_key,
                    voice_id=voice_id_to_use,
                    model_id=model_id_to_use,
                    stability=stability_to_use,
                    similarity_boost=similarity_boost_to_use,
                    style=style_to_use,
                    use_speaker_boost=use_speaker_boost_to_use
                )
        else: # ELEVENLABS_AVAILABLE is False
            if args.verbose:
                print(f"{colorama.Fore.RED}Warning: --audio flag was used, but ElevenLabs library is not installed. Please run 'pip install elevenlabs'.{colorama.Style.RESET_ALL}")


    if markdown_logger_details:
        logger_path = markdown_logger_details.get('path')
        if logger_path:
            if args.verbose:
                print(f"\n{colorama.Fore.BLUE}--- Running Logger: {colorama.Style.BRIGHT}MarkdownLogger{colorama.Style.RESET_ALL}{colorama.Fore.BLUE} ---{colorama.Style.RESET_ALL}")
            try:
                module_name = os.path.splitext(os.path.basename(logger_path))[0]
                spec = importlib.util.spec_from_file_location(module_name, logger_path)
                if spec is None or spec.loader is None:
                     raise ImportError(f"Could not load spec for module at {logger_path}")
                
                logger_module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(logger_module)

                if hasattr(logger_module, 'log_run_to_markdown'):
                    log_func = logger_module.log_run_to_markdown
                    
                    log_func_sig = inspect.signature(log_func)
                    log_call_args = {
                        "initial_input": initial_input_text,
                        "pipeline_steps": pipeline_run_history,
                        "original_filename_base": initial_input_text
                    }
                    if 'verbosity_level' in log_func_sig.parameters: # Pass verbosity to logger if it accepts it
                        log_call_args['verbosity_level'] = 2 if args.verbose else 0
                    
                    log_status = log_func(**log_call_args)
                    if args.verbose: # Only print log status if verbose
                        print(f"{colorama.Fore.GREEN}{log_status}{colorama.Style.RESET_ALL}")
                else:
                    # This error should probably always print
                    print(f"{colorama.Fore.RED}Error: MarkdownLogger ({logger_path}) does not have 'log_run_to_markdown' function.{colorama.Style.RESET_ALL}")
            except Exception as e:
                # This error should probably always print
                print(f"{colorama.Fore.RED}Error running MarkdownLogger: {e}{colorama.Style.RESET_ALL}")
        else:
            if args.verbose: # Only warn if verbose
                print(f"{colorama.Fore.YELLOW}Warning: MarkdownLogger path not defined in config. Skipping logging.{colorama.Style.RESET_ALL}")

if __name__ == "__main__":
    main()
