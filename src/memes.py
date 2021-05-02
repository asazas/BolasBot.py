from pathlib import Path
from random import randint

import discord

from discord.ext import commands


class Memes(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
    
    @commands.command()
    async def fernando(self, ctx):
        """
        Imagen aleatoria de Fernando Almeida.
        """
        image = discord.File("res/almeida{}.png".format(randint(0, 9)))
        await ctx.send(file=image)
    
    @fernando.error
    async def fernando_error(self, ctx, error):
        err_file = discord.File("res/almeida{}.png".format(randint(0, 3)))
        await ctx.reply("Se ha producido un error.", mention_author=False, file=err_file)