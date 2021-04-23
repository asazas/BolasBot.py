from pathlib import Path

import yaml     # pip install pyyaml

import pyz3r    # pip install pyz3r

import discord

from discord.ext import commands


async def generate_from_preset(preset):

    seed = None

    if Path('rando-settings/{}.yaml'.format(preset)).is_file():
        my_settings = ""
        with open("rando-settings/{}.yaml".format(preset), "r") as settings_file:
            my_settings = settings_file.read()
        
        settings_yaml = yaml.load(my_settings, Loader=yaml.FullLoader)
        seed = await pyz3r.alttpr(settings=settings_yaml['settings'])
    
    return seed


async def generate_from_hash(my_hash):
    seed = await pyz3r.alttpr(hash_id=my_hash)
    return seed


class Seedgen(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
   
    @commands.command()
    async def crea_seed(self, ctx, preset: str=""):

        my_settings = ""

        if ctx.message.attachments:
            my_settings = await (ctx.message.attachments[0]).read()
        
        if preset:
            with open("rando-settings/{}.yaml".format(preset), "r") as settings_file:
                my_settings = settings_file.read()
        
        settings_yaml = yaml.load(my_settings, Loader=yaml.FullLoader)
        seed = await pyz3r.alttpr(settings=settings_yaml['settings'])
        await ctx.reply(seed.url, mention_author=False)

    
    @crea_seed.error
    async def crea_seed_error(self, ctx, error):
        err_file = discord.File("media/error.png")
        await ctx.reply("Se ha producido un error.", mention_author=False, file=err_file)
        
