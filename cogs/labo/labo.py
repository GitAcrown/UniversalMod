
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
        return "\n".join(output)

    def recap_txt(self, texte: str, langue:str = "french", nb_phrases:int = 7):
        parser = PlaintextParser.from_string(texte, Tokenizer(langue))
        stemmer = Stemmer(langue)

        summarizer = Summarizer(stemmer)
        summarizer.stop_words = get_stop_words(langue)
        output = []

        for sentence in summarizer(parser.document, nb_phrases):
            output.append(str(sentence) + "\n")
        return "\n".join(output)

    @commands.command(pass_context=True)
    async def recap(self, ctx, url:str, phrases:int=5):
        """Permet de faire un résumé d'une URL

        Note: Les grands articles nécessite plus de phrases pour avoir un résumé pertinent"""
        await self.bot.say("**Patientez...** | La durée"
                           " peut être plus ou moins longue en fonction de la longueur du texte à résumer.")
        await asyncio.sleep(1)
        await self.bot.say(self.recap_url(url, nb_phrases=phrases))


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
    bot.add_cog(n)
