"""
overlay.py
----------
The main transparent, always-on-top overlay window built with Tkinter.

Learning concepts:
- Tkinter window attributes: transparency, always-on-top, no taskbar icon
- Threading to keep UI responsive while Gemini API call runs
- Drag-to-move a borderless window
- Dynamic text rendering (typing animation)
"""

import tkinter as tk
from tkinter import scrolledtext
import threading
import time
import io

import pystray
import keyboard
from PIL import Image, ImageDraw

from app.screen_capture import capture_region
from app.mistral_client import analyze_screen, preload_ocr_model

# ── Design Constants ──────────────────────────────────────────────────────────
BG_COLOR        = "#0d0d0f"          # near-black background
ACCENT          = "#ff7000"          # Mistral orange accent
ACCENT_LIGHT    = "#ff9a44"          # lighter orange
TEXT_COLOR      = "#e2e8f0"          # off-white text
MUTED           = "#64748b"          # muted gray
SUCCESS         = "#34d399"          # green for "ready"
ERROR_COLOR     = "#f87171"          # red for errors
FONT_FAMILY     = "Consolas"         # monospace for that terminal feel
WINDOW_ALPHA    = 0.92               # 0.0 fully transparent → 1.0 fully opaque
WINDOW_W        = 180
WINDOW_H        = 180


