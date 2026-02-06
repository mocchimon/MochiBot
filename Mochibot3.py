import discord
from discord.ext import commands
from discord import FFmpegPCMAudio
import yt_dlp
import asyncio
import os
import aiohttp
import re
import json
import threading
import base64
import time
import traceback
from flask import Flask, request
import spotipy
from spotipy.oauth2 import SpotifyClientCredentials
global current_song

# -------------------------
# CONFIG
# -------------------------
os.environ["YTDLP_JS_RUNTIME"] = "node:C:/Program Files/nodejs/node.exe"

TOKEN = ""

SPOTIFY_CLIENT_ID = ""
SPOTIFY_CLIENT_SECRET = ""
spotify_token = None
spotify_token_expiry = 0

async def get_spotify_token():
    global spotify_token, spotify_token_expiry

    # Reuse token if still valid
    if spotify_token and time.time() < spotify_token_expiry:
        return spotify_token

    auth = base64.b64encode(
        f"{SPOTIFY_CLIENT_ID}:{SPOTIFY_CLIENT_SECRET}".encode()
    ).decode()

    async with aiohttp.ClientSession() as session:
        async with session.post(
            "https://accounts.spotify.com/api/token",
            headers={"Authorization": f"Basic {auth}"},
            data={"grant_type": "client_credentials"}
        ) as resp:
            data = await resp.json()

            print("Token request status:", resp.status)
            print("Token request body:", data)

    if "access_token" not in data:
        print("Failed to obtain Spotify token")
        return None

    spotify_token = data["access_token"]
    spotify_token_expiry = time.time() + data["expires_in"] - 30

    return spotify_token

# -------------------------
# Discord bot setup
# -------------------------

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

last_output_channel = None
guild_queues = {}

# -------------------------
# Spotify API setup
# -------------------------

sp = spotipy.Spotify(
    auth_manager=SpotifyClientCredentials(
        client_id=SPOTIFY_CLIENT_ID,
        client_secret=SPOTIFY_CLIENT_SECRET
    )
)

# -------------------------------------------------
# Fetch HTML (async, non-blocking)
# -------------------------------------------------
async def fetch(url: str) -> str:
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as resp:
            return await resp.text()


# -------------------------------------------------
# YouTube search (async, non-blocking)
# -------------------------------------------------
async def youtube_search(query: str):
    def run_ydl():
        try:
            ydl = yt_dlp.YoutubeDL({
                "quiet": True,
                "default_search": "ytsearch1"
            })
            return ydl.extract_info(query, download=False)
        except Exception as e:
            print("yt_dlp error:", e)
            return None

    info = await asyncio.to_thread(run_ydl)

    if not info:
        print("youtube_search: no info returned")
        return None

    # Search result
    if isinstance(info, dict) and "entries" in info and info["entries"]:
        entry = info["entries"][0]
    else:
        entry = info

    if not isinstance(entry, dict):
        print("youtube_search: invalid entry:", entry)
        return None

    return {
        "title": entry.get("title"),
        "url": entry.get("webpage_url"),
        "duration": entry.get("duration"),
        "source": "youtube"
    }

# ============================
# Music Bot Globals & Settings
# ============================

SPOTIFY_RESOLVE_LIMIT = 5   # soft cap — easy to change later

music_queues = {}
voice_clients = {}

