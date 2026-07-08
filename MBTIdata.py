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


# --- 차트 생성 함수들 ---
def create_combined_radar_chart(
    selected_name, selected_scores, results, categories
):
    fig = go.Figure()

    name_map = {
        "에너지": "에너지(I)",
        "정신": "정신(N)",
        "본성": "본성(F)",
        "전술": "전술(P)",
        "자아": "자아(A)",
    }

    mapped_categories = [name_map.get(cat, cat) for cat in categories]
    closed_categories = list(mapped_categories) + [mapped_categories[0]]

    fill_colors = [
        "rgba(255, 99, 132, 0.45)",  # 본인 (분홍)
        "rgba(99, 102, 241, 0.35)",  # 1위 (보라)
        "rgba(59, 130, 246, 0.35)",  # 2위 (파랑)
        "rgba(16, 185, 129, 0.35)",  # 3위 (초록)
    ]
    line_colors = [
        "rgb(255, 99, 132)",
        "rgb(99, 102, 241)",
        "rgb(59, 130, 246)",
        "rgb(16, 185, 129)",
    ]

    # 1. 선택한 본인 데이터
    closed_selected_scores = list(selected_scores) + [selected_scores[0]]
    fig.add_trace(
        go.Scatterpolar(
            r=closed_selected_scores,
            theta=closed_categories,
            fill="toself",
            name=f"★ {selected_name} (나)",
            fillcolor=fill_colors[0],
            line=dict(color=line_colors[0], width=3),
            opacity=0.9,
        )
    )

    # 2. 유사한 친구 Top 3 데이터
    for i, (name, score, _, similar_scores) in enumerate(results):
        closed_similar_scores = list(similar_scores) + [similar_scores[0]]
        fig.add_trace(
            go.Scatterpolar(
                r=closed_similar_scores,
                theta=closed_categories,
                fill="toself",
                name=f"{i+1}위: {name} ({score*100:.1f}%)",
                fillcolor=fill_colors[i+1],
                line=dict(color=line_colors[i+1], width=2),
                opacity=0.75,
            )
        )

    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color="#E2E8F0", size=13),
        polar=dict(
            bgcolor="rgba(255,255,255,0.02)",
            radialaxis=dict(
                visible=True,
                range=[0, 1],
                gridcolor="rgba(255, 255, 255, 0.15)",
                linecolor="rgba(255, 255, 255, 0.2)",
                tickfont=dict(color="#9CA3AF"),
            ),
            angularaxis=dict(
                gridcolor="rgba(255, 255, 255, 0.15)",
                linecolor="rgba(255, 255, 255, 0.2)",
                tickfont=dict(color="#F3F4F6"),
            ),
        ),
        showlegend=True,
        legend=dict(
            itemclick="toggle",
            itemdoubleclick="toggleothers",
            font=dict(color="#E2E8F0"),
        ),
        title=dict(
            text=f"📊 {selected_name}님과 상위 3명의 MBTI 오각형 비교",
            font=dict(color="#FFFFFF", size=16),
        ),
        height=520,
    )
    return fig


def create_pair_radar_chart(name1, scores1, name2, scores2, score_pct, categories):
    """1:1 비교 전용 레이더 차트"""
    fig = go.Figure()

    name_map = {
        "에너지": "에너지(I)",
        "정신": "정신(N)",
        "본성": "본성(F)",
        "전술": "전술(P)",
        "자아": "자아(A)",
    }

    mapped_categories = [name_map.get(cat, cat) for cat in categories]
    closed_categories = list(mapped_categories) + [mapped_categories[0]]

    # 본인 데이터
    closed1 = list(scores1) + [scores1[0]]
    fig.add_trace(
        go.Scatterpolar(
            r=closed1,
            theta=closed_categories,
            fill="toself",
            name=f"★ {name1} (나)",
            fillcolor="rgba(255, 99, 132, 0.45)",
            line=dict(color="rgb(255, 99, 132)", width=3),
        )
    )

    # 지목한 친구 데이터
    closed2 = list(scores2) + [scores2[0]]
    fig.add_trace(
        go.Scatterpolar(
            r=closed2,
            theta=closed_categories,
            fill="toself",
            name=f"👥 {name2}",
            fillcolor="rgba(245, 158, 11, 0.45)",
            line=dict(color="rgb(245, 158, 11)", width=3),
        )
    )

    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color="#E2E8F0", size=13),
        polar=dict(
            bgcolor="rgba(255,255,255,0.02)",
            radialaxis=dict(
                visible=True,
                range=[0, 1],
                gridcolor="rgba(255, 255, 255, 0.15)",
                linecolor="rgba(255, 255, 255, 0.2)",
                tickfont=dict(color="#9CA3AF"),
            ),
            angularaxis=dict(
                gridcolor="rgba(255, 255, 255, 0.15)",
                linecolor="rgba(255, 255, 255, 0.2)",
                tickfont=dict(color="#F3F4F6"),
            ),
        ),
        showlegend=True,
        title=dict(
            text=f"⚔️ {name1} VS {name2} 성격 성향 비교 (유사도: {score_pct:.2f}%)",
            font=dict(color="#FFFFFF", size=16),
        ),
        height=500,
    )
    return fig


