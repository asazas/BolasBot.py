import re
from random import choice, randint

from src.seedgen import Seedgen
from src.db_utils import (write_lock, open_db, commit_db, close_db, insert_player_if_not_exists,
    insert_private_race, get_active_private_races) 

import discord
from discord.ext import commands


class Tourney(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
    

    @commands.command()
    async def torneoseed(self, ctx, *bans):
        """
        Crea una seed usando un preset de torneo al azar.

        Presets de torneo: ambrosia, casualboots, mc, open, standard, ad, keysanity.

        Si se especifican uno o más presets junto con el comando, estos NO se escogerán (presets baneados por jugadores).

        Si se especifica la palabra clave "ro16", se eliminarán los modos que no pueden ser escogidos en octavos de final (ad, keysanity)-
        """
        preset_list = ["ambrosia", "casualboots", "mc", "open", "standard", "ad", "keysanity"]
        if "ro16" in bans:
            preset_list.remove("ad")
            preset_list.remove("keysanity")
        for b in bans:
            if b in preset_list:
                preset_list.remove(b)
        await Seedgen.seed(self, ctx, choice(preset_list))

    
    @torneoseed.error
    async def torneoseed_error(self, ctx, error):
        error_mes = "Se ha producido un error."
        if type(error) == commands.errors.CommandInvokeError:
            if type(error.original) == IndexError:
                error_mes = "No queda ningún preset para elegir."
            else:
                error_mes = error.original
        
        err_file = discord.File("res/almeida{}.png".format(randint(0, 3)))
        await ctx.send(error_mes, file=err_file)
    

    @commands.command()
    @commands.guild_only()
    @commands.has_permissions(manage_channels=True)
    async def match(self, ctx, name: str, *players):
        """
        Abre un canal de texto para una carrera privada.

        Debe asignársele obligatoriamente un nombre.

        Tras el nombre, debe mencionarse a los jugadores o roles que participarán en la carrera. Si no se menciona a ninguno, únicamente el creador de la carrera tendrá acceso al canal.

        Este comando solo puede ser ejecutado por un moderador.
        """
        db_conn, db_cur = open_db(ctx.guild.id)
        
        creator = ctx.author

        # Comprobación de límite: máximo de 10 carreras privadas en el servidor
        races = get_active_private_races(db_cur)
        if races and len(races) >= 10:
            close_db(db_conn)
            raise commands.errors.CommandInvokeError("Demasiadas carreras activas en el servidor. Contacta a un moderador para purgar alguna.")

        # Comprobación de nombre válido
        if re.match(r'<@[!&]?\d{18}>', name):
            close_db(db_conn)
            raise commands.errors.CommandInvokeError("Es necesario introducir un nombre para la carrera.")
        
        if len(name) > 20:
            name = name[:20]
        
        # Obtener participantes de la carrera
        participants = [ctx.author]
        roles = []
        for p in players:
            mention = re.match(r'<@!?(\d{18})>', p)
            if mention:
                discord_id = int(mention.group(1))
                member = ctx.guild.get_member(discord_id)
                if member:
                    participants.append(member)
                continue
            mention = re.match(r'<@&(\d{18})>', p)
            if mention:
                role_id = int(mention.group(1))
                role = ctx.guild.get_role(role_id)
                if role:
                    roles.append(role)

        # Crear canal para la carrera
        channel_overwrites = {
            ctx.guild.default_role: discord.PermissionOverwrite(read_messages=False),
            ctx.guild.me: discord.PermissionOverwrite(read_messages=True)
        }
        for m in participants:
            channel_overwrites[m] = discord.PermissionOverwrite(read_messages=True)
        for r in roles:
            channel_overwrites[r] = discord.PermissionOverwrite(read_messages=True)

        race_channel = await ctx.guild.create_text_channel(name, overwrites=channel_overwrites)

        async with write_lock:    
            for p in participants:
                insert_player_if_not_exists(db_cur, p.id, p.name, p.discriminator, p.mention)
            insert_private_race(db_cur, name, creator.id, race_channel.id)
            commit_db(db_conn)

        close_db(db_conn)

        text_ans = 'Abierta carrera privada con nombre: {}\nCanal: {}'.format(name, race_channel.mention)

        await ctx.reply(text_ans, mention_author=False)


    @match.error
    async def match_error(self, ctx, error):
        error_mes = "Se ha producido un error."
        if type(error) == commands.errors.MissingRequiredArgument:
            error_mes = "Faltan argumentos para ejecutar el comando."
        elif type(error) == commands.errors.MissingPermissions:
            error_mes = "No tienes permiso para ejecutar este comando."
        elif type(error) == commands.errors.BadArgument:
            error_mes = "Argumentos inválidos."
        elif type(error) == commands.errors.CommandInvokeError:
            error_mes = error.original
        
        err_file = discord.File("res/almeida{}.png".format(randint(0, 3)))
        await ctx.reply(error_mes, mention_author=False, file=err_file)  
