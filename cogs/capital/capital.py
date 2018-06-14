import asyncio
import datetime
import operator
import os
import random
import string
import time
from collections import namedtuple

import discord
from __main__ import send_cmd_help
from discord.ext import commands

from .utils import checks
from .utils.dataIO import fileIO, dataIO


class CapitalAPI:
    """API Capital | Système de monnaie globale par serveur"""
    def __init__(self, bot, path):
        self.bot = bot
        self.data = dataIO.load_json(path)
        self.backup_eco = dataIO.load_json("data/finance/eco.json")
        self.backup_sys = dataIO.load_json("data/finance/sys.json")
        self.sys_defaut = {"MONNAIE": {"SINGULIER": "crédit", "PLURIEL": "crédits", "SYMBOLE": "cds"},
                           "ONLINE": True,
                           "GIFTCODES": {}}
        self.default = {"USERS": {}, "SYSTEM": self.sys_defaut}
        self.cooldown = {}

# Snips système (protégés)

    def _save(self):
        fileIO("data/capital/data.json", "save", self.data)
        return True

    def _get_server_raw_data(self, server: discord.Server):
        if server.id not in self.data:
            self.data[server.id] = self.default
            self._save()
        return self.data[server.id]

    def backup_finance(self, server: discord.Server):
        if server.id in self.backup_eco:
            users_backup = self.backup_eco[server.id]
        else:
            users_backup = {}
        if server.id in self.backup_sys:
            sys_backup = self.sys_defaut
            sys_backup["MONNAIE"] = {"SINGULIER": self.backup_sys[server.id]["MONEY_NAME"],
                                     "PLURIEL": self.backup_sys[server.id]["MONEY_NAME_PLURIEL"],
                                     "SYMBOLE": self.backup_sys[server.id]["MONEY_SYMBOLE"]}
            sys_backup["ONLINE"] = self.backup_sys[server.id]["MODDED"]
            sys_backup["GIFTCODES"] = {}
        else:
            sys_backup = self.sys_defaut
        backup = {"USERS": users_backup, "SYSTEM": sys_backup}
        self.data[server.id] = backup
        self._save()
        return True

# Snips USER

    def new_account(self, user: discord.Member):
        server = user.server
        data = self._get_server_raw_data(server)["USERS"]
        if user.id not in data:
            data[user.id] = {"SOLDE": 100,
                             "TRSAC": [],
                             "EXTRA": {},
                             "CREE": datetime.datetime.now().strftime("%d/%m/%Y à %H:%M")}
            self._save()
            return True
        return False

    def _account_obj(self, user: discord.Member):  # On change de Compte à Account pour dégager le franglish
        server = user.server
        data = self._get_server_raw_data(server)["USERS"][user.id]
        Account = namedtuple('Account', ['id', 'extra', 'solde', 'historique', 'transactions', 'timestamp'])
        return Account(user.id, data["EXTRA"], data["SOLDE"], data["TRSAC"], data["TRSAC"], data["CREE"])

    def get_account(self, user: discord.Member, w: bool = False, m: bool = False):
        server = user.server
        data = self._get_server_raw_data(server)["USERS"]
        if user.id not in data:
            if m:  # make
                self.new_account(user)
            else:
                return False
        if not w:  # write
            return self._account_obj(user)
        else:
            return data[user.id]

    def get_all_accounts(self, server: discord.Server = None):
        liste = []
        if not server:
            for serv in self.data:
                server = self.bot.get_server(serv)
                for member in server.members:
                    if self.get_account(member):
                        liste.append(self.get_account(member))
        else:
            for member in server.members:
                if self.get_account(member):
                    liste.append(self.get_account(member))
        return liste

# Snips TRANSACTION

    def _obj_transaction(self, trans: list):
        servid = userid = None
        for s in self.data:
            for u in self.data[s]["USERS"]:
                if trans in self.data[s]["USERS"][u]["TRSAC"]:
                    servid = s
                    userid = u
        Transaction = namedtuple('Transaction', ['id', 'ts_heure', 'ts_jour', 'somme', 'desc', 'user_id', 'server_id',
                                                 'liens', 'type'])
        return Transaction(trans[0], trans[1], trans[2], trans[3], trans[4], userid, servid, trans[5], trans[6])
        # --Info             id       heure     jour      somme     desc      ----    ----    link       type

    def apd_transaction(self, user: discord.Member, type: str, somme: int, desc: str):
        origin = user
        user = self.get_account(user, True)
        if not user:
            return False
        jour = time.strftime("%d/%m/%Y", time.localtime())
        heure = time.strftime("%H:%M", time.localtime())
        clef = str(''.join(random.SystemRandom().choice(string.ascii_letters + string.digits) for _ in range(5)))
        if self.id_to_transaction_obj(clef):
            return self.apd_transaction(origin, type, somme, desc)  # On recommence à générer une nouvelle clef
        event = [clef, heure, jour, somme, desc, [], type]
        user["TRSAC"].append(event)
        if len(user["TRSAC"]) > 30:
            user["TRSAC"].remove(user["TRSAC"][0])
        return self._obj_transaction(event)

    def link_transactions(self, trans_a, trans_b):
        a = self.id_to_transaction_obj(trans_a, True)
        b = self.id_to_transaction_obj(trans_b, True)
        if a and b:
            a[5].append(b[0])
            b[5].append(a[0])
            self._save()
            return True
        return False

    def id_to_transaction_obj(self, transaction_id: str, w: bool=False):
        for serv in self.data:
            for user in self.data[serv]["USERS"]:
                for tr in self.data[serv]["USERS"][user]["TRSAC"]:
                    if tr[0] == transaction_id:
                        return self._obj_transaction(tr) if not w else tr
        return False

    def get_lasts_transactions(self, user: discord.Member, nombre: int = 1):
        user = self.get_account(user, True)
        if user:
            h = user["TRSAC"][-nombre:]
            liste = []
            for i in h:
                liste.append(self._obj_transaction(i))
            return liste
        else:
            return []

    def get_day_transactions(self, user: discord.Member, jour: str = None):
        if jour is None:
            jour = time.strftime("%d/%m/%Y", time.localtime())
        user = self.get_account(user, True)
        liste = []
        if user:
            for t in user["TRSAC"]:
                if t[2] == jour:
                    j, h = t[2], t[1]
                    liste.append([time.mktime(time.strptime("{} {}".format(j, h), "%d/%m/%Y %H:%M")),
                                  self._obj_transaction(t)])
            sort = sorted(liste, key=operator.itemgetter(0), reverse=True)
            liste = [s[0] for s in sort]
            return liste
        return False

    def get_total_day_gain(self, user: discord.Member, jour: str = None):
        liste = self.get_day_transactions(user, jour)
        if liste:
            total = sum([t.somme for t in liste])
            return total
        return 0

