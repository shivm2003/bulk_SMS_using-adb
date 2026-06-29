# Bulk SMS Automation using ADB (Android)

This project provides an automated, Python-based solution for sending bulk SMS messages directly from a physical Android device using ADB (Android Debug Bridge) and the Google Messages application. The system circumvents third-party SMS gateway fees and utilizes your personal or business carrier plan to send promotional or transactional text messages.

## Features

- **Automated Sending**: Dispatches pre-written SMS messages to a list of phone numbers automatically.
- **Deduplication & Validation**: Automatically filters duplicate numbers and validates mobile numbers using regex before sending.
- **Two Connection Methods**: 
  - `sms.py` - Works over a reliable USB connection.
  - `sms_wifi.py` - Works seamlessly over Wireless ADB (WiFi), requiring no cables.
- **Smart Queue System**: Sends up to 90 messages per run to avoid throttling or carrier bans. It automatically remembers the last sent number by removing processed numbers from the queue.
- **Logging & Tracking**: Logs all successfully delivered messages to `delivered.txt` and logs failed attempts/invalid numbers to `failed.txt`.
- **UI Interaction**: Bypasses typical intent-only limits by directly interacting with the Android screen to tap the "Send" button at predetermined coordinates.

---

## Prerequisites

1. **Python 3.x**: Ensure Python 3 is installed on your Windows machine.
2. **Android Platform Tools (ADB)**: The scripts require `adb.exe`. Download it from [Google's Official Site](https://developer.android.com/studio/releases/platform-tools).
3. **Android Device**:
    - Must have **Google Messages** set as the default SMS application.
    - **Developer Options** must be enabled on your phone.
    - **USB Debugging** (for USB) and/or **Wireless Debugging** (for WiFi) must be enabled in Developer Options.

---

## Setup Instructions

1. **Update ADB Path**: 
   Open `sms.py`, `sms_wifi.py`, and `find_send.py` in a text editor and update the `ADB` variable with the exact absolute path to your `adb.exe`. 
   *(By default, it is set to `C:\Users\shivam\Downloads\platform-tools-latest-windows\platform-tools\adb.exe`)*

2. **Configure Your Input Files**:
   - **`message.txt`**: Write your SMS content inside this file. If the file doesn't exist, the script will create it with a placeholder message.
   - **`numbers.txt`**: Add your target phone numbers here. Put **one number per line**.

3. **Configure the 'Send' Button Coordinates**:
   Because Android devices vary in screen resolution, you may need to adjust the tap coordinates (`SEND_TAP_X` and `SEND_TAP_Y`) for the Google Messages "Send" button.
   - We have provided a utility called `find_send.py` which analyzes an XML UI dump of your phone to find the exact center coordinates of the "Send" button. 
   - By default, it is configured for a `1080x2340` resolution device (X: 972, Y: 2081). 

---

## Usage

### Method 1: Using USB Connection
1. Connect your Android device via USB and accept the "Allow USB Debugging" prompt on your phone screen.
2. Open a terminal or command prompt in this directory.
3. Run the script:
   ```bash
   python sms.py
   ```
4. The script will automatically open Google Messages, input the number/message, and tap Send.

### Method 2: Using Wireless ADB (WiFi)
1. Ensure your PC and Android phone are on the **same WiFi network**.
2. Go to Developer Options -> Wireless Debugging on your phone. Note the **IP address and Port** (e.g., `192.168.1.10:43211`).
3. Run the script:
   ```bash
   python sms_wifi.py
   ```
4. When prompted in the console, enter your IP address and Port. The script will establish a wireless ADB connection and begin dispatching messages.

---

## Logs & Tracking

- **`delivered.txt`**: Check this file to see timestamps and numbers of successfully sent messages.
- **`failed.txt`**: Check this file for numbers that failed due to invalid formats, being offline, or unexpected errors.
- **`numbers.txt`**: The queue is modified dynamically. Successfully processed numbers are removed from the top, meaning you can safely restart the script if it crashes, and it will pick up exactly where it left off.

## Important Note

This script is meant for legitimate promotional or administrative purposes. **Use responsibly.** Be aware of your mobile carrier's Fair Usage Policy regarding bulk SMS sending to avoid having your SIM card temporarily restricted or permanently blocked.
