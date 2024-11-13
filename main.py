import streamlit as st
import random
import yt_dlp
import os
from db_update import connect_google_sheets
from pathlib import Path

# 다운로드 폴더 설정
DOWNLOAD_FOLDER = "downloads"
Path(DOWNLOAD_FOLDER).mkdir(exist_ok=True)

# Google Sheets에서 채널별 랜덤 10개 URL 가져오기
def get_random_video_urls(channel_name):
    sheet = connect_google_sheets()
    records = sheet.get_all_records()

    # 선택한 채널의 모든 URL 필터링
    channel_urls = [record['URL'] for record in records if record['Channel'] == channel_name]
    if len(channel_urls) < 10:
        st.warning("해당 채널에 충분한 영상이 없습니다.")
        return channel_urls

    # 랜덤으로 10개 선택
    return random.sample(channel_urls, 10)

# Streamlit UI 구성
st.title("🎬 아이와 여행갈 때 필수 ✈️✈️ \n- 영상 랜덤다운로더 📲")

# 채널 선택 드롭다운
channel_options = [
    "뽀로로", "핑크퐁", "티니핑TV", "안녕자두야 채널", "베베핀",
    "캐리와 장난감친구들", "토이몽", "Larva TUBA", 
    "베이비버스", "반짝반짝 달님이", "레인보우 버블젬"
]
selected_channel = st.selectbox("채널을 선택하세요", channel_options)

# 선택된 채널의 영상 URL을 가져와 자동 입력
if selected_channel:
    video_urls = get_random_video_urls(selected_channel)
    video_urls_text = "\n".join(video_urls)
    st.text_area("🎥 선택한 채널의 랜덤 10개 영상", video_urls_text, height=150)

# 다운로드 버튼
st.write("\n")  # 간격 조정을 위해 추가
if st.button("📥 다운로드 시작", key="download_button"):
    if not video_urls:
        st.warning("다운로드할 영상 링크가 없습니다. 채널을 선택하세요.")
    else:
        st.write("다운로드가 시작됩니다...")
        total_videos = len(video_urls)
        progress_bar = st.progress(0)

        # 다운로드 함수 정의
        def download_video(url, output_folder, ydl_opts):
            try:
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    ydl.download([url])
            except yt_dlp.utils.DownloadError as e:
                st.error(f"다운로드 실패: {str(e)}")

        # 각 URL에 대해 다운로드 수행
        completed = 0
        for i, url in enumerate(video_urls):
            if url:
                st.write(f"다운로드 중... ({i+1}/{total_videos}): {url}")
                ydl_opts = {
                    'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/mp4',
                    'outtmpl': os.path.join(DOWNLOAD_FOLDER, '%(title)s.%(ext)s'),
        
                }
                download_video(url, DOWNLOAD_FOLDER, ydl_opts)

                # 진행 상황 업데이트
                completed += 1
                progress_bar.progress(completed / total_videos)

        st.success("모든 영상 다운로드 완료! 🎉")
        st.write("다운로드 폴더:", os.path.abspath(DOWNLOAD_FOLDER))

# 스타일 추가
st.markdown("""
    <style>
    .stButton button {
        width: 50%;
        margin: 0 auto;
        display: block;
        background-color: #6a0dad;
        color: white;
        font-size: 18px;
        font-weight: bold;
        border-radius: 8px;
        padding: 10px 20px;
    }
    .stTextArea textarea {
        background-color: #f0f0f0;
        font-size: 16px;
        color: #333;
    }
    </style>
""", unsafe_allow_html=True)
