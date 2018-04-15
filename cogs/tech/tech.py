import asyncio
import os
import random
import re
import aiohttp
import zipfile

import discord
from discord.ext import commands

from .utils import checks
from .utils.dataIO import fileIO, dataIO


class Tech:
    """Module d'outils techniques de maintenance et de fonctionnalités diverses liées"""
    def __init__(self, bot):
        self.bot = bot
        self.sys = dataIO.load_json("data/tech/sys.json")  # Pas très utile mais on le garde pour plus tard

    def make_zipfile(self, output_filename, source_dir):
        relroot = os.path.abspath(os.path.join(source_dir, os.pardir))
        with zipfile.ZipFile(output_filename, "w", zipfile.ZIP_DEFLATED) as zip:
            for root, dirs, files in os.walk(source_dir):
                zip.write(root, os.path.relpath(root, relroot))
                for file in files:
                    filename = os.path.join(root, file)
                    if os.path.isfile(filename):
                        arcname = os.path.join(os.path.relpath(root, relroot), file)
                        zip.write(filename, arcname)

    @commands.command(pass_context=True)
    @checks.admin_or_permissions(manage_server=True)
    async def zip_file(self, ctx, chemin):
        """Permet de zipper un ensemble de fichiers et de le télécharger"""
        al = random.randint(0, 999)
        output = "data/tech/crap/zipped_{}.zip".format(al)
        await self.bot.say("**Compression** | Veuillez patienter...")
        self.make_zipfile(output, chemin)
        await asyncio.sleep(1)
        await self.bot.say("**Upload** | Votre fichier est bientôt prêt...")
        try:
            await self.bot.send_file(ctx.message.channel, output)
            os.remove(output)
        except:
            await self.bot.say("**Erreur** | Impossible d'upload votre fichier.\n"
                               "Le fichier est probablement trop lourd pour être téléchargé depuis Discord.")

    @commands.command(pass_context=True)
    @checks.admin_or_permissions(manage_server=True)
    async def get_file(self, ctx, chemin):
        """Permet de télécharger un unique fichier data du bot"""
        try:
            await self.bot.say("**Upload** | Veuillez patienter...")
            await self.bot.send_file(ctx.message.channel, chemin)
        except:
            await self.bot.say("**Erreur** | Impossible d'upload votre fichier.\n"
                               "Le fichier est probablement trop lourd pour être téléchargé depuis Discord.")

    @commands.command(pass_context=True)
    async def suggest(self, ctx, *description):
        """Suggérer une idée au développeur

        [description] = La description de votre idée
        Note: Vous pouvez aussi upload une image en même temps que la commande pour illustrer votre idée si besoin"""
        attach = ctx.message.attachments
        if len(attach) > 1:
            await self.bot.say("**Erreur** | N'envoyez qu'un seul fichier !")
            return
        if attach:
            a = attach[0]
            url = a["url"]
        else:
            url = None
        desc = " ".join(description)
        channel = self.bot.get_channel("435023505520721922")
        em = discord.Embed(description=desc, color=ctx.message.author.color)
        if url:
            em.set_image(url=url)
        em.set_footer(text="— {}".format(str(ctx.message.author)))
        await self.bot.send_message(channel, embed=em)
        await self.bot.say("**Succès** | Votre suggestion a été envoyée !")

def check_folders():
    if not os.path.exists("data/tech"):
        print("Creation du fichier Tech ...")
        os.makedirs("data/tech")
    if not os.path.exists("data/tech/crap"):
        print("Creation du fichier Tech/crap ...")
        os.makedirs("data/tech/crap")  # Pour toute la merde que ce module va créer, notamment en logs...

def check_files():
    if not os.path.isfile("data/tech/sys.json"):
        print("Création de tech/sys.json ...")
        fileIO("data/tech/sys.json", "save", {})

def setup(bot):
    check_folders()
    check_files()
    n = Tech(bot)
    bot.add_cog(n)
