import importlib.util
import pathlib
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("sms_wifi", ROOT / "sms_wifi.py")
sms_wifi = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(sms_wifi)


class SmsWifiTests(unittest.TestCase):
    def test_decode_output_replaces_invalid_bytes(self):
        sample = b"bad \x8f bytes"
        self.assertEqual(sms_wifi.decode_output(sample), "bad � bytes")


if __name__ == "__main__":
    unittest.main()
