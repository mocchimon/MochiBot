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

    if message.content == "!thicc":
        await client.send_message(message.channel, "Brooke is thicc! ~chi")

    if message.content == "!help":
        await client.send_message(message.channel, "Here are the commands ~chi")
        await client.send_message(message.channel, "!hi, !help, !rolelist, !setrole, !thicc,")

    if message.content == "!rolelist":
        ''' Displays all roles/IDs '''
        roles = message.server.roles
        result = 'The roles are '
        for role in roles:
            result = result + role.name + ': ' + ', '
            result2 = result + role.name + ': ' + role.id + ', '
        await client.send_message(message.channel, result)
        print(result2)

    if message.content == "!setrole":
        await client.send_message(message.channel, 'season pass required ~chi')

    if message.content == "!yt":
        await client.send_message(message.channel, 'this will be paid dlc ~chi')

@client.event
async def on_ready():
    print('Logged in as')
    print(client.user.name)
    print(client.user.id)
    print('------')

client.run('NDkzNjQ4NDIyNjcxMzUxODE5.Do14IQ.-VGCqUCJgAIxx11KpI9gXX9Lzuc')
