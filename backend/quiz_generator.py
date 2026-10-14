"""
Quiz Generator — Génération automatique de QCM à partir de PDF et vidéos.

Méthodes :
- 'auto'   : Extraction locale + génération par règles (gratuit, hors-ligne)
- 'openai' : Extraction + génération via l'API OpenAI (nécessite OPENAI_API_KEY)
"""

import os
import re
import random
import logging
import tempfile
from typing import Optional

logger = logging.getLogger(__name__)

# ===== CONFIGURATION =====
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY', '')
GROQ_API_KEY = os.getenv('GROQ_API_KEY', '')
GROQ_MODEL = os.getenv('GROQ_MODEL', 'llama-3.3-70b-versatile')

# Mots vides français à ignorer lors de l'extraction de mots-clés
STOP_WORDS_FR = {
    'le', 'la', 'les', 'un', 'une', 'des', 'de', 'du', 'et', 'ou', 'à', 'au', 'aux',
    'en', 'dans', 'sur', 'sous', 'avec', 'sans', 'pour', 'par', 'est', 'sont', 'être',
    'avoir', 'fait', 'faire', 'plus', 'moins', 'très', 'bien', 'comme', 'mais', 'donc',
    'car', 'ni', 'or', 'si', 'que', 'qui', 'quoi', 'dont', 'où', 'ce', 'cet', 'cette',
    'ces', 'mon', 'ton', 'son', 'notre', 'votre', 'leur', 'ma', 'ta', 'sa', 'mes', 'tes',
    'ses', 'nos', 'vos', 'leurs', 'je', 'tu', 'il', 'elle', 'on', 'nous', 'vous', 'ils',
    'elles', 'ne', 'pas', 'plus', 'moins', 'aussi', 'alors', 'ainsi', 'après', 'avant',
    'chez', 'vers', 'pendant', 'depuis', 'jusque', 'voici', 'voilà', 'y', 'on', 'lui',
    'leur', 'eux', 'elle', 'celles', 'celui', 'celle', 'ceux', 'celles', 'même', 'mêmes',
    'tout', 'toute', 'tous', 'toutes', 'autre', 'autres', 'même', 'tel', 'telle', 'tels',
    'telles', 'chaque', 'quel', 'quelle', 'quels', 'quelles', 'lequel', 'laquelle',
    'lesquels', 'lesquelles', 'duquel', 'desquels', 'desquelles', 'auquel', 'auxquels',
    'auxquelles', 'dont', 'où', 'quand', 'comment', 'pourquoi', 'combien', 'le', 'la',
    'les', 'l', 'd', 'j', 'c', 's', 'n', 'm', 't', 'qu', 'jusquo', 'quoique', 'lorsque',
    'puisque', 'quoique', 'bien', 'afin', 'tant', 'tellement', 'assez', 'trop', 'peu',
    'beaucoup', 'plusieurs', 'certains', 'certaines', 'quelque', 'quelques', 'chaque',
    'nul', 'nulle', 'aucun', 'aucune', 'tel', 'telle', 'tels', 'telles', 'même', 'mêmes',
    'tout', 'toute', 'tous', 'toutes', 'autre', 'autres', 'tel', 'telle', 'tels', 'telles',
    'quel', 'quelle', 'quels', 'quelles', 'lequel', 'laquelle', 'lesquels', 'lesquelles',
    'duquel', 'desquels', 'desquelles', 'auquel', 'auxquels', 'auxquelles', 'dont', 'où',
    'quand', 'comment', 'pourquoi', 'combien', 'le', 'la', 'les', 'l', 'd', 'j', 'c',
    's', 'n', 'm', 't', 'qu', 'jusquo', 'quoique', 'lorsque', 'puisque', 'quoique',
    'bien', 'afin', 'tant', 'tellement', 'assez', 'trop', 'peu', 'beaucoup', 'plusieurs',
    'certains', 'certaines', 'quelque', 'quelques', 'chaque', 'nul', 'nulle', 'aucun',
    'aucune', 'tel', 'telle', 'tels', 'telles', 'même', 'mêmes', 'tout', 'toute', 'tous',
    'toutes', 'autre', 'autres', 'tel', 'telle', 'tels', 'telles', 'quel', 'quelle',
    'quels', 'quelles', 'lequel', 'laquelle', 'lesquels', 'lesquelles', 'duquel',
    'desquels', 'desquelles', 'auquel', 'auxquels', 'auxquelles', 'dont', 'où', 'quand',
    'comment', 'pourquoi', 'combien'
}


# ===== EXTRACTION DE TEXTE =====

