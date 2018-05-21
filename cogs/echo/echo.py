import asyncio
import os
import random
import re
import time
from collections import namedtuple
from copy import deepcopy
from urllib import request

import aiohttp
import discord
from __main__ import send_cmd_help
from discord.ext import commands

from .utils import checks
from .utils.dataIO import fileIO, dataIO


class Echo:
    """Stickers et fonctionnalités dédiées aux salons écrits"""
    def __init__(self, bot):
        self.bot = bot
        self.data = dataIO.load_json("data/echo/data.json")
        self.sys = dataIO.load_json("data/echo/sys.json")
        self.cooldown = {}

    def save(self):
        fileIO("data/echo/data.json", "save", self.data)
        fileIO("data/echo/sys.json", "save", self.sys)
        return True

    def _set_server(self, server: discord.Server):
        if server.id not in self.data:
            self.data[server.id] = {}
            self.save()
        if server.id not in self.sys:
            perms = {"AJOUTER": "manage_messages",
                     "SUPPRIMER": "manage_messages",
                     "EDITER": "manage_messages",
                     "UTILISER": None}
            disp = {"IMAGE": "upload",
                    "AUDIO": "upload",
                    "VIDEO": "web"}
            dl = {"IMAGE": True,
                  "AUDIO": True,
                  "VIDEO": False}
            self.sys[server.id] = {"PERMISSIONS_STK": perms, "DISPLAY_STK": disp, "DOWNLOAD_STK": dl,
                                   "BLACKLIST": [], "CORRECT": None}
            self.save()
        if not os.path.exists("data/echo/img/{}".format(server.id)):
            os.makedirs("data/echo/img/{}".format(server.id))
        return True

    def _obj_sticker(self, server: discord.Server, nom: str):
        """Renvoie l'objet Sticker() contenant toutes ses données"""
        self._set_server(server)
        for stk in self.data[server.id]:
            if nom is self.data[server.id][stk]["NOM"]:
                data = self.data[server.id][stk]
                output = re.compile(r"([A-z]+)(\d*)?", re.DOTALL | re.IGNORECASE).findall(nom)[0]
                racine = output[0]
                nb = output[1]
                fichnom = data["URL"].split("/")[-1]
                ext = fichnom.split(".")[1]
                typex = self.get_sticker_type(ext)
                Stats = namedtuple('Stats', ['compte', 'like', 'dislike'])
                stats = Stats(data["STATS"]["COMPTE"], data["STATS"]["LIKE"], data["STATS"]["DISLIKE"])
                Sticker = namedtuple('Sticker', ['id', 'nom', 'path', 'author', 'url', 'creation', 'stats', 'display',
                                                 'racine', 'place', 'type', 'approb'])
                return Sticker(stk, data["NOM"], data["PATH"], data["AUTHOR"], data["URL"], data["CREATION"],
                               stats, data["DISPLAY"], racine, nb, typex, data["APPROB"])
        return False

    def get_sticker(self, server: discord.Server, nom: str, w: bool = False):
        self._set_server(server)
        stk = self._obj_sticker(server, nom)
        if stk:
            if stk.approb:
                return stk if not w else self.data[server.id][stk.id]
        else:
            return False  # TODO : Utiliser levenstein pour retrouver le sticker

    def get_all_stickers(self, server: discord.Server):
        self._set_server(server)
        all = []
        for s in self.data[server.id]:
            if self.data[server.id][s]["APPROB"]:
                all.append(self._obj_sticker(server, self.data[server.id][s]["NOM"]))
        return all

    def add_sticker(self, nom: str, author: discord.Member, url: str, chemin: str = None, replace: bool = False):
        """Ajoute un sticker sur le serveur"""
        server = author.server
        self._set_server(server)
        if not self._obj_sticker(server, nom):
            clef = random.randint(100000, 999999)
            if clef in self.data[server.id]:
                return self.add_sticker(nom, author, url, chemin)
            stats = {"COMPTE": 0,
                     "LIKE": [],
                     "DISLIKE": []}
            fichnom = url.split("/")[-1]
            ext = fichnom.split(".")[1]
            self.data[server.id][clef] = {"NOM": nom,
                                          "PATH": chemin,
                                          "AUTHOR": author.id,
                                          "URL": url,
                                          "CREATION": time.time(),
                                          "STATS": stats,
                                          "DISPLAY": self.get_display(server, self.get_sticker_type(ext)),
                                          "APPROB": self.get_perms(author, "AJOUTER")}
            self.save()
            return True if self.get_perms(author, "AJOUTER") else False
        if replace:
            clef = self.get_sticker(server, nom).id
            stats = {"COMPTE": 0,
                     "LIKE": [],
                     "DISLIKE": []}
            fichnom = url.split("/")[-1]
            ext = fichnom.split(".")[1]
            self.data[server.id][clef] = {"NOM": nom,
                                          "PATH": chemin,
                                          "AUTHOR": author.id,
                                          "URL": url,
                                          "CREATION": time.time(),
                                          "STATS": stats,
                                          "DISPLAY": self.get_display(server, self.get_sticker_type(ext)),
                                          "APPROB": self.get_perms(author, "AJOUTER")}
            self.save()
            return True if self.get_perms(author, "EDITER") else False
        return False

    def approb_sticker(self, user: discord.Member, identifiant: int):
        """Approuver un sticker en attente"""
        server = user.server
        self._set_server(server)
        if identifiant in self.data[server.id]:
            if not self.data[server.id][identifiant]["APPROB"]:
                if self.get_perms(user, "AJOUTER"):
                    self.data[server.id][identifiant]["APPROB"] = True
                    self.save()
                    return True
        return False

    def get_collection(self, server: discord.Server, racine: str):
        """Renvoie une liste d'objets Sticker() des Stickers contenant le nom racine"""
        self._set_server(server)
        collection = []
        for stk in self.data[server.id]:
            if self.data[server.id][stk]["NOM"].startswith(racine):
                collection.append(self._obj_sticker(server, self.data[server.id][stk]["NOM"]))
        return collection

    def find_dispo_in(self, server: discord.Server, racine: str):
        """Trouve un nom disponible dans une Collection"""
        coll = self.get_collection(server, racine)
        if coll:
            n = 1
            f = lambda n: racine + str(n)
            nom = f(n)
            while nom in [stk.nom for stk in coll]:
                n += 1
                nom = f(n)
            return nom
        return False

    def get_sticker_type(self, extension: str):
        """Renvoie le type du sticker en fonction de son extension"""
        ext = extension.lower()
        if ext in ["jpeg", "gif", "jpg", "png"]:
            return "IMAGE"
        elif ext in ["wav", "mp3"]:
            return "AUDIO"
        elif ext in ["mp4", "webm"]:
            return "VIDEO"
        else:
            return "INCONNU"

    def get_display(self, server: discord.Server, type: str):
        """Renvoie l'affichage par défaut d'un type

        TYPE: IMAGE, AUDIO ou VIDEO"""
        if type not in ["IMAGE", "AUDIO", "VIDEO"]:
            return "web"
        self._set_server(server)
        disp = self.sys[server.id]["DISPLAY_STK"][type]
        if type is "AUDIO" and disp is "integre":
            return "upload"
        elif type is "VIDEO" and disp is "integre":
            return "web"
        if disp not in ["web", "upload", "integre"]:
            return "web"
        else:
            return disp

    def get_download_auth(self, server: discord.Server, type: str):
        """Renvoie l'autorisation ou non de télécharger un sticker

        TYPE: IMAGE, AUDIO ou VIDEO"""
        if type not in ["IMAGE", "AUDIO", "VIDEO"]:
            return False
        self._set_server(server)
        return self.sys[server.id]["DOWNLOAD_STK"][type]

    def get_perms(self, user: discord.Member, action: str):
        """Vérifie les permissions de l'utilisateur"""
        server = user.server
        self._set_server(server)
        perm = self.sys[server.id]["PERMISSIONS_STK"][action.upper()]
        if perm == "manage_messages":
            return user.server_permissions.manage_messages
        elif perm == "kick_members":
            return user.server_permissions.kick_members
        elif perm == "ban_members":
            return user.server_permissions.ban_members
        elif perm == "manage_emojis":
            return user.server_permissions.manage_emojis
        elif perm == "administrator":
            return user.server_permissions.administrator
        else:
            return True

    def levenshtein(self, s1, s2):
        if len(s1) < len(s2):
            m = s1
            s1 = s2
            s2 = m
        if len(s2) == 0:
            return len(s1)
        previous_row = range(len(s2) + 1)
        for i, c1 in enumerate(s1):
            current_row = [i + 1]
            for j, c2 in enumerate(s2):
                insertions = previous_row[
                                 j + 1] + 1
                deletions = current_row[j] + 1
                substitutions = previous_row[j] + (c1 != c2)
                current_row.append(min(insertions, deletions, substitutions))
            previous_row = current_row
        return previous_row[-1]

    def similarite(self, mot, liste, tolerance=3):
        prochenb = tolerance
        prochenom = None
        for i in liste:
            if self.levenshtein(i, mot) < prochenb:
                prochenom = i
                prochenb = self.levenshtein(i, mot)
        else:
            return prochenom

