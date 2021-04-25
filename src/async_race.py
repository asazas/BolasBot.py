# pylint: disable=import-error

import re
import time

import discord

from discord.ext import commands

from src.db_utils import (open_db, commit_db, close_db, insert_player_if_not_exists,
    insert_async, get_async_by_name, get_async_by_submit, update_async_status, save_async_result,
    get_results_for_race, get_player_by_id) 

from src.seedgen import generate_from_preset, generate_from_hash, generate_from_yaml


class BadAsyncError(Exception):
    pass


def get_results_text(db_cur, name):
    results = get_results_for_race(db_cur, name)
    msg = "```\n"
    msg += "+" + "-"*47 + "+\n"
    msg += "| Pos. | Jugador              | Tiempo   | Col. |\n"
    
    pos = 1
    for res in results:
        m, s = divmod(res[1], 60)
        h, m = divmod(m, 60)
        time_str = "{:02d}:{:02d}:{:02d}".format(h, m, s)
        msg += "|" + "-" * 47 + "|\n"
        msg += "| {:4d} | {:20s} | {} | {:4d} |\n".format(pos, res[0], time_str, res[2])
        pos += 1
    
    msg += "+" + "-"*47 + "+\n"
    msg += "```"
    return msg


def get_async_data(db_cur, name):
    my_async = get_async_by_name(db_cur, name)
    player = get_player_by_id(db_cur, my_async[2])

    msg = "__**CARRERA ASÍNCRONA: {}**__\n".format(my_async[1])
    msg += "**Abierta por: **{}\n".format(player[1])
    msg += "**Fecha de inicio (UTC): **{}\n".format(my_async[3])
    msg += "**Seed: **{}".format(my_async[7])
    if my_async[6]:
        msg += " ({})".format(my_async[6])
    
    return msg