def extract_text_from_pdf(file_path: str) -> str:
    """Extrait le texte d'un fichier PDF avec pdfplumber (meilleure qualité)."""
    # Essayer pdfplumber d'abord (meilleure extraction)
    try:
        import pdfplumber
        text_parts = []
        with pdfplumber.open(file_path) as pdf:
            for page in pdf.pages:
                page_text = page.extract_text()
                if page_text:
                    text_parts.append(page_text)
        full_text = '\n'.join(text_parts)
        logger.info(f"Extraction PDF (pdfplumber): {len(full_text)} caractères depuis {os.path.basename(file_path)}")
        if len(full_text) > 100:
            return full_text
        logger.warning(f"pdfplumber a extrait peu de texte ({len(full_text)} chars), essai avec PyPDF2")
    except Exception as e:
        logger.warning(f"pdfplumber a échoué: {e}, essai avec PyPDF2")

    # Fallback sur PyPDF2
    try:
        import PyPDF2
        text_parts = []
        with open(file_path, 'rb') as f:
            reader = PyPDF2.PdfReader(f)
            for page in reader.pages:
                page_text = page.extract_text()
                if page_text:
                    text_parts.append(page_text)
        full_text = '\n'.join(text_parts)
        logger.info(f"Extraction PDF (PyPDF2): {len(full_text)} caractères depuis {os.path.basename(file_path)}")
        return full_text
    except Exception as e:
        logger.exception(f"Erreur extraction PDF: {e}")
        return ""


def extract_text_from_video(file_path: str) -> str:
    """Extrait le texte d'une vidéo via transcription audio."""
    try:
        from moviepy.editor import VideoFileClip
        import speech_recognition as sr
        from pydub import AudioSegment

        # Extraire l'audio de la vidéo
        with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as tmp_audio:
            audio_path = tmp_audio.name

        video = VideoFileClip(file_path)
        audio = video.audio
        audio.write_audiofile(audio_path, fps=16000, nbytes=2, codec='pcm_s16le')
        video.close()
        audio.close()

        # Transcrire l'audio en texte
        recognizer = sr.Recognizer()
        with sr.AudioFile(audio_path) as source:
            audio_data = recognizer.record(source)
            try:
                text = recognizer.recognize_google(audio_data, language='fr-FR')
            except sr.UnknownValueError:
                text = ""
            except sr.RequestError:
                text = ""

        # Nettoyer le fichier temporaire
        os.unlink(audio_path)
        return text

    except Exception as e:
        logger.exception(f"Erreur extraction vidéo: {e}")
        return ""


# ===== GÉNÉRATION LOCALE (RÈGLES) =====

