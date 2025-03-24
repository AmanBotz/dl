import os
import re
import logging
from pyrogram import Client, filters
from config import API_ID, API_HASH, BOT_TOKEN
import downloader

# Set logging level
logging.basicConfig(level=logging.INFO)

# In-memory conversation state. In production, consider a persistent store.
conversations = {}

def reset_conversation(chat_id):
    conversations[chat_id] = {"state": "START"}

# Initialize Pyrogram client.
app = Client("parmar_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

# /start command: begin the conversation.
@app.on_message(filters.command("start"))
def start_cmd(client, message):
    chat_id = message.chat.id
    reset_conversation(chat_id)
    message.reply_text("Welcome to the Parmar Academy Video Downloader Bot.\nFetching courses list, please wait...")
    courses = downloader.get_all_purchases()
    if not courses:
        message.reply_text("No courses found at the moment.")
        return
    conversations[chat_id]["state"] = "COURSE"
    conversations[chat_id]["courses"] = courses
    reply = "Please choose a course by sending its number:\n"
    for idx, course in enumerate(courses, start=1):
        reply += f"{idx}. {course['course_name']}\n"
    message.reply_text(reply)

# Handle numeric replies for course, subject, topic, and video selection.
@app.on_message(filters.text & ~filters.command())
def handle_reply(client, message):
    chat_id = message.chat.id
    if chat_id not in conversations:
        reset_conversation(chat_id)
        message.reply_text("Session restarted. Please use /start to begin.")
        return

    ctx = conversations[chat_id]
    state = ctx.get("state", "START")
    text = message.text.strip()

    if not text.isdigit():
        message.reply_text("Please reply with a valid number.")
        return

    num = int(text)

    if state == "COURSE":
        courses = ctx.get("courses", [])
        if num < 1 or num > len(courses):
            message.reply_text("Invalid course number. Try again.")
            return
        selected_course = courses[num - 1]
        ctx["selected_course"] = selected_course
        ctx["state"] = "SUBJECT"
        subjects = downloader.get_titles(selected_course['id'])
        if not subjects:
            message.reply_text("No subjects found for this course. Please /start again.")
            reset_conversation(chat_id)
            return
        ctx["subjects"] = subjects
        reply = f"Selected course: {selected_course['course_name']}\nNow choose a subject:\n"
        for idx, subj in enumerate(subjects, start=1):
            reply += f"{idx}. {subj['subject_name']}\n"
        message.reply_text(reply)
        return

    if state == "SUBJECT":
        subjects = ctx.get("subjects", [])
        if num < 1 or num > len(subjects):
            message.reply_text("Invalid subject number. Try again.")
            return
        selected_subject = subjects[num - 1]
        ctx["selected_subject"] = selected_subject
        ctx["state"] = "TOPIC"
        course_id = ctx["selected_course"]["id"]
        topics = downloader.get_titles_of_topic(course_id, selected_subject['subjectid'])
        if not topics:
            message.reply_text("No topics found for this subject. Please /start again.")
            reset_conversation(chat_id)
            return
        ctx["topics"] = topics
        reply = f"Selected subject: {selected_subject['subject_name']}\nNow choose a topic:\n"
        for idx, topic in enumerate(topics, start=1):
            reply += f"{idx}. {topic['topic_name']}\n"
        message.reply_text(reply)
        return

    if state == "TOPIC":
        topics = ctx.get("topics", [])
        if num < 1 or num > len(topics):
            message.reply_text("Invalid topic number. Try again.")
            return
        selected_topic = topics[num - 1]
        ctx["selected_topic"] = selected_topic
        ctx["state"] = "VIDEO"
        course_id = ctx["selected_course"]["id"]
        subject_id = ctx["selected_subject"]["subjectid"]
        videos = downloader.get_all_video_links(course_id, subject_id, selected_topic['topicid'])
        videos = [v for v in videos if v.get("material_type") == "VIDEO"]
        if not videos:
            message.reply_text("No videos found for this topic. Please /start again.")
            reset_conversation(chat_id)
            return
        ctx["videos"] = videos
        reply = f"Selected topic: {selected_topic['topic_name']}\nNow choose a video:\n"
        for idx, video in enumerate(videos, start=1):
            reply += f"{idx}. {video['Title']}\n"
        message.reply_text(reply)
        return

    if state == "VIDEO":
        videos = ctx.get("videos", [])
        if num < 1 or num > len(videos):
            message.reply_text("Invalid video number. Try again.")
            return
        selected_video = videos[num - 1]
        ctx["selected_video"] = selected_video
        message.reply_text(f"Downloading video: {selected_video['Title']}\nPlease wait... This might take a while.")
        course = ctx["selected_course"]
        subject = ctx["selected_subject"]
        topic = ctx["selected_topic"]
        output_dir = os.path.join("downloads", course['course_name'], subject['subject_name'], topic['topic_name'])
        os.makedirs(output_dir, exist_ok=True)
        video_file = downloader.download_video(course, subject, topic, selected_video, output_dir)
        if video_file and downloader.check_video_playable(video_file):
            message.reply_text("Download complete! Sending video file...")
            message.reply_video(video=video_file)
        else:
            message.reply_text("Downloaded video appears to be corrupted or not playable.")
        reset_conversation(chat_id)
        return

@app.on_message(filters.command("cancel"))
def cancel_cmd(client, message):
    reset_conversation(message.chat.id)
    message.reply_text("Conversation cancelled. Use /start to begin again.")

if __name__ == "__main__":
    print("Bot started. Press Ctrl+C to exit.")
    app.run()  # Start the Pyrogram client using long polling.