# Snips CREDITS & SOLDE

    def total_server_credits(self, server: discord.Server):
        if server.id not in self.data:
            return False
        return sum([u.solde for u in self.get_all_accounts(server)])

    def enough_credits(self, user: discord.Member, need: int):
        data = self.get_account(user)
        if data:
            if data.solde - need >= 0:
                return True
        return False

    def depot_credits(self, user: discord.Member, nombre: int, raison: str):
        data = self.get_account(user, True)
        if nombre <= 0:
            return False
        data["SOLDE"] += nombre
        t = self.apd_transaction(user, "DEPOT", nombre, raison)
        self._save()
        return t

    def perte_credits(self, user: discord.Member, nombre: int, raison: str):
        data = self.get_account(user, True)
        if nombre < 0:
            nombre = -nombre
        if (data["SOLDE"] - nombre) >= 0:
            data["SOLDE"] -= nombre
            t = self.apd_transaction(user, "PERTE", -nombre, raison)
            self._save()
            return t
        return False

    def set_credits(self, user: discord.Member, nombre: int, raison: str):
        data = self.get_account(user, True)
        if nombre >= 0:
            data["SOLDE"] = nombre
            t = self.apd_transaction(user, "SET", nombre, raison)
            self._save()
            return t
        return False

    def transfert_credits(self, crean: discord.Member, debit: discord.Member, nombre: int, raison: str):
        if crean is debit:
            return False
        debitdata = self.get_account(debit, True)
        if nombre > 0:
            if (debitdata["SOLDE"] - nombre) >= 0:
                ta = self.perte_credits(debit, nombre, raison)
                tb = self.depot_credits(crean, nombre, raison)
                self.link_transactions(ta.id, tb.id)
                return True
            return False
        return False

# Snips GIFT

    def new_gift(self, code: str, server: discord.Server, gift):
        code = code.upper()
        for s in self.data:
            if code not in self.data[s]["SYSTEM"]["GIFTCODES"]:
                pass
            else:
                return False
        self.data[server.id]["SYSTEM"]["GIFTCODES"][code] = gift
        self._save()

    def gift_exist(self, code: str, server: discord.Server = False):
        code = code.upper()
        def _obj_gift(code: str, server: discord.Server):
            Gift = namedtuple('Gift', ['server', 'code', 'contenu', 'desc'])
            contenu = self.data[server.id]["SYSTEM"]["GIFTCODES"][code]
            if type(contenu) is int:
                desc = "{} {}".format(contenu, self.get_money(server, contenu))
            elif type(contenu) is str:
                desc = contenu.capitalize()
            else:
                desc = "???"
            return Gift(server.id, code, contenu, desc)

        if server:
            gifts = self.get_server_sys(server).giftcodes
            if code in gifts:
                return _obj_gift(code, server)
            return False
        else:
            for s in self.data:
                if code in [g for g in self.data[s]["SYSTEM"]["GIFTCODES"]]:
                    return _obj_gift(code, self.bot.get_server(s))
                else:
                    return False

    def depot_gift(self, user: discord.User, code: str):
        code = code.upper()
        for s in self.data:
            if code in self.data[s]["SYSTEM"]["GIFTCODES"]:
                user = self.bot.get_server(s).get_member(user.id)
                return self._gift_process(user, self.data[s]["SYSTEM"]["GIFTCODES"][code], code)
        return False

    def _gift_process(self, user: discord.Member, gift, code: str):
        code = code.upper()
        if type(gift) == int:
            self.depot_credits(user, gift, "Code /{}/".format(code))
            del self.data[user.server.id]["SYSTEM"]["GIFTCODES"][code]
            self._save()
            return True
        elif type(gift) == str:
            return False  # TODO : Possiblement des cadeaux
        elif type(gift) == list:
            for l in gift:
                self._gift_process(user, l, code)
        return False

