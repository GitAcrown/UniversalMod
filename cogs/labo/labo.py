
import asyncio
import os
import time
from collections import namedtuple

import discord
from discord.ext import commands
from sumy.nlp.stemmers import Stemmer
from sumy.nlp.tokenizers import Tokenizer
from sumy.parsers.html import HtmlParser
from sumy.parsers.plaintext import PlaintextParser
from sumy.summarizers.lsa import LsaSummarizer as Summarizer
from sumy.utils import get_stop_words

from .utils import checks
from .utils.dataIO import fileIO, dataIO


class Labo:
    """Module poubelle d'expérimentation et commandes random - parfois des trucs sympa en sortent !"""
    def __init__(self, bot):
        self.bot = bot
        self.sys = dataIO.load_json("data/labo/sys.json")  # Pas très utile mais on le garde pour plus tard
        self.sys_def = {"REPOST": []}
        self.msg = dataIO.load_json("data/labo/msg.json")
        # Chronos modele : [jour, heure, type (EDIT/SUPPR), MSGID, M_avant, M_après (NONE SI SUPPR)]

    def clean_chronos(self, user: discord.Member):
        jour = time.strftime("%d/%m/%Y", time.localtime())
        if user.id in self.msg:
            for e in self.msg[user.id]:
                if e[0] != jour:
                    del self.msg[user.id][e]
            fileIO("data/labo/msg.json", "save", self.msg)
            return True
        return False

    def get_chronos_obj(self, user: discord.Member, identifiant: str):
        if user.id in self.msg:
            for e in self.msg[user.id]:
                if e[3] == identifiant:
                    Chronos = namedtuple('Chronos', ['id', 'jour', 'heure', 'type', 'message_before', 'message_after'])
                    return Chronos(e[3], e[0], e[1], e[2], e[4], e[5])
        return False

    def check(self, reaction, user):
        return not user.bot

    @commands.command(aliases=["hp"], pass_context=True)
    @checks.admin_or_permissions(manage_messages=True)
    async def chronos(self, ctx, user: discord.Member, identifiant: str = None):
        """Système CHRONOS - Permet de remonter le temps (au niveau des messages)..."""
        if user.id not in self.msg:
            self.msg[user.id] = []
            fileIO("data/labo/msg.json", "save", self.msg)
            await self.bot.say("**Vide** | Cet utilisateur n'a aucun historique")
            return
        self.clean_chronos(user)
        if not identifiant:
            txt = ""
            hist = [e for e in self.msg[user.id]]
            for e in hist:
                txt += "**{}** ─ {}: `{}`\n".format(e[1], e[2], e[3])
            em = discord.Embed(title="Historique CHRONOS", description=txt, color=user.color)
            em.set_footer(text="Entrez l'identifiant du message pour voir l'historique")
            msg = await self.bot.say(embed=em)
            await asyncio.sleep(0.25)
            rep = await self.bot.wait_for_message(author=ctx.message.author, channel=ctx.message.channel, timeout=60)
            if rep is None:
                em.set_footer(text="── Session expirée ──")
                await self.bot.edit_message(msg, embed=em)
                return
            elif rep.content.isdigit():
                identifiant = rep.content
            else:
                em.set_footer(text="Cet identifiant n'est pas valable")
                await self.bot.edit_message(msg, embed=em)
                return
        ch = self.get_chronos_obj(user, identifiant)
        if ch.type == "EDIT":
            txt_before = "*{}*".format(ch.message_before)
            txt_after = "*{}*\n─ {}".format(ch.message_after, ch.heure)
            em = discord.Embed(color=user.color)
            em.add_field(name="Avant édition", value=txt_before)
            em.add_field(name="Après édition", value=txt_after)
            em.set_footer(text="Auteur ─ {} | L'action expirera à minuit".format(user.name))
            await self.bot.say(embed=em)
        else:
            txt = "*{}*\n─ {}".format(ch.message_before, ch.heure)
            em = discord.Embed(title="Message avant suppression", description=txt, color=user.color)
            em.set_footer(text="Auteur ─ {} | L'action expirera à minuit".format(user.name))
            await self.bot.say(embed=em)

    @commands.command(pass_context=True)
    async def vaporwave(self, ctx, *texte):
        """Formatte un texte en ｖａｐｏｒｗａｖｅ"""
        norm = [l for l in "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz1234567890 ',.&:;?!"]
        vapo = [l for l in "ＡＢＣＤＥＦＧＨＩＪＫＬＭＮＯＰＱＲＳＴＵＶＷＸＹＺａｂｃｄｅｆｇｈｉｊｋｌｍｎｏｐｑｒｓｔｕｖｗｘｙｚ" \
                           "１２３４５６７８９０　＇，．＆：；？！"]
        texte = " ".join(texte)
        fin_texte = texte
        for char in texte:
            if char in norm:
                ind = norm.index(char)
                fin_texte = fin_texte.replace(char, vapo[ind])
        await self.bot.say("**Ｖａｐｏｒ** | {}".format(fin_texte))

    def recap_url(self, url: str, langue:str = "french", nb_phrases:int = 7):
        parser = HtmlParser.from_url(url, Tokenizer(langue))
        # or for plain text files
        # parser = PlaintextParser.from_file("document.txt", Tokenizer(LANGUAGE))
        stemmer = Stemmer(langue)

        summarizer = Summarizer(stemmer)
        summarizer.stop_words = get_stop_words(langue)
        output = []

        for sentence in summarizer(parser.document, nb_phrases):
            output.append(str(sentence) + "\n")
        return "".join(output)

    def recap_txt(self, texte: str, langue:str = "french", nb_phrases:int = 5):
        parser = PlaintextParser.from_string(texte, Tokenizer(langue))
        stemmer = Stemmer(langue)

        summarizer = Summarizer(stemmer)
        summarizer.stop_words = get_stop_words(langue)
        output = []

        for sentence in summarizer(parser.document, nb_phrases):
            output.append(str(sentence) + "\n")
        return "".join(output)

    @commands.command(pass_context=True)
    async def recapurl(self, ctx, url:str, phrases:int=5):
        """Permet de faire un résumé d'une URL

        Note: Les grands articles nécessite plus de phrases pour avoir un résumé pertinent"""
        await self.bot.say("**Patientez...** | La durée"
                           " peut être plus ou moins longue en fonction de la longueur du texte à résumer.")
        await asyncio.sleep(1)
        try:
            recap = self.recap_url(url, nb_phrases=phrases)
        except:
            await self.bot.say("**Erreur** | Cette page ne me laisse pas lire le texte")
            return
        if recap:
            await self.bot.say(recap)
        else:
            await self.bot.say("Je n'ai pas réussi à faire un résumé de ce lien")

    @commands.command(pass_context=True)
    async def recaptxt(self, ctx, *texte):
        """Permet de faire un résumé d'un texte"""
        await self.bot.say("**Patientez...** | La durée"
                           " peut être plus ou moins longue en fonction de la longueur du texte à résumer.")
        await asyncio.sleep(1)
        recap = self.recap_txt(" ".join(texte))
        if recap:
            await self.bot.say(recap)
        else:
            await self.bot.say("**Erreur** | Impossible de faire un résumé de ça.")

    async def read(self, message):
        splitted = message.content.split(" ")
        server = message.channel.server
        if not message.author.bot:
            if "http" in message.content:
                for e in splitted:
                    if e.startswith("http"):
                        if server.id not in self.sys:
                            self.sys[server.id] = self.sys_def
                            fileIO("data/labo/sys.json", "save", self.sys)
                        if e.lower() in self.sys[server.id]["REPOST"]:
                            await self.bot.add_reaction(message, "♻")
                        else:
                            self.sys[server.id]["REPOST"].append(e.lower())
                            if len(self.sys[server.id]["REPOST"]) > 100:
                                self.sys[server.id]["REPOST"].remove(self.sys[server.id]["REPOST"][0])
                            fileIO("data/labo/sys.json", "save", self.sys)

    async def read_edit(self, before, after):
        user = before.author
        if user.id not in self.msg:
            self.msg[user.id] = []
        jour = time.strftime("%d/%m/%Y", time.localtime())
        heure = time.strftime("%H:%M", time.localtime())
        messageid = before.id if not self.get_chronos_obj(user, before.id) else "{}{}".format(
            before.id, time.strftime("%H%M%S", time.localtime()))
        self.msg[user.id].append([jour, heure, "EDIT", messageid, before.content, after.content])

    async def read_suppr(self, message):
        user = message.author
        if user.id not in self.msg:
            self.msg[user.id] = []
        jour = time.strftime("%d/%m/%Y", time.localtime())
        heure = time.strftime("%H:%M", time.localtime())
        messageid = message.id if not self.get_chronos_obj(user, message.id) else "{}{}".format(
            message.id, time.strftime("%H%M%S", time.localtime()))
        self.msg[user.id].append([jour, heure, "SUPPR", messageid, message.content, None])

    async def reactrecap(self, reaction, user):
        message = reaction.message
        server = message.channel.server
        texte = message.content
        if reaction.emoji == "✂":
            if message.content.startswith("http"):
                url = message.content.split()[0]
                notif = await self.bot.send_message(user, "**Patientez...** | La durée"
                                   " peut être plus ou moins longue en fonction de la longueur du texte à résumer.")
                await asyncio.sleep(1)
                try:
                    recap = self.recap_url(url)
                except:
                    await self.bot.send_message(user, "**Erreur** | Cette page ne me laisse pas lire le texte")
                    return
                if recap:
                    await self.bot.send_message(recap)
                    await self.bot.delete_message(notif)
                else:
                    await self.bot.send_message("Je n'ai pas réussi à faire un résumé de ce lien")
            else:
                notif = await self.bot.send_message(user, "**Patientez...** | La durée"
                                   " peut être plus ou moins longue en fonction de la longueur du texte à résumer.")
                await asyncio.sleep(1)
                recap = self.recap_txt(texte)
                if recap:
                    await self.bot.delete_message(notif)
                    await self.bot.send_message(user, recap)
                else:
                    await self.bot.send_message(user, "**Erreur** | Impossible de faire un résumé de ça.")


def check_folders():
    if not os.path.exists("data/labo"):
        print("Creation du fichier Labo ...")
        os.makedirs("data/labo")


def check_files():
    if not os.path.isfile("data/labo/sys.json"):
        print("Création de labo/sys.json ...")
        fileIO("data/labo/sys.json", "save", {})
    if not os.path.isfile("data/labo/msg.json"):
        print("Création de labo/msg.json ...")
        fileIO("data/labo/msg.json", "save", {})


def setup(bot):
    check_folders()
    check_files()
    n = Labo(bot)
    bot.add_listener(n.read, "on_message")
    bot.add_listener(n.read_suppr, "on_message_delete")
    bot.add_listener(n.read_edit, "on_message_edit")
    bot.add_listener(n.reactrecap, "on_reaction_add")
    bot.add_cog(n)
