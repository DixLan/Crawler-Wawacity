import requests
from bs4 import BeautifulSoup
from urllib.parse import urlparse, parse_qs
import os
import re

def fetch_links_by_provider(url, providers):
    try:
        response = requests.get(url)
        response.raise_for_status()
    except requests.RequestException as e:
        print(f"Erreur lors de la récupération de la page: {e}")
        return None

    soup = BeautifulSoup(response.text, 'html.parser')
    links_by_provider = {provider: [] for provider in providers}

    for row in soup.find_all('tr'):
        provider_cell = row.find('td', class_='text-center')
        if provider_cell and provider_cell.text.strip() in providers:
            link_tag = row.find('a', rel="external nofollow")
            if link_tag:
                href = link_tag.get('href')
                if href:
                    links_by_provider[provider_cell.text.strip()].append(href)

    return links_by_provider

def save_links_to_file(directory, file_name, links_by_provider):
    if not os.path.exists(directory):
        os.makedirs(directory)
    file_path = os.path.join(directory, file_name)
    with open(file_path, 'w', encoding='utf-8') as file:
        for provider, links in links_by_provider.items():
            file.write(f"{provider} :\n")
            for link in links:
                file.write(f"{link}\n")
            file.write("\n")

providers = ['1fichier', 'Rapidgator', 'Fikper', 'Turbobit', 'Nitroflare', 'Uptobox']

urls = []
print("Entrez les URLs (tapez 'done' pour terminer) :")
while True:
    url_input = input("URL : ")
    if url_input.lower() == 'done':
        break
    urls.append(url_input)

base_directory = "Downloaded_Links"

# Expression régulière pour extraire la partie générique du nom de la série
pattern = re.compile(r'(\D+)')  # Extrait les caractères non numériques

for url in urls:
    query = urlparse(url).query
    params = parse_qs(query)
    serie_id = params['id'][0] if 'id' in params else 'unknown'
    # Appliquer l'expression régulière pour extraire le nom générique
    match = pattern.search(serie_id)
    generic_name = match.group(1).strip('-').replace('-saison', '') if match else 'unknown'

    directory_path = os.path.join(base_directory, generic_name)

    links_by_provider = fetch_links_by_provider(url, providers)
    if links_by_provider:
        save_links_to_file(directory_path, serie_id + ".txt", links_by_provider)
        print(f"Les liens ont été sauvegardés dans le fichier {os.path.join(directory_path, serie_id + '.txt')}")
    else:
        print(f"Aucun lien trouvé ou erreur lors de la récupération des liens pour l'URL {url}")
