"""Scrolldown Simulator Basic

Press the hotkey to send an inertial scroll-down to the window under the mouse cursor.
Pressing the hotkey again while scrolling stops it.
The hotkey is picked from the free ones with the "Change hotkey" button.
Uses only the Python standard library (ctypes + tkinter).
Settings are saved to settings.json next to the script (or the .exe).
"""
import ctypes
import json
import sys
import threading
import time
import tkinter as tk
from ctypes import wintypes
from pathlib import Path

user32 = ctypes.windll.user32
kernel32 = ctypes.windll.kernel32
winmm = ctypes.windll.winmm

MOD_ALT, MOD_CONTROL, MOD_SHIFT, MOD_NOREPEAT = 0x0001, 0x0002, 0x0004, 0x4000
VK_L, VK_SHIFT, VK_CONTROL, VK_MENU = 0x4C, 0x10, 0x11, 0x12
WM_HOTKEY, WM_APP = 0x0312, 0x8000
MOUSEEVENTF_WHEEL = 0x0800

# Key combinations tried when scanning for free hotkeys
MODIFIERS = [MOD_CONTROL | MOD_SHIFT, MOD_CONTROL | MOD_ALT, MOD_ALT | MOD_SHIFT,
             MOD_CONTROL | MOD_ALT | MOD_SHIFT]
KEYS = ({vk: chr(vk) for vk in range(0x41, 0x5B)}            # A-Z
        | {vk: chr(vk) for vk in range(0x30, 0x3A)}          # 0-9
        | {0x6F + i: f"F{i}" for i in range(1, 13)})         # F1-F12

TICK = 0.01                 # one wheel signal every 10 ms
MAX_UNITS_PER_SEC = 52000   # starting speed at 100 (one wheel notch = 120 units)

# A one-file .exe unpacks to a temp folder, so keep settings next to the .exe itself
APP_DIR = Path(sys.executable).parent if getattr(sys, "frozen", False) else Path(__file__).parent
SETTINGS_FILE = APP_DIR / "settings.json"
settings = {"speed": 50, "duration": 3.0, "hotkey": [MOD_CONTROL | MOD_SHIFT, VK_L]}
scrolling = threading.Event()
stop = threading.Event()
hotkey_thread_id = None
hotkey_registered = None    # None: not tried yet, True/False: registration result


def is_down(vk):
    return user32.GetAsyncKeyState(vk) & 0x8000


def modifier_down():
    return is_down(VK_CONTROL) or is_down(VK_SHIFT) or is_down(VK_MENU)


def hotkey_name(mod, vk):
    parts = [name for bit, name in ((MOD_CONTROL, "Ctrl"), (MOD_ALT, "Alt"), (MOD_SHIFT, "Shift"))
             if mod & bit]
    return "+".join(parts + [KEYS.get(vk, hex(vk))])


def save_settings():
    SETTINGS_FILE.write_text(json.dumps(settings), encoding="utf-8")


def scroll():
    # With Ctrl/Shift/Alt held the wheel zooms or scrolls sideways, so wait until they are released
    while modifier_down() and not stop.is_set():
        time.sleep(TICK)
    v0 = settings["speed"] / 100 * MAX_UNITS_PER_SEC
    T = settings["duration"]
    winmm.timeBeginPeriod(1)  # make sleep 1 ms accurate instead of 15 ms
    try:
        start = last = time.perf_counter()
        pending = 0.0
        while not stop.is_set():
            time.sleep(TICK)
            now = time.perf_counter()
            t = now - start
            if t >= T:
                break
            # Speed curve: v(t) = v0 * (1 - t/T)^3 -> starts fast, long smooth tail, stops exactly at T
            pending += v0 * (1 - t / T) ** 3 * (now - last)
            last = now
            step = int(pending)
            # If Ctrl/Shift/Alt is pressed mid-scroll (e.g. to stop), hold off so the wheel does not zoom
            if step and not modifier_down():
                user32.mouse_event(MOUSEEVENTF_WHEEL, 0, 0, -step, 0)
                pending -= step
    finally:
        winmm.timeEndPeriod(1)
        scrolling.clear()


