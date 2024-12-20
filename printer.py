import os
import pyperclip

def afficher_fichiers_extensions_autorisees(extensions, dossiers_exclus):
    contenu_final = ""  # Chaîne qui contiendra tout le texte à copier dans le presse-papiers

    # Parcourt tous les sous-dossiers et fichiers du répertoire de travail actuel
    for racine, sous_dossiers, fichiers in os.walk(os.getcwd()):
        # Filtre les dossiers exclus pour qu'ils ne soient pas parcourus
        sous_dossiers[:] = [d for d in sous_dossiers if d not in dossiers_exclus]

        for fichier in fichiers:
            # Filtre les fichiers selon les extensions spécifiées
            if any(fichier.endswith(ext) for ext in extensions):
                chemin_relatif = os.path.relpath(os.path.join(racine, fichier))
                contenu_final += f"file path : {chemin_relatif}\n"
                
                try:
                    with open(os.path.join(racine, fichier), 'r', encoding='utf-8') as f:
                        contenu_fichier = f.read()
                        contenu_final += f"{contenu_fichier}\n\n"
                except Exception as e:
                    contenu_final += f"Erreur de lecture du fichier : {e}\n\n"
    
    # Affiche le contenu dans le terminal
    print(contenu_final)
    
    # Copie le tout dans le presse-papiers
    pyperclip.copy(contenu_final)
    print("L'ensemble du contenu a été copié dans le presse-papiers.")

# Exemple d'utilisation avec les extensions autorisées et les dossiers exclus
extensions_autorisees = ['.py', 'Dockerfile', '.env', '.MD', '.yml', '.txt']  # Remplacez par les extensions souhaitées
dossiers_exclus = ['.venv', 'printer.py']  # Remplacez par les dossiers à ignorer
afficher_fichiers_extensions_autorisees(extensions_autorisees, dossiers_exclus)