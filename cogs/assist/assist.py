import os
import re
from copy import deepcopy

import discord
import wikipedia
from __main__ import send_cmd_help
from discord.ext import commands
from sympy import sympify

from .utils import checks
from .utils.dataIO import fileIO, dataIO


class Assist:
    """Assistant intelligent en langage naturel & fonctionnalités à l'écrit"""
    def __init__(self, bot):
        self.bot = bot
        self.sys = dataIO.load_json("data/assist/sys.json")
        self.def_sys = {"ASSIST": True, "ANTI-SPOIL": True, "ASSIST_BALISE": False, "AFK": [], "SPOILS": {}}

    @commands.group(name="assist", pass_context=True, no_pm=True)
    @checks.admin_or_permissions(ban_members=True)
    async def _assist(self, ctx):
        """Paramètres du module Assist"""
        if ctx.invoked_subcommand is None:
            await send_cmd_help(ctx)

    @_assist.command(pass_context=True)
    async def toggle(self, ctx):
        """Active/désactive l'Assistant sur le serveur (ne désactive pas les fonctionnalités annexes)"""
        server = ctx.message.server
        if server.id not in self.sys:
            self.sys[server.id] = self.def_sys
        if self.sys[server.id]["ASSIST"]:
            self.sys[server.id]["ASSIST"] = False
            await self.bot.say("**Succès** | L'assistant à été désactivé sur ce serveur")
        else:
            self.sys[server.id]["ASSIST"] = True
            await self.bot.say("**Succès** | L'assistant à été activé sur ce serveur")
        fileIO("data/assist/sys.json", "save", self.sys)

    @_assist.command(pass_context=True)
    async def balise(self, ctx, balise: str =None):
        """Permet de changer la balise d'invocation (Par défaut la mention du bot)"""
        server = ctx.message.server
        if server.id not in self.sys:
            self.sys[server.id] = self.def_sys
        if balise:
            self.sys[server.id]["ASSIST_BALISE"] = balise
            await self.bot.say("**Changée** | La balise est désormais `{}`".format(balise))
        else:
            self.sys[server.id]["ASSIST_BALISE"] = False
            await self.bot.say("**Retirée** | La balise par défaut est la mention du bot")
        fileIO("data/assist/sys.json", "save", self.sys)

    @_assist.command(pass_context=True)
    async def antispoil(self, ctx):
        """Active/désactive l'anti-spoil §"""
        server = ctx.message.server
        if server.id not in self.sys:
            self.sys[server.id] = self.def_sys
        if self.sys[server.id]["ANTI-SPOIL"]:
            self.sys[server.id]["ANTI-SPOIL"] = False
            await self.bot.say("**Succès** | La balise spoil  été désactivée")
        else:
            self.sys[server.id]["ANTI-SPOIL"] = True
            await self.bot.say("**Succès** | La balise spoil est active (§)")
        fileIO("data/assist/sys.json", "save", self.sys)

    @_assist.command(pass_context=True)
    async def afk(self, ctx):
        """Active/désactive la détection d'AFK"""
        server = ctx.message.server
        if server.id not in self.sys:
            self.sys[server.id] = self.def_sys
        if type(self.sys[server.id]["AFK"]) is list:
            self.sys[server.id]["AFK"] = False
            await self.bot.say("**Succès** | La fonction \"AFK\" est désactivée")
        else:
            self.sys[server.id]["AFK"] = []
            await self.bot.say("**Succès** | La fonction \"AFK\" est activée")
        fileIO("data/assist/sys.json", "save", self.sys)

    def redux(self, string: str, separateur: str = ".", limite: int = 2000):
        n = -1
        while len(separateur.join(string.split(separateur)[:n])) >= limite:
            n -= 1
        return separateur.join(string.split(separateur)[:n]) + separateur

    def wiki(self, recherche: str, langue: str = 'fr', souple: bool = True):
        wikipedia.set_lang(langue)
        s = wikipedia.search(recherche, 8, True)
        try:
            if s[1]:
                r = s[1]
            else:
                r = s[0][0] if s[0] else None
            if r:
                page = wikipedia.page(r, auto_suggest=souple)
                images = page.images
                image = images[0]
                for i in images:
                    if i.endswith(".png") or i.endswith(".gif") or i.endswith(".jpg") or i.endswith(".jpeg"):
                        image = i
                resum = page.summary
                if not resum:
                    resum = "Contenu indisponible"
                if len(resum) + len(r) > 1995:
                    resum = self.redux(resum, limite=1950)
                em = discord.Embed(title=r.capitalize(), description=resum)
                em.set_thumbnail(url=image)
                em.set_footer(text="Similaire: {}".format(", ".join(s[0])))
                return em
            else:
                if langue == "en":
                    return "Impossible de trouver {}".format(recherche)
                else:
                    return self.wiki(recherche, "en")
        except:
            if langue == "en":
                if souple:
                    if s[0]:
                        if len(s[0]) >= 2:
                            wikipedia.set_lang("fr")
                            s = wikipedia.search(recherche, 3, True)
                            return "**Introuvable** | Réessayez peut-être avec *{}* ?".format(s[0][1])
                        else:
                            return "**Introuvable** | Aucun résultat pour *{}*".format(recherche)
                    else:
                        return "**Introuvable** | Aucun résultat pour *{}*".format(recherche)
                else:
                    return self.wiki(recherche, "en", False)
            else:
                if souple:
                    return self.wiki(recherche, "en")
                else:
                    return self.wiki(recherche, "fr", False)

    #========== COMMANDES-FONCTIONS ============

    @commands.command(pass_context=True)
    async def calcule(self, ctx, calcul: str):
        """Permet de calculer une expression donnée"""
        em = discord.Embed(title=calcul, description=str(sympify(calcul)), color=ctx.message.author.color)
        await self.bot.say(embed=em)

    @commands.command(pass_context=True)
    async def wikipedia(self, ctx, recherche: str):
        """Cherche quelque chose sur Wikipedia (FR ou EN)"""
        r = self.wiki(recherche)
        if type(r) is str:
            await self.bot.say(r)
        else:
            try:
                await self.bot.say(embed=r)
            except:
                await self.bot.say("**Erreur** | La ressource demandée est indisponible")

    def _decode(self, message: discord.Message, regex):
        """Décode un regex et le transforme en arguments (str)"""
        server = message.channel.server
        if server.id not in self.sys:
            self.sys[server.id] = self.def_sys
        if not self.sys[server.id]["ASSIST_BALISE"]:
            msg = " ".join(message.content.split()[1:])
        else:
            msg = message.content.replace(self.sys[server.id]["ASSIST_BALISE"], "", 1)
        msg = msg.replace("`", "")
        output = re.compile(regex, re.IGNORECASE | re.DOTALL).findall(msg)
        if output:
            return list([i for i in output[0] if i])
        else:
            return False

    async def execute(self, message: discord.Message, commandstr: str, regex):
        """Transforme un message en commande et l'exécute (pour les commandes simples)"""
        server = message.channel.server
        commandstr = commandstr.replace("{}", "%s") # Aucazou
        count = commandstr.count("%s")
        args = self._decode(message, regex)
        if args:
            args = tuple(args[:count])
            command = commandstr % args
            prefix = self.bot.settings.get_prefixes(server)[0]
            new_message = deepcopy(message)
            new_message.content = prefix + command
            await self.bot.process_commands(new_message)
            return True
        else:
            return False

    async def read(self, message):
        channel = message.channel
        if not hasattr(channel, 'server'):
            return
        server = channel.server
        author = message.author
        content = message.content
        if "@everyone" in content or "@here" in content:  # Pour les petits malins
            content = content.replace("@everyone", "everyone")
            content = content.replace("@here", "here")
        if server.id not in self.sys:
            self.sys[server.id] = self.def_sys
            fileIO("data/assist/sys.json", "save", self.sys)

        if type(self.sys[server.id]["AFK"]) is list:  # SYSTEME AFK
            for afk in self.sys[server.id]["AFK"]:
                if author.id == afk[0]:
                    self.sys[server.id]["AFK"].remove([afk[0], afk[1], afk[2]])
            if "afk" in content.lower():
                if content.lower().startswith("j'afk"):
                    raison = content.lower().replace("j'afk", "", 1)
                else:
                    raison = content.lower().replace("afk", "", 1)
                if raison.startswith(" "):
                    raison = raison[1:]
                self.sys[server.id]["AFK"].append([author.id, author.name, raison])
            if message.mentions:
                for m in message.mentions:
                    for afk in self.sys[server.id]["AFK"]:
                        if m.id == afk[0]:
                            if afk[2] != "":
                                await self.bot.send_message(channel, "**__{}__ est AFK** | *{}*".format(afk[1], afk[2]))
                            else:
                                await self.bot.send_message(channel, "**__{}__ est AFK** | "
                                                                     "Ce membre sera de retour sous peu".format(afk[1]))

        if self.sys[server.id]["ANTI-SPOIL"]:
            if content.startswith("§") or content.lower().startswith("spoil:"):
                balise = "spoil:" if content.lower().startswith("spoil:") else "§"
                await self.bot.delete_message(message)
                self.sys[server.id]["SPOILS"][message.id] = {"TEXTE": content.replace(balise, ""),
                                                             "AUTEUR": message.author.name,
                                                             "AUTEURIMG": message.author.avatar_url,
                                                             "COLOR": message.author.color}
                em = discord.Embed(color=message.author.color)
                em.set_author(name=message.author.name, icon_url=message.author.avatar_url)
                em.set_footer(text="📩 ─ Réveler le spoil")
                msg = await self.bot.send_message(channel, embed=em)
                await self.bot.add_reaction(msg, "📩")
                return

        if self.sys[server.id]["ASSIST"]:  # SYSTEME ASSISTANT
            balise = self.sys[server.id]["ASSIST_BALISE"] if self.sys[
                server.id]["ASSIST_BALISE"] else "<@{}>".format(self.bot.user.id)
            if content.startswith(balise):
                if await self.execute(message, "ban {}", r"ban <@(.\d+)>"):
                    return  # Ban un membre
                if await self.execute(message, "kick {}", r"kick <@(.\d+)>"):
                    return  # Kick un membre
                if await self.execute(message, "calcul {}", r"(?:combien|calcule*) (?:font|fait)?(.*)"):
                    return  # Calcule un truc (Simpy)
                if await self.execute(message, "wikipedia {}", r"(?:re)?cherche (.*)"):
                    return  # Recherche sur Wikipedia en FR puis en EN si nécessaire

    async def react(self, reaction, user):
        message = reaction.message
        server = message.channel.server
        if server.id not in self.sys:
            self.sys[server.id] = self.def_sys
            fileIO("data/assist/sys.json", "save", self.sys)
        if reaction.emoji == "📩":
            if not user.bot:
                if message.id in self.sys[server.id]["SPOILS"]:
                    await self.bot.remove_reaction(message, "📩", user)
                    param = self.sys[server.id]["SPOILS"][message.id]
                    em = discord.Embed(color=param["COLOR"], description=param["TEXTE"])
                    em.set_author(name=param["AUTEUR"], icon_url=param["AUTEURIMG"])
                    await self.bot.send_message(user, embed=em)


def check_folders():
    if not os.path.exists("data/assist"):
        print("Creation du fichier assist ...")
        os.makedirs("data/assist")


def check_files():
    if not os.path.isfile("data/assist/sys.json"):
        print("Création de assist/sys.json ...")
        fileIO("data/assist/sys.json", "save", {})


def setup(bot):
    check_folders()
    check_files()
    n = Assist(bot)
    bot.add_listener(n.read, "on_message")
    bot.add_listener(n.react, "on_reaction_add")
    bot.add_cog(n)