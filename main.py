from configparser import ConfigParser
from pathlib import Path
import sqlite3

import yaml

from src.seedgen import Seedgen
from src.util import Util
from src.async_race import AsyncRace

from discord.ext import commands  # pip install discord.py

class BolasBot(commands.Bot):
    async def on_ready(self):
        print('Logged on as {0}!'.format(self.user))


if __name__ == "__main__":
    config = ConfigParser()
    config.read('config.ini')
    bot = BolasBot(command_prefix=config['commands']['prefix'])
    bot.add_cog(Seedgen(bot))
    bot.add_cog(Util(bot))
    bot.add_cog(AsyncRace(bot))

    Path('data').mkdir(parents=True, exist_ok=True)

    bot.run(config['auth']['token'])