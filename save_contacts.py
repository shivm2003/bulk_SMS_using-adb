import time
import subprocess
import re
import os
import sys
import xml.etree.ElementTree as ET

NUMBERS_FILE = "numbers.txt"
SAVED_FILE = "saved.txt"
ADB = r"C:\Users\shivam\Downloads\platform-tools-latest-windows\platform-tools\adb.exe"

DEVICE_IP = ""

def load_numbers():
    try:
        with open(NUMBERS_FILE, "r") as f:
            numbers = [line.strip() for line in f if line.strip()]
    except FileNotFoundError:
        return []

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

def get_starting_index():
    last_idx = 0
    try:
        with open(SAVED_FILE, "r") as f:
            for line in f:
                match = re.match(r"Test(\d+)", line.strip())
                if match:
                    idx = int(match.group(1))
                    if idx > last_idx:
                        last_idx = idx
    except FileNotFoundError:
        pass
    return last_idx + 1

def adb_run(*args, retries=2):
    """Run an ADB command targeting the WiFi connected device."""
    if DEVICE_IP:
        cmd = [ADB, "-s", DEVICE_IP] + list(args)
    else:
        cmd = [ADB] + list(args)
        
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

def get_save_button_coords():
    """Dynamically finds the save button coordinates using uiautomator dump."""
    adb_run("shell", "uiautomator dump /sdcard/window_dump.xml")
    result = adb_run("shell", "cat /sdcard/window_dump.xml")
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
            text = node.get('text', '').lower()
            content_desc = node.get('content-desc', '').lower()
            resource_id = node.get('resource-id', '').lower()
            
            is_save_button = False
            # Look for common save button texts/ids
            if text in ['save', 'done', 'ok'] or content_desc in ['save', 'done']:
                is_save_button = True
            elif 'save' in resource_id:
                is_save_button = True
                
            if is_save_button:
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

def save_contact(number, index):
    print(f"Saving contact for {number}...")
    try:
        name = f"Test{index}"
        
        # Step 1: Open Contacts app to add new contact
        result = adb_run("shell", f"am start -a android.intent.action.INSERT -t vnd.android.cursor.dir/contact -e name '{name}' -e phone '{number}'")
        
        if result.returncode != 0:
            print(f"  Failed to open Contacts app: {result.stderr.strip()}")
            return False
            
        # Step 2: Wait for UI to load
        time.sleep(3.0)
        
        # Step 3: Try to find and click the save button
        coords = get_save_button_coords()
        if coords:
            tap_x, tap_y = coords
            tap_result = adb_run("shell", f"input tap {tap_x} {tap_y}")
            if tap_result.returncode == 0:
                print(f"  ✓ Tapped Save dynamically at ({tap_x}, {tap_y})")
            else:
                print(f"  ✗ Failed to tap Save button: {tap_result.stderr.strip()}")
                return False
        else:
            print("  [Warning] Could not find Save button dynamically. Trying generic keyevent (Enter)...")
            # Try to send Enter keyevent (sometimes works for forms)
            adb_run("shell", "input keyevent 66")
            
        time.sleep(2.0)
        
        # Press back to exit contact screen just in case it's still open
        adb_run("shell", "input keyevent 4")
        time.sleep(1.0)
        
        return True
    except Exception as e:
        print(f"Failed to save contact via ADB: {e}")
        return False

def connect_wifi_device():
    global DEVICE_IP
    print("\n--- Wireless ADB Setup ---")
    print("Leave blank and press enter if using USB connection.")
    ip_port = input("Enter your phone's IP address and Port (e.g., 192.168.1.10:5555): ").strip()
    
    if not ip_port:
        print("Using standard USB connection or default adb device.")
        return
        
    print(f"Connecting to {ip_port}...")
    result = subprocess.run([ADB, "connect", ip_port], capture_output=True, text=True)
    print(result.stdout.strip())
    
    if "cannot connect" in result.stdout.lower() or "failed" in result.stdout.lower():
        print("Failed to connect. Using default connection instead.")
        return
        
    DEVICE_IP = ip_port
    print(f"Successfully connected to {DEVICE_IP}")

def main():
    connect_wifi_device()
    
    queue = load_numbers()
    if not queue:
        print(f"No numbers found in {NUMBERS_FILE}.")
        return
        
    saved_count = 0
    
    print(f"Found {len(queue)} numbers to save.")
    
    idx = get_starting_index()
    print(f"Resuming from Test{idx}...")
    
    while queue:
        number = queue[0]
        success = save_contact(number, idx)
        if success:
            saved_count += 1
            with open(SAVED_FILE, "a") as f:
                f.write(f"Test{idx} : {number}\n")
            
            queue.pop(0)
            save_numbers(queue)
            
            idx += 1
        else:
            print("Stopping due to failure (possibly device offline).")
            break
            
    if not queue:
        print(f"\nDone! Successfully saved {saved_count} contacts. Queue is empty.")
    else:
        print(f"\nStopped! Saved {saved_count} contacts this run. {len(queue)} remaining.")

if __name__ == "__main__":
    main()
