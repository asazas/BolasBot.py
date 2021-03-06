from configparser import ConfigParser
from pathlib import Path

import logging

from src.seedgen import Seedgen
from src.util import Util
from src.racing import AsyncRace
from src.memes import Memes
from src.tourney import Tourney
from src.archipelago import Archipelago

import discord
from discord.ext import commands

class BolasBot(commands.Bot):
    async def on_ready(self):
        print('Logged in as {0}!'.format(self.user))


if __name__ == "__main__":
    Path('log').mkdir(parents=True, exist_ok=True)
    logger = logging.getLogger('discord')
    handler = logging.FileHandler(filename="log/discord.log", encoding="utf-8", mode="w")
    handler.setFormatter(logging.Formatter('%(asctime)s:%(levelname)s:%(name)s: %(message)s'))
    logger.addHandler(handler)

    intents = discord.Intents.default()
    intents.members = True
    config = ConfigParser()
    config.read('config.ini')
    bot = BolasBot(command_prefix=config['commands']['prefix'], intents=intents)
    bot.add_cog(Seedgen(bot))
    bot.add_cog(Util(bot))
    bot.add_cog(AsyncRace(bot))
    bot.add_cog(Memes(bot))
    bot.add_cog(Tourney(bot))
    bot.add_cog(Archipelago(bot))

    Path('data').mkdir(parents=True, exist_ok=True)

    bot.run(config['auth']['token'])