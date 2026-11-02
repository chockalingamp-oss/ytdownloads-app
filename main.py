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


class TrackRow(ctk.CTkFrame):
    """Represents an individual row with asynchronous thumbnail loading."""
    def __init__(self, master, index, title, url, thumbnail_url, default_format, app_instance):
        super().__init__(master, fg_color=BG_CARD, corner_radius=8)
        self.url = url
        self.title = title
        self.thumbnail_url = thumbnail_url
        self.saved_path = None
        self.app_instance = app_instance

        self.grid_columnconfigure(2, weight=1)

        # Checkbox
        self.var = ctk.BooleanVar(value=True)
        self.checkbox = ctk.CTkCheckBox(self, text=f"{index}.", variable=self.var, width=40, font=ctk.CTkFont(size=12))
        self.checkbox.grid(row=0, column=0, padx=(10, 0), pady=10, sticky="w")

        # Thumbnail Button
        fallback = Image.new("RGB", (60, 36), color=(45, 45, 50))
        self.fallback_img = ctk.CTkImage(light_image=fallback, dark_image=fallback, size=(60, 36))
        
        self.thumb_btn = ctk.CTkButton(
            self, image=self.fallback_img, text="", width=60, height=36,
            fg_color="transparent", hover_color=("#E0E0E0", "#2A2A2E"),
            command=self.play_preview
        )
        self.thumb_btn.grid(row=0, column=1, padx=6, pady=6)

        # Title Label
        self.title_lbl = ctk.CTkLabel(self, text=title[:40] + "..." if len(title) > 40 else title, anchor="w", font=ctk.CTkFont(size=12))
        self.title_lbl.grid(row=0, column=2, padx=6, pady=10, sticky="ew")

        # Format Dropdown Menu
        self.format_var = ctk.StringVar(value=default_format if default_format in FORMAT_LIST else "mp3 320k")
        self.format_var.trace_add("write", self.on_format_changed)
        
        self.format_menu = ctk.CTkOptionMenu(
            self, variable=self.format_var, width=135, height=28,
            values=FORMAT_LIST
        )
        self.format_menu.grid(row=0, column=3, padx=6, pady=10)

        # Status Label
        self.status_label = ctk.CTkLabel(self, text="Ready", text_color=TEXT_MUTED, width=70, anchor="e")
        self.status_label.grid(row=0, column=4, padx=6, pady=10)

        # Circular Red Download Button
        self.circular_dl_icon = create_circular_red_download_icon((22, 22))
        self.download_btn = ctk.CTkButton(
            self, text="", image=self.circular_dl_icon, width=32, height=28,
            fg_color="transparent", hover_color=("#EAEAEA", "#2A2A2E"),
            command=self.trigger_single_download
        )
        self.download_btn.grid(row=0, column=5, padx=(2, 2), pady=10)

        # Folder Button
        self.folder_btn = ctk.CTkButton(
            self, text="📁", width=32, height=28, fg_color=("#D1E7DD", "#1F4E3D"),
            text_color=TEXT_PRIMARY, command=self.open_folder
        )
        self.folder_btn.grid(row=0, column=6, padx=(2, 10), pady=10)
        self.folder_btn.grid_remove()

        threading.Thread(target=self._load_thumbnail_async, daemon=True).start()

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
        self.app_instance.open_player(self.url, self.title)

    def on_format_changed(self, *args):
        if self.saved_path:
            self.download_btn.grid()
            self.folder_btn.grid_remove()
            self.status_label.configure(text="Ready", text_color=TEXT_MUTED)
            self.saved_path = None

    def trigger_single_download(self):
        threading.Thread(target=self.app_instance.run_download_job, args=([self],), daemon=True).start()

    def set_status(self, text, color=None):
        self.status_label.configure(text=text)
        if color:
            self.status_label.configure(text_color=color)

    def enable_completion(self, filepath):
        self.saved_path = filepath
        self.download_btn.grid_remove()
        self.folder_btn.grid()

    def open_folder(self):
        if self.saved_path and os.path.exists(self.saved_path):
            subprocess.run(["explorer", "/select,", os.path.normpath(self.saved_path)])
        elif self.saved_path:
            os.startfile(os.path.dirname(os.path.normpath(self.saved_path)))


class YTDownloadsApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("YTDownloads -v1.0")
        self.geometry("1150x740")
        self.minsize(980, 640)
        self.configure(fg_color=BG_MAIN)

        self.download_dir = os.path.join(os.path.expanduser("~"), "Downloads")
        self.all_entries = []
        self.current_page = 0
        self.page_size = 50
        self.track_rows = []
        self.is_dark_mode = True

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(3, weight=1)

        self._build_header()
        self._build_input_card()
        self._build_progress_bar()
        self._build_queue_card()
        self._build_footer()

    def _build_header(self):
        header = ctk.CTkFrame(self, fg_color=BG_CARD, height=65, corner_radius=0)
        header.grid(row=0, column=0, sticky="ew")
        header.grid_columnconfigure(0, weight=1)
        header.grid_columnconfigure(1, weight=1)
        header.grid_columnconfigure(2, weight=1)

        # Left: Clean Header Version & Icon
        head_frame = ctk.CTkFrame(header, fg_color="transparent")
        head_frame.grid(row=0, column=0, padx=16, pady=14, sticky="w")
        
        icon_img = create_circular_red_download_icon((22, 22))
        ctk.CTkLabel(head_frame, image=icon_img, text="").pack(side="left", padx=(0, 8))
        ctk.CTkLabel(head_frame, text="YTDownloads -v1.0", font=ctk.CTkFont(size=16, weight="bold")).pack(side="left")

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

        # Right: Theme & Folder Controls
        controls = ctk.CTkFrame(header, fg_color="transparent")
        controls.grid(row=0, column=2, padx=16, pady=12, sticky="e")

        self.theme_btn = ctk.CTkButton(controls, text="☀ Light Mode", width=110, height=32, command=self.toggle_theme)
        self.theme_btn.pack(side="left", padx=6)

        ctk.CTkButton(controls, text="📁 Set Folder", width=100, height=32, command=self.choose_directory).pack(side="left")

    def _build_input_card(self):
        card = ctk.CTkFrame(self, fg_color=BG_CARD, corner_radius=10)
        card.grid(row=1, column=0, padx=16, pady=(12, 6), sticky="ew")
        card.grid_columnconfigure(0, weight=1)

        row = ctk.CTkFrame(card, fg_color="transparent")
        row.grid(row=0, column=0, padx=16, pady=16, sticky="ew")
        row.grid_columnconfigure(0, weight=1)

        self.url_entry = ctk.CTkEntry(row, placeholder_text="Paste YouTube video, music, or playlist URL here...", height=40)
        self.url_entry.grid(row=0, column=0, padx=(0, 10), sticky="ew")

        self.master_format_var = ctk.StringVar(value="mp3 320k")
        self.format_menu = ctk.CTkOptionMenu(
            row, variable=self.master_format_var, width=175, height=40,
            values=FORMAT_LIST
        )
        self.format_menu.grid(row=0, column=1, padx=6)

        ctk.CTkButton(row, text="Paste", width=75, height=40, command=self.paste_clipboard).grid(row=0, column=2, padx=6)
        ctk.CTkButton(row, text="Fetch Info", width=110, height=40, fg_color=ACCENT_BLUE, text_color="#000000", font=ctk.CTkFont(weight="bold"), command=self.start_fetch).grid(row=0, column=3, padx=(6, 0))

    def _build_progress_bar(self):
        self.prog_frame = ctk.CTkFrame(self, fg_color="transparent", height=15)
        self.prog_frame.grid(row=2, column=0, padx=16, sticky="ew")
        self.prog_frame.grid_columnconfigure(0, weight=1)

        self.progressbar = ctk.CTkProgressBar(self.prog_frame, height=8, mode="indeterminate")

    def _build_queue_card(self):
        self.queue_card = ctk.CTkFrame(self, fg_color=BG_CARD, corner_radius=10)
        self.queue_card.grid(row=3, column=0, padx=16, pady=(6, 6), sticky="nsew")
        self.queue_card.grid_columnconfigure(0, weight=1)
        self.queue_card.grid_rowconfigure(1, weight=1)

        q_head = ctk.CTkFrame(self.queue_card, fg_color="transparent")
        q_head.grid(row=0, column=0, padx=16, pady=10, sticky="ew")
        q_head.grid_columnconfigure(1, weight=1)

        self.queue_title_lbl = ctk.CTkLabel(q_head, text="Queue (0 items)", font=ctk.CTkFont(size=15, weight="bold"))
        self.queue_title_lbl.grid(row=0, column=0, sticky="w")

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

    def toggle_theme(self):
        if self.is_dark_mode:
            ctk.set_appearance_mode("Light")
            self.theme_btn.configure(text="☾ Dark Mode")
            self.is_dark_mode = False
        else:
            ctk.set_appearance_mode("Dark")
            self.theme_btn.configure(text="☀ Light Mode")
            self.is_dark_mode = True

    def choose_directory(self):
        sel = filedialog.askdirectory(initialdir=self.download_dir)
        if sel:
            self.download_dir = os.path.normpath(sel)

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
        self.progressbar.grid(row=0, column=0, sticky="ew")
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
        self.empty_lbl.grid(row=0, column=0, pady=50)
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

    def start_fetch(self):
        url = self.url_entry.get().strip()
        if not url:
            messagebox.showwarning("Missing URL", "Please enter a valid YouTube or media URL.")
            return

        for r in self.track_rows:
            r.destroy()
        self.track_rows.clear()
        self.all_entries.clear()
        self.empty_lbl.grid_forget()

        self.progressbar.grid(row=0, column=0, sticky="ew")
        self.progressbar.start()

        threading.Thread(target=self._fetch_worker, args=(url,), daemon=True).start()

    def _fetch_worker(self, url):
        try:
            playlist_title, entries = downloader.fetch_url_info(url)
            self.all_entries = entries
            self.current_page = 0
            self.after(0, lambda: self.render_page(0))
        except Exception as e:
            self.after(0, lambda: messagebox.showerror("Fetch Error", str(e)))
            self.after(0, self._hide_progress)

    def _hide_progress(self):
        self.progressbar.stop()
        self.progressbar.grid_forget()

    def render_page(self, page_num):
        self._hide_progress()
        for r in self.track_rows:
            r.destroy()
        self.track_rows.clear()

        total_items = len(self.all_entries)
        if total_items == 0:
            self.empty_lbl.grid(row=0, column=0, pady=50)
            self.page_lbl.configure(text="Page 0 of 0")
            self.prev_btn.configure(state="disabled")
            self.next_btn.configure(state="disabled")
            self.queue_title_lbl.configure(text="Queue (0 items)")
            return

        self.empty_lbl.grid_forget()
        total_pages = (total_items + self.page_size - 1) // self.page_size
        self.current_page = max(0, min(page_num, total_pages - 1))

        start_idx = self.current_page * self.page_size
        end_idx = min(start_idx + self.page_size, total_items)
        page_items = self.all_entries[start_idx:end_idx]

        default_fmt = self.master_format_var.get()
        for i, item in enumerate(page_items):
            absolute_idx = start_idx + i + 1
            thumb = item.get("thumbnail", "")
            row = TrackRow(self.scroll_frame, absolute_idx, item["title"], item["url"], thumb, default_fmt, self)
            row.grid(row=i, column=0, padx=4, pady=4, sticky="ew")
            self.track_rows.append(row)

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
        for row in rows_to_download:
            self.after(0, row.set_status, "Downloading", "#3B8ED0")
            
            def hook(d):
                if d["status"] == "finished":
                    self.after(0, row.set_status, "Converting...", "#E69500")

            opts = downloader.get_ydl_options(row.format_var.get(), self.download_dir, hook)

            try:
                with yt_dlp.YoutubeDL(opts) as ydl:
                    info = ydl.extract_info(row.url, download=True)
                    if not info:
                        raise Exception("Download failed.")

                    filepath = None
                    if info.get("requested_downloads"):
                        filepath = info["requested_downloads"][0].get("filepath")
                    
                    if not filepath:
                        prep = ydl.prepare_filename(info)
                        ext = "mp3" if "mp3" in row.format_var.get() else ("flac" if "FLAC" in row.format_var.get() else ("wav" if "WAV" in row.format_var.get() else "mp4"))
                        filepath = os.path.splitext(prep)[0] + f".{ext}"

                self.after(0, row.set_status, "Completed ✓", "#2FA572")
                self.after(0, row.enable_completion, filepath)
            except Exception as e:
                self.after(0, row.set_status, "Error ✗", "#D9534F")
                print(f"DOWNLOAD ERROR: {e}")

    def open_issue_dialog(self):
        """Pops up the 'Describe the issue' ticket creation window."""
        dialog = ctk.CTkToplevel(self)
        dialog.title("Describe the issue")
        dialog.geometry("450x480")
        dialog.resizable(False, False)
        dialog.grab_set()

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
Description of issue that user typed: {udesc}

