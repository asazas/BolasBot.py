import asyncio

import discord

from discord.ext import commands

class Util(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
    
    @commands.command()
    async def countdown(self, ctx, count: int=10):
        count = min(count, 10)
        for i in range(count, 0, -1):
            await ctx.send(str(i))
            await asyncio.sleep(0.9)
        await ctx.send("GO!")
    
    @countdown.error
    async def countdown_error(self, ctx, error):
        err_file = discord.File("media/error.png")
        await ctx.reply("Se ha producido un error.", mention_author=False, file=err_file)