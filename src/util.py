import asyncio
from random import randint

import discord

from discord.ext import commands

class Util(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
    
    @commands.command()
    async def countdown(self, ctx, count: int=10):
        """
        Inicia una cuenta atrás.

        Se puede especificar el valor de inicio. Por defecto, es 10. Este valor es también el máximo.
        """
        count = min(abs(count), 10)
        for i in range(count, 0, -1):
            await ctx.send(str(i))
            await asyncio.sleep(0.8)
        await ctx.send("GO!")
    
    @countdown.error
    async def countdown_error(self, ctx, error):
        err_file = discord.File("res/almeida{}.png".format(randint(0, 3)))
        await ctx.reply("Se ha producido un error.", mention_author=False, file=err_file)
