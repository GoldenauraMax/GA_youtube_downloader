import os
import yt_dlp
import gspread
from google.oauth2.service_account import Credentials
import requests
import time
from dotenv import load_dotenv

# .env 파일에서 환경 변수 불러오기
load_dotenv()

# 환경 변수 설정
SHEET_ID = os.getenv("SHEET_ID")
SHEET_NAME = os.getenv("SHEET_NAME")
SERVICE_ACCOUNT_FILE = os.getenv("SERVICE_ACCOUNT_FILE")
YOUTUBE_API_KEY = os.getenv("YOUTUBE_API_KEY")

# Google Sheets와 연결 설정
def connect_google_sheets():
    credentials = Credentials.from_service_account_file(
        SERVICE_ACCOUNT_FILE,
        scopes=["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
    )
    gc = gspread.authorize(credentials)
    spreadsheet = gc.open_by_key(SHEET_ID)

    # 시트가 없으면 새로 생성
    try:
        sheet = spreadsheet.worksheet(SHEET_NAME)
    except gspread.exceptions.WorksheetNotFound:
        sheet = spreadsheet.add_worksheet(title=SHEET_NAME, rows="100", cols="2")
        sheet.append_row(["Channel", "URL"])  # 헤더 추가

    return sheet

# Google Sheets에서 이미 저장된 URL 가져오기
def get_existing_urls(sheet):
    rows = sheet.get_all_values()
    existing_urls = {row[1] for row in rows[1:]}  # URL이 있는 두 번째 열에서 중복을 제거하여 집합으로 저장
    return existing_urls

# 핸들 또는 사용자 이름을 채널 ID로 변환
def get_channel_id_from_handle_or_username(identifier):
    url = f"https://www.googleapis.com/youtube/v3/channels?key={YOUTUBE_API_KEY}&forUsername={identifier}&part=id"
    response = requests.get(url)
    data = response.json()
    
    if response.status_code == 200 and "items" in data and data["items"]:
        return data["items"][0]["id"]
    return None

# 특정 채널에서 10분 이상인 영상만 가져오는 함수 (중복 제거 및 예외 처리 포함)
def get_long_videos_from_channel(channel_id, existing_urls, min_duration=600, max_results=50):
    video_urls = []
    ydl_opts = {
        'extract_flat': 'in_playlist',  # 영상 목록만 가져오기
        'quiet': True
    }
    channel_url = f"https://www.youtube.com/channel/{channel_id}"

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        try:
            channel_info = ydl.extract_info(channel_url, download=False)
            entries = channel_info.get('entries', [])
        except yt_dlp.utils.DownloadError as e:
            print(f"Failed to retrieve channel information for {channel_url}: {e}")
            return video_urls

        for entry in entries:
            video_url = f"https://www.youtube.com/watch?v={entry['id']}"
            
            # 기존에 저장된 URL인지 확인
            if video_url in existing_urls:
                print(f"Skipping already saved video: {video_url}")
                continue

            # 영상 길이 확인
            try:
                video_info = ydl.extract_info(video_url, download=False)
                duration = video_info.get('duration', 0)
            except yt_dlp.utils.DownloadError as e:
                print(f"Skipping unavailable video: {video_url} - {e}")
                continue

            # 10분 이상인 영상만 필터링
            if duration >= min_duration:
                video_urls.append(video_url)
                existing_urls.add(video_url)

            if len(video_urls) >= max_results:
                break

            time.sleep(0.1)  # 지연 추가

    print(f"Fetched {len(video_urls)} videos over {min_duration // 60} minutes from {channel_url}")
    return video_urls

# 새로운 영상 URL을 Google Sheets에 추가
def update_sheet_with_new_videos(sheet, channel_name, new_video_urls):
    for url in new_video_urls:
        sheet.append_row([channel_name, url])
        time.sleep(0.1)  # 지연 추가
    print(f"Added {len(new_video_urls)} new videos to Google Sheets for {channel_name}")

# 메인 함수: Google Sheets에서 기존 URL을 가져오고 새 영상 추가
def main():
    sheet = connect_google_sheets()
    existing_urls = get_existing_urls(sheet)  # Google Sheets에 저장된 기존 URL 가져오기

    channels = {
        "뽀로로": "UC56gTxNs4f9xZ7Pa2i5xNzg",
        "핑크퐁": "UCoookXUzPciGrEZEXmh4Jjg",
        "티니핑TV": "https://www.youtube.com/@teeniepingTV",
        "안녕자두야 채널": "https://www.youtube.com/@hellojadooya",
        "캐리와 장난감친구들": "https://www.youtube.com/@CarrieAndToys",
        "베베핀": "UC_Py3VQ4sjXHj1c4Rhb5ITw"
    }

    for channel_name, channel_id_or_url in channels.items():
        # URL 형식 처리 및 채널 ID 변환
        if "@" in channel_id_or_url:
            # 핸들 URL을 채널 ID로 변환
            channel_id = get_channel_id_from_handle_or_username(channel_id_or_url.replace("https://www.youtube.com/", ""))
            if channel_id is None:
                print(f"Failed to retrieve channel ID for {channel_id_or_url}")
                continue
        else:
            channel_id = channel_id_or_url

        new_video_urls = get_long_videos_from_channel(channel_id, existing_urls)
        update_sheet_with_new_videos(sheet, channel_name, new_video_urls)

if __name__ == "__main__":
    main()
