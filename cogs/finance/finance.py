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


class FinanceAPI:
    """API Finance | Système commun de monnaie sur le bot"""
    def __init__(self, bot, path):
        self.bot = bot
        self.eco = dataIO.load_json(path)

    def _save(self):
        """Sauvegarde l'API seulement"""
        fileIO("data/finance/eco.json", "save", self.eco)
        return True

    def new(self, user: discord.Member):
        """Création d'un nouveau profil

        Renvoie True si créé, False si déjà présent"""
        server = user.server
        if server.id == "321734343695532033":
            return False
        if server.id not in self.eco:
            self.eco[server.id] = {}
        if user.id not in self.eco:
            self.eco[server.id][user.id] = {"SOLDE": 100,
                                            "TRSAC": [],
                                            "EXTRA": {},
                                            "CREE": datetime.datetime.now().strftime("%d/%m/%Y à %H:%M")}
            self._save()
            return True
        else:
            return False

    def get(self, user: discord.Member, w: bool = False, m: bool = False):
        """Retourne les informations d'un utilisateur

        Renvoie False si non présent, sinon renvoie un namedtuple de ses infos"""
        server = user.server
        if server.id not in self.eco:
            self.eco[server.id] = {}
            self._save()
        if user.id not in self.eco[server.id]:
            if m:  # make
                self.new(user)
            else:
                return False
        if not w:  # write
            user = self.eco[server.id][user.id]
            Compte = namedtuple('Compte', ['id', 'extra', 'solde', 'trsac', 'transactions', 'timestamp'])
            return Compte(id, user["EXTRA"], user["SOLDE"], user["TRSAC"], user["TRSAC"], user["CREE"])
        else:
            return self.eco[server.id][user.id]

    def obj_transaction(self, trans: list):
        """Transforme une transaction de format liste en format namedtuple

        Renvoie un namedtuple de la Transaction"""
        servid = userid = None
        for s in self.eco:
            for u in self.eco[s]:
                if trans in self.eco[s][u]["TRSAC"]:
                    servid = s
                    userid = u
        Transaction = namedtuple('Transaction', ['id', 'ts_heure', 'ts_jour', 'somme', 'desc', 'user_id', 'server_id',
                                                 'liens', 'type'])
        return Transaction(trans[0], trans[1], trans[2], trans[3], trans[4], userid, servid, trans[5], trans[6])
        # --Info             id       heure     jour      somme     desc      ----    ----    link       type

    def apd_transaction(self, user: discord.Member, type: str, somme: int, desc: str):
        """Ajoute une transaction à l'utilisateur

        Renvoie obj_transaction()"""
        origin = user
        user = self.get(user, True)
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
        return self.obj_transaction(event)

    def link_transactions(self, trans_a, trans_b):
        """Lie deux transactions entre elles

        Renvoie un bool"""
        a = self.id_to_transaction_obj(trans_a, True)
        b = self.id_to_transaction_obj(trans_b, True)
        if a and b:
            a[5].append(b[0])
            b[5].append(a[0])
            self._save()
            return True
        return False

    def id_to_transaction_obj(self, transaction_id: str, w: bool=False):
        """Retrouve une transaction à partir de l'identifiant universel

        Renvoie obj_transaction()"""
        for serv in self.eco:
            for user in self.eco[serv]:
                for tr in self.eco[serv][user]["TRSAC"]:
                    if tr[0] == transaction_id:
                        return self.obj_transaction(tr) if not w else tr
        return False

    def get_lasts_transactions(self, user: discord.Member, nombre: int = 1):
        """Renvoie une liste des x dernières transactions

        Renvoie une liste d'obj_transaction()"""
        user = self.get(user, True)
        if user:
            h = user["TRSAC"][-nombre:]
            liste = []
            for i in h:
                liste.append(self.obj_transaction(i))
            return liste
        else:
            return False

    def total_server_credits(self, server: discord.Server):
        """Renvoie le nombre de crédits possédés au total sur le serveur"""
        if server.id not in self.eco:
            self.eco[server.id] = {}
            self._save()
        total = 0
        for u in self.eco[server.id]:
            total += self.eco[server.id][u]["SOLDE"]
        return total

    def enough_credits(self, user:discord.Member, need:int):
        """Vérifie si le membre possède assez d'argent

        Renvoie un bool"""
        data = self.get(user)
        if data:
            if data.solde - need >= 0:
                return True
        return False

    def depot_credits(self, user: discord.Member, nombre: int, raison: str):
        """Dépose des crédits sur le compte de la personne

        Renvoie un bool correspondant à l'acceptation de la transaction"""
        data = self.get(user, True)
        if nombre <= 0:
            return False
        data["SOLDE"] += nombre
        t = self.apd_transaction(user, "DEPOT", nombre, raison)
        self._save()
        return t

    def perte_credits(self, user: discord.Member, nombre: int, raison: str):
        """Retire des crédits sur le compte de la personne

        Renvoie un bool correspondant à l'acceptation de la transaction"""
        data = self.get(user, True)
        if nombre < 0:
            nombre = -nombre
        if (data["SOLDE"] - nombre) >= 0:
            data["SOLDE"] -= nombre
            t = self.apd_transaction(user, "PERTE", -nombre, raison)
            self._save()
            return t
        return False

    def set_credits(self, user: discord.Member, nombre: int, raison: str):
        """Règle les crédits de la personne à cette somme précise

        Renvoie un bool correspondant à l'acceptation de la transaction"""
        data = self.get(user, True)
        if nombre >= 0:
            data["SOLDE"] = nombre
            t = self.apd_transaction(user, "SET", nombre, raison)
            self._save()
            return t
        return False

    def transfert_credits(self, crean: discord.Member, debit: discord.Member, nombre: int, raison: str):
        """Transfère un certain nombre de crédits du membre Débitteur (qui paye) au membre Créancier (qui recoit)

        Renvoie un bool correspondant à l'acceptation de la transaction"""
        if crean is debit:
            return False
        debitdata = self.get(debit, True)
        if nombre > 0:
            if (debitdata["SOLDE"] - nombre) >= 0:
                ta = self.perte_credits(debit, nombre, raison)
                tb = self.depot_credits(crean, nombre, raison)
                self.link_transactions(ta.id, tb.id)
                return True
            return False
        return False

    def get_accounts(self, server: discord.Server = None):
        """Renvoie une liste des tous les comptes d'un serveur (objets)"""
        liste = []
        if not server:
            for serv in self.eco:
                server = self.bot.get_server(serv)
                for member in server.members:
                    liste.append(self.get(member))
        else:
            for member in server.members:
                liste.append(self.get(member))
        if liste:
            return liste
        return False

    def gen_palmares(self, server: discord.Server, nombre: int):
        """Renvoie une liste ordonnée des membres les plus riches"""
        if server.id in self.eco:
            liste = [[self.eco[server.id][u]["SOLDE"], u] for u in self.eco[server.id]]
            sort = sorted(liste, key=operator.itemgetter(0), reverse=True)
            return sort[:nombre]
        else:
            return False

    def reset_server_data(self, server: discord.Server, all: bool = False):
        """Supprime les données d'un serveur"""
        if all:
            self.eco = {}
        if server.id in self.eco:
            self.eco[server.id] = {}
        else:
            return False
        self._save()
        return True

    def reset_user_data(self, user: discord.Member):
        """Supprime les données d'un membre du serveur"""
        server = user.server
        if server.id in self.eco:
            if user.id in self.eco[server.id]:
                del self.eco[server.id][user.id]
                self._save()
                return True
        return False

