import asyncio
import os
import random
import time
from copy import deepcopy
from collections import namedtuple

import discord
from __main__ import send_cmd_help
from cogs.utils.dataIO import fileIO, dataIO
from discord.ext import commands

from .utils import checks


class KarmaAPI:
    """API de Karma | Fonctionnalités de modération avancées"""

    def __init__(self, bot, path):
        self.bot = bot
        self.data = dataIO.load_json(path)
        self.cycle = bot.loop.create_task(self.karma_loop())

    def save(self):
        fileIO("data/karma/data.json", "save", self.data)
        return True

    async def karma_loop(self):
        await self.bot.wait_until_ready()
        try:
            await asyncio.sleep(5)  # Temps de mise en route
            while True:
                for serv in self.data:
                    for user in self.data[serv]["USERS"]:
                        if self.data[serv]["USERS"][user]["KARMA"] < 5:
                            self.data[serv]["USERS"][user]["KARMA"] += 1
                print("-> Karma +1 pour tous (Succès)")
                await asyncio.sleep(86400)
        except asyncio.CancelledError:
            pass

    def search_obj(self, server: discord.Server, obj):
        """Recherche quel Objet lui est donné et renvoie celui-ci"""
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

    def get_server(self, server: discord.Server):
        """Renvoie les données du serveur"""
        if server.id not in self.data:
            self.data[server.id] = {"OPTS": {"prison_role": None,
                                             "prison_salon": None,
                                             "prison_msgsalon": None,
                                             "filtre": {},
                                             "logs_salons": {}},
                                    "USERS": {}}
            self.save()
        return self.data[server.id]

    def get_casier(self, user: discord.Member):
        """Renvoie les données du membre"""
        s = self.get_server(user.server)
        if user.id not in s["USERS"]:
            s["USERS"][user.id] = {"LOGS": [],
                                   "KARMA": 5,
                                   "PUBLIC_NOTE": "",
                                   "SUIVI": False}
            self.save()
        return s["USERS"][user.id]

    async def send_log(self, server: discord.Server, logtype: str, titre: str, texte: str):
        """Envoie un log sur le bon channel"""
        sys = self.get_server(server)["OPTS"]["logs_salons"]
        for chan in sys:
            if logtype.lower() in sys[chan]:
                em = discord.Embed(title=titre, description=texte)
                em.set_footer(text="─ {}".format(logtype.lower()))
                channel = server.get_channel(chan)
                await self.bot.send_message(channel, embed=em)
                return True
        return False

    def get_karma(self, user: discord.Member, modif: int = None):
        """Renvoie le Karma du membre et le modifie si besoin (de 5 à -5)"""
        case = self.get_casier(user)
        if modif:
            if modif > 0:
                case["KARMA"] += modif if case["KARMA"] < 5 else 0
                if case["KARMA"] > 5:
                    case["KARMA"] = 5
            elif modif < 0:
                case["KARMA"] -= abs(modif) if case["KARMA"] > -5 else 0
                if case["KARMA"] < -5:
                    case["KARMA"] = -5
            self.save()
        return case["KARMA"]

    def add_event(self, user: discord.Member, symbole: str, texte: str):
        """Rajoute un event aux logs personnels du membre"""
        case = self.get_casier(user)
        jour = time.strftime("%d/%m/%Y", time.localtime())
        heure = time.strftime("%H:%M", time.localtime())
        case["LOGS"].append([jour, heure, symbole, texte])
        case["LOGS"] = case["LOGS"][-20:]
        return case["LOGS"][-1]