# Base de connaissances pour générer du contexte à partir des titres de chapitres
TITLE_KNOWLEDGE_BASE = {
    'équation': {
        'keywords': ['équation', 'résolution', 'inconnue', 'degré', 'racine', 'polynôme'],
        'context': """Les équations sont des expressions mathématiques qui établissent une égalité entre deux membres contenant une ou plusieurs inconnues.
La résolution d'une équation consiste à trouver les valeurs de l'inconnue qui rendent l'égalité vraie.
Les équations du premier degré ont la forme ax + b = 0 et admettent une unique solution.
Les équations du second degré ont la forme ax² + bx + c = 0 et peuvent admettre deux solutions.
Le discriminant Δ = b² - 4ac détermine le nombre de solutions d'une équation du second degré.
Les méthodes de résolution incluent la factorisation, la complétion du carré et l'utilisation du discriminant."""
    },
    'fonction': {
        'keywords': ['fonction', 'courbe', 'graphique', 'domaine', 'ensemble', 'image', 'antécédent'],
        'context': """Une fonction est une application qui associe à chaque élément de son domaine de définition un unique élément appelé image.
L'ensemble de définition d'une fonction est l'ensemble des valeurs pour lesquelles la fonction est définie.
La courbe représentative d'une fonction est l'ensemble des points (x, f(x)) dans un repère.
Les fonctions affines sont de la forme f(x) = ax + b et leur courbe est une droite.
Les fonctions polynômes sont de la forme f(x) = ax² + bx + c et leur courbe est une parabole.
L'étude d'une fonction comprend le calcul de la dérivée, l'étude du signe et la recherche d'extrema."""
    },
    'suite': {
        'keywords': ['suite', 'terme', 'convergence', 'limite', 'arithmétique', 'géométrique', 'raison'],
        'context': """Une suite est une fonction définie sur l'ensemble des entiers naturels.
Une suite arithmétique est définie par u(n+1) = u(n) + r où r est la raison.
Une suite géométrique est définie par u(n+1) = u(n) × q où q est la raison.
La limite d'une suite est la valeur vers laquelle tendent les termes lorsque n tend vers l'infini.
Une suite convergente admet une limite finie, une suite divergente n'admet pas de limite finie.
La somme des termes d'une suite arithmétique est donnée par S(n) = n/2 × (u(0) + u(n)).
La somme des termes d'une suite géométrique est donnée par S(n) = u(0) × (1 - q^n) / (1 - q)."""
    },
    'limite': {
        'keywords': ['limite', 'continuité', 'asymptote', 'convergence', 'infini'],
        'context': """La limite d'une fonction en un point est la valeur vers laquelle tend la fonction lorsque la variable s'approche de ce point.
Une fonction est continue en un point si sa limite en ce point est égale à sa valeur en ce point.
Les asymptotes sont des droites qui approchent indéfiniment la courbe d'une fonction.
Les limites à l'infini permettent de décrire le comportement d'une fonction aux bornes de son domaine.
Les opérations sur les limites incluent la somme, le produit, le quotient et la composition."""
    },
    'dérivée': {
        'keywords': ['dérivée', 'taux', 'variation', 'extremum', 'tangente', 'dérivation'],
        'context': """La dérivée d'une fonction mesure le taux de variation instantané de cette fonction.
La dérivée d'une fonction f en un point x est définie par la limite du taux d'accroissement.
La dérivée d'une fonction polynôme de degré n est une fonction polynôme de degré n-1.
Les règles de dérivation incluent la dérivation des sommes, produits, quotients et compositions.
Le signe de la dérivée indique le sens de variation de la fonction.
Les points où la dérivée s'annule correspondent à des extrema locaux ou des points d'inflexion."""
    },
    'intégrale': {
        'keywords': ['intégrale', 'primitive', 'aire', 'volume', 'calcul'],
        'context': """Une primitive d'une fonction est une fonction dont la dérivée est la fonction donnée.
L'intégrale d'une fonction sur un intervalle est l'aire algébrique sous la courbe de la fonction.
Le calcul intégral permet de déterminer des aires, des volumes et des longueurs.
Les méthodes d'intégration incluent l'intégration par parties et le changement de variable.
L'intégrale définie d'une fonction continue sur un intervalle est égale à la différence des primitives aux bornes.
Les propriétés de l'intégralité incluent la linéarité et l'additivité."""
    },
    'matrice': {
        'keywords': ['matrice', 'déterminant', 'système', 'linéaire', 'inverse'],
        'context': """Une matrice est un tableau rectangulaire de nombres organisé en lignes et colonnes.
Le déterminant d'une matrice carrée est un scalaire qui caractérise la matrice.
Un système d'équations linéaires peut être résolu par la méthode de Gauss ou par les matrices.
L'inverse d'une matrice carrée A est une matrice B telle que AB = BA = I.
Le rang d'une matrice est la dimension du sous-espace vectoriel engendré par ses lignes ou colonnes.
Les opérations sur les matrices incluent l'addition, la multiplication et la transposition."""
    },
    'probabilité': {
        'keywords': ['probabilité', 'aléatoire', 'variable', 'loi', 'espérance', 'variance'],
        'context': """Une probabilité mesure la chance qu'un événement se réalise, comprise entre 0 et 1.
Une variable aléatoire est une fonction qui associe un nombre réel à chaque résultat d'une expérience aléatoire.
Les lois de probabilité décrivent la répartition des probabilités sur les valeurs d'une variable aléatoire.
L'espérance mathématique d'une variable aléatoire est la moyenne pondérée des valeurs possibles.
La variance mesure la dispersion des valeurs d'une variable aléatoire autour de son espérance.
Les lois usuelles incluent la loi binomiale, la loi normale et la loi de Poisson."""
    },
    'complexe': {
        'keywords': ['complexe', 'imaginaire', 'module', 'argument', 'forme'],
        'context': """Un nombre complexe est de la forme z = a + bi où i² = -1.
Le module d'un nombre complexe z = a + bi est |z| = √(a² + b²).
L'argument d'un nombre complexe est l'angle formé par le vecteur avec l'axe réel.
La forme trigonométrique d'un nombre complexe est z = r(cos θ + i sin θ).
La forme exponentielle d'un nombre complexe est z = re^(iθ).
Les opérations sur les nombres complexes incluent l'addition, la multiplication et la division."""
    },
    'vecteur': {
        'keywords': ['vecteur', 'espace', 'base', 'dimension', 'scalaire'],
        'context': """Un vecteur est un élément d'un espace vectoriel caractérisé par sa direction, son sens et sa norme.
Un espace vectoriel est un ensemble muni d'une addition et d'une multiplication par un scalaire.
Une base d'un espace vectoriel est une famille de vecteurs qui engendre l'espace et est libre.
La dimension d'un espace vectoriel est le nombre de vecteurs dans une de ses bases.
Le produit scalaire de deux vecteurs est un scalaire qui mesure leur alignement.
Les opérations sur les vecteurs incluent l'addition, la multiplication par un scalaire et le produit scalaire."""
    },
    'polynôme': {
        'keywords': ['polynôme', 'factorisation', 'racine', 'degré', 'coefficient'],
        'context': """Un polynôme est une expression algébrique de la forme P(x) = a_n x^n + ... + a_1 x + a_0.
Le degré d'un polynôme est la plus grande puissance de x avec un coefficient non nul.
La factorisation d'un polynôme consiste à l'écrire comme produit de polynômes irréductibles.
Les racines d'un polynôme sont les valeurs de x pour lesquelles P(x) = 0.
Le théorème de factorisation affirme que tout polynôme de degré n admet exactement n racines complexes.
Les méthodes de factorisation incluent la recherche de racines évidentes et la division euclidienne."""
    },
    'nombre': {
        'keywords': ['nombre', 'réel', 'entier', 'rationnel', 'opération'],
        'context': """Les nombres réels comprennent les nombres entiers, rationnels et irrationnels.
Les nombres entiers relatifs sont ..., -2, -1, 0, 1, 2, ...
Les nombres rationnels sont de la forme p/q où p et q sont des entiers.
Les nombres irrationnels ne peuvent pas s'écrire comme une fraction de deux entiers.
Les opérations sur les nombres incluent l'addition, la soustraction, la multiplication et la division.
Les propriétés des opérations incluent la commutativité, l'associativité et la distributivité."""
    },
    'triangle': {
        'keywords': ['triangle', 'angle', 'côté', 'aire', 'périmètre'],
        'context': """Un triangle est un polygone à trois côtés et trois angles.
La somme des angles d'un triangle est toujours égale à 180 degrés.
Les triangles rectangles ont un angle droit de 90 degrés.
Le théorème de Pythagore établit que dans un triangle rectangle, le carré de l'hypoténuse est égal à la somme des carrés des deux autres côtés.
L'aire d'un triangle est donnée par A = (base × hauteur) / 2.
Le périmètre d'un triangle est la somme des longueurs de ses trois côtés."""
    },
    'cercle': {
        'keywords': ['cercle', 'rayon', 'diamètre', 'circonférence', 'aire'],
        'context': """Un cercle est l'ensemble des points situés à une distance fixe (le rayon) d'un centre.
Le diamètre d'un cercle est le double de son rayon.
La circonférence d'un cercle est donnée par C = 2πr où r est le rayon.
L'aire d'un cercle est donnée par A = πr².
Un arc de cercle est une portion de la circonférence.
Un secteur circulaire est la région délimitée par deux rayons et un arc."""
    },
    'pourcentage': {
        'keywords': ['pourcentage', 'proportion', 'taux', 'calcul'],
        'context': """Un pourcentage est une proportion exprimée sur 100.
Le calcul d'un pourcentage se fait par la forme : (partie / total) × 100.
Un taux de pourcentage indique une proportion par rapport à une quantité de référence.
Les variations en pourcentage se calculent par la forme : ((nouvelle - ancienne) / ancienne) × 100.
Les pourcentages sont utilisés pour exprimer des réductions, des augmentations et des proportions."""
    },
    'statistique': {
        'keywords': ['statistique', 'moyenne', 'médiane', 'écart-type', 'donnée'],
        'context': """La statistique est la science de la collecte et de l'analyse des données.
La moyenne arithmétique est la somme des valeurs divisée par le nombre de valeurs.
La médiane est la valeur qui sépare la série en deux parties égales.
L'écart-type mesure la dispersion des valeurs autour de la moyenne.
Un diagramme en boîte représente la distribution des données par quartiles.
Les indicateurs statistiques permettent de résumer et de comparer des séries de données."""
    },
    'géométrie': {
        'keywords': ['géométrie', 'figure', 'solide', 'volume', 'aire'],
        'context': """La géométrie étudie les propriétés des figures et des solides.
Les figures planes incluent les triangles, les quadrilatères et les cercles.
Les solides incluent les cubes, les sphères, les cylindres et les cônes.
Le volume d'un solide mesure l'espace qu'il occupe.
L'aire d'une figure plane mesure la surface qu'elle délimite.
Les transformations géométriques incluent les translations, les rotations et les symétries."""
    },
    'informatique': {
        'keywords': ['algorithme', 'programme', 'variable', 'boucle', 'condition', 'fonction', 'tableau'],
        'context': """Un algorithme est une suite finie et ordonnée d'instructions permettant de résoudre un problème.
Un programme est la traduction d'un algorithme dans un langage de programmation.
Une variable est un conteneur qui stocke une valeur modifiable pendant l'exécution d'un programme.
Les boucles permettent de répéter une suite d'instructions un certain nombre de fois.
Les conditions permettent d'exécuter des instructions différentes selon des critères.
Une fonction est un bloc d'instructions réutilisable qui peut recevoir des paramètres.
Un tableau est une structure de données qui stocke plusieurs valeurs du même type."""
    },
    'base de données': {
        'keywords': ['base', 'donnée', 'table', 'requête', 'sql', 'relation'],
        'context': """Une base de données est un ensemble organisé de données structurées.
Une table est une structure qui organise les données en lignes et en colonnes.
Une requête SQL permet de sélectionner, insérer, modifier ou supprimer des données.
Les jointures permettent de combiner des données de plusieurs tables.
Les index améliorent les performances des requêtes sur de grandes tables.
Les transactions garantissent l'intégrité des données lors des modifications."""
    },
    'réseau': {
        'keywords': ['réseau', 'protocole', 'adresse', 'ip', 'routeur', 'serveur'],
        'context': """Un réseau informatique est un ensemble d'équipements connectés pour échanger des données.
Un protocole est un ensemble de règles qui régissent la communication entre équipements.
Une adresse IP identifie de manière unique un équipement sur un réseau.
Un routeur achemine les paquets de données entre les différents réseaux.
Un serveur est un équipement qui fournit des services à d'autres équipements appelés clients.
Les modèles OSI et TCP/IP décrivent les couches de communication réseau."""
    },
    'système': {
        'keywords': ['système', 'exploitation', 'processus', 'mémoire', 'fichier'],
        'context': """Un système d'exploitation est le logiciel qui gère les ressources matérielles d'un ordinateur.
Un processus est un programme en cours d'exécution.
La mémoire vive (RAM) stocke temporairement les données et programmes en cours d'utilisation.
Un fichier est une unité de stockage nommée contenant des données.
L'ordonnanceur gère l'allocation du temps CPU entre les différents processus.
Les systèmes de fichiers organisent le stockage des fichiers sur les disques."""
    },
    'c': {
        'keywords': ['c', 'programme', 'variable', 'fonction', 'pointeur', 'tableau', 'boucle', 'condition'],
        'context': """Le langage C est un langage de programmation impératif et généraliste.
Un programme C est composé de fonctions, dont la fonction main est le point d'entrée.
Les variables en C ont un type (int, float, char, etc.) et une portée.
Les pointeurs sont des variables qui contiennent l'adresse mémoire d'une autre variable.
Les tableaux permettent de stocker plusieurs valeurs du même type.
Les boucles (for, while, do-while) permettent de répéter des instructions.
Les conditions (if, switch) permettent d'exécuter du code conditionnellement.
La gestion de la mémoire en C se fait manuellement avec malloc et free."""
    },
    'algorithme': {
        'keywords': ['algorithme', 'tri', 'recherche', 'complexité', 'big o', 'pile', 'file', 'liste'],
        'context': """Un algorithme est une suite finie et ordonnée d'instructions permettant de résoudre un problème.
Les algorithmes de tri incluent le tri à bulles, le tri par insertion, le tri rapide et le tri fusion.
Les algorithmes de recherche incluent la recherche linéaire et la recherche dichotomique.
La complexité algorithmique mesure le temps et l'espace mémoire nécessaires pour exécuter un algorithme.
La notation Big O décrit la complexité dans le pire des cas.
Une pile est une structure de données LIFO (Last In, First Out).
Une file est une structure de données FIFO (First In, First Out).
Une liste chaînée est une structure de données où chaque élément pointe vers le suivant."""
    },
    'base de données': {
        'keywords': ['base', 'donnée', 'table', 'requête', 'sql', 'relation', 'jointure', 'index'],
        'context': """Une base de données est un ensemble organisé de données structurées.
Une table est une structure qui organise les données en lignes et en colonnes.
Une requête SQL permet de sélectionner, insérer, modifier ou supprimer des données.
Les jointures permettent de combiner des données de plusieurs tables.
Les index améliorent les performances des requêtes sur de grandes tables.
Les transactions garantissent l'intégrité des données lors des modifications.
Les formes normales (1NF, 2NF, 3NF) permettent de réduire la redondance des données."""
    },
    'réseau': {
        'keywords': ['réseau', 'protocole', 'adresse', 'ip', 'routeur', 'serveur', 'tcp', 'udp', 'http'],
        'context': """Un réseau informatique est un ensemble d'équipements connectés pour échanger des données.
Le modèle OSI décrit 7 couches de communication : physique, liaison, réseau, transport, session, présentation, application.
Le modèle TCP/IP est un modèle en 4 couches utilisé sur Internet.
Une adresse IP identifie de manière unique un équipement sur un réseau.
Le protocole TCP est orienté connexion et garantit la livraison des données.
Le protocole UDP est sans connexion mais plus rapide.
Le protocole HTTP est utilisé pour le transfert de pages web.
Un routeur achemine les paquets de données entre les différents réseaux."""
    },
    'système logique': {
        'keywords': ['logique', 'booléen', 'porte', 'circuit', 'karnaugh', 'bascule', 'compteur'],
        'context': """L'algèbre de Boole est l'algèbre des valeurs logiques (0 et 1).
Les portes logiques de base sont ET (AND), OU (OR), NON (NOT), XOR, NAND, NOR.
Les tables de Karnaugh permettent de simplifier les fonctions logiques.
Les circuits combinatoires produisent une sortie qui dépend uniquement des entrées.
Les circuits séquentiels ont une mémoire et leur sortie dépend des entrées et de l'état interne.
Les bascules (RS, D, JK) sont des éléments de mémoire élémentaires.
Les compteurs comptent les impulsions d'horloge."""
    },
}


