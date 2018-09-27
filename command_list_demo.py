import discord
from discord.ext import commands

bot = commands.Bot(command_prefix='!')

@bot.command(pass_context=True)
async def plus(ctx, a: int, b: int):
    await bot.say(a + b)

@bot.command(pass_context=True)
async def multiply(ctx, a: int, b: int):
    await bot.say(a * b)

@bot.command(pass_context=True)
async def greet(ctx):
    await bot.say(":smiley: :wave: Hello, there!" + ctx.message.author.mention)

@bot.command(pass_context=True)
async def cat(ctx):
    await bot.say("https://media.giphy.com/media/JIX9t2j0ZTN9S/giphy.gif")

@bot.command(pass_context=True)
async def roles(ctx):
    result = [role.name for role in ctx.message.server.roles if not role.is_everyone]
    await bot.say(result)

@bot.command(pass_context=True)
async def info(ctx):
    embed = discord.Embed(title="Mochi bot", description="Mochiest bot there is ever.", color=0xeee657)
    # give info about you here
    embed.add_field(name="Author", value="<Mochi#6689>")
    # give users a link to invite this bot to their server
    embed.add_field(name="Invite", value="[https://discordapp.com/oauth2/authorize?&client_id=493648422671351819&scope=bot&permissions=8]")
    await bot.say(embed=embed)

bot.remove_command('help')

@bot.command(pass_context=True)
async def help(ctx):
    embed = discord.Embed(title="nice bot", description="A Very mochi bot ~chi. List of commands are:", color=0xeee657)
    embed.add_field(name="!add X Y", value="Gives the addition of **X** and **Y**", inline=False)
    embed.add_field(name="!multiply X Y", value="Gives the multiplication of **X** and **Y**", inline=False)
    embed.add_field(name="!greet", value="Gives a nice greet message", inline=False)
    embed.add_field(name="!cat", value="Gives a cute cat gif to lighten up the mood.", inline=False)
    embed.add_field(name="!info", value="Gives a little info about the bot", inline=False)
    embed.add_field(name="!help", value="Gives this message", inline=False)
    embed.add_field(name="!roles", value="Set your role", inline=False)
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

bot.run('NDkzNjQ4NDIyNjcxMzUxODE5.Do14IQ.-VGCqUCJgAIxx11KpI9gXX9Lzuc')
