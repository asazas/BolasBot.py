from pathlib import Path

import yaml     # pip install pyyaml

import pyz3r    # pip install pyz3r

import discord

from discord.ext import commands


async def generate_from_yaml(yaml_contents):
    settings_yaml = yaml.load(yaml_contents, Loader=yaml.FullLoader)
    seed = await pyz3r.alttpr(settings=settings_yaml['settings'], customizer=settings_yaml['customizer'])
    return seed


async def generate_from_attachment(attachment):
    seed = None

    file_contents = await attachment.read()
    seed = await generate_from_yaml(file_contents)
    
    return seed


async def generate_from_preset(preset):
    seed = None

    if Path('rando-settings/{}.yaml'.format(preset)).is_file():
        my_settings = ""
        with open("rando-settings/{}.yaml".format(preset), "r") as settings_file:
            my_settings = settings_file.read()
        
        seed = await generate_from_yaml(my_settings)
    
    return seed


async def generate_from_hash(my_hash):
    seed = await pyz3r.alttpr(hash_id=my_hash)
    return seed


def get_seed_data(seed):
    return "**URL: **{}\n**Hash: **{}".format(seed.url, " | ".join(seed.code))


class Seedgen(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
   
    @commands.command()
    async def seed(self, ctx, preset: str=""):
        """
        Crea una seed probablemente horrible.
        """
        seed = None

        if ctx.message.attachments:
            try:
                seed = await generate_from_attachment(ctx.message.attachments[0])
            except:
                raise commands.errors.CommandInvokeError("Error al generar la seed. Asegúrate de que el YAML introducido sea válido.")
        elif preset:
            seed = await generate_from_preset(preset)
        
        if seed:
            await ctx.reply(get_seed_data(seed), mention_author=False)
        else:
            raise commands.errors.CommandInvokeError("Error al generar la seed. Asegúrate de que el preset o YAML introducido sea válido.")

    
    @seed.error
    async def seed_error(self, ctx, error):
        error_mes = "Se ha producido un error."
        if type(error) == commands.errors.CommandInvokeError:
            error_mes = error.original
        
        err_file = discord.File("media/error.png")
        await ctx.send(error_mes, file=err_file)
        
