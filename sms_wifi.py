from datetime import datetime
import re
import subprocess
import time
import os
import urllib.parse
import sys

NUMBERS_FILE = "numbers.txt"
DELIVERED_FILE = "delivered.txt"
FAILED_FILE = "failed.txt"
MESSAGE_FILE = "message.txt"
ADB = r"C:\Users\shivam\Downloads\platform-tools-latest-windows\platform-tools\adb.exe"

# We will set this when the script starts
DEVICE_IP = ""

def load_numbers():
    try:
        with open(NUMBERS_FILE, "r") as f:
            numbers = [line.strip() for line in f if line.strip()]
    except FileNotFoundError:
        return []

    # Deduplicate while preserving order
    seen = set()
    unique = []
    for n in numbers:
        if n not in seen:
            seen.add(n)
            unique.append(n)
    return unique

def save_numbers(numbers):
    with open(NUMBERS_FILE, "w") as f:
        f.write("\n".join(numbers))

def log(file_name, number, status):
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open(file_name, "a") as f:
        f.write(f"{ts} | {number} | {status}\n")

def is_valid_number(number):
    return bool(re.fullmatch(r"\d{10,15}", number))

def adb_run(*args, retries=2):
    """Run an ADB command targeting the WiFi connected device."""
    cmd = [ADB, "-s", DEVICE_IP] + list(args)
    for attempt in range(retries + 1):
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
            if result.returncode == 0:
                return result
            if "offline" in result.stderr or "offline" in result.stdout:
                print(f"  Device offline, retrying ({attempt+1})...")
                time.sleep(2)
                continue
            return result
        except subprocess.TimeoutExpired:
            print(f"  ADB timed out, retrying ({attempt+1})...")
            time.sleep(2)
    return result

# Send button coordinates for Google Messages on Vivo 1917 (1080x2340)
SEND_TAP_X = 972
SEND_TAP_Y = 2081

def send_sms(number, message):
    """
    Sends an SMS using ADB + Google Messages over WiFi:
    1. Opens SMS app with the number and pre-filled message
    2. Directly taps the Send button at known coordinates
    """
    print(f"Sending SMS to {number} via ADB (WiFi)...")
    try:
        # Step 1: Open Google Messages with the number and message body
        encoded_message = urllib.parse.quote(message)
        intent_uri = f"sms:{number}?body={encoded_message}"
        result = adb_run("shell", f"am start -a android.intent.action.SENDTO -d '{intent_uri}' --ez exit_on_sent true")
        
        if result.returncode != 0:
            print(f"  Failed to open SMS app: {result.stderr.strip()}")
            return False
        
        # Step 2: Wait for the app to fully load and render the message
        time.sleep(3.0)
        
        # Step 3: Tap the Send button directly
        tap_result = adb_run("shell", f"input tap {SEND_TAP_X} {SEND_TAP_Y}")
        if tap_result.returncode == 0:
            print(f"  ✓ Tapped Send at ({SEND_TAP_X}, {SEND_TAP_Y})")
        else:
            print(f"  ✗ Failed to tap Send button: {tap_result.stderr.strip()}")
            return False
        
        # Step 4: Wait before sending next SMS
        time.sleep(2.0)
        
        return True
    except FileNotFoundError:
        print("Error: ADB not found!")
        return False
    except Exception as e:
        print(f"Failed to send SMS via ADB: {e}")
        return False

def load_message():
    if not os.path.exists(MESSAGE_FILE):
        with open(MESSAGE_FILE, "w", encoding="utf-8") as f:
            f.write("Your promotional message goes here.")
        return "Your promotional message goes here."
    with open(MESSAGE_FILE, "r", encoding="utf-8") as f:
        return f.read().strip()

def connect_wifi_device():
    """Ask for the IP address and connect via adb connect."""
    global DEVICE_IP
    print("\n--- Wireless ADB Setup ---")
    print("1. Ensure your phone and PC are on the SAME WiFi network.")
    print("2. Go to Developer Options on your phone.")
    print("3. Enable 'Wireless debugging'.")
    print("4. Tap on 'Wireless debugging' to see your IP address and Port (e.g., 192.168.1.10:5555)")
    
    ip_port = input("\nEnter your phone's IP address and Port (e.g., 192.168.1.10:5555): ").strip()
    if not ip_port:
        print("Invalid IP address. Exiting.")
        sys.exit(1)
        
    print(f"Connecting to {ip_port}...")
    result = subprocess.run([ADB, "connect", ip_port], capture_output=True, text=True)
    print(result.stdout.strip())
    
    if "cannot connect" in result.stdout.lower() or "failed" in result.stdout.lower():
        print("Failed to connect. Please check the IP address and make sure Wireless debugging is enabled.")
        sys.exit(1)
        
    DEVICE_IP = ip_port
    print(f"Successfully connected to {DEVICE_IP}")

def main():
    # First, setup WiFi connection
    connect_wifi_device()
    
    message = load_message()
    if not message:
        print(f"Message file {MESSAGE_FILE} is empty. Please add a message and try again.")
        return

    queue = load_numbers()
    
    max_to_send = 90
    sent_count = 0

    while queue and sent_count < max_to_send:
        number = queue[0]

        if not is_valid_number(number):
            log(FAILED_FILE, number, "INVALID_NUMBER")
            queue.pop(0)
            save_numbers(queue)
            continue

        try:
            success = send_sms(number, message)

            if success:
                log(DELIVERED_FILE, number, "SENT")
                queue.pop(0)
                save_numbers(queue)
                sent_count += 1
                print(f"  Progress: {sent_count}/{max_to_send} messages sent.")
            else:
                log(FAILED_FILE, number, "FAILED")
                # If ADB completely fails (e.g. device offline), we stop the whole script
                break

        except Exception as e:
            log(FAILED_FILE, number, f"ERROR: {e}")
            break
            
    if sent_count >= max_to_send:
        print(f"\nDone! Sent {max_to_send} messages as requested.")
    elif not queue:
        print("\nDone! All numbers in the queue have been processed.")
    else:
        print("\nScript stopped before finishing the queue (likely due to a connection error).")

if __name__ == "__main__":
    main()
