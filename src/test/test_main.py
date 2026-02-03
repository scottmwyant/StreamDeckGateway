"""Unit tests for StreamDeck state model and HID input report handling."""

import unittest
import time
from driver import InputReport, Streamdeck, BUTTON_COUNT


class TestInputReport(unittest.TestCase):
    """Test suite for InputReport class."""
    
    def test_init_valid_report(self):
        """Test initialization with valid 512-byte report."""
        header = [0x01, 0x00, 0x0f, 0x00]
        payload = [0x00] * 508
        report = bytes(header + payload)
        ir = InputReport(report)
        self.assertEqual(ir.report_id, 0x01)
        self.assertEqual(ir.command, 0x00)
        self.assertEqual(ir.length, 15)
        self.assertEqual(ir.value, 0)
        self.assertEqual(ir.countKeysDown, 0)
        self.assertEqual(ir.countKeysUp, 15)
    
    def test_init_invalid_length(self):
        """Test that invalid report length raises ValueError."""
        report = bytes([0x01, 0x00, 0x0f, 0x00] + [0x00] * 100)
        with self.assertRaises(ValueError):
            InputReport(report)
    
    def test_init_invalid_payload_length(self):
        """Test that mismatched payload length raises ValueError."""
        header = [0x01, 0x00, 0x10, 0x00]  # length = 16, but only 15 buttons
        payload = [0x00] * 508
        report = bytes(header + payload)
        with self.assertRaises(ValueError):
            InputReport(report)
    
    def test_init_invalid_type(self):
        """Test that non-bytes input raises TypeError."""
        with self.assertRaises(TypeError):
            InputReport("not bytes")
    
    def test_button_state_parsing(self):
        """Test that button states are correctly parsed into bit-packed value."""
        header = [0x01, 0x00, 0x0f, 0x00]
        payload = [0x00] * 15
        # Set buttons 0, 3, and 14 down
        payload[0] = 0x01
        payload[3] = 0x01
        payload[14] = 0x01
        payload.extend([0x00] * 493)
        report = bytes(header + payload)
        ir = InputReport(report)
        self.assertTrue(ir.isButtonDown(0))
        self.assertFalse(ir.isButtonDown(1))
        self.assertTrue(ir.isButtonDown(3))
        self.assertTrue(ir.isButtonDown(14))
        self.assertEqual(ir.countKeysDown, 3)
        self.assertEqual(ir.countKeysUp, 12)
    
    def test_button_index_out_of_range(self):
        """Test that invalid button indices raise ValueError."""
        header = [0x01, 0x00, 0x0f, 0x00]
        payload = [0x00] * 508
        report = bytes(header + payload)
        ir = InputReport(report)
        with self.assertRaises(ValueError):
            ir.isButtonDown(-1)
        with self.assertRaises(ValueError):
            ir.isButtonDown(15)
    
    def test_has_button_changed_requires_mask(self):
        """Test that hasButtonChanged raises if changedMask not set."""
        header = [0x01, 0x00, 0x0f, 0x00]
        payload = [0x00] * 508
        report = bytes(header + payload)
        ir = InputReport(report)
        with self.assertRaises(ValueError):
            ir.hasButtonChanged(0)
    
    def test_has_button_changed(self):
        """Test button change detection."""
        header = [0x01, 0x00, 0x0f, 0x00]
        payload = [0x00] * 508
        report = bytes(header + payload)
        ir = InputReport(report)
        # Manually set changedMask (bits 0, 2, 5 changed)
        ir.changedMask = 0b100101
        self.assertTrue(ir.hasButtonChanged(0))
        self.assertFalse(ir.hasButtonChanged(1))
        self.assertTrue(ir.hasButtonChanged(2))
        self.assertTrue(ir.hasButtonChanged(5))
        self.assertFalse(ir.hasButtonChanged(6))

class TestStreamdeck(unittest.TestCase):
    """Test suite for Streamdeck class."""
    
    def _createReport(self, button_states: dict = None) -> InputReport:
        """Helper to create an InputReport with optional button states."""
        header = [0x01, 0x00, 0x0f, 0x00]
        payload = [0x00] * 15
        if button_states:
            for idx, state in button_states.items():
                payload[idx] = 0x01 if state else 0x00
        payload.extend([0x00] * 493)
        report = bytes(header + payload)
        return InputReport(report)
    
    def test_init(self):
        """Test Streamdeck initialization."""
        sd = Streamdeck()
        self.assertEqual(len(sd._buffer), 1)  # Seeded with initial report
    
    def test_determine_event_type_no_change(self):
        """Test event type determination when no buttons change."""
        sd = Streamdeck()
        report = self._createReport()
        eventType = sd._determineEventType(report)
        self.assertEqual(eventType, 3)  # WakeUp
    
    def test_determine_event_type_key_down(self):
        """Test event type determination for KeyDown event."""
        sd = Streamdeck()
        report = self._createReport({0: True})  # Button 0 pressed
        # Set changedMask to indicate button 0 changed
        report.changedMask = 0b1
        report.changedCount = 1
        event_type = sd._determineEventType(report)
        self.assertEqual(event_type, 1)  # KeyDown
    
    def test_determine_event_type_key_up(self):
        """Test event type determination for KeyUp event."""
        sd = Streamdeck()
        # First, press a button
        report1 = self._createReport({0: True})
        report1.changedMask = 0b1
        report1.changedCount = 1
        sd._buffer.append(report1)
        
        # Then release it
        report2 = self._createReport({0: False})
        report2.changedMask = 0b1
        report2.changedCount = 1
        event_type = sd._determineEventType(report2)
        self.assertEqual(event_type, 0)  # KeyUp
    
    def test_handle_hid_input_report_invalid_type(self):
        """Test that invalid report type raises TypeError."""
        sd = Streamdeck()
        with self.assertRaises(TypeError):
            sd.handle_hid_input_report("invalid")

if __name__ == "__main__":
    unittest.main()
