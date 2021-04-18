from configparser import ConfigParser

import yaml

import seedgen

import discord  # pip install discord.py

class MyClient(discord.Client):
    async def on_ready(self):
        print('Logged on as {0}!'.format(self.user))

    async def on_message(self, message):
        print('Message from {0.author}: {0.content}'.format(message))

        if message.content == "!crea-seed" and message.attachments:
            print("Es un crea seed")
            settings_file = message.attachments[0]
            my_file = await settings_file.read()
            my_yaml = yaml.load(my_file, Loader=yaml.FullLoader)
            seed = await seedgen.crea_seed_con_settings(my_yaml)
            await message.reply(seed.url, mention_author=False)


if __name__ == "__main__":
    config = ConfigParser()
    config.read('config.ini')
    client = MyClient()
    client.run(config['auth']['token'])