def _generate_context_from_title(chapter_title: str) -> str:
    """
    Génère du contenu pédagogique pertinent basé sur le titre du chapitre.
    Utilise une base de connaissances pour matcher les mots-clés du titre.
    """
    title_lower = chapter_title.lower()
    context_parts = [f"Chapitre: {chapter_title}", ""]

    # Chercher dans la base de connaissances
    matched_topics = []
    for topic, data in TITLE_KNOWLEDGE_BASE.items():
        if any(keyword in title_lower for keyword in data['keywords']):
            matched_topics.append(data['context'])

    if matched_topics:
        context_parts.extend(matched_topics)
    else:
        # Génération générique mais structurée avec plus de contenu
        context_parts.append(f"""Ce chapitre couvre les concepts fondamentaux et avancés du sujet : {chapter_title}.

Les étudiants doivent comprendre les principes de base, les applications pratiques,
et les relations entre les différents concepts abordés dans ce chapitre.

Points clés à maîtriser :
- Les définitions et notions fondamentales
- Les principes et règles importantes
- Les applications et cas pratiques
- Les relations entre les concepts
- Les méthodes et techniques utilisées

Objectifs d'apprentissage :
- Comprendre les concepts clés du chapitre
- Savoir appliquer les méthodes présentées
- Être capable de résoudre des exercices types
- Maîtriser les notions prérequis pour les chapitres suivants

Compétences visées :
- Analyser les problèmes liés au sujet
- Choisir la méthode appropriée
- Vérifier la validité des résultats
- Communiquer les solutions de manière claire""")

    return "\n\n".join(context_parts)

