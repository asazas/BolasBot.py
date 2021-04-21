from configparser import ConfigParser

import yaml

from seedgen import Seedgen

from discord.ext import commands  # pip install discord.py

class BolasBot(commands.Bot):
    async def on_ready(self):
        print('Logged on as {0}!'.format(self.user))


if __name__ == "__main__":
    config = ConfigParser()
    config.read('config.ini')
    bot = BolasBot(command_prefix=config['commands']['prefix'])
    bot.add_cog(Seedgen(bot))
    bot.run(config['auth']['token'])