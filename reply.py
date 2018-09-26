import discord


client = discord.Client()

@client.event
async def on_message(message):
    # we do not want the bot to reply to itself
    if message.author == client.user:
        return

    if message.content.startswith('!hi'):
        msg = 'Hello {0.author.mention} ~chi'.format(message)
        await client.send_message(message.channel, msg)
        
    if message.content == "!hello":
        await client.send_message(message.channel, "Hello World ~chi")

    if message.content == "!thicc":
        await client.send_message(message.channel, "Brooke is thicc! ~chi")

    if message.content == "!help":
        await client.send_message(message.channel, "Here are the commands ~chi: !hi, !help, !rolelist, !setrole, !yt, !kick, !ban, !thicc,")

#mods stuff

    if message.content == "!kick":
        await client.send_message(message.channel, 'coming soon ~chi')

    if message.content == "!ban":
        await client.send_message(message.channel, 'coming soon ~chi')

    if message.content == "!rolelist":
        roles = message.server.roles
        result = 'The roles are '
        for role in roles:
            result = result + role.name + ': ' + ', '
        await client.send_message(message.channel, result)

    if message.content == "!setrole":
        await client.send_message(message.channel, 'season pass required ~chi')

#youtube stuffs

    if message.content == "!yt":
        await client.send_message(message.channel, 'this will be paid dlc ~chi')

    if message.content == "!play":
        await client.send_message(message.channel, 'this will be paid dlc ~chi')

    if message.content == "!skip":
        await client.send_message(message.channel, 'this will be paid dlc ~chi')

    if message.content == "!stop":
        await client.send_message(message.channel, 'this will be paid dlc ~chi')


@client.event
async def on_ready():
    print('Logged in as')
    print(client.user.name)
    print(client.user.id)
    print('------')

client.run('NDkzNjQ4NDIyNjcxMzUxODE5.Do14IQ.-VGCqUCJgAIxx11KpI9gXX9Lzuc')