# ---------- COMMANDES ---------------

    @commands.group(name="stk", pass_context=True, no_pm=True)
    async def _stk(self, ctx):
        """Gestion des Stickers"""
        if ctx.invoked_subcommand is None:
            await send_cmd_help(ctx)

    def get_size(self, start_path):
        total_size = 0
        for dirpath, dirnames, filenames in os.walk(start_path):
            for f in filenames:
                fp = os.path.join(dirpath, f)
                total_size += os.path.getsize(fp)
        return int(total_size)

    @_stk.command(aliases=["new"], pass_context=True)
    async def add(self, ctx, nom, url=None):
        """Ajouter un Sticker (Image, audio ou vidéo)
        Supporté : jpeg, jpg, png, gif, mp3, wav, mp4

        <nom> = Nom du sticker à ajouter
        [url] = Facultatif, URL du fichier si provenant d'Internet
        -- Il est possible de directement importer l'image à ajouter sur Discord"""
        author = ctx.message.author
        server = ctx.message.server
        storage = "data/echo/img/{}/".format(server.id)
        output = re.compile(r"([A-z]+)(\d*)?", re.DOTALL | re.IGNORECASE).findall(nom)[0]
        racine = output[0]
        nb = output[1]
        poids = self.get_size(storage)
        replace = False
        self._set_server(server)
        if self.get_sticker(server, nom):
            if nom == racine:
                prefix = self.bot.settings.get_prefixes(server)[0]
                new_message = deepcopy(ctx.message)
                newname = self.find_dispo_in(server, racine)
                command = "stk add {}{}".format(newname, " {}".format(url) if url else "")
                new_message.content = prefix + command
                await self.bot.process_commands(new_message)
                return
            else:
                em = discord.Embed(description="**{}** existe déjà. Que voulez-vous faire ?\n\n"
                                               "❎ ─ Annuler\n"
                                               "♻ ─ Remplacer le sticker existant\n"
                                               "❇ ─ Intégrer à la collection `{}`".format(nom, racine))
                em.set_footer(text="Choisissez l'action à réaliser avec les réactions ci-dessous")
                msg = await self.bot.say(embed=em)
                await self.bot.add_reaction(msg, "❎")
                await self.bot.add_reaction(msg, "♻")
                await self.bot.add_reaction(msg, "❇")
                await asyncio.sleep(0.25)

                def check(reaction, user):
                    return not user.bot

                rep = await self.bot.wait_for_reaction(["❎", "♻", "❇"], message=msg, timeout=30,
                                                       check=check, user=ctx.message.author)
                if rep is None or rep.reaction.emoji == "❎":
                    await self.bot.say(
                        "**Annulé** ─ Vous pourrez toujours l'ajouter un plus tard avec `{}stk add` ".format(
                            ctx.prefix))
                    await self.bot.delete_message(msg)
                    return False
                elif rep.reaction.emoji == "♻":
                    replace = True
                    await self.bot.delete_message(msg)
                elif rep.reaction.emoji == "❇":
                    await self.bot.delete_message(msg)
                    prefix = self.bot.settings.get_prefixes(server)[0]
                    new_message = deepcopy(ctx.message)
                    newname = self.find_dispo_in(server, racine)
                    command = "stk add {}{}".format(newname, " {}".format(url) if url else "")
                    new_message.content = prefix + command
                    await self.bot.process_commands(new_message)
                    return
                else:
                    await self.bot.say("**Erreur** | Désolé je n'ai pas compris...")
                    return False

        if not url:
            attach = ctx.message.attachments
            if len(attach) > 1:
                await self.bot.say("**Erreur** | Vous ne pouvez ajouter qu'un seul fichier à la fois.")
                return
            if attach:
                a = attach[0]
                url = a["url"]
                filename = a["filename"]
            else:
                await self.bot.say("**Erreur** | Ce fichier n'est pas pris en charge.")
                return
            fichnom = url.split("/")[-1]
            ext = fichnom.split(".")[1]
            type = self.get_sticker_type(ext)
            dl = self.get_download_auth(server, type)
            if dl:
                if poids > 500000000:
                    await self.bot.say("**+500 MB** | L'espace alloué à ce serveur est plein. "
                                       "Veuillez faire de la place en supprimant quelques stickers enregistrés.")
                    return
                filepath = os.path.join(storage, filename)

                async with aiohttp.get(url) as new:
                    f = open(filepath, "wb")
                    f.write(await new.read())
                    f.close()
                done = self.add_sticker(nom, author, url, chemin=filepath, replace=replace)
                if done is None:
                    await self.bot.say("**Erreur** | Une erreur à eu lieue en essayant d'ajouter ce sticker.")
                elif done is False:
                    await self.bot.say("**En attente d'approbation** | Un membre habilité pourra "
                                       "approuver ce sticker avec `{}stk approb {}`".format(ctx.prefix, nom))
                else:
                    await self.bot.say("**Ajouté** | Votre sticker est disponible avec `:{}:`".format(nom))
            else:
                done = self.add_sticker(nom, author, url, replace=replace)
                if done is None:
                    await self.bot.say("**Erreur** | Une erreur à eu lieue en essayant d'ajouter ce sticker.")
                elif done is False:
                    await self.bot.say("**En attente d'approbation** | Un membre habilité pourra "
                                       "approuver ce sticker avec `{}stk approb {}`".format(ctx.prefix, nom))
                else:
                    await self.bot.say("**Ajouté** | Votre sticker est disponible avec `:{}:`".format(nom))
        else:
            fichnom = url.split("/")[-1]
            ext = fichnom.split(".")[1]
            type = self.get_sticker_type(ext)
            dl = self.get_download_auth(server, type)
            if ext in ["jpg", "jpeg", "png", "gif", "wav", "mp3", "mp4", "webm"]:
                if dl:
                    if poids > 500000000:
                        await self.bot.say("**+500 MB** | L'espace alloué à ce serveur est plein. "
                                           "Veuillez faire de la place en supprimant quelques stickers enregistrés.")
                        return
                    filename = url.split('/')[-1]
                    if filename in os.listdir(storage):
                        exten = filename.split(".")[1]
                        nomsup = random.randint(1, 999999)
                        filename = filename.split(".")[0] + str(nomsup) + "." + exten
                    try:
                        f = open(filename, 'wb')
                        f.write(request.urlopen(url).read())
                        f.close()
                        file = storage + filename
                        os.rename(filename, file)
                        done = self.add_sticker(nom, author, url, chemin=file, replace=replace)
                        if done is None:
                            await self.bot.say("**Erreur** | Une erreur à eu lieue en essayant d'ajouter ce sticker.")
                        elif done is False:
                            await self.bot.say("**En attente d'approbation** | Un membre habilité pourra "
                                               "approuver ce sticker avec `{}stk approb {}`".format(ctx.prefix, nom))
                        else:
                            await self.bot.say("**Ajouté** | Votre sticker est disponible avec `:{}:`".format(nom))
                    except Exception as e:
                        print("Impossible de télécharger le fichier : {}".format(e))
                        await self.bot.say(
                            "**Erreur** | Impossible de télécharger le fichier. Essayez de changer l'hébergeur")
                else:
                    done = self.add_sticker(nom, author, url, replace=replace)
                    if done is None:
                        await self.bot.say("**Erreur** | Une erreur à eu lieue en essayant d'ajouter ce sticker.")
                    elif done is False:
                        await self.bot.say("**En attente d'approbation** | Un membre habilité pourra "
                                           "approuver ce sticker avec `{}stk approb {}`".format(ctx.prefix, nom))
                    else:
                        await self.bot.say("**Ajouté** | Votre sticker est disponible avec `:{}:`".format(nom))
            else:
                await self.bot.say("**Erreur** | Ce format n'est pas supporté.")

    @_stk.command(pass_context=True)
    async def delete(self, ctx, nom: str):
        """Supprimer un sticker"""
        author = ctx.message.author
        server = ctx.message.server
        self._set_server(server)
        if self.get_perms(author, "SUPPRIMER"):
            stk = self.get_sticker(server, nom)
            if stk:
                txt = ""
                if stk.path:
                    file = stk.path.split('/')[-1]
                    splitted = "/".join(stk.path.split('/')[:-1]) + "/"
                    if file in os.listdir(splitted):
                        try:
                            os.remove(stk.path)
                            txt = "─ Fichier local supprimé\n"
                        except:
                            pass
                del self.data[server.id][stk.id]
                self.save()
                txt = "─ Données supprimées"
                em = discord.Embed(title="Suppression de {}".format(nom), description=txt)
                em.set_footer(text="Sticker supprimé avec succès")
                await self.bot.say(embed=em)
            else:
                await self.bot.say("**Erreur** | Ce sticker n'existe pas")
        else:
            await self.bot.say("**Impossible** | Vous n'avez pas l'autorisation de faire cette action")

    def valid_url(self, url: str):
        fichnom = url.split("/")[-1]
        ext = fichnom.split(".")[1]
        if ext in ["jpg", "jpeg", "png", "gif", "wav", "mp3", "mp4", "webm"]:
            return True
        return False

    @_stk.command(pass_context=True)
    async def edit(self, ctx, nom: str):
        """Editer un sticker"""
        author = ctx.message.author
        server = ctx.message.server
        storage = "data/echo/img/{}/".format(server.id)
        self._set_server(server)
        if self.get_perms(author, "EDITER"):
            stk = self.get_sticker(server, nom, w=True)
            if stk:
                while True:
                    infos = self.get_sticker(server, nom)
                    if infos.path:
                        poids = int(os.path.getsize(infos.path)) / 100
                    txt = "\🇦 ─ Nom: `{}`\n".format(infos.nom)
                    txt += "\🇧 ─ URL: `{}`\n".format(infos.url)
                    txt += "\🇨 ─ Affichage: `{}`\n".format(infos.display)
                    txt += "\🇩 ─ Téléchargé: `{}`{}\n".format(
                        True if infos.path else False, "" if not infos.path else " ({} KB)".format(poids))
                    em = discord.Embed(title="Modifier {}".format(infos.id), description=txt, color=author.color)
                    em.set_image(url=infos.url)
                    em.set_footer(text="Cliquez sur la réaction correspondante à l'action désirée | ❌ = Quitter")
                    msg = await self.bot.say(embed=em)
                    await self.bot.add_reaction(msg, "🇦")
                    await self.bot.add_reaction(msg, "🇧")
                    await self.bot.add_reaction(msg, "🇨")
                    await self.bot.add_reaction(msg, "🇩")
                    await self.bot.add_reaction(msg, "❌")
                    await asyncio.sleep(0.25)

                    def check(reaction, user):
                        return not user.bot

                    rep = await self.bot.wait_for_reaction(["🇦", "🇧", "🇨", "🇩", "❌"], message=msg, timeout=30,
                                                           check=check, user=ctx.message.author)
                    if rep is None or rep.reaction.emoji == "❌":
                        await self.bot.delete_message(msg)
                        return
                    elif rep.reaction.emoji == "🇦":
                        await self.bot.delete_message(msg)
                        txt = "**Quel nom voulez-vous lui attribuer ?**"
                        em = discord.Embed(title="Modifier le nom", description=txt, color=author.color)
                        em.set_footer(text="Le nom ne doit pas comporter d'espaces")
                        m = await self.bot.say(embed=em)
                        valid = False
                        while valid is False:
                            rep = await self.bot.wait_for_message(channel=ctx.message.channel,
                                                                  author=ctx.message.author,
                                                                  timeout=60)
                            if rep is None:
                                await self.bot.delete_message(m)
                                return
                            elif not self.get_sticker(server, rep.content):
                                self.data[server.id][infos.id]["NOM"] = rep.content
                                self.save()
                                await self.bot.say("**Succès** | Le nom du sticker a été modifié.")
                                valid = True
                            else:
                                await self.bot.say("**Impossible** | Ce nom existe déjà. Retour au menu...")
                                valid = True
                    elif rep.reaction.emoji == "🇧":
                        await self.bot.delete_message(msg)
                        txt = "**Entrez le nouvel URL du fichier**"
                        em = discord.Embed(title="Modifier l'URL", description=txt, color=author.color)
                        em.set_footer(text="L'URL doit se terminer par l'extension (png, gif, mp3...)")
                        m = await self.bot.say(embed=em)
                        valid = False
                        while valid is False:
                            rep = await self.bot.wait_for_message(channel=ctx.message.channel,
                                                                  author=ctx.message.author,
                                                                  timeout=60)
                            if rep is None:
                                await self.bot.delete_message(m)
                                return
                            elif self.valid_url(rep.content):
                                self.data[server.id][infos.id]["URL"] = rep.content
                                self.save()
                                await self.bot.say("**Succès** | L'URL a été modifié.")
                                valid = True
                            else:
                                await self.bot.say("**Erreur** | L'URL ne semble pas valable.")
                                valid = True
                    elif rep.reaction.emoji == "🇨":
                        if infos.type == "IMAGE":
                            dispo = ["web", "upload", "integre"]
                        elif infos.type == "VIDEO":
                            dispo = ["web", "upload"]
                        elif infos.type == "AUDIO":
                            dispo = ["web", "upload"]
                        else:
                            dispo = ["web"]
                        await self.bot.delete_message(msg)
                        txt = "**Quel affichage doit être privilégié pour ce sticker ?**\n\n"
                        if "web" in dispo:
                            txt += "`WEB` ─ Poste le lien lors de l'invocation\n"
                        if "upload" in dispo:
                            txt += "`UPLOAD` ─ Télécharge directement sur Discord le sticker\n"
                        if "integre" in dispo:
                            txt += "`INTEGRE` ─ Affiche le sticker dans un format similaire à cette interface"
                        em = discord.Embed(title="Modifier l'URL", description=txt, color=author.color)
                        em.set_footer(text="Entrez le nom de l'affichage ci-dessous")
                        m = await self.bot.say(embed=em)
                        valid = False
                        while valid is False:
                            rep = await self.bot.wait_for_message(channel=ctx.message.channel,
                                                                  author=ctx.message.author,
                                                                  timeout=60)
                            if rep is None:
                                await self.bot.delete_message(m)
                                return
                            elif rep.content.lower() in dispo:
                                self.data[server.id][infos.id]["DISPLAY"] = rep.content.lower()
                                self.save()
                                await self.bot.say("**Succès** | L'affichage a été changé.")
                                valid = True
                            else:
                                await self.bot.say("**Erreur** | Je ne connais pas ce type d'affichage.")
                                valid = True
                    elif rep.reaction.emoji == "🇩":
                        await self.bot.delete_message(msg)
                        txt = "**Dois-je posséder un exemplaire du Sticker en local ? (Oui/Non)**"
                        em = discord.Embed(title="Modifier l'URL", description=txt, color=author.color)
                        em.set_footer(text="L'autoriser permet de rendre le sticker disponible même si l'URL tombe en "
                                           "désuétude, mais prend de la place sur le stockage alloué à votre serveur.")
                        m = await self.bot.say(embed=em)
                        valid = False
                        while valid is False:
                            rep = await self.bot.wait_for_message(channel=ctx.message.channel,
                                                                  author=ctx.message.author,
                                                                  timeout=60)
                            if rep is None or rep.content.lower() == "non":
                                await self.bot.delete_message(m)
                                if infos.path:
                                    try:
                                        os.remove(infos.path)
                                        await self.bot.say("**Effacé** | Le fichier local du sticker à été supprimé")
                                    except:
                                        await self.bot.sat("**Erreur** | "
                                                           "Je n'ai pas réussi à effacer le fichier local du sticker")
                                else:
                                    await self.bot.say("**Inutile** | Aucun"
                                                       " fichier de ce sticker n'est présent localement")
                                valid = True
                            elif rep.content.lower() == "oui":
                                if infos.path:
                                    await self.bot.say("**Inutile** | Le sticker est déjà stocké en local.")
                                    valid = True
                                    continue
                                url = infos.url
                                filename = url.split('/')[-1]
                                await self.bot.say("**Téléchargement** | Le téléchargement du fichier est en cours...")
                                if filename in os.listdir(storage):
                                    exten = filename.split(".")[1]
                                    nomsup = random.randint(1, 999999)
                                    filename = filename.split(".")[0] + str(nomsup) + "." + exten
                                try:
                                    f = open(filename, 'wb')
                                    f.write(request.urlopen(url).read())
                                    f.close()
                                    file = storage + filename
                                    os.rename(filename, file)
                                    self.data[server.id][infos.id]["PATH"] = file
                                    self.save()
                                    await self.bot.say("**Succès** | Le sticker est stocké en local.")
                                    valid = True
                                except:
                                    await self.bot.say("**Echec** | Impossible de télécharger l'image.\n"
                                                       "Essayez de changer d'hébergeur et réessayez.")
                                    valid = True
                            else:
                                await self.bot.say("**Erreur** | Cette réponse n'est pas valable.")
                                valid = True
                    else:
                        await self.bot.say("**Erreur** | Désolé je n'ai pas compris...")
            else:
                await self.bot.say("**Erreur** | Ce sticker n'existe pas")
        else:
            await self.bot.say("**Impossible** | Vous n'avez pas les permissions de faire cette action")

    @_stk.command(aliases=["apb"], pass_context=True)
    async def approb(self, ctx, nom: str= None):
        """Approuver un sticker proposé par un membre du serveur"""
        author = ctx.message.author
        server = ctx.message.server
        self._set_server(server)
        if nom:
            if self.get_perms(author, "AJOUTER"):
                stk = self.get_sticker(server, nom, w=True)
                sid = self.get_sticker(server, nom).id
                if stk:
                    em = discord.Embed(title="{}, proposé par {}".format(
                        stk["NOM"], server.get_member(stk["AUTHOR"]).name),
                        color=server.get_member(stk["AUTHOR"]).color)
                    em.set_image(url=stk["URL"])
                    em.set_footer(text="✔ = Approuver | ✖ = Refuser")
                    msg = await self.bot.say(embed=em)
                    await self.bot.add_reaction(msg, "✔")
                    await self.bot.add_reaction(msg, "✖")
                    await asyncio.sleep(0.25)

                    def check(reaction, user):
                        return not user.bot

                    rep = await self.bot.wait_for_reaction(["✔", "✖"], message=msg, timeout=40,
                                                           check=check, user=ctx.message.author)
                    if rep is None:
                        await self.bot.say(
                            "**Annulé** ─ La session a expiré !".format(
                                ctx.prefix))
                        await self.bot.delete_message(msg)
                        return
                    elif rep.reaction.emoji == "✔":
                        await self.bot.delete_message(msg)
                        stk["APPROB"] = True
                        self.save()
                        await self.bot.say("**Approuvé** | Le sticker est disponible avec `:{}:`".format(nom))
                    elif rep.reaction.emoji == "✖":
                        await self.bot.delete_message(msg)
                        del self.data[server.id][sid]
                        self.save()
                        await self.bot.say("**Refusé** | La proposition à été supprimée")
                    else:
                        await self.bot.say("**Erreur** | Désolé je n'ai pas compris...")
                        return False
                else:
                    await self.bot.say("**Erreur** | Ce sticker n'existe pas")
            else:
                await self.bot.say("**Impossible** | Vous n'avez pas la permission de réaliser cette action")
        else:
            txt = "\n".join([s.nom for s in self.get_all_stickers(server) if s.approb is False])
            em = discord.Embed(title="Sticker en attente d'approbation", description=txt, color=author.color)
            em.set_footer(text="Approuvez un sticker avec {}stk approb <nom>".format(ctx.prefix))
            await self.bot.say(embed=em)

