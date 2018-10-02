import discord
from discord.ext import commands
from discord.utils import get

bot = commands.Bot(command_prefix='!')

@bot.command(pass_context=True)
async def greet(ctx):
    await bot.say(":smiley: :wave: Hello, there ~chi!" + ctx.message.author.mention)

@bot.command(pass_context=True)
async def memes(ctx):
    await bot.say("Soon")

@bot.command(pass_context=True)
async def mochi(ctx):
    await bot.say("https://media.giphy.com/media/pXIh4UdYWY1Da/giphy.gif")

@bot.command(pass_context=True)
async def roles(ctx):
    result = [role.name for role in ctx.message.server.roles if not role.is_everyone]
    await bot.say(result)

@bot.command(pass_context=True)
async def addRole(ctx, *,role_name):
    author = ctx.message.author
    await bot.create_role(author.server, name=role_name)
    await bot.say("The role: {} has been created!".format(role_name))

@bot.command(pass_context=True)
async def find(ctx, user: discord.Member):
    result = discord.utils.get(ctx.message.server.roles, name=user)
    await bot.say(result)
#trying to pull all of user's roles to create a check

@bot.command(pass_context=True)
async def assign(ctx, user: discord.Member, *,role_name):
    role = get(ctx.message.server.roles, name=role_name)
    if role:
            await bot.add_roles(user, role)
            await bot.say("The role: {} has been assigned!".format(role_name))
    elif role is roles:
        await bot.say("Role already assigned")
    if role is None:
        await bot.say("The role: {} doesn't exist".format(role_name))

@bot.command(pass_context=True)
async def unassign(ctx, user: discord.Member, *,role_name ):
    role = get(ctx.message.server.roles, name=role_name)
    if role:
            await bot.remove_roles(user, role)
            await bot.say("The role: {} has been removed!".format(role_name))
    if role is None:
        await bot.say("The role: {} doesn't exist".format(role_name))

@bot.command(pass_context=True)
async def delRole(ctx, *,role_name):
    role = discord.utils.get(ctx.message.server.roles, name=role_name)
    if role:
            await bot.delete_role(ctx.message.server, role)
            await bot.say("The role: {} has been deleted!".format(role_name))
    if role is None:
        await bot.say("The role doesn't exist!")

@bot.command(pass_context=True)
async def yt(ctx, *, url):
    author = ctx.message.author
    voice_channel = ctx.message.author.voice.voice_channel
    vc = await bot.join_voice_channel(voice_channel)
    player = await vc.create_ytdl_player(url)
    player.start()

@bot.command(pass_context=True)
async def out(ctx):
    server = ctx.message.server
    voice_channel = ctx.message.author.voice.voice_channel
    voice = bot.join_voice_channel
    if voice:
        await voice.disconnect()
        print("Bot left the voice channel")
    else:
        print("Bot was not in channel")

@bot.command(pass_context=True)
async def clear(ctx, amount=100):
    channel = ctx.message.channel
    messages = []
    async for message in bot.logs_from(channel, limit=int(amount) + 1):
        messages.append(message)
    await bot.delete_messages(messages)
    await bot.say('Messages deleted.')

bot.remove_command('help')

@bot.command(pass_context=True)
async def help(ctx):
    embed = discord.Embed(title="nice bot", description="A Very mochi bot ~chi. List of commands are:", color=0xeee657)
    embed.add_field(name="!greet", value="Gives a nice greet message", inline=False)
    embed.add_field(name="!cat", value="Gives a cute cat gif to lighten up the mood.", inline=False)
    embed.add_field(name="!info", value="Gives a little info about the bot", inline=False)
    embed.add_field(name="!help", value="Gives this message", inline=False)
    embed.add_field(name="!roles", value="Lists all roles in the server", inline=False)
    embed.add_field(name="!addRoles", value="Create a new role", inline=False)
    embed.add_field(name="!assign", value="Set user role", inline=False)
    embed.add_field(name="!unassign", value="Removes user from role", inline=False)
    embed.add_field(name="!deleteRole", value="Removes role from the server", inline=False)
    embed.add_field(name="!yt", value="Displays youtube queue", inline=False)
    embed.add_field(name="!play", value="Adds youtube videos to queue", inline=False)
    embed.add_field(name="!skip", value="Skips youtube video", inline=False)
    embed.add_field(name="!pause", value="Pause youtube video", inline=False)
    embed.add_field(name="!clear", value="Clears all texts in the channel", inline=False)
    await bot.say(embed=embed)

def on_command_error(self, error, ctx):
        if isinstance(error, commands.NoPrivateMessage):
            await
            bot.send_message(ctx.message.author,
                              "\N{WARNING SIGN} Sorry, you can't use this command in a private message!")

        elif isinstance(error, commands.DisabledCommand):
            await
            bot.send_message(ctx.message.author, "\N{WARNING SIGN} Sorry, this command is disabled!")

        elif isinstance(error, commands.CommandOnCooldown):
            await
            bot.send_message(ctx.message.channel,
                              f"{ctx.message.author.mention} slow down! Try again in {error.retry_after:.1f} seconds.")

        elif isinstance(error, commands.MissingRequiredArgument) or isinstance(error, commands.BadArgument):
            await
            bot.send_message(ctx.message.channel, f"\N{WARNING SIGN} {error}")

        elif isinstance(error, commands.CommandInvokeError):
            original_name = error.original.__class__.__name__
            print(f"In {paint(ctx.command.qualified_name, 'b_red')}:")
            traceback.print_tb(error.original.__traceback__)
            print(f"{paint(original_name, 'red')}: {error.original}")

        else:
            print(f"{paint(type(error).__name__, 'b_red')}: {error}")

@bot.event
async def on_ready():
    print('Logged in as')
    print(bot.user.name)
    print(bot.user.id)
    print('------')

bot.run('token')
