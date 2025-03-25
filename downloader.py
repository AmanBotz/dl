# downloader.py
import re
import json
import time
import os
import base64
import hashlib
import requests
import m3u8
import threading
import subprocess
from base64 import b64decode
from Crypto.Cipher import AES

def get_data_enc_key(time_val, token):
    n = time_val[-4:]
    r = int(n[0])
    i = int(n[1:3])
    o = int(n[3])
    a = time_val + token[r:i]
    s = hashlib.sha256()
    s.update(a.encode('utf-8'))
    c = s.digest()
    if o == 6:
        sign = c[:16]
    elif o == 7:
        sign = c[:24]
    else:
        sign = c
    key = base64.b64encode(sign).decode('utf-8')
    print("[Downloader] Data encryption key generated.")
    return key

def decrypt_data(data, key, ivb):
    try:
        i = b64decode(key)
        o = b64decode(ivb)
        a = b64decode(data)
        cipher = AES.new(i, AES.MODE_CBC, o)
        l = cipher.decrypt(a)
        dec = l.decode('utf-8')
        print("[Downloader] Data decrypted successfully.")
        return dec
    except Exception as e:
        print(f"[Downloader] Error in decrypt_data: {e}")
        raise

def decode_video_tsa(input_string):
    shift_value = 0xa * 0x2
    result = ''
    for char in input_string:
        result += chr(ord(char) - shift_value)
    return base64.b64decode(result)

def decode_video_tsb(input_string):
    xor_value = 0x3
    shift_value = 0x2a
    result = ''
    for char in input_string:
        result += chr((ord(char) >> xor_value) ^ shift_value)
    return base64.b64decode(result)

def decode_video_tsc(input_string):
    shift_value = 0xa
    result = ''
    for char in input_string:
        result += chr(ord(char) - shift_value)
    return base64.b64decode(result)

def decode_video_tsd(input_string):
    shift_value = 0x2
    result = ''
    for char in input_string:
        result += chr(ord(char) >> shift_value)
    return base64.b64decode(result)

def decode_video_tse(input_string):
    xor_value = 0x3
    shift_value = 0x2a
    result = ''
    for char in input_string:
        result += chr((ord(char) ^ shift_value) >> xor_value)
    return base64.b64decode(result)

def get_file_extension(url):
    match = re.search(r'\.\w+$', url)
    if match:
        return match.group(0)[1:]
    return None

def download_and_decrypt_segment(segment_url, key=None, iv=None, output_path=None, bit=7):
    if os.path.exists(output_path):
        print(f"[Downloader] Segment already exists: {output_path}")
        return
    attempt = 0
    segment_data = None
    while attempt < 5:
        try:
            print(f"[Downloader] Downloading segment: {segment_url} (Attempt {attempt+1})")
            response = requests.get(segment_url, stream=True, timeout=15)
            response.raise_for_status()
            segment_data = response.content
            break
        except Exception as e:
            print(f"[Downloader] Error downloading segment {segment_url}: {e}")
            attempt += 1
            time.sleep(2)
    if not segment_data:
        print(f"[Downloader] Skipping segment {segment_url} after 5 failed attempts.")
        return
    ext = get_file_extension(segment_url)
    if ext == "tsa":
        segment_data = decode_video_tsa(segment_data.decode("utf-8"))
    elif ext == "tsb":
        segment_data = decode_video_tsb(segment_data.decode("utf-8"))
    elif ext == "tsc":
        segment_data = decode_video_tsc(segment_data.decode("utf-8"))
    elif ext == "tsd":
        segment_data = decode_video_tsd(segment_data.decode("utf-8"))
    elif ext == "tse":
        segment_data = decode_video_tse(segment_data.decode("utf-8"))
    try:
        cipher = AES.new(key, AES.MODE_CBC, iv)
        segment_data = cipher.decrypt(segment_data)
    except Exception as e:
        print(f"[Downloader] Error decrypting segment {segment_url}: {e}")
        return
    try:
        with open(output_path + ".bak", "wb") as f:
            f.write(segment_data)
        os.rename(output_path + ".bak", output_path)
        print(f"[Downloader] Segment saved: {output_path}")
    except Exception as e:
        print(f"[Downloader] Error saving segment {segment_url}: {e}")