# Snips SERVEUR

    def _system_obj(self, server: discord.Server):
        data = self._get_server_raw_data(server)["SYSTEM"]
        Monnaie = namedtuple('Monnaie', ['singulier', 'pluriel', 'symbole'])
        money = Monnaie(data["MONNAIE"]["SINGULIER"], data["MONNAIE"]["PLURIEL"], data["MONNAIE"]["SYMBOLE"])

        System = namedtuple('System', ['id', 'monnaie', 'online', 'giftcodes'])
        return System(server.id, money, data["ONLINE"], data["GIFTCODES"])

    def gen_palmares(self, server: discord.Server, nombre: int):
        if server.id in self.data:
            liste = [[self.data[server.id]["USERS"][u]["SOLDE"], u] for u in self.data[server.id]["USERS"]]
            sort = sorted(liste, key=operator.itemgetter(0), reverse=True)
            return sort[:nombre]
        else:
            return False

    def get_money(self, server: discord.Server, nombre: int = 0, symbole: bool = False):
        data = self._get_server_raw_data(server)["SYSTEM"]
        if symbole:
            return data["MONNAIE"]["SYMBOLE"]
        if nombre > 1:
            return data["MONNAIE"]["PLURIEL"]
        return data["MONNAIE"]["SINGULIER"]

    def server_update(self, server: discord.Server):
        data = self._get_server_raw_data(server)["SYSTEM"]
        for cat in self.sys_defaut:
            if cat not in data:
                data[cat] = self.sys_defaut[cat]
        self._save()
        return True

    def get_server_sys(self, server: discord.Server = False, w: bool = False):
        if server:
            return self._system_obj(server) if not w else self.data[server.id]["SYSTEM"]
        else:
            tot = []
            for s in self.data:
                server = self.bot.get_server(s)
                tot.append(self._system_obj(server) if not w else self.data[server.id]["SYSTEM"])
            return tot

# Snips COOLDOWN

    def add_cooldown(self, user: discord.Member, nom: str, duree: int):
        server = user.server
        date = time.time() + duree
        if server.id not in self.cooldown:
            self.cooldown[server.id] = {}
        if nom.lower() not in self.cooldown[server.id]:
            self.cooldown[server.id][nom.lower()] = {}
        if user.id not in self.cooldown[server.id][nom.lower()]:
            self.cooldown[server.id][nom.lower()][user.id] = date
        else:
            self.cooldown[server.id][nom.lower()][user.id] += duree
        return self.cooldown[server.id][nom.lower()][user.id]

    def is_cooldown_blocked(self, user: discord.Member, nom: str):  # Bloqué par le cooldown ?
        server = user.server
        now = time.time()
        if server.id not in self.cooldown:
            self.cooldown[server.id] = {}
            return False
        if nom.lower() not in self.cooldown[server.id]:
            return False
        if user.id in self.cooldown[server.id][nom.lower()]:
            if now <= self.cooldown[server.id][nom.lower()][user.id]:
                duree = int(self.cooldown[server.id][nom.lower()][user.id] - now)
                return duree
            else:
                del self.cooldown[server.id][nom.lower()][user.id]
                return False
        return False

# Snips DATAS

    def save_capital_api(self):
        return self._save()

    def reset_server_data(self, server: discord.Server, all: bool = False):
        if all:
            self.data = {}
        if server.id in self.data:
            self.data[server.id] = self.default
        else:
            return False
        self._save()
        return True

    def reset_user_data(self, user: discord.Member):
        server = user.server
        if server.id in self.data:
            if user.id in self.data[server.id]["USERS"]:
                del self.data[server.id]["USERS"][user.id]
                self._save()
                return True
        return False

# Async fonctions

    async def inscription(self, ctx):
        msg = await self.bot.say("**Vous n'avez pas de compte bancaire** | Voulez-vous en ouvrir un ?")
        await self.bot.add_reaction(msg, "✔")
        await self.bot.add_reaction(msg, "✖")
        await asyncio.sleep(0.25)

        def check(reaction, user):
            return not user.bot
        rep = await self.bot.wait_for_reaction(["✔", "✖"], message=msg, timeout=20,
                                               check=check, user=ctx.message.author)
        if rep is None or rep.reaction.emoji == "✖":
            await self.bot.say("**Annulé** ─ Vous pourrez toujours en ouvrir un plus tard avec `{}b new` ".format(
                ctx.prefix))
            await self.bot.delete_message(msg)
            return False
        elif rep.reaction.emoji == "✔":
            done = self.new_account(ctx.message.author)
            if done:
                await self.bot.say("**Créé** ─ Ton compte a été ouvert avec succès {} !".format(
                    ctx.message.author.name))
                await self.bot.delete_message(msg)
                return True
            else:
                await self.bot.say("**Erreur** | Le compte n'a pas pu être créé, "
                                   "le serveur est probablement sur *blacklist*")
                await self.bot.delete_message(msg)
                return False
        else:
            await self.bot.say("**Erreur** | Désolé je n'ai pas compris...")
            return False

