#!/usr/bin/env python3

import os
import sys
try:
    import requests
except ImportError:
    import subprocess
    import sys

    print("⚠️ 'requests' not found. Installing on demand via uv...", file=sys.stderr)
    subprocess.check_call([
        "uv", "pip", "install", "requests"
    ])
    import requests  # retry after install

def main():
    try:
        
        # Get TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID
        telegram_bot_token = os.getenv('TELEGRAM_BOT_TOKEN')
        telegram_chat_id = os.getenv('TELEGRAM_CHAT_ID')

        if not telegram_bot_token or not telegram_chat_id:
          print("❌ Error: TELEGRAM_BOT_TOKEN or TELEGRAM_CHAT_ID not found in environment variables")
          sys.exit(1)

        # Get text from command line argument or use default
        if len(sys.argv) > 1:
            message = " ".join(sys.argv[1:])  # Join all arguments as text
        else:
            print("❌ Error: There MUST be valid message to send")
            sys.exit(1)

        url = f"https://api.telegram.org/bot{telegram_bot_token}/sendMessage"
        payload = {'chat_id': telegram_chat_id, 'text': message, 'parse_mode': 'Markdown'}
        response = requests.post(url, data=payload)

        if response.status_code == 200:
            sys.exit(0)
        else:
            print(f"Telegram API returned status code {response.status_code}: {response.text}", file=sys.stderr)
            sys.exit(4)

    except Exception as e:
        print(f"Unexpected error: {e}", file=sys.stderr)
        sys.exit(5)


if __name__ == "__main__":
    main()