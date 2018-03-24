import os
import random
import re
import string
import time
from datetime import datetime

import discord
from __main__ import send_cmd_help
from cogs.utils.chat_formatting import escape_mass_mentions
from discord.ext import commands

from .utils import checks
from .utils.dataIO import dataIO, fileIO


class SocialAPI:
    """API | Extension sociale & statistique pour Discord - Version UNIVERSELLE"""
    def __init__(self, bot, path):
        self.bot = bot
        self.soc = dataIO.load_json(path)
        self.past_names = dataIO.load_json("data/mod/past_names.json")
        self.past_nicknames = dataIO.load_json("data/mod/past_nicknames.json")
        self.update()

    def apisave(self):
        fileIO("data/social/soc.json", "save", self.soc)
        return True

    def get(self, user: discord.Member, sub: str = None):
        """Retourne le dict de l'utilisateur contenant toutes les données disponibles"""
        server = user.server
        if server.id in self.soc:
            if user.id not in self.soc[server.id]:
                clef = str(''.join(random.SystemRandom().choice(string.ascii_uppercase + string.digits) for _ in range(3)))
                self.soc[server.id][user.id] = {"CLEF": clef,
                                                "STATS": {},
                                                "SOC": {},
                                                "ECO": {},
                                                "LOGS": [],
                                                "ENRG": time.time()}
                self.update(user)
        return self.soc[server.id][user.id][sub] if sub else self.soc[server.id][user.id]

    def update(self, user: discord.Member = None, serverid: int = None):
        if user:
            server = user.server.id
        else:
            server = serverid
        tree = {"STATS": {"MSG_TOTAL": 0,
                          "MSG_SUPPR": 0,
                          "MSG_CHANS": {},
                          "EMOJIS": {},
                          "JOIN": 0,
                          "QUIT": 0,
                          "BAN": 0},
                "SOC": {"BIO": "",
                        "VITRINE": None,
                        "SUCCES": {},
                        "FLAMMES": [],
                        "MSG_FLUX": {},
                        "MSG_SAVE": {},
                        "SEXE": "neutre",
                        "ROLE_SAVE": [],
                        "GRADELIMIT": 3},
                "ECO": {"SOLDE": 100,
                        "TRS": [],
                        "SAC": {}}}
        for cat in tree:
            if server:
                if user:
                    if cat not in self.soc[server][user.id]:
                        self.soc[server][user.id][cat] = tree[cat]
                else:
                    for u in self.soc[server]:
                        if cat not in self.soc[server][u]:
                            self.soc[server][u][cat] = tree[cat]
                for sub in tree[cat]:
                    if user:
                        if sub not in self.soc[server][user.id][cat]:
                            self.soc[server][user.id][cat][sub] = tree[cat][sub]
                    else:
                        for u in self.soc[server]:
                            if cat in self.soc[server][u]:  # Sécurité en +
                                if sub not in self.soc[server][u][cat]:
                                    self.soc[server][u][cat][sub] = tree[cat][sub]
            else:
                for server in self.soc:
                    if user:
                        if cat not in self.soc[server][user.id]:
                            self.soc[server][user.id][cat] = tree[cat]
                    else:
                        for u in self.soc[server]:
                            if cat not in self.soc[server][u]:
                                self.soc[server][u][cat] = tree[cat]
                    for sub in tree[cat]:
                        if user:
                            if sub not in self.soc[server][user.id][cat]:
                                self.soc[server][user.id][cat][sub] = tree[cat][sub]
                        else:
                            for u in self.soc[server]:
                                if cat in self.soc[server][u]:  # Sécurité en +
                                    if sub not in self.soc[server][u][cat]:
                                        self.soc[server][u][cat][sub] = tree[cat][sub]
        if not user:
            fileIO("data/social/soc.json", "save", self.soc)
        return True

    def nb_servers(self, user: discord.Member):
        nb = 0
        for s in self.soc:
            if user.id in self.soc[s]:
                nb += 1
        return nb

    def sync(self, user: discord.Member, servbase: discord.Server, categorie: str, data=None):
        tosync = self.soc[servbase.id][user.id][categorie][data] if data else self.soc[servbase.id][user.id][categorie]
        for s in self.soc:
            if user.id in self.soc[s]:
                if data:
                    self.soc[s][user.id][categorie][data] = tosync
                else:
                    self.soc[s][user.id][categorie] = tosync
        return True

    def add_log(self, user: discord.Member, event: str):
        p = self.get(user)
        jour = time.strftime("%d/%m/%Y", time.localtime())
        heure = time.strftime("%H:%M", time.localtime())
        p["LOGS"].append([heure, jour, event])
        return True

    def color_disp(self, user: discord.Member):
        s = user.status
        if not user.bot:
            if s == discord.Status.online:
                return 0x43B581  # Vert
            elif s == discord.Status.idle:
                return 0xFAA61A  # Jaune
            elif s == discord.Status.dnd:
                return 0xF04747  # Rouge
            else:
                return 0x9ea0a3  # Gris
        else:
            return 0x2e6cc9  # Bleu

    def namelist(self, user: discord.Member):
        server = user.server
        names = self.past_names[user.id] if user.id in self.past_names else None
        try:
            nicks = self.past_nicknames[server.id][user.id]
            nicks = [escape_mass_mentions(nick) for nick in nicks]
        except:
            nicks = ""
        if names:
            names = [escape_mass_mentions(name) for name in names]
        else:
            names = ""
        return names, nicks

    def grade(self, user: discord.Member):
        data = self.get(user)
        roles = [r.name for r in user.roles]
        msg = data["STATS"]["MSG_TOTAL"]
        sexe = data["SOC"]["SEXE"]
        limite = data["SOC"]["GRADELIMIT"]
        cond = {"ROLES": 1,
                "RANG": 1}
        if "Oldfag" in roles:
            cond["ROLES"] = 2
        if "Malsain" in roles or "Modérateur" in roles or "Administrateur" in roles:
            cond["ROLES"] = 3
        if 10000 <= msg <= 30000:
            cond["RANG"] = 2
        elif 30000 < msg:
            cond["RANG"] = 3
        if cond["ROLES"] >= cond["RANG"]:
            nb = cond["ROLES"]
        else:
            nb = cond["RANG"]
        nom = ""
        if nb >= limite:
            nb = limite
        if nb == 2:
            if sexe == "masculin":
                nom = "Résident"
            elif sexe == "feminin":
                nom = "Résidente"
            else:
                nom = "Résident·e"
            return [nom, "https://i.imgur.com/QIjRE8D.png", 2]
        elif nb == 3:
            if sexe == "masculin":
                nom = "Citoyen"
            elif sexe == "feminin":
                nom = "Citoyenne"
            else:
                nom = "Citoyen·ne"
            return [nom, "https://i.imgur.com/I1mfblA.png", 3]
        else:
            if sexe == "masculin":
                nom = "Migrant"
            elif sexe == "feminin":
                nom = "Migrante"
            else:
                nom = "Migrant·e"
            return [nom, "https://i.imgur.com/2jEjkcV.png", 1]


