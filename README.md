# AllDebrid Wawacity Link Converter & Packager 🚀🔗

This Python script automatically fetches download links from Wawacity pages, converts them using the AllDebrid API (including dl‑protect links), and then groups the converted links by series into packets of 20 links (optionally). 🎉

---

## Table of Contents 📑

- [Description](#description)
- [Features](#features)
- [Prerequisites](#prerequisites)
- [Installation](#installation)
- [Usage](#usage)
  - [Season Mode](#season-mode)
  - [Global Mode (Packets by Series)](#global-mode-packets-by-series)
- [How It Works](#how-it-works)
  - [Link Extraction](#link-extraction)
  - [Conversion via AllDebrid](#conversion-via-alldebrid)
  - [Parallel Processing & Rate Limiting](#parallel-processing--rate-limiting)
  - [Link Grouping](#link-grouping)
- [Limitations](#limitations)
- [Contact / Support](#contact--support)

---

## Description 📝

This script is designed to automate the retrieval and conversion of download links from Wawacity. It extracts links for each episode from multiple providers (e.g., 1fichier, Rapidgator, Fikper, Turbobit, Nitroflare, Uptobox) and uses the AllDebrid API to convert (or "debrid") these links. 

For dl‑protect links, the script performs a two-step process:  
1. **Step 1:** It calls the `/v4/link/redirector` endpoint to get a redirection link.  
2. **Step 2:** It then calls the `/v4/link/unlock` endpoint with that redirection link to obtain the final debrided link.

The script also offers an option to group the debrided links into packets of 20 per series, making management and distribution easier. 📦✨

---

## Features ✨

- **Automatic Extraction** of links from a Wawacity page.
- **Conversion** of links via the AllDebrid API (supports dl‑protect links). 🔄
- **Parallel Processing** with multithreading to speed up conversion while respecting API rate limits.
- **Rate Limiting**: Ensures no more than 12 requests per second and 600 requests per minute.
- **Global Grouping Option**: Option to group all debrided links by series and generate files with 20 links per packet.
- **Saving Output**: Stores both the original and debrided links in a directory structure (e.g., `Downloaded_Links/<series_name>`). 💾

---

## Prerequisites ✅

- **Python 3.6+**
- Python packages:  
  - `requests`  
  - `beautifulsoup4`  
- Internet connection to access Wawacity pages and the AllDebrid API.
- A valid AllDebrid API Key (configured in the script). 🔑

---

## Installation 🛠️

1. **Clone or Download** this repository to your machine.
2. **Install the required packages** by running:

   ```bash
   pip install requests beautifulsoup4
   ```

3. **Configure** your AllDebrid API Key by editing the `API_KEY` variable in the script.

---

## Usage 🚀

Run the script from the command line:

```bash
python script.py
```

### Season Mode

- When you **do not choose** the global packets option, the script processes each URL (each representing a season) separately.
- The original and debrided links are saved in a folder named after the series (e.g., `Downloaded_Links/series_name`).

### Global Mode (Packets by Series)

- If you opt to generate packets of 20 debrided links, the script will group all debrided links from all seasons of the same series.
- For each series, within the folder `Downloaded_Links/<series_name>`, files will be created containing 20 links per packet (e.g., `series_name_alldebrid_packet_1.txt`, etc.). 📦

---

## How It Works 🔍

### Link Extraction

The script uses BeautifulSoup to parse the Wawacity page (HTML) and extract table rows (`<tr>`). It then groups the links by provider based on predefined provider names.

### Conversion via AllDebrid

- **Normal Link:**  
  For standard links, the script calls the `/v4/link/unlock` endpoint directly.
- **dl‑protect Link:**  
  For links containing `dl-protect.link`, the script:
  1. Calls `/v4/link/redirector` to get a redirection link.
  2. Uses the redirection link with `/v4/link/unlock` to obtain the final debrided link.

### Parallel Processing & Rate Limiting ⏱️

- **ThreadPoolExecutor:**  
  The script processes each episode in parallel using multiple threads (up to 12 at a time).
- **Rate Limiter:**  
  A custom rate limiter ensures that no more than **12 requests/second** and **600 requests/minute** are sent, in accordance with AllDebrid API limits.

### Link Grouping 📂

- **Season Mode:**  
  Links are saved per season in directories named after the series.
- **Global Mode (Packets):**  
  Links are accumulated per series and split into packets of 20, with each packet saved in its own file within the series folder.

---

## Limitations ⚠️

- **API Rate Limits:**  
  Although the script enforces rate limiting, processing a large number of URLs might still take some time.
- **Wawacity HTML Structure:**  
  If the Wawacity page structure changes, the BeautifulSoup parsing may need adjustments.
- **API Errors:**  
  In the event of unexpected API errors, the script will print error messages accordingly.

---

## Contact / Support 📞

If you encounter any issues or have suggestions for improvements, please open an issue or contact me directly.

---

Enjoy using the script! Happy debriding! 😄🔥
