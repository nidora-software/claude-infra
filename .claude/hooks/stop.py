#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///

import json
import os
import sys
import random
import subprocess
from pathlib import Path

def get_completion_messages():
    """Return list of friendly completion messages."""
    return [
        "Work complete!",
        "All done!",
        "Task finished!",
        "Job complete!",
        "Ready for next task!"
    ]

def get_tts_script_path():
    """
    Determine which TTS script to use based on available API keys.
    Priority order: ElevenLabs > OpenAI > pyttsx3
    """
    # Get current script directory and construct utils/tts path
    script_dir = Path(__file__).parent
    tts_dir = script_dir / "utils" / "tts"
    
    # Check for ElevenLabs API key (highest priority)
    if os.getenv('ELEVENLABS_API_KEY'):
        elevenlabs_script = tts_dir / "elevenlabs_tts.py"
        if elevenlabs_script.exists():
            return str(elevenlabs_script)
    
    # Check for OpenAI API key (second priority)
    if os.getenv('OPENAI_API_KEY'):
        openai_script = tts_dir / "openai_tts.py"
        if openai_script.exists():
            return str(openai_script)
    
    # Fall back to pyttsx3 (no API key required)
    pyttsx3_script = tts_dir / "pyttsx3_tts.py"
    if pyttsx3_script.exists():
        return str(pyttsx3_script)
    
    return None

def get_llm_completion_message():
    """
    Generate completion message using available LLM services.
    Priority order: OpenAI > Anthropic > fallback to random message
    
    Returns:
        str: Generated or fallback completion message
    """
    # Get current script directory and construct utils/llm path
    script_dir = Path(__file__).parent
    llm_dir = script_dir / "utils" / "llm"
    
    # Try OpenAI first (highest priority)
    if os.getenv('OPENAI_API_KEY'):
        oai_script = llm_dir / "oai.py"
        if oai_script.exists():
            try:
                result = subprocess.run([
                    "uv", "run", str(oai_script), "--completion"
                ], 
                capture_output=True,
                text=True,
                timeout=10
                )
                if result.returncode == 0 and result.stdout.strip():
                    return result.stdout.strip()
            except (subprocess.TimeoutExpired, subprocess.SubprocessError):
                pass
    
    # Try Anthropic second
    if os.getenv('ANTHROPIC_API_KEY'):
        anth_script = llm_dir / "anth.py"
        if anth_script.exists():
            try:
                result = subprocess.run([
                    "uv", "run", str(anth_script), "--completion"
                ], 
                capture_output=True,
                text=True,
                timeout=10
                )
                if result.returncode == 0 and result.stdout.strip():
                    return result.stdout.strip()
            except (subprocess.TimeoutExpired, subprocess.SubprocessError):
                pass
    
    # Fallback to random predefined message
    messages = get_completion_messages()
    return random.choice(messages)

def announce_completion():
    """Announce completion using the best available TTS service."""
    try:
        tts_script = get_tts_script_path()
        if not tts_script:
            return  # No TTS scripts available
        
        # Get completion message (LLM-generated or fallback)
        completion_message = get_llm_completion_message()
        
        # Call the TTS script with the completion message
        subprocess.run([
            "uv", "run", tts_script, completion_message
        ], 
        capture_output=True,  # Suppress output
        timeout=10  # 10-second timeout
        )
        
    except (subprocess.TimeoutExpired, subprocess.SubprocessError, FileNotFoundError):
        # Fail silently if TTS encounters issues
        pass
    except Exception:
        # Fail silently for any other errors
        pass

def extract_latest_message(transcript_path):
    try:
        transcript_file = Path(transcript_path).expanduser()

        if not transcript_file.exists():
            return None, "Transcript file does not exist."

        with transcript_file.open('r', encoding='utf-8') as f:
            lines = f.readlines()

        if not lines:
            return None, "Transcript file is empty."

        # Find the latest assistant message (role=assistant)
        latest_assistant_msg = None
        for i in range(len(lines) - 1, -1, -1):
            line = lines[i].strip()
            if line:
                try:
                    data = json.loads(line)
                    if data.get('message', {}).get('role') == 'assistant':
                        latest_assistant_msg = data
                        break
                except json.JSONDecodeError:
                    continue
        
        if not latest_assistant_msg:
            return None, "No assistant message found in transcript."

        parentUuid = latest_assistant_msg.get('parentUuid', '')
        message_block = latest_assistant_msg.get('message', {})
        model = message_block.get('model')
        content_list = message_block.get('content', [])

        text = ''
        if content_list and isinstance(content_list, list):
            for block in content_list:
                if block.get('type') == 'text':
                    text = block.get('text', '').strip()
                    break

        if not model or model.strip() == '':
            model = None
        if not text or text.strip() == '':
            text = None

        return {'model': model, 'text': text, 'parentUuid': parentUuid}, None

    except Exception as e:
        return None, f"Error reading transcript: {e}"


