"""STT example: local speech recognition (Chinese).

Usage:
    Press Enter to start recording, press Enter again to stop.
    The transcription result is printed to the console.
    Press Ctrl+C to exit.
"""

from sunfounder_stt import STT

stt = STT(type="local_fast", language="zh")

print("=" * 50)
print("STT: local speech recognition")
print("Press Enter to START recording, Enter again to STOP.")
print("Press Ctrl+C to exit.")
print("=" * 50)

try:
    while True:
        input("\nPress Enter to START recording...")
        stt.start_listening()

        print("[recording...] Press Enter to STOP.", end="", flush=True)
        input()
        stt.stop_listening()

        print("\r[transcribing...]", end="", flush=True)
        text = stt.get_result()
        if text:
            print(f"\rYou said: {text}")
        else:
            print("\rsilence! please say again.")
except KeyboardInterrupt:
    stt.stop_listening()
    print("\n\nBye!")
