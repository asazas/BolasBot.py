from pathlib import Path
import re
from random import randint, choice
from io import StringIO
from json import dumps

import yaml

import pyz3r

import discord

from discord.ext import commands


DUNGEON_CODES = {
    "H2": "H2-HyruleCastle",
    "A1": "A1-CastleTower",
    "P1": "P1-EasternPalace",
    "P2": "P2-DesertPalace",
    "P3": "P3-TowerOfHera",
    "D1": "D1-PalaceOfDarkness",
    "D2": "D2-SwampPalace",
    "D3": "D3-SkullWoods",
    "D4": "D4-ThievesTown",
    "D5": "D5-IcePalace",
    "D6": "D6-MiseryMire",
    "D7": "D7-TurtleRock",
    "A2": "A2-GanonsTower"
}


def get_seed_data(seed, preset=""):
    if not hasattr(seed, "randomizer"):     # VARIA randomizer
        if preset:
            return "**Preset: **{}\n**URL: **{}".format(preset, seed.url)
        return "**URL: **{}".format(seed.url)

    if seed.randomizer in ["sm", "smz3"]:
        code = " | ".join(seed.code.split())
    else:
        code = " | ".join(seed.code)

    if preset:
        return "**Preset: **{}\n**URL: **{}\n**Hash: **{}".format(preset, seed.url, code)
    return "**URL: **{}\n**Hash: **{}".format(seed.url, code)


def is_preset(preset):
    if list(Path('rando-settings').glob('*/{}.yaml'.format(preset))):
        return True
    return False


def add_default_customizer(settings_yaml):
    if "l" not in settings_yaml["settings"]:
        custom_settings = ""
        with open('res/default-customizer.yaml', "r", encoding="utf-8") as custom_file:
            custom_settings = custom_file.read()
        custom_yaml = yaml.load(custom_settings, Loader=yaml.FullLoader)
        settings_yaml["settings"] = {**settings_yaml["settings"], **custom_yaml}


async def generate_alttpr(settings_yaml, extra):
    if "spoiler" in extra:
        settings_yaml["settings"]["spoilers"] = "on"
    if "noqs" in extra:
        settings_yaml["settings"]["allow_quickswap"] = False
    if "pistas" in extra:
        settings_yaml["settings"]["hints"] = "on"
    if "ad" in extra:
        settings_yaml["settings"]["goal"] = "dungeons"
    if "hard" in extra:
        settings_yaml["settings"]["item"]["pool"] = "hard"
    if "botas" in extra:
        add_default_customizer(settings_yaml)
        settings_yaml['customizer'] = True
        if "PegasusBoots" not in settings_yaml['settings']['eq']:
            settings_yaml['settings']['eq'].append("PegasusBoots")
            if settings_yaml['settings']['custom']['item']['count']['PegasusBoots'] > 0:
                settings_yaml['settings']['custom']['item']['count']['PegasusBoots'] -= 1
                settings_yaml['settings']['custom']['item']['count']['TwentyRupees2'] += 1
    return await pyz3r.alttpr(settings=settings_yaml['settings'], customizer=settings_yaml['customizer'])


async def generate_sm(settings_yaml, extra):
    if "spoiler" in extra:
        settings_yaml["settings"]["race"] = "false"
    if "split" in extra:
        settings_yaml["settings"]["placement"] = "split"
    return await pyz3r.sm(settings=settings_yaml['settings'], randomizer="sm", baseurl='https://sm.samus.link')


async def generate_smz3(settings_yaml, extra):
    if "spoiler" in extra:
        settings_yaml["settings"]["race"] = "false"
    if "hard" in extra:
        settings_yaml["settings"]["smlogic"] = "hard"
    return await pyz3r.sm(settings=settings_yaml['settings'], randomizer="smz3")


async def generate_varia(settings_yaml, extra):
    return await pyz3r.smvaria.SuperMetroidVaria.create(**settings_yaml["settings"], race=True)


async def generate_from_yaml(yaml_contents, extra):
    settings_yaml = yaml.load(yaml_contents, Loader=yaml.FullLoader)
    if settings_yaml["randomizer"] == "alttp":
        return await generate_alttpr(settings_yaml, extra)
    elif settings_yaml["randomizer"] == "sm":
        return await generate_sm(settings_yaml, extra)
    elif settings_yaml["randomizer"] == "smz3":
        return await generate_smz3(settings_yaml, extra)
    elif settings_yaml["randomizer"] == "varia":
        return await generate_varia(settings_yaml, extra)
    return None


async def generate_from_attachment(attachment):
    file_contents = await attachment.read()
    return await generate_from_yaml(file_contents)


async def generate_from_preset(preset):
    preset_name = preset[0]
    extra = preset[1:]
    seed = None

    if is_preset(preset_name):
        my_settings = ""
        p_file = next(Path("rando-settings").rglob("{}.yaml".format(preset_name)))
        with open(p_file, "r", encoding="utf-8") as settings_file:
            my_settings = settings_file.read()
        seed = await generate_from_yaml(my_settings, extra)
    
    return seed


