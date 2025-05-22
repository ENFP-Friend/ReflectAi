import os
import datetime

def log_run_to_markdown(initial_input: str, 
                        pipeline_steps: list, 
                        original_filename_base: str = "pipeline_run") -> str:
    """
    Logs the initial input and all subsequent agent outputs to a Markdown file.

    Args:
        initial_input (str): The very first text input to the pipeline.
        pipeline_steps (list): A list of dictionaries, where each dictionary is:
                               {'agent_name': str, 'output_text': str}
                               representing the output after each agent.
        original_filename_base (str): A base for the log filename, derived from 
                                      the initial input text for easier identification.

    Returns:
        str: A status message, e.g., path to the saved log file.
    """
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # Sanitize the original_filename_base to be filesystem-friendly
    # Keep it short and remove problematic characters
    safe_base = "".join(c if c.isalnum() or c in (' ', '_', '-') else '_' for c in original_filename_base[:30]).rstrip()
    safe_base = safe_base.replace(' ', '_')
    if not safe_base: # handle case where input was all non-alphanum
        safe_base = "log"

    log_filename = f"{timestamp}_{safe_base}.md"
    
    markdown_content = f"# Pipeline Run Log ({timestamp})\n\n"
    markdown_content += f"## Initial Input\n\n```\n{initial_input}\n```\n\n"
    markdown_content += "---\n\n"

    for i, step in enumerate(pipeline_steps):
        agent_name = step.get('agent_name', f"Unknown Agent {i+1}")
        output_text = step.get('output_text', "No output recorded.")
        markdown_content += f"## After Agent: {agent_name}\n\n"
        markdown_content += f"```\n{output_text}\n```\n\n"
        markdown_content += "---\n\n"
        
    # The last step in pipeline_steps is the final output of the "normal" agents
    # If MarkdownLogger is the *only* thing that ran after initial input (unlikely but possible)
    # then pipeline_steps might be empty if not handled carefully in run_pipeline.py
    if pipeline_steps:
        final_text_before_logging = pipeline_steps[-1]['output_text']
        markdown_content += f"## Final Text Processed by Pipeline (before logging)\n\n"
        markdown_content += f"```\n{final_text_before_logging}\n```\n\n"

    logs_dir = "pipeline_logs"
    if not os.path.exists(logs_dir):
        os.makedirs(logs_dir)
        
    full_log_path = os.path.join(logs_dir, log_filename)

    try:
        with open(full_log_path, 'w', encoding='utf-8') as f:
            f.write(markdown_content)
        return f"Log successfully saved to: {full_log_path}"
    except IOError as e:
        return f"Error saving log file: {e}"

# This process_text function is a placeholder to conform to the expected agent structure
# if run_pipeline.py were to call it directly in the loop.
# However, run_pipeline.py will be modified to call log_run_to_markdown directly
# with the necessary historical data.
def process_text(text: str) -> str:
    """
    Placeholder. The main functionality is in log_run_to_markdown.
    This function will ideally not be called directly by the modified run_pipeline.py
    when handling the MarkdownLogger agent.
    """
    return "MarkdownLogger executed. (This is a placeholder message; actual logging handled by log_run_to_markdown)"
