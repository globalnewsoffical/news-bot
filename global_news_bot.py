#!/usr/bin/env python3
import os
import json
import random
import requests
import asyncio
from datetime import datetime

PIXABAY_KEY   = os.getenv('PIXABAY_API_KEY')
NEWSAPI_KEY   = os.getenv('NEWSAPI_KEY')
GEMINI_KEY    = os.getenv('GEMINI_API_KEY')
YT_CLIENT_ID  = os.getenv('YOUTUBE_CLIENT_ID')
YT_SECRET     = os.getenv('YOUTUBE_CLIENT_SECRET')
YT_CHANNEL    = os.getenv('YOUTUBE_CHANNEL_ID')
YT_REFRESH    = os.getenv('YOUTUBE_REFRESH_TOKEN')

print("🤖 Global News Bot Started")
print(f"⏰ Time: {datetime.now()}")

print("\n📰 Fetching News...")
try:
    url = "https://newsapi.org/v2/everything"
    params = {
        'q': 'USA OR UK OR Canada OR China OR technology OR AI OR breaking news',
        'sortBy': 'publishedAt',
        'language': 'en',
        'apiKey': NEWSAPI_KEY,
        'pageSize': 5
    }
    response = requests.get(url, params=params, timeout=10)
    articles = response.json().get('articles', [])
    if articles:
        article   = articles[0]
        title     = article.get('title', 'Breaking News')
        news_desc = article.get('description', '') or ''
        print(f"✅ Selected: {title[:60]}...")
    else:
        print("❌ No articles found")
        exit(1)
except Exception as e:
    print(f"❌ Error: {e}")
    exit(1)

print("\n✍️ Generating Script...")
try:
    import google.generativeai as genai
    genai.configure(api_key=GEMINI_KEY)
    model = genai.GenerativeModel('gemini-1.5-flash')
    prompt = f"""Write a 50-second YouTube Shorts script about this news:
Title: {title}
Description: {news_desc}
Requirements: Engaging, hook viewers immediately, ~125-150 words, clear and punchy.
Output ONLY the script, nothing else."""
    response = model.generate_content(prompt)
    script = response.text.strip()
    print("✅ Script generated!")
except Exception as e:
    print(f"❌ Error: {e}")
    exit(1)

print("\n🎤 Generating Voiceover...")
try:
    import edge_tts
    audio_file = f"/tmp/voiceover_{int(datetime.now().timestamp())}.mp3"
    voice = "en-US-AriaNeural" if datetime.now().hour < 12 else "en-US-GuyNeural"
    async def generate_tts():
        communicate = edge_tts.Communicate(script, voice)
        await communicate.save(audio_file)
    asyncio.run(generate_tts())
    print(f"✅ Voiceover created! ({voice})")
except Exception as e:
    print(f"❌ Error: {e}")
    exit(1)

print("\n🎬 Fetching Video Footage...")
video_url = None
try:
    pix_url = "https://pixabay.com/api/videos/"
    params = {'key': PIXABAY_KEY, 'q': title.split()[0], 'per_page': 5, 'order': 'popular'}
    pix_resp = requests.get(pix_url, params=params, timeout=10)
    videos = pix_resp.json().get('hits', [])
    if videos:
        video_url = random.choice(videos)['videos']['medium']['url']
        print("✅ Found video footage!")
except Exception as e:
    print(f"⚠️ No footage: {e}")

print("\n🎥 Creating Video...")
try:
    from moviepy.editor import TextClip, AudioFileClip, CompositeVideoClip, ColorClip
    output_video = f"/tmp/final_video_{int(datetime.now().timestamp())}.mp4"
    audio = AudioFileClip(audio_file)
    duration = audio.duration
    if video_url:
        from moviepy.editor import VideoFileClip
        footage_path = "/tmp/footage.mp4"
        r = requests.get(video_url, stream=True, timeout=30)
        with open(footage_path, 'wb') as f:
            for chunk in r.iter_content(chunk_size=8192):
                f.write(chunk)
        bg = VideoFileClip(footage_path)
        bg = bg.loop(duration=duration) if bg.duration < duration else bg.subclip(0, duration)
    else:
        bg = ColorClip(size=(1080, 1920), color=(0,0,0), duration=duration)
    txt = TextClip(title, fontsize=55, color='white', font='Arial-Bold', method='caption', size=(980, None)).set_position(('center','center')).set_duration(duration)
    final = CompositeVideoClip([bg.set_duration(duration), txt]).set_audio(audio)
    final.write_videofile(output_video, fps=24, codec='libx264', audio_codec='aac', verbose=False, logger=None)
    print(f"✅ Video created!")
except Exception as e:
    print(f"❌ Error: {e}")
    exit(1)

print("\n📤 Uploading to YouTube...")
try:
    from google.oauth2.credentials import Credentials
    from googleapiclient.discovery import build
    from googleapiclient.http import MediaFileUpload
    creds = Credentials(
        token=None, refresh_token=YT_REFRESH,
        token_uri='https://oauth2.googleapis.com/token',
        client_id=YT_CLIENT_ID, client_secret=YT_SECRET,
        scopes=['https://www.googleapis.com/auth/youtube.upload']
    )
    youtube = build('youtube', 'v3', credentials=creds)
    source_name = article.get('source', {}).get('name', 'News')
    yt_desc = f"{title}\n\n{news_desc[:300]}\n\nSource: {source_name}\n\n#InternationalNews #BreakingNews #Shorts"
    request = youtube.videos().insert(
        part='snippet,status',
        body={
            'snippet': {'title': title[:100], 'description': yt_desc, 'tags': ['News','BreakingNews','Shorts'], 'categoryId': '25'},
            'status': {'privacyStatus': 'public', 'selfDeclaredMadeForKids': False}
        },
        media_body=MediaFileUpload(output_video, chunksize=-1, resumable=True)
    )
    response = request.execute()
    video_id = response.get('id')
    print(f"✅ Uploaded! https://youtube.com/watch?v={video_id}")
except Exception as e:
    print(f"❌ Upload failed: {e}")
    exit(1)

print("\n✅ BOT COMPLETED SUCCESSFULLY!")