Instructions: YTDownloads will not send any information to developer. Kindly attach this file and send an email to waalkstreets@gmail.com
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

        ctk.CTkLabel(succ, text="Thank you for reporting the issue", font=ctk.CTkFont(size=16, weight="bold")).pack(padx=20, pady=(20, 5))
        ctk.CTkLabel(succ, text=f"Ticket Number: {ticket_no}", font=ctk.CTkFont(size=13, weight="bold"), text_color=ACCENT_BLUE).pack(padx=20, pady=(0, 10))

        instructions = (
            "YTDownloads will not send any information to developer.\n"
            "Kindly download the ticket file and send an email\n"
            "with the attachment to waalkstreets@gmail.com"
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
                    messagebox.showinfo("Success", "Ticket file downloaded successfully!", parent=succ)
                except Exception as ex:
                    messagebox.showerror("Error", f"Could not save file: {ex}", parent=succ)

        btn_frame = ctk.CTkFrame(succ, fg_color="transparent")
        btn_frame.pack(padx=20, pady=(0, 20))

        ctk.CTkButton(btn_frame, text="Download File", width=140, height=34, fg_color="#2FA572", command=download_ticket_file).pack(side="left", padx=8)
        ctk.CTkButton(btn_frame, text="Close", width=100, height=34, fg_color="gray50", command=succ.destroy).pack(side="left", padx=8)


if __name__ == "__main__":
    app = YTDownloadsApp()
    app.mainloop()