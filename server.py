import socket
import random
import json
import threading
import time

class Serveur:
    def __init__(self, hote='127.0.0.2', port=10002, taille_grille_min=3, taille_grille_max=10, points_depart=10):
        # Initialisation du serveur avec des paramètres par défaut
        self.hote = hote  # Adresse IP du serveur
        self.port = port  # Port du serveur
        self.taille_grille_min = taille_grille_min  # Taille minimale de la grille de jeu
        self.taille_grille_max = taille_grille_max  # Taille maximale de la grille de jeu
        # Génération aléatoire de la taille de la grille pour la partie actuelle
        self.taille_grille = random.randint(self.taille_grille_min, self.taille_grille_max)
        self.points_depart = points_depart  # Points de départ pour chaque joueur
        # Création d'un socket TCP/IP pour le serveur
        self.socket_serveur = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.clients = {}  # Dictionnaire pour stocker les sockets des clients
        self.noms_clients = {}  # Dictionnaire pour stocker les noms des clients
        self.scores_joueurs = {}  # Dictionnaire pour stocker les scores des joueurs
        self.choix_joueurs = {}  # Dictionnaire pour stocker les choix des joueurs
        self.position_chat = self.generer_position_chat()  # Génération de la position initiale du chat
        self.historique_chat = []  # Liste pour stocker l'historique du chat
        self.verrou = threading.Lock()  # Verrou pour gérer l'accès concurrent aux ressources partagées
        self.joueurs_prets = set()  # Ensemble pour stocker les joueurs qui sont prêts
        self.partie_demarree = False  # Indicateur de début de partie
        self.partie_en_cours = False  # Indicateur de partie en cours
        self.premier_tour_passe = False  # Indicateur pour vérifier si le premier tour est passé

        
    def generer_position_chat(self):
        # Génération aléatoire de la position du chat dans la grille
        return random.randint(0, self.taille_grille - 1), random.randint(0, self.taille_grille - 1)
    

    def demarrer_serveur(self):
        # Démarrage du serveur pour écouter les connexions entrantes
        self.socket_serveur.bind((self.hote, self.port))  # Association du socket avec l'adresse IP et le port
        self.socket_serveur.listen()  # Le serveur écoute les connexions entrantes
        print(f"Serveur en écoute sur l'adresse {self.hote} et sur le port {self.port}")
        self.accepter_connexions()  # Appel de la fonction pour accepter les connexions


    def accepter_connexions(self):
        # Boucle infinie pour accepter les nouvelles connexions
        while True:
            client_socket, _ = self.socket_serveur.accept()  # Accepte une nouvelle connexion
            if self.partie_en_cours:
                # Si une partie est déjà en cours, refuse la nouvelle connexion
                print("Un joueur a tenté de se connecter pendant une partie en cours.")
                message = json.dumps({"type": "INFO", "message": "Une partie est déjà en cours. Veuillez réessayer plus tard."})
                try:
                    client_socket.send(message.encode('utf-8'))  # Envoie un message au client
                    time.sleep(1)  # Attendre un peu avant de fermer la connexion
                finally:
                    client_socket.close()  # Ferme la connexion avec le client
            else:
                # Si aucune partie n'est en cours, démarre un nouveau thread pour gérer le client
                threading.Thread(target=self.gerer_client, args=(client_socket,)).start()


    def gerer_client(self, client_socket):
        # Fonction pour gérer la communication avec un client spécifique
        try:
            while True:
                # Boucle pour lire les messages du client
                message = client_socket.recv(1024)  # Lecture d'un message du client
                if not message:
                    break  # Sortie de la boucle si aucun message n'est reçu
                message = json.loads(message.decode('utf-8'))  # Décodage et interprétation du message JSON
                action = message.get("action")  # Extraction de l'action demandée par le client

                # Traitement de l'action demandée par le client
                if action == "NOM":
                    self.enregistrer_nom(client_socket, message["nom"])
                elif action == "PRET":
                    self.gerer_pret(client_socket)
                elif action == "CHOIX":
                    self.traiter_choix(client_socket, message["position"])
                elif action == "CHAT":
                    self.traiter_chat(message["text"], client_socket)
        except socket.error as socket_error:
            # Gestion des erreurs de socket
            print(f"{socket_error}")
        finally:
            # Assure la déconnexion propre du client
            self.retirer_joueur(client_socket)


    def enregistrer_nom(self, client_socket, nom_joueur):
        # Enregistrement du nom du joueur et initialisation de son score et de son choix
        with self.verrou:
            # Utilisation d'un verrou pour éviter les conflits d'accès
            self.clients[client_socket] = nom_joueur  # Enregistrement du socket client
            self.noms_clients[nom_joueur] = client_socket  # Association du nom du joueur avec son socket
            self.scores_joueurs[nom_joueur] = self.points_depart  # Initialisation du score du joueur
            self.choix_joueurs[nom_joueur] = None  # Initialisation du choix du joueur
            print(f"{nom_joueur} est connecté.")
            # Envoi un message de bienvenue au joueur
            message_bienvenue = "Il faut un minimum de 3 joueurs pour lancer le jeu. Cliquez juste sur prêt si oui, et patientez que la grille s'active, merci."
            self.envoyer_message(nom_joueur, {"type": "INFO", "message": message_bienvenue})


    def gerer_pret(self, client_socket):
        # Gestion de l'état prêt d'un joueur
        with self.verrou:
            nom_joueur = self.clients[client_socket]
            self.joueurs_prets.add(nom_joueur)  # Ajout du joueur à l'ensemble des joueurs prêts
            
            # Vérifie si tous les joueurs sont prêts pour commencer un nouveau tour
            if len(self.joueurs_prets) == len(self.clients) and (len(self.clients) >= 3 or self.premier_tour_passe):
                self.commencer_nouveau_tour()  # Commence un nouveau tour si toutes les conditions sont remplies
                self.premier_tour_passe = True
            elif not self.premier_tour_passe:
                # Affichage de l'état de préparation des joueurs avant le début du jeu
                print(f"En attente que tous les joueurs soient prêts. {len(self.joueurs_prets)}/{len(self.clients)} joueurs prêts.")


    def commencer_nouveau_tour(self):
        # Début d'un nouveau tour de jeu
        # Réinitialisation de la taille de la grille pour le nouveau tour
        self.taille_grille = random.randint(self.taille_grille_min, self.taille_grille_max)
        self.position_chat = self.generer_position_chat()  # Génération d'une nouvelle position pour le chat
        self.joueurs_prets.clear()  # Réinitialisation des joueurs prêts pour le nouveau tour
        for nom_joueur in self.clients.values():
            self.choix_joueurs[nom_joueur] = None  # Réinitialisation des choix des joueurs pour le nouveau tour
            # Envoi de la nouvelle position du chat et de la taille de la grille aux joueurs
            self.envoyer_message(nom_joueur, {
                "type": "DEBUT_TOUR",
                "position_chat": self.position_chat_numero(),
                "taille_grille": self.taille_grille
            })
        self.partie_en_cours = True  # Indication que la partie est en cours


    def traiter_choix(self, client_socket, position):
        # Traitement du choix de position envoyé par un joueur
        nom_joueur = self.clients[client_socket]
        with self.verrou:
            # Enregistrement du choix du joueur
            self.choix_joueurs[nom_joueur] = position
            # Si tous les joueurs ont fait leur choix, calculer les scores
            if all(choix is not None for choix in self.choix_joueurs.values()):
                self.calculer_scores()
                self.envoyer_scores()


    def calculer_scores(self):
        # Calcul des scores des joueurs en fonction de leurs choix et de la position du chat
        chat_x, chat_y = self.position_chat
        for nom_joueur, position in self.choix_joueurs.items():
            joueur_x, joueur_y = divmod(position, self.taille_grille)
            # Attribution des points en fonction de la proximité du choix avec la position du chat
            if (joueur_x, joueur_y) == (chat_x, chat_y):
                self.scores_joueurs[nom_joueur] += 10
            elif (abs(joueur_x - chat_x) == 1 and joueur_y == chat_y) or \
                 (abs(joueur_y - chat_y) == 1 and joueur_x == chat_x):
                self.scores_joueurs[nom_joueur] += 2
            else:
                self.scores_joueurs[nom_joueur] -= 1
        
        # Mise en place d'un délai avant de vérifier la fin du jeu pour permettre aux joueurs de voir les résultats
        timer = threading.Timer(3.0, self.verifier_fin_jeu)
        timer.start()


    
    def verifier_fin_jeu(self):
        # Vérifie si la partie doit se terminer
        with self.verrou:
            # Identifie les joueurs dont le score est inférieur ou égal à 0
            joueurs_a_retirer = [nom for nom, score in self.scores_joueurs.items() if score <= 0]
            for nom_joueur in joueurs_a_retirer:
                # Envoi un message aux joueurs éliminés et les retire du jeu
                self.envoyer_message(nom_joueur, {"type": "FIN_JEU", "message": "Vous avez perdu toutes vos vies!"})

            # Si tous les joueurs sont éliminés,  le serveur s'arrete
            if len(self.scores_joueurs) - len(joueurs_a_retirer) == 0:
                print("Tous les joueurs ont perdu. Partie terminée.")
                self.arreter_serveur()
            elif len(self.scores_joueurs) - len(joueurs_a_retirer) == 1:
                # S'il reste un seul joueur, il est le gagnant
                gagnant = next(iter(set(self.scores_joueurs.keys()) - set(joueurs_a_retirer)))
                print(f"{gagnant} est le gagnant!")
                self.envoyer_message(gagnant, {"type": "INFO", "message": "Félicitations, vous êtes le gagnant!"})
                self.arreter_serveur()


    def position_chat_numero(self):
        # Calcule la position numérique du chat dans la grille
        return self.position_chat[0] * self.taille_grille + self.position_chat[1]
    

    def envoyer_scores(self):
        # Envoi les scores actuels et la position du chat à tous les clients
        mise_a_jour = {
            "type": "SCORES",
            "position_chat": self.position_chat_numero(),
            "scores": {nom: score for nom, score in self.scores_joueurs.items()},
            "chat_position": self.position_chat_numero()
        }
        for client_socket in self.clients.keys():
            self.envoyer_message_par_socket(client_socket, mise_a_jour)


    def traiter_chat(self, texte, client_socket):
        # Traite un message de chat envoyé par un joueur
        nom_joueur = self.clients[client_socket]
        message_chat = f"{nom_joueur}: {texte}"
        with self.verrou:
            self.historique_chat.append(message_chat)  # Ajoute le message à l'historique
            self.diffuser_chat()  # Diffuse le message à tous les joueurs

    def diffuser_chat(self):
        # Diffuse les derniers messages de chat à tous les clients
        mise_a_jour_chat = {
            "type": "CHAT",
            "historique_chat": self.historique_chat[-10:]  # Envoyer les 10 derniers messages
        }
        for client_socket in self.clients.keys():
            self.envoyer_message_par_socket(client_socket, mise_a_jour_chat)


    def envoyer_message(self, nom_joueur, message):
        # Envoi un message à un joueur spécifique
        client_socket = self.noms_clients[nom_joueur]
        if client_socket:
            self.envoyer_message_par_socket(client_socket, message)


    def envoyer_message_par_socket(self, client_socket, message):
        # Envoi un message à travers le socket spécifié
        try:
            client_socket.sendall(json.dumps(message).encode('utf-8'))
        except Exception as e:
            print(f"Erreur lors de l'envoi d'un message: {e}")
            self.retirer_joueur(client_socket)


    def retirer_joueur(self, client_socket):
        # Retire un joueur de la partie et ferme sa connexion
        with self.verrou:
            nom_joueur = self.clients.pop(client_socket, None)
            if nom_joueur:
                print(f"{nom_joueur} s'est déconnecté.")
                self.noms_clients.pop(nom_joueur, None)
                self.scores_joueurs.pop(nom_joueur, None)
                self.choix_joueurs.pop(nom_joueur, None)
                self.joueurs_prets.discard(nom_joueur)
                print(f"{nom_joueur} a été retiré du jeu.")

                try:
                    client_socket.close()
                except Exception as e:
                    print(f"Erreur lors de la fermeture d'un client socket: {e}")


    def terminer_partie(self):
        # Termine la partie et arrête le serveur
        if len(self.clients) == 0:
            print("Tous les joueurs ont perdu. Partie terminée.")
        else:
            print("Pas assez de joueurs pour continuer le jeu.")
        self.arreter_serveur()


    def arreter_serveur(self):
        # Arrête le serveur et ferme toutes les connexions
        with self.verrou:
            for nom_joueur in self.clients.values():
                self.envoyer_message(nom_joueur, {"type": "INFO", "message": "Le serveur est arrêté."})
            time.sleep(1)  # Donner un peu de temps pour que les messages soient envoyés
            for client_socket in list(self.clients.keys()):
                try:
                    client_socket.close()
                except Exception as e:
                    print(f"Erreur lors de la fermeture d'un client socket: {e}")
            self.socket_serveur.close()  # Ferme le socket serveur
            self.clients.clear()  # Efface tous les clients
            self.noms_clients.clear()  # Efface tous les noms clients
            self.scores_joueurs.clear()  # Efface tous les scores
            self.choix_joueurs.clear()  # Efface tous les choix
            self.joueurs_prets.clear()  # Efface la liste des joueurs prêts
            self.partie_en_cours = False  # Indique que la partie n'est plus en cours
            print("Serveur arrêté.")

if __name__ == "__main__":
    serveur = Serveur()
    serveur.demarrer_serveur()  # Démarre le serveur