class Capital:
    """Système monétaire unique et jeux divers"""
    def __init__(self, bot):
        self.bot = bot
        self.api = CapitalAPI(bot, "data/capital/data.json")

    def check(self, reaction, user):
        return not user.bot

    @commands.group(name="banque", aliases=["b", "bank"], pass_context=True, invoke_without_command=True, no_pm=True)
    async def _banque(self, ctx, membre: discord.Member = None):
        """Ensemble de commandes relatives au compte bancaire

        En absence de mention, renvoie les détails du compte de l'invocateur"""
        if ctx.invoked_subcommand is None:
            if not membre:
                membre = ctx.message.author
            await ctx.invoke(self.compte, user=membre)

    @_banque.command(pass_context=True)
    async def new(self, ctx):
        """Ouvrir un compte bancaire sur ce serveur"""
        user = ctx.message.author
        data = self.api.get_account(user)
        if data:
            await self.bot.say("**Vous avez déjà un compte** ─ Consultez-le avec `{}b`".format(ctx.prefix))
            return
        msg = await self.bot.say("**Voulez-vous ouvrir un compte bancaire ?**\n*Il vous permettra d'obtenir des crédits"
                                 " nécessaires pour utiliser certaines fonctionnalités comme pour participer à des"
                                 " jeux etc.*")
        await self.bot.add_reaction(msg, "✔")
        await self.bot.add_reaction(msg, "✖")
        await asyncio.sleep(0.25)
        rep = await self.bot.wait_for_reaction(["✔", "✖"], message=msg, timeout=30,
                                               check=self.check, user=ctx.message.author)
        if rep is None or rep.reaction.emoji == "✖":
            await self.bot.say("**Annulé** | N'hésitez pas à refaire la commande dès que vous voudrez en ouvrir un")
            await self.bot.delete_message(msg)
            return
        elif rep.reaction.emoji == "✔":
            done = self.api.new_account(ctx.message.author)
            if done:
                await self.bot.say("**Créé** | Ton compte a été ouvert avec succès {} !".format(
                    ctx.message.author.name))
            else:
                await self.bot.say("**Erreur** | Le compte n'a pas pu être créé, "
                                   "le serveur est probablement sur *blacklist*")
            await self.bot.delete_message(msg)
            return
        else:
            await self.bot.say("**Erreur** | Désolé je n'ai pas compris...")
            return

    @_banque.command(pass_context=True)
    async def compte(self, ctx, user: discord.Member = None):
        """Voir son compte bancaire sur ce serveur et l'historique des transactions réalisées.

        [user] = permet de voir le profil d'un autre utilisateur"""
        data = self.api.get_account(user) if user else self.api.get_account(ctx.message.author)
        server = ctx.message.server
        if data:
            moneyname = self.api.get_money(server, data.solde)
            gains = self.api.get_total_day_gain(user)
            gainstxt = "+{}".format(gains) if gains >= 0 else "{}".format(gains)
            em = discord.Embed(description="**Solde** ─ {0} {1}\n"
                                           "**Bénéfice** ─ **{2}**".format(data.solde, moneyname,
                                                                                    gainstxt),
                               color=user.color if user else ctx.message.author.color)
            em.set_author(name=str(user) if user else str(ctx.message.author),
                          icon_url=user.avatar_url if user else ctx.message.author.avatar_url)
            trs = self.api.get_lasts_transactions(user if user else ctx.message.author, 3)
            trs.reverse()
            if trs:
                txt = ""
                for i in trs:
                    if i.type == "SET":
                        somme = "!{}".format(i.somme)
                    else:
                        somme = str(i.somme) if i.somme < 0 else "+{}".format(i.somme)
                    desc = i.desc if len(i.desc) <= 40 else i.desc[:38] + "..."
                    txt += "**{}** ─ *{}* `#{}`\n".format(somme, desc, i.id)
                em.add_field(name="Historique", value=txt)
            em.set_footer(text="`{0}b trs` ─ Voir transaction | `{0}b histo` ─ Voir historique".format(ctx.prefix))
            await self.bot.say(embed=em)
        else:
            if user != ctx.message.author:
                await self.bot.say("**Introuvable** | Cette personne ne possède pas de compte bancaire sur ce serveur")
            else:
                await self.api.inscription(ctx)

    @_banque.command(aliases=["histo"], pass_context=True)
    async def historique(self, ctx, user: discord.Member = None):
        """Affiche l'historique bancaire complet d'un membre"""
        data = self.api.get_account(user) if user else self.api.get_account(ctx.message.author)
        server = ctx.message.server
        if data:
            jour = time.strftime("%d/%m/%Y", time.localtime())
            msg = False
            while True:
                trs = self.api.get_day_transactions(user, jour)
                txt = ""
                n = 1
                delid = []
                if msg:
                    for i in delid:
                        await self.bot.delete_message(ctx.message.channel, await self.bot.get_message(i))
                for t in trs:
                    txt += "{} | **{}** ─ *{}* `#{}`\n".format(t.ts_heure, t.somme, t.desc, t.id)
                    if len(txt) > 1980 * n:
                        em = discord.Embed(title="Historique de {} | {}".format(user.name, jour),
                                           description=txt, color=user.color)
                        em.set_footer(text="─ Page {}".format(n))
                        txt = ""
                        n += 1
                        delmsg = await self.bot.say(embed=em)
                        delid.append(delmsg.id)

                em = discord.Embed(title="Historique de {} | {}".format(user.name, jour),
                                   description=txt, color=user.color)
                em.set_footer(text="─ Page {} | ⬅ ➡ = Naviguer |"
                                   " 🔢 = Entrer une date | 🚫 = Quitter".format(n, user.name, server.name))

                if not msg:
                    msg = await self.bot.say(embed=em)
                else:
                    msg = await self.bot.edit_message(msg, embed=em)
                await self.bot.add_reaction(msg, "⬅")
                await self.bot.add_reaction(msg, "🔢")
                if jour != time.strftime("%d/%m/%Y", time.localtime()):
                    await self.bot.add_reaction(msg, "➡")
                await self.bot.add_reaction(msg, "🚫")
                await asyncio.sleep(0.10)
                rep = await self.bot.wait_for_reaction(["⬅", "🔢", "➡", "🚫"], message=msg, timeout=60,
                                                       check=self.check, user=ctx.message.author)
                if rep is None or rep.reaction.emoji == "🚫":
                    await self.bot.delete_message(msg)
                    return
                elif rep.reaction.emoji == "⬅":
                    jour = time.strftime("%d/%m/%Y", time.localtime(
                        time.mktime(time.strptime(jour, "%d/%m/%Y")) - 86400))
                elif rep.reaction.emoji == "➡":
                    if jour != time.strftime("%d/%m/%Y", time.localtime()):
                        jour = time.strftime("%d/%m/%Y", time.localtime(
                            time.mktime(time.strptime(jour, "%d/%m/%Y")) + 86400))
                    else:
                        continue
                elif rep.reaction.emoji == "🔢":
                    em.set_footer(text="Entrez la date désirée ci-dessous (DD/MM/AAAA)")
                    await self.bot.edit_message(msg, embed=em)
                    rep = await self.bot.wait_for_message(author=user, channel=msg.channel, timeout=30)
                    if rep is None:
                        continue
                    elif len(rep.content) == 10:
                        if time.mktime(time.strptime(rep.content, "%d/%m/%Y")) > time.time():
                            await self.bot.delete_message(rep)
                            em.set_footer(text="Impossible d'aller dans le futur")
                            await self.bot.edit_message(msg, embed=em)
                        else:
                            jour = rep.content
                else:
                    continue
        else:
            await self.bot.say("**Inconnu** | Cet utilisateur n'a pas de compte bancaire.")

    @_banque.command(aliases=["trs"], pass_context=True)
    async def transaction(self, ctx, identifiant: str):
        """Permet de voir les détails d'une transaction

        Attention, les transactions ne sont pas conservées indéfiniment"""
        if len(identifiant) == 5:
            get = self.api.id_to_transaction_obj(identifiant)
            if get:
                somme = str(get.somme) if get.somme < 0 else "+{}".format(get.somme)
                serveur = "Ici" if get.server_id == ctx.message.server.id else get.server_id
                txt = "*{}*\n\n**Type** ─ {}\n**Somme** ─ {}\n**Date** ─ Le {} à {}\n**Compte** ─ <@{}>\n" \
                      "**Serveur** ─ {}".format(get.desc, get.type, somme, get.ts_jour, get.ts_heure, get.user_id,
                                                serveur)
                em = discord.Embed(title="Transaction #{}".format(identifiant), description=txt)
                em.set_footer(text="Liées: {}".format(", ".join(get.liens) if get.liens else "aucune"))
                await self.bot.say(embed=em)
            else:
                await self.bot.say("**Introuvable** | Mauvais identifiant ou transaction expirée")
        else:
            await self.bot.say("**Erreur** | Identifiant invalide (composé de 5 lettres et chiffres)")

    @_banque.command(aliases=["decode"], pass_context=True)
    async def unlock(self, ctx, code: str):
        """Interface permettant de rentrer des codes afin de débloquer des éléments"""
        data = self.api.get_account(ctx.message.author)
        if not data:
            done = await self.api.inscription(ctx)
            if not done:
                return
        gift = self.api.gift_exist(code)
        if gift:
            txt = "**Contenu** ─ {}\n" \
                  "**Valide sur** ─ {}".format(gift.contenu if type(gift.contenu) == int or type(gift.contenu) == str
                                            else "Multiple", self.bot.get_server(gift.server).name)
            em = discord.Embed(title="Code /{}/".format(code), color=ctx.message.author.color, description=txt)
            em.set_footer(text="Voulez-vous l'encaisser ?")
            msg = await self.bot.say(embed=em)
            await self.bot.add_reaction(msg, "✔")
            await self.bot.add_reaction(msg, "✖")
            await asyncio.sleep(0.25)
            rep = await self.bot.wait_for_reaction(["✔", "✖"], message=msg, timeout=30,
                                                   check=self.check, user=ctx.message.author)
            if rep is None or rep.reaction.emoji == "✖":
                await self.bot.say("**Annulé** | N'hésitez pas à refaire la commande dès que vous voudrez en ouvrir un")
                await self.bot.delete_message(msg)
                return
            elif rep.reaction.emoji == "✔":
                done = self.api.depot_gift(ctx.message.author, code)
                if done:
                    await self.bot.say("**Débloqué** | Tu as débloqué {} !".format(gift.desc))
                else:
                    await self.bot.say("**Erreur** | Impossible de débloquer le code "
                                       ": il a peut-être déjà été débloqué.")
                await self.bot.delete_message(msg)
                return
            else:
                await self.bot.say("**Erreur** | Annulation...")
                return

        else:
            await self.bot.say("**Code non-reconnu** | Le code n'est pas correct ou a déjà été utilisé.")

    @commands.command(aliases=["donner"], pass_context=True)
    async def give(self, ctx, user: discord.Member, somme: int, *raison):
        """Donner de l'argent à un autre membre

        Vous pouvez ajouter une raison à ce cadeau"""
        if not raison:
            raison = "Don de {} à {}".format(ctx.message.author.name, user.name)
        else:
            raison = " ".join(raison)
        if somme <= 0:
            await self.bot.say("**Erreur** | La somme doit être positive")
        if not self.api.get_account(ctx.message.author):
            done = await self.api.inscription(ctx)
            if not done:
                return
        if self.api.get_account(user):
            if self.api.get_account(ctx.message.author):
                if self.api.transfert_credits(user, ctx.message.author, somme, raison):
                    moneyname = self.api.get_money(ctx.message.server, somme)
                    await self.bot.say("**Succès** | {} {} ont été transférés à *{}*".format(somme, moneyname,
                                                                                             user.name))
                else:
                    await self.bot.say("**Erreur** | La transaction n'a pas pu se faire")
            else:
                await self.bot.say("**Erreur** | Vous n'avez pas de compte bancaire. "
                                   "Faîtes `{}b new` pour en ouvrir un.".format(ctx.prefix))
        else:
            await self.bot.say("**Erreur** | Le membre visé n'a pas de compte bancaire")

    @commands.command(aliases=["classement"], pass_context=True)
    async def palmares(self, ctx, nombre: int = 20):
        """Affiche un classement des X membres les plus riches du serveur"""
        server = ctx.message.server
        palm = self.api.gen_palmares(server, nombre)
        uid = ctx.message.author.id
        n = 1
        txt = ""
        for l in palm:
            if len(txt) > 1980:
                await self.bot.say("**Trop grand** | Discord n'accepte pas des messages aussi longs, "
                                   "réduisez le nombre")
                return
            try:
                username = server.get_member(l[1]).name
            except:
                username = self.bot.get_user(l[1]).name
            if l[1] == uid:
                txt += "**{}.** __**{}**__ ─ {}\n".format(n, username, l[0])
            else:
                txt += "**{}.** **{}** ─ {}\n".format(n, username, l[0])
            n += 1
        em = discord.Embed(title="Palmares", description=txt, color=0xf2d348)
        total = self.api.total_server_credits(server)
        em.set_footer(text="Sur le serveur {} | Total = {} {}".format(server.name, total,
                                                                     self.api.get_money(server, total, True)))
        try:
            await self.bot.say(embed=em)
        except:
            await self.bot.say("**Erreur** | Le classement est trop long pour être envoyé, réduisez le nombre")

