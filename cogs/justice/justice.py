import asyncio
import os
import random
import time

import discord
from cogs.utils.dataIO import fileIO, dataIO
from discord.ext import commands

from .utils import checks


class Justice:
    """Module ajoutant des fonctionnalités avancées de modération"""
    def __init__(self, bot):
        self.bot = bot
        self.sys = dataIO.load_json("data/just/sys.json")
        self.reg = dataIO.load_json("data/just/reg.json")

    def save(self):
        fileIO("data/just/sys.json", "save", self.sys)
        fileIO("data/just/reg.json", "save", self.reg)
        return True

    """@commands.command(aliases=["p", "jail"], pass_context=True)
    @checks.admin_or_permissions(manage_messages=True)
    async def prison(self, ctx, user: discord.Member, temps: str = "5m"):
        Emprisonner un membre sur un salon dédié (Défaut: 5m)

        <user> = Utilisateur à mettre en prison
        <temps> = Temps pendant lequel l'utilisateur est en prison (Minimum 60s)
        Format de temps:
        's' pour seconde(s)
        'm' pour minute(s)
        'h' pour heure(s)
        'j' pour jour(s)
        Exemple : &p @membre 5h

        Note: Il est possible d'ajouter ou retirer du temps avec '+' et '-' avant le chiffre
        Exemple : &p @membre +10m
        reg = r"<@(.\d+)>\s?([+-])?([0-9])?([smhj])?"
        server = ctx.message.server
        if temps.isdigit():
            await self.bot.whisper("**N'oubliez pas le format !**\n"
                                   "Formats disponibles : m (minutes), h (heures), j (jours)\n"
                                   "Exemple: &p @membre 5h")
            return
        role = self.sys["ROLE_PRISON"]
        apply = discord.utils.get(ctx.message.server.roles, name=role)
        form = temps[-1:]
        if form not in ["s", "m", "h", "j"]:
            await self.bot.say("Ce format n'existe pas (s, m, h ou j)")
            return
        save = user.name
        if temps.startswith("+") or temps.startswith("-"):  # Ajouter ou retirer du temps de prison
            val = temps.replace(form, "")
            val = int(val.replace(temps[0], ""))
            if user.id in self.reg:
                if role in [r.name for r in user.roles]:
                    modif = self.convert_sec(form, val)
                    if temps[0] == "+":
                        self.reg[user.id]["FIN_PEINE"] += modif
                        self.new_event("add", user.id, ctx.message.author.id, modif)
                        estim = time.strftime("%H:%M", time.localtime(self.reg[user.id]["FIN_PEINE"]))
                        await self.bot.say(
                            "**Ajout de *{}{}* pour *{}* réalisé avec succès.**".format(val, form, user.name))
                        await self.bot.send_message(user,
                                                    "*{}{}* ont été ajoutés à ta peine par *{}*\nSortie désormais prévue à: `{}`".format(
                                                        val, form, ctx.message.author.name, estim))
                    elif temps[0] == "-":
                        self.reg[user.id]["FIN_PEINE"] -= modif
                        self.new_event("sub", user.id, ctx.message.author.id, modif)
                        estim = time.strftime("%H:%M", time.localtime(self.reg[user.id]["FIN_PEINE"]))
                        await self.bot.say(
                            "**Retrait de *{}{}* pour *{}* réalisé avec succès.**".format(val, form, user.name))
                        await self.bot.send_message(user,
                                                    "*{}{}* ont été retirés de ta peine par *{}*\nSortie désormais prévue à: `{}`".format(
                                                        val, form, ctx.message.author.name, estim))
                    else:
                        await self.bot.say("Symbole non reconnu. Ajoutez du temps avec '+' et retirez-en avec '-'.")
                        return
                else:
                    await self.bot.say(
                        "L'utilisateur n'est pas en prison. Vous ne pouvez donc pas lui ajouter ni retirer du temps de peine.")
                    return
            else:
                await self.bot.say(
                    "L'utilisateur n'a jamais été en prison. Vous ne pouvez donc pas lui ajouter ni retirer du temps de peine.")
                return
        else:
            val = int(temps.replace(form, ""))
            sec = self.convert_sec(form, val)
            if sec >= 60:  # Au moins une minute
                if sec > 86400:
                    await self.bot.whisper(
                        "Il est déconseillé d'utiliser la prison pour une peine dépassant 24h (1j) à cause des instabilités de Discord pouvant causer une peine infinie.")
                if user.id not in self.reg:
                    self.reg[user.id] = {"FIN_PEINE": None,
                                         "DEB_PEINE": None,
                                         "BANG": 0,
                                         "ROLES": [r.name for r in user.roles],
                                         "D_PSEUDO": user.display_name,
                                         "TRACKER": []}
                    self.save()
                if role not in [r.name for r in user.roles]:
                    b_peine = time.time()
                    estim = time.strftime("%H:%M", time.localtime(b_peine + sec))
                    self.reg[user.id]["DEB_PEINE"] = b_peine
                    self.reg[user.id]["FIN_PEINE"] = b_peine + sec
                    self.new_event("in", user.id, ctx.message.author.id, temps)
                    await self.bot.add_roles(user, apply)
                    await self.bot.say("{} **a été mis(e) en prison pendant *{}* par *{}***".format(user.mention, temps,
                                                                                                    ctx.message.author.name))
                    await self.bot.send_message(user,
                                                "**Tu as été mis(e) en prison pendant {}**\nSortie prévue à: `{}`\n"
                                                "Un salon textuel écrit est disponible sur le serveur afin de contester cette punition ou afin d'obtenir plus d'informations.".format(
                                                    temps, estim))
                    self.save()
                    while time.time() < self.reg[user.id]["FIN_PEINE"]:
                        await asyncio.sleep(0.5)
                    if user in server.members:
                        if role in [r.name for r in user.roles]:
                            self.reg[user.id]["DEB_PEINE"] = self.reg[user.id]["FIN_PEINE"] = 0
                            self.new_event("out", user.id, "auto")
                            await self.bot.remove_roles(user, apply)
                            await self.bot.say("{} **est libre**".format(user.mention))
                            self.save()
                        else:
                            return
                    else:
                        await self.bot.say(
                            "{} ne peut être sorti de prison car il n'est plus sur le serveur.".format(save))
                else:
                    self.reg[user.id]["DEB_PEINE"] = self.reg[user.id]["FIN_PEINE"] = 0
                    self.new_event("out", user.id, ctx.message.author.id)
                    await self.bot.remove_roles(user, apply)
                    await self.bot.say("{} **a été libéré par *{}***".format(user.mention, ctx.message.author.name))
                    self.save()
            else:
                await self.bot.say("Le temps minimum est de 1m")"""

    def convert_sec(self, form: str, val: int):
        if form == "j":
            return val * 86400
        elif form == "h":
            return val * 3600
        elif form == "m":
            return val * 60
        else:
            return val  # On considère alors que c'est déjà en secondes

    @commands.command(pass_context=True, hidden=True)
    @checks.admin_or_permissions(manage_roles=True)
    async def resetprison(self, ctx):
        """Reset totalement la prison et libère tous les membres"""
        server = ctx.message.server
        if server.id in self.reg:
            for u in self.reg[server.id]:
                self.reg[server.id][u]["TS_SORTIE"] = self.reg[server.id][u]["TS_ENTREE"] = 0
            self.save()
            await self.bot.say("**Reset** | Effectué avec succès, tous les membres ont été libérés.")
        else:
            await self.bot.say("**Inutile** | Le reset sur ce serveur est inutile.")

    @commands.command(aliases=["bp", "betajail"], pass_context=True)
    @checks.admin_or_permissions(manage_roles=True)
    async def betaprison(self, ctx, user: discord.Member, temps: str = "10m"):
        """Emprisonner un membre pendant un certain temps (Défaut = 10m)

        <user> = Membre à emprisonner
        <temps> = Valeur suivie de l'unité (m, h ou j)
        -- Il est possible d'ajouter devant la valeur de temps '+' et '-' pour moduler une peine"""
        message = ctx.message
        server = message.server
        form = temps[-1:]  # C'est le format du temps (smhj)
        if temps.isdigit() or form not in ["s", "m", "h", "j"]:
            await self.bot.whisper("**Unités** | `m` = Minutes, `h` = Heures, `j` = Jours\n"
                                   "Exemple: `{}p @membre 5h`".format(ctx.prefix))
            return
        if server.id not in self.reg:
            self.reg[server.id] = {}
        role = "Prison"  # FOR TEST PURPOSEEEEES (Bien sûr)
        try:
            apply = discord.utils.get(message.server.roles, name=role)  # Objet: Rôle
        except:
            await self.bot.say("**Erreur** | Le rôle *Prison* n'est pas présent sur ce serveur.")
            return

        if temps.startswith("+") or temps.startswith("-"):  # Ajouter ou retirer du temps de prison
            val = temps.replace(form, "")
            val = int(val.replace(temps[0], ""))
            if user in self.reg[server.id]:
                if role in [r.name for r in user.roles]:
                    modif = self.convert_sec(form, val)
                    if temps[0] == "+":
                        self.reg[server.id][user.id]["TS_SORTIE"] += modif
                        estim = time.strftime("%H:%M", time.localtime(self.reg[server.id][user.id]["TS_SORTIE"]))
                        msg = "{} ─ Ajout de **{}{}** de peine".format(user.mention, val, form)
                        estim_txt = "Sortie estimée à {}".format(estim)

                        em = discord.Embed(description=msg, color=apply.color)
                        em.set_footer(text=estim_txt)
                        notif = await self.bot.say(embed=em)
                        await asyncio.sleep(7)
                        await self.bot.delete_message(notif)

                        em = discord.Embed(description="**Peine augmentée** ─ **+{}{}** par *{}*".format(
                            val, form, ctx.message.author.name), color=apply.color)
                        em.set_footer(text="Sortie prévue à {}".format(estim))
                        await self.bot.send_message(user, embed=em)
                    elif temps[0] == "-":
                        self.reg[server.id][user.id]["TS_SORTIE"] -= modif
                        if self.reg[server.id][user.id]["TS_SORTIE"] < time.time():
                            estim = time.strftime("%H:%M", time.localtime())
                        else:
                            estim = time.strftime("%H:%M", time.localtime(self.reg[server.id][user.id]["TS_SORTIE"]))
                        msg = "{} ─ Réduction de **{}{}** de peine".format(user.mention, val, form)
                        estim_txt = "Sortie estimée à {}".format(estim)

                        em = discord.Embed(description=msg, color=apply.color)
                        em.set_footer(text=estim_txt)
                        notif = await self.bot.say(embed=em)
                        await asyncio.sleep(7)
                        await self.bot.delete_message(notif)

                        em = discord.Embed(description="**Peine réduite** ─ **-{}{}** par *{}*".format(
                            val, form, ctx.message.author.name), color=apply.color)
                        em.set_footer(text="Sortie prévue à {}".format(estim))
                        await self.bot.send_message(user, embed=em)
                    else:
                        await self.bot.say("**Symbole non reconnu** | `+` = Ajouter / `-` = Réduire")
                        return
                else:
                    await self.bot.say("**Erreur** | Le membre n'est pas en prison (Absence de rôle)")
                    return
        else:
            val = int(temps.replace(form, ""))
            sec = self.convert_sec(form, val)
            n = 0
            if sec < 60:
                sec = 60 # Au moins une minute
            if sec > 86400:
                notif = await self.bot.say("**Attention** | "
                                           "Une telle durée peut causer une peine infinie à la moindre instabilité")
                await asyncio.sleep(5)
                await self.bot.delete_message(notif)
            if user.id not in self.reg[server.id]:
                self.reg[server.id][user.id] = {"TS_ENTREE": 0,
                                                "TS_SORTIE": 0,
                                                "CASIER": []}
            if role not in [r.name for r in user.roles]:
                b_peine = time.time()
                self.reg[server.id][user.id]["TS_ENTREE"] = b_peine
                self.reg[server.id][user.id]["TS_SORTIE"] = b_peine + sec
                estim = time.strftime("%H:%M", time.localtime(self.reg[server.id][user.id]["TS_SORTIE"]))
                await self.bot.add_roles(user, apply)
                msg = "{} ─ Mise en prison pour **{}{}**".format(user.mention, val, form)
                estim_txt = "Sortie estimée à {}".format(estim)
                em = discord.Embed(description="**Peine de prison** ─ **{}{}** par *{}*\n"
                                               "Vous avez accès au salon *Prison* pour toute réclamation"
                                               "".format(val, form, ctx.message.author.name), color=apply.color)
                em.set_footer(text="Sortie prévue à {}".format(estim))
                await self.bot.send_message(user, embed=em)

                em = discord.Embed(description=msg, color=apply.color)
                em.set_footer(text=estim_txt)
                notif = await self.bot.say(embed=em)
                await asyncio.sleep(7)
                await self.bot.delete_message(notif)

                self.save()
                while time.time() < self.reg[server.id][user.id]["TS_SORTIE"]:
                    await asyncio.sleep(1)  # TIMER ============#

                if user in server.members:
                    if role in [r.name for r in user.roles]:
                        self.reg[server.id][user.id]["TS_ENTREE"] = self.reg[server.id][user.id]["TS_SORTIE"] = 0
                        self.save()
                        await self.bot.remove_roles(user, apply)
                        rand = random.choice(["est désormais libre", "regagne sa liberté", "est sorti de prison",
                                              "profite à nouveau de l'air frais"])
                        em = discord.Embed(description="{} {}".format(user.mention, rand), color=apply.color)
                        notif = await self.bot.say(embed=em)
                        await asyncio.sleep(7)
                        await self.bot.delete_message(notif)
                    else:
                        return
                else:
                    em = discord.Embed(description="**Sortie de** <@{}> | Il n'est plus sur le serveur.")
                    notif = await self.bot.say(embed=em)
                    await asyncio.sleep(5)
                    await self.bot.delete_message(notif)
            else:
                self.reg[user.id]["TS_ENTREE"] = self.reg[user.id]["TS_SORTIE"] = 0
                await self.bot.remove_roles(user, apply)
                self.save()
                em = discord.Embed(description="{} a été libéré par {}".format(
                    user.mention, ctx.message.author.mention), color=apply.color)
                notif = await self.bot.say(embed=em)
                em = discord.Embed(description="**Peine de prison** ─ Vous êtes désormais libre", color=apply.color)
                await self.bot.send_message(user, embed=em)

                await asyncio.sleep(7)
                await self.bot.delete_message(notif)


def check_folders():
    folders = ("data", "data/justice/")
    for folder in folders:
        if not os.path.exists(folder):
            print("Création du fichier " + folder)
            os.makedirs(folder)


def check_files():
    default = {"ROLE_PRISON": "Prison", "SALON_PRISON": None}
    if not os.path.isfile("data/justice/reg.json"):
        fileIO("data/justice/reg.json", "save", {})
    if not os.path.isfile("data/justice/sys.json"):
        fileIO("data/justice/sys.json", "save", default)


def setup(bot):
    check_folders()
    check_files()
    n = Justice(bot)
    bot.add_cog(n)