class OverlayApp:
    """
    Transparent floating overlay that captures the screen and queries Mistral Pixtral.
    Press Ctrl+Shift+A to trigger a capture, or use the Capture button.
    """

    def __init__(self, root: tk.Tk):
        self.root = root
        self.api_key = "Enter Your Mistral Api key"
        self._drag_x = 0
        self._drag_y = 0
        self._analyzing = False
        self._tray_icon = None

        self._setup_window()
        self._build_ui()
        self._setup_tray()
        self._setup_global_hotkeys()

        # Pre-load OCR model in the background so it's ready super fast
        threading.Thread(target=preload_ocr_model, daemon=True).start()

    # ── Window Setup ──────────────────────────────────────────────────────────

    def _setup_window(self):
        """Configure the transparent always-on-top borderless window."""
        self.root.title("Mistral Screen Assistant")
        self.root.geometry(f"{WINDOW_W}x{WINDOW_H}+80+80")

        # Transparent background color key (same as window bg so it blends)
        self.root.configure(bg=BG_COLOR)

        # Always on top of other windows
        self.root.attributes("-topmost", True)

        # Semi-transparent window
        self.root.attributes("-alpha", WINDOW_ALPHA)

        # Remove the default title bar and window decorations
        self.root.overrideredirect(True)

        # Keep it off the taskbar on Windows (we'll use tray icon instead)
        self.root.wm_attributes("-toolwindow", True)

        # Handle the window close (X) event gracefully
        self.root.protocol("WM_DELETE_WINDOW", self._hide_to_tray)

        # Keep polling for hotkey events on the main thread
        self.root.after(200, self._poll_hotkeys)

        # Bind drag events so the user can move the window
        self.root.bind("<ButtonPress-1>",   self._on_drag_start)
        self.root.bind("<B1-Motion>",       self._on_drag_move)

        # Hotkey: Ctrl+Shift+Z → capture
        self.root.bind_all("<Control-Shift-Z>", lambda e: self._trigger_capture())
        self.root.bind_all("<Control-Shift-z>", lambda e: self._trigger_capture())

    # ── UI Construction ───────────────────────────────────────────────────────

    def _build_ui(self):
        """Build all UI widgets."""
        self._build_title_bar()
        self._build_status_bar()
        self._build_response_area()
        self._build_button_row()

    def _build_title_bar(self):
        bar = tk.Frame(self.root, bg=BG_COLOR, height=34)
        bar.pack(fill="x")
        bar.pack_propagate(False)

        # Drag handle covers the whole bar
        bar.bind("<ButtonPress-1>", self._on_drag_start)
        bar.bind("<B1-Motion>",     self._on_drag_move)

        

        # Close button → hides to tray (use tray Quit to fully exit)
        close_btn = tk.Label(bar, text="✕", bg=BG_COLOR, fg="white",
                             font=(FONT_FAMILY, 12, "bold"), padx=10, cursor="hand2")
        close_btn.pack(side="right", fill="y")
        close_btn.bind("<Button-1>", lambda e: self._hide_to_tray())

        # Minimize / hide to tray button
        hide_btn = tk.Label(bar, text="—", bg=BG_COLOR, fg="white",
                            font=(FONT_FAMILY, 12), padx=8, cursor="hand2")
        hide_btn.pack(side="right", fill="y")
        hide_btn.bind("<Button-1>", lambda e: self._hide_to_tray())

    def _build_status_bar(self):
        self.status_frame = tk.Frame(self.root, bg="#1a1a2e", pady=5, padx=12)
        self.status_frame.pack(fill="x")

    

        

    def _build_response_area(self):
        frame = tk.Frame(self.root, bg=BG_COLOR, padx=12, pady=8)
        frame.pack(fill="both", expand=True)

       

        self.response_text = scrolledtext.ScrolledText(
            frame,
            bg="#111827", fg=TEXT_COLOR,
            font=(FONT_FAMILY, 10),
            wrap=tk.WORD,
            relief="flat",
            padx=10, pady=10,
            state="disabled",
            insertbackground=ACCENT_LIGHT,
            highlightthickness=1,
            highlightbackground="#2d2d3f",
            highlightcolor=ACCENT,
        )
        self.response_text.pack(fill="both", expand=True)

        # Style the scrollbar (Windows only, limited)
        self.response_text.vbar.configure(
            troughcolor="#1e1e2e", bg=ACCENT, activebackground=ACCENT_LIGHT,
            relief="flat", width=6
        )

    def _build_button_row(self):
        frame = tk.Frame(self.root, bg=BG_COLOR, pady=10, padx=12)
        frame.pack(fill="x")

        self.capture_btn = tk.Button(
            frame,
            text="⬤  Capture Screen",
            command=self._trigger_capture,
            bg=ACCENT, fg="white",
            activebackground=ACCENT_LIGHT, activeforeground="white",
            font=(FONT_FAMILY, 10, "bold"),
            relief="flat", padx=16, pady=6,
            cursor="hand2", bd=0
        )
        self.capture_btn.pack(side="left")

        clear_btn = tk.Button(
            frame,
            text="Clear",
            command=self._clear_response,
            bg="#1e1e2e", fg=MUTED,
            activebackground="#2d2d3f", activeforeground=TEXT_COLOR,
            font=(FONT_FAMILY, 9),
            relief="flat", padx=12, pady=6,
            cursor="hand2", bd=0
        )
        clear_btn.pack(side="left", padx=(8, 0))

        # Transparency slider
        tk.Label(frame, text="opacity", bg=BG_COLOR, fg=MUTED,
                 font=(FONT_FAMILY, 8)).pack(side="right")

        self.alpha_slider = tk.Scale(
            frame, from_=30, to=100, orient="horizontal",
            command=self._on_alpha_change,
            bg=BG_COLOR, fg=MUTED, troughcolor="#1e1e2e",
            highlightthickness=0, sliderrelief="flat",
            length=80, sliderlength=14, width=6,
            showvalue=False
        )
        self.alpha_slider.set(int(WINDOW_ALPHA * 100))
        self.alpha_slider.pack(side="right", padx=(0, 6))

    # ── System Tray ───────────────────────────────────────────────────────────

    def _make_tray_icon_image(self) -> Image.Image:
        """Generate a simple violet circle icon for the system tray."""
        size = 64
        img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        # Outer circle (accent color)
        draw.ellipse([2, 2, size - 2, size - 2], fill=(124, 58, 237, 255))
        # Inner ✦ symbol — draw as a simple white dot
        draw.ellipse([20, 20, size - 20, size - 20], fill=(255, 255, 255, 220))
        return img

    def _setup_tray(self):
        """Create and start the pystray system tray icon in a background thread."""
        icon_image = self._make_tray_icon_image()

        menu = pystray.Menu(
            pystray.MenuItem("Show Assistant",  self._show_from_tray, default=True),
            pystray.MenuItem("Capture Screen",  lambda icon, item: self._trigger_capture()),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("Quit",             self._quit_app),
        )

        self._tray_icon = pystray.Icon(
            name="MistralAssistant",
            icon=icon_image,
            title="Mistral Screen Assistant",
            menu=menu,
        )

        # Run tray icon in its own daemon thread
        tray_thread = threading.Thread(target=self._tray_icon.run, daemon=True)
        tray_thread.start()

    def _setup_global_hotkeys(self):
        """
        Register global hotkeys using the `keyboard` library.
        These fire even when the window is hidden or not focused.

        Ctrl+Shift+Space  → toggle show/hide the overlay
        Ctrl+Shift+Z      → capture screen globally
        """
        self._toggle_requested = False
        self._capture_requested = False

        keyboard.add_hotkey("ctrl+shift+space", self._request_toggle, suppress=False)
        keyboard.add_hotkey("ctrl+shift+z", self._request_capture, suppress=False)

    def _request_toggle(self):
        """Called from the keyboard thread — sets a flag for the main thread to act on."""
        self._toggle_requested = True
        
    def _request_capture(self):
        """Called from the keyboard thread for capture."""
        self._capture_requested = True

    def _poll_hotkeys(self):
        """Main-thread polling loop that processes hotkey flags every 200ms."""
        if self._toggle_requested:
            self._toggle_requested = False
            self._toggle_visibility()
        if self._capture_requested:
            self._capture_requested = False
            self._trigger_capture()
        self.root.after(200, self._poll_hotkeys)

    def _toggle_visibility(self):
        """Show the window if hidden, hide it if visible."""
        if self.root.state() == "withdrawn":
            self.root.deiconify()
            self.root.attributes("-topmost", True)
        else:
            self.root.withdraw()

    def _hide_to_tray(self):
        """Hide the window (restore with Ctrl+Shift+Space)."""
        self.root.withdraw()

    def _show_from_tray(self, icon=None, item=None):
        """Restore the window from tray (thread-safe)."""
        self.root.after(0, self.root.deiconify)
        self.root.after(0, lambda: self.root.attributes("-topmost", True))

    def _quit_app(self, icon=None, item=None):
        """Cleanly quit the app from the tray menu."""
        if self._tray_icon:
            self._tray_icon.stop()
        self.root.after(0, self.root.destroy)

    # ── Drag Logic ────────────────────────────────────────────────────────────

    def _on_drag_start(self, event):
        self._drag_x = event.x_root - self.root.winfo_x()
        self._drag_y = event.y_root - self.root.winfo_y()

    def _on_drag_move(self, event):
        x = event.x_root - self._drag_x
        y = event.y_root - self._drag_y
        self.root.geometry(f"+{x}+{y}")

    # ── Capture & Analyze ─────────────────────────────────────────────────────

    def _trigger_capture(self):
        """Called by button or hotkey. Validates API key then launches snipping tool."""
        if self._analyzing:
            return

        if not self.api_key:
            self._set_status("⚠ API key is not set", ERROR_COLOR)
            if self.root.state() == "withdrawn":
                self._toggle_visibility()
            return

        self.root.withdraw()  # hide overlay before snip

        # Small delay to let the OS hide the window properly before drawing snip overlay
        self.root.after(150, lambda: SnippingTool(self.root, self._on_snip_completed))

    def _on_snip_completed(self, x, y, w, h):
        """Callback from SnippingTool with selected region."""
        if x is None:
            # User cancelled snip
            self.root.deiconify()
            return

        self._analyzing = True
        self._set_status("Running fast OCR on selection…", ACCENT_LIGHT)
        self.capture_btn.config(state="disabled", text="⏳  Analyzing…")
        self.root.deiconify()

        # Run OCR + API in background thread
        thread = threading.Thread(target=self._capture_and_analyze, args=(x, y, w, h), daemon=True)
        thread.start()

    def _capture_and_analyze(self, x, y, w, h):
        """Background thread: capture snippet → OCR → Mistral text-only → display."""
        try:
            # 1. Capture the specific region (much faster for OCR than full screen)
            image = capture_region(x, y, w, h)

            # 2. Pipeline: fast OCR → Mistral clean text answer
            self._set_status("Extracting text via OCR…", ACCENT_LIGHT)
            response_text = analyze_screen(image, self.api_key)

            # 3. Display result
            self._set_status("● Answer ready", SUCCESS)
            self._animate_text(response_text)

        except Exception as exc:
            self.root.deiconify()
            err_msg = str(exc)
            # Friendly message for specific API errors
            if "401" in err_msg or "Unauthorized" in err_msg:
                friendly = "401 Unauthorized: Your Mistral API Key is invalid. Check console.mistral.ai"
            elif "429" in err_msg or "rate_limit" in err_msg.lower() or "Rate limit" in err_msg:
                friendly = "Rate limit hit. Wait ~30 seconds and try again."
            else:
                friendly = err_msg[:120]
            self._set_status(f"Error: {friendly}", ERROR_COLOR)
            self._write_response(f"[ERROR]\n{exc}")

        finally:
            self._analyzing = False
            self.root.after(0, lambda: self.capture_btn.config(
                state="normal", text="⬤  Capture Screen"
            ))

    # ── UI Helpers ────────────────────────────────────────────────────────────

    def _set_status(self, message: str, color: str = MUTED):
        def _update():
            self.status_label.config(text=f"  {message}", fg=color)
            self.status_dot.config(fg=color)
        self.root.after(0, _update)

    def _resize_window_to_content(self):
        """Dynamically adjust window height based on text lines to expand if the answer is long."""
        self.response_text.update_idletasks()
        try:
            display_lines = self.response_text.count("1.0", tk.END, "displaylines")
            num_lines = display_lines[0] if display_lines else 1
        except Exception:
            num_lines = 1

        if num_lines < 1:
            num_lines = 1

        # Base height is around 160. Each text line adds ~18 pixels. Max height ~600
        new_h = min(600, 160 + num_lines * 18)
        
        # Only set geometry if the height needs to change, preventing unnecessary UI freezes
        current_geom = self.root.geometry() # e.g. '480x520+80+80'
        try:
            current_h = int(current_geom.split('+')[0].split('x')[1])
            if current_h == new_h:
                return
        except Exception:
            pass

        self.root.geometry(f"{WINDOW_W}x{new_h}")

    def _write_response(self, text: str):
        """Directly write text to the response box (thread-safe via after)."""
        def _update():
            self.response_text.config(state="normal")
            self.response_text.delete("1.0", tk.END)
            self.response_text.insert(tk.END, text)
            self._resize_window_to_content()
            self.response_text.config(state="disabled")
        self.root.after(0, _update)

    def _animate_text(self, full_text: str, delay_ms: int = 8):
        """Type-writer animation: reveals characters one by one."""
        def _update():
            self.response_text.config(state="normal")
            self.response_text.delete("1.0", tk.END)
            self._resize_window_to_content()
            self.response_text.config(state="disabled")

        self.root.after(0, _update)

        def _type_char(index: int):
            if index <= len(full_text):
                def _insert():
                    self.response_text.config(state="normal")
                    self.response_text.insert(tk.END, full_text[index - 1] if index > 0 else "")
                    self.response_text.see(tk.END)
                    self._resize_window_to_content()
                    self.response_text.config(state="disabled")
                self.root.after(0, _insert)
                if index < len(full_text):
                    self.root.after(delay_ms, lambda i=index + 1: _type_char(i))

        self.root.after(delay_ms, lambda: _type_char(1))

    def _clear_response(self):
        self.response_text.config(state="normal")
        self.response_text.delete("1.0", tk.END)
        self._resize_window_to_content()
        self.response_text.config(state="disabled")
        self._set_status("Ready — Press Ctrl+Shift+Z or click Capture", SUCCESS)

    def _on_alpha_change(self, value):
        self.root.attributes("-alpha", int(value) / 100)


