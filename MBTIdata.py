import streamlit as st
import numpy as np
import pandas as pd
from oauth2client.service_account import ServiceAccountCredentials
import gspread
import plotly.graph_objects as go

# --- Google Sheets Data Loading ---
@st.cache_data(ttl=300) # Cache data for 5 minutes
def load_data_from_gsheets():
    scope = ['https://spreadsheets.google.com/feeds',
             'https://www.googleapis.com/auth/drive']

    # 🚨 수정된 부분: 파일 경로 대신 Streamlit Secrets에서 인증 정보를 가져옵니다.
    credentials_dict = dict(st.secrets["gcp_service_account"])
    credential = ServiceAccountCredentials.from_json_keyfile_dict(credentials_dict, scope)
    gc = gspread.authorize(credential)

    spreadsheet_url = "https://docs.google.com/spreadsheets/d/1xZwtZS7i7RDgemeAvkUczHFr8pe8KKstjM9qXqQPiCw/edit?usp=sharing"

    doc = gc.open_by_url(spreadsheet_url)
    sheet = doc.worksheet("설문지 응답 시트1")

    data = sheet.get_all_records()

    user_dict = {
        str(row['이름']): [
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
        return f"{target_name}이라는 이름은 데이터에 없습니다."
    target_vec = unit_vectors[target_name]['vector']

    similarities = []
    for name, data in unit_vectors.items():
        if name == target_name:
            continue

        score = np.dot(target_vec, data['vector'])
        similarities.append((name, score, data['msg'], data['original_scores']))

    similarities.sort(key=lambda x: x[1], reverse=True)
    return similarities[:3]

def create_radar_chart(scores, categories, title):
    fig = go.Figure()
    fig.add_trace(go.Scatterpolar(
        r=scores,
        theta=categories,
        fill='toself',
        name=title
    ))
    fig.update_layout(
        polar=dict(
            radialaxis=dict(
                visible=True,
                range=[0, 1] 
            )),
        showlegend=True,
        title=title
    )
    return fig

# --- Streamlit UI ---
st.set_page_config(layout="wide")
st.title('MBTI 유사도 분석기')

user_dict, unit_vectors = load_data_from_gsheets()

if not unit_vectors:
    st.error("데이터를 불러오지 못했습니다. Google Sheets 연결을 확인해주세요.")
else:
    user_names = list(user_dict.keys())
    selected_name = st.selectbox('당신의 이름을 선택하세요:', user_names)

    if selected_name:
        st.write(f"## {selected_name}님의 유사한 친구")
        results = find(selected_name, unit_vectors)

        if isinstance(results, list) and results:
            col1, col2 = st.columns(2)
            with col1:
                st.subheader("가장 유사한 친구들")
                for i, (name, score, msg, _) in enumerate(results):
                    st.write(f"{i+1}위: **{name}** (유사도: {score*100:.2f}%)")
                    st.write(f"- 한마디: _{msg}_")

            with col2:
                st.subheader("점수 비교 (레이더 차트)")
                categories = ['정신', '에너지', '본성', '전술', '자아']

                # Create radar chart for the selected user
                selected_user_scores = unit_vectors[selected_name]['original_scores']
                fig_selected = create_radar_chart(selected_user_scores, categories, f'{selected_name}님의 점수')
                st.plotly_chart(fig_selected, use_container_width=True)

                # Create radar charts for similar friends
                for i, (name, score, msg, similar_scores) in enumerate(results):
                    fig_similar = create_radar_chart(similar_scores, categories, f'{name} (유사도: {score*100:.2f}%)')
                    st.plotly_chart(fig_similar, use_container_width=True)

        else:
            st.write(results)
            st.info("유사한 친구를 찾을 수 없습니다. 데이터가 충분한지 확인해주세요.")
