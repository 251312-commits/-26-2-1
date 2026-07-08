import gspread
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from oauth2client.service_account import ServiceAccountCredentials

# --- Streamlit Page Config ---
st.set_page_config(layout="wide", page_title="우리 학교 MBTI 분석기")

# --- Custom CSS (다크 테마 + 가로 그라데이션 + 세로 카드 포디움 디자인) ---
st.markdown(
    """
<style>
    /* 1. 짙은 회색 기반 가로 그라데이션 배경 */
    .stApp {
        background: linear-gradient(90deg, #0d0f17 0%, #1a1d2e 50%, #1D2951 100%);
        color: #f0f2f5;
    }

    /* 2. 텍스트 입력창(Text Input) & 라벨 질문 문구 디자인 */
    .stTextInput label, div[data-testid="stWidgetLabel"] p {
        color: #ffffff !important;   /* 질문 문구 흰색 설정 */
        font-size: 1.05rem !important;
        font-weight: 600 !important;
    }
    .stTextInput > div > div > input {
        background-color: #1e2235 !important;
        color: #ffffff !important;
        border-radius: 12px !important;
        border: 1px solid #333a56 !important;
        padding: 12px 16px !important;
        font-size: 1rem !important;
    }
    .stTextInput > div > div > input:focus {
        border-color: #6366f1 !important;
        box-shadow: 0 0 12px rgba(99, 102, 241, 0.4) !important;
    }

    /* 3. 기본 세로 카드 (2위, 3위) */
    .friend-card {
        background: rgba(255, 255, 255, 0.04);
        backdrop-filter: blur(12px);
        -webkit-backdrop-filter: blur(12px);
        border-radius: 20px;
        padding: 24px 16px;
        border: 1px solid rgba(255, 255, 255, 0.08);
        box-shadow: 0 10px 30px rgba(0, 0, 0, 0.3);
        text-align: center;
        margin-top: 30px; /* 1위 카드보다 아래에 위치하도록 여백 설정 */
    }

    /* 4. 중앙 강조 카드 (1위: 위로 우뚝 솟은 포디움 효과) */
    .friend-card-center {
        background: rgba(99, 102, 241, 0.12);
        backdrop-filter: blur(16px);
        -webkit-backdrop-filter: blur(16px);
        border-radius: 20px;
        padding: 28px 16px;
        border: 1px solid rgba(99, 102, 241, 0.5);
        box-shadow: 0 15px 35px rgba(99, 102, 241, 0.25);
        text-align: center;
        transform: translateY(-10px); /* 위로 입체적으로 떠오름 */
    }

    /* 카드 내부 요소 스타일 */
    .badge {
        display: inline-block;
        padding: 4px 12px;
        border-radius: 12px;
        font-size: 0.85rem;
        font-weight: bold;
        margin-bottom: 12px;
    }
    .badge-1 { background: #6366f1; color: #ffffff; }
    .badge-2 { background: #3b82f6; color: #ffffff; }
    .badge-3 { background: #10b981; color: #ffffff; }

    .friend-name {
        font-size: 1.4rem;
        font-weight: 700;
        color: #ffffff;
        margin-bottom: 6px;
    }
    .similarity-score {
        font-size: 1.1rem;
        font-weight: 600;
        color: #a5b4fc;
        margin-bottom: 14px;
    }
    .message-box {
        font-size: 0.88rem;
        color: #d1d5db;
        background: rgba(0, 0, 0, 0.25);
        padding: 10px 12px;
        border-radius: 10px;
        font-style: italic;
        word-break: break-word;
        border-left: 3px solid rgba(255, 255, 255, 0.2);
    }
</style>
""",
    unsafe_allow_html=True,
)


# --- Google Sheets Data Loading ---
@st.cache_data(ttl=300)
def load_data_from_gsheets():
    scope = [
        "https://spreadsheets.google.com/feeds",
        "https://www.googleapis.com/auth/drive",
    ]

    credentials_dict = dict(st.secrets["gcp_service_account"])
    credential = ServiceAccountCredentials.from_json_keyfile_dict(
        credentials_dict, scope
    )
    gc = gspread.authorize(credential)

    spreadsheet_url = "https://docs.google.com/spreadsheets/d/1xZwtZS7i7RDgemeAvkUczHFr8pe8KKstjM9qXqQPiCw/edit?usp=sharing"

    doc = gc.open_by_url(spreadsheet_url)
    sheet = doc.worksheet("설문지 응답 시트1")

    data = sheet.get_all_records()

    user_dict = {
        str(row["이름"]).strip(): [
            row["선택"],  # 만약 'MBTI' 문자를 넣고 싶다면 row['MBTI']로 변경
            (
                row["정신"] / 100
                if str(row["MBTI"])[1].lower() == "n"
                else 1 - row["정신"] / 100
            ),
            (
                row["에너지"] / 100
                if str(row["MBTI"])[0].lower() == "i"
                else 1 - row["에너지"] / 100
            ),
            (
                row["본성"] / 100
                if str(row["MBTI"])[2].lower() == "f"
                else 1 - row["본성"] / 100
            ),
            (
                row["전술"] / 100
                if str(row["MBTI"])[3].lower() == "p"
                else 1 - row["전술"] / 100
            ),
            (
                row["자아"] / 100
                if str(row["MBTI"])[4].lower() == "a"
                else 1 - row["자아"] / 100
            ),
        ]
        for row in data
    }

    unit_vectors = {}
    for name, info in user_dict.items():
        numdata = np.array(info[1:], dtype=float)
        norm = np.linalg.norm(numdata)
        if norm == 0:
            unit_vector = np.zeros_like(numdata)
        else:
            unit_vector = numdata / norm

        unit_vectors[name] = {
            "vector": unit_vector,
            "msg": info[0],
            "original_scores": info[1:],
        }
    return user_dict, unit_vectors


def find(target_name, unit_vectors):
    if target_name not in unit_vectors:
        return None
    target_vec = unit_vectors[target_name]["vector"]

    similarities = []
    for name, data in unit_vectors.items():
        if name == target_name:
            continue

        score = np.dot(target_vec, data["vector"])
        similarities.append((name, score, data["msg"], data["original_scores"]))

    similarities.sort(key=lambda x: x[1], reverse=True)
    return similarities[:3]


def create_combined_radar_chart(
    selected_name, selected_scores, results, categories
):
    fig = go.Figure()

    # 💡 기존 카테고리 이름을 원하는 이름으로 1:1 매핑
    name_map = {
        "에너지": "에너지(I)",
        "정신": "정신(N)",
        "본성": "본성(F)",
        "전술": "전술(P)",
        "자아": "자아(A)",
    }

    # 매핑된 카테고리 이름으로 변환
    mapped_categories = [name_map.get(cat, cat) for cat in categories]
    closed_categories = list(mapped_categories) + [mapped_categories[0]]

    fill_colors = [
        "rgba(255, 99, 132, 0.45)",  # 본인 (분홍)
        "rgba(99, 102, 241, 0.35)",  # 1위 (보라)
        "rgba(59, 130, 246, 0.35)",  # 2위 (파랑)
        "rgba(16, 185, 129, 0.35)",  # 3위 (초록)
    ]
