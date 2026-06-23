import requests
import re

# Verified global sports sources on GitHub
SPORTS_INDEX_URLS = [
    "https://raw.githubusercontent.com/freetv-org/freetv/main/playlists/playlist_bd.m3u",
    "https://raw.githubusercontent.com/LaneSh4d0w/warcraft-iptv/main/warcraft-sports.m3u",
    "https://raw.githubusercontent.com/itsToggle/tvheadend-profiles/main/bengali_sports.m3u",
    "https://raw.githubusercontent.com/MochaSuri/IPTV-Channels/main/sports.m3u"
]

def extract_unique_sports_links():
    print("Searching and scraping verified sports links from high-uptime sources...")
    raw_links = [] # Master list to store all discovered links

    for url in SPORTS_INDEX_URLS:
        try:
            headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
            response = requests.get(url, headers=headers, timeout=12)
            if response.status_code == 200:
                # Scrapes all HTTP/HTTPS stream URLs from the current source
                found_links = re.findall(r'(https?://[^\s"\'\>]+)', response.text)
                raw_links.extend(found_links) # Appends into the master list
        except Exception as e:
            print(f"Skipping source due to timeout/error: {url} | Details: {e}")

    # Clean query parameters, trailing tags and filter streaming protocols
    filtered_links = []
    for link in raw_links:
        clean_url = link.strip().split('#')[0].split('"')[0].split("'")[0]
        if any(ext in clean_url.lower() for ext in ['.m3u8', '.ts', '.mpd', '/live', '/stream']):
            filtered_links.append(clean_url)

    # Filter and keep UNIQUE links only (Removes all duplicate links from the master list)
    unique_links = list(set(filtered_links))
    print(f"Total links crawled in master list: {len(raw_links)}")
    print(f"Total UNIQUE streams left after deduplication: {len(unique_links)}")
    return unique_links

def is_stream_live(url):
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
    try:
        # Fast HEAD request validation
        response = requests.head(url, headers=headers, timeout=3, allow_redirects=True)
        if response.status_code in [200, 201, 206]:
            return True
    except:
        # Strict GET fallback for tokenized streaming servers
        try:
            response = requests.get(url, headers=headers, timeout=3, stream=True)
            if response.status_code in [200, 201, 206]:
                return True
        except:
            pass
    return False

def main():
    # Fetching the deduplicated unique master list
    unique_sports_urls = extract_unique_sports_links()
    valid_streams = []

    print("Validating streams against strict response codes...")
    for count, url in enumerate(unique_sports_urls):
        # Cap the valid list to 120 streams to optimize workflow speed
        if len(valid_streams) >= 120:
            print("Target reached (120 active channels). Wrapping up playlist.")
            break

        if is_stream_live(url):
            print(f"[LIVE] -> {url}")
            valid_streams.append(url)

    # Compile and generate the clean unique sports.m3u8 playlist
    if valid_streams:
        with open("sports.m3u8", "w", encoding="utf-8") as f:
            f.write("#EXTM3U\n")
            for i, stream_url in enumerate(valid_streams):
                f.write(f"#EXTINF:-1 tvg-id='Sports-{i+1}' tvg-name='Sports {i+1}',Live Sports {i+1}\n")
                f.write(f"{stream_url}\n")
        print(f"Successfully generated sports.m3u8 with {len(valid_streams)} unique working streams!")
    else:
        print("No active streams passed the validation filter.")

if __name__ == "__main__":
    main()
