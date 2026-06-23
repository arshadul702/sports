import requests
import re

# input whatever you want: can be a direct file, a folder tree, or main repo URL
TARGET_SOURCES = [
    "https://raw.githubusercontent.com/Free-TV/IPTV/refs/heads/master/playlist.m3u8",
    "https://github.com/iptv-org/iptv/commit/fb466a2221e6c62b1a9385e10d1bd2c4b17eb698.patch",
	"https://github.com/iptv-org/iptv/tree/db97f9431e072b3d7e67224103e25148c7ed96ef/streams",
]

def smart_crawl_github():
    print("🤖 Starting Smart GitHub URL analyzer...")
    raw_file_urls = []
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
    
    for url in TARGET_SOURCES:
        url_clean = url.strip()
        
        # 1. Condition: If it's already a direct raw usercontent file link
        if "raw.githubusercontent.com" in url_clean:
            raw_file_urls.append(url_clean)
            continue
            
        try:
            response = requests.get(url_clean, headers=headers, timeout=15)
            if response.status_code != 200:
                print(f"⚠️ Could not access URL: {url_clean} (Status: {response.status_code})")
                continue
                
            # If the URL contains '/blob/', it's a single file view on GitHub
            if "/blob/" in url_clean:
                print(f"📄 Target is a FILE: {url_clean}")
                raw_url = url_clean.replace("github.com", "raw.githubusercontent.com").replace("/blob/", "/")
                raw_file_urls.append(raw_url)
                
            # If the URL contains '/tree/' or is the main repository root, it's a FOLDER
            elif "/tree/" in url_clean or url_clean.count('/') <= 4:
                print(f"📁 Target is a FOLDER: {url_clean}")
                # Extract all internal paths mentioned inside the page HTML
                all_paths = re.findall(r'href="([^"]+)"', response.text)
                
                for path in all_paths:
                    # Filter paths that strictly signify a FILE extension inside the repo view
                    if "/blob/" in path and any(ext in path.lower() for ext in ['.m3u', '.m3u8']):
                        raw_url = f"https://raw.githubusercontent.com{path}".replace("/blob/", "/")
                        raw_file_urls.append(raw_url)
            else:
                # Fallback check for direct streams or unformatted source endpoints
                raw_file_urls.append(url_clean)
                
        except Exception as e:
            print(f"❌ Failed processing target {url_clean}: {e}")
            
    # Deduplicate the master raw file collection
    return list(set(raw_file_urls))

def extract_unique_sports_links():
    # Fetching parsed raw file targets dynamically
    all_raw_files = smart_crawl_github()
    print(f"📋 Total parsed raw playlist files to scan: {len(all_raw_files)}")
    
    raw_links = [] # Master list for all discovered playlist lines

    # Read content line by line from all files
    for count, file_url in enumerate(all_raw_files):
        if count >= 40: # Safety boundary condition for GitHub Actions runtime limit
            break
        try:
            headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
            response = requests.get(file_url, headers=headers, timeout=10)
            if response.status_code == 200:
                found_links = re.findall(r'(https?://[^\s"\'\>]+)', response.text)
                raw_links.extend(found_links)
        except:
            pass

    # Filtering valid stream format types
    filtered_links = []
    for link in raw_links:
        clean_url = link.strip().split('#')[0].split('"')[0].split("'")[0]
        if any(ext in clean_url.lower() for ext in ['.m3u8', '.ts', '.mpd', '/live', '/stream']) or "sports" in clean_url.lower():
            filtered_links.append(clean_url)

    # REMOVE DUPLICATES - Deduplicating master stream list
    unique_links = list(set(filtered_links))
    print(f"📊 Total raw streams scraped: {len(raw_links)}")
    print(f"🎯 Total UNIQUE streams left for verification: {len(unique_links)}")
    return unique_links

def is_stream_live(url):
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
    try:
        # Fast validation using network HEAD request
        response = requests.head(url, headers=headers, timeout=3, allow_redirects=True)
        if response.status_code in [200, 201, 206]:
            return True
    except:
        try:
            # Fallback strict validation using streaming GET channel response
            response = requests.get(url, headers=headers, timeout=3, stream=True)
            if response.status_code in [200, 201, 206]:
                return True
        except:
            pass
    return False

def main():
    unique_sports_urls = extract_unique_sports_links()
    valid_streams = []

    print("⚡ Starting high-speed validation on unique streams...")
    for count, url in enumerate(unique_sports_urls):
        if len(valid_streams) >= 150: # Caps final playlist channel output boundary
            print("Maximum target capacity reached (150 active lines). Saving file.")
            break

        if is_stream_live(url):
            print(f"[LIVE] -> {url}")
            valid_streams.append(url)

    # Output generation
    if valid_streams:
        with open("sports.m3u8", "w", encoding="utf-8") as f:
            f.write("#EXTM3U\n")
            for i, stream_url in enumerate(valid_streams):
                f.write(f"#EXTINF:-1 tvg-id='Sports-{i+1}' tvg-name='Sports {i+1}',Live Sports {i+1}\n")
                f.write(f"{stream_url}\n")
        print(f"✅ Success! sports.m3u8 updated with {len(valid_streams)} clean unique active streams.")
    else:
        print("❌ Script closed. No streams passed active network filters.")

if __name__ == "__main__":
    main()
