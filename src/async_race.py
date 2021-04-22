from pathlib import Path

import discord

from discord.ext import commands

from src.db_utils import init_db, save_async_result # pylint: disable=import-error

class AsyncRace(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
   
    @commands.command()
    @commands.has_permissions(manage_channels=True)
    async def async_done(self, ctx):
        guild_id = ctx.guild.id
        my_db = 'data/{}.db'.format(guild_id)
        if not Path(my_db).is_file():
            init_db(my_db)
        
        save_async_result(my_db, ctx.author)
        await ctx.reply("Hecho.", mention_author=False)

    
    @async_done.error
    async def async_done_error(self, ctx, error):
        err_file = discord.File("media/error.png")
        await ctx.reply("Se ha producido un error.", mention_author=False, file=err_file)
        