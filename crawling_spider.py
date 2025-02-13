import requests
from bs4 import BeautifulSoup
from urllib.parse import urlparse, parse_qs
import os
import re
import threading
import time
from collections import deque
from concurrent.futures import ThreadPoolExecutor, as_completed

# --- Paramètres API AllDebrid ---
API_KEY = "EnterAPIkeyHERE"
REDIRECTOR_URL = "http://api.alldebrid.com/v4/link/redirector"
UNLOCK_URL = "http://api.alldebrid.com/v4/link/unlock"

# --- Rate Limiter ---
class RateLimiter:
    def __init__(self, max_calls_per_second, max_calls_per_minute):
        self.max_calls_per_second = max_calls_per_second
        self.max_calls_per_minute = max_calls_per_minute
        self.lock = threading.Lock()
        self.calls_second = deque()
        self.calls_minute = deque()

    def wait(self):
        with self.lock:
            now = time.time()
            # Éliminer les anciens appels (plus d'1 seconde ou 60 secondes)
            while self.calls_second and now - self.calls_second[0] > 1:
                self.calls_second.popleft()
            while self.calls_minute and now - self.calls_minute[0] > 60:
                self.calls_minute.popleft()
            wait_time = 0
            if len(self.calls_second) >= self.max_calls_per_second:
                wait_time = max(wait_time, 1 - (now - self.calls_second[0]))
            if len(self.calls_minute) >= self.max_calls_per_minute:
                wait_time = max(wait_time, 60 - (now - self.calls_minute[0]))
            if wait_time > 0:
                time.sleep(wait_time)
                now = time.time()
            self.calls_second.append(now)
            self.calls_minute.append(now)

# Instance globale de RateLimiter
rate_limiter = RateLimiter(12, 600)

def get_redirect_link(link):
    """
    Appelle l'endpoint /v4/link/redirector pour obtenir le lien de redirection.
    Retourne le premier lien de la liste renvoyée par l'API.
    """
    rate_limiter.wait()
    headers = {"Authorization": f"Bearer {API_KEY}"}
    files = {"link": (None, link)}
    try:
        response = requests.post(REDIRECTOR_URL, headers=headers, files=files)
        response.raise_for_status()
        data = response.json()
        if data.get("status") == "success" and "data" in data:
            links_list = data["data"].get("links", [])
            if links_list:
                return links_list[0]
            else:
                print(f"[Redirector] Réponse sans lien: {data}")
                return None
        else:
            print(f"[Redirector] Échec de la conversion: {data}")
            return None
    except Exception as e:
        print(f"[Redirector] Erreur pour {link}: {e}")
        return None

def unlock_link(link):
    """
    Appelle l'endpoint /v4/link/unlock avec le lien fourni (celui obtenu via le redirector)
    pour obtenir le lien débriadé final.
    """
    rate_limiter.wait()
    headers = {"Authorization": f"Bearer {API_KEY}"}
    files = {"link": (None, link)}
    try:
        response = requests.post(UNLOCK_URL, headers=headers, files=files)
        response.raise_for_status()
        data = response.json()
        if data.get("status") == "success" and "data" in data and data["data"].get("link"):
            return data["data"]["link"]
        else:
            print(f"[Unlock] Échec pour {link}: {data}")
            return None
    except Exception as e:
        print(f"[Unlock] Erreur pour {link}: {e}")
        return None

def convert_dlprotect_link(link):
    """
    Si le lien contient "dl-protect.link", effectue la procédure en deux étapes :
      1. Appel à /v4/link/redirector pour obtenir le lien de redirection.
      2. Appel à /v4/link/unlock avec le lien de redirection.
    Sinon, tente directement de débriader le lien.
    """
    if "dl-protect.link" in link:
        print(f"Conversion du lien dl-protect: {link}")
        redirect_link = get_redirect_link(link)
        if redirect_link:
            print(f"  Lien de redirection obtenu: {redirect_link}")
            final_link = unlock_link(redirect_link)
            return final_link
        else:
            print("  Échec lors de l'obtention du lien de redirection.")
            return None
    else:
        return unlock_link(link)

def fetch_links_by_provider(url, providers):
    """
    Récupère les liens depuis la page Wawacity et les regroupe par provider.
    Retourne un dictionnaire du type :
      { '1fichier': [lien1, lien2, ...],
        'Rapidgator': [lien1, lien2, ...],
         ... }
    """
    try:
        response = requests.get(url)
        response.raise_for_status()
    except requests.RequestException as e:
        print(f"Erreur lors de la récupération de la page : {e}")
        return None

    soup = BeautifulSoup(response.text, 'html.parser')
    links_by_provider = {provider: [] for provider in providers}
    for row in soup.find_all('tr'):
        provider_cell = row.find('td', class_='text-center')
        if provider_cell:
            prov = provider_cell.text.strip()
            if prov in providers:
                link_tag = row.find('a', rel="external nofollow")
                if link_tag:
                    href = link_tag.get('href')
                    if href:
                        links_by_provider[prov].append(href)
    return links_by_provider

def process_episode(episode_index, links_by_provider, providers_order):
    """
    Traite un épisode (déduit par son index dans chaque liste de provider).
    Pour cet épisode, tente les providers dans l'ordre jusqu'à obtenir un lien débriadé.
    Retourne le lien débriadé ou None.
    """
    for provider in providers_order:
        links = links_by_provider.get(provider, [])
        if episode_index < len(links):
            raw_link = links[episode_index]
            print(f"Épisode {episode_index+1} - Essai de {provider}: {raw_link}")
            converted = convert_dlprotect_link(raw_link)
            if converted:
                print(f"Épisode {episode_index+1} - {provider} réussi: {converted}")
                return converted
            else:
                print(f"Épisode {episode_index+1} - {provider} échoué.")
    print(f"Aucun lien fonctionnel trouvé pour l'épisode {episode_index+1}.")
    return None

