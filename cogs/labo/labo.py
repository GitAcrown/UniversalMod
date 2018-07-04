
import asyncio
import os
import re
import time
from collections import namedtuple
from datetime import datetime, timedelta

import country_converter as coco
import discord
import pyfootball
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
        self.sys_def = {"REPOST": [], "FOOT_SUB": {}, "SERV_CONV": {}, "ETUDES_STATS": {}}
        self.msg = dataIO.load_json("data/labo/msg.json")
        self.foot = pyfootball.Football("ec9727b5fad84d18ae9bb716743b61c4")
        self.cc = coco.CountryConverter()
        self.cycle = bot.loop.create_task(self.loop())
        self.reset = False
        self.fb_mem = []
        self.analyse_avt = {}
        # Chronos modele : [jour, heure, type (EDIT/SUPPR), MSGID, M_avant, M_après (NONE SI SUPPR)]

    async def loop(self):
        await self.bot.wait_until_ready()
        try:
            await asyncio.sleep(15)  # Temps de mise en route
            while True:
                now = datetime.now()
                for i in self.sys["FOOT_SUB"]:
                    warn = datetime.strptime(self.sys["FOOT_SUB"][i]["WARNING"], "%d/%m/%Y %H:%M")
                    localtime = datetime.strptime(self.sys["FOOT_SUB"][i]["DATE"], "%d/%m/%Y %H:%M")
                    if warn <= now:
                        match = self.sys["FOOT_SUB"][i]
                        txt = "**Votre match commence bientôt !** Début du match : `{}`".format(
                            localtime.strftime("%Hh%M"))
                        em = discord.Embed(title="{} *{}* — {} *{}*".format(match["HOME_FLAG"], match["HOME"],
                                                                            match["AWAY_FLAG"], match["AWAY"]),
                                           description=txt)
                        for u in self.sys["FOOT_SUB"][i]["ABON"]:
                            serv = self.bot.get_server(self.sys["SERV_CONV"][u][0])
                            user = serv.get_member(u)
                            try:
                                await self.bot.send_message(user, embed=em)
                            except Exception as e:
                                print("Impossible d'envoyer une notif du match à {} : {}".format(user.name, e))
                                pass
                        del self.sys["FOOT_SUB"][i]

                await asyncio.sleep(60)
        except asyncio.CancelledError:
            pass

    def clean_chronos(self, user: discord.Member):
        jour = time.strftime("%d/%m/%Y", time.localtime())
        if user.id in self.msg:
            for e in self.msg[user.id]:
                if e[0] != jour:
                    self.msg[user.id].remove(e)
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

    @commands.command(aliases=["sd", "emostatdel"], pass_context=True)
    @checks.admin_or_permissions(ban_members=True)
    async def scrapdelete(self, ctx, nom: str, force: bool= False):
        """Supprime une étude d'Emojis"""
        if "ETUDES_STATS" not in self.sys:
            self.sys["ETUDES_STATS"] = {}
        nom = nom.upper()
        if not force:
            if nom in self.analyse_avt:
                if self.analyse_avt[nom]:
                    await self.bot.say("**Impossible** | Attendez la fin de l'étude pour la supprimer")
                    return
        if nom in self.sys["ETUDES_STATS"]:
            del self.sys["ETUDES_STATS"][nom]
            fileIO("data/labo/sys.json", "save", self.sys)
            await self.bot.say("**Etude supprimée avec succès**")
        else:
            await self.bot.say("**Inexistante** | Aucune étude ne porte ce nom")

    @commands.command(aliases=["se", "emostat"], pass_context=True)
    @checks.admin_or_permissions(ban_members=True)
    async def scrapemoji(self, ctx, nom: str, date: str, channel: discord.Channel = None):
        """Récolte un ensemble de statistiques sur les Emojis du serveur, réactions comprises.

        -- Pour chaque emoji:
        - Nombre d'apparition
        - Première apparition
        - Ratio apparitions/jour"""
        origin = date
        nom = nom.upper()
        if not channel:
            channel = ctx.message.channel
        if "/" in date and len(date) == 10:
            date = datetime.strptime(date, "%d/%m/%Y")
        else:
            await self.bot.say("**Date invalide** | La date doit être au format JJ/MM/AAAA")
            return
        server = channel.server
        if "ETUDES_STATS" not in self.sys:
            self.sys["ETUDES_STATS"] = {}
        if nom not in self.sys["ETUDES_STATS"]:
            self.sys["ETUDES_STATS"][nom] = {}
            fileIO("data/labo/sys.json", "save", self.sys)
            await self.bot.say("**Nouvelle étude** | Votre étude **{}** à été créée avec succès.".format(nom))
        else:
            await self.bot.say("**Chargement d'étude** | Votre étude **{}** à été chargée avec succès. "
                               "Les données récoltées seront fusionnées à cette étude.".format(nom))
        data = self.sys["ETUDES_STATS"][nom]
        maxnb = 1000000000
        nbjour = 0
        if nom not in self.analyse_avt:
            self.analyse_avt[nom] = origin
        else:
            if self.analyse_avt[nom]:
                await self.bot.say("**Etude en cours** | Désolé mais il m'est impossible "
                                   "de faire deux récoltes à la fois sur la même étude.")
                return
        servemo = [i.name for i in server.emojis]
        await asyncio.sleep(2)
        await self.bot.say("**Récolte de statistiques sur les Emojis** | Cela peut prendre beaucoup de temps si "
                           "l'échantillon est important (> 30j).\n"
                           "Sachez que vous pouvez consulter l'avancement avec `{}sa {}`.".format(ctx.prefix, nom))
        async for msg in self.bot.logs_from(channel, limit=maxnb, after=date):
            nbjour += 1
            day = msg.timestamp.strftime("%d/%m/%Y à %H:%M")
            self.analyse_avt[nom] = day
            reacts = msg.reactions
            output = re.compile(':(.*?):', re.DOTALL | re.IGNORECASE).findall(msg.content)
            if reacts:  # En réaction
                for e in reacts:
                    if type(e.emoji) is str:
                        continue
                    if e.emoji.name in servemo:
                        if e.emoji.name not in data:
                            data[e.emoji.name] = {"NB": 1, "FIRST": day}
                        else:
                            data[e.emoji.name]["NB"] += 1
                            data[e.emoji.name]["FIRST"] = day
            if output:  # En message
                for e in output:
                    if e in servemo:
                        if e not in data:
                            data[e] = {"NB": 1, "FIRST": day}
                        else:
                            data[e]["NB"] += 1
                            data[e]["FIRST"] = day
        self.analyse_avt[nom] = None
        txt = "─ **La prolonger**\nVous pouvez la prolonger si vous le désirez en faisant " \
              "`{}se {} {}` sur un autre salon écrit. Les données ainsi récoltées seront fusionnées.\n\n".format(
            ctx.prefix, nom, origin)
        txt += "─ **Voir les résultats**\nVous pouvez voir les résultats avec `{}sr {}`. Sachez que " \
               "faire ça ne vous empêche pas ensuite de continuer votre étude sur d'autres salons".format(
            ctx.prefix, nom)
        em = discord.Embed(title="Etude {} | Récolte terminée".format(nom), description=txt)
        fileIO("data/labo/sys.json", "save", self.sys)
        await self.bot.say(embed=em)

    @commands.command(aliases=["sr", "emostatresult"], pass_context=True)
    @checks.admin_or_permissions(ban_members=True)
    async def scrapresult(self, ctx, nom: str):
        """Consulter les résultats d'une étude.

        Si les données sont trop importantes, ne renvoie qu'un fichier txt contenant ces données récoltées."""
        if "ETUDES_STATS" not in self.sys:
            self.sys["ETUDES_STATS"] = {}
        nom = nom.upper()
        today = time.strftime("%d/%m/%Y à %H:%M", time.localtime())
        txt = "EMOJI\tNOMBRE\tPOURCENTAGE\n\n"
        datxt = "NOM\tNOMBRE\tPREM.APPAR.\tPOURCENTAGE\n\n"
        if nom in self.sys["ETUDES_STATS"]:
            await self.bot.say("**Patientez SVP.** | J'organise les statistiques pour qu'elles soient lisibles.")
            data = self.sys["ETUDES_STATS"][nom]
            total = sum([data[i]["NB"] for i in data])
            for e in data:
                txt += "**{}**\t{}\t{}\n".format(e, data[e]["NB"], round((data[e]["NB"] / total) * 100, 2))
                datxt += "{}\t{}\t{}\t{}\n".format(e, data[e]["NB"], data[e]["FIRST"],
                                                   round((data[e]["NB"] / total) * 100, 2))
            datxt += "\n\n- Résultats générés le {}\n-- Seuls les emojis présents sur le serveur au moment de la " \
                     "récolte des données ont été pris en compte\n--- Si ces résultats vous semblent louches," \
                     " contactez Acrown#4424\n---- Ce fichier à été formatté de façon à ce que vous puissiez faire " \
                     "un Copier/Coller directement dans un tableau Excel"
            em = discord.Embed(title="Résultats de l'étude {}".format(nom), description=txt)
            try:
                await self.bot.say(embed=em)
            except:
                pass
            filename = "StatsEmojiEtude_{}".format(nom)
            file = open("data/labo/{}.txt".format(filename), "w", encoding="utf-8")
            file.write(txt)
            file.close()
            try:
                await self.bot.send_file(ctx.message.channel, "data/labo/{}.txt".format(filename))
                os.remove("data/labo/{}.txt".format(filename))
            except:
                await self.bot.say("**Erreur** | Je n'arrive pas à upload le fichier.")

    @commands.command(aliases=["sa", "emostatavancemt"], pass_context=True)
    @checks.admin_or_permissions(ban_members=True)
    async def scrapavancemt(self, ctx, nom: str):
        """Affiche l'avancement de la récolte pour une Etude donnée"""
        if "ETUDES_STATS" not in self.sys:
            self.sys["ETUDES_STATS"] = {}
        nom = nom.upper()
        if nom in self.analyse_avt:
            if self.analyse_avt[nom]:
                await self.bot.say("**Avancement {}** ─ J'ai analysé pour le moment tous les messages postés avant le "
                                   "{}".format(nom, self.analyse_avt[nom]))
            else:
                await self.bot.say("**Avancement {}** ─ Cette étude est à l'arrêt.".format(nom))
        else:
            await self.bot.say("**Erreur** | Cette étude n'existe pas")

    @commands.command(pass_context=True, hidden=True)
    async def asimov(self, ctx, nb: int = None):
        """Renvoie les 4 lois d'Asimov tels que formulés dans son livre 'Terre et Fondation et Prélude à Fondation'"""
        liste = [["Loi Zéro","Un robot ne peut pas porter atteinte à l'humanité, ni, par son inaction, permettre "
                             "que l'humanité soit exposée au danger."],
                 ["Première Loi", "Un robot ne peut porter atteinte à un être humain, ni, restant passif, permettre qu'un être humain "
                 "soit exposé au danger, sauf contradiction avec la Loi Zéro."],
                 ["Deuxième Loi","Un robot doit obéir aux ordres que lui donne un être humain, sauf si de tels ordres entrent en "
                 "conflit avec la Première Loi ou la Loi Zéro."],
                 ["Toisième Loi","Un robot doit protéger son existence tant que cette protection n'entre pas en conflit avec la "
                 "Première ou la Deuxième Loi ou la Loi Zéro."]]
        em = discord.Embed()
        if not nb:
            for e in liste:
                em.add_field(name=e[0], value=e[1])
            em.set_footer(text="Lois d'Asimov, corrigées, telle que formulées dans son livre "
                               "'Terre et Fondation et Prélude à Fondation'")
        else:
            em.add_field(name=liste[nb][0], value=liste[nb][1])
            em.set_footer(text="Loi d'Asimov, corrigée, telle que formulée dans son livre "
                               "'Terre et Fondation et Prélude à Fondation'")
        await self.bot.say(embed=em)

    @commands.command(aliases=["ge"], pass_context=True)
    async def getemoji(self, ctx, emoji: discord.Emoji):
        """Retourne l'Emoji discord"""
        em = discord.Embed(title=emoji.name, description="[URL]({})".format(emoji.url))
        em.set_footer(text="Création ─ {}".format(emoji.created_at))
        em.set_image(url=emoji.url)
        await self.bot.say(embed=em)

    @commands.group(name="football", aliases=["fb"], pass_context=True)
    async def _football(self, ctx):
        """Informations sur les prochains matchs de la Coupe du Monde"""
        if ctx.invoked_subcommand is None:
            await ctx.invoke(self.next)

    @_football.command(pass_context=True)
    async def live(self, ctx, reset: bool=False):
        """Affiche les scores en direct du match en cours"""
        comp = self.foot.get_competition(467)
        furl = "http://www.ohda.org/imgs/soccer-roll-logo.gif"
        try:
            lives = [f for f in comp.get_fixtures() if f.status == "IN_PLAY"]
        except:
            await self.bot.say("**Aucun live** | Impossible de trouver un direct\n"
                               "*Si il y a un match en cours, patientez quelques secondes et réessayez.*")
            return
        if reset:
            self.reset = True
            self.fb_mem = []
            await self.bot.say("**Arrêt** | Le score live va s'aarrêter dans quelques instants...")
            return
        for live in lives:
            nom = "{}-{}".format(live.home_team, live.away_team)
            if nom not in self.fb_mem:
                break
        else:
            await self.bot.say("**Aucun live** | Il semblerait que vous ayez déjà démarré une session de Scores en "
                               "live pour les matchs en cours")
            return

        nom = "{}-{}".format(live.home_team, live.away_team)
        self.fb_mem.append(nom)
        livedebut = live.date + timedelta(hours=2)
        now = datetime.now()
        flaghome = ":flag_{}: ".format(self.cc.convert(names=live.home_team, to='ISO2').lower()) \
            if self.cc.convert(names=live.home_team, to='ISO2').lower() != "not found" else ""
        flagaway = ":flag_{}: ".format(self.cc.convert(names=live.away_team, to='ISO2').lower()) \
            if self.cc.convert(names=live.away_team, to='ISO2').lower() != "not found" else ""
        home = "**{}**".format(live.result["home_team_goals"]) if \
            live.result["home_team_goals"] >= live.result["away_team_goals"] else "{}".format(
            live.result["home_team_goals"])
        away = "**{}**".format(live.result["away_team_goals"]) if \
            live.result["away_team_goals"] >= live.result["home_team_goals"] else "{}".format(
            live.result["away_team_goals"])
        em = discord.Embed(title="{}{} / {}{}".format(flaghome, live.home_team, flagaway, live.away_team),
                           description="{} — {}".format(home, away), color=0x212223)
        em.set_footer(text="Score en live (BETA)", icon_url=furl)
        current = {live.home_team: live.result["home_team_goals"],
                   live.away_team: live.result["away_team_goals"]}
        await self.bot.say(embed=em)
        while live.status == "IN_PLAY" or self.reset is False:
            try:
                comp = self.foot.get_competition(467)
                for f in comp.get_fixtures():
                    vn = "{}-{}".format(f.home_team, f.away_team)
                    if vn == nom:
                        if f.status == "IN_PLAY":
                            live = f
                else:
                    if not live:
                        self.reset = True
                        continue
            except:
                pass
            new = {live.home_team: live.result["home_team_goals"], live.away_team: live.result["away_team_goals"]}
            if current != new:
                flaghome = ":flag_{}: ".format(self.cc.convert(names=live.home_team, to='ISO2').lower()) \
                    if self.cc.convert(names=live.home_team, to='ISO2').lower() != "not found" else ""
                flagaway = ":flag_{}: ".format(self.cc.convert(names=live.away_team, to='ISO2').lower()) \
                    if self.cc.convert(names=live.away_team, to='ISO2').lower() != "not found" else ""
                home = "**{}**".format(live.result["home_team_goals"]) if \
                    live.result["home_team_goals"] >= live.result["away_team_goals"] else "{}".format(
                    live.result["home_team_goals"])
                away = "**{}**".format(live.result["away_team_goals"]) if \
                    live.result["away_team_goals"] >= live.result["home_team_goals"] else "{}".format(
                    live.result["away_team_goals"])
                if new[live.home_team] > current[live.home_team]:
                    butteur = live.home_team
                else:
                    butteur = live.away_team
                em = discord.Embed(title="{}{} / {}{}".format(flaghome, live.home_team, flagaway, live.away_team),
                                   description="{} — {}\n+ But **{}**".format(home, away, butteur), color=0x212223)
                em.set_footer(text="Score en live (BETA)", icon_url=furl)
                current = {live.home_team: live.result["home_team_goals"],
                           live.away_team: live.result["away_team_goals"]}
                await self.bot.say(embed=em)
            await asyncio.sleep(31)

        await asyncio.sleep(5)
        self.reset = False
        livedebut = live.date + timedelta(hours=2)
        now = datetime.now()
        flaghome = ":flag_{}: ".format(self.cc.convert(names=live.home_team, to='ISO2').lower()) \
            if self.cc.convert(names=live.home_team, to='ISO2').lower() != "not found" else ""
        flagaway = ":flag_{}: ".format(self.cc.convert(names=live.away_team, to='ISO2').lower()) \
            if self.cc.convert(names=live.away_team, to='ISO2').lower() != "not found" else ""
        home = "**{}**".format(live.result["home_team_goals"]) if \
            live.result["home_team_goals"] >= live.result["away_team_goals"] else "{}".format(
            live.result["home_team_goals"])
        away = "**{}**".format(live.result["away_team_goals"]) if \
            live.result["away_team_goals"] >= live.result["home_team_goals"] else "{}".format(
            live.result["away_team_goals"])
        gagn = "Egalité"
        if live.result["home_team_goals"] > live.result["away_team_goals"]:
            gagn = live.home_team
        elif live.result["away_team_goals"] > live.result["home_team_goals"]:
            gagn = live.away_team
        em = discord.Embed(title="FIN | {}{} / {}{}".format(flaghome, live.home_team, flagaway, live.away_team),
                           description="{} — {}\nGagnant : **{}**".format(home, away, gagn), color=0x212223)
        em.set_footer(text="Fin du live".format(int((now - livedebut).seconds / 60)), icon_url=furl)
        await self.bot.say(embed=em)


    @_football.command(pass_context=True)
    async def notif(self, ctx):
        """Permet de s'abonner à un match pour recevoir une notification avant le démarrage"""
        author = ctx.message.author
        server = ctx.message.server
        comp = self.foot.get_competition(467)
        emojis = [s for s in "🇦🇧🇨🇩🇪🇫🇬🇭🇮🇯🇰🇱🇲🇳🇴🇵🇶🇷🇸🇹🇺🇻🇼🇽🇾🇿"]
        if "FOOT_SUB" not in self.sys:
            self.sys["FOOT_SUB"] = {}
            fileIO("data/labo/sys.json", "save", self.sys)
        if "SERV_CONV" not in self.sys:
            self.sys["SERV_CONV"] = {}
            fileIO("data/labo/sys.json", "save", self.sys)
        if author.id not in self.sys["SERV_CONV"]:
            self.sys["SERV_CONV"][author.id] = [server.id]
        elif server.id not in self.sys["SERV_CONV"][author.id]:
                self.sys["SERV_CONV"][author.id].append(server.id)
        msg = None
        while True:
            n = 0
            emolist = []
            fbl = []
            txt = ""
            for f in comp.get_fixtures():
                localdate = f.date + timedelta(hours=2)
                if not f.result:
                    nom = "{}-{}-{}".format(f.home_team_id, f.away_team_id, localdate.strftime("%d%m%Y%H%M"))
                    if nom in self.sys["FOOT_SUB"]:
                        if author.id in self.sys["FOOT_SUB"][nom]["ABON"]:
                            subbed = "✅"
                        else:
                            subbed = "❎"
                    else:
                        subbed = "❎"
                    fbl.append([emojis[n], f])
                    emolist.append(emojis[n])
                    flaghome = ":flag_{}:".format(self.cc.convert(names=f.home_team, to='ISO2').lower()) \
                        if self.cc.convert(names=f.home_team, to='ISO2').lower() != "not found" else ""
                    flagaway = ":flag_{}:".format(self.cc.convert(names=f.away_team, to='ISO2').lower()) \
                        if self.cc.convert(names=f.away_team, to='ISO2').lower() != "not found" else ""
                    txt += "{} | \{} — {} *{}* **VS** {} *{}*\n".format(subbed, emojis[n], flaghome, f.home_team,
                                                                        flagaway, f.away_team)
                    n += 1
                    if n == 5:
                        break

            em = discord.Embed(title="Abonnements matchs {} | Coupe du Monde Russie 2018".format(str(author)),
                               description=txt, color=0xedb83d)
            em.set_footer(text="Abonnez-vous en cliquant sur la lettre correspondante | 🚫 = Quitter")
            if msg:
                await self.bot.clear_reactions(msg)
                msg = await self.bot.edit_message(msg, embed=em)
            else:
                msg = await self.bot.say(embed=em)
            for e in emolist:
                await self.bot.add_reaction(msg, e)
            await self.bot.add_reaction(msg, "🚫")
            await asyncio.sleep(0.15)

            rep = await self.bot.wait_for_reaction(emolist + ["🚫"], message=msg, timeout=30,
                                                   check=self.check, user=author)
            if rep is None or rep.reaction.emoji == "🚫":
                await self.bot.delete_message(msg)
                return
            elif rep.reaction.emoji in emolist:
                for i in fbl:
                    if rep.reaction.emoji == i[0]:
                        f = i[1]
                        localdate = f.date + timedelta(hours=2)
                        nom = "{}-{}-{}".format(f.home_team_id, f.away_team_id, localdate.strftime("%d%m%Y%H%M"))
                        if nom not in self.sys["FOOT_SUB"]:
                            flaghome = ":flag_{}:".format(self.cc.convert(names=f.home_team, to='ISO2').lower()) \
                                if self.cc.convert(names=f.home_team, to='ISO2').lower() != "not found" else ""
                            flagaway = ":flag_{}:".format(self.cc.convert(names=f.away_team, to='ISO2').lower()) \
                                if self.cc.convert(names=f.away_team, to='ISO2').lower() != "not found" else ""
                            warn = localdate - timedelta(minutes=15)
                            self.sys["FOOT_SUB"][nom] = {"ABON": [],
                                                         "DATE": localdate.strftime("%d/%m/%Y %H:%M"),
                                                         "HOME": f.home_team,
                                                         "HOME_FLAG": flaghome,
                                                         "AWAY": f.away_team,
                                                         "AWAY_FLAG": flagaway,
                                                         "WARNING": warn.strftime("%d/%m/%Y %H:%M")}
                        if author.id not in self.sys["FOOT_SUB"][nom]["ABON"]:
                            self.sys["FOOT_SUB"][nom]["ABON"].append(author.id)
                            em.set_footer(text="— Vous vous êtes abonné au match {} VS {}".format(f.home_team,
                                                                                                  f.away_team))
                            await self.bot.edit_message(msg, embed=em)
                            await asyncio.sleep(2.5)
                        else:
                            self.sys["FOOT_SUB"][nom]["ABON"].remove(author.id)
                            em.set_footer(text="— Vous vous êtes désabonné du match {} VS {}".format(f.home_team,
                                                                                                  f.away_team))
                            await self.bot.edit_message(msg, embed=em)
                            await asyncio.sleep(2.5)
                fileIO("data/labo/sys.json", "save", self.sys)
            else:
                await self.bot.delete_message(msg)
                return

    @_football.command(pass_context=True)
    async def next(self, ctx):
        """Affiche les matchs du moment (terminés et à venir)"""
        comp = self.foot.get_competition(467)
        furl = "http://www.ohda.org/imgs/soccer-roll-logo.gif"
        today = datetime.now()
        date = lambda dt: dt.strftime("%d/%m")
        em = discord.Embed(title="Matchs")
        n = 0
        for f in comp.get_fixtures():
            localdate = f.date + timedelta(hours=2)
            if localdate.strftime("%d/%m") == today.strftime("%d/%m"):
                if f.result:
                    if f.status == "IN_PLAY":
                        n += 1
                        home = "**{}**".format(f.result["home_team_goals"]) if \
                            f.result["home_team_goals"] >= f.result["away_team_goals"] else "{}".format(
                            f.result["home_team_goals"])
                        away = "**{}**".format(f.result["away_team_goals"]) if \
                            f.result["away_team_goals"] >= f.result["home_team_goals"] else "{}".format(
                            f.result["away_team_goals"])
                        txt = "**LIVE :** {} — {}\n".format(home, away)
                        flaghome = ":flag_{}:".format(self.cc.convert(names=f.home_team, to='ISO2').lower()) \
                            if self.cc.convert(names=f.home_team, to='ISO2').lower() != "not found" else ""
                        flagaway = ":flag_{}:".format(self.cc.convert(names=f.away_team, to='ISO2').lower()) \
                            if self.cc.convert(names=f.away_team, to='ISO2').lower() != "not found" else ""
                        em.add_field(name="{} {} VS {} {}".format(flaghome, f.home_team, flagaway, f.away_team), value=txt, inline=False)
                    else:
                        n += 1
                        home = "**{}**".format(f.result["home_team_goals"]) if \
                            f.result["home_team_goals"] >= f.result["away_team_goals"] else "{}".format(f.result["home_team_goals"])
                        away = "**{}**".format(f.result["away_team_goals"]) if \
                            f.result["away_team_goals"] >= f.result["home_team_goals"] else "{}".format(f.result["away_team_goals"])
                        txt = "**Terminé :** {} — {}\n".format(home, away)
                        flaghome = ":flag_{}:".format(self.cc.convert(names=f.home_team, to='ISO2').lower()) \
                            if self.cc.convert(names=f.home_team, to='ISO2').lower() != "not found" else ""
                        flagaway = ":flag_{}:".format(self.cc.convert(names=f.away_team, to='ISO2').lower()) \
                            if self.cc.convert(names=f.away_team, to='ISO2').lower() != "not found" else ""
                        em.add_field(name="{} {} VS {} {}".format(flaghome, f.home_team, flagaway, f.away_team), value=txt, inline=False)
                else:
                    n += 1
                    if f.odds:
                        odds = "{} - {} - {}".format(f.odds["home_win"], f.odds["draw"], f.odds["away_win"])
                    else:
                        odds = ""
                    txt = "**{}**\n{}\n".format(localdate.strftime("Aujourd'hui à %H:%M"), odds)
                    flaghome = ":flag_{}:".format(self.cc.convert(names=f.home_team, to='ISO2').lower()) \
                        if self.cc.convert(names=f.home_team, to='ISO2').lower() != "not found" else ""
                    flagaway = ":flag_{}:".format(self.cc.convert(names=f.away_team, to='ISO2').lower()) \
                        if self.cc.convert(names=f.away_team, to='ISO2').lower() != "not found" else ""
                    em.add_field(name="{} {} VS {} {}".format(flaghome, f.home_team, flagaway, f.away_team), value=txt, inline=False)
            elif localdate >= today:
                n += 1
                if f.odds:
                    odds = "{} - {} - {}".format(f.odds["home_win"], f.odds["draw"], f.odds["away_win"])
                else:
                    odds = ""
                txt = "**{}**\n{}\n".format(localdate.strftime("%d/%m %H:%M"), odds)
                flaghome = ":flag_{}:".format(self.cc.convert(names=f.home_team, to='ISO2').lower()) \
                    if self.cc.convert(names=f.home_team, to='ISO2').lower() != "not found" else ""
                flagaway = ":flag_{}:".format(self.cc.convert(names=f.away_team, to='ISO2').lower()) \
                    if self.cc.convert(names=f.away_team, to='ISO2').lower() != "not found" else ""
                em.add_field(name="{} {} VS {} {}".format(flaghome, f.home_team, flagaway, f.away_team), value=txt, inline=False)
            if n == 5:
                break
        em.set_footer(text="Coupe du Monde 2018 en Russie", icon_url=furl)
        await self.bot.say(embed=em)

    def normalize(self, texte: str):
        texte = texte.lower()
        norm = [l for l in "neeecaiiuuo"]
        modif = [l for l in "ñéèêçàîïûùö"]
        fin_texte = texte
        for char in texte:
            if char in modif:
                ind = modif.index(char)
                fin_texte = fin_texte.replace(char, norm[ind])
        return fin_texte

    def rolex(self, texte: str):
        """Permet d'extraire des informations temporelles d'un message en français"""
        date = datetime.now()
        annee = date.year
        texte = self.normalize(texte)
        out = re.compile(r'(apres[-\s]?demain)', re.DOTALL | re.IGNORECASE).findall(texte)
        out2 = re.compile(r'(demain)', re.DOTALL | re.IGNORECASE).findall(texte)
        if out:
            date = date + timedelta(days=2)
        elif out2:
            date = date + timedelta(days=1)
        out = re.compile(r'(avant[-\s]?hier)', re.DOTALL | re.IGNORECASE).findall(texte)
        out2 = re.compile(r'(hier)', re.DOTALL | re.IGNORECASE).findall(texte)
        if out:
            date = date - timedelta(days=2)
        elif out2:
            date = date - timedelta(days=1)
        out = re.compile(r'(lundi|mardi|mercredi|jeudi|vendredi|samedi|dimanche)\s(?=prochaine?)',
                         re.DOTALL | re.IGNORECASE).findall(texte)
        if out:  # On est obligé de traduire, datetime ne supporte pas le français
            if out[0] == "lundi":
                wd = 0
            elif out[0] == "mardi":
                wd = 1
            elif out[0] == "mercredi":
                wd = 2
            elif out[0] == "jeudi":
                wd = 3
            elif out[0] == "vendredi":
                wd = 4
            elif out[0] == "samedi":
                wd = 5
            else:
                wd = 6
            date = date + timedelta(((wd-1)-date.weekday()) % 7+1)

        out = re.compile(r'(semaine)\s(?=prochaine?)', re.DOTALL | re.IGNORECASE).findall(texte)
        if out:
            date = date + timedelta(weeks=1)

        out = re.compile(r'(tou[ts]\s?a\s?l\'?heure)', re.DOTALL | re.IGNORECASE).findall(texte)
        if out:
            date = date + timedelta(hours=4)

        out = re.compile(r'(soire?e?)', re.DOTALL | re.IGNORECASE).findall(texte)
        if out:
            date = date.replace(hour=20, minute=0, second=0)

        out = re.compile(r'(journee?)', re.DOTALL | re.IGNORECASE).findall(texte)
        if out:
            date = date.replace(hour=15, minute=0, second=0)

        out = re.compile(r'(midi)', re.DOTALL | re.IGNORECASE).findall(texte)
        if out:
            date = date.replace(hour=12, minute=0, second=0)

        out = re.compile(r'(apres[-\s]?midi|aprem)', re.DOTALL | re.IGNORECASE).findall(texte)
        if out:
            date = date.replace(hour=13, minute=0, second=0)

        out = re.compile(r'(minuit)', re.DOTALL | re.IGNORECASE).findall(texte)
        if out:
            date = date.replace(hour=0, minute=0, second=0)

        out = re.compile(r'(matin)', re.DOTALL | re.IGNORECASE).findall(texte)
        if out:
            date = date.replace(hour=9, minute=0, second=0)

        out = re.compile(r'(trois[-\s]?quart)', re.DOTALL | re.IGNORECASE).findall(texte)
        out2 = re.compile(r'(quart)', re.DOTALL | re.IGNORECASE).findall(texte)
        out3 = re.compile(r'(demie?)', re.DOTALL | re.IGNORECASE).findall(texte)
        out4 = re.compile(r'(moins[-\s]?(?:le\s?)?quart)', re.DOTALL | re.IGNORECASE).findall(texte)
        modif = False
        if out:
            modif = "tq"
        elif out4:
            modif = "mq"
        elif out2:
            modif = "q"
        elif out3:
            modif = "d"

        out = re.compile(r'([0-2]?[0-9])[:h]([0-5][0-9])?', re.DOTALL | re.IGNORECASE).findall(texte)
        if out:
            out = out[0]
            if not modif:
                date = date.replace(hour=int(out[0]), minute=int(out[1]) if out[1] else 0, second=0)
            else:
                date = date.replace(hour=int(out[0]), second=0)

        out = re.compile(r'(\d{1,2})[\/.-](\d{1,2})[\/.-](\d{4})', re.DOTALL | re.IGNORECASE).findall(texte)
        if out:
            out = out[0]
            date = date.replace(day=int(out[0]), month=int(out[1]), year=int(out[2]))

        if modif == "tq":
            date = date.replace(minute=45)
        elif modif == "mq":
            date = date.replace(minute=45)
            date = date - timedelta(hours=1)
        elif modif == "q":
            date = date.replace(minute=15)
        elif modif == "tq":
            date = date.replace(minute=30)

        out = re.compile(r'(\d{1,2})\s?(septembre|octobre|novembre|decembre|janvier|fevrier|mars|avril|mai|juin'
                         r'|juillet|aout)\s?(\d{4})?', re.DOTALL | re.IGNORECASE).findall(texte)
        if out:
            out = out[0]
            if out[1] == "janvier":
                m = 1
            elif out[1] == "fevrier":
                m = 2
            elif out[1] == "mars":
                m = 3
            elif out[1] == "avril":
                m = 4
            elif out[1] == "mai":
                m = 5
            elif out[1] == "juin":
                m = 6
            elif out[1] == "juillet":
                m = 7
            elif out[1] == "aout":
                m = 8
            elif out[1] == "septembre":
                m = 9
            elif out[1] == "octobre":
                m = 10
            elif out[1] == "novembre":
                m = 11
            else:
                m = 12
            date = date.replace(day=int(out[0]), month=m, year=int(out[2]) if out[2] else int(annee))

        out = re.compile(r'dans\s?(\d+)\s?(heures? | minutes?| jours? | semaines? |[hmj])(\d{1,2})?',
                         re.DOTALL | re.IGNORECASE).findall(texte)
        if out:
            out = out[0]
            if out[1] in ["h", "heure", "heures"]:
                r = out[0]
                if int(out[0]) >= 24:
                    jours = int(out[0] / 24)
                    date = date + timedelta(days=jours)
                    r = out[0] - (jours * 24)
                date = date + timedelta(hours=int(r))
                if out[2]:
                    date = date + timedelta(minutes=int(out[2]))
            elif out[1] in ["m", "minute", "minutes"]:
                date = date + timedelta(minutes=int(out[0]))
            elif out[1] in ["semaine", "semaines"]:
                date = date + timedelta(weeks=int(out[0]))
            else:
                date = date + timedelta(days=int(out[0]))

        out = re.compile(r'(la\s?veill?e)', re.DOTALL | re.IGNORECASE).findall(texte)
        if out:
            date = date - timedelta(days=1)

        return date

    @commands.command(pass_context=True, hidden=True)
    async def getchans(self, ctx):
        """Récupérer les channels du serveur (TEST)"""
        server = ctx.message.server
        channels = [channel.name for channel in server.channels if type(channel.type) != int]
        txt = "\n".join(channels)
        await self.bot.say(txt)

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
    async def jeu(self, ctx):
        """???"""
        user = ctx.message.author
        if user.id == "212312231428227072":
            await self.bot.send_message(self.bot.get_channel("395316684292096005"), "Lasagne à lancé le JEU")
            name = user.name
            await asyncio.sleep(7)
            await self.bot.whisper("**Jeu** - Localiser et tuer {}".format(name))
            await asyncio.sleep(4)
            await self.bot.send_typing(user)
            await asyncio.sleep(5)
            await self.bot.whisper("Bon, déjà on va essayer de trouver son adresse...")
            await asyncio.sleep(15)
            await self.bot.send_typing(user)
            await asyncio.sleep(8)
            await self.bot.whisper("Ah oui ! Tu avais posté une image le 2 juin et une autre vers janvier, "
                                        "on va pouvoir chopper les adresses :)")
            await asyncio.sleep(24)
            await self.bot.send_typing(user)
            await asyncio.sleep(4)
            await self.bot.whisper("N'en parle à personne, ça ne fera qu'accélérer les choses...")
            await asyncio.sleep(14)
            await self.bot.send_typing(user)
            await asyncio.sleep(8)
            await self.bot.whisper("Voilà. Bon j'AFK une minute faut que j'aille me préparer pour aller sur place...")
            await asyncio.sleep(54)
            await self.bot.send_typing(user)
            await asyncio.sleep(7)
            await self.bot.whisper("Celui-là fera l'affaire "
                                   "http://image.noelshack.com/fichiers/2018/24/6/1529185515-jpeg-20180616-234411.jpg")
            await asyncio.sleep(35)
            await self.bot.send_typing(user)
            await asyncio.sleep(3)
            await self.bot.whisper("Bon voilà, fin prêt. "
                                   "http://image.noelshack.com/fichiers/2018/24/6/1529185353-img-20180616-234127.jpg")
            await asyncio.sleep(24)
            await self.bot.send_typing(user)
            await asyncio.sleep(8)
            heure = int(time.strftime("%H", time.localtime()))
            if 22 <= heure <= 5:
                bye = "bonne *dernière* nuit"
            elif 6 <= heure <= 10:
                bye = "bonne matinée"
            elif heure == 11 or heure == 12 or heure == 13:
                bye = "bon appétit, savoure ton dernier repas"
            elif 14 <= heure <= 18:
                bye = "bonne aprem'"
            else:
                bye = "bonne soirée"
            await self.bot.whisper("Je vais couper j'ai plus beaucoup de batterie. On se retrouve sur place, "
                                   "allez à plus tard et {} !".format(bye))
            await asyncio.sleep(64800)
            await self.bot.send_typing(user)
            await asyncio.sleep(1)
            await self.bot.whisper("**Bouh.**")
        else:
            await self.bot.whisper("Désolé, c'est **Lasagne** que je cherche.")


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
        if not server:
            return
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
    bot.add_listener(n.read_suppr, "on_message_delete")
    bot.add_listener(n.read_edit, "on_message_edit")
    bot.add_listener(n.reactrecap, "on_reaction_add")
    bot.add_cog(n)