class Karma:
    """Fonctionnalités de modération avancées"""
    def __init__(self, bot):
        self.bot = bot
        self.api = KarmaAPI(bot, "data/karma/data.json")
        self.session = {}

    def get_session(self, server: discord.Server):
        """Retourne la session en cours de Karma"""
        if server.id not in self.session:
            self.session[server.id] = {"PRISON": {},
                                       "MSG_PRISON": [],
                                       "SLOW": {},
                                       "GLOBAL_SLOW": False}
        return self.session[server.id]

    def get_prison_role(self, server: discord.Server):
        """Retourne le rôle de la prison"""
        serv = self.api.get_server(server)["OPTS"]
        for role in server.roles:
            if role.id == serv["prison_role"]:
                return role
        return None

    def convert_sec(self, form: str, val: int):
        """Convertit le temps donné en m, h ou j en secondes"""
        if form == "j":
            return val * 86400
        elif form == "h":
            return val * 3600
        elif form == "m":
            return val * 60
        else:
            return val

    async def tgl_prison(self, ctx, server: discord.Server, obj, temps: str = "10m"):
        """Ajoute ou retire un membre/rôle en prison"""
        obj = self.api.search_obj(server, obj)
        today = time.strftime("%d/%m", time.localtime())
        serv = self.api.get_server(server)
        session = self.get_session(server)
        form = temps[-1:]  # Format du temps
        prschannel = self.bot.get_channel(serv["OPTS"]["prison_salon"])
        prsrole = self.get_prison_role(server)
        prsmsg = self.bot.get_channel(serv["OPTS"]["prison_msgsalon"]) if serv["OPTS"]["prison_msgsalon"] else False
        if server.id not in session["PRISON"]:
            session["PRISON"] = {}
            session["MSG_PRISON"] = []
        if prsrole:
            if form.lower() in ["s", "m", "h", "j"]:
                if type(obj) == discord.Member:
                    user = obj
                    if temps.startswith("+") or temps.startswith("-"):
                        val = temps.replace(form, "")
                        val = int(val.replace(temps[0], ""))
                        if user.id in session["PRISON"]:
                            if prsrole in [r.name for r in user.roles]:
                                modif = self.convert_sec(form, val)
                                if temps[0] == "+":
                                    session["PRISON"][user.id]["SORTIE"] += modif
                                    await self.api.send_log(server, "prison", "Temps de prison",
                                                            "Ajout de **{}{}** pour **{}**".format(
                                                                val, form, user.mention))
                                    estim = time.strftime("%H:%M", time.localtime(session["PRISON"][user.id]["SORTIE"]))
                                    estimdate = time.strftime("%d/%m", time.localtime(
                                        session["PRISON"][user.id]["SORTIE"]))
                                    msg = "{} ─ Ajout de **{}{}** de peine".format(user.mention, val, form)
                                    if estimdate == today:
                                        estim_txt = "Sortie estimée à {}".format(estim)
                                    else:
                                        estim_txt = "Sortie estimée le {} à {}".format(estimdate, estim)

                                    emp = discord.Embed(description="**Peine augmentée** ─ **+{}{}** par *{}*".format(
                                        val, form, ctx.message.author.name), color=prsrole.color)
                                    if estimdate == today:
                                        emp.set_footer(text="Sortie prévue à {}".format(estim))
                                    else:
                                        emp.set_footer(text="Sortie prévue le {} à {}".format(estimdate, estim))
                                    try:
                                        await self.bot.send_message(user, embed=emp)
                                    except:
                                        if prschannel:
                                            await self.bot.send_message(prschannel, embed=emp)

                                    em = discord.Embed(description=msg, color=prsrole.color)
                                    em.set_footer(text=estim_txt)
                                    notif = await self.bot.say(embed=em)
                                    await asyncio.sleep(10)
                                    await self.bot.delete_message(notif)

                                elif temps[0] == "-":
                                    session["PRISON"][user.id]["SORTIE"] -= modif
                                    await self.api.send_log(server, "prison", "Temps de prison",
                                                            "Réduction de **{}{}** pour **{}**".format(
                                                                val, form, user.mention))
                                    if session["PRISON"][user.id]["SORTIE"] < time.time():
                                        estim = time.strftime("%H:%M", time.localtime())
                                        estimdate = time.strftime("%d/%m", time.localtime())
                                    else:
                                        estim = time.strftime("%H:%M", time.localtime(
                                            session["PRISON"][user.id]["SORTIE"]))
                                        estimdate = time.strftime("%d/%m", time.localtime(
                                            session["PRISON"][user.id]["SORTIE"]))
                                    msg = "{} ─ Réduction de **{}{}** de peine".format(user.mention, val, form)
                                    if estimdate == today:
                                        estim_txt = "Sortie estimée à {}".format(estim)
                                    else:
                                        estim_txt = "Sortie estimée le {} à {}".format(estimdate, estim)

                                    emp = discord.Embed(description="**Peine réduite** ─ **-{}{}** par *{}*".format(
                                        val, form, ctx.message.author.name), color=prsrole.color)
                                    if estimdate == today:
                                        emp.set_footer(text="Sortie prévue à {}".format(estim))
                                    else:
                                        emp.set_footer(text="Sortie prévue le {} à {}".format(estimdate, estim))
                                    try:
                                        await self.bot.send_message(user, embed=emp)
                                    except:
                                        if prschannel:
                                            await self.bot.send_message(prschannel, embed=emp)

                                    em = discord.Embed(description=msg, color=prsrole.color)
                                    em.set_footer(text=estim_txt)
                                    notif = await self.bot.say(embed=em)
                                    await asyncio.sleep(10)
                                    await self.bot.delete_message(notif)
                                else:
                                    await self.bot.say("**Symbole non reconnu** — `+` = Ajouter / `-` = Réduire")
                                    return
                            else:
                                if temps[0] == "+":
                                    await self.tgl_prison(server, user, temps.replace("+", ""))
                                else:
                                    await self.bot.say("**Echec** — Le membre n'est pas en prison (Absence de rôle)")
                                    return
                        else:
                            if temps[0] == "+":
                                await self.tgl_prison(server, user, temps.replace("+", ""))
                            else:
                                await self.bot.say("**Echec** — Le membre n'est pas en prison (Non-enregistré)")
                                return
                    else:
                        val = int(temps.replace(form, ""))
                        sec = self.convert_sec(form, val)
                        if sec < 60:
                            sec = 60  # Au moins une minute
                        warn = False
                        if sec > 86400:
                            warn = await self.bot.say("**Attention** — Une telle durée ne permet pas de garantir "
                                                      "la sortie automatique du membre lorsqu'il aura purgé sa peine.")
                        if user.id not in session["PRISON"]:
                            session["PRISON"][user.id] = {"ENTREE": 0,
                                                               "SORTIE": 0}
                        if prsrole not in [r.name for r in user.roles]:
                            b_peine = time.time()
                            session["PRISON"][user.id]["ENTREE"] = b_peine
                            session["PRISON"][user.id][" SORTIE"] = b_peine + sec
                            await self.bot.add_roles(user, prsrole)
                            msg = "{} ─ Mise en prison pour **{}{}**".format(user.mention, val, form)
                            await self.api.send_log(server, "prison", "Mise en prison",
                                                    "**{}** vient de mettre **{}** en prison pour **{}{}**".format(
                                                        ctx.message.author.mention, user.mention, val, form))
                            estim = time.strftime("%H:%M", time.localtime(session["PRISON"][user.id]["SORTIE"]))
                            estimdate = time.strftime("%d/%m", time.localtime(
                                session["PRISON"][user.id]["SORTIE"]))
                            if estimdate == today:
                                estim_txt = "Sortie estimée à {}".format(estim)
                            else:
                                estim_txt = "Sortie estimée le {} à {}".format(estimdate, estim)
                            if prschannel:
                                txt = "\n• Vous avez accès au salon *{}* pour toute réclamation".format(prschannel)
                            else:
                                txt = ""
                            if prsmsg:
                                txt += "\n• Vous avez le droit d'envoyer un dernier message avec `{}msg`".format(
                                    ctx.prefix)
                                if user.id not in session["MSG_PRISON"]:
                                    session["MSG_PRISON"].append(user.id)

                            emp = discord.Embed(description="**Peine de prison** ─ **{}{}** par *{}*{}".format(
                                val, form, ctx.message.author.name, txt), color=prsrole.color)
                            if estimdate == today:
                                emp.set_footer(text="Sortie prévue à {}".format(estim))
                            else:
                                emp.set_footer(text="Sortie prévue le {} à {}".format(estimdate, estim))
                            try:
                                await self.bot.send_message(user, embed=emp)
                            except:
                                if prschannel:
                                    await self.bot.send_message(prschannel, "{}".format(user.mention))
                                    await self.bot.send_message(prschannel, embed=emp)

                            em = discord.Embed(description=msg, color=prschannel.color)
                            em.set_footer(text=estim_txt)
                            notif = await self.bot.say(embed=em)
                            await asyncio.sleep(10)
                            await self.bot.delete_message(notif)
                            if warn:
                                await self.bot.delete_message(warn)

                            while time.time() < session["PRISON"][user.id]["SORTIE"]:
                                await asyncio.sleep(0.75)  # TIMER ============#

                            if user in server.members:
                                if prsrole in [r.name for r in user.roles]:
                                    session["PRISON"][user.id]["ENTREE"] = \
                                        session["PRISON"][user.id]["SORTIE"] = 0
                                    await self.bot.remove_roles(user, prsrole)
                                    await self.api.send_log(server, "prison", "Sortie de prison",
                                                            "Peine de **{}** terminée".format(user.mention))
                                    if user.id in session["MSG_PRISON"]:
                                        session["MSG_PRISON"].remove(user.id)
                                    em = discord.Embed(description="**Peine de prison** ─ Vous êtes désormais libre",
                                                       color=prsrole.color)
                                    try:
                                        await self.bot.send_message(user, embed=em)
                                    except:
                                        if prschannel:
                                            await self.bot.send_message(prschannel, "{}".format(user.mention))
                                            await self.bot.send_message(prschannel, embed=em)

                                    rand = random.choice(
                                        ["est désormais libre", "regagne sa liberté", "est sorti·e de prison",
                                         "profite à nouveau de l'air frais"])
                                    em = discord.Embed(description="{} {}".format(user.mention, rand),
                                                       color=prsrole.color)
                                    notif = await self.bot.say(embed=em)
                                    await asyncio.sleep(10)
                                    await self.bot.delete_message(notif)
                                else:
                                    return
                            else:
                                em = discord.Embed(description="**Sortie auto. de** <@{}> ─ "
                                                               "Le membre n'est plus sur le serveur.".format(user.id))
                                if user.id in session["MSG_PRISON"]:
                                    session["MSG_PRISON"].remove(user.id)
                                notif = await self.bot.say(embed=em)
                                await self.api.send_log(server, "prison", "Sortie de prison",
                                                        "Sortie automatique de **{}**, "
                                                        "ce membre n'est plus sur le serveur".format(user.mention))
                                await asyncio.sleep(5)
                                await self.bot.delete_message(notif)
                        else:
                            session["PRISON"][user.id]["ENTREE"] = session["PRISON"][user.id]["SORTIE"] = 0
                            await self.bot.remove_roles(user, prsrole)
                            if user.id in session["MSG_PRISON"]:
                                session["MSG_PRISON"].remove(user.id)
                            em = discord.Embed(description="{} a été libéré par {}".format(
                                user.mention, ctx.message.author.mention), color=prsrole.color)
                            notif = await self.bot.say(embed=em)
                            em = discord.Embed(description="**Peine de prison** ─ Vous êtes désormais libre",
                                               color=prsrole.color)
                            await self.api.send_log(server, "prison", "Libération de prison",
                                                    "**{}** a été libéré par **{}**".format(user.mention,
                                                                                                 ctx.message.author.mention))
                            try:
                                await self.bot.send_message(user, embed=em)
                            except:
                                if prschannel:
                                    await self.bot.send_message(prschannel, "{}".format(user.mention))
                                    await self.bot.send_message(prschannel, embed=em)
                            await asyncio.sleep(10)
                            await self.bot.delete_message(notif)

                elif type(obj) == discord.Role:
                    target = []
                    for member in server.members:
                        if obj.id in [r.id for r in member.roles]:
                            target.append(member)
                    if len(target) <= 20:
                        for i in target:
                            await self.tgl_prison(ctx, server, i, temps)
                    else:
                        await self.bot.say("**Sécurité** ─ Impossible de mettre plus de 20 membres en prison à la fois")
                else:
                    await self.bot.say("**Cible introuvable** ─ La cible doit être un membre ou un rôle.")
            else:
                await self.bot.say("**Formats** ─ `m` = minutes, `h` = heures, `j` = jours")

        else:
            await self.bot.say("**Rôle introuvable** ─ "
                               "Assignez un rôle à la prison avec `{}ks mp role`".format(ctx.prefix))

    @commands.command(aliases=["p", "jail"], pass_context=True, no_pm=True)
    @checks.admin_or_permissions(manage_roles=True)
    async def prison(self, ctx, cible, temps: str= "10m", karma: int = 2):
        """Emprisonner un membre/un ensemble de membres (via un rôle) pendant un certain temps (def. 10m)

        <cible> - Membre ou rôle à emprisonner (20 pers. max.)
        [temps] - Valeur suivie de l'unité (m, h, j)
        [karma] - Nombre de points de Karma à retirer, par défaut 2
        Ajoutez l'opérateur '+' pour ajouter du temps, et '-' pour en retirer"""
        await self.tgl_prison(ctx, ctx.message.server, cible, temps)
        obj = self.api.search_obj(ctx.message.server, cible)
        if type(obj) == discord.Member:
            self.api.get_karma(obj, -karma)
        elif type(obj) == discord.Role:
            target = []
            for member in ctx.message.server.members:
                if obj.id in [r.id for r in member.roles]:
                    target.append(member)
            for i in target:
                self.api.get_karma(i, -karma)
        else:
            pass

    @commands.command(name="prisonmsg", aliases=["pmsg"], pass_context=True)
    async def prison_msg(self, ctx, *message: str):
        """Permet d'envoyer un dernier message après votre mise en prison"""
        author = ctx.message.author
        server = ctx.message.server
        session = self.get_session(server)
        sys = self.api.get_server(server)
        if sys["OPTS"]["prison_msgsalon"]:
            salon = self.bot.get_channel(sys["OPTS"]["prison_msgsalon"])
            message = " ".join(message)
            if author.id in session["MSG_PRISON"]:
                if len(message) > 300:
                    await self.bot.say("**Trop long** | Ce message est limité à 300 caractères, pas un de plus.")
                    return
                em = discord.Embed(color=author.color, description="*{}*".format(message))
                em.set_author(name="Prison ─ Message de {}".format(str(author)), icon_url=author.avatar_url)
                em.set_footer(text="Cet unique message provient de la prison où {} est enfermé·e.".format(
                    author.name))
                await self.bot.send_typing(salon)
                await asyncio.sleep(1)
                if author.id in session["MSG_PRISON"]:
                    session["MSG_PRISON"].remove(author.id)
                await self.bot.send_message(salon, embed=em)
                self.api.save()
                await self.bot.say("**Votre message à été envoyé avec succès**")
                await self.api.send_log(server, "prison", "Message de la prison",
                                        "{} a utilisé son message de prison :\n\n*{}*".format(author.mention, message))

            else:
                await self.bot.say("**Refusé** ─ Vous n'y avez pas le droit.")

    @commands.command(aliases=["s"], pass_context=True)
    @checks.admin_or_permissions(manage_messages=True)
    async def slow(self, ctx, user: discord.Member = None, limite: int = 5):
        """Passe un membre en mode Slow, limitant ses messages au nombre indiqué (def. 5)

        Si aucun membre n'est précisé, limite le serveur en entier
        -Ne retire pas de Karma"""
        server = ctx.message.server
        session = self.get_session(server)
        if user:
            if user.id not in session["SLOW"]:
                session["SLOW"][user.id] = limite
                em = discord.Embed(description="**Slow** ─ {} est désormais limité à {} messages par minute.".format(
                    user.mention, limite), color=ctx.message.author.color)
                msg = await self.bot.say(embed=em)
                await self.bot.send_message(user, "**Slow** ─ Vous êtes désormais limité à {} messages par minute (par {})"
                                                  "".format(limite, ctx.message.author.mention))
                await self.api.send_log(server, "slow", "Slow d'un membre",
                                        "**{}** est désormais limité à {} par {}".format(user.mention,
                                                                                limite, ctx.message.author.mention))
                await asyncio.sleep(6)
                await self.bot.delete_message(msg)
            else:
                del session["SLOW"][user.id]
                em = discord.Embed(description="**Slow** ─ {} n'est plus limité.".format(
                    user.mention), color=ctx.message.author.color)
                msg = await self.bot.say(embed=em)
                await self.bot.send_message(user, "**Slow** ─ Vous avez été sorti du mode (par {})"
                                                  "".format(ctx.message.author.mention))
                await self.api.send_log(server, "slow", "Slow d'un membre",
                                        "**{}** n'est désormais plus limité (par {})".format(user.mention,
                                                                                         ctx.message.author.mention))
                await asyncio.sleep(6)
                await self.bot.delete_message(msg)
        else:
            if session["GLOBAL_SLOW"]:
                session["GLOBAL_SLOW"] = False
                em = discord.Embed(description="**Slow** ─ Limitation globale retirée")
                msg = await self.bot.say(embed=em)
                await self.api.send_log(server, "slow", "Slow du serveur", "Le serveur n'est plus limité")
                await asyncio.sleep(6)
                await self.bot.delete_message(msg)
            else:
                session["GLOBAL_SLOW"] = limite
                em = discord.Embed(description="**Slow** ─ Les membres sont désormais limités à {} "
                                               "messages par minute".format(limite))
                msg = await self.bot.say(embed=em)
                await self.api.send_log(server, "slow", "Slow du serveur", "Le serveur entier est désormais limité à"
                                                                           "{} messages par minutes".format(limite))

                await asyncio.sleep(6)
                await self.bot.delete_message(msg)

    @commands.command(aliases=["kc"], pass_context=True, no_pm=True)
    @checks.admin_or_permissions(manage_messages=True)
    async def casier(self, ctx, user: discord.Member = None):
        """Voir le casier du membre"""
        server = ctx.message.server
        today = time.strftime("%d/%m/%Y", time.localtime())
        case = self.api.get_casier(user)
        karma = "+" + case["KARMA"] if case["KARMA"] >= 0 else case["KARMA"]
        txt = "**Karma** ─ {}\n".format(karma)
        txt += "**Note** ─ {}".format(case["PUBLIC_NOTE"] if case["PUBLIC_NOTE"] else "Aucune note")
        em = discord.Embed(title="Casier de {}".format(user.name), description=txt)
        if case["LOGS"]:
            logs = ""
            for e in case["LOGS"][::-1]:
                if e[0] == today:
                    logs += "**{}** ─ **{}** *{}*\n".format(e[1], e[2], e[3])
                else:
                    logs += "**{}** ─ **{}** *{}*\n".format(e[0], e[2], e[3])
        else:
            logs = "Aucun historique de modération"
        em.add_field(name="Logs", value=logs)
        await self.bot.say(embed=em)

    @commands.command(pass_context=True, no_pm=True)
    @checks.admin_or_permissions(manage_messages=True)
    async def suivre(self, ctx, user: discord.Member):
        """Suivre un membre

        Cette fonction permet, entre autres:
        - De recevoir tous les messages qu'il poste (si les logs sont activés)
        - D'obtenir un résumé quotidien de ses faits et gestes [Bientôt]
        - D'auto-modérer certains abus comme les spams [Bientôt]"""
        case = self.api.get_casier(user)
        if case["SUIVI"]:
            case["SUIVI"] = False
            self.api.save()
            await self.bot.say("**Arrêt** ─ Le membre n'est plus suivi")
        else:
            case["SUIVI"] = True
            self.api.save()
            await self.bot.say("**Démarrage** ─ Le membre est désormais suivi")

    @commands.command(pass_context=True, no_pm=True)
    @checks.admin_or_permissions(manage_messages=True)
    async def note(self, ctx, user: discord.Member, *texte):
        """Change la note de modération d'un membre"""
        case = self.api.get_casier(user)
        if texte:
            texte = " ".join(texte)
            case["PUBLIC_NOTE"] = texte
            self.api.save()
            await self.bot.say("**Succès** ─ La note de modération du membre à été changée.")
        else:
            case["PUBLIC_NOTE"] = ""
            self.api.save()
            await self.bot.say("**Retirée** ─ Le membre n'a plus de note de modération.")

    @commands.group(name="karmaset", aliases=["modkarma", "ks"], pass_context=True, no_pm=True)
    @checks.admin_or_permissions(manage_roles=True)
    async def _karmaset(self, ctx):
        """Ensemble des paramètres Karma (fonctionnalitées avancées de modération)"""
        if ctx.invoked_subcommand is None:
            await send_cmd_help(ctx)

    @_karmaset.command(pass_context=True)
    async def setkarma(self, ctx, user: discord.Member, valeur: int):
        """Change la valeur de Karma d'un membre"""
        case = self.api.get_casier(user)
        if -5 <= valeur <= 5:
            case["KARMA"] = valeur
            self.api.save()
            await self.bot.say("**Succès** ─ Le Karma du membre à été modifié")
        else:
            await self.bot.say("**Erreur** ─ Le Karma doit être compris entre -5 et 5")

    @_karmaset.group(name="logs", pass_context=True)
    async def _logsset(self, ctx):
        """Paramètres des logs"""
        if ctx.invoked_subcommand is None:
            await send_cmd_help(ctx)

    @_logsset.command(pass_context=True)
    async def add(self, ctx, *logstype):
        """Ajoute des logs sur ce channel"""
        channel = ctx.message.channel
        sys = self.api.get_server(ctx.message.server)["OPTS"]
        if not logstype:
            liste = "**Messages**\n" \
                    "• `suivi` (messages des membres suivis)\n" \
                    "• `badkarma` (messages des membres ayant un karma négatif)\n" \
                    "• `delete` (tous les msg supprimés)\n" \
                    "• `reactclear` (nettoyage des réactions d'un msg)\n" \
                    "• `bots` (tous les msg de bots)\n" \
                    "• `mentions` (tous les msg contenant des mentions membre ou rôle)\n" \
                    "\n" \
                    "**Commandes & Triggers**\n" \
                    "• `kick` (kick d'un membre)\n" \
                    "• `ban` (ban d'un membre)\n" \
                    "• `softban` (softban d'un membre)\n" \
                    "• `mute` (membre muté)\n" \
                    "• `slow` (slow d'un membre ou d'un groupe)\n" \
                    "• `prison` (mise en prison d'un membre ou groupe)\n" \
                    "• `namechange` (changement de pseudo d'un membre)\n" \
                    "\n" \
                    "**Spéciaux**\n" \
                    "• `notif` (diverses notifications de modération)\n\n" \
                    "Vous pouvez ajouter des logs sur ce salon en faisant `{0}ks logs add` suivi de la liste des logs " \
                    "désirés (séparés par ';')\n" \
                    "__Exemple:__ `{0}ks logs add kick;ban;softban;delete;namechange` ajoutera les logs de Kick, Ban, " \
                    "Softban, des messages supprimés et des changements de pseudo".format(ctx.prefix)
            em = discord.Embed(title="Logs disponibles", description=liste)
            await self.bot.say(embed=em)
        else:
            logs = "".join(logstype).split(";")
            pb = []
            base = sys["logs_salons"][channel.id] if channel.id in sys["logs_salons"] else []
            for e in logs:
                if e.lower() not in ["suivi", "badkarma", "delete", "reactclear", "bots", "mentions", "kick",
                             "ban", "softban", "slow", "prison", "suivi", "unban", "namechange", "joindata", "quitdata",
                             "notif"]:
                    pb.append(e.lower())
                else:
                    base.append(e.lower())
            if not pb:
                sys["logs_salons"][channel.id] = base
                self.api.save()
                await self.bot.say("**Logs ajoutés** ─ Faîtes `{}ks logs list` pour voir la liste des logs liés à ce "
                                   "salon".format(ctx.prefix))
            else:
                await self.bot.say("**Erreur** ─ Les logs suivants ne sont pas reconnus :\n{}".format("\n".join(pb)))

    @_logsset.command(pass_context=True)
    async def remove(self, ctx, *logstype):
        """Retire des logs de ce channel

        Si aucun log n'est indiqué, affichera la liste des logs liés au salon"""
        channel = ctx.message.channel
        sys = self.api.get_server(ctx.message.server)["OPTS"]
        logs = sys["logs_salons"]
        if channel.id in logs:
            if not logstype:
                em = discord.Embed(title="Logs liés à ce salon", description="\n".join(logs[channel.id]) if logs[channel.id] else "Aucun")
                await self.bot.say(embed=em)
            else:
                logstype = "".join(logstype).split(";")
                for e in logstype:
                    logs[channel.id].remove(e.lower())
                sys["logs_salons"] = logs
                self.api.save()
                await self.bot.say("**Logs retirés** ─ Faîtes `{}ks logs list` pour voir la liste des logs liés à ce "
                                   "salon".format(ctx.prefix))
        else:
            await self.bot.say("**Aucun logs** ─ Ce salon ne possède aucune chaîne de logs")

    @_logsset.command(pass_context=True)
    async def list(self, ctx):
        """Affiche les logs liés à ce salon"""
        channel = ctx.message.channel
        sys = self.api.get_server(ctx.message.server)["OPTS"]
        logs = sys["logs_salons"]
        if channel.id in logs:
            em = discord.Embed(title="Logs liés à ce salon",
                               description="\n".join(logs[channel.id]) if logs[channel.id] else "Aucun")
            await self.bot.say(embed=em)
        else:
            await self.bot.say("**Aucun logs** ─ Ce salon ne possède aucune chaîne de logs")

    @_karmaset.group(name="prison", aliases=["mp"], pass_context=True)
    async def _prisonset(self, ctx):
        """Paramètres de la prison"""
        if ctx.invoked_subcommand is None:
            await send_cmd_help(ctx)

    @_prisonset.command(pass_context=True)
    async def role(self, ctx, role: discord.Role):
        """Change le rôle dédié aux prisonniers"""
        server = ctx.message.server
        serv = self.api.get_server(server)["OPTS"]
        if role.name in [r.name for r in server.roles]:
            serv["prison_role"] = role.id
            self.api.save()
            await self.bot.say("**Succès** — Le rôle de prisonnier est désormais *{}*."
                               "\nVérifiez que les permissions liées au rôle soient correctes.".format(role.name))
        else:
            await self.bot.say("**Echec** — Le rôle n'existe pas sur ce serveur.")

    @_prisonset.command(pass_context=True)
    async def salon(self, ctx, salon: discord.Channel):
        """Change le salon dédié à la Prison"""
        server = ctx.message.server
        serv = self.api.get_server(server)["OPTS"]
        serv["prison_salon"] = salon.id
        self.api.save()
        await self.bot.say("**Succès** — Le salon dédié à la prison est désormais {}".format(salon.mention))

    @_prisonset.command(pass_context=True)
    async def msgsalon(self, ctx, salon: discord.Channel = None):
        """Change le salon où les messages des prisonniers doivent être envoyés

        Si aucun salon n'est fourni, les prisonniers n'auront pas accès à cette fonction"""
        server = ctx.message.server
        serv = self.api.get_server(server)["OPTS"]
        if salon:
            serv["prison_msgsalon"] = salon.id
            await self.bot.say("**Activé** — Les prisonniers pourront envoyer un message sur {}".format(salon.mention))
        else:
            serv["prison_msgsalon"] = None
            await self.bot.say("**Désactivé** — Les prisonniers ne pourront pas envoyer de messages d'appel")
        self.api.save()

    @_prisonset.command(pass_context=True)
    async def reset(self, ctx):
        """Reset la prison et libère les prisonniers

        En cas de blocage seulement"""
        server = ctx.message.server
        prsrole = self.get_prison_role(server)
        if prsrole:
            self.msg_prison = {server.id: []}
            self.prison = {server.id: {}}
            for member in server.members:
                if prsrole.name in [r.name for r in member.roles]:
                    await self.bot.remove_roles(member, prsrole)
            await self.bot.say("**Succès** — La prison à été reset et les membres ont été libérés.")
        else:
            await self.bot.say("**Echec** — Aucun rôle n'est dédié à la prison, "
                               "il m'est donc impossible d'en libérer les membres.")

    async def on_message(self, message):
        server = message.server
        author = message.author
        mentions, rolesmention = message.mentions, message.role_mentions
        casier = self.api.get_casier(author)
        if casier["SUIVI"]:
            await self.api.send_log(server, "suivi", "Membre suivi — {}".format(author.name), message.content)
        if casier["KARMA"] < 0:
            await self.api.send_log(server, "badkarma", "Membre ayant un Karma négatif — {}".format(author.name),
                                message.content)
        if author.bot:
            await self.api.send_log(server, "bots", "Bot ayant posté un message — {}".format(author.name), message.content)
        if mentions or rolesmention:
            await self.api.send_log(server, "mentions", "Mentions détectées — {}".format(author.name), message.content)

    async def on_message_delete(self, message):
        server = message.server
        author = message.author
        await self.api.send_log(server, "delete", "Message supprimé de {}".format(author.name), message.content)

    async def on_reaction_clear(self, message, reactions):
        server = message.server
        author = message.author
        await self.api.send_log(server, "reactclear", "Réactions du message de {} retirés".format(author.name),
                            message.content)

    async def on_member_update(self, before, after):
        server = after.server
        if after.name != before.name:
            await self.api.send_log(server, "namechange", "Changement de pseudo", "**{}** est désormais nommé "
                                                                                  "__**{}**__".format(
                before.name, after.name))
        if after.display_name != before.display_name:
            if after.display_name != after.name:
                await self.api.send_log(server, "namechange", "Changement de surnom",
                                        "**{}** est désormais connu en tant "
                                        "que __**{}**__".format(
                                            before.display_name, after.display_name))
            else:
                await self.api.send_log(server, "namechange", "Changement de surnom",
                                        "**{}** n'a désormais plus de surnom".format(
                                            before.name))

def check_folders():
    folders = ("data", "data/karma/")
    for folder in folders:
        if not os.path.exists(folder):
            print("Création du fichier " + folder)
            os.makedirs(folder)


def check_files():
    if not os.path.isfile("data/karma/data.json"):
        fileIO("data/karma/data.json", "save", {})


def setup(bot):
    check_folders()
    check_files()
    n = Karma(bot)
    bot.add_listener(n.on_message, "on_message")
    bot.add_listener(n.on_message_delete, "on_message_delete")
    bot.add_listener(n.on_reaction_clear, "on_reaction_clear")
    bot.add_listener(n.on_member_update, "on_member_update")
    bot.add_cog(n)