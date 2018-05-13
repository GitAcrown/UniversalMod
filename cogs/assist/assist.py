import os
import random
import re
import urllib
from copy import deepcopy
from random import choice

import aiohttp
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
        self.session = aiohttp.ClientSession()
        if os.path.exists("data/just"):
            self.justice_on = True
        else:
            self.justice_on = False

    def __unload(self):
        self.session.close()

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
                em = discord.Embed(title=r.capitalize(), description=resum, color=0xeeeeee)
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
    @commands.cooldown(5, 60, commands.BucketType.server)
    async def google(self, ctx, text):
        """Faire une recherche google
        Exemple: google Chats

        -- Options: Image, Images, Maps
        - google image qqchose > Retourne la première image
        - google maps Paris > Recherche google maps de paris
        - google images chiens > Retourne une image au hasard"""
        result = await self.get_response(ctx)
        await self.bot.say(result)

    async def images(self, ctx, regex, option, images: bool = False):
        uri = "https://www.google.com/search?hl=fr&tbm=isch&tbs=isz:m&q="
        num = 7
        if images:
            num = 8
        if isinstance(ctx, str):
            quary = str(ctx[num - 1:].lower())
        else:
            quary = str(ctx.message.content
                        [len(ctx.prefix + ctx.command.name) + num:].lower())
        encode = urllib.parse.quote_plus(quary, encoding='utf-8',
                                         errors='replace')
        uir = uri + encode
        url = None
        async with self.session.get(uir, headers=option) as resp:
            test = await resp.content.read()
            unicoded = test.decode("unicode_escape")
            query_find = regex[0].findall(unicoded)
            try:
                if images:
                    url = choice(query_find)
                elif not images:
                    url = query_find[0]
                error = False
            except IndexError:
                error = True
        return url, error

    def parsed(self, find, regex, found: bool = True):
        find = find[:5]
        for r in find:
            if regex[3].search(r):
                m = regex[3].search(r)
                r = r[:m.start()] + r[m.end():]
            r = self.unescape(r)
        for i in range(len(find)):
            if i == 0:
                find[i] = "<" + find[i] + ">" + "\n\n**Aussi:**"
            else:
                find[i] = "<{}>".format(find[i])
        return find

    def unescape(self, msg):
        regex = ["<br \/>", "(?:\\\\[rn])", "(?:\\\\['])", "%25", "\(", "\)"]
        subs = ["\n", "", "'", "%", "%28", "%29"]
        for i in range(len(regex)):
            sub = re.sub(regex[i], subs[i], msg)
            msg = sub
        return msg

    async def get_response(self, ctx):
        if isinstance(ctx, str):
            search_type = ctx.lower().split(" ")
            search_valid = str(ctx.lower())
        else:
            search_type = ctx.message.content[len(ctx.prefix + ctx.command.name) + 1:].lower().split(" ")
            search_valid = str(ctx.message.content
                               [len(ctx.prefix + ctx.command.name) + 1:].lower())
        option = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 6.1; WOW64; rv:40.0) Gecko/20100101 Firefox/40.1'
        }
        regex = [
            re.compile(",\"ou\":\"([^`]*?)\""),
            re.compile("<h3 class=\"r\"><a href=\"\/url\?url=([^`]*?)&amp;"),
            re.compile("<h3 class=\"r\"><a href=\"([^`]*?)\""),
            re.compile("\/url?url=")
        ]

        # Start of Image
        if search_type[0] == "image" or search_type[0] == "images":
            msg = "Votre recherche n'a rien donné."
            if search_valid == "image" or search_valid == "images":
                msg = "Vous devez taper votre recherche."
                return msg
            else:
                if search_type[0] == "image":
                    url, error = await self.images(ctx, regex, option)
                elif search_type[0] == "images":
                    url, error = await self.images(ctx, regex, option, images=True)
                if url and not error:
                    return url
                elif error:
                    return msg
                    # End of Image
        # Start of Maps
        elif search_type[0] == "maps":
            if search_valid == "maps":
                msg = "Vous cherchez quoi ?"
                return msg
            else:
                uri = "https://www.google.com/maps/search/"
                if isinstance(ctx, str):
                    quary = str(ctx[5:].lower())
                else:
                    quary = str(ctx.message.content
                                [len(ctx.prefix + ctx.command.name) + 6:].lower())
                encode = urllib.parse.quote_plus(quary, encoding='utf-8',
                                                 errors='replace')
                uir = uri + encode
                return uir
                # End of Maps
        # Start of generic search
        else:
            uri = "https://www.google.com/search?hl=fr&q="
            if isinstance(ctx, str):
                quary = str(ctx)
            else:
                quary = str(ctx.message.content
                            [len(ctx.prefix + ctx.command.name) + 1:])
            encode = urllib.parse.quote_plus(quary, encoding='utf-8',
                                             errors='replace')
            uir = uri + encode
            async with self.session.get(uir, headers=option) as resp:
                test = str(await resp.content.read())
                query_find = regex[1].findall(test)
                if not query_find:
                    query_find = regex[2].findall(test)
                    try:
                        query_find = self.parsed(query_find, regex)
                    except IndexError:
                        return IndexError
                elif regex[3].search(query_find[0]):
                    query_find = self.parsed(query_find, regex)
                else:
                    query_find = self.parsed(query_find, regex, found=False)
            query_find = "\n".join(query_find)
            return query_find

    @commands.command(pass_context=True)
    async def calcule(self, ctx, *calcul):
        """Permet de calculer une expression donnée"""
        calcul = " ".join(calcul)
        em = discord.Embed(title=calcul, description="`" + str(sympify(calcul)) + "`", color=ctx.message.author.color)
        await self.bot.say(embed=em)

    @commands.command(pass_context=True)
    async def wikipedia(self, ctx, *recherche):
        """Cherche quelque chose sur Wikipedia (FR ou EN)"""
        recherche = " ".join(recherche)
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
            return output
        else:
            return False

    async def execute(self, message: discord.Message, commandstr: str, regex):
        """Transforme un message en commande et l'exécute (pour les commandes simples)"""
        server = message.channel.server
        commandstr = commandstr.replace("{}", "%s")  # Aucazou
        count = commandstr.count("%s")
        args = self._decode(message, regex)
        if args:
            if count == 1:
                args = args[0]
            else:
                while len(args) < count:
                    args.append("")
                if len(args) > count:
                    args = args[:count]
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
        if author.bot:
            return
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
                rs = lambda: random.randint(0, 255)
                color = int('0x%02X%02X%02X' % (rs(), rs(), rs()), 16)
                balise = "spoil:" if content.lower().startswith("spoil:") else "§"
                await self.bot.delete_message(message)
                em = discord.Embed(color=color)
                em.set_author(name=message.author.name, icon_url=message.author.avatar_url)
                em.set_footer(text="👁 ─ Voir le spoil")
                msg = await self.bot.send_message(channel, embed=em)
                self.sys[server.id]["SPOILS"][msg.id] = {"TEXTE": content.replace(balise, ""),
                                                             "AUTEUR": message.author.name,
                                                             "AUTEURIMG": message.author.avatar_url}
                await self.bot.add_reaction(msg, "👁")
                return

        if self.sys[server.id]["ASSIST"]:  # SYSTEME ASSISTANT
            balise = self.sys[server.id]["ASSIST_BALISE"] if self.sys[
                server.id]["ASSIST_BALISE"] else "<@{}>".format(self.bot.user.id)
            if content.startswith(balise):
                if await self.execute(message, "ban {}", r"ban <@(.\d+)>"):
                    return  # Ban un membre
                if await self.execute(message, "kick {}", r"kick <@(.\d+)>"):
                    return  # Kick un membre
                if await self.execute(message, "calcule {}", r"(?:combien|calcule*) (?:font|fait)?(.*)"):
                    return  # Calcule un truc (Simpy)
                if await self.execute(message, "wikipedia {}", r"(?:re)?cherche (.*)"):
                    return  # Recherche sur Wikipedia en FR puis en EN si nécessaire
                if await self.execute(message, "help {}", r"(?:aide|explique|help) (.*)"):
                    return  # Propose une aide sur la commande
                if self.justice_on:
                    output = re.compile(
                        r"(?:emprisonnes*|lib[èe]res*|met en prison|jail|isole|sort) <@(.\d+)>(?:\s?\w*?\s)?([0-9]*[jhms])?",
                        re.IGNORECASE | re.DOTALL).findall(message)
                    if output:
                        u = output[0]
                        plus = " {}".format(u[1]) if u[1] else ""
                        new_message = deepcopy(message)
                        prefix = self.bot.settings.get_prefixes(server)[0]
                        txt = "p <@{}>{}".format(u[0], plus)
                        new_message.content = prefix + txt
                        await self.bot.process_commands(new_message)
                        return

    async def react(self, reaction, user):
        message = reaction.message
        server = message.channel.server
        if server.id not in self.sys:
            self.sys[server.id] = self.def_sys
            fileIO("data/assist/sys.json", "save", self.sys)
        if reaction.emoji == "👁":
            if not user.bot:
                if message.id in self.sys[server.id]["SPOILS"]:
                    try:
                        await self.bot.remove_reaction(message, "👁", user)
                    except:
                        pass
                    rs = lambda: random.randint(0, 255)
                    color = int('0x%02X%02X%02X' % (rs(), rs(), rs()), 16)
                    param = self.sys[server.id]["SPOILS"][message.id]
                    em = discord.Embed(color=color, description=param["TEXTE"])
                    em.set_author(name=param["AUTEUR"], icon_url=param["AUTEURIMG"])
                    try:
                        await self.bot.send_message(user, embed=em)
                    except:
                        print("SPOIL - Impossible d'envoyer un message à {} (Bloqué)".format(str(user)))


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