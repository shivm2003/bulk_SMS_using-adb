from datetime import datetime
import re
import subprocess
import time
import os
import urllib.parse
import sys
import xml.etree.ElementTree as ET

NUMBERS_FILE = "whatsappnumber.txt"
DELIVERED_FILE = "delivered_wa.txt"
FAILED_FILE = "failed_wa.txt"
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
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=15, encoding="utf-8", errors="replace")
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

# Previous hardcoded coordinates for WhatsApp (fallback)
# You may need to update these for your specific phone if dynamic finding fails
SEND_TAP_X = 990 
SEND_TAP_Y = 2200

def get_whatsapp_send_coords():
    """Dynamically finds the send button coordinates using uiautomator dump for WhatsApp."""
    adb_run("shell", "uiautomator dump /sdcard/window_dump_wa.xml")
    result = adb_run("shell", "cat /sdcard/window_dump_wa.xml")
    xml_data = result.stdout
    
    try:
        xml_start = xml_data.find("<?xml")
        if xml_start != -1:
            xml_data = xml_data[xml_start:]
        else:
            xml_start = xml_data.find("<hierarchy")
            if xml_start != -1:
                xml_data = xml_data[xml_start:]
                
        if not xml_data.strip():
            return None

        root = ET.fromstring(xml_data)
        
        for node in root.iter('node'):
            content_desc = (node.get('content-desc') or '').lower().strip()
            resource_id = (node.get('resource-id') or '').lower().strip()
            
            is_send_button = False
            # Common WhatsApp send button identifiers
            if 'com.whatsapp:id/send' in resource_id:
                is_send_button = True
            elif content_desc == 'send':
                is_send_button = True
                
            if is_send_button:
                bounds = node.get('bounds')
                if bounds:
                    match = re.match(r'\[(\d+),(\d+)\]\[(\d+),(\d+)\]', bounds)
                    if match:
                        x1, y1, x2, y2 = map(int, match.groups())
                        center_x = (x1 + x2) // 2
                        center_y = (y1 + y2) // 2
                        return center_x, center_y
    except Exception as e:
        print(f"  [Warning] XML parsing error: {e}")
        
    return None

def send_whatsapp(number, message):
    """
    Sends a WhatsApp message using ADB over WiFi:
    1. Opens WhatsApp Android App with the number and pre-filled message
    2. Dynamically finds and taps the Send button
    """
    print(f"Sending WhatsApp message to {number} via ADB (WiFi)...")
    try:
        # Use native app intent (not web browser URL)
        encoded_message = urllib.parse.quote(message)
        # Deep link specifically for the WhatsApp Android package
        intent_uri = f"whatsapp://send?phone={number}&text={encoded_message}"
        result = adb_run("shell", f"am start -a android.intent.action.VIEW -d '{intent_uri}' com.whatsapp.w4b")
        
        if result.returncode != 0:
            print(f"  Failed to open WhatsApp: {result.stderr.strip()}")
            return False
        
        # Wait for WhatsApp to fully load the chat and render the text
        time.sleep(3.5)
        
        # Find the Send button dynamically (with retries in case the text takes a moment to populate)
        coords = None
        for _ in range(3):
            coords = get_whatsapp_send_coords()
            if coords:
                break
            time.sleep(1.5)
        
        if coords:
            tap_x, tap_y = coords
            tap_result = adb_run("shell", f"input tap {tap_x} {tap_y}")
            if tap_result.returncode == 0:
                print(f"  ✓ Tapped WhatsApp Send dynamically at ({tap_x}, {tap_y})")
            else:
                print(f"  ✗ Failed to tap Send button: {tap_result.stderr.strip()}")
                return False
        else:
            print("  [Warning] Could not find WhatsApp Send button dynamically. Trying alternative keyevents...")
            # Fallback for WhatsApp: often just pressing Enter works if the text box has focus
            adb_run("shell", "input keyevent 66")
            # Try tapping the hardcoded coordinates
            adb_run("shell", f"input tap {SEND_TAP_X} {SEND_TAP_Y}")
            print(f"  ✓ Attempted fallback methods (Keyevents + Tap at {SEND_TAP_X}, {SEND_TAP_Y})")
        
        # Wait a moment before returning to ensure the message is sent before the app is closed/switched
        time.sleep(2.0)
        
        # Optional: return to home screen or close WhatsApp to prevent background clutter
        # adb_run("shell", "input keyevent 3") # Home button
        
        return True
    except Exception as e:
        print(f"Failed to send WhatsApp message via ADB: {e}")
        return False