class Social:
    """Social | Module ajoutant des fonctionnalités sociales et statistiques - Version universelle"""

    def __init__(self, bot):
        self.bot = bot
        self.api = SocialAPI(bot, "data/social/soc.json")  # SocialAPI-> UNIV
        self.sys = dataIO.load_json("data/social/sys.json")
        self._save_instance = {"COUNT": 0, "NEED": 100, "SAVETIME": time.time() + 300, "FIRST": False}
        self.quit_msg = ["Au revoir {} !", "Bye bye {}.", "{} s'est trompé de bouton.",
                         "{} a été suicidé de deux bans dans le dos.", "{} a ragequit le serveur.",
                         "GAME OVER {}", "A jamais {} !", "Les meilleurs partent en premier, sauf {}...",
                         "{} est parti, un de moins !", "{} s'envole vers d'autres cieux !", "YOU DIED {}",
                         "De toute évidence {} ne faisait pas parti de l'élite.", "{} a sauté d'un trottoir.",
                         "{} a roulé jusqu'en bas de la falaise.", "{} est parti ouvrir son propre serveur...",
                         "{} n'était de toute évidence pas assez *gaucho* pour ce serveur.",
                         "{}... désolé c'est qui ce random ?", "On m'annonce à l'oreillette que {} est parti.",
                         "C'est la fin pour {}...",
                         "{} a été jeté dans la fosse aux randoms.", "{} est parti rejoindre Johnny...",
                         "{} ne supportait plus d'être l'*Omega* du serveur.", "{} a paniqué une fois de plus.",
                         "{} s'est *enfin* barré !", "Plus besoin de le bloquer, {} est parti !",
                         "Boop bip boup {} bip", "{} a pris sa retraite.",
                         "{} a disparu dans des circonstances floues...", "Non pas toi {} ! 😢",
                         "{} a quitté. Un de plus ou un de moins hein...",
                         "{} était de toute évidence trop underground pour ce serveur de normies.",
                         "{} est parti faire une manif'.",
                         "{} a quitté/20", "Ce n'est qu'un *au revoir* {} !"]

    def smart_save(self):  # Oeuvre d'art ce truc
        if not self._save_instance["FIRST"]:
            self.api.apisave()
            self._save_instance["FIRST"] = True
        self._save_instance["COUNT"] += 1
        if self._save_instance["COUNT"] >= self._save_instance["NEED"]:
            self._save_instance["COUNT"] = 0
            self.api.apisave()
            if time.time() < self._save_instance["SAVETIME"]:
                if self._save_instance["NEED"] < 500:
                    self._save_instance["NEED"] += 10
                    self._save_instance["SAVETIME"] = time.time() + 300
            elif time.time() > self._save_instance["SAVETIME"] + 300:
                if self._save_instance["NEED"] > 30:
                    self._save_instance["NEED"] -= 10
                    self._save_instance["SAVETIME"] = time.time() + 300
            else:
                self._save_instance["SAVETIME"] = time.time() + 300
        return True

    @commands.group(no_pm=True, pass_context=True)
    @checks.admin_or_permissions(manage_roles=True)
    async def socmod(self, ctx):
        """Gestion des paramètres du module Social"""
        if ctx.invoked_subcommand is None:
            await send_cmd_help(ctx)

    @socmod.command(pass_context=True)
    async def forcesave(self, ctx):
        """Permet de forcer la sauvegarde des données (en cas d'API Discord instable)"""
        if self.api.apisave():
            await self.bot.say("**Sauvegarde forcée effectuée avec succès**")
        else:
            await self.bot.say("Impossible de réaliser la sauvegarde")

    @socmod.command(pass_context=True)
    async def limite(self, ctx, user: discord.Member, lim: int = 3):
        """Permet de limiter le grade du membre visé
        1 - Migrant·e maximum
        2 - Résident·e maximum
        3 - Aucune limitation"""
        data = self.api.get(user, "SOC")
        if lim == 1:
            data["GRADELIMIT"] = lim
            await self.bot.say("**Succès** | Le membre sera limité au grade *Migrant*")
        elif lim == 2:
            data["GRADELIMIT"] = lim
            await self.bot.say("**Succès** | Le membre sera limité au grade *Résident*")
        elif lim == 3:
            data["GRADELIMIT"] = None
            await self.bot.say("**Succès** | Le membre ne sera pas limité dans son grade")
        else:
            await self.bot.say("**Impossible** | La valeur doit être entre 1 et 3 (Voir `&help socmod limite`)")
        self.smart_save()

    @socmod.command(pass_context=True)
    async def restore(self, ctx, user: discord.Member):
        """Permet de restaurer les rôles du membre qu'il a perdu en quittant le serveur (ou kick/ban) [BETA]"""
        data = self.api.get(user, "SOC")
        server = user.server
        if not data["ROLE_SAVE"]:
            await self.bot.say("**Erreur** | Aucun rôle n'est restaurable pour cet utilisateur.")
            return
        suc = ""
        dom = 0
        for role in server.roles:
            if role.id in data["ROLE_SAVE"]:
                await self.bot.add_roles(user, role)
                suc += "{}\n".format(role.mention if role.mentionable else "***" + role.name + "***")
            else:
                dom += 1
        if suc:
            if dom > 0:
                suc += "\n**{}** *rôles n'ont pu être restaurés*"
            em = discord.Embed(title="{} | Rôles restaurés".format(user.name), description=suc,
                               color=ctx.message.author.color)
            data["ROLE_SAVE"] = []
            em.set_footer(text="Les rôles sauvegardés ont été reinitialisés pour l'utilisateur")
            self.api.add_log(user, "Rôles restaurés par le staff")
            await self.bot.say(embed=em)
        else:
            await self.bot.say("**Impossible** | Aucun rôle n'est restaurable, il est possible qu'ils n'existent plus "
                               "ou que Discord ai changé leurs identifiants.")
        self.smart_save()

    @socmod.command(pass_context=True)
    async def depart(self, ctx, channel: discord.Channel = None):
        """Active/désactive les messages de départ sur un channel défini

        Par défaut sur le channel où est réalisée la commande"""
        server = ctx.message.server
        if server.id not in self.sys:
            self.sys[server.id] = {"DEPART": False}
        if self.sys[server.id]["DEPART"]:
            self.sys[server.id]["DEPART"] = False
            await self.bot.say("**Désactivé** | Vous n'aurez plus de messages de départ")
        else:
            self.sys[server.id]["DEPART"] = channel.id
            await self.bot.say("**Activé** | Les messages de départ seront affichés sur {}".format(channel.mention))
        fileIO("data/social/sys.json", "save", self.sys)

    @socmod.command(pass_context=True)
    async def majmsg(self, ctx, max: int, channel: discord.Channel = None):
        """Recherche et met à jour les dates des premiers messages des membres rétroactivement
        ! Tout message supprimé n'est PAS pris en compte car inaccessible !

        i - Réglez le paramètre 'max' de manière à ce que ça corresponde avec le nombre de messages dans le channel"""
        await self.bot.say("**Recherche démarrée** | Ce processus peut prendre jusqu'à"
                           " plusieures heures en fonction des serveurs et du paramètre `max` défini.")
        if not channel:
            channel = ctx.message.channel
        server = ctx.message.server
        data = {}
        n = 0
        async for msg in self.bot.logs_from(channel, limit=max):
            if n == (0.25 * max):
                await self.bot.say("**Avancement** | Env. 25%")
            if n == (0.50 * max):
                await self.bot.say("**Avancement** | Env. 50%")
            if n == (0.75 * max):
                await self.bot.say("**Avancement** | Env. 75%")
            if n == (0.90 * max):
                await self.bot.say("**Avancement** | Env. 90%")
            n += 1
            ts = msg.timestamp.timestamp()
            user = msg.author
            if user.id not in data:
                data[user.id] = ts
            if data[user.id] > ts: data[user.id] = ts
        for u in self.soc[server.id]:
            if u in data:
                self.soc[server.id][u]["ENRG"] = ts
        self.api.apisave()

    # COMMANDES UTILISATEURS ==========

    @commands.group(name="carte", aliases=["c"], pass_context=True, invoke_without_command=True, no_pm=True)
    async def _carte(self, ctx, membre: discord.Member = None):
        """Ensemble de commandes relatives à la Carte de membre

        En absence de mention, renvoie la carte du membre invocateur"""
        if ctx.invoked_subcommand is None:
            if not membre:
                membre = ctx.message.author
            await ctx.invoke(self.profil, membre=membre)

    @_carte.command(pass_context=True)
    async def profil(self, ctx, membre: discord.Member = None):
        """Affiche la carte de membre de l'utilisateur"""
        formatname = membre.name if membre.display_name == membre.name else "{} «{}»".format(membre.name,
                                                                                             membre.display_name)
        pseudos, surnoms = self.api.namelist(membre)
        today = time.strftime("%d/%m/%Y", time.localtime())
        data = self.api.get(membre)
        em = discord.Embed(title=formatname, description=data["SOC"]["BIO"], color=self.api.color_disp(membre))
        if membre.avatar_url:
            em.set_thumbnail(url=membre.avatar_url)
        em.add_field(name="Données", value="**ID** `{}`\n"
                                           "**Clef** `{}`\n"
                                           "**Solde** `{} crédits`\n"
                                           "`{}`\🔥".format(membre.id, data["CLEF"], data["ECO"]["SOLDE"],
                                                            len(data["SOC"]["FLAMMES"])))
        servnb = self.api.nb_servers(membre)
        timestamp = ctx.message.timestamp
        creation = (timestamp - membre.created_at).days
        datecreation = membre.created_at.strftime("%d/%m/%Y")
        arrive = (timestamp - membre.joined_at).days
        datearrive = membre.joined_at.strftime("%d/%m/%Y")
        origine = datetime.fromtimestamp(data["ENRG"])
        since_origine = (timestamp - origine).days
        strorigine = datetime.strftime(origine, "%d/%m/%Y %H:%M")
        em.add_field(name="Dates", value="**Création:** `{}` (**{}**j)\n"
                                         "**Arrivée:** `{}` (**{}**j)\n"
                                         "**Premier msg:** `{}` (**{}**j)\n"
                                         "**Serveurs:** {}".format(datecreation, creation, datearrive, arrive,
                                                                   strorigine, since_origine, servnb))
        roles = []
        for r in membre.roles:
            if r.name != "@everyone":
                if r.mentionable:
                    roles.append(r.mention)
                else:
                    roles.append("*" + r.name + "*")
        em.add_field(name="Rôles", value="{}".format(", ".join(roles) if roles else "**Aucun**"))
        em.add_field(name="Anciennement", value="**Pseudos:** {}\n**Surnoms:** {}".format(", ".join(
            pseudos[-3:]) if pseudos else "**Aucun**", ", ".join(surnoms[-3:]) if surnoms else "**Aucun**"))
        txt = ""
        if data["LOGS"]:
            b = data["LOGS"][-3:]
            b.reverse()
            for e in b:
                if e[1] == today:
                    txt += "**{}** - {}\n".format(e[0], e[2])
                else:
                    txt += "**{}** - {}\n".format(e[1], e[2])
        else:
            txt = "Aucune action"
        em.add_field(name="Historique local", value=txt)
        if data["SOC"]["VITRINE"]:
            em.set_image(url=data["SOC"]["VITRINE"])
        em.set_footer(
            text="{}{}".format(self.api.grade(membre)[0], " | {}".format(membre.game) if membre.game else ""),
            icon_url=self.api.grade(membre)[1])
        await self.bot.say(embed=em)

    @_carte.command(pass_context=True)
    async def sexe(self, ctx, sexe: str = "neutre"):
        """Permet d'indiquer au bot son sexe, permettant d'adapter certaines fonctionnalités
        Reconnus : n/neutre, f/feminin/femme, m/masculin/homme

        i - Syncronisé entre les serveurs"""
        data = self.api.get(ctx.message.author, "SOC")
        if sexe.lower() in ["neutre", "n"]:
            data["SEXE"] = "neutre"
            self.api.add_log(ctx.message.author, "Sexe modifié pour Neutre")
            await self.bot.say("**Succès** | Vous serez désigné de manière la plus neutre possible")
        elif sexe.lower() in ["femme", "feminin", "f"]:
            data["SEXE"] = "feminin"
            self.api.add_log(ctx.message.author, "Sexe modifié pour Féminin")
            await self.bot.say("**Succès** | Vous serez désignée comme une personne de sexe féminin")
        elif sexe.lower() in ["homme", "masculin", "h"]:
            data["SEXE"] = "masculin"
            self.api.add_log(ctx.message.author, "Sexe modifié pour Masculin")
            await self.bot.say("**Succès** | Vous serez désigné comme une personne de sexe masculin")
        else:
            await self.bot.say(
                "**Inconnu** | Je ne reconnais que 3 sexes: **Neutre**, **Feminin** et **Masculin**.\n"
                "*Veillez à ne pas mettre d'accents !*")
        self.api.sync(ctx.message.author, ctx.message.server, "SOC", "SEXE")
        self.smart_save()

    @_carte.command(pass_context=True)
    async def bio(self, ctx, *texte: str):
        """Modifier sa bio sur sa carte (en-tête)
        Ne pas mettre de texte permet de retirer celui-ci de la carte

        i - Syncronisée entre les serveurs"""
        u = self.api.get(ctx.message.author, "SOC")
        if texte:
            await self.bot.say("**Succès** | Votre bio s'affichera en haut de votre carte de membre.")
        else:
            await self.bot.say("**Succès** | Votre bio n'affichera aucun texte.")
        self.api.add_log(ctx.message.author, "Changement de bio")
        u["BIO"] = " ".join(texte)
        self.api.sync(ctx.message.author, ctx.message.server, "SOC", "BIO")
        self.smart_save()

    @_carte.command(pass_context=True)
    async def image(self, ctx, url: str = None):
        """Modifier sa vitrine
        Ne pas mettre d'URL permet de retirer l'image de la carte

        i - Synchronisée entre les serveurs"""
        u = self.api.get(ctx.message.author, "SOC")
        if url:
            if url.startswith("http"):
                await self.bot.say(
                    "**Succès** | L'image s'affichera en bas de votre carte.\n*Si vous rencontrez un "
                    "problème d'affichage c'est que celle-ci est trop lourde ou le lien est invalide.*")
                u["VITRINE"] = url
            else:
                await self.bot.say("**Erreur** | Cette URL n'est pas valide.")
                return
        else:
            await self.bot.say("**Retirée** | Aucune image ne s'affichera sur votre carte")
            u["VITRINE"] = None
        self.api.add_log(ctx.message.author, "Image vitrine modifiée")
        self.api.sync(ctx.message.author, ctx.message.server, "SOC", "VITRINE")
        self.smart_save()

