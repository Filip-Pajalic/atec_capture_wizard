#!/usr/bin/env python3
"""
Atec Capture Wizard

A guided GUI that walks you through a Phase 2b capture session.
For each step, it:
  - Tells you what to do at the heat pump
  - Records the timestamp when you click "Done"
  - Lets you type what you saw on the display
  - Saves everything to a clean log file you can upload

Requirements: Python 3.8+ with tkinter (usually preinstalled on Linux desktops).
On a fresh Debian/Ubuntu: sudo apt install python3-tk

Usage: python3 atec_capture_wizard.py
"""

import tkinter as tk
from tkinter import ttk, scrolledtext, filedialog, messagebox
from datetime import datetime
import json
import os

# ============================================================
# The capture script — list of steps the wizard walks through
# ============================================================
# Each step has:
#   id          — short id for the log
#   phase       — A/B/C/D as per Phase 2b plan
#   instruction — what to do at the heat pump
#   prompt      — what to write down (label for the text input)
#   wait_after  — recommended seconds to wait BEFORE clicking Done (advisory)
# ============================================================

STEPS = [
    # ---------- PHASE A — IDLE BASELINE ----------
    {
        "id": "A0_setup",
        "phase": "A — Setup",
        "instruction": (
            "Before we start:\n\n"
            "1. Make sure SSCOM is connected to 192.168.1.200:4196\n"
            "2. HEXShow is ticked, Show Time and Packe is ticked\n"
            "3. Click ClearData to wipe the buffer\n"
            "4. Tick ReceivedToFile and save as atec_session2_<date>.dat\n\n"
            "When the file is recording, click 'Done' to start the timed walk."
        ),
        "prompt": "Capture filename (paste the path SSCOM is recording to)",
        "wait_after": 0,
    },
    {
        "id": "A1_idle_baseline",
        "phase": "A — Idle baseline",
        "instruction": (
            "Phase A — Idle baseline (about 1 minute)\n\n"
            "Stand at the heat pump. The display should be in normal idle state\n"
            "(main screen, nothing scrolled).\n\n"
            "DON'T touch any buttons.\n\n"
            "Look at the main display screen. Write down EVERY value visible.\n"
            "Click 'Done' when you've written everything down."
        ),
        "prompt": "Main display values (one per line, e.g.\nUTE: 7.8\nFRAMLEDNING: 27.5)",
        "wait_after": 60,
    },
    # ---------- PHASE B — WALK INFO SCREENS ----------
    {
        "id": "B1_screen1",
        "phase": "B — Info screens",
        "instruction": (
            "Phase B begins — we'll walk through every info screen.\n\n"
            "Press the DOWN ARROW once.\n\n"
            "Wait ~10 seconds for any values to update,\n"
            "then write down the screen name and every visible value.\n\n"
            "Click 'Done' when written down."
        ),
        "prompt": "Screen 1 — name + values:",
        "wait_after": 20,
    },
    {
        "id": "B2_screen2",
        "phase": "B — Info screens",
        "instruction": "Press DOWN ARROW once. Wait, then write down screen name + values.",
        "prompt": "Screen 2 — name + values:",
        "wait_after": 20,
    },
    {
        "id": "B3_screen3",
        "phase": "B — Info screens",
        "instruction": "Press DOWN ARROW once. Write down screen name + values.",
        "prompt": "Screen 3 — name + values:",
        "wait_after": 20,
    },
    {
        "id": "B4_screen4",
        "phase": "B — Info screens",
        "instruction": "Press DOWN ARROW once. Write down screen name + values.",
        "prompt": "Screen 4 — name + values:",
        "wait_after": 20,
    },
    {
        "id": "B5_screen5",
        "phase": "B — Info screens",
        "instruction": "Press DOWN ARROW once. Write down screen name + values.",
        "prompt": "Screen 5 — name + values:",
        "wait_after": 20,
    },
    {
        "id": "B6_screen6",
        "phase": "B — Info screens",
        "instruction": "Press DOWN ARROW once. Write down screen name + values.",
        "prompt": "Screen 6 — name + values:",
        "wait_after": 20,
    },
    {
        "id": "B7_screen7",
        "phase": "B — Info screens",
        "instruction": (
            "Press DOWN ARROW once. Write down screen name + values.\n\n"
            "If you've cycled back to the main screen or a screen you've seen before,\n"
            "just write 'cycled back' in the box."
        ),
        "prompt": "Screen 7 — name + values (or 'cycled back'):",
        "wait_after": 20,
    },
    {
        "id": "B8_screen8",
        "phase": "B — Info screens",
        "instruction": "Press DOWN ARROW once. Write screen name + values, or 'cycled back' if you've seen this.",
        "prompt": "Screen 8 — name + values (or 'cycled back'):",
        "wait_after": 20,
    },
    {
        "id": "B9_back_to_main",
        "phase": "B — Info screens",
        "instruction": (
            "Keep pressing DOWN until you're back at the main display screen.\n\n"
            "Write down what's on the main screen now (it might have updated)."
        ),
        "prompt": "Main display values now:",
        "wait_after": 10,
    },
    # ---------- PHASE C — SERVICE MENU ----------
    {
        "id": "C1_enter_service",
        "phase": "C — Service menu",
        "instruction": (
            "Phase C — Service menu visit.\n\n"
            "Enter the service menu now (your usual button combo, e.g. hold left arrow 5 sec).\n\n"
            "Write down what you see in the top-level service menu — list the menu items."
        ),
        "prompt": "Top-level service menu items (e.g. KYLA, TILLSATS, MANUELL TEST, ...):",
        "wait_after": 15,
    },
    {
        "id": "C2_enter_installation",
        "phase": "C — Service menu",
        "instruction": (
            "Navigate to and ENTER the INSTALLATION submenu.\n\n"
            "Write down the items inside INSTALLATION."
        ),
        "prompt": "INSTALLATION submenu items:",
        "wait_after": 15,
    },
    {
        "id": "C3_kalibrering_givare",
        "phase": "C — Service menu",
        "instruction": (
            "Navigate to KALIBRERING GIVARE (sensor calibration).\n\n"
            "Write down EVERY sensor name and its offset value.\n"
            "(Likely all are 0.0; some might say -1000 = sensor not connected.)\n\n"
            "DO NOT change any values — read only.\n\n"
            "Scroll down in the menu to make sure you see all sensors."
        ),
        "prompt": "All sensor names and their offsets:",
        "wait_after": 60,
    },
    {
        "id": "C4_exit_service",
        "phase": "C — Service menu",
        "instruction": (
            "Exit out of all menus, back to the main display screen.\n\n"
            "Note anything unusual that happened during the service menu visit."
        ),
        "prompt": "Anything unusual? (or just 'no'):",
        "wait_after": 10,
    },
    # ---------- PHASE D — IDLE TAIL ----------
    {
        "id": "D1_idle_tail",
        "phase": "D — Idle tail",
        "instruction": (
            "Phase D — final idle period (about 1 minute).\n\n"
            "Don't touch anything. Let the bus run.\n\n"
            "When you're ready (no rush), click 'Done' to stop the session."
        ),
        "prompt": "Anything notable during the idle tail? (or just 'no'):",
        "wait_after": 60,
    },
    {
        "id": "STOP",
        "phase": "End",
        "instruction": (
            "All done!\n\n"
            "1. Go back to SSCOM and untick ReceivedToFile (this closes the .DAT cleanly)\n"
            "2. The capture log will be saved when you click Done\n\n"
            "Then upload BOTH files back to the conversation:\n"
            "   - the .DAT capture file\n"
            "   - the .txt log this wizard generates"
        ),
        "prompt": "(nothing to enter — just click Done to save the log)",
        "wait_after": 0,
    },
]


