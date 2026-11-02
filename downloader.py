import os
import yt_dlp


def fetch_url_info(url):
    """Extracts metadata safely and ensures thumbnail URLs are properly retrieved."""
    ydl_opts = {
        "extract_flat": "in_playlist",
        "quiet": True,
        "no_warnings": True,
        "skip_unavailable_fragments": True,
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=False)

    entries = []
    title = info.get("title") or "Unknown Title"
    
    if "entries" in info:
        for entry in info["entries"]:
            if entry:
                v_url = entry.get("url") or f"https://www.youtube.com/watch?v={entry.get('id')}"
                v_title = entry.get("title") or "Untitled Track"
                duration = entry.get("duration") or 0
                
                # Robust thumbnail extraction across different YouTube dict keys
                thumbnail = entry.get("thumbnail")
                if not thumbnail and entry.get("thumbnails"):
                    thumbnails = entry.get("thumbnails")
                    if thumbnails:
                        thumbnail = thumbnails[-1].get("url")
                
                entries.append({"title": v_title, "url": v_url, "duration": duration, "thumbnail": thumbnail or ""})
    else:
        v_url = info.get("webpage_url") or url
        duration = info.get("duration") or 0
        thumbnail = info.get("thumbnail") or (info.get("thumbnails")[-1].get("url") if info.get("thumbnails") else "")
        entries.append({"title": title, "url": v_url, "duration": duration, "thumbnail": thumbnail or ""})

    return title, entries


def get_ydl_options(format_choice, output_dir, progress_hook):
    """Maps user quality selections to strict FFmpeg merge parameters."""
    outtmpl = os.path.join(output_dir, "%(title)s.%(ext)s")
    
    opts = {
        "outtmpl": outtmpl,
        "noplaylist": True,
        "progress_hooks": [progress_hook],
        "quiet": True,
        "no_warnings": True,
        "ignoreerrors": True,
        "keepvideo": False,
    }

    if "mp3" in format_choice:
        bitrate = format_choice.split()[1].replace("k", "")
        opts.update({
            "format": "bestaudio/best",
            "postprocessors": [{"key": "FFmpegExtractAudio", "preferredcodec": "mp3", "preferredquality": bitrate}],
        })
    elif "FLAC" in format_choice:
        opts.update({
            "format": "bestaudio/best",
            "postprocessors": [{"key": "FFmpegExtractAudio", "preferredcodec": "flac", "preferredquality": "0"}],
        })
    elif "WAV" in format_choice:
        opts.update({
            "format": "bestaudio/best",
            "postprocessors": [{"key": "FFmpegExtractAudio", "preferredcodec": "wav", "preferredquality": "0"}],
        })
    else:
        if "360p" in format_choice:
            v_format = "bestvideo[height<=360]+bestaudio/best[height<=360]/best"
        elif "720p" in format_choice:
            v_format = "bestvideo[height<=720]+bestaudio/best[height<=720]/best"
        elif "1080p" in format_choice:
            v_format = "bestvideo[height<=1080]+bestaudio/best[height<=1080]/best"
        else:
            v_format = "bestvideo+bestaudio/best"

        opts.update({
            "format": v_format,
            "merge_output_format": "mp4",
        })

    return opts