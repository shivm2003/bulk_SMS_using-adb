"""Quick script to find the Send button coordinates from ui_dump.xml on the phone."""
import subprocess, re

ADB = r"C:\Users\shivam\Downloads\platform-tools-latest-windows\platform-tools\adb.exe"

# Read the XML from the phone
result = subprocess.run([ADB, "-d", "shell", "cat /sdcard/ui_dump.xml"], capture_output=True, text=True, timeout=15)
xml = result.stdout

if not xml:
    print("ERROR: Could not read ui_dump.xml from device")
    print("stderr:", result.stderr)
else:
    print(f"Got {len(xml)} chars of XML")
    # Find all elements with "send" in content-desc or resource-id
    # Pattern: anything with Send near bounds
    nodes = re.findall(r'<node[^>]*(?:content-desc|resource-id)="[^"]*[Ss]end[^"]*"[^>]*>', xml)
    if not nodes:
        # Try reverse order (bounds before content-desc)
        nodes = re.findall(r'<node[^>]*bounds="[^"]*"[^>]*(?:content-desc|resource-id)="[^"]*[Ss]end[^"]*"[^>]*>', xml)
    
    if nodes:
        for node in nodes:
            print(f"\nFound node: {node[:200]}")
            bounds = re.search(r'bounds="\[(\d+),(\d+)\]\[(\d+),(\d+)\]"', node)
            if bounds:
                x1, y1, x2, y2 = int(bounds.group(1)), int(bounds.group(2)), int(bounds.group(3)), int(bounds.group(4))
                cx, cy = (x1+x2)//2, (y1+y2)//2
                print(f"  Bounds: [{x1},{y1}][{x2},{y2}]  ->  Center: ({cx}, {cy})")
    else:
        print("No nodes with 'send' found. Searching all content-desc values:")
        descs = re.findall(r'content-desc="([^"]+)"', xml)
        for d in descs:
            print(f"  - {d}")
