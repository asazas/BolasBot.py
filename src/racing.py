import re
from random import randint

import discord

from discord.ext import commands

from src.db_utils import (write_lock, open_db, commit_db, close_db, insert_player_if_not_exists,
    insert_async, get_async_by_submit, get_active_async_races, update_async_status, save_async_result,
    get_results_for_race, get_player_by_id, get_async_history_channel, set_async_history_channel,
    get_private_race_by_channel, update_private_status) 

from src.seedgen import generate_from_preset, generate_from_hash, generate_from_attachment, is_preset, get_spoiler


def get_results_text(db_cur, submit_channel):
    results = get_results_for_race(db_cur, submit_channel)
    msg = "```\n"
    msg += "+" + "-"*41 + "+\n"
    msg += "| Rk | Jugador           | Tiempo   | CR  |\n"
    
    if results:
        msg += "|" + "-" * 41 + "|\n"
        pos = 1
        for res in results:
            time_str = "Forfeit "
            if res[1] < 359999:
                m, s = divmod(res[1], 60)
                h, m = divmod(m, 60)
                time_str = "{:02d}:{:02d}:{:02d}".format(h, m, s)
            msg += "| {:2d} | {:17s} | {} | {:3d} |\n".format(pos, res[0][:17], time_str, res[2])
            pos += 1
    
    msg += "+" + "-"*41 + "+\n"
    msg += "```"
    return msg


def get_async_data(db_cur, submit_channel):
    my_async = get_async_by_submit(db_cur, submit_channel)
    player = get_player_by_id(db_cur, my_async[2])

    msg = "__**CARRERA ASÍNCRONA: {}**__\n".format(my_async[1])
    msg += "**Iniciada por: **{}\n".format(player[1])
    msg += "**Fecha de inicio (UTC): **{}\n".format(my_async[3])
    if my_async[4]:
        msg += "**Fecha de cierre (UTC): **{}\n".format(my_async[4])
    if my_async[6]:
        msg += "**Descripción: **{}\n".format(my_async[6])
    if my_async[9]:
        msg += "**Seed: **{}".format(my_async[9])
    if my_async[8]:
        msg += " ({})".format(my_async[8])
    
    return msg


def check_race_permissions(ctx, member_id, submit_id):
    auth_permissions = ctx.author.permissions_in(ctx.guild.get_channel(submit_id))
    if auth_permissions.manage_channels or ctx.author.id == member_id:
        return True    
    return False


    ########################################


