
import asyncio
import os

from discord.ext import commands
from sumy.nlp.stemmers import Stemmer
from sumy.nlp.tokenizers import Tokenizer
from sumy.parsers.html import HtmlParser
from sumy.parsers.plaintext import PlaintextParser
from sumy.summarizers.lsa import LsaSummarizer as Summarizer
from sumy.utils import get_stop_words

from .utils.dataIO import fileIO, dataIO


class Labo:
    """Module poubelle d'expérimentation et commandes random - parfois des trucs sympa en sortent !"""
    def __init__(self, bot):
        self.bot = bot
        self.sys = dataIO.load_json("data/labo/sys.json")  # Pas très utile mais on le garde pour plus tard
        self.sys_def = {}

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

    @commands.command(pass_context=True, hidden=True)
    async def balance(self, ctx):
        """Permet de voir l'argent possédée (HIDDEN_TEST)"""
        finance = self.bot.get_cog("Finance").api
        solde = finance.get(ctx.message.author).solde
        await self.bot.say("Vous avez {} {}".format(solde, finance.get_credits_str(ctx.message.server, solde)))

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


def setup(bot):
    check_folders()
    check_files()
    n = Labo(bot)
    bot.add_listener(n.reactrecap, "on_reaction_add")
    bot.add_cog(n)
