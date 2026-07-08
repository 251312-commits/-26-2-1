import streamlit as st
import numpy as np
import pandas as pd
from oauth2client.service_account import ServiceAccountCredentials
import gspread
import plotly.graph_objects as go

# --- Streamlit Page Config ---
st.set_page_config(layout="wide", page_title="우리 학교 MBTI 분석기")

# --- Custom CSS (다크 테마 + 가로 그라데이션 + 세로 카드 포디움 디자인) ---
st.markdown("""
<style>
    /* 1. 짙은 회색 기반 가로 그라데이션 배경 */
    .stApp {
        background: linear-gradient(90deg, #0d0f17 0%, #1a1d2e 50%, #0d0f17 100%);
        color: #1D2951;
    }

    /* 2. 텍스트 입력창(Text Input) 디자인 */
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
""", unsafe_allow_html=True)


# --- Google Sheets Data Loading ---
@st.cache_data(ttl=300)
def load_data_from_gsheets():
    scope = ['https://spreadsheets.google.com/feeds',
             'https://www.googleapis.com/auth/drive']

    credentials_dict = dict(st.secrets["gcp_service_account"])
    credential = ServiceAccountCredentials.from_json_keyfile_dict(credentials_dict, scope)
    gc = gspread.authorize(credential)

    spreadsheet_url = "https://docs.google.com/spreadsheets/d/1xZwtZS7i7RDgemeAvkUczHFr8pe8KKstjM9qXqQPiCw/edit?usp=sharing"

    doc = gc.open_by_url(spreadsheet_url)
    sheet = doc.worksheet("설문지 응답 시트1")

    data = sheet.get_all_records()

    user_dict = {
        str(row['이름']).strip(): [
            row['선택'],
            row['정신']/100,
            row['에너지']/100,
            row['본성']/100,
            row['전술']/100,
            row['자아']/100
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
            'vector': unit_vector,
            'msg': info[0],
            'original_scores': info[1:]
        }
    return user_dict, unit_vectors


def find(target_name, unit_vectors):
    if target_name not in unit_vectors:
        return None
    target_vec = unit_vectors[target_name]['vector']

    similarities = []
    for name, data in unit_vectors.items():
        if name == target_name:
            continue

        score = np.dot(target_vec, data['vector'])
        similarities.append((name, score, data['msg'], data['original_scores']))

    similarities.sort(key=lambda x: x[1], reverse=True)
    return similarities[:3]


def create_combined_radar_chart(selected_name, selected_scores, results, categories):
    fig = go.Figure()

    fill_colors = [
        'rgba(255, 99, 132, 0.45)', # 본인 (분홍)
        'rgba(99, 102, 241, 0.35)', # 1위 (보라)
        'rgba(59, 130, 246, 0.35)', # 2위 (파랑)
        'rgba(16, 185, 129, 0.35)'  # 3위 (초록)
    ]
    line_colors = [
        'rgb(255, 99, 132)',
        'rgb(99, 102, 241)',
        'rgb(59, 130, 246)',
        'rgb(16, 185, 129)'
    ]

    closed_categories = list(categories) + [categories[0]]

    # 1. 선택한 본인 데이터
    closed_selected_scores = list(selected_scores) + [selected_scores[0]]
    fig.add_trace(go.Scatterpolar(
        r=closed_selected_scores,
        theta=closed_categories,
        fill='toself',
        name=f"★ {selected_name} (나)",
        fillcolor=fill_colors[0],
        line=dict(color=line_colors[0], width=3),
        opacity=0.9
    ))

    # 2. 유사한 친구 Top 3 데이터
    for i, (name, score, _, similar_scores) in enumerate(results):
        closed_similar_scores = list(similar_scores) + [similar_scores[0]]
        fig.add_trace(go.Scatterpolar(
            r=closed_similar_scores,
            theta=closed_categories,
            fill='toself',
            name=f"{i+1}위: {name} ({score*100:.1f}%)",
            fillcolor=fill_colors[i+1],
            line=dict(color=line_colors[i+1], width=2),
            opacity=0.75
        ))

    # 3. 다크 모드 전용 레이아웃 설정
    fig.update_layout(
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        font=dict(color='#E2E8F0', size=13),
        polar=dict(
            bgcolor='rgba(255,255,255,0.02)',
            radialaxis=dict(
                visible=True,
                range=[0, 1],
                gridcolor='rgba(255, 255, 255, 0.15)',
                linecolor='rgba(255, 255, 255, 0.2)',
                tickfont=dict(color='#9CA3AF')
            ),
            angularaxis=dict(
                gridcolor='rgba(255, 255, 255, 0.15)',
                linecolor='rgba(255, 255, 255, 0.2)',
                tickfont=dict(color='#F3F4F6')
            )
        ),
        showlegend=True,
        legend=dict(
            itemclick="toggle",
            itemdoubleclick="toggleothers",
            font=dict(color='#E2E8F0')
        ),
        title=dict(
            text=f"📊 {selected_name}님과 상위 3명의 MBTI 오각형 비교",
            font=dict(color='#FFFFFF', size=16)
        ),
        height=520
    )
    return fig


# --- App Main UI ---
st.title('유영이가꼽줘서살기싫다')
st.subheader('벡터를 이용해 Python으로 우리 학교 학생들의 MBTI 기반 성격 유사도 분석')
st.markdown("---")

user_dict, unit_vectors = load_data_from_gsheets()

if not unit_vectors:
    st.error("데이터를 불러오지 못했습니다. Google Sheets 연결을 확인해주세요.")
else:
    # 사용자 이름 입력받기 (st.text_input)
    input_name = st.text_input('당신의 이름을 입력해 주세요:', placeholder='예: 홍길동').strip()

    if input_name:
        results = find(input_name, unit_vectors)

        if results:
            st.markdown(f"### 🔍 **{input_name}**님과 가장 잘 맞는 친구들")

            # --- 카드 3개 레이아웃 (포디움배치: 2위 | 1위(중앙/우뚝) | 3위) ---
            c_left, c_center, c_right = st.columns(3)

            # 2위 카드 (왼쪽)
            if len(results) >= 2:
                name, score, msg, _ = results[1]
                with c_left:
                    st.markdown(f"""
                        <div class="friend-card">
                            <span class="badge badge-2">🥈 2위</span>
                            <div class="friend-name">{name}</div>
                            <div class="similarity-score">{score*100:.2f}%</div>
                            <div class="message-box">"{msg}"</div>
                        </div>
                    """, unsafe_allow_html=True)

            # 1위 카드 (중앙 - 우뚝 솟음)
            if len(results) >= 1:
                name, score, msg, _ = results[0]
                with c_center:
                    st.markdown(f"""
                        <div class="friend-card-center">
                            <span class="badge badge-1">👑 1위 (최고의 궁합)</span>
                            <div class="friend-name">{name}</div>
                            <div class="similarity-score">{score*100:.2f}%</div>
                            <div class="message-box">"{msg}"</div>
                        </div>
                    """, unsafe_allow_html=True)

            # 3위 카드 (오른쪽)
            if len(results) >= 3:
                name, score, msg, _ = results[2]
                with c_right:
                    st.markdown(f"""
                        <div class="friend-card">
                            <span class="badge badge-3">🥉 3위</span>
                            <div class="friend-name">{name}</div>
                            <div class="similarity-score">{score*100:.2f}%</div>
                            <div class="message-box">"{msg}"</div>
                        </div>
                    """, unsafe_allow_html=True)

            st.write("")
            st.write("")

            # --- 레이더 차트 분석 ---
            categories = ['정신', '에너지', '본성', '전술', '자아']
            selected_user_scores = unit_vectors[input_name]['original_scores']

            fig_combined = create_combined_radar_chart(
                input_name,
                selected_user_scores,
                results,
                categories
            )

            st.plotly_chart(fig_combined, use_container_width=True)

        else:
            st.warning(f"'{input_name}' 님의 데이터가 존재하지 않습니다. 정확한 이름으로 다시 검색해보세요!")
    else:
        st.info("👆 위 입력창에 본인의 이름을 입력하면 유사도 분석 결과를 확인하실 수 있습니다.")