async def generate_from_hash(my_hash):
    seed = await pyz3r.alttpr(hash_id=my_hash)
    return seed


def get_spoiler(seed):
    spoiler_file = None
    if hasattr(seed, "get_formatted_spoiler"):
        spoiler_text = seed.get_formatted_spoiler()
        if spoiler_text:
            spoiler_dumps = dumps(spoiler_text, indent=4)
            for k, v in DUNGEON_CODES.items():
                spoiler_dumps = spoiler_dumps.replace(k, v)
            spoiler_io = StringIO(spoiler_dumps)
            spoiler_file = discord.File(spoiler_io, filename="spoiler.json", spoiler=True)
    return spoiler_file


class Seedgen(commands.Cog):
    def __init__(self, bot):
        self.bot = bot


    @commands.command()
    async def seed(self, ctx, *preset):
        """
        Crea una seed.

        Requiere indicar un preset o adjuntar un YAML de ajustes. Si usas un preset, puedes añadir opciones extra.

        Opciones extra disponibles para ALTTPR: 
         - spoiler: Hace que el spoiler log de la seed esté disponible.
         - noqs: Deshabilita quickswap.
         - pistas: Las casillas telepáticas pueden dar pistas sobre localizaciones de ítems.
         - ad: All Dungeons, Ganon solo será vulnerable al completar todas las mazmorras del juego, incluyendo Torre de Agahnim.
         - hard: Cambia el item pool a hard, reduciendo el número máximo de corazones, espadas e ítems de seguridad.
         - botas: Las Botas de Pegaso estarán equipadas al inicio de la partida.
        
        Opciones extra disponibles para SM:
         - spoiler: Hace que el spoiler log de la seed esté disponible.
         - split: Cambia el algoritmo de randomización a Major/Minor Split.
        
        Opciones extra disponibles para SMZ3:
         - spoiler: Hace que el spoiler log de la seed esté disponible.
         - hard: Establece la lógica de Super Metroid a Hard.

        Si introduces la URL de una seed de ALTTPR ya creada, se devolverá su hash y, si está disponible, su spoiler log.
        """
        seed = None
        preset_used = False

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
                    preset_used = True
            
        if seed:
            spoiler_file = get_spoiler(seed)
            if preset_used:
                await ctx.reply(get_seed_data(seed, " ".join(preset)), mention_author=False, file=spoiler_file)
            else:
                await ctx.reply(get_seed_data(seed), mention_author=False, file=spoiler_file)
        else:
            raise commands.errors.CommandInvokeError("Error al generar la seed. Asegúrate de que el preset o YAML introducido sea válido.")
    
    
    @seed.error
    async def seed_error(self, ctx, error):
        error_mes = "Se ha producido un error."
        if type(error) == commands.errors.CommandInvokeError:
            error_mes = error.original
        
        err_file = discord.File("res/almeida{}.png".format(randint(0, 3)))
        await ctx.send(error_mes, file=err_file)

    
    @commands.command(aliases=["presets"])
    async def preset(self, ctx, preset: str=""):
        """
        Información sobre presets.

        Usado sin parámetros, lista los presets disponibles. Añadiendo el nombre de un preset, da más detalles sobre el mismo.
        """
        msg = ""
        if not preset or not is_preset(preset):
            msg += "**Presets disponibles: **\n```"
            for folder in sorted(Path("rando-settings").iterdir()):
                msg += "{}:\n".format(folder.stem)
                preset_files = sorted(folder.glob("*.yaml"))
                for f in preset_files:
                    msg += " - {}\n".format(f.stem)
                msg += "\n"
            msg += "```"
        
        else:
            my_settings = ""
            p_file = next(Path("rando-settings").rglob("{}.yaml".format(preset)))
            with open(p_file, "r", encoding="utf-8") as settings_file:
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
    

    @commands.command(aliases=["random"])
    async def randomseed(self, ctx, *presets):
        """
        Crea una seed de ALTTPR usando un preset aleatorio.

        Usado sin parámetros, usará un preset aleatorio de entre todos los disponibles, sin usar modificadores.

        Si se da una lista de presets como parámetro, se seleccionará uno de ellos. Para usar un preset con modificadores, rodearlo entre comillas (ejemplo: "open spoiler").
        """
        if not presets:
            preset_list = []
            for preset_file in Path("rando-settings/alttp").iterdir():
                preset_list.append(preset_file.stem)
            await Seedgen.seed(self, ctx, choice(preset_list))
        else:
            preset_list = list(presets)
            while True:
                preset_choice = choice(preset_list)
                if is_preset(preset_choice.split()[0]):
                    await Seedgen.seed(self, ctx, *preset_choice.split())
                    break
                else:
                    preset_list.remove(preset_choice)

    
    @randomseed.error
    async def randomseed_error(self, ctx, error):
        error_mes = "Se ha producido un error."
        if type(error) == commands.errors.CommandInvokeError:
            if type(error.original) == IndexError:
                error_mes = "Ninguno de los presets dados es válido."
            else:
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