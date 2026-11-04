import io
import os
import subprocess
import threading
import time
from tkinter import filedialog, messagebox
import customtkinter as ctk
import yt_dlp
from PIL import Image, ImageDraw
import downloader
from PIL import Image
from customtkinter import CTkImage
import sys
import json


def get_resource_path(relative_path):
    """ Get absolute path to resource, works for dev and for PyInstaller """
    try:
        # PyInstaller creates a temp folder and stores path in _MEIPASS
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

# Default Theme Setup
ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")

BG_MAIN = ("#F4F4F6", "#121214")
BG_CARD = ("#FFFFFF", "#1D1D20")
TEXT_PRIMARY = ("#111115", "#F2F2F5")
TEXT_MUTED = ("#666670", "#8E8E96")
ACCENT_BLUE = "#47B8F5"

FORMAT_LIST = [
    "mp4 360p", "mp4 720p", "mp4 1080p", "mp4 best",
    "mp3 128k", "mp3 192k", "mp3 320k",
    "FLAC / ALAC 1,411 kbps", "WAV 1,411 kbps"
]


def create_circular_red_download_icon(size=(24, 24)):
    """Generates circular white background icon with red tray and downward arrow."""
    img = Image.new("RGBA", size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    draw.ellipse([0, 0, size[0]-1, size[1]-1], fill=(255, 255, 255, 255))
    
    w, h = size
    draw.rectangle([int(w*0.25), int(h*0.72), int(w*0.75), int(h*0.80)], fill="#FF0000")
    draw.rectangle([int(w*0.25), int(h*0.55), int(w*0.32), int(h*0.72)], fill="#FF0000")
    draw.rectangle([int(w*0.68), int(h*0.55), int(w*0.75), int(h*0.72)], fill="#FF0000")
    
    draw.polygon([
        (int(w*0.5), int(h*0.62)),
        (int(w*0.28), int(h*0.38)),
        (int(w*0.42), int(h*0.38)),
        (int(w*0.42), int(h*0.18)),
        (int(w*0.58), int(h*0.18)),
        (int(w*0.58), int(h*0.38)),
        (int(w*0.72), int(h*0.38))
    ], fill="#FF0000")
    
    return ctk.CTkImage(light_image=img, dark_image=img, size=size)

def create_circular_red_download_icon(size=(24, 24)):
    from PIL import Image, ImageDraw
    scale = 2
    w, h = size[0] * scale, size[1] * scale
    img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    
    # Red circular background
    draw.ellipse([0, 0, w - 1, h - 1], fill="#DC2626")
    
    # White downward arrow
    draw.line([(w * 0.5, h * 0.28), (w * 0.5, h * 0.65)], fill="white", width=max(2, scale))
    draw.polygon([
        (w * 0.32, h * 0.5), 
        (w * 0.5, h * 0.7), 
        (w * 0.68, h * 0.5)
    ], fill="white")
    
    img = img.resize(size, Image.Resampling.LANCZOS)
    return ctk.CTkImage(light_image=img, dark_image=img, size=size)

class TrackRow(ctk.CTkFrame):
    """Represents an individual row with asynchronous thumbnail loading."""
    def __init__(self, master, index, title, url, thumbnail_url, default_format, app_instance):
        super().__init__(master, fg_color=BG_CARD, corner_radius=8)
        self.url = url
        self.title = title
        self.thumbnail_url = thumbnail_url
        self.saved_path = None
        self.app_instance = app_instance

        # Give weight to COLUMN 2 (the title column) so it stretches left-to-right
        self.grid_columnconfigure(2, weight=1)

        # Checkbox (col 0)
        self.var = ctk.BooleanVar(value=True)
        self.checkbox = ctk.CTkCheckBox(self, text=f"{index}.", variable=self.var, width=40, font=ctk.CTkFont(size=12))
        self.checkbox.grid(row=0, column=0, padx=(10, 0), pady=10, sticky="w")

        # Thumbnail Button (col 1)
        fallback = Image.new("RGB", (60, 36), color=(45, 45, 50))
        self.fallback_img = ctk.CTkImage(light_image=fallback, dark_image=fallback, size=(60, 36))
        
        self.thumb_btn = ctk.CTkButton(
            self, image=self.fallback_img, text="", width=60, height=36,
            fg_color="transparent", hover_color=("#E0E0E0", "#2A2A2E"),
            command=self.play_preview
        )
        self.thumb_btn.grid(row=0, column=1, padx=6, pady=6)

        # Title Label (col 2)
        self.title_lbl = ctk.CTkLabel(self, text=title[:40] + "..." if len(title) > 40 else title, anchor="w", font=ctk.CTkFont(size=12))
        self.title_lbl.grid(row=0, column=2, padx=6, pady=10, sticky="ew")

        # Format Dropdown Menu (col 3)
        self.format_var = ctk.StringVar(value=default_format if default_format in FORMAT_LIST else "mp3 320k")
        self.format_var.trace_add("write", self.on_format_changed)
        
        self.format_menu = ctk.CTkOptionMenu(
            self, variable=self.format_var, width=135, height=28,
            values=FORMAT_LIST
        )
        self.format_menu.grid(row=0, column=3, padx=6, pady=10)

        # Status Label (col 4)
        self.status_label = ctk.CTkLabel(self, text="Ready", text_color=TEXT_MUTED, width=70, anchor="e")
        self.status_label.grid(row=0, column=4, padx=6, pady=10)

        # Circular Red Download Button (col 5)
       # --- High Quality Circular Red Download Button (col 5) ---
        self.circular_dl_icon = create_circular_red_download_icon((24, 24))

        self.download_btn = ctk.CTkButton(
             self, text="", image=self.circular_dl_icon, width=32, height=28,
             fg_color="transparent", hover_color=("#EAEAEA", "#2A2A2E"),
             command=self.trigger_single_download
        )
        self.download_btn.grid(row=0, column=5, padx=6, pady=10)

        # Folder Button (col 6)
        self.folder_btn = ctk.CTkButton(
            self, text="📁", width=32, height=28, fg_color=("#D1E7DD", "#1F4E3D"),
            text_color=TEXT_PRIMARY, command=self.open_folder
        )
        self.folder_btn.grid(row=0, column=6, padx=(2, 10), pady=10)
        self.folder_btn.grid_remove()

        threading.Thread(target=self._load_thumbnail_async, daemon=True).start()

        # ==========================================
        # 2. Live Speed & Progress Elements (Row 1 & 2)
        # ==========================================
        # Row 1 Live Speed / ETA Text Label (Distinct from status_label!)
        self.speed_label = ctk.CTkLabel(self, text="", font=ctk.CTkFont(size=11), text_color="gray")
        self.speed_label.grid(row=1, column=1, sticky="w", padx=10, pady=(0, 2))
        self.speed_label.grid_remove()  # Hidden by default

        # Row 2 Individual Live Progress Bar
        self.progress_bar = ctk.CTkProgressBar(self, height=5)
        self.progress_bar.grid(row=2, column=1, columnspan=4, sticky="ew", padx=10, pady=(0, 5))
        self.progress_bar.set(0)
        self.progress_bar.grid_remove()  # Hidden by default


    def set_downloading_state(self):
        """Switches the action button to a Pause state."""
        self.is_paused = False
        self.is_cancelled = False
        
        # Safely configure the single download button into a Pause button (Yellow)
        if hasattr(self, "download_btn") and self.download_btn:
            self.download_btn.configure(
                text="⏸", 
                image="",  # Clear the red icon image so text shows cleanly
                fg_color="#EAB308", 
                hover_color="#CA8A04", 
                command=self.toggle_pause_resume
            )
            self.download_btn.grid(row=0, column=5, padx=6, pady=10)

    def toggle_pause_resume(self):
        """Toggles between Pause and Resume states."""
        if not self.is_paused:
            self.is_paused = True
            self.download_btn.configure(text="▶", fg_color="#2FA572", hover_color="#238257")
            if hasattr(self, "status_label"):
                self.status_label.configure(text="Paused")
        else:
            self.is_paused = False
            self.download_btn.configure(text="⏸", fg_color="#EAB308", hover_color="#CA8A04")

    def cancel_download(self):
        """Flags the download as cancelled so yt-dlp aborts and resets the row."""
        self.is_cancelled = True
        self.is_paused = False
        
        # Call your reset helper to clean up UI elements instantly
        self.reset_to_ready_state()
        print(f"[Download Cancelled for {self.url}]")

    def reset_to_ready_state(self):
        """Resets the row back to the default ready state."""
        self.is_paused = False
        self.is_cancelled = False
        self.saved_path = None

        # 1. Reset main status label back to "Ready" and keep it visible
        if hasattr(self, "status_label") and self.status_label:
            self.status_label.configure(text="Ready", text_color=TEXT_MUTED)
            self.status_label.grid(row=0, column=4, padx=6, pady=10)

        # 2. Hide live speed/progress bar elements on row 1
        if hasattr(self, "speed_label") and self.speed_label:
            self.speed_label.grid_remove()
        if hasattr(self, "progress_bar"):
            self.progress_bar.set(0)
            self.progress_bar.grid_remove()
            
        # 3. Hide the folder button completely
        if hasattr(self, "folder_btn") and self.folder_btn:
            self.folder_btn.grid_remove()
            
        # 4. Restore the single circular red download button in column 5
        if hasattr(self, "download_btn") and self.download_btn:
            self.download_btn.configure(
                text="", 
                image=self.circular_dl_icon,
                fg_color="transparent", 
                hover_color=("#EAEAEA", "#2A2A2E"), 
                command=self.trigger_single_download
            )
            self.download_btn.grid(row=0, column=5, padx=6, pady=10)
    
    def _load_thumbnail_async(self):
        try:
            if self.thumbnail_url:
                import urllib.request
                req = urllib.request.Request(self.thumbnail_url, headers={'User-Agent': 'Mozilla/5.0'})
                with urllib.request.urlopen(req, timeout=3) as resp:
                    img_data = resp.read()
                pil_img = Image.open(io.BytesIO(img_data)).resize((60, 36))
                ctk_img = ctk.CTkImage(light_image=pil_img, dark_image=pil_img, size=(60, 36))
                self.after(0, lambda: self.thumb_btn.configure(image=ctk_img))
        except Exception:
            pass

    def play_preview(self):
        if hasattr(self.app_instance, "open_player"):
            self.app_instance.open_player(self.url, self.title)

    def trigger_single_download(self):
        """Triggers the download for this specific row asynchronously in a background thread."""
        if hasattr(self, "app_instance") and self.app_instance:
            # Run the download job in a daemon thread to prevent freezing the GUI
            threading.Thread(
                target=self.app_instance.run_download_job, 
                args=([self],), 
                daemon=True
            ).start()

    def on_format_changed(self, *args):
        """Called when the user selects a new format from the dropdown."""
        _ = args  # Satisfies linter
        
        # 1. Reset progress bars, status text, and flags
        self.reset_to_ready_state()
        
        # 2. Explicitly hide the folder button and bring back the red download button
        if hasattr(self, "folder_btn") and self.folder_btn:
            self.folder_btn.grid_remove()
            
        if hasattr(self, "download_btn") and self.download_btn:
            self.download_btn.configure(
                text="", 
                image=self.circular_dl_icon,
                fg_color="transparent", 
                hover_color=("#EAEAEA", "#2A2A2E"), 
                command=self.trigger_single_download
            )
            self.download_btn.grid(row=0, column=5, padx=6, pady=10)
            
        self.saved_path = None
               

    def set_status(self, text, color=None):
        self.status_label.configure(text=text)
        if color:
            self.status_label.configure(text_color=color)

    def enable_completion(self, filepath):
        """Swaps the download/pause button to the Folder button upon completion."""
        self.saved_path = filepath
        if hasattr(self, "download_btn") and self.download_btn:
            self.download_btn.grid_remove()
        if hasattr(self, "folder_btn") and self.folder_btn:
            self.folder_btn.grid(row=0, column=6, padx=(2, 10), pady=10)  # Put folder button in column 5 where download button was!

    def open_folder(self):
        if self.saved_path and os.path.exists(self.saved_path):
            subprocess.run(["explorer", "/select,", os.path.normpath(self.saved_path)])
        elif self.saved_path:
            os.startfile(os.path.dirname(os.path.normpath(self.saved_path)))


SETTINGS_FILE = "settings.json"

class SettingsWindow(ctk.CTkToplevel):
    """Spacious Settings Window featuring Search Timeout, Theme Switcher, and Editable Download Directory."""
    def __init__(self, parent, update_timeout_callback=None, update_dir_callback=None, update_theme_callback=None, current_dir=""):
        super().__init__(parent)
        self.title("YTDownloads - Settings")
        self.geometry("700x600")
        self.minsize(600, 500)
        self.update_timeout_callback = update_timeout_callback
        self.update_dir_callback = update_dir_callback
        self.update_theme_callback = update_theme_callback
        self.current_dir = current_dir

        # Apply custom high-quality logo icon to popup window title bar
        try:
            icon_path = get_resource_path("app_icon.ico")
            if os.path.exists(icon_path):
                self.iconbitmap(icon_path)
        except Exception as e:
            print(f"Popup icon load warning: {e}")

        self.transient(parent)
        self.grab_set()

        # Load settings dictionary
        self.settings = self.load_settings()

        # Main Layout Container
        self.main_container = ctk.CTkScrollableFrame(self, fg_color="transparent")
        self.main_container.pack(fill="both", expand=True, padx=20, pady=(20, 0))

        title_label = ctk.CTkLabel(
            self.main_container, 
            text="Application Settings", 
            font=ctk.CTkFont(size=22, weight="bold")
        )
        title_label.pack(anchor="w", pady=(0, 20))

        # ==========================================
        # 1. SETTING CATEGORY: Search Timeout
        # ==========================================
        ctk.CTkLabel(self.main_container, text="Search & Fetch Timeout", font=ctk.CTkFont(size=16, weight="bold")).pack(anchor="w", pady=(10, 5))
        search_frame = ctk.CTkFrame(self.main_container, fg_color=("gray90", "gray16"))
        search_frame.pack(fill="x", pady=5, ipady=10, ipadx=10)

        ctk.CTkLabel(search_frame, text="Change search time (Seconds):", font=ctk.CTkFont(size=13)).pack(anchor="w", padx=15, pady=(10, 5))

        control_subframe = ctk.CTkFrame(search_frame, fg_color="transparent")
        control_subframe.pack(fill="x", padx=15, pady=5)

        current_timeout = self.settings.get("search_timeout", 60)

        self.slider = ctk.CTkSlider(control_subframe, from_=10, to=300, number_of_steps=290, command=self.on_slider_change)
        self.slider.set(current_timeout)
        self.slider.pack(side="left", fill="x", expand=True, padx=(0, 15))

        self.entry_var = ctk.StringVar(value=str(current_timeout))
        self.entry_box = ctk.CTkEntry(control_subframe, textvariable=self.entry_var, width=70, justify="center")
        self.entry_box.pack(side="left", padx=(0, 10))
        self.entry_box.bind("<Return>", self.on_entry_change)
        self.entry_box.bind("<FocusOut>", self.on_entry_change)

        ctk.CTkButton(control_subframe, text="Default", width=90, fg_color="gray50", hover_color="gray40", command=self.reset_to_default).pack(side="left", padx=5)

        # ==========================================
        # 2. SETTING CATEGORY: Appearance Theme (Switch Toggle)
        # ==========================================
        ctk.CTkLabel(self.main_container, text="Appearance Theme", font=ctk.CTkFont(size=16, weight="bold")).pack(anchor="w", pady=(20, 5))
        theme_frame = ctk.CTkFrame(self.main_container, fg_color=("gray90", "gray16"))
        theme_frame.pack(fill="x", pady=5, ipady=10, ipadx=10)

        theme_subframe = ctk.CTkFrame(theme_frame, fg_color="transparent")
        theme_subframe.pack(fill="x", padx=15, pady=5)

        ctk.CTkLabel(theme_subframe, text="Dark Mode", font=ctk.CTkFont(size=13)).pack(side="left", anchor="w")

        # Determine initial switch state based on saved settings
        current_mode = self.settings.get("theme", "Dark")
        switch_var = ctk.StringVar(value=current_mode)

        self.theme_switch = ctk.CTkSwitch(
            theme_subframe, 
            text="", 
            variable=switch_var,
            onvalue="Dark",
            offvalue="Light",
            command=self.on_theme_switch_toggle
        )
        self.theme_switch.pack(side="right", padx=5)
        self.store_switch_var = switch_var  # keep reference so we can read it on save

        # ==========================================
        # 3. SETTING CATEGORY: Download Directory (Editable)
        # ==========================================
        ctk.CTkLabel(self.main_container, text="Downloads", font=ctk.CTkFont(size=16, weight="bold")).pack(anchor="w", pady=(20, 5))
        dir_frame = ctk.CTkFrame(self.main_container, fg_color=("gray90", "gray16"))
        dir_frame.pack(fill="x", pady=5, ipady=10, ipadx=10)

        ctk.CTkLabel(dir_frame, text="Location", font=ctk.CTkFont(size=13, weight="bold")).pack(anchor="w", padx=15, pady=(5, 2))

        # Subframe to hold the entry box and browse button side-by-side
        input_subframe = ctk.CTkFrame(dir_frame, fg_color="transparent")
        input_subframe.pack(fill="x", padx=15, pady=5)

        saved_dir = self.settings.get("download_dir", self.current_dir or os.getcwd())
        self.dir_var = ctk.StringVar(value=saved_dir)

        # Shorter editable entry field that expands gracefully
        self.dir_entry = ctk.CTkEntry(input_subframe, textvariable=self.dir_var, font=ctk.CTkFont(size=12), height=32)
        self.dir_entry.pack(side="left", fill="x", expand=True, padx=(0, 10))
        self.dir_entry.bind("<KeyRelease>", self.on_dir_entry_change)

        # Dedicated Browse button with fixed width so text is never cut off
        ctk.CTkButton(input_subframe, text="Browse", width=100, height=32, command=self.browse_directory).pack(side="left")

        # Bottom Action Bar (Fixed outside the scrollable area so it never hides)
        action_bar = ctk.CTkFrame(self, fg_color="transparent")
        action_bar.pack(fill="x", padx=20, pady=15)

        ctk.CTkButton(
            action_bar, 
            text="Save & Close", 
            command=self.save_and_close, 
            width=120, 
            height=35
        ).pack(side="right")


    def on_theme_switch_toggle(self):
        """Saves the theme selection live as the switch is toggled."""
        selected_theme = self.store_switch_var.get()
        self.settings["theme"] = selected_theme
        self.save_settings()

    def load_settings(self):
        if os.path.exists(SETTINGS_FILE):
            try:
                with open(SETTINGS_FILE, "r") as f:
                    return json.load(f)
            except Exception:
                pass
        return {"search_timeout": 60, "download_dir": "", "theme": "Dark"}

    def save_settings(self):
        try:
            with open(SETTINGS_FILE, "w") as f:
                json.dump(self.settings, f, indent=4)
        except Exception as e:
            print(f"Error saving settings: {e}")

    def on_slider_change(self, value):
        int_val = int(float(value))
        self.entry_var.set(str(int_val))
        self.settings["search_timeout"] = int_val
        self.save_settings()
        if self.update_timeout_callback:
            self.update_timeout_callback(int_val)

    def on_entry_change(self, event=None):
        try:
            val = int(self.entry_var.get())
            val = max(10, min(305, val))
            self.slider.set(val)
            self.settings["search_timeout"] = val
            self.save_settings()
            if self.update_timeout_callback:
                self.update_timeout_callback(val)
        except ValueError:
            self.entry_var.set(str(int(self.slider.get())))

    def reset_to_default(self):
        self.slider.set(60)
        self.entry_var.set("60")
        self.settings["search_timeout"] = 60
        self.save_settings()
        if self.update_timeout_callback:
            self.update_timeout_callback(60)

    def on_theme_change(self, selected_theme):
        self.settings["theme"] = selected_theme
        self.save_settings()

    def on_dir_entry_change(self, event=None):
        """Saves path live as the user types or pastes into the entry box."""
        typed_dir = self.dir_var.get()
        self.settings["download_dir"] = typed_dir
        self.save_settings()
        if self.update_dir_callback:
            self.update_dir_callback(typed_dir)

    def browse_directory(self):
        chosen_dir = filedialog.askdirectory(initialdir=self.dir_var.get())
        if chosen_dir:
            self.dir_var.set(chosen_dir)
            self.settings["download_dir"] = chosen_dir
            self.save_settings()
            if self.update_dir_callback:
                self.update_dir_callback(chosen_dir)

    def save_and_close(self):
        """Applies theme and timeout changes globally and closes window."""
        selected_theme = self.settings.get("theme", "Dark")
        ctk.set_appearance_mode(selected_theme)
        
        if self.update_theme_callback:
            self.update_theme_callback(selected_theme)
            
        if self.update_dir_callback:
            self.update_dir_callback(self.dir_var.get())

        self.destroy()

class YTDownloadsApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.track_rows = []
        self.all_entries = []
        self.page_size = 10

        # Load saved settings (timeout, download_dir, theme) on startup
        self.load_initial_settings()

        # Automatically finds your user folder and sets it to the standard Downloads directory
        self.download_dir = os.path.join(os.path.expanduser("~"), "Downloads")

        self.title("")
        self.geometry("800x600")
        
        # Safely load the window icon for both python runs and compiled .exe files
        try:
            icon_path = get_resource_path("app_icon.ico")
            if os.path.exists(icon_path):
                self.iconbitmap(icon_path)
        except Exception as e:
            print(f"Icon load warning: {e}")
            
        self.state("zoomed")

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(3, weight=1)

        # 1. Load the image icon FIRST using get_resource_path so it exists for the header in compiled .exe
        logo_path = get_resource_path("logo.png")
        self.download_button_icon = CTkImage(
            light_image=Image.open(logo_path),
            dark_image=Image.open(logo_path),
            size=(20, 20)
        )  

        # 2. THEN build the header
        self._build_header()
               
        # 3. Build your input card / search bar (Row 1)
        self._build_input_card()
        
        # 4. Build your progress bar in Row 2
        self.progressbar = ctk.CTkProgressBar(self, mode="indeterminate", height=10)
        self.progressbar.grid(row=2, column=0, pady=10, padx=20, sticky="ew")
        self.progressbar.set(0)
        self.progressbar.grid_remove() # Keep it hidden until any action starts
        
        # 5. Build your queue card / download list (Row 3)
        self._build_queue_card()
                
        # 6. Build footer if you have one
        self._build_footer()
         
    def load_initial_settings(self):
        """Loads saved settings (timeout, directory, theme) from settings.json on startup."""
        import json
        import os
        
        # Default fallbacks
        self.current_timeout_ms = 60000
        self.download_dir = os.path.join(os.path.expanduser("~"), "Downloads")
        
        if os.path.exists("settings.json"):
            try:
                with open("settings.json", "r") as f:
                    data = json.load(f)
                    
                    # 1. Load Timeout
                    timeout_sec = data.get("search_timeout", 60)
                    self.current_timeout_ms = timeout_sec * 1000
                    
                    # 2. Load Download Directory
                    saved_dir = data.get("download_dir", "")
                    if saved_dir and os.path.exists(saved_dir):
                        self.download_dir = saved_dir
                        
                    # 3. Load & Apply Theme
                    saved_theme = data.get("theme", "Dark")
                    ctk.set_appearance_mode(saved_theme)
                    
            except Exception as e:
                print(f"Error loading settings.json: {e}")


    def update_theme_setting(self, new_theme):
        """Called when settings are saved to apply the appearance theme globally."""
        ctk.set_appearance_mode(new_theme)
        print(f"[Settings Updated] Theme set to: {new_theme}")
   

    def delete_selected_items(self):

        # 1. Check if any items are actually selected (checkbox.get() is True)
        selected_rows = [row for row in self.track_rows if row.var.get()]
        
        if not selected_rows:
            import tkinter.messagebox as messagebox
            messagebox.showwarning("No Selection", "Select item(s) to be deleted")
            return
        
        # Filter out rows where the checkbox is checked
        remaining_entries = []
        for row in self.track_rows:
            if not row.var.get():
                matching = next((e for e in self.all_entries if e["url"] == row.url), None)
                if matching:
                    remaining_entries.append(matching)
        
        self.all_entries = remaining_entries
        self.render_page(0)

    def _build_header(self):
        header = ctk.CTkFrame(self, fg_color=BG_CARD, height=65, corner_radius=0)
        header.grid(row=0, column=0, sticky="ew", padx=0, pady=0)
        header.grid_propagate(False)
        header.grid_columnconfigure(0, weight=1)
        header.grid_columnconfigure(1, weight=1)
        header.grid_columnconfigure(2, weight=1)

        # Left: Tiny logo icon & Text
        left_frame = ctk.CTkFrame(header, fg_color="transparent")
        left_frame.grid(row=0, column=0, padx=16, pady=14, sticky="w")

        left_icon_label = ctk.CTkLabel(left_frame, image=self.download_button_icon, text="")
        left_icon_label.pack(side="left", padx=(0, 6))

        left_title_label = ctk.CTkLabel(
            left_frame, 
            text="YTDownloads -v1.1", 
            font=ctk.CTkFont(size=16, weight="bold")
        )
        left_title_label.pack(side="left")

        # Center: Support YTDownloads Deep Red Pill Button
        center_frame = ctk.CTkFrame(header, fg_color="transparent")
        center_frame.grid(row=0, column=1, pady=14)
        
        paypal_btn = ctk.CTkButton(
            center_frame, text="Support YTDownloads", width=160, height=34,
            fg_color="#8B0000", hover_color="#5C0000", text_color="#FFFFFF",
            corner_radius=17, font=ctk.CTkFont(size=12, weight="bold"),
            command=lambda: os.system("start https://www.paypal.com/paypalme/walkstreets")
        )
        paypal_btn.pack()

        # Right: Settings Control
        controls = ctk.CTkFrame(header, fg_color="transparent")
        controls.grid(row=0, column=2, padx=16, pady=12, sticky="e")

        # Compact Settings Icon Button (Gear / Tool symbol)
        self.btn_settings = ctk.CTkButton(
            controls, 
            text="⚙", 
            width=32,
            height=32,
            command=self.open_settings_window
        )
        self.btn_settings.pack(side="right", padx=6)


    def _build_input_card(self):
        card = ctk.CTkFrame(self, fg_color=BG_CARD, corner_radius=10)
        card.grid(row=1, column=0, padx=16, pady=(12, 6), sticky="ew")
        card.grid_columnconfigure(0, weight=1)

        # 1. Define 'row' FIRST so widgets can reference it
        row = ctk.CTkFrame(card, fg_color="transparent")
        row.grid(row=0, column=0, padx=16, pady=16, sticky="ew")
        row.grid_columnconfigure(0, weight=1)

        # 2. Add widgets inside 'row'
        self.url_entry = ctk.CTkEntry(row, placeholder_text="Paste YouTube video, music, or playlist URL here...", height=40)
        self.url_entry.grid(row=0, column=0, padx=(0, 10), sticky="ew")

        self.master_format_var = ctk.StringVar(value="mp3 320k")
        self.format_menu = ctk.CTkOptionMenu(
            row, variable=self.master_format_var, width=175, height=40,
            values=FORMAT_LIST
        )
        self.format_menu.grid(row=0, column=1, padx=6)

        ctk.CTkButton(row, text="Paste", width=75, height=40, command=self.paste_clipboard).grid(row=0, column=2, padx=6)
        
        # 3. Add your state-managed Fetch button matching the 40px height
        self.fetch_btn = ctk.CTkButton(
            row, 
            text="Fetch Info", 
            height=40,           # Matches the 40px height of Paste and OptionMenu!
            fg_color=ACCENT_BLUE, 
            text_color="#000000", 
            font=ctk.CTkFont(weight="bold"), 
            command=self.on_fetch_btn_click
        )
        self.fetch_btn.grid(row=0, column=3, padx=(6, 0))


    def _build_progress_bar(self):
        self.prog_frame = ctk.CTkFrame(self, fg_color="transparent", height=15)
        self.prog_frame.grid(row=2, column=0, padx=16, sticky="ew")
        self.prog_frame.grid_columnconfigure(0, weight=1)

        self.progressbar = ctk.CTkProgressBar(self.prog_frame, height=8, mode="indeterminate")
        self.progressbar.grid(row=2, column=0, sticky="ew")
        self.progressbar.set(0)
        self.progressbar.grid_remove() # <--- Add this line right here!

    def _build_queue_card(self):
        self.queue_card = ctk.CTkFrame(self, fg_color=BG_CARD, corner_radius=10)
        self.queue_card.grid(row=3, column=0, padx=16, pady=(6, 6), sticky="nsew")
        self.queue_card.grid_columnconfigure(0, weight=1)
        self.queue_card.grid_rowconfigure(1, weight=1)

        q_head = ctk.CTkFrame(self.queue_card, fg_color="transparent")
        q_head.grid(row=0, column=0, padx=16, pady=10, sticky="ew")
        
        # Configure 3 columns: Left (Delete), Center (Title), Right (Action buttons)
        q_head.grid_columnconfigure(0, weight=0)
        q_head.grid_columnconfigure(1, weight=1)
        q_head.grid_columnconfigure(2, weight=0)

        # 1. Delete Selected Button on the left (directly above track checkboxes)
        self.delete_selected_btn = ctk.CTkButton(
            q_head, text="Delete Selected", width=110, height=28, 
            fg_color="#DC2626", hover_color="#B91C1C", 
            command=self.delete_selected_items
        )
        self.delete_selected_btn.grid(row=0, column=0, sticky="w")

        # 2. Queue Title / Counter Label Centered
        self.queue_title_lbl = ctk.CTkLabel(
            q_head, text="Queue (0 items)", 
            font=ctk.CTkFont(size=15, weight="bold"),
            anchor="center"
        )
        self.queue_title_lbl.grid(row=0, column=1, sticky="ew", padx=10)

        # 3. Action Buttons on the right
        btn_bar = ctk.CTkFrame(q_head, fg_color="transparent")
        btn_bar.grid(row=0, column=2, sticky="e")

        ctk.CTkButton(btn_bar, text="Clear All", width=80, height=28, fg_color="#D9534F", command=self.start_clear_all).pack(side="left", padx=4)
        ctk.CTkButton(btn_bar, text="Select All", width=85, height=28, command=lambda: self.toggle_all(True)).pack(side="left", padx=4)
        ctk.CTkButton(btn_bar, text="Deselect All", width=95, height=28, fg_color="gray50", command=lambda: self.toggle_all(False)).pack(side="left", padx=4)
        ctk.CTkButton(btn_bar, text="Download Selected", width=140, height=28, fg_color="#2FA572", command=self.start_download_selected).pack(side="left", padx=(10, 0))

        self.scroll_frame = ctk.CTkScrollableFrame(self.queue_card, fg_color="transparent")
        self.scroll_frame.grid(row=1, column=0, padx=12, pady=(0, 6), sticky="nsew")
        self.scroll_frame.grid_columnconfigure(0, weight=1)

        self.empty_lbl = ctk.CTkLabel(self.scroll_frame, text="No downloads queued. Paste a URL and click 'Fetch Info'.", text_color=TEXT_MUTED)
        self.empty_lbl.grid(row=0, column=0, pady=50)

        # Pagination Controls Bar
        self.page_bar = ctk.CTkFrame(self.queue_card, fg_color="transparent", height=40)
        self.page_bar.grid(row=2, column=0, padx=16, pady=(0, 10), sticky="ew")
        self.page_bar.grid_columnconfigure(1, weight=1)

        self.prev_btn = ctk.CTkButton(self.page_bar, text="◀ Previous", width=100, height=28, command=self.prev_page, state="disabled")
        self.prev_btn.grid(row=0, column=0, sticky="w")

        self.page_lbl = ctk.CTkLabel(self.page_bar, text="Page 0 of 0", font=ctk.CTkFont(size=12, weight="bold"))
        self.page_lbl.grid(row=0, column=1, sticky="n")

        self.next_btn = ctk.CTkButton(self.page_bar, text="Next ▶", width=100, height=28, command=self.next_page, state="disabled")
        self.next_btn.grid(row=0, column=2, sticky="e")

    def _build_footer(self):
        footer = ctk.CTkFrame(self, fg_color=BG_CARD, height=35, corner_radius=0)
        footer.grid(row=4, column=0, sticky="ew")
        footer.grid_columnconfigure(0, weight=1)

        issue_lbl = ctk.CTkLabel(footer, text="Report an Issue", text_color=ACCENT_BLUE, font=ctk.CTkFont(size=12, underline=True))
        issue_lbl.grid(row=0, column=0, pady=8)
        issue_lbl.bind("<Button-1>", lambda e: self.open_issue_dialog())
           
    def open_settings_window(self):
        """Opens the spacious settings modal."""
        SettingsWindow(
            self, 
            update_timeout_callback=self.update_search_timeout_setting,
            update_dir_callback=self.update_download_dir_setting,
            update_theme_callback=self.update_theme_setting,  # <-- Make sure this is passed!
            current_dir=getattr(self, "download_directory", os.getcwd())
        )
    
    def update_search_timeout_setting(self, new_timeout_seconds):
            """Called live whenever the search time slider/entry is modified."""
            # Convert seconds to milliseconds for your self.after() timer call
            self.current_timeout_ms = new_timeout_seconds * 1000
            print(f"[Settings Updated] Search timeout set to {new_timeout_seconds} seconds ({self.current_timeout_ms} ms)")

    def update_download_dir_setting(self, new_dir):
        """Called live whenever a new download folder is selected in settings."""
        self.download_dir = new_dir
        self.download_path = new_dir
        print(f"[Settings Updated] Download directory set to: {new_dir}")

    def choose_directory(self):
        folder_selected = ctk.filedialog.askdirectory()
        if folder_selected:
            self.download_dir = folder_selected  # Update both or stick to download_dir consistently
            self.download_path = folder_selected
            print(f"Download folder set to: {self.download_dir}")

    def paste_clipboard(self):
        try:
            self.url_entry.delete(0, "end")
            self.url_entry.insert(0, self.clipboard_get().strip())
        except Exception:
            pass

    def toggle_all(self, state):
        for r in self.track_rows:
            r.var.set(state)

    def start_clear_all(self):
        self.progressbar.grid(row=2, column=0, sticky="ew")
        self.progressbar.start()
        
        self.url_entry.delete(0, "end")
        for r in self.track_rows:
            r.grid_forget()
        
        def clear_job():
            for r in self.track_rows:
                r.destroy()
            self.track_rows.clear()
            self.all_entries.clear()
            self.current_page = 0
            self.after(0, self._finish_clear)

        threading.Thread(target=clear_job, daemon=True).start()


    def _finish_clear(self):
        self.progressbar.stop()
        self.progressbar.grid_forget()
        self.empty_lbl.grid(row=2, column=0, pady=50)
        self.queue_title_lbl.configure(text="Queue (0 items)")
        self.page_lbl.configure(text="Page 0 of 0")
        self.prev_btn.configure(state="disabled")
        self.next_btn.configure(state="disabled")

    def open_player(self, url, title):
        top = ctk.CTkToplevel(self)
        top.title(f"Preview: {title}")
        top.geometry("720x450")
        top.minsize(600, 400)

        ctk.CTkLabel(top, text=title, font=ctk.CTkFont(size=14, weight="bold")).pack(padx=16, pady=10)
        vid_frame = ctk.CTkFrame(top, fg_color="#000000")
        vid_frame.pack(fill="both", expand=True, padx=16, pady=(0, 16))

        try:
            ydl_opts = {"format": "best[height<=720]/best", "quiet": True}
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)
                stream_url = info.get("url")

            if stream_url:
                import tkinterweb
                browser = tkinterweb.HtmlFrame(vid_frame)
                browser.load_website(url)
                browser.pack(fill="both", expand=True)
            else:
                raise Exception()
        except Exception:
            ctk.CTkLabel(vid_frame, text="Preview stream unavailable directly.\nClick below to open in browser.", text_color="#FFFFFF").pack(expand=True)
            ctk.CTkButton(vid_frame, text="Open on YouTube", command=lambda: os.system(f"start {url}")).pack(pady=10)

    def on_fetch_btn_click(self):
        current_text = self.fetch_btn.cget("text")
        
        if current_text == "Fetch Info":
            self.start_fetch()
        elif current_text == "Cancel search":
            self.cancel_search_action(manual=True)
        elif current_text == "Clear search":
            self.clear_search_and_reset()

    def start_fetch(self):
        url = self.url_entry.get().strip()
        if not url:
            messagebox.showwarning("Missing URL", "Please enter a valid URL.")
            return

        # 1. Change button to "Cancel search" in Red
        self.fetch_btn.configure(text="Cancel search", fg_color="#DC2626", hover_color="#B91C1C")
        
        # 2. Show and start progress bar on Row 2
        self.progressbar.grid(row=2, column=0, padx=20, pady=(10, 5), sticky="ew")
        self.progressbar.start()
        
        # 3. Set state flags
        self.fetch_in_progress = True
        self.user_cancelled = False

        def fetch_job():
            try:
                playlist_title, entries = downloader.fetch_url_info(url)
                
                if self.fetch_in_progress and not self.user_cancelled:
                    self.fetch_in_progress = False
                    self.all_entries = entries
                    self.current_page = 0
                    self.after(0, lambda: self._finish_fetch_success(entries))
            except Exception as e:
                if self.fetch_in_progress and not self.user_cancelled:
                    self.fetch_in_progress = False
                    self.after(0, lambda: self._finish_fetch_error(str(e)))

        threading.Thread(target=fetch_job, daemon=True).start()

        # 4. Set 30-second timeout watchdog (30,000 ms)
        self.fetch_timer_id = self.after(120000, self._check_fetch_timeout)

    def cancel_search_action(self, manual=True):
        # Explicitly mark as user cancelled so the timeout watchdog ignores it
        self.user_cancelled = True
        self.fetch_in_progress = False
        
        # Cancel the 30-second timer safely
        if hasattr(self, "fetch_timer_id"):
            try:
                self.after_cancel(self.fetch_timer_id)
            except Exception:
                pass

        # Stop progress bar and hide it
        self.progressbar.stop()
        self.progressbar.grid_remove()

        # Change button to "Clear search" in Amber, keeping the URL in the box
        self.fetch_btn.configure(text="Clear search", fg_color="#D97706", hover_color="#B45309")

    def _check_fetch_timeout(self):
        # Only trigger timeout if fetch is still running and user did NOT manually cancel
        if getattr(self, "fetch_in_progress", False) and not getattr(self, "user_cancelled", False):
            self.fetch_in_progress = False
            
            # Stop progress bar and hide it
            self.progressbar.stop()
            self.progressbar.grid_remove()
            
            # Show popup warning with OK button
            messagebox.showwarning(
                "Download Restricted", 
                "URL does not allow downloads. Please try different URL."
            )
            
            # URL remains in search box, change button to "Clear search" in Amber
            self.fetch_btn.configure(text="Clear search", fg_color="#D97706", hover_color="#B45309")

    def clear_search_and_reset(self):
        # 1. Clear the search box
        self.url_entry.delete(0, "end")
        
        # 2. Reset button back to original "Fetch Info" and original accent color
        self.fetch_btn.configure(
            text="Fetch Info", 
            fg_color=ACCENT_BLUE, 
            hover_color=ctk.ThemeManager.theme["CTkButton"]["hover_color"] # or your default hover color constant
        )

    def _finish_fetch_success(self, entries):
        if hasattr(self, "fetch_timer_id"):
            self.after_cancel(self.fetch_timer_id)
            
        self.progressbar.stop()
        self.progressbar.grid_remove()
        
        # When successfully fetched, turn button into "Clear search" in Amber
        self.fetch_btn.configure(text="Clear search", fg_color="#D97706", hover_color="#B45309")
        
        self.render_page(0)

    def clear_search_and_reset(self):
        # 1. Clear the URL entry box
        self.url_entry.delete(0, "end")
        
        # 2. Clear out the entries list and re-render to wipe items from screen
        self.all_entries = []
        self.current_page = 0
        if hasattr(self, "render_page"):
            self.render_page(0)
            
        # 3. Reset button back to original "Fetch Info" and original ACCENT_BLUE color
        self.fetch_btn.configure(
            text="Fetch Info", 
            fg_color=ACCENT_BLUE, 
            hover_color=ctk.ThemeManager.theme["CTkButton"]["hover_color"]
        )

    def _finish_fetch_error(self, err_msg=None):
        if hasattr(self, "fetch_timer_id"):
            self.after_cancel(self.fetch_timer_id)
            
        self.progressbar.stop()
        self.progressbar.grid_remove()
        
        # Turn into "Clear search" in Amber on error
        self.fetch_btn.configure(text="Clear search", fg_color="#D97706", hover_color="#B45309")
        
        if err_msg:
            messagebox.showerror("Fetch Error", err_msg)

    def clear_search_and_reset(self):
        self.url_entry.delete(0, "end")
        
        # Reset back to "Fetch Info" with ACCENT_BLUE
        self.fetch_btn.configure(
            text="Fetch Info", 
            fg_color=ACCENT_BLUE, 
            hover_color=ctk.ThemeManager.theme["CTkButton"]["hover_color"]
        )

    def _hide_progress(self):
        self.progressbar.stop()
        self.progressbar.grid_forget()

    def render_page(self, page_num):
        # 1. Hide progress and clear old rows
        self._hide_progress()
        for r in self.track_rows:
            r.destroy()
        self.track_rows.clear()

        # 2. Calculate total items and handle empty state FIRST
        total_items = len(self.all_entries)
        if total_items == 0:
            self.empty_lbl.grid(row=0, column=0, pady=50)
            self.page_lbl.configure(text="Page 0 of 0")
            self.prev_btn.configure(state="disabled")
            self.next_btn.configure(state="disabled")
            self.queue_title_lbl.configure(text="Queue (0 items)")
            return

        # 3. Setup pagination boundaries
        self.empty_lbl.grid_forget()
        total_pages = (total_items + self.page_size - 1) // self.page_size
        self.current_page = max(0, min(page_num, total_pages - 1))

        start_idx = self.current_page * self.page_size
        end_idx = min(start_idx + self.page_size, total_items)
        page_items = self.all_entries[start_idx:end_idx]

        # 4. Render track rows using TrackRow with balanced margins (padx=16)
        default_fmt = self.master_format_var.get()
        for i, item in enumerate(page_items):
            absolute_idx = start_idx + i + 1
            thumb = item.get("thumbnail", "")
            
            # Create the custom TrackRow object
            row = TrackRow(self.scroll_frame, absolute_idx, item["title"], item["url"], thumb, default_fmt, self)
            
            # Use padx=16 (instead of 4) for balanced left/right margins
            row.grid(row=i, column=0, padx=16, pady=4, sticky="ew")
            self.track_rows.append(row)

        # 5. Update labels and pagination buttons
        self.queue_title_lbl.configure(text=f"Queue ({total_items} items found) — Showing {start_idx+1}-{end_idx}")
        self.page_lbl.configure(text=f"Page {self.current_page + 1} of {total_pages}")
        
        self.prev_btn.configure(state="normal" if self.current_page > 0 else "disabled")
        self.next_btn.configure(state="normal" if self.current_page < total_pages - 1 else "disabled")

    def prev_page(self):
        if self.current_page > 0:
            self.render_page(self.current_page - 1)

    def next_page(self):
        total_pages = (len(self.all_entries) + self.page_size - 1) // self.page_size
        if self.current_page < total_pages - 1:
            self.render_page(self.current_page + 1)

    def start_download_selected(self):
        selected = [r for r in self.track_rows if r.var.get()]
        if not selected:
            messagebox.showwarning("No Selection", "Please check at least one track in the current view to download.")
            return
        
        threading.Thread(target=self.run_download_job, args=(selected,), daemon=True).start()
        
    def run_download_job(self, rows_to_download):
        import concurrent.futures

        def download_single(row):
            # Initialize control flags on the row object
            row.is_cancelled = False
            row.is_paused = False

            # 1. Reveal progress UI & switch download button to Pause (Yellow) + status to Cancel
            self.after(0, row.status_label.grid)
            self.after(0, row.progress_bar.grid)
            self.after(0, row.set_downloading_state)  # This handles the Pause/Cancel button styling
            
            def hook(d):
                # Check for user cancellation inside the download hook
                if getattr(row, "is_cancelled", False):
                    raise Exception("Download cancelled by user.")
                    
                # Handle pausing: loop and sleep while paused
                while getattr(row, "is_paused", False):
                    if getattr(row, "is_cancelled", False):
                        raise Exception("Download cancelled by user.")
                    import time
                    time.sleep(0.5)

                if d["status"] == "downloading":
                    try:
                        downloaded = d.get('downloaded_bytes', 0)
                        total = d.get('total_bytes') or d.get('total_bytes_estimate', 1)
                        pct = downloaded / total
                        
                        # Clean out ANSI terminal color escape codes (e.g. [0;32m) from strings
                        import re
                        raw_speed = d.get('_speed_str', 'N/A')
                        speed = re.sub(r'\x1b\[[0-9;]*m', '', raw_speed)
                        
                        raw_eta = d.get('_eta_str', 'N/A')
                        eta = re.sub(r'\x1b\[[0-9;]*m', '', raw_eta)
                        
                        pct_text = f"{pct * 100:.1f}%"

                        # Safely update progress bar and status text on main thread
                        self.after(0, lambda: row.progress_bar.set(pct))
                        self.after(0, lambda: row.speed_label.configure(text=f"{pct_text} at {speed} — ETA: {eta}"))
                    except Exception as ex:
                        print(f"Hook progress error: {ex}")

                elif d["status"] == "finished":
                    self.after(0, lambda: row.progress_bar.set(1.0))
                    self.after(0, row.set_status, "Converting...", "#E69500")

            # Uses self.download_dir which is updated via your settings
            opts = downloader.get_ydl_options(row.format_var.get(), self.download_dir, hook)

            try:
                if getattr(row, "is_cancelled", False):
                    return

                with yt_dlp.YoutubeDL(opts) as ydl:
                    info = ydl.extract_info(row.url, download=True)
                    if not info or getattr(row, "is_cancelled", False):
                        raise Exception("Download failed or cancelled.")

                    filepath = None
                    if info.get("requested_downloads"):
                        filepath = info["requested_downloads"][0].get("filepath")
                    
                    if not filepath:
                        prep = ydl.prepare_filename(info)
                        ext = "mp3" if "mp3" in row.format_var.get() else ("flac" if "FLAC" in row.format_var.get() else ("wav" if "WAV" in row.format_var.get() else "mp4"))
                        filepath = os.path.splitext(prep)[0] + f".{ext}"

                self.after(0, lambda: row.progress_bar.set(1.0))
                self.after(0, row.set_status, "Completed ✓", "#2FA572")
                self.after(0, row.enable_completion, filepath)
            except Exception as e:
                if "cancelled" in str(e).lower():
                    self.after(0, lambda: row.set_status("Cancelled", "gray"))
                    print(f"[Download Cancelled for {row.url}]")
                else:
                    self.after(0, row.set_status, "Error ✗", "#D9534F")
                    print(f"DOWNLOAD ERROR: {e}")

        # Run concurrent downloads (2 items at a time)
        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
            executor.map(download_single, rows_to_download)

    def open_issue_dialog(self):
        """Pops up the 'Describe the issue' ticket creation window."""
        dialog = ctk.CTkToplevel(self)
        dialog.title("Describe the issue")
        dialog.geometry("450x480")
        dialog.resizable(False, False)
        dialog.grab_set()

        # --- Set the professional app icon ---
        try:
            dialog.iconbitmap(r"C:\YTDownloads\app_icon.ico")
        except Exception as e:
            print(f"Icon load error: {e}")

        ctk.CTkLabel(dialog, text="Report an Issue", font=ctk.CTkFont(size=16, weight="bold")).pack(padx=20, pady=(20, 10), anchor="w")

        ctk.CTkLabel(dialog, text="User Name:", font=ctk.CTkFont(size=12)).pack(padx=20, pady=(5, 0), anchor="w")
        name_entry = ctk.CTkEntry(dialog, width=410, height=32)
        name_entry.pack(padx=20, pady=(0, 10))

        ctk.CTkLabel(dialog, text="Email Address:", font=ctk.CTkFont(size=12)).pack(padx=20, pady=(5, 0), anchor="w")
        email_entry = ctk.CTkEntry(dialog, width=410, height=32)
        email_entry.pack(padx=20, pady=(0, 10))

        ctk.CTkLabel(dialog, text="Describe the issue:", font=ctk.CTkFont(size=12)).pack(padx=20, pady=(5, 0), anchor="w")
        desc_text = ctk.CTkTextbox(dialog, width=410, height=120)
        desc_text.pack(padx=20, pady=(0, 15))

        btn_row = ctk.CTkFrame(dialog, fg_color="transparent")
        btn_row.pack(padx=20, pady=(0, 20), fill="x")

        def on_submit():
            uname = name_entry.get().strip()
            uemail = email_entry.get().strip()
            udesc = desc_text.get("1.0", "end-1c").strip()

            if not uname or not uemail or not udesc:
                messagebox.showwarning("Missing Fields", "Please fill in all fields before submitting.", parent=dialog)
                return

            timestamp = int(time.time())
            ticket_no = f"INC{timestamp}"
            
            file_content = f"""Ticket number: {ticket_no}
User name : {uname}
Email address : {uemail}
Description of issue : {udesc}

Instructions: YTDownloads will not send any information to developer autom Kindly attach this file and send an email to waalkstreets@gmail.com
"""
            dialog.destroy()
            self.open_success_dialog(ticket_no, file_content)

        ctk.CTkButton(btn_row, text="Cancel", width=90, fg_color="gray50", command=dialog.destroy).pack(side="right", padx=5)
        ctk.CTkButton(btn_row, text="Submit", width=90, fg_color="#2FA572", command=on_submit).pack(side="right", padx=5)

    def open_success_dialog(self, ticket_no, file_content):
        """Confirmation window featuring the ticket number, instructions, and a Download button."""
        succ = ctk.CTkToplevel(self)
        succ.title("Thank you")
        succ.geometry("450x320")
        succ.resizable(False, False)
        succ.grab_set()

        # --- Set the professional app icon for the Thank you window ---
        try:
            succ.iconbitmap(r"C:\YTDownloads\app_icon.ico")
        except Exception as e:
            print(f"Icon load error: {e}")

        ctk.CTkLabel(succ, text="Thank you for reporting the issue", font=ctk.CTkFont(size=16, weight="bold")).pack(padx=20, pady=(20, 5))
        ctk.CTkLabel(succ, text=f"Ticket Number: {ticket_no}", font=ctk.CTkFont(size=13, weight="bold"), text_color=ACCENT_BLUE).pack(padx=20, pady=(0, 10))

        instructions = (
            "YTDownloads will not send any information to developer automatically.\n"
            "Kindly download the file and attach the file and send it to waalkstreets@gmail.com\n"
            )
        ctk.CTkLabel(succ, text=instructions, font=ctk.CTkFont(size=12), text_color=TEXT_MUTED, justify="center").pack(padx=20, pady=(0, 20))

        def download_ticket_file():
            default_filename = f"{ticket_no}.txt"
            save_path = filedialog.asksaveasfilename(
                parent=succ, defaultextension=".txt",
                initialfile=default_filename,
                filetypes=[("Text Files", "*.txt")]
            )
            if save_path:
                try:
                    with open(save_path, "w", encoding="utf-8") as f:
                        f.write(file_content)
                    
                    # --- SUCCESS POPUP FIX: Setting parent=succ forces the messagebox to inherit the icon ---
                    msg_box = messagebox.showinfo("Success", "Ticket file downloaded successfully!", parent=succ)
                    
                except Exception as ex:
                    messagebox.showerror("Error", f"Could not save file: {ex}", parent=succ)

        btn_frame = ctk.CTkFrame(succ, fg_color="transparent")
        btn_frame.pack(padx=20, pady=(0, 20))

        ctk.CTkButton(btn_frame, text="Download File", width=140, height=34, fg_color="#2FA572", command=download_ticket_file).pack(side="left", padx=8)
        ctk.CTkButton(btn_frame, text="Close", width=100, height=34, fg_color="gray50", command=succ.destroy).pack(side="left", padx=8)

if __name__ == "__main__":
    try:
        app = YTDownloadsApp()
        # Set custom icon for the window titlebar and taskbar
        try:
            app.iconbitmap(get_resource_path("app_icon.ico"))
        except Exception:
            pass
        app.mainloop()
    except Exception as e:
        import traceback
        import os
        # Write traceback to a crash log instead of using input()
        error_log = os.path.join(os.path.expanduser("~"), "YTDownloads_error.log")
        with open(error_log, "w") as f:
            traceback.print_exc(file=f)
        print(f"Error logged to {error_log}")