import discord
from discord.ext import commands
from discord import FFmpegPCMAudio
import yt_dlp
import asyncio
import os
import threading
from flask import Flask, request
import spotipy
from spotipy.oauth2 import SpotifyClientCredentials


# -------------------------
# CONFIG
# -------------------------
os.environ["YTDLP_JS_RUNTIME"] = "node:C:/Program Files/nodejs/node.exe"

TOKEN = ""

SPOTIFY_CLIENT_ID = ""
SPOTIFY_CLIENT_SECRET = ""

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

def resolve_spotify_track(url):
    try:
        track_id = url.split("/track/")[1].split("?")[0]
        data = sp.track(track_id)
        name = data["name"]
        artist = data["artists"][0]["name"]
        return f"{name} {artist}"
    except Exception as e:
        print("Spotify resolver error:", e)
        return None

# -------------------------
# YouTube search (returns video URL)
# -------------------------
def youtube_search(query):
    ydl_opts = {
        "format": "bestaudio/best",
        "quiet": True,
        "default_search": "ytsearch1",
        "postprocessor_args": {
            "youtube": [
                "--js-runtime",
                "node:C:/Program Files/nodejs/node.exe"
            ]
        }
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(query, download=False)
        if "entries" in info:
            return info["entries"][0]["webpage_url"]
        return info["webpage_url"]


# -------------------------
# Download audio (stable)
# -------------------------
def download_audio(url):
    # Remove any previous audio files
    for f in os.listdir():
        if f.startswith("current_song"):
            try:
                os.remove(f)
            except:
                pass

    ydl_opts = {
        "format": "bestaudio/best",
        "quiet": True,
        "outtmpl": "current_song.%(ext)s",
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=True)
        file_path = ydl.prepare_filename(info)

    # Ensure file is fully written before returning
    while not os.path.exists(file_path) or os.path.getsize(file_path) == 0:
        time.sleep(0.05)

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

async def play_next(guild_id):
    queue = guild_queues.get(guild_id)

    # If queue is empty → announce and stop
    if not queue:
        channel = last_output_channel
        if channel:
            await channel.send("🎶 Queue finished. No more songs.")
        return



    url = queue.pop(0)

    # Get voice client
    voice = discord.utils.get(bot.voice_clients, guild__id=guild_id)
    if not voice:
        print("DEBUG: No voice client for guild", guild_id)
        return

    # Resolve FFmpeg
    ffmpeg_path = get_ffmpeg_path()
    if not ffmpeg_path:
        print("DEBUG: FFmpeg path missing")
        return

    # Download audio
    filepath = download_audio(url)

    # Debugging to ensure file is valid
    print("DEBUG filepath:", filepath)
    print("DEBUG exists:", os.path.exists(filepath))
    print("DEBUG cwd:", os.getcwd())
    print("DEBUG ffmpeg:", ffmpeg_path)

    if not os.path.exists(filepath):
        print("ERROR: File does not exist after download:", filepath)
        return

    # Create audio source
    source = discord.FFmpegPCMAudio(filepath, executable=ffmpeg_path)

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
    except Exception as e:
        print("ERROR: voice.play failed:", e)
        return

    # Wait until playback actually starts (but with timeout)
    for _ in range(40):  # 2 seconds max
        if voice.is_playing():
            break
        await asyncio.sleep(0.05)

    if not voice.is_playing():
        print("ERROR: Playback never started for:", filepath)
        return

    # Announce now playing
    channel = last_output_channel
    if channel:
        await channel.send(f"🎵 Now playing: {url}")

# -------------------------
# Flask server
# -------------------------

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

            # Proper fake context for Streamer.bot-triggered commands
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

                    # REQUIRED so Discord.py doesn't misinterpret ctx.guild
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


def run_flask():
    print("Starting Flask server...")
    app.run(host="0.0.0.0", port=5000)

threading.Thread(target=run_flask, daemon=True).start()

# -------------------------
# Commands
# -------------------------

@bot.command()
async def queue(ctx):
    queue = guild_queues.get(ctx.guild.id, [])

    if not queue:
        await ctx.send("The queue is currently empty.")
        return

    message = "**Current Queue:**\n"
    for i, url in enumerate(queue, start=1):
        message += f"{i}. {url}\n"

    await ctx.send(message)

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

@bot.command()
async def play(ctx, *, query=None):
    if query is None:
        await ctx.send("Usage: `!play <song name or URL>`")
        return

    global last_output_channel
    last_output_channel = ctx.channel

    if ctx.author.voice is None:
        await ctx.send("Join a voice channel first.")
        return

    voice = discord.utils.get(bot.voice_clients, guild=ctx.guild)
    if not voice:
        voice = await ctx.author.voice.channel.connect()

    # Spotify → YouTube search
    if "spotify.com/track" in query:
        resolved = resolve_spotify_track(query)
        if not resolved:
            await ctx.send("Failed to resolve Spotify track.")
            return
        query = resolved

    # YouTube search → ALWAYS use webpage_url
    try:
        info = yt_dlp.YoutubeDL({"quiet": True, "default_search": "ytsearch1"}).extract_info(query, download=False)
        if "entries" in info:
            url = info["entries"][0]["webpage_url"]
        else:
            url = info["webpage_url"]
    except Exception as e:
        print("YouTube search error:", e)
        await ctx.send("Failed to search YouTube.")
        return

    # Get queue for this guild
    queue = guild_queues.setdefault(ctx.guild.id, [])

    # If nothing is playing → play immediately
    if not voice.is_playing():
        queue.append(url)
        await ctx.send(f"Playing: **{query}**")
        await play_next(ctx.guild.id)
        return

    # Otherwise → add to queue
    queue.append(url)
    await ctx.send(f"Added to queue: **{query}**")
    return

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