class SnippingTool:
    """A full-screen transparent overlay that lets the user drag a box to capture a region."""
    
    def __init__(self, parent_root, on_complete_callback):
        self.parent_root = parent_root
        self.on_complete = on_complete_callback

        self.top = tk.Toplevel(parent_root)
        self.top.attributes("-fullscreen", True)
        self.top.attributes("-alpha", 0.3)
        self.top.attributes("-topmost", True)
        self.top.config(cursor="crosshair")

        self.canvas = tk.Canvas(self.top, bg="black", highlightthickness=0)
        self.canvas.pack(fill="both", expand=True)

        self.start_x = None
        self.start_y = None
        self.start_x_root = None
        self.start_y_root = None
        self.rect_id = None

        self.canvas.bind("<ButtonPress-1>", self.on_press)
        self.canvas.bind("<B1-Motion>", self.on_drag)
        self.canvas.bind("<ButtonRelease-1>", self.on_release)
        self.top.bind("<Escape>", lambda e: self.cancel())
        self.canvas.bind("<Button-3>", lambda e: self.cancel())  # Right click to cancel

    def on_press(self, event):
        self.start_x = event.x
        self.start_y = event.y
        self.start_x_root = event.x_root
        self.start_y_root = event.y_root
        self.rect_id = self.canvas.create_rectangle(
            self.start_x, self.start_y, self.start_x, self.start_y,
            outline="#34d399", width=2, fill="#7c3aed", stipple="gray50"
        )

    def on_drag(self, event):
        self.canvas.coords(self.rect_id, self.start_x, self.start_y, event.x, event.y)

    def on_release(self, event):
        x1 = min(self.start_x_root, event.x_root)
        y1 = min(self.start_y_root, event.y_root)
        x2 = max(self.start_x_root, event.x_root)
        y2 = max(self.start_y_root, event.y_root)
        
        w = x2 - x1
        h = y2 - y1

        self.top.destroy()
        self.parent_root.update()

        if w > 10 and h > 10:
            self.on_complete(x1, y1, w, h)
        else:
            self.cancel()

    def cancel(self):
        self.top.destroy()
        self.on_complete(None, None, None, None)