def _split_sentences(text: str) -> list[str]:
    """Découpe un texte en phrases."""
    # Nettoyer le texte
    text = re.sub(r'\s+', ' ', text).strip()
    # Découper sur les points, points d'exclamation, points d'interrogation
    sentences = re.split(r'[.!?]+', text)
    return [s.strip() for s in sentences if len(s.strip()) > 20]


def _extract_keywords(sentence: str) -> list[str]:
    """Extraie les mots-clés d'une phrase (noms, verbes, adjectifs)."""
    words = re.findall(r'\b[a-zA-ZÀ-ÿ]{4,}\b', sentence.lower())
    return [w for w in words if w not in STOP_WORDS_FR]


def _generate_distractors(correct_answer: str, all_keywords: list[str], count: int = 3) -> list[str]:
    """Génère des distracteurs (fausses réponses) à partir des mots-clés."""
    # Filtrer les mots-clés différents de la bonne réponse
    candidates = [k for k in all_keywords if k.lower() != correct_answer.lower()]
    random.shuffle(candidates)
    return candidates[:count]


def generate_questions_local(text: str, num_questions: int = 10) -> list[dict]:
    """
    Génère des QCM variés et pédagogiques à partir d'un texte.
    Utilise la base de connaissances pour créer des distracteurs logiques.
    """
    sentences = _split_sentences(text)
    logger.info(f"Génération locale: {len(sentences)} phrases trouvées")

    # Extraire tous les mots-clés du texte
    all_keywords = []
    for s in sentences:
        all_keywords.extend(_extract_keywords(s))
    all_keywords = list(set(all_keywords))

    # Détecter le sujet pour utiliser la bonne base de connaissances
    text_lower = text.lower()
    matched_context = ""
    for topic, data in TITLE_KNOWLEDGE_BASE.items():
        if any(keyword in text_lower for keyword in data['keywords']):
            matched_context = data['context']
            break

    questions = []
    used_sentences = set()

    # Type 1: Questions de définition (Qu'est-ce que...)
    definition_starters = [
        "Qu'est-ce que",
        "Comment définit-on",
        "Quelle est la définition de",
        "Que signifie",
    ]
    for starter in definition_starters:
        if len(questions) >= num_questions:
            break
        for sentence in sentences:
            if len(questions) >= num_questions:
                break
            if sentence in used_sentences:
                continue
            keywords = _extract_keywords(sentence)
            if not keywords:
                continue
            keywords.sort(key=len, reverse=True)
            target = keywords[0]
            # Créer des distracteurs logiques basés sur le contexte
            distractors = _generate_logical_distractors(target, all_keywords, matched_context, 3)
            options = [target.capitalize()] + distractors[:3]
            random.shuffle(options)
            questions.append({
                'texte': f"{starter} {target} ?",
                'options': [{'texte': o, 'est_correcte': o.lower() == target.lower()} for o in options]
            })
            used_sentences.add(sentence)
            break

    # Type 2: Questions de complétion (trou dans la phrase)
    for sentence in sentences:
        if len(questions) >= num_questions:
            break
        if sentence in used_sentences:
            continue
        keywords = _extract_keywords(sentence)
        if not keywords:
            continue
        keywords.sort(key=len, reverse=True)
        target = keywords[0]
        question_text = sentence.replace(target, '______', 1)
        if question_text == sentence:
            pattern = re.compile(re.escape(target), re.IGNORECASE)
            question_text = pattern.sub('______', sentence, count=1)
        distractors = _generate_logical_distractors(target, all_keywords, matched_context, 3)
        options = [target.capitalize()] + distractors[:3]
        random.shuffle(options)
        questions.append({
            'texte': f"Complétez : {question_text}",
            'options': [{'texte': o, 'est_correcte': o.lower() == target.lower()} for o in options]
        })
        used_sentences.add(sentence)

    # Type 3: Questions de méthode (Comment...)
    method_starters = [
        "Comment résout-on",
        "Quelle méthode permet de",
        "Par quelle technique peut-on",
        "Quelle est la procédure pour",
    ]
    for starter in method_starters:
        if len(questions) >= num_questions:
            break
        for sentence in sentences:
            if len(questions) >= num_questions:
                break
            if sentence in used_sentences:
                continue
            keywords = _extract_keywords(sentence)
            if not keywords:
                continue
            keywords.sort(key=len, reverse=True)
            target = keywords[0]
            distractors = _generate_logical_distractors(target, all_keywords, matched_context, 3)
            options = [target.capitalize()] + distractors[:3]
            random.shuffle(options)
            questions.append({
                'texte': f"{starter} {target} ?",
                'options': [{'texte': o, 'est_correcte': o.lower() == target.lower()} for o in options]
            })
            used_sentences.add(sentence)
            break

    # Type 4: Questions de relation (Quel est le lien...)
    relation_starters = [
        "Quel est le lien entre",
        "Comment s'articulent",
        "Quelle est la relation entre",
        "En quoi",
    ]
    for starter in relation_starters:
        if len(questions) >= num_questions:
            break
        for sentence in sentences:
            if len(questions) >= num_questions:
                break
            if sentence in used_sentences:
                continue
            keywords = _extract_keywords(sentence)
            if not keywords:
                continue
            keywords.sort(key=len, reverse=True)
            target = keywords[0]
            distractors = _generate_logical_distractors(target, all_keywords, matched_context, 3)
            options = [target.capitalize()] + distractors[:3]
            random.shuffle(options)
            questions.append({
                'texte': f"{starter} {target} et les autres concepts ?",
                'options': [{'texte': o, 'est_correcte': o.lower() == target.lower()} for o in options]
            })
            used_sentences.add(sentence)
            break

    # Compléter si pas assez de questions
    while len(questions) < num_questions:
        for sentence in sentences:
            if len(questions) >= num_questions:
                break
            if sentence in used_sentences:
                continue
            keywords = _extract_keywords(sentence)
            if not keywords:
                continue
            keywords.sort(key=len, reverse=True)
            target = keywords[0]
            question_text = sentence.replace(target, '______', 1)
            if question_text == sentence:
                pattern = re.compile(re.escape(target), re.IGNORECASE)
                question_text = pattern.sub('______', sentence, count=1)
            distractors = _generate_logical_distractors(target, all_keywords, matched_context, 3)
            options = [target.capitalize()] + distractors[:3]
            random.shuffle(options)
            questions.append({
                'texte': f"Identifiez le mot manquant : {question_text}",
                'options': [{'texte': o, 'est_correcte': o.lower() == target.lower()} for o in options]
            })
            used_sentences.add(sentence)

    logger.info(f"Génération locale: {len(questions)} questions créées")
    return questions[:num_questions]