# --- App Main UI ---
st.title("성격 유사도 분석")
st.subheader("벡터를 이용해 Python으로 우리 학교 학생들의 MBTI 기반 성격 유사도 분석")

# 🔄 새로고침 버튼
if st.button("🔄 구글 시트 데이터 즉시 새로고침"):
    st.cache_data.clear()
    st.rerun()

# ---------------------------------------------------------
# ✨ [신규 기능 1] 알고리즘 / 수학적 원리 설명 버튼 (Expander)
# ---------------------------------------------------------
with st.expander("📐 **수학/알고리즘 원리 알아보기 (클릭)**"):
    st.markdown(
        """
    #### 1. MBTI 성격의 5차원 벡터화
    각 사람의 MBTI 5가지 척도(정신, 에너지, 본성, 전술, 자아) 비율 데이터를 5차원 공간상의 위치(벡터)인 $\vec{v} = (v_1, v_2, v_3, v_4, v_5)$ 로 나타냅니다.
    
    #### 2. 단위 벡터 정규화 ($L_2$ Norm)
    성향의 절댓값 크기가 아닌 **'성향 비율의 방향성'**만을 비교하기 위해 각 벡터를 크기(길이) $1$인 단위 벡터 $\hat{u}$로 정규화합니다.
    $$\hat{u} = \\frac{\vec{v}}{\|\vec{v}\|}$$
    
    #### 3. 벡터 내적(Dot Product)과 코사인 유사도
    두 사람의 정규화된 성격 벡터 $\hat{u}_A$와 $\hat{u}_B$의 내적을 구하면, 이는 두 성향 벡터가 이루는 각도의 **코사인 유사도(Cosine Similarity)**가 됩니다.
    $$\text{Similarity} = \hat{u}_A \cdot \hat{u}_B = \|\hat{u}_A\|\|\hat{u}_B\|\cos(\theta) = \cos(\theta)$$
    
    * 두 사람의 성향 패턴이 완전히 일치하면 $\theta = 0^\circ \rightarrow \mathbf{100\%}$
    * 벡터가 이루는 각이 커질수록 유사도 점수가 낮아지게 됩니다.
    """
    )

st.markdown("---")

user_dict, unit_vectors = load_data_from_gsheets()

if not unit_vectors:
    st.error("데이터를 불러오지 못했습니다. Google Sheets 연결을 확인해주세요.")
