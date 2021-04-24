# pylint: disable=import-error

import re

import discord

from discord.ext import commands

from src.db_utils import (open_db, commit_and_close_db, insert_player_if_not_exists,
    insert_async, get_async_by_name, update_async_status, save_async_result) 

from src.seedgen import generate_from_preset, generate_from_hash

class AsyncRace(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    
    @commands.command()
    @commands.guild_only()
    async def async_start(self, ctx, name: str, url_or_preset: str):
        db_conn, db_cur = open_db(ctx.guild.id)

        if len(name) > 20:
            name = name[:20]
        
        creator = ctx.author
        insert_player_if_not_exists(db_cur, creator.id, creator.name, creator.discriminator, creator.mention)

        # Crear o procesar seed
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

        # Crear canales y rol para la async

        server = ctx.guild

        async_role = await server.create_role(name=name)
        channel_overwrites = {
            server.default_role: discord.PermissionOverwrite(read_messages=False),
            server.me: discord.PermissionOverwrite(read_messages=True),
            async_role: discord.PermissionOverwrite(read_messages=True)
        }

        async_category = await server.create_category_channel(name, overwrites=channel_overwrites)
        results_channel = await server.create_text_channel("{}-results".format(name), category=async_category)
        spoilers_channel = await server.create_text_channel("{}-spoilers".format(name), category=async_category)

        results_msg = await results_channel.send("MENSAJE DE RESULTADOS")
               
        insert_async(db_cur, name, creator.id, seed_hash, seed_url, async_role.id,
                     results_channel.id, results_msg.id, spoilers_channel.id)

        commit_and_close_db(db_conn)

        text_ans = 'Abierta carrera asíncrona con nombre: {}\nSeed: {}'.format(name, seed_url)
        if seed:
            text_ans += '\nHash: ' + ' | '.join(seed.code)

        await ctx.reply(text_ans, mention_author=False)


    @commands.command()
    @commands.guild_only()
    async def async_end(self, ctx, name: str):
        db_conn, db_cur = open_db(ctx.guild.id)

        race = get_async_by_name(db_cur, name)
        if race:
            update_async_status(db_cur, race[0], 1)

        commit_and_close_db(db_conn)


    @commands.command()
    @commands.guild_only()
    async def async_purge(self, ctx, name: str):
        db_conn, db_cur = open_db(ctx.guild.id)

        race = get_async_by_name(db_cur, name)
        if race and race[4] == 1:
            update_async_status(db_cur, race[0], 2)

            async_role = ctx.guild.get_role(race[7])
            await async_role.delete()

            results_channel = ctx.guild.get_channel(race[8])
            category = results_channel.category
            await results_channel.delete()

            spoilers_channel = ctx.guild.get_channel(race[10])
            await spoilers_channel.delete()

            await category.delete()
        
        commit_and_close_db(db_conn)


    @commands.command()
    @commands.guild_only()
    async def async_done(self, ctx, race: str, time: str, collection: int):
        db_conn, db_cur = open_db(ctx.guild.id)

        message = ctx.message
        await message.delete()

        race = get_async_by_name(db_cur, race)
        if race and race[4] == 0:
            save_async_result(db_cur, ctx.author)
            await ctx.reply("Hecho.", mention_author=False)
        
        commit_and_close_db(db_conn)


    @async_done.error
    async def async_done_error(self, ctx, error):
        err_file = discord.File("media/error.png")
        await ctx.reply("Se ha producido un error.", mention_author=False, file=err_file)
        