# -------------------------------------------------
# Spotify single track → "Song Artist"
# -------------------------------------------------
async def resolve_spotify_playlist(url):
    try:
        playlist_id = url.split("/playlist/")[1].split("?")[0]
    except:
        print("Invalid Spotify playlist URL")
        return []

    token = await get_spotify_token()
    if not token:
        print("Failed to get Spotify token")
        return []

    api_url = f"https://api.spotify.com/v1/playlists/{playlist_id}"
    headers = {"Authorization": f"Bearer {token}"}

    results = []
    unresolved = []

    async with aiohttp.ClientSession() as session:
        async with session.get(api_url, headers=headers) as resp:
            if resp.status != 200:
                print("Spotify API error:", resp.status)
                return []
            data = await resp.json()

        tracks = data.get("tracks", {})
        items = tracks.get("items", [])
        next_url = tracks.get("next")

        # Process first page
        for item in items:
            track = item.get("track")
            if not track:
                continue

            name = track.get("name")
            artists = track.get("artists", [])
            artist = artists[0]["name"] if artists else None

            if not name or not artist:
                continue

            # Build unresolved entry
            unresolved.append({
                "title": name,
                "artist": artist,
                "source": "spotify",
                "resolved": False
            })

        # Pagination — collect metadata only
        while next_url:
            async with session.get(next_url, headers=headers) as resp:
                if resp.status != 200:
                    break
                page = await resp.json()

            items = page.get("items", [])
            next_url = page.get("next")

            for item in items:
                track = item.get("track")
                if not track:
                    continue

                name = track.get("name")
                artists = track.get("artists", [])
                artist = artists[0]["name"] if artists else None

                if not name or not artist:
                    continue

                unresolved.append({
                    "title": name,
                    "artist": artist,
                    "source": "spotify",
                    "resolved": False
                })

    # Resolve only the first N tracks
    to_resolve = unresolved[:SPOTIFY_RESOLVE_LIMIT]
    remaining = unresolved[SPOTIFY_RESOLVE_LIMIT:]

    for entry in to_resolve:
        query = f"{entry['title']} {entry['artist']}"
        yt_data = await youtube_search(query)

        print(f"DEBUG playlist track: {query} → {yt_data}")

        if yt_data and yt_data.get("url") and yt_data.get("title"):
            entry.update({
                "url": yt_data["url"],
                "duration": yt_data["duration"],
                "resolved": True
            })
            results.append(entry)
        else:
            print(f"Skipping track (invalid YouTube metadata): {query}")

    # Add unresolved tracks after resolved ones
    results.extend(remaining)

    print(f"DEBUG resolver returning {len(results)} tracks "
          f"({len(to_resolve)} resolved, {len(remaining)} unresolved)")

    return results


async def process_spotify_item(item, results):
    track = item.get("track")
    if not track:
        return

    name = track.get("name")
    artists = track.get("artists", [])
    artist = artists[0]["name"] if artists else None

    if not name or not artist:
        return

    query = f"{name} {artist}"
    yt_data = await youtube_search(query)

    print(f"DEBUG playlist track: {query} → {yt_data}")

    if yt_data and yt_data.get("url") and yt_data.get("title"):
        results.append({
            "title": yt_data["title"],
            "url": yt_data["url"],
            "duration": yt_data["duration"]
        })

async def resolve_youtube(query):
    import re

    def clean_title(raw):
        if not raw:
            return None

        # Remove junk like (Official Video), [Lyrics], (HD), etc.
        raw = re.sub(r"\(.*?\)", "", raw)
        raw = re.sub(r"\[.*?\]", "", raw)

        # Strip leading/trailing quotes and whitespace
        raw = raw.strip().strip("'\"").strip()

        return raw

    def split_artist_title(raw):
        if not raw:
            return None, None

        # Normalize dashes
        raw = raw.replace("—", "-").replace("–", "-")

        # Split on first dash
        if " - " in raw:
            artist, title = raw.split(" - ", 1)
            return artist.strip(), title.strip()

        return None, raw.strip()

    def run_ydl():
        ydl_opts = {
            "quiet": True,
            "skip_download": True,
            "extract_flat": False,
            "format": "bestaudio/best",
        }
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            return ydl.extract_info(query, download=False)

    info = await asyncio.to_thread(run_ydl)
    results = []

    # Playlist
    if "entries" in info:
        for entry in info["entries"]:
            if entry:
                raw_title = entry.get("title")
                clean = clean_title(raw_title)
                artist, title = split_artist_title(clean)

                results.append({
                    "title": title,
                    "artist": artist,
                    "url": entry.get("url") or entry.get("webpage_url"),
                    "duration": entry.get("duration"),
                    "source": "youtube",
                    "resolved": True
                })
        return results

    # Single video
    raw_title = info.get("title")
    clean = clean_title(raw_title)
    artist, title = split_artist_title(clean)

    return [{
        "title": title,
        "artist": artist,
        "url": info.get("webpage_url"),
        "duration": info.get("duration"),
        "source": "youtube",
        "resolved": True
    }]
# -------------------------
# YouTube search (returns video URL)
# -------------------------
async def youtube_search(query):
    """
    Returns a metadata object:
    {
        "title": "...",
        "url": "...",
        "duration": ...
    }
    """

    # Clean query (Spotify sometimes includes weird characters)
    query = query.replace("’", "'").strip()

    def run_ydl(q):
        ydl_opts = {
            "quiet": True,
            "skip_download": True,
            "extract_flat": False,
            "format": "bestaudio/best",
            "default_search": "ytsearch1"
        }
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            return ydl.extract_info(q, download=False)

    # First attempt
    try:
        info = await asyncio.to_thread(run_ydl, query)
    except:
        info = None

    # If first attempt fails, try again with quotes
    if not info:
        try:
            info = await asyncio.to_thread(run_ydl, f"\"{query}\"")
        except:
            return None

    if not info:
        return None

    # ytsearch1 returns a list under "entries"
    if "entries" in info:
        info = info["entries"][0]

    url = info.get("webpage_url")
    title = info.get("title")

    if not url or not title:
        return None

    return {
        "title": title,
        "url": url,
        "duration": info.get("duration")
    }
