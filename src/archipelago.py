from random import randint

import requests

import discord

from discord.ext import commands
    

ENDPOINT = "https://archipelago.gg/api/generate"


class Archipelago(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
    
    @commands.command(aliases=["multi"])
    async def multiworld(self, ctx, *options):
        """
        Crea una partida de multiworld de ALTTPR.

        Requiere adjuntar un .zip incluyendo los ajustes de cada uno de los jugadores.

        Opciones extra:
         - spoiler: Hace que los spoiler logs de las seeds estén disponibles.
        """

        async with ctx.typing():
            if not ctx.message.attachments:
                raise commands.errors.CommandInvokeError("Se requiere un .zip con los ajustes de cada jugador.")
            
            my_zip = ctx.message.attachments[0]
            if not my_zip.content_type == "application/zip":
                raise commands.errors.CommandInvokeError("Se requiere un .zip con los ajustes de cada jugador.")
            
            settings = await my_zip.read()
            sent_file = {"file": ("multi.zip", settings)}

            payload = {"race": 1}

            if options and "spoiler" in options:
                payload["race"] = 0

            r = requests.post(ENDPOINT, data=payload, files=sent_file)

            if r.status_code == 201:
                game_url = eval(r.text)["url"]
                await ctx.reply(f"Partida de multiworld creada en: {game_url}", mention_author = False)
            else:
                raise commands.errors.CommandInvokeError("Error al generar la partida. Revisa que los ajustes de los jugadores sean válidos.")


    @multiworld.error
    async def multiworld_error(self, ctx, error):
        error_mes = "Se ha producido un error."
        if type(error) == commands.errors.CommandInvokeError:
            error_mes = error.original

        err_file = discord.File("res/almeida{}.png".format(randint(0, 3)))
        await ctx.reply(error_mes, mention_author=False, file=err_file)