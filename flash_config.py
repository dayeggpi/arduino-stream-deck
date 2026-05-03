#!/usr/bin/env python3
"""
flash_config.py - Push settings.ini keybindings to Arduino via serial.

Usage:
    python flash_config.py                        # auto-detect port
    python flash_config.py --port COM3            # specify port
    python flash_config.py --config mykeys.ini    # alternate config file
    python flash_config.py --dump                 # read current config from Arduino
    python flash_config.py --reset                # reset Arduino to firmware defaults
"""

import argparse
import configparser
import sys
import time

try:
    import serial
    import serial.tools.list_ports
except ImportError:
    print("ERROR: pyserial not installed. Run:  pip install pyserial")
    sys.exit(1)

# ── Key value map (must match Arduino Keyboard.h) ─────────────────────────────

KEY_MAP = {
    # Modifiers
    "CTRL":         0x80, "LCTRL":        0x80, "LEFT_CTRL":    0x80,
    "SHIFT":        0x81, "LSHIFT":       0x81, "LEFT_SHIFT":   0x81,
    "ALT":          0x82, "LALT":         0x82, "LEFT_ALT":     0x82,
    "GUI":          0x83, "WIN":          0x83, "LGUI":         0x83,
    "RCTRL":        0x84, "RIGHT_CTRL":   0x84,
    "RSHIFT":       0x85, "RIGHT_SHIFT":  0x85,
    "RALT":         0x86, "RIGHT_ALT":    0x86,
    "RGUI":         0x87, "RIGHT_GUI":    0x87,
    # Function keys F1-F12
    "F1":  0xC2, "F2":  0xC3, "F3":  0xC4, "F4":  0xC5,
    "F5":  0xC6, "F6":  0xC7, "F7":  0xC8, "F8":  0xC9,
    "F9":  0xCA, "F10": 0xCB, "F11": 0xCC, "F12": 0xCD,
    # Function keys F13-F24
    "F13": 0xF0, "F14": 0xF1, "F15": 0xF2, "F16": 0xF3,
    "F17": 0xF4, "F18": 0xF5, "F19": 0xF6, "F20": 0xF7,
    "F21": 0xF8, "F22": 0xF9, "F23": 0xFA, "F24": 0xFB,
    # Navigation
    "UP":           0xDA, "DOWN":         0xD9,
    "LEFT":         0xD8, "RIGHT":        0xD7,
    "BACKSPACE":    0xB2, "TAB":          0xB3,
    "RETURN":       0xB0, "ENTER":        0xB0,
    "ESC":          0xB1, "ESCAPE":       0xB1,
    "INSERT":       0xD1,
    "DELETE":       0xD4, "DEL":          0xD4,
    "PAGE_UP":      0xD3, "PAGEUP":       0xD3,
    "PAGE_DOWN":    0xD6, "PAGEDOWN":     0xD6,
    "HOME":         0xD2, "END":          0xD5,
    "CAPS_LOCK":    0xC1, "CAPSLOCK":     0xC1,
    "SPACE":        0x20,
    "PRINT_SCREEN": 0xCE,
}

MODIFIERS = {0x80, 0x81, 0x82, 0x83, 0x84, 0x85, 0x86, 0x87}


def resolve_key(token: str) -> int:
    token = token.strip()
    upper = token.upper()
    if upper in KEY_MAP:
        return KEY_MAP[upper]
    if len(token) == 1:
        return ord(token)
    raise ValueError(f"Unknown key: '{token}'")


def parse_binding(value: str) -> tuple[int, int, int]:
    """Return (modifier1, modifier2, key) as 0-255 ints."""
    parts = [p.strip() for p in value.split("+")]
    if len(parts) > 3:
        raise ValueError(f"Too many parts in '{value}' (max: MOD+MOD+KEY)")

    values = [resolve_key(p) for p in parts]

    mods = [v for v in values if v in MODIFIERS]
    keys = [v for v in values if v not in MODIFIERS]

    if len(keys) == 0:
        raise ValueError(f"No non-modifier key found in '{value}'")
    if len(keys) > 1:
        raise ValueError(f"Multiple non-modifier keys in '{value}'")
    if len(mods) > 2:
        raise ValueError(f"More than 2 modifiers in '{value}'")

    mod1 = mods[0] if len(mods) >= 1 else 0
    mod2 = mods[1] if len(mods) >= 2 else 0
    return mod1, mod2, keys[0]