# -------------------------
# Download audio (stable)
# -------------------------
async def download_audio(url):
    # Remove previous audio files (run in thread to avoid blocking)
    def cleanup():
        for f in os.listdir():
            if f.startswith("current_song"):
                try:
                    os.remove(f)
                except:
                    pass

    await asyncio.to_thread(cleanup)

    # Run yt_dlp in a thread
    def run_ydl():
        ydl_opts = {
            "format": "bestaudio/best",
            "quiet": True,
            "outtmpl": "current_song.%(ext)s",
        }
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            return ydl.prepare_filename(info)

    file_path = await asyncio.to_thread(run_ydl)

    # Wait for file to exist without blocking the event loop
    while not os.path.exists(file_path) or os.path.getsize(file_path) == 0:
        await asyncio.sleep(0.05)

    return file_path

# -------------------------
# FFmpeg path
# -------------------------

def get_ffmpeg_path():
    if os.system("ffmpeg -version >nul 2>&1") == 0:
        return "ffmpeg"

    local_path = os.path.join(os.getcwd(), "ffmpeg.exe")
    if os.path.isfile(local_path):
        return local_path

    print("ERROR: ffmpeg not found.")
    return None

# -------------------------
# Playback
# -------------------------
def strip_playlist(url):
    if "youtube.com/watch" in url and "&list=" in url:
        return url.split("&list=")[0]
    return url

async def play_next(guild_id):
    queue = guild_queues.get(guild_id)

    # Debug: show queue before popping
    print("DEBUG queue:", queue)

    # If queue is empty → announce and stop
    if not queue:
        channel = last_output_channel
        if channel:
            await channel.send("🎶 Queue finished. No more songs.")
        return

    # Pop the next track
    track = queue.pop(0)
    print("DEBUG popped track:", track, type(track))

    # ⭐ Lazy resolve unresolved Spotify tracks
    if track.get("source") == "spotify" and not track.get("resolved"):
        print("DEBUG lazy resolving:", track["title"], track["artist"])
        yt = await youtube_search(f"{track['title']} {track['artist']}")
        if yt:
            track.update({
                "title": yt["title"],
                "url": yt["url"],
                "duration": yt["duration"],
                "source": "youtube",
                "resolved": True
            })
        else:
            print("DEBUG lazy resolve failed, skipping")
            return await play_next(guild_id)

    # Normalize: convert strings → dicts
    if isinstance(track, str):
        track = {
            "title": track,
            "url": track,
            "duration": None
        }

    # Extract URL safely
    url = track.get("url")
    print("DEBUG resolved url:", url)

    if not url:
        print("ERROR: Track missing URL:", track)
        return

    # Strip playlist parameters
    url = strip_playlist(url)
    print("DEBUG stripped url:", url)

    # ⭐ Correct voice client lookup
    guild = bot.get_guild(guild_id)
    voice = guild.voice_client if guild else None

    print("DEBUG voice client:", voice, "type:", type(voice))

    if not voice:
        print("DEBUG: No voice client for guild", guild_id)
        return

    # Resolve FFmpeg
    ffmpeg_path = get_ffmpeg_path()
    if not ffmpeg_path:
        print("DEBUG: FFmpeg path missing")
        return

    # Download audio (ASYNC SAFE)
    print("DEBUG: starting download for:", url)
    filepath = await download_audio(url)
    print("DEBUG: download finished:", filepath)

    # Debugging to ensure file is valid
    print("DEBUG filepath:", filepath)
    print("DEBUG exists:", os.path.exists(filepath))
    print("DEBUG file size:", os.path.getsize(filepath) if os.path.exists(filepath) else "N/A")
    print("DEBUG cwd:", os.getcwd())
    print("DEBUG ffmpeg:", ffmpeg_path)

    if not os.path.exists(filepath):
        print("ERROR: File does not exist after download:", filepath)
        return

    # Create audio source
    source = discord.FFmpegPCMAudio(filepath, executable=ffmpeg_path)
    print("DEBUG source:", source)

    # Safe callback wrapper
    def after_play(err):
        try:
            if err:
                print("Playback error:", err)
            asyncio.run_coroutine_threadsafe(play_next(guild_id), bot.loop)
        except Exception as e:
            print("Callback exception:", e)

    # Start playback
    try:
        voice.play(source, after=after_play)
        print("DEBUG: voice.play() called successfully")
    except Exception as e:
        print("ERROR: voice.play failed:", e)
        return

    # Give FFmpeg a moment to spin up
    await asyncio.sleep(0.1)

    # ⭐ STORE CURRENT SONG AS "Artist — Title"
    global current_song

    title = track.get("title", url)
    artist = track.get("artist")

    if artist:
        current_song = f"{artist} — {title}"
    else:
        current_song = title

    # Announce now playing
    channel = last_output_channel
    if channel:
        await channel.send(f"🎵 Now playing: {current_song}")
