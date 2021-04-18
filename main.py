from configparser import ConfigParser
import discord

class MyClient(discord.Client):
    async def on_ready(self):
        print('Logged on as {0}!'.format(self.user))

    async def on_message(self, message):
        print('Message from {0.author}: {0.content}'.format(message))


if __name__ == "__main__":
    config = ConfigParser()
    config.read('config.ini')
    client = MyClient()
    client.run(config['auth']['token'])