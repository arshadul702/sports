import requests
import re
from concurrent.futures import ThreadPoolExecutor, as_completed

# Target sources including subcontinent and global sports focus
TARGET_SOURCES = [
    "https://raw.githubusercontent.com/freetv-org/freetv/main/playlists/playlist_bd.m3u",
    "https://raw.githubusercontent.com/LaneSh4d0w/warcraft-iptv/main/warcraft-sports.m3u",
    "https://github.com/SpwR/iptv/tree/master",
    "https://github.com/moesope/iptv/tree/master"
]

# Strict sports keywords to keep inside the final pool
SPORTS_KEYWORDS = [
    'sports', 'cricket', 'football', 'sony', 'star', 't-sports', 'gtv', 'ghazi', 
    'willow', 'supersport', 'ten', 'ptv', 'espn', 'sky', 'beinsports', 'astro', 
    'live-sports', 'match', 'ipl', 't20', 'fifa', 'champions', 'gazi'
]

def smart_crawl_github():
    print("🤖 Scanning target sources for live sports databases...")
    raw_file_urls = []
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
    
    for url in TARGET_SOURCES:
        url_clean = url.strip()
        if "raw.githubusercontent.com" in url_clean:
            raw_file_urls.append(url_clean)
            continue
            
        try:
            response = requests.get(url_clean, headers=headers, timeout=12)
            if response.status_code != 200:
                continue
                
            if "/blob/" in url_clean:
                raw_url = url_clean.replace("github.com", "raw.githubusercontent.com").replace("/blob/", "/")
                raw_file_urls.append(raw_url)
            elif "/tree/" in url_clean or url_clean.count('/') <= 4:
                all_paths = re.findall(r'href="([^"]+)"', response.text)
                for path in all_paths:
                    if "/blob/" in path and any(ext in path.lower() for ext in ['.m3u', '.m3u8']):
                        raw_url = f"https://raw.githubusercontent.com{path}".replace("/blob/", "/")
                        raw_file_urls.append(raw_url)
        except Exception as e:
            print(f"❌ Failed processing target {url_clean}: {e}")
            
    return list(set(raw_file_urls))

def process_and_filter_sources():
    all_raw_files = smart_crawl_github()
    print(f"📋 Total parsed raw playlist files to scan: {len(all_raw_files)}")
    
    master_channel_pool = []
    
    for count, file_url in enumerate(all_raw_files):
        if count >= 30: 
            break
        try:
            headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
            response = requests.get(file_url, headers=headers, timeout=8)
            if response.status_code == 200:
                lines = response.text.split('\n')
                current_name = "Live Sports Channel"
                
                for line in lines:
                    line = line.strip()
                    if line.startswith('#EXTINF:'):
                        # Extract the actual channel name after the last comma
                        match_name = re.search(r',\s*(.*)$', line)
                        if match_name:
                            current_name = match_name.group(1).strip()
                        else:
                            current_name = line
                    elif line.startswith('http://') or line.startswith('https://'):
                        clean_url = line.split('#')[0].split('"')[0].split("'")[0]
                        
                        # Phase 1: Filter by file extension stability
                        if any(ext in clean_url.lower() for ext in ['.m3u8', '.ts', '.mpd', '/live', '/stream']):
                            # Phase 2: Check if name or link belongs to sports
                            link_match = any(keyword in clean_url.lower() for keyword in SPORTS_KEYWORDS)
                            name_match = any(keyword in current_name.lower() for keyword in SPORTS_KEYWORDS)
                            
                            if link_match or name_match:
                                master_channel_pool.append({
                                    'name': current_name,
                                    'url': clean_url
                                })
                        current_name = "Live Sports Channel" # Reset for fallback
        except Exception as e:
            print(f"Error parsing file {file_url}: {e}")

    print(f"📊 Extracted total streams from all sources: {len(master_channel_pool)}")

    # Phase 3: Smart Deduplication (Removes exact duplicates, keeps backup links with same name)
    unique_channel_pool = []
    seen_pairs = set()
    
    for item in master_channel_pool:
        # Create a signature using both name and URL to catch true identical entries
        pair_signature = (item['name'].lower(), item['url'].lower())
        if pair_signature not in seen_pairs:
            seen_pairs.add(pair_signature)
            unique_channel_pool.append(item)

    print(f"🎯 Total UNIQUE items left for validation (Backups retained): {len(unique_channel_pool)}")
    return unique_channel_pool

def is_stream_live(channel_obj):
    url = channel_obj['url']
    name = channel_obj['name']
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
    try:
        response = requests.head(url, headers=headers, timeout=2, allow_redirects=True)
        if response.status_code in [200, 201, 206]:
            return channel_obj, True
    except:
        try:
            response = requests.get(url, headers=headers, timeout=2, stream=True)
            if response.status_code in [200, 201, 206]:
                return channel_obj, True
        except:
            pass
    return channel_obj, False

def main():
    filtered_channel_pool = process_and_filter_sources()
    valid_streams = []
    max_channels = 150 
    
    print(f"⚡ Validating streams with high-speed Multi-threading (25 workers)...")
    
    with ThreadPoolExecutor(max_workers=25) as executor:
        future_to_channel = {executor.submit(is_stream_live, item): item for item in filtered_channel_pool}
        
        for future in as_completed(future_to_channel):
            if len(valid_streams) >= max_channels:
                break
                
            try:
                channel_obj, is_live = future.result()
                if is_live:
                    print(f"⚽ [LIVE] {channel_obj['name']} -> {channel_obj['url']}")
                    valid_streams.append(channel_obj)
            except:
                pass

    if valid_streams:
        with open("sports.m3u8", "w", encoding="utf-8") as f:
            f.write("#EXTM3U\n")
            for i, stream in enumerate(valid_streams):
                # Using the real scraped channel name directly into the output playlist
                clean_name = stream['name'].replace('"', '').replace("'", "")
                f.write(f"#EXTINF:-1 tvg-id='Sports-{i+1}' tvg-name='{clean_name}',{clean_name}\n")
                f.write(f"{stream['url']}\n")
        print(f"✅ Success! sports.m3u8 updated with {len(valid_streams)} clean unique sports streams including backup options.")
    else:
        print("❌ No active sports streams passed network checking criteria.")

if __name__ == "__main__":
    main()