def process_links_by_episode(links_by_provider, providers_order):
    """
    Traite les épisodes en parallèle.
    Retourne une liste de liens débriadés (dans l'ordre des épisodes).
    """
    max_episodes = max(len(links_by_provider[prov]) for prov in providers_order if prov in links_by_provider)
    final_links = [None] * max_episodes
    with ThreadPoolExecutor(max_workers=12) as executor:
        futures = {executor.submit(process_episode, i, links_by_provider, providers_order): i for i in range(max_episodes)}
        for future in as_completed(futures):
            idx = futures[future]
            result = future.result()
            final_links[idx] = result
    return final_links

def save_links_in_packets(directory, base_file_name, links, packet_size=20):
    """
    Divise la liste de liens en paquets de 'packet_size' liens et
    sauvegarde chaque paquet dans un fichier distinct dans le répertoire donné.
    """
    os.makedirs(directory, exist_ok=True)
    num_packets = (len(links) + packet_size - 1) // packet_size
    for i in range(num_packets):
        chunk = links[i * packet_size:(i + 1) * packet_size]
        file_name = f"{base_file_name}_packet_{i+1}.txt"
        file_path = os.path.join(directory, file_name)
        with open(file_path, 'w', encoding='utf-8') as f:
            for link in chunk:
                f.write(link + "\n")
        print(f"Paquet {i+1} sauvegardé dans {file_path}")

def save_original_links_to_file(directory, file_name, links_by_provider):
    """
    Sauvegarde les liens originaux (non convertis) dans un fichier, regroupés par provider.
    """
    os.makedirs(directory, exist_ok=True)
    file_path = os.path.join(directory, file_name)
    with open(file_path, 'w', encoding='utf-8') as f:
        for provider, links in links_by_provider.items():
            f.write(f"{provider} :\n")
            for link in links:
                f.write(link + "\n")
            f.write("\n")
    print(f"Les liens originaux ont été sauvegardés dans {file_path}")

def main():
    # Ordre dans lequel essayer les providers
    providers_order = ['1fichier', 'Rapidgator', 'Fikper', 'Turbobit', 'Nitroflare', 'Uptobox']
    urls = []
    print("Entrez les URLs (tapez 'done' pour terminer) :")
    while True:
        url_input = input("URL: ").strip()
        if url_input.lower() == 'done':
            break
        urls.append(url_input)
    
    # Demande si l'utilisateur veut générer des paquets de 20 liens débriadés (mode global par série)
    packet_option = input("Voulez-vous générer des paquets de 20 liens débriadés (global, par série) ? (O/n) [par défaut O] : ").strip().lower()
    use_packets = True if packet_option == "" or packet_option in ["o", "oui", "yes"] else False

    # Dictionnaire pour stocker les liens débriadés par série (mode global)
    series_to_links = {}
    base_directory = "Downloaded_Links"
    
    # Traitement de chaque URL (chaque URL correspond à une saison)
    for url in urls:
        query = urlparse(url).query
        params = parse_qs(query)
        serie_id = params['id'][0] if 'id' in params else 'unknown'
        # Extraction du nom de la série (on ignore la partie "-saison")
        match = re.compile(r'(\D+)').search(serie_id)
        generic_name = match.group(1).strip('-').replace('-saison', '') if match else 'unknown'
        
        print(f"\n=== Traitement de la saison '{serie_id}' de la série '{generic_name}' ===")
        links_by_provider = fetch_links_by_provider(url, providers_order)
        if links_by_provider:
            season_dir = os.path.join(base_directory, generic_name)
            original_file = serie_id + ".txt"
            save_original_links_to_file(season_dir, original_file, links_by_provider)
            
            final_links = process_links_by_episode(links_by_provider, providers_order)
            if final_links:
                # Mode global : ajouter les liens débriadés à la liste de la série
                if generic_name not in series_to_links:
                    series_to_links[generic_name] = []
                series_to_links[generic_name].extend([link for link in final_links if link])
            else:
                print("Aucun lien fonctionnel n'a été trouvé après conversion pour cette saison.")
        else:
            print(f"Aucun lien trouvé ou erreur lors de la récupération des liens pour l'URL {url}")
    
    if use_packets:
        # Pour chaque série, créer des fichiers par paquets de 20 liens dans le sous-dossier de la série.
        for series, links in series_to_links.items():
            series_dir = os.path.join(base_directory, series)
            if links:
                base_file_name = f"{series}_alldebrid"
                save_links_in_packets(series_dir, base_file_name, links, packet_size=20)
            else:
                print(f"Aucun lien débriadé trouvé pour la série {series}.")
    else:
        # Sinon, pour chaque série, créer un seul fichier regroupant tous les liens débriadés.
        for series, links in series_to_links.items():
            series_dir = os.path.join(base_directory, series)
            file_name = f"{series}_alldebrid.txt"
            file_path = os.path.join(series_dir, file_name)
            with open(file_path, 'w', encoding='utf-8') as f:
                for link in links:
                    f.write(link + "\n")
            print(f"Fichier complet sauvegardé dans {file_path}")

if __name__ == "__main__":
    main()