class Finance:
    """Economie centralisée pour les divers jeux"""
    def __init__(self, bot):
        self.bot = bot
        self.api = FinanceAPI(bot, "data/finance/eco.json")
        self.sys = dataIO.load_json("data/finance/sys.json")
        self.sys_defaut = {"MONEY_NAME": "crédit", "MONEY_NAME_PLURIEL": "crédits", "MONEY_SYMBOLE": "cds",
                           "MODDED": False, "COOLDOWN": {}}

    def credits_str(self, server: discord.Server, nombre=None, reduc: bool = False):
        if server.id not in self.sys:
            self.sys[server.id] = self.sys_defaut
            fileIO("data/finance/sys.json", "save", self.sys)
        if reduc:
            return self.sys[server.id]["MONEY_SYMBOLE"]
        if nombre:
            if int(nombre) > 1:
                return self.sys[server.id]["MONEY_NAME_PLURIEL"]
            return self.sys[server.id]["MONEY_NAME"]
        return self.sys[server.id]["MONEY_NAME_PLURIEL"]  # par défaut le pluriel

    def server_update(self, server: discord.Server):
        if server.id not in self.sys:
            self.sys[server.id] = self.sys_defaut
            fileIO("data/finance/sys.json", "save", self.sys)
        for cat in self.sys_defaut:
            if cat not in self.sys[server.id]:
                self.sys[server.id][cat] = self.sys_defaut[cat]
        fileIO("data/finance/sys.json", "save", self.sys)
        return True

    def add_cooldown(self, user: discord.Member, nom:str, duree:int):
        server = user.server
        self.server_update(server)
        date = time.time() + duree
        if nom.lower() not in self.sys[server.id]["COOLDOWN"]:
            self.sys[server.id]["COOLDOWN"][nom.lower()] = {}
        if user.id not in self.sys[server.id]["COOLDOWN"][nom.lower()]:
            self.sys[server.id]["COOLDOWN"][nom.lower()][user.id] = date
        else:
            self.sys[server.id]["COOLDOWN"][nom.lower()][user.id] += duree
        return self.sys[server.id]["COOLDOWN"][nom.lower()][user.id]

    def is_cooldown_blocked(self, user: discord.Member, nom: str): #  Bloqué par le cooldown ?
        server = user.server
        self.server_update(server)
        now = time.time()
        if nom.lower() not in self.sys[server.id]["COOLDOWN"]:
            return False
        if user.id in self.sys[server.id]["COOLDOWN"][nom.lower()]:
            if now <= self.sys[server.id]["COOLDOWN"][nom.lower()][user.id]:
                duree = int(self.sys[server.id]["COOLDOWN"][nom.lower()][user.id] - now)
                return duree
            else:
                del self.sys[server.id]["COOLDOWN"][nom.lower()][user.id]
                return False
        return False

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
        data = self.api.get(user)
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
            done = self.api.new(ctx.message.author)
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
        data = self.api.get(user) if user else self.api.get(ctx.message.author)
        server = ctx.message.server
        if data:
            moneyname = self.credits_str(server, data.solde)
            em = discord.Embed(description="**Solde** ─ {} {}".format(data.solde, moneyname),
                               color=user.color if user else ctx.message.author.color)
            em.set_author(name=str(user) if user else str(ctx.message.author),
                          icon_url=user.avatar_url if user else ctx.message.author.avatar_url)
            trs = self.api.get_lasts_transactions(user if user else ctx.message.author, 5)
            if trs:
                txt = ""
                for i in trs:
                    if i.type == "SET":
                        somme = "!{}".format(i.somme)
                    else:
                        somme = str(i.somme) if i.somme < 0 else "+{}".format(i.somme)
                    desc = i.desc if len(i.desc) <= 40 else i.desc[:38] + "..."
                    txt += "**{}** ─ *{}* [{}]\n".format(somme, desc, i.id)
                em.add_field(name="Historique des transactions", value=txt)
            em.set_footer(text="Compte ouvert le {}".format(data.timestamp))
            await self.bot.say(embed=em)
        else:
            if user != ctx.message.author:
                await self.bot.say("**Introuvable** | Cette personne ne possède pas de compte bancaire sur ce serveur")
            else:
                msg = await self.bot.say("**Vous n'avez pas de compte bancaire** | Voulez-vous en ouvrir un ?")
                await self.bot.add_reaction(msg, "✔")
                await self.bot.add_reaction(msg, "✖")
                await asyncio.sleep(0.25)
                rep = await self.bot.wait_for_reaction(["✔", "✖"], message=msg, timeout=20,
                                                       check=self.check, user=ctx.message.author)
                if rep is None or rep.reaction.emoji == "✖":
                    await self.bot.say("**OK !** ─ Vous pourrez toujours en ouvrir un plus tard avec `{}b new` ".format(
                        ctx.prefix))
                    await self.bot.delete_message(msg)
                    return
                elif rep.reaction.emoji == "✔":
                    done = self.api.new(ctx.message.author)
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
                em = discord.Embed(title="Transaction [{}]".format(identifiant), description=txt)
                em.set_footer(text="Liées: {}".format(", ".join(get.liens) if get.liens else "aucune"))
                await self.bot.say(embed=em)
            else:
                await self.bot.say("**Introuvable** | Mauvais identifiant ou transaction expirée")
        else:
            await self.bot.say("**Erreur** | Identifiant invalide (composé de 5 lettres et chiffres)")

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
        if self.api.get(user):
            if self.api.get(ctx.message.author):
                if self.api.transfert_credits(user, ctx.message.author, somme, raison):
                    moneyname = self.credits_str(ctx.message.server, somme)
                    await self.bot.say("**Succès** | {} {} ont été transférés à *{}*".format(somme, moneyname,
                                                                                            user.name))
                else:
                    await self.bot.say("**Erreur** | La transaction n'a pas pu se faire")
            else:
                await self.bot.say("**Erreur** | Vous n'avez pas de compte bancaire. "
                                   "Faîtes `{}b new` pour en ouvrir un.".format(ctx.prefix))
        else:
            await self.bot.say("**Erreur** | Le membre n'a pas de compte bancaire")

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
            if l[1] == uid:
                txt += "**{}.** __**{}**__ ─ {}\n".format(n, server.get_member(l[1]).name, l[0])
            else:
                txt += "**{}.** **{}** ─ {}\n".format(n, server.get_member(l[1]).name, l[0])
            n += 1
        em = discord.Embed(title="Palmares", description=txt, color=0xf2d348)
        total = self.api.total_server_credits(server)
        em.set_footer(text="Sur le serveur {} | Total = {}{}".format(server.name, total,
                                                                     self.credits_str(server, total, True)))
        try:
            await self.bot.say(embed=em)
        except:
            await self.bot.say("**Erreur** | Le classement est trop long pour être envoyé, réduisez le nombre")

    # ------------- JEUX & AUTRE -------------------

    @commands.command(aliases=["rj"], pass_context=True)
    async def revenu(self, ctx):
        """Percevoir son revenu journalier

        Il ne peut pas être perçu si vous avez plus de 10 000 crédits"""
        user = ctx.message.author
        server = ctx.message.server
        date = time.strftime("%d/%m/%Y", time.localtime())
        data = self.api.get(user, True)
        if "EXTRA" not in data:
            data["EXTRA"] = {}
        if "REVENU_DATE" not in data["EXTRA"]:
            data["EXTRA"]["REVENU_DATE"] = None
        if self.api.get(user).solde < 10000:
            if date != data["EXTRA"]["REVENU_DATE"]:
                data["EXTRA"]["REVENU_DATE"] = date
                self.api.depot_credits(user, 50, "Revenu journalier")
                await self.bot.say("**Revenu** ─ Vous avez reçu 50 {} sur votre compte {} !".format(
                    self.credits_str(server, 50), user.name))
            else:
                await self.bot.say("**Refusé** ─ Vous avez déjà pris votre revenu aujourd'hui")
        else:
            await self.bot.say("**Refusé** ─ Vous avez plus de 10 000 {}.".format(
                self.credits_str(server, 10000, True)))

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
        data = self.api.get(user)
        if data:
            if self.api.enough_credits(user, offre):
                cool = self.is_cooldown_blocked(user, "slot")
                if not cool:
                    self.add_cooldown(user, "slot", 30)
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
                    disp = "**Offre:** {} {}\n\n".format(base, self.credits_str(server, base))
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
                    m = None
                    for i in range(3):
                        points = "•" * (i + 1)
                        pat = "**{}** {}".format(intro, points)
                        em = discord.Embed(title="Machine à sous ─ {}".format(user.name), description=pat, color=0x4286f4)
                        if not m:
                            m = await self.bot.say(embed=em)
                        else:
                            await self.bot.edit_message(m, embed=em)
                        await asyncio.sleep(1)
                    if offre > 0:
                        gain = offre - base
                        self.api.depot_credits(user, gain, "Gain machine à sous")
                        em = discord.Embed(title="Machine à sous ─ {}".format(user.name), description=disp, color=0x41f468)
                    else:
                        self.api.perte_credits(user, base, "Perte machine à sous")
                        em = discord.Embed(title="Machine à sous ─ {}".format(user.name), description=disp, color=0xf44141)
                    em.set_footer(text=msg.format(offre, self.credits_str(server, offre, True)))
                    await self.bot.edit_message(m, embed=em)
                else:
                    await self.bot.say("**Cooldown** ─ Patientez encore {}s".format(cool))
            else:
                await self.bot.say("**Solde insuffisant** ─ Réduisez votre offre si possible")
        else:
            await self.bot.say("**Vous n'avez pas de compte** ─ Ouvrez-en un avec `{}b new`".format(ctx.prefix))

