import json
import importlib.util
import os
import argparse

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
    try:
        with open('pipeline_config.json', 'r') as f:
            config = json.load(f)
    except FileNotFoundError:
        print("Error: pipeline_config.json not found.")
        return
    except json.JSONDecodeError:
        print("Error: Could not decode pipeline_config.json. Please check its format.")
        return

    agents_map = {agent['name']: agent for agent in config.get('agents', [])}
    execution_order = config.get('execution_order', [])

    if not execution_order:
        print("No execution order defined in pipeline_config.json.")
        return
    
    if not agents_map:
        print("No agents defined in pipeline_config.json.")
        return

    parser = argparse.ArgumentParser(description="Run the GPT agent pipeline.")
    parser.add_argument("input_text", type=str, help="The initial text to process through the pipeline.")
    args = parser.parse_args()

    initial_input_text = args.input_text
    current_text = initial_input_text
    print(f"Initial text: {current_text}\n")

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
            # If MarkdownLogger is present but not last, run it as a normal agent (using its placeholder process_text)
            # Or print a warning. For now, let it run as normal if not last.
            print(f"Warning: MarkdownLogger is configured but not as the last agent. It might not function as a full logger.")


    for agent_name in agents_to_run_in_loop:
        if agent_name not in agents_map:
            print(f"Warning: Agent '{agent_name}' in execution_order not found in agents definition. Skipping.")
            continue
        
        agent_details = agents_map[agent_name]
        agent_path = agent_details.get('path')
        
        if not agent_path:
            print(f"Warning: Path not defined for agent '{agent_name}'. Skipping.")
            continue

        print(f"--- Running Agent: {agent_name} ---")
        try:
            process_text_func = load_agent_function(agent_path)
            current_text = process_text_func(current_text)
            pipeline_run_history.append({'agent_name': agent_name, 'output_text': current_text})
            print(f"Text after {agent_name}: {current_text}\n")
        except FileNotFoundError as e:
            print(f"Error loading agent {agent_name}: {e}")
            print("Pipeline execution halted.")
            return
        except (ImportError, AttributeError) as e:
            print(f"Error with agent {agent_name} module ({agent_path}): {e}")
            print("Pipeline execution halted.")
            return
        except Exception as e:
            print(f"An unexpected error occurred while running agent {agent_name}: {e}")
            print("Pipeline execution halted.")
            return
            
    print("--- Pipeline Finished ---")
    final_text_before_logging = current_text
    print(f"Final text processed by agents: {final_text_before_logging}")

    if markdown_logger_details:
        logger_path = markdown_logger_details.get('path')
        if logger_path:
            print(f"\n--- Running Logger: MarkdownLogger ---")
            try:
                # Dynamically import the specific logging function
                module_name = os.path.splitext(os.path.basename(logger_path))[0]
                spec = importlib.util.spec_from_file_location(module_name, logger_path)
                if spec is None or spec.loader is None:
                     raise ImportError(f"Could not load spec for module at {logger_path}")
                
                logger_module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(logger_module)

                if hasattr(logger_module, 'log_run_to_markdown'):
                    log_func = logger_module.log_run_to_markdown
                    # Use args.input_text for a potentially cleaner base filename
                    log_status = log_func(initial_input=initial_input_text, 
                                          pipeline_steps=pipeline_run_history,
                                          original_filename_base=args.input_text)
                    print(log_status)
                else:
                    print(f"Error: MarkdownLogger ({logger_path}) does not have 'log_run_to_markdown' function.")
            except Exception as e:
                print(f"Error running MarkdownLogger: {e}")
        else:
            print("Warning: MarkdownLogger path not defined in config. Skipping logging.")

if __name__ == "__main__":
    main()
