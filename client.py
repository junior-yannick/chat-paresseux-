import socket
import json
import threading
import tkinter as tk
from tkinter import simpledialog, messagebox, scrolledtext
import random
import time

class Client:
    def __init__(self, hote='127.0.0.2', port=10002):
        # Initialisation du client avec l'adresse IP et le port du serveur
        self.hote = hote
        self.port = port
        # Création d'un socket client pour la communication réseau
        self.socket_client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        # Indique l'état de connexion du client
        self.connecte = False
        # Nom du joueur, à définir plus tard
        self.nom_joueur = None
        # Taille de la grille de jeu, déterminée par le serveur
        self.taille_grille = None
        # Liste des boutons représentant la grille de jeu
        self.boutons = []
        # Position choisie par le joueur dans la grille
        self.position_choisie = None
        # Indique si le joueur a fait un choix dans la grille
        self.est_choix_fait = False
        # Historique actuel des messages du chat
        self.historique_chat_actuel = []
        # Configuration de l'interface graphique du client
        self.configurer_gui()


    def configurer_gui(self):
        # Configuration de l'interface graphique principale
        self.root = tk.Tk()
        self.root.title("Le Chat Paresseux")  # Titre de la fenêtre
        # Définition de l'action à effectuer lorsque la fenêtre est fermée
        self.root.protocol("WM_DELETE_WINDOW", self.deconnecter)

        # Zone de texte pour afficher l'historique du chat
        self.historique_chat = scrolledtext.ScrolledText(self.root, state='disabled', height=10, width=50)
        self.historique_chat.grid(row=0, column=10, rowspan=10, padx=(10, 0), sticky='ns')

        # Champ de texte pour écrire un message à envoyer
        self.message_chat = tk.Entry(self.root, width=40, fg='grey')
        self.message_chat.insert(0, "Écrivez un message...")

        # Gestion des événements de focus pour le champ de texte
        self.message_chat.bind("<FocusIn>", self.effacer_placeholder)
        self.message_chat.bind("<FocusOut>", self.ajouter_placeholder)

        # Envoi du message lorsque la touche Entrée est pressée
        self.message_chat.bind("<Return>", self.envoyer_message_chat)
        self.message_chat.grid(row=10, column=10, sticky='ew')

        # Bouton pour envoyer le message écrit dans le champ de texte
        self.bouton_envoyer = tk.Button(self.root, text="Envoyer", command=self.envoyer_message_chat)
        self.bouton_envoyer.grid(row=10, column=11)

        # Zone de texte pour afficher les scores des joueurs
        self.zone_scores = tk.Text(self.root, height=5, width=50)
        self.zone_scores.grid(row=11, column=10, columnspan=2, sticky="ew")
        self.zone_scores.config(state='disabled')

        # Bouton pour indiquer que le joueur est prêt à jouer
        self.bouton_pret = tk.Button(self.root, text="Prêt", command=self.indiquer_pret)
        self.bouton_pret.grid(row=12, column=10, columnspan=2, sticky="ew")

        # Bouton pour se déconnecter du serveur
        self.bouton_deconnexion = tk.Button(self.root, text="Déconnexion", command=self.deconnecter)
        self.bouton_deconnexion.grid(row=13, column=10, columnspan=2, sticky="ew")


    def effacer_placeholder(self, event):
        # Efface le texte indicatif lorsque le champ de saisie est sélectionné
        if self.message_chat.get() == "Écrivez un message...":
            self.message_chat.delete(0, "end")
            self.message_chat.config(fg='black')


    def ajouter_placeholder(self, event):
        # Remet le texte indicatif si le champ de saisie est vide lorsqu'il perd le focus
        if not self.message_chat.get().strip():
            self.message_chat.insert(0, "Écrivez un message...")
            self.message_chat.config(fg='grey')


    def construire_grille(self):
        # Construit la grille de boutons pour le jeu
        for row in self.boutons:
            for bouton in row:
                bouton.destroy()  # Supprime les boutons existants
        self.boutons = []  # Réinitialise la liste des boutons
        # Crée de nouveaux boutons pour la grille selon sa taille
        for i in range(self.taille_grille):
            row = []
            for j in range(self.taille_grille):
                bouton = tk.Button(self.root, text=f"{i*self.taille_grille+j}", width=4, height=2,
                                   command=lambda n=i*self.taille_grille+j: self.envoyer_choix(n))
                bouton.grid(row=i, column=j)
                row.append(bouton)
            self.boutons.append(row)


    def se_connecter_au_serveur(self):
        # Connexion au serveur
        self.demander_nom()  # Demande le nom du joueur
        try:
            self.socket_client.connect((self.hote, self.port))  # Tentative de connexion au serveur
            # Envoie le nom du joueur au serveur
            self.socket_client.send(json.dumps({"action": "NOM", "nom": self.nom_joueur}).encode('utf-8'))
            self.connecte = True  # Marque le client comme connecté
            # Démarre un thread pour recevoir les messages du serveur
            threading.Thread(target=self.recevoir_messages, daemon=True).start()
        except Exception as e:
            # Affiche un message d'erreur en cas de problème de connexion
            messagebox.showerror("Erreur de connexion", f"Impossible de se connecter au serveur : {e}")
            self.deconnecter()  # Déconnecte le client en cas d'erreur


    def recevoir_messages(self):
        # Boucle de réception des messages du serveur
        while self.connecte:
            try:
                donnees = self.socket_client.recv(4096)  # Réception des données du serveur
                if donnees:
                    message = json.loads(donnees.decode('utf-8'))  # Décodage du message JSON
                    self.gerer_message(message)  # Gestion des messages reçus
                else:
                    # Affiche un message si la connexion est perdue
                    messagebox.showinfo("Information", "La connexion avec le serveur a été perdue.")
                    self.deconnecter()  # Déconnecte le client
                    break
            except ConnectionResetError:
                # Gestion de la déconnexion inattendue par le serveur
                self.deconnecter()
                break
            except Exception as e:
                # Affiche un message en cas d'erreur de réception
                messagebox.showerror("Erreur", f"Un problème est survenu : {e}")
                self.deconnecter()
                break


    def gerer_message(self, message):
        # Traite les différents types de messages reçus du serveur
        if message["type"] == "CHAT":
            # Mise à jour de l'historique du chat
            self.historique_chat_actuel = message["historique_chat"]
            self.mettre_a_jour_historique_chat(message["historique_chat"])
        elif message["type"] == "DEBUT_TOUR":
            # Mise à jour de la grille pour un nouveau tour
            self.taille_grille = message["taille_grille"]
            self.construire_grille()
            self.reinitialiser_bouton_pret()
        elif message["type"] == "SCORES":
            # Affichage des scores
            self.afficher_scores(message["scores"])
            self.afficher_position_chat(message["position_chat"])
        elif message["type"] == "FIN_JEU":
            # Notification de fin de jeu et déconnexion
            messagebox.showinfo("Fin du jeu", message["message"])
            self.deconnecter()
        elif message["type"] == "INFO":
            # Affichage d'informations diverses
            messagebox.showinfo("Information", message["message"])
            if "gagnant" in message["message"].lower():
                self.deconnecter()  # Déconnexion si le joueur gagne



    def envoyer_choix(self, position):
        # Envoi le choix de position du joueur au serveur
        if self.connecte and not self.est_choix_fait:
            self.est_choix_fait = True  # Marque le choix comme fait
            self.position_choisie = position  # Sauvegarde la position choisie
            # Met en évidence la position choisie dans l'interface utilisateur
            self.boutons[position // self.taille_grille][position % self.taille_grille].config(bg='red')
            # Envoye le choix au serveur
            self.socket_client.send(json.dumps({"action": "CHOIX", "position": position}).encode('utf-8'))
            self.desactiver_grille()  # Désactive la grille après le choix

    def envoyer_message_chat(self, event=None):
        # Envoi un message écrit dans le chat au serveur
        message = self.message_chat.get()  # Obtenir le message du champ de saisie
        if message and self.connecte:
            # Envoye le message au serveur si le client est connecté
            self.socket_client.send(json.dumps({"action": "CHAT", "text": message}).encode('utf-8'))
            self.message_chat.delete(0, tk.END)  # Effacer le champ de saisie après l'envoi


    def activer_grille(self):
        # Active tous les boutons de la grille pour permettre des choix
        for row in self.boutons:
            for bouton in row:
                bouton.config(state='normal', bg='SystemButtonFace')


    def desactiver_grille(self):
        # Désactive tous les boutons de la grille pour empêcher plusieurs choix
        for row in self.boutons:
            for bouton in row:
                bouton.config(state='disabled', bg='grey')


    def afficher_scores(self, scores):
        self.scores = scores  # Met à jour le dictionnaire des scores
        self.zone_scores.config(state='normal')
        self.zone_scores.delete(1.0, tk.END)
        scores_texte = "\n".join([f"{nom}: {score} points" for nom, score in scores.items()])
        self.zone_scores.insert(tk.END, scores_texte)
        self.zone_scores.config(state='disabled')
    # Mise à jour de l'historique de chat pour afficher le score actuel
        self.mettre_a_jour_historique_chat(self.historique_chat_actuel)


    def afficher_position_chat(self, position_chat_numero):
        # Calcule les coordonnées du chat à partir de sa position numérique
        x_chat, y_chat = divmod(position_chat_numero, self.taille_grille)
        
        # Démarre une animation qui montre le déplacement du chat pendant 5 secondes
        fin_animation = time.time() + 5
        while time.time() < fin_animation:
            # Choisis une nouvelle position aléatoire pour le chat à chaque itération
            nouvelle_x = random.randint(0, self.taille_grille - 1)
            nouvelle_y = random.randint(0, self.taille_grille - 1)
            self.boutons[nouvelle_x][nouvelle_y].config(bg='yellow')
            
            # Met à jour l'interface utilisateur et attend un peu
            self.root.update()
            time.sleep(0.3) 
            
            # Remet la couleur du bouton précédent à la normale
            self.boutons[nouvelle_x][nouvelle_y].config(bg='SystemButtonFace')
        
        # Affiche la position finale du chat
        self.boutons[x_chat][y_chat].config(bg='yellow')
        # Réinitialise la position choisie par le joueur après l'animation 
        if self.position_choisie is not None:
            x_choisi, y_choisi = divmod(self.position_choisie, self.taille_grille)
            if (x_choisi, y_choisi) != (x_chat, y_chat):
                self.boutons[x_choisi][y_choisi].config(bg='white')
        # Réinitialise la grille après un bref délai
        self.root.after(4000, self.reinitialiser_grille)


    def reinitialiser_grille(self):
        # Réinitialise l'état de la grille pour un nouveau tour
        for ligne in self.boutons:
            for bouton in ligne:
                bouton.config(state='normal', bg='SystemButtonFace')
        self.position_choisie = None  # Réinitialise la position choisie
        self.est_choix_fait = False  # Réinitialise l'état de choix
        self.desactiver_grille()  # Désactive la grille


    def reinitialiser_bouton_pret(self):
        # Réinitialise l'état du bouton "Prêt" pour un nouveau tour
        self.bouton_pret.config(state='normal', bg='SystemButtonFace')


    def demander_nom(self):
        # Demander au joueur de saisir son nom
        self.nom_joueur = simpledialog.askstring("Nom", "Bienvenu, veuillez entrez votre nom:")
        if not self.nom_joueur:
            messagebox.showerror("Erreur", "Vous devez entrer un nom pour jouer.")
            self.root.destroy()  # Ferme l'application si aucun nom n'est fourni


    def mettre_a_jour_historique_chat(self, historique_chat):
        # Mettre à jour l'affichage de l'historique du chat
        self.historique_chat.config(state='normal')  # Active la zone de texte
        self.historique_chat.delete(1.0, tk.END)  # Effacer le contenu actuel
        if self.nom_joueur in self.scores:
            score_joueur = self.scores[self.nom_joueur]
            info_joueur = f"{self.nom_joueur} : {score_joueur} points\n"
            self.historique_chat.insert(tk.END, info_joueur)  # Affiche le score du joueur
        self.historique_chat.insert(tk.END, "\n".join(historique_chat))  # Ajoute les messages du chat
        self.historique_chat.config(state='disabled')  # Désactive la zone de texte


    def indiquer_pret(self):
        # Indique au serveur que le joueur est prêt
        self.bouton_pret.config(bg='grey', state='disabled')
        self.socket_client.send(json.dumps({"action": "PRET"}).encode('utf-8'))


    def deconnecter(self):
        # Déconnecte proprement le serveur
        if self.connecte:
            try:
                self.socket_client.send(json.dumps({"action": "DECONNEXION"}).encode('utf-8'))
            except Exception as e:
                print(f"Erreur lors de l'envoi du message de déconnexion : {e}")
            finally:
                self.socket_client.close()  # Ferme le socket
                self.connecte = False  # Marque comme déconnecté
                self.root.destroy()  # Ferme l'interface graphique


    def executer(self):
        # Exécute la boucle principale de l'interface graphique
        self.root.mainloop()


if __name__ == "__main__":
    client = Client()
    try:
        client.se_connecter_au_serveur()
        client.executer()
    except Exception as e:
        print(f"Erreur lors de la connexion ou du fonctionnement du client : {e}")