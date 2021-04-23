# pylint: disable=import-error

import re

import discord

from discord.ext import commands

from src.db_utils import (insert_player_if_not_exists, insert_async,
    get_db_for_server, save_async_result) 

from src.seedgen import generate_from_preset, generate_from_hash

class AsyncRace(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    
    @commands.command()
    async def async_start(self, ctx, name: str, url_or_preset: str):
        my_db = get_db_for_server(ctx.guild.id)
        
        creator = ctx.author
        insert_player_if_not_exists(my_db, creator.id, creator.name, creator.discriminator, creator.mention)

        seed = None
        seed_hash = None
        seed_url = url_or_preset

        if re.match(r'https://alttpr\.com/h/\w*$', url_or_preset):
            seed_hash = url_or_preset.split('/')
            seed = await generate_from_hash(seed_hash)
        else:
            seed = await generate_from_preset(url_or_preset)
            if seed:
                seed_hash = seed.hash
                seed_url = seed.url
               
        insert_async(my_db, name, creator.id, seed_hash, seed_url)

        text_ans = 'Abierta carrera asíncrona con nombre: {}\nSeed: {}'.format(name, seed_url)
        if seed:
            text_ans += '\nHash: ' + ' | '.join(seed.code)

        await ctx.reply(text_ans, mention_author=False)




    @commands.command()
    @commands.has_permissions(manage_channels=True)
    async def async_done(self, ctx):
        my_db = get_db_for_server(ctx.guild.id)

        save_async_result(my_db, ctx.author)
        await ctx.reply("Hecho.", mention_author=False)
    
    @async_done.error
    async def async_done_error(self, ctx, error):
        err_file = discord.File("media/error.png")
        await ctx.reply("Se ha producido un error.", mention_author=False, file=err_file)
        