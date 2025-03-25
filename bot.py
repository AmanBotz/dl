# bot.py
import os
import re
import time
import threading
import requests
from pyrogram import Client, filters
from pyrogram.types import Message
from config import BOT_TOKEN, API_ID, API_HASH, USER_ID, AUTHORIZATION
from downloader import handle_download_start

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
    html = html.replace('"quality":"360p","isPremier":', '"quality":"720p","isPremier":')
    return html

app = Client("parmar_bot", bot_token=BOT_TOKEN, api_id=API_ID, api_hash=API_HASH)

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
        sent_msg = message.reply_text(f"Selected video: {selected_video['Title']}\nStarting download...")
        # For full video download, pass max_segment=0
        threading.Thread(target=process_video_download, args=(chat_id, sent_msg, state, 0)).start()
        state.clear()

def process_video_download(chat_id: int, sent_msg, state, max_seg):
    print("[Bot] Starting video download process.")
    course_id = state["selected_course"]["id"]
    video_id = state["selected_video"]["id"]
    video_title = re.sub(r'\W', '', state["selected_video"]["Title"])
    print(f"[Bot] Video title: {video_title}")
    token = get_video_token(course_id, video_id)
    print("[Bot] Retrieved video token.")
    html = get_video_html(token)
    print("[Bot] Retrieved video HTML.")
    if "Token Expired" in html:
        sent_msg.reply_text("Token expired. Please try again later.")
        return
    output_file = f"{video_title}"
    print("[Bot] Initiating download via downloader module.")
    result = handle_download_start(html, isFile=False, output_file=output_file, max_thread=5, max_segment=max_seg)
    if result and os.path.exists(result):
        sent_msg.reply_text("Download complete! Sending video...")
        print(f"[Bot] Download complete. Sending video: {result}")
        app.send_video(chat_id, result, caption=video_title)
    else:
        sent_msg.reply_text("Failed to download video.")
        print("[Bot] Failed to download video.")

def run_bot():
    app.run()

if __name__ == "__main__":
    run_bot()
