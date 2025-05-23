# ReflectAI Text Processing Pipeline

## Overview

ReflectAI is a Python-based text processing pipeline designed for modularity and extensibility. Its core purpose is to allow users to chain together a series of custom "agents" to transform or analyze input text. Each agent performs a specific, user-defined task, and new agents can be easily created and integrated into the pipeline.

The current set of agents serves as examples to demonstrate the pipeline's capabilities. The true function of the project lies in its flexible architecture, enabling users to build diverse and complex text processing workflows.

The pipeline supports various input methods, including direct text input and voice input (via Whisper), and can generate audio output of the final processed text (via ElevenLabs). The behavior and sequence of agents are controlled by `pipeline_config.json`.

## Running the Pipeline (`run_pipeline.py`)

The main script to execute the pipeline is `run_pipeline.py`.

### Commands and Arguments:

1.  **`input_text`** (Positional Argument)
    *   **Description**: The initial text string that you want the pipeline to process.
    *   **Usage**:
        ```bash
        python run_pipeline.py "This is the sample text to be processed by the agents."
        ```
    *   **Note**: If this argument is omitted, the script will attempt to capture audio input from the microphone.

2.  **`-a`** or **`--audio`** (Optional Flag)
    *   **Description**: When this flag is included, the script will generate and play an audio version of the final processed text using the ElevenLabs API. This requires the ElevenLabs library to be installed and an `ELEVENLABS_API_KEY` to be set in your `.env` file.
    *   **Usage**:
        ```bash
        python run_pipeline.py "Process this text and speak it." -a
        python run_pipeline.py "Another example." --audio
        python run_pipeline.py -a  # (If using voice input for the text)
        ```

3.  **`--mic-duration <seconds>`** (Optional Argument)
    *   **Description**: If no `input_text` is provided (i.e., you intend to use voice input), this argument specifies the duration in seconds for which the microphone will record audio.
    *   **Default**: `5` seconds.
    *   **Usage**:
        ```bash
        python run_pipeline.py --mic-duration 10  # Records voice input for 10 seconds
        python run_pipeline.py --mic-duration 7 -a # Records for 7 seconds and then plays audio output
        ```

### Configuration:

*   **`pipeline_config.json`**: This file defines the agents available to the pipeline and the sequence in which they should be executed. Each agent entry typically specifies a `name` and a `path` to its Python script. Agents might also have specific configurations like `gpt_version`.
*   **`.env` file**: Used to store environment variables, such as:
    *   `GOOGLE_GEMINI_MODEL_NAME`: Specifies a default Gemini model for agents that use it.
    *   `ELEVENLABS_API_KEY`: Your API key for ElevenLabs text-to-speech.
    *   `ELEVENLABS_VOICE_ID`: The specific voice ID to use for audio generation.
    *   Other ElevenLabs settings like `ELEVENLABS_MODEL_ID`, `ELEVENLABS_STABILITY`, `ELEVENLABS_SIMILARITY_BOOST`, `ELEVENLABS_STYLE`, `ELEVENLABS_USE_SPEAKER_BOOST`.

### Example Usage:

*   Process text provided directly:
    ```bash
    python run_pipeline.py "Hello world, let's transform this text."
    ```
*   Process text and get audio output:
    ```bash
    python run_pipeline.py "Speak this message after processing." --audio
    ```
*   Use voice input for 8 seconds:
    ```bash
    python run_pipeline.py --mic-duration 8
    ```
*   Use voice input (default duration) and get audio output:
    ```bash
    python run_pipeline.py --audio
    ```

The pipeline will process the input through the sequence of agents defined in `execution_order` within `pipeline_config.json`. If the `MarkdownLogger` agent is configured as the last agent, it will create a markdown file summarizing the pipeline run and the transformations at each step.