def parse_ini(path: str) -> list[list[tuple[int, int, int]]]:
    """Returns bindings[page][button] = (mod1, mod2, key)."""
    cfg = configparser.ConfigParser()
    cfg.read(path)

    bindings = []
    for page_num in range(1, 5):
        section = f"Page{page_num}"
        if section not in cfg:
            raise ValueError(f"Missing [{section}] in {path}")
        page = []
        for btn_num in range(1, 5):
            key_name = f"Button{btn_num}"
            if key_name not in cfg[section]:
                raise ValueError(f"Missing {key_name} in [{section}]")
            value = cfg[section][key_name]
            try:
                page.append(parse_binding(value))
            except ValueError as e:
                raise ValueError(f"[{section}] {key_name}: {e}")
        bindings.append(page)
    return bindings


def find_arduino_port() -> str | None:
    keywords = ["arduino", "pro micro", "usb serial", "usb-serial", "leonardo", "sparkfun"]
    for port in serial.tools.list_ports.comports():
        desc = (port.description or "").lower()
        mfg  = (port.manufacturer or "").lower()
        if any(k in desc or k in mfg for k in keywords):
            return port.device
    return None


def open_serial(port: str, baud: int = 9600, retries: int = 3) -> serial.Serial:
    for i in range(retries):
        try:
            s = serial.Serial(port, baud, timeout=2)
            time.sleep(1.5)  # wait for Arduino reset after DTR
            s.reset_input_buffer()
            return s
        except serial.SerialException as e:
            if i == retries - 1:
                raise
            print(f"  Retry {i+1}/{retries}...")
            time.sleep(1)


def send_command(ser: serial.Serial, cmd: str) -> str:
    ser.write((cmd + "\n").encode())
    ser.flush()
    resp = ser.readline().decode(errors="replace").strip()
    return resp


def flash(ser: serial.Serial, bindings: list) -> bool:
    resp = send_command(ser, "CFG_START")
    if resp != "READY":
        print(f"ERROR: expected READY, got '{resp}'")
        return False
    print("Arduino ready. Sending bindings...")

    for p, page in enumerate(bindings):
        for b, (mod1, mod2, key) in enumerate(page):
            cmd = f"P{p+1}B{b+1} {mod1} {mod2} {key}"
            resp = send_command(ser, cmd)
            if resp != "OK":
                print(f"ERROR on {cmd}: '{resp}'")
                send_command(ser, "CFG_END")
                return False
            print(f"  P{p+1}B{b+1}: mod1={mod1} mod2={mod2} key={key}  → {resp}")

    resp = send_command(ser, "CFG_END")
    if resp != "SAVED":
        print(f"ERROR: expected SAVED, got '{resp}'")
        return False
    return True


def dump(ser: serial.Serial):
    ser.write(b"CFG_DUMP\n")
    ser.flush()
    print("Current Arduino config:")
    while True:
        line = ser.readline().decode(errors="replace").strip()
        if not line or line == "DUMP_END":
            break
        print(" ", line)


def reset_arduino(ser: serial.Serial):
    resp = send_command(ser, "CFG_RESET")
    if resp == "RESET":
        print("Arduino reset to firmware defaults and saved.")
    else:
        print(f"Unexpected response: '{resp}'")


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Flash keybindings to Steam Deck 2 Arduino")
    parser.add_argument("--port",   help="Serial port (e.g. COM3, /dev/ttyACM0)")
    parser.add_argument("--baud",   type=int, default=9600)
    parser.add_argument("--config", default="settings.ini", help="Path to settings.ini")
    parser.add_argument("--dump",   action="store_true", help="Dump current Arduino config")
    parser.add_argument("--reset",  action="store_true", help="Reset Arduino to firmware defaults")
    args = parser.parse_args()

    # Resolve port
    port = args.port
    if not port:
        port = find_arduino_port()
        if port:
            print(f"Auto-detected Arduino on {port}")
        else:
            print("ERROR: Arduino not found. Specify with --port COM3")
            print("Available ports:")
            for p in serial.tools.list_ports.comports():
                print(f"  {p.device}  {p.description}")
            sys.exit(1)

    # Connect
    print(f"Connecting to {port} @ {args.baud} baud...")
    try:
        ser = open_serial(port, args.baud)
    except serial.SerialException as e:
        print(f"ERROR: {e}")
        sys.exit(1)

    try:
        if args.dump:
            dump(ser)
        elif args.reset:
            reset_arduino(ser)
        else:
            print(f"Parsing {args.config}...")
            try:
                bindings = parse_ini(args.config)
            except (ValueError, FileNotFoundError) as e:
                print(f"ERROR: {e}")
                sys.exit(1)

            if flash(ser, bindings):
                print("\nDone! Keybindings saved to EEPROM.")
            else:
                print("\nFailed. Check connection and retry.")
                sys.exit(1)
    finally:
        ser.close()


if __name__ == "__main__":
    main()