# ------------- MODERATION ---------------------

    @commands.group(name="modbanque", aliases=["modbank", "mb"], pass_context=True)
    @checks.admin_or_permissions(ban_members=True)
    async def _modbanque(self, ctx):
        """Paramètres du module Finance et commandes de modération"""
        if ctx.invoked_subcommand is None:
            await send_cmd_help(ctx)

    @_modbanque.command(pass_context=True)
    async def monnaie(self, ctx, *form):
        """Permet de changer le nom de la monnaie

        Format: singulier/pluriel/réduit (ou symbole)
        Ex: crédit/crédits/cds"""
        form = " ".join(form)
        server = ctx.message.server
        if "/" in form:
            splitted = form.split("/")
            if len(splitted) is 3:
                if server.id not in self.sys:
                    self.sys[server.id] = self.sys_defaut
                self.sys[server.id]["MONEY_NAME"] = splitted[0]
                self.sys[server.id]["MONEY_NAME_PLURIEL"] = splitted[1]
                self.sys[server.id]["MONEY_SYMBOLE"] = splitted[2]
                fileIO("data/finance/sys.json", "save", self.sys)
                txt = "__**Nouvelle monnaie**__\n" \
                      "• Singulier: {}\n" \
                      "• Pluriel: {}\n" \
                      "• Symbole (ou raccourcis): {}".format(splitted[0], splitted[1], splitted[2])
                await self.bot.say(txt)
            else:
                await self.bot.say("**Format** | *singulier*/*pluriel*/*symbole* (ou raccourcis)")
        else:
            await self.bot.say("**Format** | *singulier*/*pluriel*/*symbole* (ou raccourcis)")

    @_modbanque.command(pass_context=True)
    async def modif(self, ctx, user: discord.Member, type:str, somme:int, *raison):
        """Modifie le solde d'un membre (+/-/!)

        ATTENTION : Utiliser cette commande de manière excessive interdira les membres de transférer leur argent sur d'autres serveurs"""
        get = self.api.get(user)
        self.server_update(ctx.message.server)
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
                if (somme - get.solde) > int(total /2):
                    avert = True
            if avert:
                if not self.sys[ctx.message.server.id]["MODDED"]:
                    msg = await self.bot.say("**Avertissement** ─ L'opération que vous allez réaliser est excessive "
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
                        self.sys[ctx.message.server.id]["MODDED"] = True
                        fileIO("data/finance/sys.json", "save", self.sys)
                        await self.bot.say("**OK !** ─ Cet avertissement ne s'affichera plus à l'avenir (sauf reset)")
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
        if not self.api.get(user):
            self.api.new(user)
            await self.bot.say("**Succès** | Le compte bancaire de {} à été créé".format(user.mention))
        else:
            await self.bot.say("**Erreur** | Ce membre possède déjà un compte bancaire")

    @_modbanque.command(pass_context=True)
    async def deleteuser(self, ctx, user: discord.Member):
        """Supprime le compte bancaire d'un membre"""
        if self.api.get(user):
            self.api.reset_user_data(user)
            await self.bot.say("**Succès** | Le compte du membre a été effacé")
        else:
            await self.bot.say("**Erreur** | Le membre ne possède pas de compte bancaire")

    @_modbanque.command(pass_context=True)
    async def resetserveur(self, ctx):
        """Reset les données du serveur, y compris la monnaie et les comptes bancaires des membres"""
        self.api.reset_server_data(ctx.message.server)
        self.sys[ctx.message.server.id] = self.sys_defaut
        fileIO("data/finance/sys.json", "save", self.sys)
        await self.bot.say("**Succès** | Toutes les données du serveur ont été reset")

def check_folders():
    if not os.path.exists("data/finance"):
        print("Creation du fichier Finance ...")
        os.makedirs("data/finance")

def check_files():
    if not os.path.isfile("data/finance/sys.json"):
        print("Création de finance/sys.json ...")
        fileIO("data/finance/sys.json", "save", {})
    if not os.path.isfile("data/finance/eco.json"):
        print("Création de finance/eco.json ...")
        fileIO("data/finance/eco.json", "save", {})

def setup(bot):
    check_folders()
    check_files()
    n = Finance(bot)
    bot.add_cog(n)