# -------------------------
# Flask server
# -------------------------
from flask import Flask, request, Response
import threading
import json

app = Flask(__name__)

@app.route("/command", methods=["POST"])
def command():
    global last_output_channel

    data = request.get_json(silent=True)
    if not data:
        return "Invalid JSON", 400

    cmd = data.get("command")
    if not cmd:
        return "Missing 'command'", 400

    print("Received command from Streamer.bot:", cmd)

    parts = cmd.split(" ", 1)
    command_name = parts[0].lstrip("!")
    arg = parts[1] if len(parts) > 1 else None

    command_obj = bot.get_command(command_name)
    if not command_obj:
        print("Unknown command:", command_name)
        return "Unknown command", 400

    async def run_command():
        try:
            if not last_output_channel:
                print("No last_output_channel set. Use !join first.")
                return

            class Ctx:
                print("DEBUG: NEW Ctx class is running")

                def __init__(self, bot, channel, command_obj):
                    self.bot = bot
                    self.guild = channel.guild
                    self.channel = channel
                    self.author = channel.guild.me
                    self.message = None
                    self.prefix = "!"
                    self.command = command_obj
                    self.voice_client = channel.guild.voice_client

                async def send(self, msg):
                    await self.channel.send(msg)

            ctx = Ctx(bot, last_output_channel, command_obj)

            if arg:
                await command_obj(ctx, query=arg)
            else:
                await command_obj(ctx)

        except Exception as e:
            print("Error inside run_command():", e)

    bot.loop.create_task(run_command())
    return "OK", 200


# ---------------------------------------------------
# ⭐ UNICODE‑SAFE ENDPOINT FOR STREAMER.BOT
# ---------------------------------------------------
SongQueue = ""   # must appear before the endpoint

@app.route("/songqueue", methods=["GET"])
def songqueue():
    global SongQueue
    payload = {"queue": SongQueue}

    return Response(
        json.dumps(payload, ensure_ascii=False),
        mimetype="application/json"
    )


def run_flask():
    print("Starting Flask server...")
    app.run(host="0.0.0.0", port=5000)

threading.Thread(target=run_flask, daemon=True).start()

# -------------------------
# Commands
# -------------------------

    # If queue is empty → announce and stop


@bot.command()
async def join(ctx):
    global last_output_channel
    last_output_channel = ctx.channel

    if ctx.author.voice is None:
        await ctx.send("You're not in a voice channel.")
        return

    channel = ctx.author.voice.channel

    existing = discord.utils.get(bot.voice_clients, guild=ctx.guild)
    if existing and existing.is_connected():
        await existing.disconnect(force=True)

    await channel.connect()
    await ctx.send(f"Joined {channel.name}")

@bot.command()
async def leave(ctx):
    global last_output_channel
    last_output_channel = ctx.channel

    voice = discord.utils.get(bot.voice_clients, guild=ctx.guild)
    if voice and voice.is_connected():
        await voice.disconnect(force=True)
        await ctx.send("Disconnected.")
    else:
        await ctx.send("I'm not in a voice channel.")

async def expand_playlist(url):
    ydl_opts = {
        "extract_flat": True,
        "skip_download": True,
        "quiet": True,
        "no_warnings": True,
    }

    def run_ydl():
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            return ydl.extract_info(url, download=False)

    info = await asyncio.to_thread(run_ydl)

    # Not a playlist
    if "entries" not in info:
        return [url]

    urls = []
    for entry in info["entries"]:
        if not entry:
            continue

        raw = entry.get("url")

        if not raw:
            continue

        # If it's already a full URL, use it as-is
        if raw.startswith("http"):
            urls.append(raw)
        else:
            # Otherwise treat it as a video ID
            urls.append(f"https://www.youtube.com/watch?v={raw}")

    return urls
def is_url(s: str):
    return s.startswith("http://") or s.startswith("https://")

