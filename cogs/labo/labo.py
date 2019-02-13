
import asyncio
import os
import re
import time
import random
from collections import namedtuple
from datetime import datetime, timedelta

import country_converter as coco
import discord
import pyfootball
from discord.ext import commands

from .utils import checks
from .utils.dataIO import fileIO, dataIO


class Labo:
    """Module poubelle d'expérimentation et commandes random - parfois des trucs sympa en sortent !"""
    def __init__(self, bot):
        self.bot = bot
        self.sys = dataIO.load_json("data/labo/sys.json")  # Pas très utile mais on le garde pour plus tard
        self.sys_def = {"REPOST": [], "FOOT_SUB": {}, "SERV_CONV": {}, "ETUDES_STATS": {}}
        self.msg = dataIO.load_json("data/labo/msg.json")
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

    def discord_detect(self, server, obj):
        """Détecte le type de l'objet Discord"""
        if obj.startswith("<@&"):
            obj = obj.replace("<@&", "")
            obj = obj.replace(">", "")
            for role in server.roles:
                if role.id == obj:
                    return role
        elif obj.startswith("<@"):
            obj = obj.replace("<@", "")
            obj = obj.replace(">", "")
            return server.get_member(obj)
        elif obj.startswith("<#"):
            obj = obj.replace("<#", "")
            obj = obj.replace(">", "")
            for channel in server.channels:
                if channel.id == obj:
                    return channel
        else:
            user = server.get_member_named(obj)
            if user:
                return user
            for channel in server.channels:
                if channel.name.lower() == obj.lower():
                    return channel
            for role in server.roles:
                if role.name.lower() == obj.lower():
                    return role
            for member in server.members:
                if member.name.lower() == obj.lower():
                    return member
                if member.display_name.lower() == obj.lower():
                    return member
            return None

    def get_info(self, user: discord.Member):
        return user.name

    @commands.command(pass_context=True)
    async def supinfo(self, ctx, user: discord.User):
        """Retrouve les informations du membre"""
        await self.bot.say(self.get_info(user))

    @commands.command(aliases=["triso"], pass_context=True)
    async def trisomize(self, ctx, *texte):
        """Trisomise le texte donné, basé sur le délire chelou de Koala et Francis

        --- Options ---
        Ajouter une lettre : -ajout -add -plus -p
        Retirer une lettre : -retirer -remove -moins -m
        Mixer les lettres : -mix -shuffle -melange -s
        Remplacer une lettre : -replace -remplace -r
        Alterner Maj/Min : -alterner -majmin -a
        Ne pas mettre en minuscule : -nolower -nl"""
        texte = list(texte)
        opts = [r for r in texte if r.startswith("-")]
        # avl = ["-mix", "-shuffle", "-melange", "-ajout", "-add", "-plus", "-moins", "-retirer", "-remove",
        # "-replace", "-remplace", "-s", "-p", "-m", "-r", "-nolower", "-nl"]
        if not opts or opts == ["-nl"] or opts == ["-nolower"]:
            opts.append("-s")
            opts.append(random.choice(["-m", "-p", "-r"]))
        for i in opts:
            if i in texte:
                texte.remove(i)
        s = []
        char = [i for i in "abcdefghijklmnopqrstuvwxyz"]

        def comparelist(l1: list, l2: list):
            for _ in l1:
                if _ in l2:
                    return _
            return False

        for t in texte:
            if comparelist(opts, ["-replace", "-remplace", "-r"]):
                rdn = random.randint(0, len(t) - 1)
                t = t.replace(t[rdn], random.choice(char), 1)
            if comparelist(opts, ["-moins", "-retirer", "-remove", "-m"]):
                t = t.replace(random.choice([_ for _ in t]), "", 1)
            if comparelist(opts, ["-ajout", "-add", "-plus", "-p"]):
                place = random.randint(0, len(t) - 1)
                t = t[:place] + random.choice(char) + t[place:]
            if comparelist(opts, ["-mix", "-shuffle", "-melange", "-s"]):
                t = ''.join(random.sample(t, len(t)))
            if comparelist(opts, ["-majmin", "-alterner", "-a"]):
                t = t if comparelist(opts, ["-nolower", "-nl"]) else t.lower()
                n = 0
                txtl = []
                for i in t:
                    if n % 2 == 0:
                        if i != "i":
                            txtl.append(i.upper())
                            n += 1
                            continue
                        else:
                            txtl.append(i)
                            continue
                    txtl.append(i)
                    n += 1
                t = "".join(txtl)
            else:
                if not comparelist(opts, ["-nolower", "-nl"]):
                    t = t.lower()
            s.append(t)
        if s:
            await self.bot.say(" ".join(s))
        else:
            await self.bot.say(random.choice(["Ce ne serait pas vous le triso qui ne sait pas utiliser cette commande ?",
                                              "Vous oubliez pas quelque chose ?", "Oui d'accord, mais pour quel texte ?",
                                              "Il n'y a pas que les options dans la vie.", "C'est bien beau de me donner les options mais pour quel texte ?",
                                              "Hey, c'est toi le triso, c'est sur quel texte que je dois appliquer ces options ?"]))

    @commands.command(pass_context=True)
    @checks.admin_or_permissions(ban_members=True)
    async def msgstats(self, ctx, maxnb: int = 10000000, channel: discord.Channel = None):
        """Réalise des statistiques sur les messages d'un channel

        Si un message est illisible (expiré ou buggué) il est ignoré."""
        if not channel:
            channel = ctx.message.channel
        server = channel.server
        await self.bot.say("**Récolte de statistiques sur les Messages** | Cela peut prendre beaucoup de temps si "
                           "l'échantillon est important (> 30j).")
        nbjour = nbmsg = nbmots = nblets = 0
        userdata = {}
        day = ""
        async for msg in self.bot.logs_from(channel, limit=maxnb):
            if nbmsg == (0.05 * maxnb):
                await self.bot.say("**Analyse** | Env. 5%")
            if nbmsg == (0.15 * maxnb):
                await self.bot.say("**Analyse** | Env. 15%")
            if nbmsg == (0.25 * maxnb):
                await self.bot.say("**Analyse** | Env. 25%")
            if nbmsg == (0.35 * maxnb):
                await self.bot.say("**Analyse** | Env. 35%")
            if nbmsg == (0.45 * maxnb):
                await self.bot.say("**Analyse** | Env. 45%")
            if nbmsg == (0.55 * maxnb):
                await self.bot.say("**Analyse** | Env. 55%")
            if nbmsg == (0.65 * maxnb):
                await self.bot.say("**Analyse** | Env. 65%")
            if nbmsg == (0.75 * maxnb):
                await self.bot.say("**Analyse** | Env. 75%")
            if nbmsg == (0.85 * maxnb):
                await self.bot.say("**Analyse** | Env. 85%")
            if nbmsg == (0.95 * maxnb):
                await self.bot.say("**Analyse** | Env. 95% - Bientôt terminée")
            nbmsg += 1
            if day != msg.timestamp.strftime("%d/%m/%Y"):
                day = msg.timestamp.strftime("%d/%m/%Y")
                nbjour += 1
            author = msg.author
            mots = len(msg.content.split())
            nbmots += mots
            lettres = len(msg.content)
            nblets += lettres
            if day not in userdata:
                userdata[day] = {}
            if author.id not in userdata[day]:
                userdata[day][author.id] = {"NB_MSG": 0,
                                            "NB_MOTS": 0,
                                            "NB_LETS": 0}
            userdata[day][author.id]["NB_MSG"] += 1
            userdata[day][author.id]["NB_MOTS"] += mots
            userdata[day][author.id]["NB_LETS"] += lettres
        await self.bot.say("**Analyse terminée** | Patientez pendant que j'imprime et upload les résultats...")
        daydata = {}
        for d in userdata:
            if d not in daydata:
                daydata[d] = {"NB_MSG": 0,
                              "NB_MOTS": 0,
                              "NB_LETS": 0}
            daydata[d]["NB_MSG"] = sum([userdata[d][a]["NB_MSG"] for a in userdata[d]])
            daydata[d]["NB_MOTS"] = sum([userdata[d][a]["NB_MOTS"] for a in userdata[d]])
            daydata[d]["NB_LETS"] = sum([userdata[d][a]["NB_LETS"] for a in userdata[d]])
        ud = {}
        for d in userdata:
            for u in userdata[d]:
                if u not in ud:
                    ud[u] = {"NB_MSG": 0,
                             "NB_MOTS": 0,
                             "NB_LETS": 0}
                ud[u]["NB_MSG"] += userdata[d][u]["NB_MSG"]
                ud[u]["NB_MOTS"] += userdata[d][u]["NB_MOTS"]
                ud[u]["NB_LETS"] += userdata[d][u]["NB_LETS"]
        txt = "STATS GENERALES\n\n" \
              "Nb jours analyses\t{}\n" \
              "Nb msg analyses\t{}\n" \
              "Nb mots\t{}\n" \
              "Nb lettres\t{}\n".format(nbjour, nbmsg, nbmots, nblets)
        txt += "\nSTATS PAR JOUR\nDate / Nb. msg / Nb. mots / Nb. lettres\n"
        for d in daydata:
            txt += "{}\t{}\t{}\t{}\n".format(d, daydata[d]["NB_MSG"], daydata[d]["NB_MOTS"], daydata[d]["NB_LETS"])
        txt += "\nSTATS PAR MEMBRE\nMembre / Nb. msg / Nb. mots / Nb. lettres\n"
        for u in ud:
            if u in [i.id for i in server.members]:
                user = server.get_member(u).name
            else:
                user = u
            txt += "{}\t{}\t{}\t{}\n".format(user, ud[u]["NB_MSG"], ud[u]["NB_MOTS"],
                                             ud[u]["NB_LETS"])
        txt += "\n\n# Il est possible de Copier/Coller directement chacune de ces categories dans un tableur\n" \
               "# Certains messages peuvent devenir inaccessibles si ils datent de plus d'un an, ce qui peut fausser " \
               "les resultats\n" \
               ""
        filename = "STATSMessages_Juillet2018"
        file = open("data/labo/{}.txt".format(filename), "w", encoding="utf-8")
        file.write(txt)
        file.close()
        try:
            await self.bot.send_file(ctx.message.channel, "data/labo/{}.txt".format(filename))
            os.remove("data/labo/{}.txt".format(filename))
        except:
            await self.bot.say("**Erreur** | Je n'arrive pas à upload le fichier.")

    @commands.command(pass_context=True)
    async def dtype(self, ctx, objet):
        """Détecte le type de l'objet soumis"""
        obj = self.discord_detect(ctx.message.server, objet)
        if type(obj) == discord.Channel:
            await self.bot.say("Channel: {}".format(obj.mention))
        elif type(obj) == discord.Role:
            await self.bot.say("Rôle: {}".format(obj.mention))
        elif type(obj) == discord.Member:
            await self.bot.say("Membre: {}".format(obj.mention))
        else:
            await self.bot.say("Inconnu")

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
            file.write(datxt)
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



    @commands.command(aliases=["estcelevraiacrown", "sjlva", "eclva"], pass_context=True)
    async def suisjelevraiacrown(self, ctx, membre: discord.Member = None):
        """Suis-je le vrai Acrown ?"""
        ida = "172376505354158080"
        m = ctx.message.author.id if not membre else membre.id
        if m == ida:
            await self.bot.say("Identifiant valide, c'est le vrai Acrown.")
        else:
            await self.bot.say("Identifiant invalide, ce n'est pas le vrai Acrown.")



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
