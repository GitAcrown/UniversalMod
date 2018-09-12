import asyncio
import os
from .utils import checks
import discord
from collections import namedtuple
from __main__ import send_cmd_help
from discord.ext import commands
import time
import operator
import random
from .utils.dataIO import fileIO, dataIO


class Pendu:
    """Jeu du pendu (Compatible Iota Pay)"""
    def __init__(self, bot):
        self.bot = bot
        self.data = dataIO.load_json("data/pendu/data.json")
        self.session = {}
        self.themes = ["beta"]

    def save(self):
        fileIO("data/pendu/data.json", "save", self.data)
        return True

    def bottomtext(self, status: str):
        if status.lower() == "good":
            return random.choice(["Exact", "Bien joué", "Excellent", "Absolument", "Correct"])
        elif status.lower() == "bad":
            return random.choice(["Loupé", "Dommage", "Incorrect", "Nope", "C'est pas ça"])
        else:
            return random.choice(["Désolé", "Invalide", "Oups...", "Pardon ?"])

    def get_base(self, server: discord.Server):
        """Charge les listes d'origine"""
        mots = {"beta": ['ANGLE', 'ARMOIRE', 'BANC', 'BUREAU', 'CABINET', 'CARREAU', 'CHAISE', 'CLASSE', 'CLEF',
                          'COIN', 'COULOIR', 'DOSSIER', 'EAU', 'ECOLE', 'ENTRER', 'ESCALIER', 'ETAGERE', 'EXTERIEUR',
                          'FENETRE', 'INTERIEUR', 'LAVABO', 'LIT', 'MARCHE', 'MATELAS', 'MATERNELLE', 'MEUBLE',
                          'MOUSSE', 'MUR', 'PELUCHE', 'PLACARD', 'PLAFOND', 'PORTE', 'POUBELLE', 'RADIATEUR', 'RAMPE',
                          'RIDEAU', 'ROBINET', 'SALLE', 'SALON', 'SERRURE', 'SERVIETTE', 'SIEGE', 'SIESTE', 'SILENCE',
                          'SOL', 'SOMMEIL', 'SONNETTE', 'SORTIE', 'TABLE', 'TABLEAU', 'TABOURET', 'TAPIS', 'TIROIR',
                          'TOILETTE', 'VITRE', 'ALLER', 'AMENER', 'APPORTER', 'APPUYER', 'ATTENDRE', 'BAILLER',
                          'COUCHER', 'DORMIR', 'ECLAIRER', 'EMMENER', 'EMPORTER', 'ENTRER', 'FERMER', 'FRAPPER',
                          'INSTALLER', 'LEVER', 'OUVRIR', 'PRESSER', 'RECHAUFFER', 'RESTER', 'SONNER', 'SORTIR',
                          'VENIR', 'ABSENT', 'ASSIS', 'BAS', 'HAUT', 'PRESENT', 'GAUCHE', 'DROITE', 'DEBOUT',
                          'DEDANS', 'DEHORS', 'FACE', 'LOIN', 'PRES', 'TARD', 'TOT', 'APRES', 'AVANT', 'CONTRE',
                          'DANS', 'DE', 'DERRIERE', 'DEVANT', 'DU', 'SOUS', 'SUR', 'CRAYON', 'STYLO', 'FEUTRE',
                          'MINE', 'GOMME', 'DESSIN', 'COLORIAGE', 'RAYURE', 'PEINTURE', 'PINCEAU', 'COULEUR',
                          'CRAIE', 'PAPIER', 'FEUILLE', 'CAHIER', 'CARNET', 'CARTON', 'CISEAUX', 'DECOUPAGE',
                          'PLIAGE', 'PLI', 'COLLE', 'AFFAIRE', 'BOITE', 'CASIER', 'CAISSE', 'TROUSSE', 'CARTABLE',
                          'JEU', 'JOUET', 'PION', 'DOMINO', 'PUZZLE', 'CUBE', 'PERLE', 'CHOSE', 'FORME', 'CARRE',
                          'ROND', 'PATE', 'MODELER', 'TAMPON', 'LIVRE', 'HISTOIRE', 'BIBLIOTHEQUE', 'IMAGE', 'ALBUM',
                          'TITRE', 'CONTE', 'DICTIONNAIRE', 'MAGAZINE', 'CATALOGUE', 'PAGE', 'LIGNE', 'MOT',
                          'ENVELOPPE', 'ETIQUETTE', 'CARTE', 'APPEL', 'AFFICHE', 'ALPHABET', 'APPAREIL', 'CAMESCOPE',
                          'CASSETTE', 'CHAINE', 'CHANSON', 'CHIFFRE', 'CONTRAIRE', 'DIFFERENCE', 'DOIGT', 'ECRAN',
                          'ECRITURE', 'FILM', 'FOIS', 'FOI', 'IDEE', 'INSTRUMENT', 'INTRUS', 'LETTRE', 'LISTE',
                          'MAGNETOSCOPE', 'MAIN', 'MICRO', 'MODELE', 'MUSIQUE', 'NOM', 'NOMBRE', 'ORCHESTRE',
                          'ORDINATEUR', 'PHOTO', 'POINT', 'POSTER', 'POUCE', 'PRENOM', 'QUESTION', 'RADIO', 'SENS',
                          'TAMBOUR', 'TELECOMMANDE', 'TELEPHONE', 'TELEVISION', 'TRAIT', 'TROMPETTE', 'VOIX',
                          'XYLOPHONE', 'ZERO', 'CHANTER', 'CHERCHER', 'CHOISIR', 'CHUCHOTER', 'COLLER', 'COLORIER',
                          'COMMENCER', 'COMPARER', 'COMPTER', 'CONSTRUIRE', 'CONTINUER', 'COPIER', 'COUPER',
                          'DECHIRER', 'DECOLLER', 'DECORER', 'DECOUPER', 'DEMOLIR', 'DESSINER', 'DIRE', 'DISCUTER',
                          'ECOUTER', 'ECRIRE', 'EFFACER', 'ENTENDRE', 'ENTOURER', 'ENVOYER', 'FAIRE', 'FINIR',
                          'FOUILLER', 'GOUTER', 'IMITER', 'LAISSER', 'LIRE', 'METTRE', 'MONTRER', 'OUVRIR', 'PARLER',
                          'PEINDRE', 'PLIER', 'POSER', 'PRENDRE', 'PREPARER', 'RANGER', 'RECITER', 'RECOMMENCER',
                          'REGARDER', 'REMETTRE', 'REPETER', 'REPONDRE', 'SENTIR', 'SOULIGNER', 'TAILLER', 'TENIR',
                          'TERMINER', 'TOUCHER', 'TRAVAILLER', 'TRIER', 'AMI', 'ATTENTION', 'CAMARADE', 'COLERE',
                          'COPAIN', 'COQUIN', 'DAME', 'DIRECTEUR', 'DIRECTRICE', 'DROIT', 'EFFORT', 'ELEVE', 'ENFANT',
                          'FATIGUE', 'FAUTE', 'FILLE', 'GARCON', 'GARDIEN', 'MADAME', 'MAITRE', 'MAITRESSE',
                          'MENSONGE', 'ORDRE', 'PERSONNE', 'RETARD', 'JOUEUR', 'SOURIRE', 'TRAVAIL', 'AIDER',
                          'DEFENDRE', 'DESOBEIR', 'DISTRIBUER', 'ECHANGER', 'EXPLIQUER', 'GRONDER', 'OBEIR', 'OBLIGER',
                          'PARTAGER', 'PRETER', 'PRIVER', 'PROMETTRE', 'PROGRES', 'PROGRESSER', 'PUNIR', 'QUITTER',
                          'RACONTER', 'EXPLIQUER', 'REFUSER', 'SEPARER', 'BLOND', 'BRUN', 'CALME', 'CURIEUX',
                          'DIFFERENT', 'DOUX', 'ENERVER', 'GENTIL', 'GRAND', 'HANDICAPE', 'INSEPARABLE', 'JALOUX',
                          'MOYEN', 'MUET', 'NOIR', 'NOUVEAU', 'PETIT', 'POLI', 'PROPRE', 'ROUX', 'SAGE', 'SALE',
                          'SERIEUX', 'SOURD', 'TRANQUILLE', 'ARROSOIR', 'ASSIETTE', 'BALLE', 'BATEAU', 'BOITE',
                          'BOUCHON', 'BOUTEILLE', 'BULLES', 'CANARD', 'CASSEROLE', 'CUILLERE', 'CUVETTE', 'DOUCHE',
                          'ENTONNOIR', 'GOUTTES', 'LITRE', 'MOULIN', 'PLUIE', 'POISSON', 'PONT', 'POT', 'ROUE', 'SAC',
                          'PLASTIQUE', 'SALADIER', 'SEAU', 'TABLIER', 'TASSE', 'TROUS', 'VERRE', 'AGITER', 'AMUSER',
                          'ARROSER', 'ATTRAPER', 'AVANCER', 'BAIGNER', 'BARBOTER', 'BOUCHER', 'BOUGER', 'DEBORDER',
                          'DOUCHER', 'ECLABOUSSER', 'ESSUYER', 'ENVOYER', 'COULER', 'PARTIR', 'FLOTTER', 'GONFLER',
                          'INONDER', 'JOUER', 'LAVER', 'MELANGER', 'MOUILLER', 'NAGER', 'PLEUVOIR', 'PLONGER',
                          'POUSSER', 'POUVOIR', 'PRESSER', 'RECEVOIR', 'REMPLIR', 'RENVERSER', 'SECHER', 'SERRER',
                          'SOUFFLER', 'TIRER', 'TOURNER', 'TREMPER', 'VERSER', 'VIDER', 'VOULOIR', 'AMUSANT', 'CHAUD',
                          'FROID', 'HUMIDE', 'INTERESSANT', 'MOUILLE', 'SEC', 'TRANSPARENT', 'MOITIE', 'AUTANT',
                          'BEAUCOUP', 'ENCORE', 'MOINS', 'PEU', 'PLUS', 'TROP', 'ANORAK', 'ARC', 'BAGAGE', 'BAGUETTE',
                          'BARBE', 'BONNET', 'BOTTE', 'BOUTON', 'BRETELLE', 'CAGOULE', 'CASQUE', 'CASQUETTE',
                          'CEINTURE', 'CHAPEAU', 'CHAUSSETTE', 'CHAUSSON', 'CHAUSSURE', 'CHEMISE', 'CIGARETTE', 'COL',
                          'COLLANT', 'COURONNE', 'CRAVATE', 'CULOTTE', 'ECHARPE', 'EPEE', 'FEE', 'FLECHE', 'FUSIL',
                          'GANT', 'HABIT', 'JEAN', 'JUPE', 'LACET', 'LAINE', 'LINGE', 'LUNETTES', 'MAGICIEN', 'MAGIE',
                          'MAILLOT', 'MANCHE', 'MANTEAU', 'MOUCHOIR', 'MOUFLE', 'NOEUD', 'PAIRE', 'PANTALON', 'PIED',
                          'POCHE', 'PRINCE', 'PYJAMA', 'REINE', 'ROBE', 'ROI', 'RUBAN', 'SEMELLE', 'SOLDAT', 'SOCIERE']}
        for theme in mots:
            if theme.lower() in self.themes:
                self.ajt_mots(server, theme, mots[theme])
        return True

    def get_system(self, server: discord.Server):
        """Renvoie les données système du Pendu du serveur"""
        if server.id not in self.data:
            self.data[server.id] = {"MOTS": {},
                                    "ENCODE_CHAR": "•"}
            self.get_base(server)
            self.save()
        return self.data[server.id]

    def get_session(self, server: discord.Server, reset = False):
        """Retourne la session en cours du Pendu"""
        if server.id not in self.session or reset:
            self.session[server.id] = {"ON": False,
                                       "JOUEURS": {},
                                       "VIES": 0,
                                       "AVANCEMENT": [],
                                       "PROPOSE": []}
        return self.session[server.id]

    def load_themes(self, server: discord.Server, themes):
        """Charge les themes donnés sur le serveur"""
        sys = self.get_system(server)
        mots = []
        ok = []
        themes = themes[:3]
        for theme in themes:
            for m in sys["MOTS"]:
                if sys["MOTS"][m]["theme"].lower() == theme.lower():
                    mots.append([m, sys["MOTS"][m]["niveau"]])
                    ok.append(theme)
        if mots:
            return mots
        return "**Absent·s :** `{}`".format(" ,".join([i for i in themes if i not in ok]))

    def ajt_mots(self, server: discord.Server, theme, mots: list):
        """Ajoute des mots à un thème"""
        sys = self.get_system(server)
        theme = theme.lower()
        if theme in self.themes:
            for w in mots:
                if w.lower() not in sys["MOTS"]:
                    if len(w) <= 21:
                        if  3 <= len(w) <= 6:
                            niv = 1
                        elif 7 <= len(w) <= 15:
                            niv = 2
                        else:
                            niv = 3
                        sys["MOTS"][w.lower()] = {"niveau": niv,
                                                  "theme": theme.lower()}
            return sys["MOTS"]
        return False

    def get_mot(self, server: discord.Server, liste):
        """Choisi un mot au hasard dans la liste, l'encode et renvoie l'objet Mot()"""
        symb = self.get_system(server)["ENCODE_CHAR"]
        mot = random.choice(liste)
        mot, niveau = mot[0], mot[1]
        SumNetwork = namedtuple('Mot', ['literal', 'lettres', 'encode', 'niveau'])
        return SumNetwork(mot.upper(), [self.normal(l).upper() for l in mot], [n for n in symb * len(mot)], niveau)

    def check(self, msg: discord.Message):
        session = self.get_session(msg.author.server)
        if session["ON"]:
            if msg.content.lower()[0] in ["?", "&", ";;", "!", "\\", "§"] or len(msg.content.split(" ")) > 1:
                return False
            if not msg.author.bot:
                if msg.author.id in [i for i in session["JOUEURS"]]:
                    return True
        return False

    def leven(self, s1, s2):
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

    def normal(self, txt):
        ch1 = "àâçéèêëîïôöùûüÿ"
        ch2 = "aaceeeeiioouuuy"
        final = []
        for l in txt.lower():
            if l in ch1:
                final.append(ch2[ch1.index(l)])
            else:
                final.append(l)
        return "".join(final)

    def msgbye(self):
        heure = int(time.strftime("%H", time.localtime()))
        if 6 <= heure <= 12:
            return "Bonne matinée !"
        elif 13 <= heure <= 17:
            return "Bonne après-midi !"
        elif 18 <= heure <= 22:
            return "Bonne soirée !"
        else:
            return "Bonne nuit !"

    def simplecheck(self, reaction, user):
        return not user.bot

    @commands.command(pass_context=True, no_pm=True)
    async def pendu(self, ctx, *themes):
        """Lance une partie de Pendu classique"""
        server = ctx.message.server
        if not server.id == "328632789836496897": # LOCK
            return
        author = ctx.message.author
        pay = self.bot.get_cog("Pay").pay
        session, sys = self.get_session(server), self.get_system(server)
        if not session["ON"]:
            if themes:
                mots = self.load_themes(server, themes)
                if type(mots) != str:
                    session = self.get_session(server, True)
                    mot = self.get_mot(server, mots)
                    session["VIES"] = 7 + len(themes)
                    session["ON"] = True
                    session["AVANCEMENT"] = mot.encode
                    session["JOUEURS"][author.id] = {"BONUS": 0,
                                                     "MALUS": 0}
                    while session["VIES"] > 0 and "".join(session["AVANCEMENT"]) != mot.literal and session["ON"]:
                        txt = "**Vies** — {}\n".format(session["VIES"])
                        txt += "**Joueurs** — {}\n".format(" ,".join([server.get_member(i).name for
                                                                      i in session["JOUEURS"]]))
                        txt += "\n{}".format("".join(session["AVANCEMENT"]))
                        em = discord.Embed(title="PENDU — {}".format(" ,".join([i.title() for i in themes])),
                                           description=txt, color=0x286fff)
                        em.set_footer(text="Lettres proposées — {}".format("·".join(session["PROPOSE"])))
                        msg = await self.bot.say(embed=em)
                        rep = await self.bot.wait_for_message(channel=ctx.message.channel, timeout=90,
                                                              check=self.check)
                        if not rep:
                            if session["ON"]:
                                em.set_footer(text="× Partie terminée pour cause d'inactivité")
                                await self.bot.edit_message(msg, embed=em)
                                self.get_session(server, True)
                            else:
                                pass
                            return
                        elif rep.author.id in [i for i in session["JOUEURS"]]:
                            content = self.normal(rep.content).upper()
                            if content == "STOP":
                                await self.bot.say("**Partie terminée prématurément** — "
                                                   "Vos comptes ne sont pas affectés.")
                                self.get_session(server, True)
                                return
                            elif len(content) == 1:
                                if content in mot.lettres:
                                    if content not in self.normal("".join(session["AVANCEMENT"])) and \
                                            content not in session["PROPOSE"]:
                                        indexes = [[i,x] for i, x in enumerate(mot.lettres) if self.normal(x) == content]
                                        for l in indexes:
                                            session["AVANCEMENT"][l[0]] = l[1].upper()
                                            session["JOUEURS"][rep.author.id]["BONUS"] += 1
                                        session["PROPOSE"].append(content)
                                        if mot.lettres.count(content) > 1:
                                            phx = "{} lettres trouvées !".format(mot.lettres.count(content))
                                        else:
                                            phx = "Une lettre trouvée !"
                                        em.set_footer(text="{} — {}".format(self.bottomtext("good"), phx))
                                        await self.bot.edit_message(msg, embed=em)
                                        await asyncio.sleep(1)
                                    else:
                                        em.set_footer(text="{} — Vous avez déjà proposé cette lettre !".format(
                                            self.bottomtext("neutre")))
                                        await self.bot.edit_message(msg, embed=em)
                                        await asyncio.sleep(1)
                                else:
                                    session["VIES"] -= 1
                                    session["JOUEURS"][rep.author.id]["MALUS"] -= 1
                                    session["PROPOSE"].append(content)
                                    em.set_footer(text="{} — Cette lettre ne s'y trouve pas !".format(
                                        self.bottomtext("neutre")))
                                    await self.bot.edit_message(msg, embed=em)
                                    await asyncio.sleep(1)
                            elif content == "".join(mot.literal):
                                    session["JOUEURS"][rep.author.id]["BONUS"] += 2 * session["AVANCEMENT"].count(
                                        sys["ENCODE_CHAR"])
                                    session["AVANCEMENT"] = mot.lettres
                            else:
                                session["VIES"] -= 1
                                if self.leven("".join(mot.literal), content) == 1:
                                    session["JOUEURS"][rep.author.id]["MALUS"] -= 1
                                    em.set_footer(text="{} — Presque, mais non".format(self.bottomtext("bad")))
                                else:
                                    session["JOUEURS"][rep.author.id]["MALUS"] -= 2
                                    em.set_footer(text="{} — Ce n'est pas le mot recherché".format(
                                        self.bottomtext("bad")))
                                await self.bot.edit_message(msg, embed=em)
                                await asyncio.sleep(1)
                        else:
                            pass
                    if not session["VIES"]:
                        msg = "────────\n" \
                              "    |  //     |\n" \
                              "    |//       |\n" \
                              "    |/       (X)\n" \
                              "    |         /|\\\n" \
                              "    |           |\n" \
                              "    |         / \\\n" \
                              "   [|]\n" \
                              "  [ | ]\n" \
                              "#####################\n"
                        msg += "\nLe mot était **{}**".format(mot.literal.upper())
                        unord = []
                        for p in session["JOUEURS"]:
                            perte = session["JOUEURS"][p]["MALUS"] * mot.niveau
                            unord.append([perte, p])
                        classt = sorted(unord, key=operator.itemgetter(0), reverse=True)
                        clt = ""
                        monnaie = pay.get_money_name(server, symbole=True)
                        for i in classt:
                            user = server.get_member(i[1])
                            pay.perte_credits(user, i[0], "Échec au pendu", True)
                            clt += "**{}** — **-{}** {}\n".format(user.name, i[0], monnaie)
                        em = discord.Embed(title="PENDU — Échec", description=msg, color=0xff2841)
                        em.add_field(name="Perdants", value=clt)
                        em.set_footer(text=self.msgbye())
                        await self.bot.say(embed=em)
                        self.get_session(server, True)
                    elif "".join(session["AVANCEMENT"]) == mot.literal:
                        msg = "**Bravo !** Le mot est **{}**".format(mot.literal)
                        unord = []
                        for p in session["JOUEURS"]:
                            gain = session["JOUEURS"][p]["BONUS"] * mot.niveau
                            unord.append([gain, p])
                        classt = sorted(unord, key=operator.itemgetter(0), reverse=True)
                        clt = ""
                        monnaie = pay.get_money_name(server, symbole=True)
                        for i in classt:
                            user = server.get_member(i[1])
                            pay.gain_credits(user, i[0], "Gain au pendu")
                            clt += "**{}** — **-{}** {}\n".format(user.name, i[0], monnaie)
                        em = discord.Embed(title="PENDU — Victoire", description=msg, color=0x42f44b)
                        em.add_field(name="Gagnants", value=clt)
                        em.set_footer(text=self.msgbye())
                        await self.bot.say(embed=em)
                        self.get_session(server, True)
                    else:
                        await self.bot.say("**Partie arrêtée** — Vos comptes ne sont pas affectés")
                        self.get_session(server, True)
                else:
                    await self.bot.say("**Erreur** — Thème·s inexistant·s\n{}".format(mots))
            else:
                txt = ""
                for p in self.themes:
                    txt += "• {}\n".format(p)
                em = discord.Embed(title="Thèmes", description=txt, color=0xFFC125)
                em.set_footer(text="Charger plusieurs thèmes à la fois vous donne plus de vies (max. 3)")
                await self.bot.say(embed=em)
        elif themes[0].lower() == "stop":
            await self.bot.say("**Partie stoppée de force**")
            session["ON"] = False
            self.get_session(server, True)
        else:
            if author.id not in session["JOUEURS"]:
                session["jOUEURS"][author.id] = {"BONUS": 0,
                                                 "MALUS": 0}
                em = discord.Embed(description="{} a rejoint la partie de pendu !".format(author.mention),
                                   color=0xFFC125)
                await self.bot.say(embed=em)
            else:
                await self.bot.say("**Refusé** — Finissez déjà la partie en cours ou faîtes ")

    @commands.group(pass_context=True, no_pm=True)
    @checks.admin_or_permissions(ban_members=True)
    async def setpendu(self, ctx):
        """Paramètres du Pendu"""
        if ctx.invoked_subcommand is None:
            await send_cmd_help(ctx)

    @setpendu.command(pass_context=True)
    async def symbole(self, ctx, symbole: str):
        """Change le symbole utilisé pour cacher les lettres du mot"""
        sys = self.get_system(ctx.message.server)
        if len(symbole) == 1:
            if symbole not in ["*", "_", "~", "{", "}"]:
                sys["ENCODE_CHAR"] = symbole
                await self.bot.say("**Symbole changé** — Le mot sera désormais encodé avec ce symbole")
                self.save()
            else:
                await self.bot.say("**Déconseillé** — Ce symbole est utilisé dans le formattage du texte sur Discord "
                                   "et pourrait causer des bugs d'affichage")
        else:
            await self.bot.say("**Refusé** — Le symbole doit être composé que d'un caractère")

    @setpendu.command(aliases=["addwords", "addw"], pass_context=True)
    async def ajtmots(self, ctx, theme, *mots):
        """Permet d'ajouter des mots un par un à un thème, séparés par un espace

        - Chaque mot doit faire entre 3 et 21 caractères et ne doit pas être déjà présent dans un thème"""
        sys = self.get_system(ctx.message.server)
        if theme.lower() in self.themes:
            if mots:
                txt = ""
                for m in mots:
                    if 3 <= len(m) <= 21:
                        if m.lower() not in sys["MOTS"]:
                            txt += "• {}\n".format(m.lower())
                        else:
                            txt += "◦ ~~{}~~\n".format(m.lower())
                em = discord.Embed(title="Voulez-vous ajouter ces mots ?", description=txt, color=0xFFC125)
                em.set_footer(text="Ils seront ajoutés au thème \"{}\"".format(theme.title()))
                msg = await self.bot.say(embed=em)
                await self.bot.add_reaction(msg, "✅")
                await self.bot.add_reaction(msg, "❎")
                rep = await self.bot.wait_for_reaction(message=msg, timeout=60, check=self.simplecheck,
                                                       user=ctx.message.author)
                if not rep or rep.reaction.emoji == "❎":
                    await self.bot.delete_message(msg)
                    await self.bot.say("**Annulé** — Ces mots ne seront pas ajoutés à ce thème")
                else:
                    if self.ajt_mots(ctx.message.server, theme, mots):
                        await self.bot.say("**Succès** — Ces mots ont été ajoutés au thème")
                        self.save()
                    else:
                        await self.bot.say("**Erreur** — Impossible d'ajouter ces mots au thème")
            else:
                txt = " ,".join([w.lower() for w in self.load_themes(ctx.message.server, theme)])
                em = discord.Embed(title="Mots présents dans le thème \"{}\"".format(theme.title()),
                                   description=txt, color=0xFFC125)
                await self.bot.say(embed=em)
        else:
            txt = ""
            for p in self.themes:
                txt += "• {}\n".format(p)
            em = discord.Embed(title="Thèmes", description=txt, color=0xFFC125)
            em.set_footer(text="Un même mot ne peut être dans deux thèmes différents")
            await self.bot.say(embed=em)

    @setpendu.command(aliases=["delwords", "delw"], pass_context=True)
    async def delmots(self, ctx, *mots):
        """Supprime des mots de leurs thèmes respectifs (séparés par un espace)"""
        sys = self.get_system(ctx.message.server)
        succes = []
        for m in mots:
            if m.lower() in sys["MOTS"]:
                del sys["MOTS"][m.lower()]
                succes.append(m.lower())
        txt = ""
        for s in succes:
            "◦ ~~{}~~\n".format(s)
        em = discord.Embed(title="Mots supprimés", description=txt, color=0xc9000a)
        em.set_footer(text="Les mots éventuellement non-affichés n'ont pas pu être supprimés")
        await self.bot.say(embed=em)

def check_folders():
    if not os.path.exists("data/pendu/"):
        print("Creation du dossier Jeu du pendu...")
        os.makedirs("data/pendu")


def check_files():
    if not os.path.isfile("data/pendu/data.json"):
        print("Création du fichier Jeu du pendu")
        fileIO("data/pendu/data.json", "save", {})


def setup(bot):
    check_folders()
    check_files()
    n = Pendu(bot)
    bot.add_cog(n)