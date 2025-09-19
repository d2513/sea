import streamlit as st
import ee
import geemap.foliumap as geemap
import google.auth
import folium
import pandas as pd
import plotly.express as px

# -------------------- 초기화 --------------------
try:
    KEY_FILE_PATH = 'your-secret-key-file.json'  # 본인 파일 이름으로 변경
    credentials, project_id = google.auth.load_credentials_from_file(KEY_FILE_PATH)
    scoped_credentials = credentials.with_scopes(
        ['https://www.googleapis.com/auth/cloud-platform', 'https://www.googleapis.com/auth/earthengine'])
    ee.Initialize(credentials=scoped_credentials)
    st.sidebar.success("✅ GEE 인증 성공!")
except Exception as e:
    st.error(f"🚨 Earth Engine 인증 오류가 발생했습니다: {e}")
    st.stop()

# -------------------- 페이지 설정 및 제목 --------------------
st.set_page_config(layout="wide")
st.title("🌊 해수면 상승 시뮬레이터")

# -------------------- 해수면 상승 데이터 --------------------
sea_level_data = {
    '연도': [2020, 2030, 2040, 2050, 2060, 2070, 2080, 2090, 2100, 2110, 2120, 2130, 2140, 2150],
    '해수면 상승 (m)': [0.00, 0.03, 0.07, 0.12, 0.18, 0.25, 0.32, 0.40, 0.44, 0.48, 0.53, 0.58, 0.63, 0.68]
}
df_sea_level = pd.DataFrame(sea_level_data)

# -------------------- 사용자 입력 --------------------
col1, col2 = st.columns([1, 2]) # 슬라이더와 그래프를 위한 컬럼 분할

with col1:
    year = st.slider("연도 선택", 2025, 2150, 2100, step=5)
    
    # 선택된 연도에 가장 가까운 데이터를 찾아 해수면 상승량 계산 (선형 보간)
    # 2020년 이전 선택 시 0으로 처리
    if year <= 2020:
        current_sea_level_rise = 0.00
    else:
        # 선택된 연도 주변의 데이터 포인트 찾기
        before_year = df_sea_level[df_sea_level['연도'] <= year].tail(1)
        after_year = df_sea_level[df_sea_level['연도'] >= year].head(1)

        if not before_year.empty and not after_year.empty and before_year.iloc[0]['연도'] != after_year.iloc[0]['연도']:
            x1 = before_year.iloc[0]['연도']
            y1 = before_year.iloc[0]['해수면 상승 (m)']
            x2 = after_year.iloc[0]['연도']
            y2 = after_year.iloc[0]['해수면 상승 (m)']
            
            # 선형 보간
            current_sea_level_rise = y1 + (y2 - y1) * (year - x1) / (x2 - x1)
        elif not before_year.empty: # 선택된 연도가 가장 마지막 데이터 이후인 경우
            current_sea_level_rise = before_year.iloc[0]['해수면 상승 (m)']
        else: # 그 외 (예: 2020년 이전)
            current_sea_level_rise = 0.00


    st.write(f"📏 예상 해수면 상승: **{current_sea_level_rise:.2f} m**")

with col2:
    # 해수면 상승 그래프
    fig = px.line(df_sea_level, x='연도', y='해수면 상승 (m)', 
                  title='연도별 해수면 상승 예측 (m)',
                  labels={'해수면 상승 (m)': '해수면 상승 (m)'},
                  markers=True)
    
    # 현재 선택된 연도에 해당하는 해수면 상승량을 그래프에 표시
    fig.add_scatter(x=[year], y=[current_sea_level_rise],
                    mode='markers',
                    marker=dict(size=10, color='red'),
                    name=f'선택된 연도: {year} ({current_sea_level_rise:.2f}m)')
    
    fig.update_layout(hovermode="x unified") # 마우스 오버 시 정보 표시 방식
    st.plotly_chart(fig, use_container_width=True)


# -------------------- DEM 및 데이터 불러오기 --------------------
dem = ee.Image('CGIAR/SRTM90_V4').select('elevation')
flooded_area = dem.lte(current_sea_level_rise)
flooded_mask = flooded_area.selfMask()

# -------------------- 지도 생성 --------------------
m = geemap.Map(center=[36.5, 127.5], zoom=7)

# -------------------- 🎯 레이어 추가 방식 변경 🎯 --------------------
try:
    map_id_dict = flooded_mask.getMapId({'palette': ['0000FF']})

    folium.TileLayer(
        tiles=map_id_dict['tile_fetcher'].url_format,
        attr='Google Earth Engine',
        overlay=True,
        name='침수 예상 지역',
        show=True
    ).add_to(m)

    folium.LayerControl().add_to(m)

except Exception as e:
    st.error(f"GEE 레이어를 지도에 추가하는 중 오류 발생: {e}")
    st.stop()

# -------------------- Streamlit에 표시 --------------------
st.write("지도에서 파란색으로 표시된 지역이 침수 예상 지역입니다.")
m.to_streamlit(height=600)

# -------------------- 정보 패널 --------------------
st.sidebar.header("📌 정보")
st.sidebar.info(
    """
    - **DEM:** SRTM90 V4 (전 세계 90m 해상도 지형 데이터)
    - **해수면 상승 모델:** IPCC 시나리오 기반의 예측 데이터를 사용합니다.
    - 슬라이더를 움직여 연도에 따른 해수면 상승 및 침수 예상 지역 변화를 확인해 보세요.
    - 그래프에서 현재 선택된 연도의 해수면 상승량을 빨간색 점으로 확인할 수 있습니다.
    """
)