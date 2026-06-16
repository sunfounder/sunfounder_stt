"""STT example: cloud speech recognition via OpenAI API.

Requires an OpenAI API key. Set it before running::

    export OPENAI_API_KEY="sk-..."

Usage:
    Press Enter to start recording, press Enter again to stop.
    The transcription result is printed to the console.
    Type "quit" to exit.
"""

import os
from sunfounder_stt import STT

api_key = os.environ.get("OPENAI_API_KEY")
if not api_key:
    api_key = input("Enter your OpenAI API key: ").strip()
    if not api_key:
        print("No API key provided, exiting.")
        exit(1)

STT.API_KEY = api_key

stt = STT(type="online", language="zh")

print("=" * 50)
print("STT: cloud speech recognition")
print("Press Enter to START recording, Enter again to STOP.")
print("Type 'quit' to exit.")
print("=" * 50)

while True:
    cmd = input().strip()
    if cmd.lower() == "quit":
        break

    print("[recording...]", end="", flush=True)
    stt.start_listening()

    input()
    stt.stop_listening()
    print("\r[transcribing...]", end="", flush=True)

    text = stt.get_result()
    print(f"\rYou said: {text}")
