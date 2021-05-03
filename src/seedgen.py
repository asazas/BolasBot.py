from pathlib import Path
import re
from random import randint

import yaml     # pip install pyyaml

import pyz3r    # pip install pyz3r

import discord

from discord.ext import commands


async def generate_from_yaml(yaml_contents, extra):
    settings_yaml = yaml.load(yaml_contents, Loader=yaml.FullLoader)
    if "spoiler" in extra:
        settings_yaml["settings"]["spoilers"] = True
    if "noqs" in extra:
        settings_yaml["settings"]["allow_quickswap"] = False
    if "pistas" in extra:
        settings_yaml["settings"]["hints"] = "on"
    if "ad" in extra:
        settings_yaml["settings"]["goal"] = "dungeons"
    if "mc" in extra:
        settings_yaml["settings"]["dungeon_items"] = "mc"
    if "hard" in extra:
        settings_yaml["settings"]["item"]["pool"] = "hard"
    seed = await pyz3r.alttpr(settings=settings_yaml['settings'], customizer=settings_yaml['customizer'])
    return seed


async def generate_from_attachment(attachment):
    seed = None

    file_contents = await attachment.read()
    seed = await generate_from_yaml(file_contents)
    
    return seed


async def generate_from_preset(preset):
    seed = None
    spoiler = False
    noqs = False
    pistas = False
    hard = False

    preset_name = preset[0]
    extra = preset[1:]

    if Path('rando-settings/{}.yaml'.format(preset_name)).is_file():         
        if extra:
            if "spoiler" in extra:
                spoiler = True
            if "noqs" in extra:
                noqs = True
            if "pistas" in extra:
                pistas = True
            if "hard" in extra:
                hard = True

        my_settings = ""
        with open("rando-settings/{}.yaml".format(preset_name), "r", encoding="utf-8") as settings_file:
            my_settings = settings_file.read()
        seed = await generate_from_yaml(my_settings, extra)
    
    return seed


async def generate_from_hash(my_hash):
    seed = await pyz3r.alttpr(hash_id=my_hash)
    return seed


def get_seed_data(seed):
    return "**URL: **{}\n**Hash: **{}".format(seed.url, " | ".join(seed.code))


def is_preset(preset):
    if Path('rando-settings/{}.yaml'.format(preset)).is_file():
        return True
    return False


class Seedgen(commands.Cog):
    def __init__(self, bot):
        self.bot = bot


    @commands.command()
    async def seed(self, ctx, *preset):
        """
        Crea una seed de ALTTPR.

        Requiere indicar un preset o adjuntar un YAML de ajustes. Si usas un preset, puedes añadir opciones extra.

        Opciones extra disponibles: spoiler, noqs, pistas, ad, mc, hard.

        Si introduces la URL de una seed ya creada, se devolverá su hash.
        """
        seed = None

        async with ctx.typing():
            if ctx.message.attachments:
                try:
                    seed = await generate_from_attachment(ctx.message.attachments[0])
                except:
                    raise commands.errors.CommandInvokeError("Error al generar la seed. Asegúrate de que el YAML introducido sea válido.")
            elif preset:
                if re.match(r'https://alttpr\.com/([a-z]{2}/)?h/\w{10}$', preset[0]):
                    seed_hash = (preset[0]).split('/')[-1]
                    seed = await generate_from_hash(seed_hash)
                else:
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
        
        err_file = discord.File("res/almeida{}.png".format(randint(0, 3)))
        await ctx.send(error_mes, file=err_file)

    
    @commands.command()
    async def preset(self, ctx, preset: str=""):
        """
        Información sobre presets.

        Usado sin parámetros, lista los presets disponibles. Añadiendo el nombre de un preset, da más detalles sobre el mismo.
        """
        msg = ""
        if not preset or not is_preset(preset):
            preset_files = sorted(Path("rando-settings").glob("*.yaml"))
            msg += "**Presets disponibles: **`"
            for i in range(len(preset_files)):
                msg += preset_files[i].stem
                if i != len(preset_files) - 1:
                    msg += ", "
            msg += "`"
        
        else:
            my_settings = ""
            with open("rando-settings/{}.yaml".format(preset), "r", encoding="utf-8") as settings_file:
                my_settings = settings_file.read()
                settings_yaml = yaml.load(my_settings, Loader=yaml.FullLoader)
                msg += "**{}**: {}".format(settings_yaml["goal_name"], settings_yaml["description"])
        
        await ctx.reply(msg, mention_author=False)

    
    @preset.error
    async def preset_error(self, ctx, error):
        error_mes = "Se ha producido un error."
        if type(error) == commands.errors.CommandInvokeError:
            error_mes = error.original
        
        err_file = discord.File("res/almeida{}.png".format(randint(0, 3)))
        await ctx.send(error_mes, file=err_file)
    

    @commands.command()
    async def yaml(self, ctx):
        """
        YAML de configuración de ALTTPR de ejemplo.

        Puede usarse de base para crear YAML personalizados.
        """
        my_yaml = discord.File("res/ejemplo.yaml")
        await ctx.send("Ejemplo de YAML de configuración de ALTTPR.", file=my_yaml)