# TRIGGERS ----------------------------------------------

    async def social_msg(self, message):
        if not hasattr(message, "server"):
            return
        date = time.strftime("%d/%m/%Y", time.localtime())
        hier = time.strftime("%d/%m/%Y",
                             time.localtime(time.mktime(time.strptime(date, "%d/%m/%Y")) - 86400))
        author = message.author
        channel = message.channel
        server = message.server
        p = self.api.get(author)
        p["STATS"]["MSG_TOTAL"] += 1
        p["STATS"]["MSG_CHANS"][channel.id] = p["STATS"]["MSG_CHANS"][channel.id] + 1 if \
            channel.id in p["STATS"]["MSG_CHANS"] else 1
        if hier in p["SOC"]["FLAMMES"]:
            if date not in p["SOC"]["FLAMMES"]:
                p["SOC"]["FLAMMES"].append(date)
        else:
            if date not in p["SOC"]["FLAMMES"]:
                p["SOC"]["FLAMMES"] = [date]
        if ":" in message.content:
            output = re.compile(':(.*?):', re.DOTALL | re.IGNORECASE).findall(message.content)
            if output:
                for i in output:
                    if i in [e.name for e in server.emojis]:
                        p["STATS"]["EMOJIS"][i] = p["STATS"]["EMOJIS"][i] + 1 if i in p["STATS"]["EMOJIS"] else 1
        self.smart_save()

    async def social_msgdel(self, message):
        if not hasattr(message, "server"):
            return
        author = message.author
        p = self.api.get(author)
        p["STATS"]["MSG_SUPPR"] += 1
        self.smart_save()

    async def social_react(self, reaction, author):
        message = reaction.message
        if not hasattr(message, "server"):
            return
        server = message.server
        p = self.api.get(author)
        if type(reaction.emoji) is str:
            name = reaction.emoji
        else:
            name = reaction.emoji.name
        if name in [e.name for e in server.emojis]:
            p["STATS"]["EMOJIS"][name] = p["STATS"]["EMOJIS"][name] + 1 if name in p["STATS"]["EMOJIS"] else 1
        self.smart_save()

    async def social_join(self, user: discord.Member):
        p = self.api.get(user, "STATS")
        server = user.server
        p["JOIN"] += 1
        if p["QUIT"] > 0:
            self.api.add_log(user, "Retour sur le serveur")
        else:
            self.api.add_log(user, "Arrivée sur le serveur")
        self.smart_save()

    async def social_quit(self, user: discord.Member):
        p = self.api.get(user)
        server = user.server
        p["STATS"]["QUIT"] += 1
        save = False
        if len([r.name for r in user.roles if r.name != "@everyone"]) > 0:
            if len(p["SOC"]["ROLE_SAVE"]) < len([r.name for r in user.roles if r.name != "@everyone"]):
                p["SOC"]["ROLE_SAVE"] = [r.name for r in user.roles if r.name != "@everyone"]
                save = True
        self.api.add_log(user, "Quitte le serveur")
        self.smart_save()
        if self.sys[server.id]["DEPART"]:
            msgchannel = self.bot.get_channel(self.sys[server.id]["DEPART"])
            grade, img, nomb = self.api.grade(user)
            quitmsg = random.choice(self.quit_msg).format("<@" + str(user.id) + ">")
            em = discord.Embed(description="👋 {}".format(quitmsg),
                               color=user.color if user.color != discord.Colour.default() else 0x607d8b)
            bip = user.top_role.name if user.top_role.name != "@everyone" else "Aucun rôle"
            em.set_footer(text="{} | {}".format(user.display_name, bip),
                          icon_url=img)
            await self.bot.send_message(msgchannel, embed=em)

    async def social_perso(self, before, after):
        p = self.api.get(after, "STATS")
        if after.name != before.name:
            self.api.add_log(after, "Changement de pseudo pour *{}*".format(after.name))
        if after.display_name != before.display_name:
            if after.display_name == after.name:
                self.api.add_log(after, "Surnom retiré")
            else:
                self.api.add_log(after, "Changement du surnom pour *{}*".format(after.display_name))
        if after.avatar_url != before.avatar_url:
            url = before.avatar_url
            url = url.split("?")[0]  # On retire le reformatage serveur Discord
            self.api.add_log(after, "Changement d'avatar [(?)]({})".format(url))
        if after.top_role != before.top_role:
            if after.top_role > before.top_role:
                self.api.add_log(after, "A reçu le rôle {}".format(after.top_role.name))
            else:
                if after.top_role.name != "@everyone":
                    self.api.add_log(after, "A été rétrogradé {}".format(after.top_role.name))
                else:
                    self.api.add_log(after, "Ne possède plus de rôles")

    async def social_ban(self, user):
        p = self.api.get(user)
        p["STATS"]["QUIT"] += 1
        p["STATS"]["BAN"] += 1
        self.api.add_log(user, "Banni du serveur")
        self.smart_save()


def check_folders():
    if not os.path.exists("data/social"):
        print("Création du dossier SOCIAL...")
        os.makedirs("data/social")


def check_files():
    if not os.path.isfile("data/social/soc.json"):
        print("Création de Social/soc.json")
        dataIO.save_json("data/social/soc.json", {})
    if not os.path.isfile("data/social/sys.json"):
        print("Création de Social/sys.json")
        dataIO.save_json("data/social/sys.json", {})


def setup(bot):
    check_folders()
    check_files()
    n = Social(bot)
    bot.add_listener(n.social_msg, "on_message")
    bot.add_listener(n.social_msgdel, "on_message_delete")
    bot.add_listener(n.social_react, "on_reaction_add")
    bot.add_listener(n.social_join, "on_member_join")
    bot.add_listener(n.social_quit, "on_member_remove")
    bot.add_listener(n.social_perso, "on_member_update")
    bot.add_listener(n.social_ban, "on_member_ban")
    bot.add_cog(n)