else:
    input_name = st.text_input(
        "당신의 이름을 입력해 주세요:", placeholder="예: 홍길동"
    ).strip()

    if input_name:
        results = find(input_name, unit_vectors)

        if results:
            st.markdown(f"### 🔍 **{input_name}**님과 가장 잘 맞는 Top 3 친구들")

            # --- 카드 3개 레이아웃 (포디움배치: 2위 | 1위(중앙/우뚝) | 3위) ---
            c_left, c_center, c_right = st.columns(3)

            # 2위 카드 (왼쪽)
            if len(results) >= 2:
                name, score, msg, _ = results[1]
                with c_left:
                    st.markdown(
                        f"""
                        <div class="friend-card">
                            <span class="badge badge-2">🥈 2위</span>
                            <div class="friend-name">{name}</div>
                            <div class="similarity-score">{score*100:.2f}%</div>
                            <div class="message-box">"{msg}"</div>
                        </div>
                    """,
                        unsafe_allow_html=True,
                    )

            # 1위 카드 (중앙)
            if len(results) >= 1:
                name, score, msg, _ = results[0]
                with c_center:
                    st.markdown(
                        f"""
                        <div class="friend-card-center">
                            <span class="badge badge-1">👑 1위 (최고의 궁합)</span>
                            <div class="friend-name">{name}</div>
                            <div class="similarity-score">{score*100:.2f}%</div>
                            <div class="message-box">"{msg}"</div>
                        </div>
                    """,
                        unsafe_allow_html=True,
                    )

            # 3위 카드 (오른쪽)
            if len(results) >= 3:
                name, score, msg, _ = results[2]
                with c_right:
                    st.markdown(
                        f"""
                        <div class="friend-card">
                            <span class="badge badge-3">🥉 3위</span>
                            <div class="friend-name">{name}</div>
                            <div class="similarity-score">{score*100:.2f}%</div>
                            <div class="message-box">"{msg}"</div>
                        </div>
                    """,
                        unsafe_allow_html=True,
                    )

            st.write("")
            st.write("")

            # Top 3 전체 비교 레이더 차트
            categories = ["정신", "에너지", "본성", "전술", "자아"]
            selected_user_scores = unit_vectors[input_name]["original_scores"]

            fig_combined = create_combined_radar_chart(
                input_name, selected_user_scores, results, categories
            )
            st.plotly_chart(fig_combined, use_container_width=True)

            # ---------------------------------------------------------
            # ✨ [신규 기능 2] 특정 친구 검색 및 1:1 비교
            # ---------------------------------------------------------
            st.markdown("---")
            st.markdown("### 🎯 **특정 친구와 1:1 비교 분석하기**")

            # 내 이름을 제외한 나머지 친구 목록 추출
            other_friends = [
                name for name in unit_vectors.keys() if name != input_name
            ]

            if other_friends:
                target_friend = st.selectbox(
                    "궁금한 친구의 이름을 선택하세요:",
                    options=other_friends,
                    index=0,
                )

                if target_friend:
                    # 선택한 친구와의 내적 유사도 계산
                    vec1 = unit_vectors[input_name]["vector"]
                    vec2 = unit_vectors[target_friend]["vector"]
                    pair_score = float(np.dot(vec1, vec2)) * 100

                    scores1 = unit_vectors[input_name]["original_scores"]
                    scores2 = unit_vectors[target_friend]["original_scores"]

                    # 지목된 친구의 한마디 메시지 가져오기
                    friend_msg = unit_vectors[target_friend]["msg"]

                    # 결과 출력
                    col_info1, col_info2 = st.columns([1, 2])

                    with col_info1:
                        st.markdown(
                            f"""
                            <div class="friend-card" style="margin-top: 0px; text-align: left;">
                                <h3 style="color:#ffffff; margin-bottom:10px;">🤝 궁합 분석 결과</h3>
                                <p style="font-size: 1.1rem;"><b>{input_name}</b> & <b>{target_friend}</b></p>
                                <div style="font-size: 2.2rem; font-weight: bold; color: #6366f1; margin: 15px 0;">
                                    {pair_score:.2f}%
                                </div>
                                <p style="color: #a5b4fc; font-size: 0.9rem;">💬 <b>{target_friend}의 한마디:</b></p>
                                <div class="message-box">"{friend_msg}"</div>
                            </div>
                        """,
                            unsafe_allow_html=True,
                        )

                    with col_info2:
                        fig_pair = create_pair_radar_chart(
                            input_name,
                            scores1,
                            target_friend,
                            scores2,
                            pair_score,
                            categories,
                        )
                        st.plotly_chart(fig_pair, use_container_width=True)

        else:
            st.warning(
                f"'{input_name}' 님의 데이터가 존재하지 않습니다. 정확한 이름으로 다시 검색해보세요!"
            )
    else:
        st.info(
            "👆 위 입력창에 본인의 이름을 입력하면 유사도 분석 결과를 확인하실 수 있습니다."
        )