def download_m3u8_playlist(playlist, output_file, key, directory, max_thread=1, max_segment=0):
    print(f"[Downloader] Starting download of m3u8 playlist with {len(playlist.segments)} segments.")
    os.makedirs(directory, exist_ok=True)
    if not playlist.segments:
        raise ValueError("No segments found in the playlist")
    segment_files = []
    for i in range(0, len(playlist.segments), max_thread):
        threads = []
        batch = playlist.segments[i:i + max_thread]
        for j, segment in enumerate(batch):
            if max_segment and (i + j) >= max_segment:
                break
            segment_url = segment.uri
            segment_file = f"segment_{i+j}.ts"
            segment_files.append(segment_file)
            iv = None
            if segment.key and segment.key.method == "AES-128":
                iv = bytes.fromhex(segment.key.iv[2:]) if segment.key.iv else None
            t = threading.Thread(target=download_and_decrypt_segment, args=(segment_url, key, iv, directory + segment_file))
            threads.append(t)
            t.start()
        for t in threads:
            t.join()
        if max_segment and (i + len(batch)) >= max_segment:
            break
    segment_files = sorted(segment_files, key=lambda f: int(re.search(r'_(\d+)\.ts$', f).group(1)))
    print("[Downloader] Combining segments in sorted order...")
    try:
        combined_ts = output_file + ".ts"
        with open(combined_ts + ".bak", "wb") as output:
            for segment_file in segment_files:
                seg_path = directory + segment_file
                if os.path.exists(seg_path):
                    with open(seg_path, "rb") as seg:
                        output.write(seg.read())
                    os.remove(seg_path)
                else:
                    print(f"[Downloader] Warning: Missing segment file {seg_path}.")
        os.rename(combined_ts + ".bak", combined_ts)
        print(f"[Downloader] Combined TS file saved as {combined_ts}")
    except Exception as e:
        print(f"[Downloader] Error combining segments: {e}")
        return None

    final_output = output_file + ".mp4"
    try:
        print(f"[Downloader] Converting {combined_ts} to {final_output} using FFmpeg...")
        # New command: re-encode the combined TS file into MP4
        subprocess.run([
            "ffmpeg", "-y", "-i", combined_ts,
            "-c:v", "libx264", "-preset", "veryfast", "-crf", "28",
            "-c:a", "aac", "-b:a", "128k",
            final_output
        ], check=True)
        print(f"[Downloader] Video converted successfully into {final_output}")
        os.remove(combined_ts)
        return final_output
    except Exception as e:
        print(f"[Downloader] Error converting video: {e}")
        return combined_ts

def extract_quality_options(html):
    print("[Downloader] Extracting quality options from HTML.")
    pattern = r'<script(.*?) id="__NEXT_DATA__"(.*?)>(.*?)</script>'
    match = re.search(pattern, html, re.DOTALL)
    if not match:
        print("[Downloader] No JSON data found in HTML.")
        return None, None
    json_content = match.group(3).strip()
    try:
        decoded = json.loads(json_content)["props"]["pageProps"]
    except Exception as e:
        print(f"[Downloader] Error decoding JSON: {e}")
        return None, None
    urls = decoded.get("urls")
    if not urls:
        return None, None
    quality_list = [item.get("quality", "unknown") for item in urls]
    return decoded, quality_list

def handle_download_start(html, isFile=False, output_file="", max_thread=1, max_segment=0, quality_index=None):
    print("[Downloader] Starting handle_download_start.")
    pattern = r'<script(.*?) id="__NEXT_DATA__"(.*?)>(.*?)</script>'
    if isFile:
        with open(html, "r") as f:
            html = f.read()
    match = re.search(pattern, html, re.DOTALL)
    if match:
        json_content = match.group(3).strip()
        try:
            decoded = json.loads(json_content)["props"]["pageProps"]
        except Exception as e:
            print(f"[Downloader] Error decoding JSON: {e}")
            return None
        datetime_val = decoded.get("datetime")
        token = decoded.get("token")
        iv = decoded.get("ivb6")
        urls = decoded.get("urls")
        if not (datetime_val and token and iv and urls):
            print("[Downloader] Missing required fields in JSON data.")
            return None
        data_dec_key = get_data_enc_key(datetime_val, token)
        if quality_index is not None and quality_index < len(urls):
            chosen = urls[quality_index]
        else:
            chosen = urls[0]
        quality = chosen.get("quality", "unknown")
        output_file = output_file + " " + quality
        if os.path.exists(output_file + ".mp4") or os.path.exists(output_file + ".ts"):
            print(f"[Downloader] Video already downloaded: {output_file}")
            return output_file + ".mp4" if os.path.exists(output_file + ".mp4") else output_file + ".ts"
        try:
            kstr = chosen.get("kstr")
            jstr = chosen.get("jstr")
            video_dec_key = decrypt_data(kstr, data_dec_key, iv)
            video_dec_key = base64.b64decode(video_dec_key)
            video_m3u8 = decrypt_data(jstr, data_dec_key, iv)
        except Exception as e:
            print(f"[Downloader] Error during decryption of keys/playlist: {e}")
            return None
        print("[Downloader] Parsing m3u8 playlist.")
        playlist = m3u8.loads(video_m3u8)
        result = download_m3u8_playlist(playlist, output_file, video_dec_key, ".temp/", max_thread, max_segment)
        return result
    else:
        print("[Downloader] Failed to extract JSON data from HTML.")
        return None
