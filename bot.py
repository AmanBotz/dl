# bot.py
import os
import re
import time
import threading
import json
import subprocess
import requests
from pyrogram import Client, filters
from pyrogram.types import Message
from config import BOT_TOKEN, API_ID, API_HASH, USER_ID, AUTHORIZATION, MAX_THREADS
from downloader import handle_download_start, extract_quality_options

# Initialize Pyrogram Client immediately so decorators work.
app = Client("parmar_bot", bot_token=BOT_TOKEN, api_id=API_ID, api_hash=API_HASH)

# Helper functions for metadata extraction
def run_cmd(cmd):
    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, universal_newlines=True)
    lines = []
    while True:
        line = proc.stdout.readline()
        if not line:
            break
        lines.append(line.strip())
    proc.wait()
    return proc.returncode, "\n".join(lines)

def ffprobe_info(filepath):
    cmd = [
        "ffprobe", "-v", "quiet",
        "-print_format", "json",
        "-show_streams",
        filepath
    ]
    code, out = run_cmd(cmd)
    if code != 0:
        return None, None, None
    try:
        info = json.loads(out)
        for s in info.get("streams", []):
            if s.get("codec_type") == "video":
                dur = float(s.get("duration", 0.0))
                w = s.get("width", 0)
                h = s.get("height", 0)
                return dur, w, h
    except Exception as e:
        print(f"[Bot] ffprobe error: {e}")
    return None, None, None

def extract_thumbnail(filepath, thumb_path):
    cmd = [
        "ffmpeg", "-y",
        "-i", filepath,
        "-ss", "1",
        "-vframes", "1",
        thumb_path
    ]
    code, out = run_cmd(cmd)
    if code != 0 or not os.path.exists(thumb_path):
        return None
    return thumb_path

BASE_URL = "https://parmaracademyapi.classx.co.in"
user_state = {}

def get_all_courses():
    url = f"{BASE_URL}/get/courselist?exam_name=&start=0"
    response = requests.get(url, headers={
        "Authorization": AUTHORIZATION,
        "User-Agent": "Mozilla/5.0",
        "Origin": "https://www.parmaracademy.in",
        "Referer": "https://www.parmaracademy.in/",
        "Auth-Key": "appxapi",
    })
    return response.json()["data"]

def get_subjects(course_id):
    url = f"{BASE_URL}/get/allsubjectfrmlivecourseclass?courseid={course_id}&start=-1"
    response = requests.get(url, headers={
        "Authorization": AUTHORIZATION,
        "User-Agent": "Mozilla/5.0",
        "Origin": "https://www.parmaracademy.in",
        "Referer": "https://www.parmaracademy.in/",
        "Auth-Key": "appxapi",
    })
    return response.json()["data"]

def get_topics(course_id, subject_id):
    url = f"{BASE_URL}/get/alltopicfrmlivecourseclass?courseid={course_id}&subjectid={subject_id}&start=-1"
    response = requests.get(url, headers={
        "Authorization": AUTHORIZATION,
        "User-Agent": "Mozilla/5.0",
        "Origin": "https://www.parmaracademy.in",
        "Referer": "https://www.parmaracademy.in/",
        "Auth-Key": "appxapi",
    })
    return response.json()["data"]

def get_videos(course_id, subject_id, topic_id):
    url = (f"{BASE_URL}/get/livecourseclassbycoursesubtopconceptapiv3?"
           f"courseid={course_id}&subjectid={subject_id}&topicid={topic_id}&conceptid=&windowsapp=false&start=-1")
    response = requests.get(url, headers={
        "Authorization": AUTHORIZATION,
        "User-Agent": "Mozilla/5.0",
        "Origin": "https://www.parmaracademy.in",
        "Referer": "https://www.parmaracademy.in/",
        "Auth-Key": "appxapi",
    })
    return response.json()["data"]

def get_video_token(course_id, video_id):
    url = f"{BASE_URL}/get/fetchVideoDetailsById?course_id={course_id}&video_id={video_id}&ytflag=0&folder_wise_course=0"
    response = requests.get(url, headers={
        "Authorization": AUTHORIZATION,
        "User-Agent": "Mozilla/5.0",
        "Origin": "https://www.parmaracademy.in",
        "Referer": "https://www.parmaracademy.in/",
        "Auth-Key": "appxapi",
    })
    return response.json()["data"]["video_player_token"]

def get_video_html(token):
    url = f"https://player.akamai.net.in/secure-player?token={token}&watermark="
    response = requests.get(url)
    html = response.text
    html = html.replace('src="/', 'src="https://www.parmaracademy.in/')
    html = html.replace('href="/', 'href="https://www.parmaracademy.in/')
    return html

@app.on_message(filters.command("start"))
def start_handler(client, message: Message):
    chat_id = message.chat.id
    user_state[chat_id] = {"step": "course"}
    courses = get_all_courses()
    text = "Select a course:\n"
    for idx, course in enumerate(courses, start=1):
        text += f"{idx}. {course['course_name']}\n"
    user_state[chat_id]["courses"] = courses
    message.reply_text(text)

