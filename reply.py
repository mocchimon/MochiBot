import discord

client = discord.Client()

@client.event
async def on_message(message):
    # we do not want the bot to reply to itself
    if message.author == client.user:
        return

    if message.content.startswith('!hello'):
        msg = 'Hello {0.author.mention} ~chi'.format(message)
        await client.send_message(message.channel, msg)
        
    if message.content == "!hi":
        await client.send_message(message.channel, "Hello World ~chi")

    if message.content == "!rolelist":
        await client.send_message(message.channel, "much roles ~chi")

@client.event
async def on_ready():
    print('Logged in as')
    print(client.user.name)
    print(client.user.id)
    print('------')

client.run('NDkzNjQ4NDIyNjcxMzUxODE5.Do14IQ.-VGCqUCJgAIxx11KpI9gXX9Lzuc')