class AsyncRace(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    
    @commands.command()
    @commands.guild_only()
    async def async_start(self, ctx, name: str, url_or_preset: str=""):
        db_conn, db_cur = open_db(ctx.guild.id)

        if len(name) > 20:
            name = name[:20]
        
        creator = ctx.author
        insert_player_if_not_exists(db_cur, creator.id, creator.name, creator.discriminator, creator.mention)

        if get_async_by_name(db_cur, name):
            close_db(db_conn)
            raise Exception("Ya hay registrada una carrera asíncrona con ese nombre.")


        # Crear o procesar seed
        seed = None
        seed_hash = None
        seed_code = None
        seed_url = url_or_preset

        if ctx.message.attachments:
            my_settings = await (ctx.message.attachments[0]).read()
            seed = await generate_from_yaml(my_settings)
        elif re.match(r'https://alttpr\.com/h/\w*$', url_or_preset):
            seed_hash = url_or_preset.split('/')
            seed = await generate_from_hash(seed_hash)
        else:
            seed = await generate_from_preset(url_or_preset)

        if seed:
            seed_hash = seed.hash
            seed_url = seed.url
            seed_code = " | ".join(seed.code)

        # Crear canales y rol para la async

        server = ctx.guild

        async_role = await server.create_role(name=name)
        res_overwrites = {
            server.default_role: discord.PermissionOverwrite(read_messages=False, send_messages=False),
            server.me: discord.PermissionOverwrite(read_messages=True, send_messages=True),
            async_role: discord.PermissionOverwrite(read_messages=True)
        }
        spoiler_overwrites = {
            server.default_role: discord.PermissionOverwrite(read_messages=False),
            server.me: discord.PermissionOverwrite(read_messages=True),
            async_role: discord.PermissionOverwrite(read_messages=True)
        }

        async_category = await server.create_category_channel(name)
        submit_channel = await server.create_text_channel("{}-submit".format(name), category=async_category)
        results_channel = await server.create_text_channel("{}-results".format(name), category=async_category, overwrites=res_overwrites)
        spoilers_channel = await server.create_text_channel("{}-spoilers".format(name), category=async_category, overwrites=spoiler_overwrites)

        results_text = get_results_text(db_cur, name)
        results_msg = await results_channel.send(results_text)
               
        insert_async(db_cur, name, creator.id, seed_hash, seed_code, seed_url, async_role.id,
                     submit_channel.id, results_channel.id, results_msg.id, spoilers_channel.id)

        commit_db(db_conn)
        async_data = get_async_data(db_cur, name)
        close_db(db_conn)

        data_msg = await submit_channel.send(async_data)
        await data_msg.pin()

        text_ans = 'Abierta carrera asíncrona con nombre: {}\nEnvía resultados en {}'.format(name, submit_channel.mention)

        await ctx.reply(text_ans, mention_author=False)


    @commands.command()
    @commands.guild_only()
    async def end(self, ctx):
        db_conn, db_cur = open_db(ctx.guild.id)

        author = ctx.author
        insert_player_if_not_exists(db_cur, author.id, author.name, author.discriminator, author.mention)

        race = get_async_by_submit(db_cur, ctx.channel.id)
        if race:
            update_async_status(db_cur, race[0], 1)
            commit_db(db_conn)
            close_db(db_conn)
        else:
            close_db(db_conn)


    @commands.command()
    @commands.guild_only()
    async def purge(self, ctx):
        db_conn, db_cur = open_db(ctx.guild.id)

        author = ctx.author
        insert_player_if_not_exists(db_cur, author.id, author.name, author.discriminator, author.mention)

        race = get_async_by_submit(db_cur, ctx.channel.id)
        if race and race[4] == 1:
            update_async_status(db_cur, race[0], 2)

            async_role = ctx.guild.get_role(race[8])
            await async_role.delete()

            submit_channel = ctx.guild.get_channel(race[9])
            category = submit_channel.category
            await submit_channel.delete()

            results_channel = ctx.guild.get_channel(race[10])
            await results_channel.delete()

            spoilers_channel = ctx.guild.get_channel(race[12])
            await spoilers_channel.delete()

            await category.delete()
            
            commit_db(db_conn)
            close_db(db_conn)
        
        else:
            close_db(db_conn)


    @commands.command()
    @commands.guild_only()
    async def done(self, ctx, time: str, collection: int=0):
        db_conn, db_cur = open_db(ctx.guild.id)

        author = ctx.author
        insert_player_if_not_exists(db_cur, author.id, author.name, author.discriminator, author.mention)

        race = get_async_by_submit(db_cur, ctx.channel.id)
        if race and race[4] == 0:
            if re.match(r'^\d?\d:[0-5]\d:[0-5]\d$', time):
                time_arr = [int(x) for x in time.split(':')]
                time_s = 3600*time_arr[0] + 60*time_arr[1] + time_arr[2]
                save_async_result(db_cur, race[0], author.id, time_s, collection)

                message = ctx.message
                await message.delete()

                results_text = get_results_text(db_cur, race[1])
                results_channel = ctx.guild.get_channel(race[10])
                results_msg = await results_channel.fetch_message(race[11])
                await results_msg.edit(content=results_text)

                await ctx.send("GG {}, tu resultado se ha registrado.".format(author.mention))
                async_role = ctx.guild.get_role(race[8])
                await author.add_roles(async_role)
        
            else:
                close_db(db_conn)
                raise commands.errors.BadArgument("Tiempo inválido.")
        
        else:
            close_db(db_conn)
            raise commands.errors.CommandInvokeError("La carrera asíncrona indicada no está abierta.")
        
        commit_db(db_conn)
        close_db(db_conn)


    @done.error
    async def done_error(self, ctx, error):
        message = ctx.message
        await message.delete()

        error_mes = "Se ha producido un error."
        if type(error) == commands.errors.MissingRequiredArgument:
            error_mes = "Faltan argumentos para ejecutar el comando."
        elif type(error) == commands.errors.BadArgument:
            error_mes = "Argumentos inválidos."
        elif type(error) == commands.errors.CommandInvokeError:
            error_mes = "La carrera asíncrona indicada no está abierta."
        
        err_file = discord.File("media/error.png")
        await ctx.send(error_mes, mention_author=False, file=err_file)
        