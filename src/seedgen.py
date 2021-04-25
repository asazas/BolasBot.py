from pathlib import Path

import yaml     # pip install pyyaml

import pyz3r    # pip install pyz3r

import discord

from discord.ext import commands


async def generate_from_yaml(yaml_contents):
    settings_yaml = yaml.load(yaml_contents, Loader=yaml.FullLoader)
    seed = await pyz3r.alttpr(settings=settings_yaml['settings'], customizer=settings_yaml['customizer'])
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


class Seedgen(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
   
    @commands.command()
    async def seed(self, ctx, preset: str=""):
        """
        Crea una seed probablemente horrible.
        """
        my_settings = ""

        if ctx.message.attachments:
            my_settings = await (ctx.message.attachments[0]).read()
            seed = await generate_from_yaml(my_settings)
        
        elif preset:
            seed = await generate_from_preset(preset)
        
        if seed:
            await ctx.reply(seed.url, mention_author=False)
        else:
            await ctx.reply("Error al generar la seed.", mention_author=False,
                            file=discord.File("media/error.png"))

    
    @seed.error
    async def seed_error(self, ctx, error):
        await ctx.reply("Se ha producido un error.", mention_author=False,
                        file=discord.File("media/error.png"))
        