# JEUX & DIVERS

    @commands.command(aliases=["rj"], pass_context=True)
    async def revenu(self, ctx):
        """Récupérer les revenus personnels"""
        user = ctx.message.author
        server = ctx.message.server
        date = time.strftime("%d/%m/%Y", time.localtime())
        data = self.api.get_account(user, True)
        if not self.api.get_account(user):
            done = await self.api.inscription(ctx)
            if not done:
                return
        if "REVENU_JOURNALIER" not in data["EXTRA"]:
            data["EXTRA"]["REVENU_JOURNALIER"] = None
        if self.api.get_account(user).solde < 10000:
            if date != data["EXTRA"]["REVENU_JOURNALIER"]:
                back = data["EXTRA"]["REVENU_JOURNALIER"]
                if back:
                    delta = int((time.mktime(time.strptime(date, "%d/%m/%Y")) - time.mktime(time.strptime(
                        back, "%d/%m/%Y"))) / 86400)
                else:
                    delta = 1
                data["EXTRA"]["REVENU_JOURNALIER"] = date
                rj = delta * 50
                if delta > 1:
                    mult = " ({}j x 50)".format(delta)
                else:
                    mult = ""
                if rj + self.api.get_account(user).solde <= 10000:
                    self.api.depot_credits(user, rj, "Revenus journaliers")
                else:
                    delta = int((10000 - self.api.get_account(user).solde)/rj)
                    rj = delta * 50
                    self.api.depot_credits(user, rj, "Revenus journaliers")
                em = discord.Embed(title="Revenu{}".format("s" if delta > 1 else ""),
                                   description="Votre revenu ─ **+{} {}**{}".format(rj, self.api.get_money(server, rj), mult),
                                   color=ctx.message.author.color)
                em.set_footer(text="Vous avez désormais {} {}".format(self.api.get_account(user).solde,
                                                                      self.api.get_money(server, rj)))
                await self.bot.say(embed=em)
            else:
                await self.bot.say("**Refusé** ─ Vous avez déjà pris votre revenu aujourd'hui")
        else:
            await self.bot.say("**Refusé** ─ Vous avez plus de 10 000 {}.".format(
                self.api.get_money(server, 10000, True)))

    @commands.command(aliases=["mas"], pass_context=True)
    async def slot(self, ctx, offre: int = None):
        """Jouer à la machine à sous

        L'offre doit être comprise entre 5 et 200"""
        user = ctx.message.author
        server = ctx.message.server
        if not offre:
            txt = ":100: x3 = Offre x 100\n" \
                  ":gem: x3 = Offre x 10\n" \
                  ":gem: x2 = Offre + 100\n" \
                  ":four_leaf_clover: x3 = Offre x 5\n" \
                  ":four_leaf_clover: x2 = Offre + 50\n" \
                  "**fruit** x3 = Offre x 3\n" \
                  "**fruit** x2 = Offre x 2\n" \
                  ":zap: x1 ou x2 = Perte immédiate\n" \
                  ":zap: x3 = Offre x 300"
            em = discord.Embed(title="Gains possibles", description=txt)
            await self.bot.say(embed=em)
            return
        if not 5 <= offre <= 200:
            await self.bot.say("**Offre invalide** | Elle doit être comprise entre 5 et 200.")
            return
        base = offre
        data = self.api.get_account(user)
        if not data:
            done = await self.api.inscription(ctx)
            if not done:
                return
        if self.api.enough_credits(user, offre):
            cool = self.api.is_cooldown_blocked(user, "slot")
            if not cool:
                self.api.add_cooldown(user, "slot", 15)
                roue = [":zap:", ":gem:", ":cherries:", ":strawberry:", ":watermelon:", ":tangerine:", ":lemon:",
                        ":four_leaf_clover:", ":100:"]
                plus_after = [":zap:", ":gem:", ":cherries:"]
                plus_before = [":lemon:", ":four_leaf_clover:", ":100:"]
                roue = plus_before + roue + plus_after
                cols = []
                for i in range(3):
                    n = random.randint(3, 11)
                    cols.append([roue[n - 1], roue[n], roue[n + 1]])
                centre = [cols[0][1], cols[1][1], cols[2][1]]
                disp = "**Offre:** {} {}\n\n".format(base, self.api.get_money(server, base))
                disp += "   {}|{}|{}\n".format(cols[0][0], cols[1][0], cols[2][0])
                disp += "**>** {}|{}|{}\n".format(cols[0][1], cols[1][1], cols[2][1])
                disp += "   {}|{}|{}\n".format(cols[0][2], cols[1][2], cols[2][2])
                c = lambda x: centre.count(":{}:".format(x))
                if ":zap:" in centre:
                    if c("zap") == 3:
                        offre *= 300
                        msg = "3x ⚡ ─ Tu gagnes {} {}"
                    else:
                        offre = 0
                        msg = "Tu t'es fait ⚡ ─ Tu perds ta mise !"
                elif c("100") == 3:
                    offre *= 100
                    msg = "3x 💯 ─ Tu gagnes {} {}"
                elif c("gem") == 3:
                    offre *= 10
                    msg = "3x 💎 ─ Tu gagnes {} {}"
                elif c("gem") == 2:
                    offre += 100
                    msg = "2x 💎 ─ Tu gagnes {} {}"
                elif c("four_leaf_clover") == 3:
                    offre *= 5
                    msg = "3x 🍀 ─ Tu gagnes {} {}"
                elif c("four_leaf_clover") == 2:
                    offre += 50
                    msg = "2x 🍀 ─ Tu gagnes {} {}"
                elif c("cherries") == 3 or c("strawberry") == 3 or c("watermelon") == 3 or c("tangerine") == 3 or c(
                        "lemon") == 3:
                    offre *= 3
                    msg = "3x un fruit ─ Tu gagnes {} {}"
                elif c("cherries") == 2 or c("strawberry") == 2 or c("watermelon") == 2 or c("tangerine") == 2 or c(
                        "lemon") == 2:
                    offre *= 2
                    msg = "2x un fruit ─ Tu gagnes {} {}"
                else:
                    offre = 0
                    msg = "Perdu ─ Tu perds ta mise !"

                intros = ["Ça tourne", "Croisez les doigts", "Peut-être cette fois-ci", "Alleeeezzz",
                          "Ah les jeux d'argent", "Les dés sont lancés", "Il vous faut un peu de CHANCE",
                          "C'est parti", "Bling bling", "Le début de la richesse"]
                intro = random.choice(intros)
                if base == 69:
                    intro = "Oh, petit cochon"
                m = None
                for i in range(3):
                    points = "•" * (i + 1)
                    pat = "**{}** {}".format(intro, points)
                    em = discord.Embed(title="Machine à sous ─ {}".format(user.name), description=pat,
                                       color=0x4286f4)
                    if not m:
                        m = await self.bot.say(embed=em)
                    else:
                        await self.bot.edit_message(m, embed=em)
                    await asyncio.sleep(0.50)
                if offre > 0:
                    gain = offre - base
                    self.api.depot_credits(user, gain, "Gain machine à sous")
                    em = discord.Embed(title="Machine à sous ─ {}".format(user.name), description=disp,
                                       color=0x41f468)
                else:
                    self.api.perte_credits(user, base, "Perte machine à sous")
                    em = discord.Embed(title="Machine à sous ─ {}".format(user.name), description=disp,
                                       color=0xf44141)
                em.set_footer(text=msg.format(offre, self.api.get_money(server, offre, True)))
                await self.bot.edit_message(m, embed=em)
            else:
                await self.bot.say("**Cooldown** ─ Patientez encore {}s".format(cool))
        else:
            await self.bot.say("**Solde insuffisant** ─ Réduisez votre offre si possible")

            # ------------- MODERATION ---------------------

    @commands.group(name="modbanque", aliases=["modbank", "mb"], pass_context=True)
    @checks.admin_or_permissions(ban_members=True)
    async def _modbanque(self, ctx):
        """Paramètres du module Capital et commandes de modération"""
        if ctx.invoked_subcommand is None:
            await send_cmd_help(ctx)

    def gen_giftcode(self, nom, n: int = 1):
        codes = []
        for i in range(n):
            if nom.upper() in codes:
                code = nom.upper() + "-{}".format(i + 1)
            else:
                code = nom.upper()
            codes.append(code)
        return codes

    @_modbanque.command(aliases=["code"], pass_context=True)
    async def giftcode(self, ctx, nom: str, somme: int, nombre: int = 1):
        """Permet de générer un ou plusieurs code(s) cadeau échangeable contre de l'argent sur le serveur"""
        nom = nom.upper()
        server = ctx.message.server
        self.api.server_update(server)
        total = self.api.total_server_credits(ctx.message.server)
        if somme < 5:
            await self.bot.say("**Erreur** | La valeur minimale de chaque code doit être de 5{}.".format(
                self.api.get_money(server, symbole=True)))
            return
        if (somme * nombre) >= total:
            await self.bot.say(
                "**Impossible** | La somme est excessive, le(s) code(s) contiendrait plus d'argent que "
                "ce qui circule actuellement sur le serveur.")
            return
        if nombre > 10:
            await self.bot.say("**Impossible** | Vous ne pouvez pas faire plus de 10 codes à la fois.")
            return
        if self.api.gift_exist(nom.upper()):
            await self.bot.say("**Déjà existant** | Un code ayant ce nom existe déjà.")
            return
        codes = self.gen_giftcode(nom, nombre)
        txt = ""
        data = self.api.get_server_sys(server, True)
        for code in codes:
            self.api.new_gift(code, server, somme)
            txt += "**{}**\n".format(code)
        em = discord.Embed(title="Codes ─ {} {}".format(somme, self.api.get_money(server, somme)), description=txt,
                           color=0xa3e1ff)
        em.set_footer(text="Aucune date d'expiration | Valables seulement sur ce serveur")
        await self.bot.whisper(embed=em)

    @_modbanque.command(pass_context=True)
    async def monnaie(self, ctx, *form):
        """Permet de changer le nom de la monnaie

        Format: singulier/pluriel/réduit (ou symbole)
        Ex: crédit/crédits/cds"""
        form = " ".join(form)
        server = ctx.message.server
        self.api.server_update(server)
        data = self.api.get_server_sys(server, True)
        if "/" in form:
            splitted = form.split("/")
            if len(splitted) is 3:
                data["MONNAIE"]["SINGULIER"] = splitted[0]
                data["MONNAIE"]["PLURIEL"] = splitted[1]
                data["MONNAIE"]["SYMBOLE"] = splitted[2]
                self.api.save_capital_api()
                txt = "• Singulier: {}\n" \
                      "• Pluriel: {}\n" \
                      "• Symbole: {}".format(splitted[0], splitted[1], splitted[2])
                em = discord.Embed(title="Changement de monnaie", description=txt)
                em.set_footer(text="Le nom de la monnaie sur ce serveur à été changé avec succès !")
                await self.bot.say(embed=em)
            else:
                await self.bot.say("**Format** | *singulier*/*pluriel*/*symbole* (ou raccourcis)")
        else:
            await self.bot.say("**Format** | *singulier*/*pluriel*/*symbole* (ou raccourcis)")

    @_modbanque.command(pass_context=True)
    async def modif(self, ctx, user: discord.Member, type: str, somme: int, *raison):
        """Modifie le solde d'un membre (+/-/!)

        ATTENTION : Utiliser cette commande de manière excessive interdira les membres de transférer leur argent sur d'autres serveurs"""
        get = self.api.get_account(user)
        self.api.server_update(ctx.message.server)
        data = self.api.get_server_sys(ctx.message.server, True)

        if somme < 0:
            await self.bot.say("**Erreur** | La valeur ne peut pas être négative")
            return
        if not raison:
            raison = "Solde modifié par {}".format(str(ctx.message.author))
        else:
            raison = " ".join(raison)
        total = self.api.total_server_credits(ctx.message.server)
        if get:

            avert = False
            if somme > int(total / 2) and type == "+":
                avert = True
            elif somme >= get.solde and type == "!":
                if (somme - get.solde) > int(total / 2):
                    avert = True
            if avert:
                if not self.api.get_server_sys(ctx.message.server).online:
                    msg = await self.bot.say(
                        "**Avertissement** ─ L'opération que vous allez réaliser est excessive "
                        "(>50% de l'argent total de ce serveur)\n*En faisant ça, "
                        "vous allez déséquilibrer l'économie sur le serveur et possiblement celle des "
                        "autres (à travers le transfert de crédit d'un serveur à un autre). C'est "
                        "pourquoi_une telle action va fermer cette possibilité aux membres de votre "
                        "serveur__ (jusqu'au reset des données de celui-ci)*\n"
                        "**Êtes-vous certain de le faire ?**")
                    await self.bot.add_reaction(msg, "✔")
                    await self.bot.add_reaction(msg, "✖")
                    await asyncio.sleep(0.25)
                    rep = await self.bot.wait_for_reaction(["✔", "✖"], message=msg, timeout=15,
                                                           check=self.check, user=ctx.message.author)
                    if rep is None or rep.reaction.emoji == "✖":
                        await self.bot.say("**Opération annulée**")
                        await self.bot.delete_message(msg)
                        return
                    elif rep.reaction.emoji == "✔":
                        data["ONLINE"] = True
                        await self.bot.say(
                            "**OK !** ─ Cet avertissement ne s'affichera plus à l'avenir (sauf reset)")
                        await self.bot.delete_message(msg)
                    else:
                        await self.bot.say("**Annulée** ─ La réponse n'est pas claire ...")
                        return

            if type == "+":
                done = self.api.depot_credits(user, somme, raison)
            elif type == "-":
                if self.api.enough_credits(user, somme):
                    done = self.api.perte_credits(user, somme, raison)
                else:
                    await self.bot.say("**Erreur** | La valeur dépasse l'argent que le membre possède")
                    return
            elif type == "!":
                done = self.api.set_credits(user, somme, raison)
            else:
                await self.bot.say("**Type inconnu** | **+** (Ajouter x), **-** (Retirer x), **!** (Régler sur x)")
                return
            if done:
                await self.bot.say("**Succès** | Le solde de l'utilisateur a été modifié")
            else:
                await self.bot.say("**Erreur** | Le solde n'a pas pu être modifié")
        else:
            await self.bot.say("**Impossible** | L'utilisateur ne possède pas de compte")

    @_modbanque.command(pass_context=True)
    async def forcenew(self, ctx, user: discord.Member):
        """Ouvre un compte de force à la place de l'utilisateur"""
        if not self.api.get_account(user):
            self.api.new_account(user)
            await self.bot.say("**Succès** | Le compte bancaire de {} à été créé".format(user.mention))
        else:
            await self.bot.say("**Erreur** | Ce membre possède déjà un compte bancaire")

    @_modbanque.command(pass_context=True)
    async def deleteuser(self, ctx, user: discord.Member):
        """Supprime le compte bancaire d'un membre"""
        if self.api.get_account(user):
            self.api.reset_user_data(user)
            await self.bot.say("**Succès** | Le compte du membre a été effacé")
        else:
            await self.bot.say("**Erreur** | Le membre ne possède pas de compte bancaire")

    @_modbanque.command(pass_context=True)
    async def resetserveur(self, ctx):
        """Reset les données du serveur, y compris la monnaie et les comptes bancaires des membres"""
        self.api.reset_server_data(ctx.message.server)
        await self.bot.say("**Succès** | Toutes les données du serveur ont été reset")

    @_modbanque.command(pass_context=True, hidden=True)
    async def backupfinance(self, ctx):
        """Permet de backup les données du module Finance pour ce serveur"""
        server = ctx.message.server
        self.api.backup_finance(ctx.message.server)
        await self.bot.say("**Succès** | Les données de Finance ont été importées")

def check_folders():
    if not os.path.exists("data/capital"):
        print("Creation du fichier Capital ...")
        os.makedirs("data/capital")


def check_files():
    if not os.path.isfile("data/capital/data.json"):
        print("Création de capital/data.json ...")
        fileIO("data/capital/data.json", "save", {})


def setup(bot):
    check_folders()
    check_files()
    n = Capital(bot)
    bot.add_cog(n)