@bot.command()
async def play(ctx, *, query=None):
    if query is None:
        await ctx.send("Usage: `!play <song name or URL>`")
        return

    global last_output_channel
    last_output_channel = ctx.channel

    # Must be in voice
    if ctx.author.voice is None:
        await ctx.send("Join a voice channel first.")
        return

    # Connect if needed
    voice = discord.utils.get(bot.voice_clients, guild=ctx.guild)
    if not voice:
        voice = await ctx.author.voice.channel.connect()

    guild_id = ctx.guild.id
    queue = guild_queues.setdefault(guild_id, [])

    # Debug
    print("DEBUG queue in !play BEFORE adding:", queue)
    print("DEBUG guild_id in !play:", guild_id)

    # -------------------------------------------------
    # SPOTIFY LINKS (track or playlist)
    # -------------------------------------------------
    if "spotify.com" in query:
        if "track" in query:
            tracks = [await resolve_spotify_track(query)]
        elif "playlist" in query:
            tracks = await resolve_spotify_playlist(query)
        else:
            await ctx.send("Unsupported Spotify link.")
            return

        if not tracks:
            await ctx.send("Failed to resolve Spotify link.")
            return

        # ⭐ Detect if queue was empty BEFORE adding
        was_empty = (len(queue) == 0)

        # Add tracks
        for t in tracks:
            if t:
                queue.append(t)

        print("DEBUG queue in !play AFTER adding:", queue)

        # ⭐ If queue was empty, push the first track back in
        #    so play_next sees a non-empty queue for Twitch display
        if was_empty:
            print("DEBUG pushing first track back into queue for display")
            queue.insert(0, queue[0])   # <-- ⭐ THE FIX

            print("DEBUG calling play_next from !play (Spotify)")
            await play_next(guild_id)
        else:
            await ctx.send(f"Added {len(tracks)} track(s) to the queue.")

        return

@bot.command()
async def queue(ctx):
    global current_song

    guild_id = ctx.guild.id
    queue_list = guild_queues.get(guild_id, [])

    # Local helper for duration formatting
    def format_duration(seconds):
        if not seconds:
            return ""
        minutes = seconds // 60
        secs = seconds % 60
        return f"{minutes}:{secs:02d}"

    message = ""

    # ⭐ Now Playing
    if current_song:
        message += f"**Now Playing:** {current_song}\n\n"
    else:
        message += "**Now Playing:** Nothing\n\n"

    # ⭐ Up Next
    MAX_SHOW = 5

    if queue_list:
        message += f"**Up Next (showing first {MAX_SHOW}):**\n"

        for i, track in enumerate(queue_list[:MAX_SHOW], start=1):
            title = track.get("title", track.get("url", "Unknown Title"))
            artist = track.get("artist")
            duration = format_duration(track.get("duration"))

            # Artist — Title
            if artist:
                display = f"{artist} — {title}"
            else:
                display = title

            display = display.strip("'\"")

            if not track.get("resolved", True):
                display += " (unresolved)"

            # Add duration if available
            if duration:
                display += f" ({duration})"

            message += f"{i}. {display}\n"

        if len(queue_list) > MAX_SHOW:
            message += f"\n… and {len(queue_list) - MAX_SHOW} more tracks."
    else:
        message += "Queue is empty."

    await ctx.send(message)

    # ⭐ Twitch output
    twitch_parts = []

    if current_song:
        twitch_parts.append(f"Now Playing: {current_song}")

    for track in queue_list[:MAX_SHOW]:
        title = track.get("title", track.get("url", "Unknown Title"))
        artist = track.get("artist")
        duration = format_duration(track.get("duration"))

        if artist:
            display = f"{artist} — {title}"
        else:
            display = title

        display = display.strip("'\"")

        if not track.get("resolved", True):
            display += " (unresolved)"

        if duration:
            display += f" ({duration})"

        twitch_parts.append(display)

    global SongQueue
    SongQueue = " | ".join(twitch_parts)


@bot.command()
async def skip(ctx):
    voice = discord.utils.get(bot.voice_clients, guild=ctx.guild)

    if not voice or not voice.is_playing():
        await ctx.send("Nothing is currently playing.")
        return

    await ctx.send("⏭️ Skipping current song...")
    voice.stop()  # <-- THIS triggers after_play(), which triggers play_next()

@bot.command()
async def stop(ctx):
    queue = guild_queues.get(ctx.guild.id)
    if queue:
        queue.clear()

    voice = discord.utils.get(bot.voice_clients, guild=ctx.guild)
    if voice and voice.is_playing():
        voice.stop()

    await ctx.send("Stopped playback and cleared queue.")


# -------------------------
# Run bot
# -------------------------
bot.run('')