# ---------- OPTIONS ------------

    @commands.group(name="stkmod", pass_context=True, no_pm=True)
    @checks.admin_or_permissions(manage_messages=True)
    async def _stkmod(self, ctx):
        """Paramètres serveur du module Stickers"""
        if ctx.invoked_subcommand is None:
            await send_cmd_help(ctx)

    @_stkmod.command(pass_context=True)
    async def perms(self, ctx, permission: str, valeur: str):
        """Permet de modifier la valeur des permissions

        -- Permissions:
        AJOUTER
        SUPPRIMER
        EDITER
        UTILISER

        -- Valeurs:
        manage_messages (Gérer les messages)
        kick_members (Kicker des membres)
        ban_members (Bannir des membres)
        manage_emojis (Gérer les emojis)
        administrator (Être administrateur)
        none (Aucune permission particulière)"""
        server = ctx.message.server
        self._set_server(server)
        if permission.upper() in ["AJOUTER", "SUPPRIMER", "EDITER", "UTILISER"]:
            if valeur.lower() in ["manage_messages", "kick_members", "ban_members",
                                  "manage_emojis", "administrator", "none"]:
                self.sys[server.id]["PERMISSIONS_STK"][permission.upper()] = valeur.lower()
                self.save()
                await self.bot.say("**Succès** | {} un sticker nécessitera désormais la permission `{}`".format(
                    permission.capitalize(), valeur.lower()))
            else:
                txt = ""
                for e in ["manage_messages", "kick_members", "ban_members",
                                  "manage_emojis", "administrator", "none"]:
                    txt += "`{}\n".format(e)
                await self.bot.say("__**Valeurs disponibles**__\n" + txt)
        else:
            await self.bot.say("__**Permissions à accorder**__\n"
                               "`AJOUTER`\n`SUPPRIMER`\n`EDITER`\n`UTILISER`")

    @_stkmod.command(pass_context=True)
    async def affichage(self, ctx, categorie: str, valeur: str):
        """Changer l'affichage par défaut d'un type de sticker

        -- Catégories:
        IMAGE
        AUDIO
        VIDEO

        -- Valeurs:
        web (Afficher l'URL)
        upload (Télécharger sur Discord)
        integre (Afficher en billet, disponible qu'avec IMAGE)"""
        server = ctx.message.server
        self._set_server(server)
        if categorie.upper() in ["IMAGE", "AUDIO", "VIDEO"]:
            if valeur.lower() in ["web", "upload", "integre"]:
                if categorie.upper() in ["AUDIO", "VIDEO"] and valeur.lower() == "integre":
                    await self.bot.say("**Erreur** | L'affichage intégré n'est disponible qu'avec les **images**.")
                    return
                self.sys[server.id]["DISPLAY_STK"][categorie.upper()] = valeur.lower()
                self.save()
                await self.bot.say("**Succès** | Les fichiers {} s'afficheront par défaut en format `{}`".format(
                    categorie.lower(), valeur.lower()))
            else:
                await self.bot.say("**__Valeurs disponibles__**\n"
                                   "`web` = Afficher l'URL\n"
                                   "`upload` = Télécharger le sticker sur Discord\n"
                                   "`integre` = Afficher le sticker en billet (IMAGE seulement)")
        else:
            await self.bot.say("__**Catégories**__\n"
                               "`AUDIO`, `IMAGE` ou `VIDEO`")

    @_stkmod.command(pass_context=True)
    async def download(self, ctx, categorie: str, valeur: bool):
        """Autoriser ou non à télécharger par défaut un sticker dans une catégorie

        -- Catégories:
        IMAGE
        AUDIO
        VIDEO

        -- Valeurs:
        True (Autoriser)
        False (Refuser)"""
        server = ctx.message.server
        self._set_server(server)
        if categorie.upper() in ["IMAGE", "AUDIO", "VIDEO"]:
            if type(valeur) is bool:
                self.sys[server.id]["DOWNLOAD_STK"][categorie.upper()] = valeur
                self.save()
                if valeur:
                    await self.bot.say("**Succès** | Les fichiers {} seront téléchargés "
                                       "(si le stockage le permet)".format(categorie.lower()))
                else:
                    await self.bot.say("**Succès** | Les fichiers {} ne seront pas téléchargés".format(
                        categorie.lower()))
            else:
                await self.bot.say("**__Valeurs disponibles__**\n"
                                   "`True` = Autoriser à telécharger par défaut tout les stickers de cette catégorie\n"
                                   "`False` = Refuser de télécharger le sticker, même si le stockage le permet")
        else:
            await self.bot.say("__**Catégories**__\n"
                               "`AUDIO`, `IMAGE` ou `VIDEO`")

    @_stkmod.command(pass_context=True)
    async def blacklist(self, ctx, user: discord.Member):
        """Interdit ou autorise un utilisateur d'utiliser les stickers"""
        server = ctx.message.server
        self._set_server(server)
        if user.id not in self.sys[server.id]["BLACKLIST"]:
            self.sys[server.id]["BLACKLIST"].append(user.id)
            self.save()
            await self.bot.say("**Ajouté** | Ce moment ne pourra plus utiliser de stickers")
        else:
            self.sys[server.id]["BLACKLIST"].remove(user.id)
            self.save()
            await self.bot.say("**Retiré** | Le membre peut de nouveau utiliser les stickers")

    @_stkmod.command(pass_context=True)
    async def correct(self, ctx, niveau: int):
        """Active ou désactive la correction automatique du nom des Stickers

        Niveaux:
        0 = Désactivé (défaut)
        1 = Correction faible
        2 = Correction forte
        3 = Correction exagérée"""
        server = ctx.message.server
        self._set_server(server)
        if 0 <= niveau <= 3:
            self.sys[server.id]["CORRECT"] = niveau if niveau > 0 else None
            self.save()
            await self.bot.say("**Correction automatique changée avec succès**")
        else:
            await self.bot.say("**Erreur** | La valeur doit être comprise entre 0 et 3 "
                               "(Voir `{}help stkmod correct`)".format(ctx.prefix))

    @_stkmod.command(pass_context=True)
    async def taille(self, ctx):
        """Renvoie la taille du fichier de stockage des stickers de votre serveur en MB

        Taille maximale allouée"""
        result = self.get_size("data/echo/img/{}/".format(ctx.message.server.id))
        await self.bot.say("**Taille du fichier** ─ {} MB\n"
                           "**Taille maximale autorisée** ─ 500 MB\n".format(result / 100000))

