import os
import re
import time
import m3u8
import subprocess
import logging
import requests
from config import USER_ID, AUTHORIZATION, HOST
from Crypto.Cipher import AES

# Set logging level
logging.basicConfig(level=logging.INFO)

# HTTP headers for Parmar Academy API
HEADERS = {
    "Authorization": AUTHORIZATION,
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/133.0.0.0 Safari/537.36",
    "Origin": "https://www.parmaracademy.in",
    "Referer": "https://www.parmaracademy.in/",
    "Sec-Ch-Ua-Platform": "Windows",
    "Auth-Key": "appxapi",
    "Client-Service": "Appx",
    "Accept": "*/*",
    "Accept-Language": "en-US,en;q=0.9",
    "Accept-Encoding": "gzip, deflate, br"
}

# -------------------------------
# API functions to retrieve course info
# -------------------------------
def get_all_purchases():
    """Retrieve list of courses."""
    res = requests.get(HOST + "/get/courselist?exam_name=&start=0", headers=HEADERS).json()
    return res["data"]

def get_titles(course_id, start=-1):
    """Retrieve list of subjects for a course."""
    res = requests.get(HOST + f"/get/allsubjectfrmlivecourseclass?courseid={course_id}&start={start}", headers=HEADERS).json()
    return res["data"]

def get_titles_of_topic(course_id, subject_id):
    """Retrieve list of topics for a subject."""
    res = requests.get(HOST + f"/get/alltopicfrmlivecourseclass?courseid={course_id}&subjectid={subject_id}&start=-1", headers=HEADERS).json()
    return res["data"]

def get_all_video_links(course_id, subject_id, topic_id):
    """Retrieve list of video links for a topic."""
    res = requests.get(
        HOST + f"/get/livecourseclassbycoursesubtopconceptapiv3?courseid={course_id}&subjectid={subject_id}&topicid={topic_id}&conceptid=&windowsapp=false&start=-1",
        headers=HEADERS
    ).json()
    return res["data"]

def get_video_token(course_id, video_id):
    """Retrieve video token used to fetch video player HTML."""
    res = requests.get(
        HOST + f"/get/fetchVideoDetailsById?course_id={course_id}&video_id={video_id}&ytflag=0&folder_wise_course=0",
        headers=HEADERS
    ).json()
    return res["data"]["video_player_token"]

def get_video_html(token):
    """Retrieve HTML of video player using the token."""
    res = requests.get(f"https://player.akamai.net.in/secure-player?token={token}&watermark=").text
    return res

# -------------------------------
# Downloading and merging video segments (default concatenation)
# -------------------------------
def download_video(course, subject, topic, video, output_dir):
    """
    Downloads all segments of the selected video via the m3u8 playlist,
    then merges them by concatenating the downloaded segment files.
    Returns the merged video file path.
    """
    course_id = course['id']
    video_id = video['id']
    token = get_video_token(course_id, video_id)
    html = get_video_html(token)
    
    # Adjust HTML content: fix relative URLs and quality settings
    html = html.replace('src="/', 'src="https://www.parmaracademy.in/')
    html = html.replace('href="/', 'href="https://www.parmaracademy.in/')
    html = html.replace('"quality":"360p","isPremier":', '"quality":"720p","isPremier":')

    # Save HTML for debugging purposes
    html_file = os.path.join(output_dir, f"{video['Title']}.html")
    with open(html_file, "w", encoding="utf-8") as f:
        f.write(html)

    # Extract m3u8 URL from the HTML content
    m = re.search(r'(https://.*?\.m3u8)', html)
    if m:
        m3u8_url = m.group(1)
    else:
        logging.error("m3u8 URL not found in HTML")
        return None

    logging.info(f"Found m3u8 URL: {m3u8_url}")
    
    # Load the m3u8 playlist
    playlist = m3u8.load(m3u8_url)
    segment_dir = os.path.join(output_dir, "segments")
    os.makedirs(segment_dir, exist_ok=True)
    segment_files = []
    
    # Download every segment in the playlist sequentially
    for idx, segment in enumerate(playlist.segments):
        segment_url = segment.uri
        segment_file = os.path.join(segment_dir, f"segment_{idx}.ts")
        segment_files.append(segment_file)
        for attempt in range(5):
            try:
                r = requests.get(segment_url, headers=HEADERS, timeout=15)
                r.raise_for_status()
                with open(segment_file, "wb") as f:
                    f.write(r.content)
                break
            except Exception as e:
                logging.warning(f"Error downloading segment {idx}, attempt {attempt+1}: {e}")
                time.sleep(2)
    
    # Merge segments by concatenating the files
    cleaned_title = re.sub(r'\W', '', video['Title'])
    merged_file = os.path.join(output_dir, f"{cleaned_title}.mp4")
    temp_file = merged_file + ".bak"
    with open(temp_file, "wb") as output:
        for seg in segment_files:
            with open(seg, "rb") as f:
                output.write(f.read())
            os.remove(seg)
    os.rename(temp_file, merged_file)
    logging.info(f"Video merged into: {merged_file}")
    return merged_file

def check_video_playable(video_file):
    """
    Uses ffprobe to verify that the merged video contains a valid video stream.
    Returns True if playable.
    """
    cmd = [
        "ffprobe", "-v", "error", "-select_streams", "v:0",
        "-show_entries", "stream=codec_name", "-of", "default=noprint_wrappers=1:nokey=1", video_file
    ]
    result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    output = result.stdout.decode('utf-8').strip()
    return bool(output)