class AsyncRace(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    
    @commands.command(aliases=["async", "blindasync"])
    @commands.guild_only()
    async def asyncstart(self, ctx, name: str, *preset):
        """
        Inicia una carrera asíncrona.

        Debe asignársele obligatoriamente un nombre.

        Tras el nombre se puede indicar un preset de ALTTPR, en cuyo caso se generará automáticamente una seed. También puede añadirse una descripción cualquiera.

        Este comando crea aleatoriamente los canales de Discord necesarios para alojar la carrera asíncrona.
        """
        db_conn, db_cur = open_db(ctx.guild.id)

        # Comprobación de límite: máximo de 10 asíncronas en el servidor
        asyncs = get_active_async_races(db_cur)
        if asyncs and len(asyncs) >= 10:
            close_db(db_conn)
            raise commands.errors.CommandInvokeError("Demasiadas asíncronas activas en el servidor. Contacta a un moderador para purgar alguna.")

        # Comprobación de nombre válido
        if re.match(r'https://alttpr\.com/([a-z]{2}/)?h/\w{10}$', name) or is_preset(name):
            close_db(db_conn)
            raise commands.errors.CommandInvokeError("El nombre de la carrera no puede ser un preset o una URL de seed.")
        
        if len(name) > 20:
            name = name[:20]

        # Crear o procesar seed
        seed = None
        seed_hash = None
        seed_code = None
        seed_url = None
        desc = " ".join(preset)
        spoiler_file = None

        async with ctx.typing():
            if ctx.message.attachments:
                attachment = ctx.message.attachments[0]
                try:
                    seed = await generate_from_attachment(attachment)
                except:
                    close_db(db_conn)
                    raise commands.errors.CommandInvokeError("Error al generar la seed. Asegúrate de que el YAML introducido sea válido.")

            elif preset:
                if re.match(r'https://alttpr\.com/([a-z]{2}/)?h/\w{10}$', preset[0]):
                    seed = await generate_from_hash((preset[0]).split('/')[-1])
                    if seed:
                        desc = " ".join(preset[1:])
                else:
                    seed = await generate_from_preset(preset)

        if seed:
            seed_url = seed.url
            if not hasattr(seed, "randomizer"):     # VARIA
                seed_hash = seed.data["seedKey"]
            elif seed.randomizer in ["sm", "smz3"]:
                seed_code = " | ".join(seed.code.split())
                seed_hash = seed.slug_id
            else:
                seed_code = " | ".join(seed.code)
                seed_hash = seed.hash
            spoiler_file = get_spoiler(seed)

        # Crear canales y rol para la async

        server = ctx.guild
        async_role = None
        res_overwrites = None
        spoiler_overwrites = None

        if ctx.invoked_with == "blindasync":
            res_overwrites = {
                server.default_role: discord.PermissionOverwrite(read_messages=False, send_messages=False),
                server.me: discord.PermissionOverwrite(read_messages=True, send_messages=True)
            }
            spoiler_overwrites = {
                server.default_role: discord.PermissionOverwrite(read_messages=False),
                server.me: discord.PermissionOverwrite(read_messages=True)
            }
        else:            
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

        results_text = get_results_text(db_cur, submit_channel.id)
        results_msg = await results_channel.send(results_text)
               
        creator = ctx.author
        async with write_lock:
            insert_player_if_not_exists(db_cur, creator.id, creator.name, creator.discriminator, creator.mention)
            if ctx.invoked_with == "blindasync":
                insert_async(db_cur, name, creator.id, desc, seed_hash, seed_code, seed_url, None,
                             submit_channel.id, results_channel.id, results_msg.id, spoilers_channel.id)
            else:
                insert_async(db_cur, name, creator.id, desc, seed_hash, seed_code, seed_url, async_role.id,
                             submit_channel.id, results_channel.id, results_msg.id, spoilers_channel.id)
            commit_db(db_conn)

        async_data = get_async_data(db_cur, submit_channel.id)
        close_db(db_conn)

        data_msg = await submit_channel.send(async_data, file=spoiler_file)
        await data_msg.pin()
        await submit_channel.send("Enviad resultados usando el comando: `!done hh:mm:ss CR`\n"
                                  "Por ejemplo: `!done 1:40:35 144`, `!done ff` (este último registra un forfeit)\n"
                                  "Usad preferiblemente tiempo real, no in-game time.\n"
                                  "Por favor, mantened este canal lo más limpio posible y SIN SPOILERS.")

        text_ans = 'Abierta carrera asíncrona con nombre: {}\nEnvía resultados en {}'.format(name, submit_channel.mention)

        await ctx.reply(text_ans, mention_author=False)


    @asyncstart.error
    async def asyncstart_error(self, ctx, error):
        error_mes = "Se ha producido un error."
        if type(error) == commands.errors.MissingRequiredArgument:
            error_mes = "Faltan argumentos para ejecutar el comando."
        elif type(error) == commands.errors.BadArgument:
            error_mes = "Argumentos inválidos."
        elif type(error) == commands.errors.CommandInvokeError:
            error_mes = error.original
        
        err_file = discord.File("res/almeida{}.png".format(randint(0, 3)))
        await ctx.reply(error_mes, mention_author=False, file=err_file)  


    ########################################


    @commands.command()
    @commands.guild_only()
    async def end(self, ctx):
        """
        Cierra una carrera asíncrona.

        Deja de aceptar nuevos resultados para la carrera asíncrona.

        Solo funciona en el canal "submit" asociado a la carrera, y solamente si lo usa el creador original de la carrera o un moderador.
        """
        db_conn, db_cur = open_db(ctx.guild.id)

        race = get_async_by_submit(db_cur, ctx.channel.id)

        if not race:
            close_db(db_conn)
            return

        if not check_race_permissions(ctx, race[2], race[11]):
            close_db(db_conn)
            raise commands.errors.CommandInvokeError("Esta operación solo puede realizarla el creador original de la carrera o un moderador.")

        if race[5] == 0:
            author = ctx.author
            async with write_lock:
                insert_player_if_not_exists(db_cur, author.id, author.name, author.discriminator, author.mention)
                update_async_status(db_cur, race[0], 1)
                commit_db(db_conn)

            close_db(db_conn)
            await ctx.reply("Esta carrera ha sido cerrada.", mention_author=False)
        else:
            close_db(db_conn)
            raise commands.errors.CommandInvokeError("Esta carrera no está abierta.")

    
    @end.error
    async def end_error(self, ctx, error):
        error_mes = "Se ha producido un error."
        if type(error) == commands.errors.MissingRequiredArgument:
            error_mes = "Faltan argumentos para ejecutar el comando."
        elif type(error) == commands.errors.BadArgument:
            error_mes = "Argumentos inválidos."
        elif type(error) == commands.errors.CommandInvokeError:
            error_mes = error.original
        
        err_file = discord.File("res/almeida{}.png".format(randint(0, 3)))
        await ctx.reply(error_mes, mention_author=False, file=err_file)  


    ########################################


    @commands.command()
    @commands.guild_only()
    async def reopen(self, ctx):
        """
        Reabre una carrera asíncrona.

        Comienza a aceptar de nuevo resultados para la carrera asíncrona.

        Solo funciona en el canal "submit" asociado a la carrera, y solamente si lo usa el creador original de la carrera o un moderador.
        """
        db_conn, db_cur = open_db(ctx.guild.id)

        race = get_async_by_submit(db_cur, ctx.channel.id)

        if not race:
            close_db(db_conn)
            return

        if not check_race_permissions(ctx, race[2], race[11]):
            close_db(db_conn)
            raise commands.errors.CommandInvokeError("Esta operación solo puede realizarla el creador original de la carrera o un moderador.")

        if race[5] == 1:
            author = ctx.author
            async with write_lock:
                insert_player_if_not_exists(db_cur, author.id, author.name, author.discriminator, author.mention)
                update_async_status(db_cur, race[0], 0)
                commit_db(db_conn)

            close_db(db_conn)
            await ctx.reply("Esta carrera ha sido reabierta.", mention_author=False)
        else:
            close_db(db_conn)
            raise commands.errors.CommandInvokeError("Esta carrera no está cerrada.")

    
    @reopen.error
    async def reopen_error(self, ctx, error):
        error_mes = "Se ha producido un error."
        if type(error) == commands.errors.MissingRequiredArgument:
            error_mes = "Faltan argumentos para ejecutar el comando."
        elif type(error) == commands.errors.BadArgument:
            error_mes = "Argumentos inválidos."
        elif type(error) == commands.errors.CommandInvokeError:
            error_mes = error.original
        
        err_file = discord.File("res/almeida{}.png".format(randint(0, 3)))
        await ctx.reply(error_mes, mention_author=False, file=err_file)  


    ########################################


    @commands.command()
    @commands.guild_only()
    async def purge(self, ctx):
        """
        Purga una carrera asíncrona.

        Elimina todos los roles y canales asociados a la carrera. Los resultados, si hay alguno, se archivarán en "async-historico"

        Solo funciona en el canal "submit" asociado a la carrera, y solamente si lo usa el creador original de la carrera o un moderador.

        También sirve para eliminar el canal asociado a una carrera privada.
        """
        db_conn, db_cur = open_db(ctx.guild.id)

        race = get_async_by_submit(db_cur, ctx.channel.id)

        if not race:
            race = get_private_race_by_channel(db_cur, ctx.channel.id)
            if race:
                if check_race_permissions(ctx, race[2], race[5]):
                    author = ctx.author
                    async with write_lock:
                        insert_player_if_not_exists(db_cur, author.id, author.name, author.discriminator, author.mention)
                        update_private_status(db_cur, race[0], 2)
                        commit_db(db_conn)

                    race_channel = ctx.guild.get_channel(race[5])
                    await race_channel.delete()
                else:
                    close_db(db_conn)
                    raise commands.errors.CommandInvokeError("Esta operación solo puede realizarla el creador original de la carrera o un moderador.")
            close_db(db_conn)
            return

        if not check_race_permissions(ctx, race[2], race[11]):
            close_db(db_conn)
            raise commands.errors.CommandInvokeError("Esta operación solo puede realizarla el creador original de la carrera o un moderador.")

        if race[5] == 1:
            author = ctx.author
            async with write_lock:
                insert_player_if_not_exists(db_cur, author.id, author.name, author.discriminator, author.mention)
                update_async_status(db_cur, race[0], 2)
                commit_db(db_conn)

            # Copia de resultados al historial, si los hay
            submit_channel = ctx.guild.get_channel(race[11])
            results = get_results_for_race(db_cur, submit_channel.id)
            if results:
                history_channel = get_async_history_channel(db_cur)
                my_hist_channel = None
                if not history_channel[0] or not ctx.guild.get_channel(history_channel[0]):
                    history_overwrites = {
                        ctx.guild.default_role: discord.PermissionOverwrite(send_messages=False),
                        ctx.guild.me: discord.PermissionOverwrite(send_messages=True)
                    }
                    my_hist_channel = await ctx.guild.create_text_channel("async-historico", overwrites=history_overwrites)
                    async with write_lock:
                        set_async_history_channel(db_cur, my_hist_channel.id)
                        commit_db(db_conn)
                else:
                    my_hist_channel = ctx.guild.get_channel(history_channel[0])

                await my_hist_channel.send(get_async_data(db_cur, submit_channel.id))
                await my_hist_channel.send(get_results_text(db_cur, submit_channel.id))

            # Eliminación de roles y canales            

            if race[10]:
                async_role = ctx.guild.get_role(race[10])
                await async_role.delete()

            category = submit_channel.category
            await submit_channel.delete()

            results_channel = ctx.guild.get_channel(race[12])
            await results_channel.delete()

            spoilers_channel = ctx.guild.get_channel(race[14])
            await spoilers_channel.delete()

            await category.delete()

            close_db(db_conn)
        
        else:
            close_db(db_conn)
            raise commands.errors.CommandInvokeError("La carrera debe cerrarse antes de ser purgada.")


    @purge.error
    async def purge_error(self, ctx, error):
        error_mes = "Se ha producido un error."
        if type(error) == commands.errors.MissingRequiredArgument:
            error_mes = "Faltan argumentos para ejecutar el comando."
        elif type(error) == commands.errors.BadArgument:
            error_mes = "Argumentos inválidos."
        elif type(error) == commands.errors.CommandInvokeError:
            error_mes = error.original
        
        err_file = discord.File("res/almeida{}.png".format(randint(0, 3)))
        await ctx.reply(error_mes, mention_author=False, file=err_file) 


    ########################################


    @commands.command(aliases=["forfeit", "ff"])
    @commands.guild_only()
    async def done(self, ctx, time: str="", collection: int=0):
        """
        Envía un resultado de la carrera asíncrona.

        Requiere indicar un tiempo en formato hh:mm:ss. Opcionalmente, se puede especificar la tasa de colección de ítems para ALTTPR.

        Para registrar un forfeit, introducir FF en lugar del tiempo.

        Solo funciona en el canal "submit" asociado a la carrera. Un segundo comando "done" del mismo jugador reemplazará el resultado anterior.
        """
        message = ctx.message
        await message.delete()
       
        db_conn, db_cur = open_db(ctx.guild.id)

        race = get_async_by_submit(db_cur, ctx.channel.id)

        if not race:
            close_db(db_conn)
            return

        if race[5] == 0:
            if ctx.invoked_with == "forfeit" or ctx.invoked_with == "ff" or time.lower() == "ff":
                time = "99:59:59"
                collection = 0
            if re.match(r'\d?\d:[0-5]\d:[0-5]\d$', time) and collection >= 0:
                time_arr = [int(x) for x in time.split(':')]
                time_s = 3600*time_arr[0] + 60*time_arr[1] + time_arr[2]
                
                author = ctx.author
                async with write_lock:
                    insert_player_if_not_exists(db_cur, author.id, author.name, author.discriminator, author.mention)
                    save_async_result(db_cur, race[0], author.id, time_s, collection)
                    commit_db(db_conn)

                results_text = get_results_text(db_cur, race[11])
                results_channel = ctx.guild.get_channel(race[12])
                results_msg = await results_channel.fetch_message(race[13])
                await results_msg.edit(content=results_text)

                if race[10]:
                    async_role = ctx.guild.get_role(race[10])
                    await author.add_roles(async_role)
                    
                await ctx.send("GG {}, tu resultado se ha registrado.".format(author.mention))
        
            else:
                close_db(db_conn)
                raise commands.errors.CommandInvokeError("Parámetros inválidos.")
        
        else:
            close_db(db_conn)
            raise commands.errors.CommandInvokeError("Esta carrera asíncrona no está abierta.")
        
        close_db(db_conn)


    @done.error
    async def done_error(self, ctx, error):
        error_mes = "Se ha producido un error."
        if type(error) == commands.errors.MissingRequiredArgument:
            message = ctx.message
            await message.delete()
            error_mes = "Faltan argumentos para ejecutar el comando."
        elif type(error) == commands.errors.BadArgument:
            message = ctx.message
            await message.delete()
            error_mes = "Argumentos inválidos."
        elif type(error) == commands.errors.CommandInvokeError:
            error_mes = error.original
        
        err_file = discord.File("res/almeida{}.png".format(randint(0, 3)))
        await ctx.send(error_mes, file=err_file)