# ============================================================
# GUI
# ============================================================

class CaptureWizard(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Atec Capture Wizard — Phase 2b")
        self.geometry("780x620")
        self.minsize(640, 540)

        self.step_idx = 0
        self.results = []  # list of {step_id, phase, timestamp, instruction, response}
        self.session_start = datetime.now()

        # ----- Top: progress -----
        top = ttk.Frame(self, padding=10)
        top.pack(fill="x")

        self.progress_label = ttk.Label(top, text="", font=("Sans", 10, "bold"))
        self.progress_label.pack(side="left")

        self.timer_label = ttk.Label(top, text="", font=("Sans", 10))
        self.timer_label.pack(side="right")

        # ----- Phase chip -----
        chip = ttk.Frame(self, padding=(10, 0))
        chip.pack(fill="x")
        self.phase_label = ttk.Label(chip, text="", font=("Sans", 12, "bold"), foreground="#2F5496")
        self.phase_label.pack(side="left")

        # ----- Instruction box -----
        instr_frame = ttk.LabelFrame(self, text="What to do", padding=10)
        instr_frame.pack(fill="both", expand=False, padx=10, pady=(8, 4))

        self.instruction_text = scrolledtext.ScrolledText(
            instr_frame, height=10, wrap="word", font=("Sans", 11), state="disabled",
            background="#FFF7E0",
        )
        self.instruction_text.pack(fill="both", expand=True)

        # ----- Response box -----
        resp_frame = ttk.LabelFrame(self, text="What you saw / what you wrote down", padding=10)
        resp_frame.pack(fill="both", expand=True, padx=10, pady=(4, 4))

        self.prompt_label = ttk.Label(resp_frame, text="", font=("Sans", 10, "italic"))
        self.prompt_label.pack(anchor="w")

        self.response_text = scrolledtext.ScrolledText(resp_frame, height=8, wrap="word", font=("Mono", 11))
        self.response_text.pack(fill="both", expand=True, pady=(4, 0))

        # ----- Buttons -----
        btn_frame = ttk.Frame(self, padding=10)
        btn_frame.pack(fill="x")

        self.back_btn = ttk.Button(btn_frame, text="◀ Back", command=self.go_back)
        self.back_btn.pack(side="left")

        self.skip_btn = ttk.Button(btn_frame, text="Skip", command=self.go_next_skip)
        self.skip_btn.pack(side="left", padx=(8, 0))

        self.save_partial_btn = ttk.Button(btn_frame, text="Save log now", command=self.save_log)
        self.save_partial_btn.pack(side="left", padx=(8, 0))

        self.done_btn = ttk.Button(btn_frame, text="Done — record timestamp ▶", command=self.go_next)
        self.done_btn.pack(side="right")

        # Keyboard: Enter or Ctrl+Return = Done
        self.bind("<Control-Return>", lambda e: self.go_next())
        # Single Return inserts newline in the text widget — don't override

        # Live elapsed-time clock
        self._tick()

        # Start
        self.show_step()

    def _tick(self):
        elapsed = (datetime.now() - self.session_start).total_seconds()
        m, s = divmod(int(elapsed), 60)
        self.timer_label.config(text=f"Session elapsed: {m:02d}:{s:02d}")
        self.after(1000, self._tick)

    def show_step(self):
        step = STEPS[self.step_idx]
        # Progress
        self.progress_label.config(text=f"Step {self.step_idx + 1} of {len(STEPS)} — {step['id']}")
        self.phase_label.config(text=step["phase"])

        # Instruction
        self.instruction_text.config(state="normal")
        self.instruction_text.delete("1.0", "end")
        self.instruction_text.insert("1.0", step["instruction"])
        self.instruction_text.config(state="disabled")

        # Prompt + response box
        self.prompt_label.config(text=step["prompt"])
        self.response_text.delete("1.0", "end")

        # Restore previous response if going back
        if self.step_idx < len(self.results):
            prev = self.results[self.step_idx]
            self.response_text.insert("1.0", prev.get("response", ""))

        # Buttons
        self.back_btn.config(state="normal" if self.step_idx > 0 else "disabled")
        if self.step_idx == len(STEPS) - 1:
            self.done_btn.config(text="Save log and finish ✓")
        else:
            self.done_btn.config(text="Done — record timestamp ▶")

        # Focus the text box
        self.response_text.focus_set()

    def _capture_response(self):
        step = STEPS[self.step_idx]
        response = self.response_text.get("1.0", "end").rstrip()
        record = {
            "step_id": step["id"],
            "phase": step["phase"],
            "instruction": step["instruction"],
            "prompt": step["prompt"],
            "timestamp": datetime.now().isoformat(timespec="seconds"),
            "response": response,
        }
        # Replace if we're rewriting an earlier step, else append
        if self.step_idx < len(self.results):
            self.results[self.step_idx] = record
        else:
            self.results.append(record)

    def go_next(self):
        self._capture_response()
        if self.step_idx == len(STEPS) - 1:
            self.save_log()
            messagebox.showinfo(
                "All done",
                "Session log saved.\n\n"
                "Don't forget to also untick ReceivedToFile in SSCOM\n"
                "to close the .DAT capture file."
            )
            self.destroy()
            return
        self.step_idx += 1
        self.show_step()

    def go_next_skip(self):
        # Record skip but no timestamp recording for the action
        step = STEPS[self.step_idx]
        record = {
            "step_id": step["id"],
            "phase": step["phase"],
            "instruction": step["instruction"],
            "prompt": step["prompt"],
            "timestamp": datetime.now().isoformat(timespec="seconds"),
            "response": "[SKIPPED]",
        }
        if self.step_idx < len(self.results):
            self.results[self.step_idx] = record
        else:
            self.results.append(record)
        if self.step_idx < len(STEPS) - 1:
            self.step_idx += 1
            self.show_step()

    def go_back(self):
        if self.step_idx > 0:
            # Save current entry first so we don't lose it
            self._capture_response()
            self.step_idx -= 1
            self.show_step()

    def save_log(self):
        # Capture the current step's response too
        self._capture_response()

        default_name = f"atec_session_{self.session_start.strftime('%Y-%m-%d_%H-%M-%S')}"
        # Try to save in the user's home dir or current dir
        default_dir = os.path.expanduser("~")

        # Save both .txt and .json
        txt_path = filedialog.asksaveasfilename(
            title="Save capture log as text",
            defaultextension=".txt",
            initialdir=default_dir,
            initialfile=default_name + ".txt",
            filetypes=[("Text files", "*.txt"), ("All files", "*.*")],
        )
        if not txt_path:
            return

        # Plain text version (human-friendly)
        with open(txt_path, "w", encoding="utf-8") as f:
            f.write("=" * 70 + "\n")
            f.write("Thermia Atec — Phase 2b Capture Session Log\n")
            f.write(f"Session started: {self.session_start.isoformat(timespec='seconds')}\n")
            f.write(f"Saved at:        {datetime.now().isoformat(timespec='seconds')}\n")
            f.write("=" * 70 + "\n\n")
            for i, r in enumerate(self.results, 1):
                f.write(f"--- Step {i}: {r['step_id']} ({r['phase']}) ---\n")
                f.write(f"Timestamp: {r['timestamp']}\n")
                f.write(f"Prompt: {r['prompt']}\n")
                f.write(f"Response:\n{r['response']}\n\n")

        # Also save JSON for easy programmatic correlation
        json_path = txt_path.replace(".txt", ".json")
        if json_path == txt_path:
            json_path = txt_path + ".json"
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump({
                "session_start": self.session_start.isoformat(timespec="seconds"),
                "saved_at": datetime.now().isoformat(timespec="seconds"),
                "steps": self.results,
            }, f, indent=2, ensure_ascii=False)

        messagebox.showinfo(
            "Saved",
            f"Saved:\n  {txt_path}\n  {json_path}\n\n"
            "Upload both files (or just the .txt) to the conversation."
        )


if __name__ == "__main__":
    app = CaptureWizard()
    app.mainloop()