@app.on_message(filters.text & ~filters.regex(r"^/"))
def text_handler(client, message: Message):
    chat_id = message.chat.id
    if chat_id not in user_state:
        message.reply_text("Please send /start to begin.")
        return
    state = user_state[chat_id]
    try:
        choice = int(message.text.strip())
    except ValueError:
        message.reply_text("Please send a valid number corresponding to the option.")
        return

    if state["step"] == "course":
        courses = state.get("courses", [])
        if not (1 <= choice <= len(courses)):
            message.reply_text("Invalid course number. Try again.")
            return
        selected_course = courses[choice - 1]
        state["selected_course"] = selected_course
        state["step"] = "subject"
        subjects = get_subjects(selected_course["id"])
        state["subjects"] = subjects
        text = f"Selected course: {selected_course['course_name']}\nSelect a subject:\n"
        for idx, subj in enumerate(subjects, start=1):
            text += f"{idx}. {subj['subject_name']}\n"
        message.reply_text(text)
    elif state["step"] == "subject":
        subjects = state.get("subjects", [])
        if not (1 <= choice <= len(subjects)):
            message.reply_text("Invalid subject number. Try again.")
            return
        selected_subject = subjects[choice - 1]
        state["selected_subject"] = selected_subject
        state["step"] = "topic"
        topics = get_topics(state["selected_course"]["id"], selected_subject["subjectid"])
        state["topics"] = topics
        text = f"Selected subject: {selected_subject['subject_name']}\nSelect a topic:\n"
        for idx, topic in enumerate(topics, start=1):
            text += f"{idx}. {topic['topic_name']}\n"
        message.reply_text(text)
    elif state["step"] == "topic":
        topics = state.get("topics", [])
        if not (1 <= choice <= len(topics)):
            message.reply_text("Invalid topic number. Try again.")
            return
        selected_topic = topics[choice - 1]
        state["selected_topic"] = selected_topic
        state["step"] = "video"
        videos = get_videos(state["selected_course"]["id"],
                            state["selected_subject"]["subjectid"],
                            selected_topic["topicid"])
        videos = [v for v in videos if v["material_type"] == "VIDEO"]
        if not videos:
            message.reply_text("No videos found for this topic.")
            state.clear()
            return
        state["videos"] = videos
        text = f"Selected topic: {selected_topic['topic_name']}\nSelect a video:\n"
        for idx, video in enumerate(videos, start=1):
            text += f"{idx}. {video['Title']}\n"
        message.reply_text(text)
    elif state["step"] == "video":
        videos = state.get("videos", [])
        if not (1 <= choice <= len(videos)):
            message.reply_text("Invalid video number. Try again.")
            return
        selected_video = videos[choice - 1]
        state["selected_video"] = selected_video
        token = get_video_token(state["selected_course"]["id"], selected_video["id"])
        html = get_video_html(token)
        decoded_data, quality_list = extract_quality_options(html)
        if not quality_list:
            state["video_html"] = html
            state["quality_data"] = None
            state["selected_quality_index"] = 0
            state["step"] = "download"
            message.reply_text("No quality options found, proceeding with default.")
            process_video_download(chat_id, state)
        else:
            text = "Select quality:\n"
            for idx, q in enumerate(quality_list, start=1):
                text += f"{idx}. {q}\n"
            state["video_html"] = html
            state["quality_data"] = decoded_data
            state["quality_options"] = quality_list
            state["step"] = "quality"
            message.reply_text(text)
    elif state["step"] == "quality":
        quality_options = state.get("quality_options", [])
        if not (1 <= choice <= len(quality_options)):
            message.reply_text("Invalid quality number. Try again.")
            return
        state["selected_quality_index"] = choice - 1
        state["step"] = "download"
        message.reply_text(f"Selected quality: {quality_options[choice-1]}\nStarting download...")
        process_video_download(chat_id, state)
    elif state["step"] == "download":
        message.reply_text("Processing download...")

def process_video_download(chat_id: int, state):
    print("[Bot] Starting video download process.")
    course_id = state["selected_course"]["id"]
    video_id = state["selected_video"]["id"]
    video_title = re.sub(r'\W', '', state["selected_video"]["Title"])
    print(f"[Bot] Video title: {video_title}")
    html = state.get("video_html")
    if not html:
        print("[Bot] Error: No video HTML found.")
        return
    quality_index = state.get("selected_quality_index", 0)
    output_file = f"{video_title}"
    print(f"[Bot] Initiating download via downloader module using quality index {quality_index}.")
    # Set max_segment=50 to download only the first 50 segments for testing.
    result = handle_download_start(html, isFile=False, output_file=output_file, max_thread=MAX_THREADS, max_segment=50, quality_index=quality_index)
    if result and os.path.exists(result):
        duration, width, height = ffprobe_info(result)
        if duration is None:
            duration = 0
        if width is None:
            width = 640
        if height is None:
            height = 360
        send_duration = int(duration)
        if send_duration < 1:
            send_duration = 1
        thumb_path = os.path.join(os.getcwd(), "temp_thumb.jpg")
        thumb = extract_thumbnail(result, thumb_path)
        try:
            app.send_video(
                chat_id=chat_id,
                video=result,
                caption=video_title,
                duration=send_duration,
                width=width,
                height=height,
                thumb=thumb,
                supports_streaming=True
            )
        except Exception as e:
            app.send_message(chat_id=chat_id, text=f"Error sending video: {e}")
            print(f"[Bot] Error sending video: {e}")
        if thumb and os.path.exists(thumb):
            os.remove(thumb)
    else:
        app.send_message(chat_id=chat_id, text="Failed to download video.")
        print("[Bot] Failed to download video.")

def run_bot():
    app.run()

if __name__ == "__main__":
    run_bot()