# ---------- ASYNC -------------

    async def read(self, message):
        author = message.author
        content = message.content
        server = message.server
        channel = message.channel
        self._set_server(server)
        if author.id not in self.sys[server.id]["BLACKLIST"]:
            if ":" in content:
                stickers = re.compile(r'([\w?]+)?:(.*?):', re.DOTALL | re.IGNORECASE).findall(message.content)
                if stickers:
                    for e in stickers:

                        # Système anti-flood
                        heure = time.strftime("%H:%M", time.localtime())
                        if heure not in self.cooldown:
                            self.cooldown = {heure: []}
                        self.cooldown[heure].append(author.id)
                        if self.cooldown[heure].count(author.id) > 3:
                            return

                        if e[1] not in self.get_all_stickers(server):
                            if self.sys[server.id]["CORRECT"]:
                                liste = []
                                for s in self.get_all_stickers(server):
                                    liste.append(s.nom)
                                found = self.similarite(e[1], liste, self.sys[server.id]["CORRECT"])
                                output = re.compile(r"([A-z]+)(\d*)?", re.DOTALL | re.IGNORECASE).findall(found)[0]
                                racine = output[0]
                                e = [e[0], self.get_sticker(server, racine).nom]
                                # On préfère la racine pour éviter d'envoyer des stickers random

                        if e[1] in self.get_all_stickers(server):
                            stk = self.get_sticker(server, e[1])
                            affichage = stk.display

                            # Gestion des options
                            option = e[0] if e[0] else None
                            output = re.compile(r"([A-z]+)(\d*)?", re.DOTALL | re.IGNORECASE).findall(stk.nom)[0]
                            racine = output[0]
                            if option == "r":
                                stk = self.get_sticker(server, racine)
                                if not stk:
                                    return
                            elif option == "c":
                                col = self.get_collection(server, racine)
                                if not col:
                                    return
                                liste = [e.nom for e in col]
                                liste.sort()
                                txt = ""
                                for e in liste:
                                    txt += "`{}`\n".format(e)
                                em = discord.Embed(title="Collection '{}'".format(racine), description=txt,
                                                   color=author.color)
                                em.set_footer(text="Composée de {} stickers au total".format(len(liste)))
                                await self.bot.send_message(author, embed=em)
                                return
                            elif option == "?":
                                col = self.get_collection(server, racine)
                                if not col:
                                    return
                                liste = [e.nom for e in col]
                                r = random.choice(liste)
                                stk = self.get_sticker(server, r)
                                if not stk:
                                    return
                            elif option == "w":
                                affichage = "web"
                            elif option == "u":
                                affichage = "upload"
                            elif option == "i":
                                if stk.type == "IMAGE":
                                    affichage = "integre"
                            elif option == "d":
                                txt = "**ID** ─ `{}`\n" \
                                      "**Type** ─ `{}`\n" \
                                      "**Affichage** ─ `{}`\n" \
                                      "**URL** ─ `{}`\n" \
                                      "**Emplacement** ─ `{}`\n".format(stk.id, stk.type, stk.display, stk.url,
                                                                        stk.path)
                                em = discord.Embed(title="{}".format(stk.nom), description=txt, color= author.color)
                                em.set_footer(text="Proposé par {}".format(server.get_member(stk.author).name))
                                await self.bot.send_message(author, embed=em)
                                return
                            elif option == "f":
                                await self.bot.delete_message(message)
                            elif option == "n":
                                return
                            elif option == "p":
                                await self.bot.send_message(author, stk.url)
                                return
                            elif option == "s":
                                await self.bot.send_message(author, "**Coming soon**")
                                return
                            elif option == "+":
                                await self.bot.send_message(author, "**Bientôt supporté**")
                                return
                            elif option == "-":
                                await self.bot.send_message(author, "**Bientôt supporté**")
                                return
                            else:
                                pass

                            # Publication du sticker
                            await self.bot.send_typing(channel)
                            if affichage == "integre":
                                if stk.type == "IMAGE":
                                    em = discord.Embed(color=author.color)
                                    em.set_image(url=stk.url)
                                    try:
                                        await self.bot.send_message(channel, embed=em)
                                        return
                                    except Exception as e:
                                        print("Impossible d'afficher {} en billet : {}".format(stk.nom, e))
                            elif affichage == "upload":
                                if stk.path:
                                    try:
                                        await self.bot.send_file(channel, stk.path)
                                        return
                                    except Exception as e:
                                        print("Impossible d'afficher {} en upload : {}".format(stk.nom, e))
                            try:
                                await self.bot.send_message(channel, stk.urk)
                            except Exception as e:
                                print("Impossible d'afficher {} en URL : {}".format(stk.nom, e))

                        elif e[1] in ["liste", "list"]:
                            liste = [e.nom for e in self.get_all_stickers(server)]
                            txt = ""
                            liste.sort()
                            n = 1
                            for e in liste:
                                txt += "`{}`\n".format(e)
                                if len(txt) > 1980 * n:
                                    em = discord.Embed(title="Liste des stickers {}".format(server.name),
                                                       description=txt,
                                                       color=author.color)
                                    em.set_footer(text="─ Page {}".format(n))
                                    await self.bot.send_message(author, embed=em)
                                    n += 1
                                    txt = ""
                            em = discord.Embed(title="Liste des stickers {}".format(server.name),
                                               description=txt,
                                               color=author.color)
                            em.set_footer(text="─ Page {}".format(n))
                            await self.bot.send_message(author, embed=em)
                            return
                        elif e[1] == "vent":
                            await asyncio.sleep(0.10)
                            await self.bot.send_typing(channel)
                            return
                        else:
                            pass


def check_folders():
    if not os.path.exists("data/echo"):
        print("Création du dossier Echo...")
        os.makedirs("data/echo")
    if not os.path.exists("data/echo/img"):
        print("Création du dossier d'Images Echo...")
        os.makedirs("data/echo/img")


def check_files():
    if not os.path.isfile("data/echo/data.json"):
        print("Création du fichier Echo/data.json...")
        fileIO("data/echo/data.json", "save", {})
    if not os.path.isfile("data/echo/sys.json"):
        print("Création du fichier Echo/sys.json...")
        fileIO("data/echo/sys.json", "save", {})


def setup(bot):
    check_folders()
    check_files()
    n = Echo(bot)
    bot.add_cog(n)
    bot.add_listener(n.read, "on_message")