def free_hotkeys():
    # Hotkeys another program took with RegisterHotKey fail to register here
    free = []
    for mod in MODIFIERS:
        for vk in KEYS:
            if user32.RegisterHotKey(None, 99, mod | MOD_NOREPEAT, vk):
                user32.UnregisterHotKey(None, 99)
                free.append((mod, vk))
    return free


def register_hotkey():
    # RegisterHotKey is bound to the calling thread, so this is only called from listen_hotkey
    global hotkey_registered
    mod, vk = settings["hotkey"]
    user32.UnregisterHotKey(None, 1)
    hotkey_registered = bool(user32.RegisterHotKey(None, 1, mod | MOD_NOREPEAT, vk))


def listen_hotkey():
    global hotkey_thread_id
    msg = wintypes.MSG()
    user32.PeekMessageW(ctypes.byref(msg), None, 0, 0, 0)  # create the message queue for PostThreadMessage
    hotkey_thread_id = kernel32.GetCurrentThreadId()
    register_hotkey()
    while user32.GetMessageW(ctypes.byref(msg), None, 0, 0) > 0:
        if msg.message == WM_APP:
            register_hotkey()
        elif msg.message == WM_HOTKEY:
            if scrolling.is_set():
                stop.set()
            else:
                stop.clear()
                scrolling.set()
                threading.Thread(target=scroll, daemon=True).start()


def main():
    try:
        settings.update(json.loads(SETTINGS_FILE.read_text(encoding="utf-8")))
    except (OSError, ValueError):
        pass

    root = tk.Tk()
    root.title("Scrolldown Simulator Basic")
    root.resizable(False, False)

    speed_var = tk.IntVar(value=settings["speed"])
    duration_var = tk.DoubleVar(value=settings["duration"])
    speed_var.trace_add("write", lambda *_: settings.update(speed=speed_var.get()))
    duration_var.trace_add("write", lambda *_: settings.update(duration=duration_var.get()))

    tk.Scale(root, label="Starting speed", from_=0, to=100, orient="horizontal",
             length=320, variable=speed_var).pack(padx=12, pady=(12, 4))
    tk.Scale(root, label="Stop after (seconds)", from_=0, to=15, resolution=0.1,
             orient="horizontal", length=320, variable=duration_var).pack(padx=12, pady=4)
    status = tk.Label(root)
    status.pack(padx=12, pady=4)

    def pick_hotkey():
        window = tk.Toplevel(root)
        window.title("Pick a hotkey")
        window.resizable(False, False)
        window.transient(root)
        window.grab_set()
        free = free_hotkeys()
        tk.Label(window, text=f"{len(free)} free hotkeys found:").pack(padx=12, pady=(12, 4))
        frame = tk.Frame(window)
        frame.pack(padx=12)
        listbox = tk.Listbox(frame, height=15, width=24)
        scrollbar = tk.Scrollbar(frame, command=listbox.yview)
        listbox.config(yscrollcommand=scrollbar.set)
        listbox.pack(side="left")
        scrollbar.pack(side="left", fill="y")
        for mod, vk in free:
            listbox.insert("end", hotkey_name(mod, vk))

        def choose(_=None):
            if not listbox.curselection():
                return
            settings["hotkey"] = list(free[listbox.curselection()[0]])
            save_settings()
            user32.PostThreadMessageW(hotkey_thread_id, WM_APP, 0, 0)
            window.destroy()

        listbox.bind("<Double-Button-1>", choose)
        listbox.bind("<Return>", choose)
        tk.Button(window, text="Select", width=10, command=choose).pack(pady=12)

    tk.Button(root, text="Change hotkey", command=pick_hotkey).pack(pady=(0, 12))

    def update_status():
        name = hotkey_name(*settings["hotkey"])
        if hotkey_registered is False:
            status.config(text=f"{name} is already used by another program!", fg="red")
        else:
            status.config(text=f"{name}: scroll   •   press again: stop", fg="black")
        root.after(300, update_status)

    def close():
        save_settings()
        root.destroy()

    threading.Thread(target=listen_hotkey, daemon=True).start()
    update_status()
    root.protocol("WM_DELETE_WINDOW", close)
    root.mainloop()


if __name__ == "__main__":
    main()
