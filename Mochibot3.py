from discord.ext import commands
import discordSuperUtils
from discordSuperUtils import MusicManager
import discord
import aiohttp

client_id = "434afb9a84174e83bbbdc3ea3f49a961"
client_secret = "d7e3e90db6a547c98da79deebfa58d39"

bot = commands.Bot(command_prefix="!")
MusicManager = MusicManager(bot, client_id=client_id,
                                  client_secret=client_secret, spotify_support=True)


@MusicManager.event()
async def on_music_error(ctx, error):
    raise error  # add your error handling here! Errors are listed in the documentation.


@MusicManager.event()
async def on_queue_end(ctx):
    print(f"The queue has ended in {ctx}")
    # You could wait and check activity, etc...


@MusicManager.event()
async def on_inactivity_disconnect(ctx):
    print(f"I have left {ctx} due to inactivity..")


@MusicManager.event()
async def on_play(ctx, player):
    await ctx.send(f"Playing {player}")

@bot.event
async def on_ready():
    print("Music manager is ready.", bot.user)

@bot.command()
async def leave(ctx):
    if await MusicManager.leave(ctx):
        await ctx.send("Left Voice Channel")


@bot.command()
async def np(ctx):
    if player := await MusicManager.now_playing(ctx):
        duration_played = await MusicManager.get_player_played_duration(ctx, player)
        # You can format it, of course.

        await ctx.send(
            f"Currently playing: {player}, \n"
            f"Duration: {duration_played}/{player.duration}"
        )


@bot.command()
async def join(ctx):
    if await MusicManager.join(ctx):
        await ctx.send("Joined Voice Channel")


@bot.command()
async def play(ctx, *, query: str):
    if not ctx.voice_client or not ctx.voice_client.is_connected():
        await MusicManager.join(ctx)

    async with ctx.typing():
        players = await MusicManager.create_player(query, ctx.author)

    if players:
        if await MusicManager.queue_add(
            players=players, ctx=ctx
        ) and not await MusicManager.play(ctx):
            await ctx.send("Added to queue")

    else:
        await ctx.send("Query not found.")

@bot.command()
async def pause(ctx):
    if await MusicManager.pause(ctx):
        await ctx.send("Player paused.")

@bot.command()
async def stop(ctx):
    if await MusicManager.pause(ctx):
        await ctx.send("Player stopped.")

@bot.command()
async def resume(ctx):
    if await MusicManager.resume(ctx):
        await ctx.send("Player resumed.")


@bot.command()
async def volume(ctx, volume: int):
    await MusicManager.volume(ctx, volume)


@bot.command()
async def loop(ctx):
    is_loop = await MusicManager.loop(ctx)

    if is_loop is not None:
        await ctx.send(f"Looping toggled to {is_loop}")


@bot.command()
async def shuffle(ctx):
    is_shuffle = await MusicManager.shuffle(ctx)

    if is_shuffle is not None:
        await ctx.send(f"Shuffle toggled to {is_shuffle}")

@bot.command(pass_context=True)
async def commands(ctx):
    embed = discord.Embed(title="nice bot", description="A Very mochi bot ~chi. List of commands are:", color=0xeee657)
    embed.add_field(name="!info", value="Gives a little info about the bot", inline=False)
    embed.add_field(name="!mochi", value="plays a gif of monster rancher mochi", inline=False)
    embed.add_field(name="!doge", value="plays a gif of a shiba inu", inline=False)
    embed.add_field(name="!commands", value="Gives this message", inline=False)
    embed.add_field(name="!play", value="Adds youtube/spotify to queue", inline=False)
    embed.add_field(name="!skip", value="Skips video", inline=False)
    embed.add_field(name="!pause", value="Pause video", inline=False)
    embed.add_field(name="!stop", value="stops video", inline=False)    
    await ctx.send(embed=embed)

@bot.command(pass_context=True)
async def info(ctx):
    await ctx.send("Bot inspired by monster rancher mochi")

@bot.command(pass_context=True)
async def mochi(ctx):
    await ctx.send("https://66.media.tumblr.com/93fcfa886fe7781eed0db910c19a09c3/tumblr_mt7emv63Zl1s5p5m0o1_400.gif")


@bot.command()
async def doge(ctx):
   async with aiohttp.ClientSession() as session:
      request = await session.get('http://shibe.online/api/shibes?count=1&urls=true&httpsUrls=true') # Make a request
      dogjson = {'link'} #creating a key
      dogjson2 = await request.json() # Convert it to a JSON dictionary
      dogjson = dogjson2
      await ctx.send (dogjson)
   embed = discord.Embed(title="Doge!", color=discord.Color.purple()) # Create embed
   embed.set_image(url=dogjson['link']) # Set the embed image to the value of the 'link' key (if there is no link key this wont work)
   await ctx.send(embed=embed) # Send the embed

@bot.command()
async def autoplay(ctx):
    is_autoplay = await MusicManager.autoplay(ctx)

    if is_autoplay is not None:
        await ctx.send(f"Autoplay toggled to {is_autoplay}")


@bot.command()
async def queueloop(ctx):
    is_loop = await MusicManager.queueloop(ctx)

    if is_loop is not None:
        await ctx.send(f"Queue looping toggled to {is_loop}")


@bot.command()
async def history(ctx):
    if ctx_queue := await MusicManager.get_queue(ctx):
        formatted_history = [
            f"Title: '{x.title}'\nRequester: {x.requester.mention}"
            for x in ctx_queue.history
        ]

        embeds = discordSuperUtils.generate_embeds(
            formatted_history,
            "Song History",
            "Shows all played songs",
            25,
            string_format="{}",
        )

        page_manager = discordSuperUtils.PageManager(ctx, embeds, public=True)
        await page_manager.run()


@bot.command()
async def skip(ctx, index: int = None):
    await MusicManager.skip(ctx, index)


@bot.command()
async def queue(ctx):
    if ctx_queue := await MusicManager.get_queue(ctx):
        formatted_queue = [
            f"Title: '{x.title}\nRequester: {x.requester.mention}"
            for x in ctx_queue.queue
        ]

        embeds = discordSuperUtils.generate_embeds(
            formatted_queue,
            "Queue",
            f"Now Playing: {await MusicManager.now_playing(ctx)}",
            25,
            string_format="{}",
        )

        page_manager = discordSuperUtils.PageManager(ctx, embeds, public=True)
        await page_manager.run()


@bot.command()
async def rewind(ctx, index: int = None):
    await MusicManager.previous(ctx, index)


@bot.command()
async def ls(ctx):
    if queue := await MusicManager.get_queue(ctx):
        loop = queue.loop
        loop_status = None

        if loop == discordSuperUtils.Loops.LOOP:
            loop_status = "Looping enabled."

        elif loop == discordSuperUtils.Loops.QUEUE_LOOP:
            loop_status = "Queue looping enabled."

        elif loop == discordSuperUtils.Loops.NO_LOOP:
            loop_status = "No loop enabled."

        if loop_status:
            await ctx.send(loop_status)


bot.run('NDkzNjQ4NDIyNjcxMzUxODE5.DpU4NA.nvKiZS7psY0i0RXbvyQ9rXFlYzE')