def load_message():
    if not os.path.exists(MESSAGE_FILE):
        with open(MESSAGE_FILE, "w", encoding="utf-8") as f:
            f.write("Your promotional message goes here.")
        return "Your promotional message goes here."
    with open(MESSAGE_FILE, "r", encoding="utf-8") as f:
        return f.read().strip()

def connect_wifi_device():
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
        
    # Auto-correct common typo (e.g. 192.168.1.40.40169 -> 192.168.1.40:40169)
    if ip_port.count('.') == 4 and ':' not in ip_port:
        parts = ip_port.rsplit('.', 1)
        ip_port = f"{parts[0]}:{parts[1]}"
        print(f"Auto-corrected IP to: {ip_port}")
        
    print(f"Connecting to {ip_port}...")
    result = subprocess.run([ADB, "connect", ip_port], capture_output=True, text=True, encoding="utf-8", errors="replace")
    print(result.stdout.strip())
    
    # Check if adb connect threw an error in stderr or stdout
    if result.returncode != 0 or "cannot resolve host" in result.stderr.lower() or "cannot connect" in result.stdout.lower() or "failed" in result.stdout.lower():
        if result.stderr.strip():
            print(f"Error: {result.stderr.strip()}")
        print("Failed to connect. Please check the IP address and make sure Wireless debugging is enabled.")
        sys.exit(1)
        
    # Verify it is actually listed in adb devices
    devices = subprocess.run([ADB, "devices"], capture_output=True, text=True, encoding="utf-8", errors="replace").stdout
    if ip_port not in devices and ip_port.split(':')[0] not in devices:
        print(f"Device {ip_port} not found in 'adb devices'. Connection might have failed.")
        sys.exit(1)
        
    DEVICE_IP = ip_port
    print(f"Successfully connected to {DEVICE_IP}")

def main():
    print("=== WhatsApp Bulk Auto-Sender (WiFi Debugging) ===")
    print("Select a mode:")
    print("1. Normal Mode (Sends to up to 90 numbers)")
    print("2. Test1 Mode (Sends to exactly 10 numbers for testing)")
    
    choice = input("Enter 1 or 2: ").strip()
    if choice == "2":
        max_to_send = 10
        print("--- Test1 Mode Selected: Will stop after 10 messages ---")
    else:
        max_to_send = 90
        print("--- Normal Mode Selected: Will send up to 90 messages ---")
        
    connect_wifi_device()
    
    message = load_message()
    if not message:
        print(f"Message file {MESSAGE_FILE} is empty. Please add a message and try again.")
        return

    queue = load_numbers()
    if not queue:
        print(f"Number list {NUMBERS_FILE} is empty or not found.")
        return
        
    sent_count = 0

    try:
        while queue and sent_count < max_to_send:
            number = queue[0]

            if not is_valid_number(number):
                log(FAILED_FILE, number, "INVALID_NUMBER")
                queue.pop(0)
                save_numbers(queue)
                continue

            try:
                success = send_whatsapp(number, message)

                if success:
                    log(DELIVERED_FILE, number, "SENT")
                    queue.pop(0)
                    save_numbers(queue)
                    sent_count += 1
                    print(f"  Progress: {sent_count}/{max_to_send} messages sent.")
                else:
                    log(FAILED_FILE, number, "FAILED")
                    queue.pop(0)
                    save_numbers(queue)
                    print(f"  [!] Failed to send to {number}. Moving to next.")

            except Exception as e:
                log(FAILED_FILE, number, f"ERROR: {e}")
                break
                
    except KeyboardInterrupt:
        print("\n[!] Script manually interrupted by user.")
        
    if sent_count >= max_to_send:
        print(f"\nDone! Sent {max_to_send} messages as requested.")
    elif not queue:
        print("\nDone! All numbers in the queue have been processed.")
    else:
        print("\nScript stopped before finishing the queue (either by you or due to an error).")

if __name__ == "__main__":
    main()
