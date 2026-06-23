import requests
import re
from concurrent.futures import ThreadPoolExecutor, as_completed

# Target URLs: Can be a folder tree, a direct raw file, or main repo URL
TARGET_SOURCES = [

    "https://github.com/abusaeeidx/IPTV-Scraper-Zilla",
]

def smart_crawl_github():
    print("🤖 Starting Smart GitHub URL analyzer...")
    raw_file_urls = []
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
    
    for url in TARGET_SOURCES:
        url_clean = url.strip()
        if "raw.githubusercontent.com" in url_clean:
            raw_file_urls.append(url_clean)
            continue
            
        try:
            response = requests.get(url_clean, headers=headers, timeout=15)
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
            else:
                raw_file_urls.append(url_clean)
        except Exception as e:
            print(f"❌ Failed processing target {url_clean}: {e}")
            
    return list(set(raw_file_urls))

def extract_unique_sports_links():
    all_raw_files = smart_crawl_github()
    print(f"📋 Total parsed raw playlist files to scan: {len(all_raw_files)}")
    
    # Step 1: Create a raw master list combining ALL data from ALL sources first
    all_scraped_entries = [] 

    for count, file_url in enumerate(all_raw_files):
        if count >= 40:
            break
        try:
            headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
            response = requests.get(file_url, headers=headers, timeout=10)
            if response.status_code == 200:
                lines = response.text.splitlines()
                current_name = "Live Sports"
                
                for line in lines:
                    line = line.strip()
                    if line.startswith("#EXTINF"):
                        name_match = line.split(",")[-1]
                        if name_match:
                            current_name = name_match.strip()
                    elif line.startswith("http://") or line.startswith("https://"):
                        # Append raw uncleaned pair to the master bundle
                        all_scraped_entries.append((line, current_name))
                        current_name = "Live Sports"
        except Exception as e:
            print(f"Error parsing file {file_url}: {e}")

    print(f"📊 Total raw entries scraped in Master List: {len(all_scraped_entries)}")

    # Step 2: Clean parameters, normalize URLs, and enforce STRICT Deduplication
    unique_channels = {}
    for raw_url, name in all_scraped_entries:
        # Strict cleaning: remove linebreaks, trailing spaces, query variables or tokens
        clean_url = raw_url.strip().split('#')[0].split('?')[0].split('"')[0].split("'")[0].strip()
        
        # Lowercase check for extensions to ensure it's a valid live stream
        url_lower = clean_url.lower()
        if any(ext in url_lower for ext in ['.m3u8', '.ts', '.mpd', '/live', '/stream']) or "sports" in url_lower:
            # Using clean_url as key completely guarantees uniqueness across all sources
            if clean_url not in unique_channels:
                unique_channels[clean_url] = name

    print(f"🎯 Total strict UNIQUE streams left for verification: {len(unique_channels)}")
    return unique_channels

def is_stream_live(url, name):
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
    try:
        response = requests.head(url, headers=headers, timeout=3, allow_redirects=True)
        if response.status_code in [200, 201, 206]:
            return url, name, True
    except:
        try:
            response = requests.get(url, headers=headers, timeout=3, stream=True)
            if response.status_code in [200, 201, 206]:
                return url, name, True
        except:
            pass
    return url, name, False

def main():
    # Fetching strictly deduplicated unique channel dictionary
    unique_channels = extract_unique_sports_links()
    valid_streams = []
    
    print(f"⚡ Starting high-speed Multi-threaded validation (25 concurrent workers)...")
    print(f"🔄 Scanning 100% of the deduplicated master list...")
    
    with ThreadPoolExecutor(max_workers=25) as executor:
        future_to_url = {executor.submit(is_stream_live, url, name): url for url, name in unique_channels.items()}
        
        for future in as_completed(future_to_url):
            try:
                url, name, is_live = future.result()
                if is_live:
                    print(f"[LIVE] -> {name}")
                    valid_streams.append((url, name))
            except Exception as e:
                pass

    # Output playlist generation (Writes clean results at once)
    if valid_streams:
        with open("playlists.m3u8", "w", encoding="utf-8") as f:
            f.write("#EXTM3U\n")
            for i, (stream_url, channel_name) in enumerate(valid_streams):
                f.write(f"#EXTINF:-1 tvg-id='Sports-{i+1}' tvg-name='{channel_name}',{channel_name}\n")
                f.write(f"{stream_url}\n")
        print(f"✅ Success! playlists.m3u8 updated with {len(valid_streams)} 100% unique live streams.")
    else:
        print("❌ Script closed. No streams passed active network filters.")

if __name__ == "__main__":
    main()