def _generate_logical_distractors(correct_answer: str, all_keywords: list[str], context: str, count: int = 3) -> list[str]:
    """
    Génère des distracteurs logiques basés sur le contexte pédagogique.
    Évite les mots aléatoires sans sens.
    """
    # Extraire les mots du contexte
    context_words = re.findall(r'\b[a-zA-ZÀ-ÿ]{4,}\b', context.lower()) if context else []
    context_words = [w for w in context_words if w not in STOP_WORDS_FR and w != correct_answer.lower()]

    # Mélanger les mots du contexte
    random.shuffle(context_words)

    # Prendre les mots les plus longs (plus significatifs)
    context_words.sort(key=len, reverse=True)

    distractors = context_words[:count]

    # Si pas assez, utiliser des mots-clés du texte
    if len(distractors) < count:
        additional = [k for k in all_keywords if k.lower() != correct_answer.lower() and k not in distractors]
        random.shuffle(additional)
        distractors.extend(additional[:count - len(distractors)])

    # Si toujours pas assez, utiliser des distracteurs génériques mais logiques
    generic_distractors = [
        "Aucune de ces réponses",
        "Toutes ces réponses",
        "Ne peut être déterminé",
        "Dépend du contexte",
    ]
    while len(distractors) < count:
        distractors.append(generic_distractors[len(distractors) % len(generic_distractors)])

    return distractors[:count]