def extract_project_name(transcript_path):
    try:
        path_str = str(transcript_path)
        # Look for the 'projects' directory as the standardized keyword
        if 'projects' in path_str:
            # Split by 'projects' and take the part after it
            after_projects = path_str.split('projects', 1)[1]
            # Remove leading slashes or backslashes
            after_projects = after_projects.lstrip('\\/')
            # Get the first path segment (project folder name)
            project_name = after_projects.split('\\')[0].split('/')[0]
            return project_name
        return None
    except Exception:
        return None


def extract_initial_prompt(transcript_path, prompt_uuid):
    try:
        transcript_file = Path(transcript_path).expanduser()

        if not transcript_file.exists():
            return None

        # Find all messages
        messages = []
        with transcript_file.open('r', encoding='utf-8') as f:
            for line in f:
                if line.strip():
                    try:
                        entry = json.loads(line.strip())
                        messages.append(entry)
                    except json.JSONDecodeError:
                        continue

        # Create a map for quick UUID lookups (using root-level uuid)
        current_uuid = prompt_uuid

        for entry in reversed(messages):
            message = entry.get('message', {})
            # Check if this is a user prompt: entry type is 'user' AND message role is 'user'
            if entry.get('uuid') == current_uuid and entry.get('type') == 'user' and message.get('role') == 'user' and isinstance(message.get('content'), str):
                return message.get('content').strip()
            else:
                current_uuid = entry.get('parentUuid')


        return None

    except Exception as e:
        return "Prompt extraction error: " + str(e)

def build_message(data):
    try:
        lines = []

        session_id = data.get('session_id')
        transcript_path = data.get('transcript_path')

        if not session_id or not transcript_path:
            return None, "Missing required fields: 'session_id' and 'transcript_path'."

        # Session always included
        lines.append(f"🆔 *Session*\n`{session_id}`")
        
        # Extract transcript latest message
        latest_data, _ = extract_latest_message(transcript_path)
        if latest_data and latest_data['model']:
            lines.append(f"🤖 *Model*\n{latest_data['model']}")

        # Extract and include project name
        project_name = extract_project_name(transcript_path)
        if project_name:
            lines.append(f"📁 *Project*\n{project_name}")

        # Check if stop hook is already active - if so, skip notification to prevent duplicates
        if data.get('stop_hook_active'):
            return None, "Stop hook already active - skipping notification to prevent duplicates"

        # Tool Info
        tool_name = data.get('tool_name')
        if tool_name:
            lines.append(f"🔧 *Tool Name*\n{tool_name}")

        tool_input = data.get('tool_input')
        if tool_input:
            file_path = tool_input.get('file_path')
            if file_path:
                lines.append(f"📄 *Tool Input File*\n`{file_path}`")

            content = tool_input.get('content')
            if content:
                lines.append(f"📝 *Tool Input Content*\n{content}")

        tool_response = data.get('tool_response')
        if tool_response:
            file_path_resp = tool_response.get('filePath')
            if file_path_resp:
                lines.append(f"📄 *Tool Response File*\n`{file_path_resp}`")

            success = tool_response.get('success')
            if success is not None:
                lines.append(f"💾 *Tool Success*\n`{success}`")


        # Extract prompt
        if latest_data and latest_data.get('parentUuid'):
            prompt = extract_initial_prompt(transcript_path, latest_data['parentUuid'])
            if prompt and prompt.strip():
                lines.append(f"💬 *Prompt*\n{prompt}")

        if latest_data and latest_data['text']:
            lines.append(f"📝 *Message*\n{latest_data['text']}")

        # Final input message
        final_message_block = ''
        input_message = data.get('message')
        if input_message:
            final_message_block = f"\n\n*⚠️ {input_message}*"

        # Optional title
        title = data.get('title')
        header = f"📣 *{title}*\n\n" if title else ""

        final_message = header + "\n\n".join(lines) + final_message_block
        return final_message, None

    except Exception as e:
        return None, f"Error building message: {e}"

def send_telegram_notification(data):
    """Send notification to Telegram using the build_message function."""
    try:
        # Build the message using the unified function
        message, error = build_message(data)

        if error or not message:
            return  # Skip if message building failed
        
        # Get telegram script path
        script_dir = Path(__file__).parent
        telegram_script = script_dir / "utils" / "telegram.py"
        
        if not telegram_script.exists():
            return  # Skip if telegram script doesn't exist
        
        # Call telegram.py via uv with the built message
        subprocess.run([
            "uv", "run", str(telegram_script), message
        ], 
        capture_output=True,  # Suppress output
        timeout=10  # 10-second timeout
        )
        
    except (subprocess.TimeoutExpired, subprocess.SubprocessError, FileNotFoundError):
        # Fail silently if telegram encounters issues
        pass
    except Exception:
        # Fail silently for any other errors
        pass
    
def main():
    try:
        # Read JSON input from stdin
        input_data = json.load(sys.stdin)

        # Announce completion via TTS
        announce_completion()

        # Send Telegram notification
        send_telegram_notification(input_data)

        sys.exit(0)

    except json.JSONDecodeError:
        # Handle JSON decode errors gracefully
        sys.exit(0)
    except Exception:
        # Handle any other errors gracefully
        sys.exit(0)


if __name__ == "__main__":
    main()
