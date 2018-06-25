import asyncio
import os
import random
import re
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
        self.meta = {"USER": False, "CHANNEL": False}

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
    async def check(self, ctx, suggestion_id, *message):
        """Permet de répondre à une suggestion"""
        basemsg = ctx.message
        try:
            sug = await self.bot.get_message(ctx.message.channel, suggestion_id)
        except:
            rep = await self.bot.say("**Impossible** | La suggestion est introuvable")
            await asyncio.sleep(4)
            await self.bot.delete_message(rep)
            return
        sugem = sug.embeds[0]
        desc = "{}\n\n**Message de {}** — {}".format(sugem["description"], str(ctx.message.author), " ".join(message))
        em = discord.Embed(description=desc, color=sugem["color"])
        ftx = sugem["footer"]["text"]
        em.set_footer(text=ftx)
        await self.bot.edit_message(sug, embed=em)
        await self.bot.delete_message(basemsg)

    @commands.command(pass_context=True)
    async def suggest(self, ctx, *description):
        """Suggérer une idée au développeur

        [description] = La description de votre idée
        Note: Vous pouvez aussi upload une image en même temps que la commande pour illustrer votre idée si besoin"""
        desc = " ".join(description)
        if not 20 <= len(desc) <= 2000:
            await self.bot.say("**Erreur** | Votre suggestion doit faire entre *20* et *2000* caractères !\n"
                               "Faîtes `{}help suggest` pour obtenir de l'aide.".format(ctx.prefix))
            return
        attach = ctx.message.attachments
        if len(attach) > 1:
            await self.bot.say("**Erreur** | N'envoyez qu'un seul fichier !")
            return
        if attach:
            a = attach[0]
            url = a["url"]
        else:
            url = None
        channel = self.bot.get_channel("435023505520721922")
        em = discord.Embed(description=desc, color=ctx.message.author.color)
        if url:
            em.set_image(url=url)
        em.set_footer(text="— {} | Sur {}".format(str(ctx.message.author), self.bot.user.name))
        await self.bot.send_message(channel, embed=em)
        await self.bot.say("**Succès** | Votre suggestion a été envoyée !")

    @commands.command(pass_context=True, hidden=True)
    async def forcesuggest(self, ctx, user: discord.Member, *description):
        """Suggérer une idée au développeur au nom de quelqu'un d'autre

        <user> = Utilisateur
        [description] = La description de votre idée
        Note: Vous pouvez aussi upload une image en même temps que la commande pour illustrer votre idée si besoin"""
        desc = " ".join(description)
        if not 20 <= len(desc) <= 2000:
            await self.bot.say("**Erreur** | Votre suggestion doit faire entre *20* et *2000* caractères !\n"
                               "Faîtes `{}help suggest` pour obtenir de l'aide.".format(ctx.prefix))
            return
        attach = ctx.message.attachments
        if len(attach) > 1:
            await self.bot.say("**Erreur** | N'envoyez qu'un seul fichier !")
            return
        if attach:
            a = attach[0]
            url = a["url"]
        else:
            url = None
        channel = self.bot.get_channel("435023505520721922")
        em = discord.Embed(description=desc, color=user.color)
        if url:
            em.set_image(url=url)
        em.set_footer(text="— {} | Sur {}".format(str(user), self.bot.user.name))
        await self.bot.send_message(channel, embed=em)
        await self.bot.say("**Succès** | La suggestion a été envoyée !")

    @commands.command(pass_context=True, no_pm=True, hidden=True)
    async def metabot(self, ctx, channelid: str):
        """Prendre le contrôle du bot"""
        if channelid == "reset":
            if self.meta["CHANNEL"]:
                self.meta = {"USER": False, "CHANNEL": False}
            await self.bot.say("**Reset effectué**")
            return
        if ctx.message.channel.id != "456948766935875604":
            await self.bot.say("**Sécurité** | Cette commande n'est disponible que sur `meta-room`")
            return
        channel = self.bot.get_channel(channelid)
        if channel:
            if not self.meta["CHANNEL"]:
                em = discord.Embed(title="META | {}".format(channel.name),
                                   description="**Connexion établie** - Les messages provenant du salon seront copiés"
                                               " dans ce channel. Tout message que vous enverrez ici sera reproduit à "
                                               "l'identique sur ***{}***.\nLa session s'arrête automatiquement au"
                                               " bout de 5m d'inactivité. Vous seul pouvez utiliser cette session."
                                               "".format(channel.name))
                em.set_author(name=self.bot.user.name, icon_url=self.bot.user.avatar_url)
                await self.bot.say(embed=em)
                await asyncio.sleep(1.5)
                self.meta["CHANNEL"] = channel.id
                self.meta["USER"] = ctx.message.author.id
                while True:
                    msg = await self.bot.wait_for_message(channel=ctx.message.channel,
                                                          author=ctx.message.author, timeout=300)
                    if not msg or msg.content.lower() == "stop":
                        await self.bot.say("**Session terminée** | "
                                           "Ce channel n'est plus connecté à *{}*".format(channel.name))
                        self.meta = {"USER": False, "CHANNEL": False}
                        return
                    else:
                        if self.meta["CHANNEL"]:
                            if msg.content.startswith("\\"):
                                continue
                            await self.bot.send_message(channel, msg.content)
                        else:
                            await self.bot.say("**Session arrêtée à distance** | Ce channel n'est plus connecté à *{}*"
                                               "".format(channel.name))
                            self.meta = {"USER": False, "CHANNEL": False}
                            return
            else:
                await self.bot.say("**Erreur** | Une session est déjà en cours")
        else:
            await self.bot.say("**Erreur** | Le channel n'est pas valide/impossible à atteindre")

    async def listen_msg(self, message):
        if self.meta["CHANNEL"]:
            if message.channel.id == self.meta["CHANNEL"]:
                if message.author.id == "172376505354158080":
                    if message.content.lower().startswith("asimov"):
                        self.meta = {"USER": False, "CHANNEL": False}
                        return
                if "<@{}>".format(self.bot.user.id) in message.content:
                    color = 0xfab84c
                else:
                    color = message.author.color

                em = discord.Embed(description=message.content, color=color)
                em.set_author(name=message.author.name, icon_url=message.author.avatar_url)
                out = re.compile(r'(https?:\/\/(?:.*)\/\w*\.[A-z]*)',
                                 re.DOTALL | re.IGNORECASE).findall(message.content)
                if out:
                    out = out[0]
                    em.set_image(url=out)

                userchan = self.bot.get_channel("456948766935875604")
                await self.bot.send_message(userchan, embed=em)

    async def listen_typing(self, channel, user, when):
        if self.meta["CHANNEL"]:
            if channel.id == "456948766935875604":
                if user.id == self.meta["USER"]:
                    chan = self.bot.get_channel(self.meta["CHANNEL"])
                    await self.bot.send_typing(chan)


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
    bot.add_listener(n.listen_msg, "on_message")
    bot.add_listener(n.listen_typing, "on_typing")
    bot.add_cog(n)