# ===== GÉNÉRATION VIA OPENAI =====

def generate_questions_ia(text: str, num_questions: int = 10, provider: str = 'groq') -> list[dict]:
    """Génère des QCM via l'IA (Groq/Llama ou OpenAI)."""
    if provider == 'groq' and GROQ_API_KEY:
        return _generate_with_groq(text, num_questions)
    elif provider == 'openai' and OPENAI_API_KEY:
        return _generate_with_openai(text, num_questions)
    else:
        logger.warning(f"Provider '{provider}' non disponible, retour à la génération locale")
        return generate_questions_local(text, num_questions)


def _generate_with_groq(text: str, num_questions: int = 10) -> list[dict]:
    """Génère des QCM via Groq (Llama)."""
    if not GROQ_API_KEY:
        logger.error("GROQ_API_KEY non définie, impossible de générer le quiz")
        return []

    try:
        from openai import OpenAI
        client = OpenAI(
            api_key=GROQ_API_KEY,
            base_url="https://api.groq.com/openai/v1"
        )

        prompt = f"""Tu es un enseignant expert. Génère exactement {num_questions} questions QCM (choix multiples) en français à partir du texte de cours suivant.

RÈGLES STRICTES :
1. Les questions doivent être DIFFICILES et porter sur les CONCEPTS CLÉS du texte (définitions, théorèmes, méthodes, propriétés, calculs)
2. Chaque question doit avoir exactement 4 options (A, B, C, D) avec UNE SEULE bonne réponse
3. Les distracteurs (fausses réponses) doivent être LOGIQUES et PERTINENTS — des erreurs courantes que les étudiants pourraient faire
4. Les questions doivent être variées : définitions, applications, calculs, interprétations, raisonnements
5. Les questions doivent tester la COMPRÉHENSION PROFONDE, pas juste la mémorisation
6. Inclus des questions qui nécessitent un RAISONNEMENT ou un CALCUL
7. Formate la réponse en JSON valide, sans texte avant ou après le JSON

Format JSON attendu (respecte EXACTEMENT ce format) :
[
  {{
    "texte": "Question difficile qui teste la compréhension ?",
    "options": [
      {{"texte": "Option A", "est_correcte": true}},
      {{"texte": "Option B", "est_correcte": false}},
      {{"texte": "Option C", "est_correcte": false}},
      {{"texte": "Option D", "est_correcte": false}}
    ]
  }}
]

Texte du cours :
{text[:8000]}
"""

        response = client.chat.completions.create(
            model=GROQ_MODEL,
            messages=[
                {"role": "system", "content": "Tu es un enseignant expert qui crée des QCM pédagogiques de qualité. Les distracteurs doivent être logiques et pertinents."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7,
            max_tokens=4000
        )

        content = response.choices[0].message.content.strip()
        logger.info(f"Réponse Groq (premiers 200 chars): {content[:200]}")

        json_match = re.search(r'\[.*\]', content, re.DOTALL)
        if json_match:
            import json
            questions = json.loads(json_match.group())
            logger.info(f"Groq a généré {len(questions)} questions")
            return questions[:num_questions]
        else:
            logger.error(f"Impossible de parser la réponse Groq. Contenu: {content[:500]}")
            return []

    except Exception as e:
        logger.exception(f"Erreur génération Groq: {e}")
        return []


def _generate_with_openai(text: str, num_questions: int = 10) -> list[dict]:
    """Génère des QCM via OpenAI."""
    try:
        from openai import OpenAI
        client = OpenAI(api_key=OPENAI_API_KEY)

        prompt = f"""Génère exactement {num_questions} questions QCM (choix multiples) en français à partir du texte suivant.
Chaque question doit avoir 4 options (A, B, C, D) avec une seule bonne réponse.
Formate la réponse en JSON valide comme ceci :

[
  {{
    "texte": "Question ?",
    "options": [
      {{"texte": "Option A", "est_correcte": true}},
      {{"texte": "Option B", "est_correcte": false}},
      {{"texte": "Option C", "est_correcte": false}},
      {{"texte": "Option D", "est_correcte": false}}
    ]
  }}
]

Texte du cours :
{text[:8000]}
"""

        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "Tu es un enseignant expert qui crée des QCM pédagogiques."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7,
            max_tokens=4000
        )

        content = response.choices[0].message.content.strip()
        json_match = re.search(r'\[.*\]', content, re.DOTALL)
        if json_match:
            import json
            questions = json.loads(json_match.group())
            return questions
        else:
            logger.error("Impossible de parser la réponse OpenAI")
            return generate_questions_local(text, num_questions)

    except Exception as e:
        logger.exception(f"Erreur génération OpenAI: {e}")
        return generate_questions_local(text, num_questions)


# ===== POINT D'ENTRÉE PRINCIPAL =====

def generate_quiz_from_chapter(
    pdf_files: list[str],
    video_files: list[str],
    num_questions: int = 10,
    method: str = 'auto',
    provider: str = 'groq',
    chapter_title: str = ''
) -> list[dict]:
    """
    Génère un quiz à partir des fichiers PDF et vidéo d'un chapitre.
    Si aucun fichier n'est fourni, utilise le titre du chapitre comme contexte.

    Args:
        pdf_files: Liste des chemins vers les fichiers PDF
        video_files: Liste des chemins vers les fichiers vidéo
        num_questions: Nombre de questions à générer
        method: 'auto' (local), 'openai' ou 'groq'
        provider: 'groq' ou 'openai' (utilisé si method != 'auto')
        chapter_title: Titre du chapitre (utilisé si aucun fichier)

    Returns:
        Liste de questions avec leurs options
    """
    # Extraire tout le texte des sources
    full_text = ""

    for pdf_path in pdf_files:
        text = extract_text_from_pdf(pdf_path)
        full_text += text + "\n\n"

    for video_path in video_files:
        text = extract_text_from_video(video_path)
        full_text += text + "\n\n"

    # Vérifier qu'on a assez de texte pour générer des questions
    if len(full_text.strip()) < 200:
        logger.warning(f"Texte extrait trop court ({len(full_text.strip())} chars), enrichissement avec le titre")
        if chapter_title:
            full_text = _generate_context_from_title(chapter_title)
        else:
            logger.warning("Aucun texte extrait et aucun titre de chapitre fourni")
            return []

    # Générer les questions UNIQUEMENT avec Groq (pas de méthode locale)
    logger.info(f"Génération de {num_questions} questions avec Groq")
    logger.info(f"GROQ_API_KEY définie: {bool(GROQ_API_KEY)}")

    if not GROQ_API_KEY:
        logger.error("GROQ_API_KEY non définie, impossible de générer le quiz")
        return []

    questions = generate_questions_ia(full_text, num_questions, provider='groq')

    logger.info(f"{len(questions)} questions générées")
    return questions
