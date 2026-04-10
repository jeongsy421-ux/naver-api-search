import streamlit as st  # Streamlit 웹 대시보드 라이브러리 임포트
import pandas as pd  # 데이터 처리를 위한 Pandas 라이브러리 임포트
import plotly.express as px  # 인터랙티브 시각화를 위한 Plotly Express 임포트
import plotly.graph_objects as go  # 세밀한 차트 제어를 위한 Plotly Graph Objects 임포트
import os  # 시스템 환경 변수 접근을 위한 os 라이브러리 임포트
import json  # JSON 데이터 파싱 및 생성을 위한 json 라이브러리 임포트
import urllib.request  # API 호출을 위한 URL 요청 라이브러리 임포트
import re  # 정규표현식을 사용한 문자열 처리를 위한 re 라이브러리 임포트
from datetime import datetime, timedelta  # 날짜 및 시간 처리를 위한 클래스 임포트
from dotenv import load_dotenv  # .env 파일 로드를 위한 library 임포트

# 페이지 기본 설정 (제목, 레이아웃, 아이콘)
st.set_page_config(page_title="Naver Real-time Market Intelligence", layout="wide", page_icon="🚀")

# .env 파일에서 환경 변수를 로드 (로컬 개발용)
load_dotenv()

# 네이버 API 자격 증명 로드: 배포 환경(Streamlit Secrets) 우선, 없으면 로컬 .env 환경변수 사용
try:
    # Streamlit Cloud 배포 환경에서는 secrets.toml에서 로드
    CLIENT_ID = st.secrets.get("NAVER_CLIENT_ID") or os.getenv("NAVER_CLIENT_ID")
    CLIENT_SECRET = st.secrets.get("NAVER_CLIENT_SECRET") or os.getenv("NAVER_CLIENT_SECRET")
except Exception:
    # 로컬 개발 환경 등 secrets.toml이 없는 경우 .env 파일에서 로드
    CLIENT_ID = os.getenv("NAVER_CLIENT_ID")
    CLIENT_SECRET = os.getenv("NAVER_CLIENT_SECRET")

# --- 유틸리티 및 캐싱 함수 영역 ---

# HTML 태그 및 특수 기호를 제거하는 세척 함수
def clean_html(text):
    if not isinstance(text, str): return ""  # 문자열이 아니면 빈 값 반환
    # 정규표현식으로 태그 제거 및 특수 기호 복구
    return re.sub(r'<[^>]*>', '', text).replace('&quot;', '"').replace('&lt;', '<').replace('&gt;', '>')

# 단어 빈도수를 계산하여 상위 n개를 반환하는 함수 (캐싱 적용)
@st.cache_data(ttl=600)
def get_word_frequency(series, top_n=30):
    all_text = " ".join(series.apply(clean_html))  # 모든 텍스트를 하나로 합침
    words = [w for w in re.findall(r'\b\w{2,}\b', all_text)]  # 2글자 이상의 단어만 추출
    if not words: return pd.DataFrame(columns=['word', 'count'])  # 단어가 없으면 빈 데이터프레임 반환
    # 단어별 갯수를 세서 데이터프레임 형태로 반환
    return pd.Series(words).value_counts().head(top_n).reset_index(name='count').rename(columns={'index': 'word'})

# --- 네이버 API 연동 함수 (캐싱 적용) ---

# 네이버 데이터랩 트렌드 API를 호출하여 검색량 추이를 가져오는 함수
@st.cache_data(ttl=600, show_spinner=False)
def fetch_datalab_trend_cached(keywords, start_date, end_date):
    if not keywords: return pd.DataFrame()  # 키워드가 없으면 즉시 종료
    url = "https://openapi.naver.com/v1/datalab/search"  # 데이터랩 API 엔드포인트
    keyword_groups = [{"groupName": kw, "keywords": [kw]} for kw in keywords]  # 키워드 그룹 설정
    body = {
        "startDate": start_date.strftime("%Y-%m-%d"),  # 시작 날짜 형식 지정
        "endDate": end_date.strftime("%Y-%m-%d"),  # 종료 날짜 형식 지정
        "timeUnit": "date",  # 시간 단위 설정
        "keywordGroups": keyword_groups  # 키워드 그룹 전달
    }
    
    request = urllib.request.Request(url)  # HTTP 요청 객체 생성
    request.add_header("X-Naver-Client-Id", CLIENT_ID)  # API ID 헤더 추가
    request.add_header("X-Naver-Client-Secret", CLIENT_SECRET)  # API Secret 헤더 추가
    request.add_header("Content-Type", "application/json")  # 콘텐츠 타입 헤더 추가
    
    try:
        # API 요청 실행 및 응답 수신
        response = urllib.request.urlopen(request, data=json.dumps(body).encode("utf-8"))
        if response.getcode() == 200:  # 성공 시
            data = json.loads(response.read().decode('utf-8'))  # JSON 파싱
            results = []  # 결과 저장 리스트
            for group in data['results']:  # 각 키워드 그룹별 순회
                title = group['title']
                for d in group['data']:  # 기간별 데이터 순회
                    results.append({"date": d['period'], "keyword": title, "ratio": d['ratio']})
            return pd.DataFrame(results)  # 데이터프레임으로 변환하여 반환
    except:
        return pd.DataFrame()  # 에러 발생 시 빈 데이터프레임 반환
    return pd.DataFrame()

# 네이버 검색 API(블로그, 뉴스 등) 단일 호출 함수
@st.cache_data(ttl=600, show_spinner=False)
def fetch_search_results_single(api_type, query):
    # API 타입별 엔드포인트 매핑
    api_map = {"blog": "blog", "news": "news", "cafe": "cafearticle", "shop": "shop"}
    endpoint = api_map.get(api_type)  # 호출할 엔드포인트 선택
    encText = urllib.parse.quote(query)  # 검색어 URL 인코딩
    url = f"https://openapi.naver.com/v1/search/{endpoint}.json?query={encText}&display=100"  # API URL 생성
    
    request = urllib.request.Request(url)  # HTTP 요청 객체 생성
    request.add_header("X-Naver-Client-Id", CLIENT_ID)  # API ID 헤더 추가
    request.add_header("X-Naver-Client-Secret", CLIENT_SECRET)  # API Secret 헤더 추가
    
    try:
        response = urllib.request.urlopen(request)  # API 호출 실행
        if response.getcode() == 200:  # 성공 시
            data = json.loads(response.read().decode('utf-8'))  # JSON 데이터 파싱
            df = pd.DataFrame(data['items'])  # 검색 결과 아이템들을 데이터프레임화
            df['search_keyword'] = query  # 검색어 정보 컬럼 추가
            return df  # 결과 반환
    except:
        return pd.DataFrame()  # 에러 시 빈 데이터프레임 반환
    return pd.DataFrame()

# 여러 키워드에 대해 검색 API를 순차 호출하여 합쳐주는 함수
def fetch_all_search_results(api_type, keywords):
    all_dfs = []  # 개별 결과들을 합치기 위한 리스트
    for kw in keywords:  # 각 키워드별로 호출
        df = fetch_search_results_single(api_type, kw)
        if not df.empty:
            all_dfs.append(df)  # 유효한 결과만 추가
    # 모든 결과를 하나의 데이터프레임으로 병합
    return pd.concat(all_dfs, ignore_index=True) if all_dfs else pd.DataFrame()

# --- 사이드바 UI 및 환경 설정 영역 ---

st.sidebar.title("🔍 실시간 마켓 분석 설정")  # 사이드바 제목

# 통합 검색 인터페이스: 입력과 선택을 하나의 칸으로 합침
if 'active_keywords_str' not in st.session_state:
    st.session_state.active_keywords_str = "선풍기, 핫팩"

# 하나의 통합 검색란에서 모든 키워드를 관리 (입력 즉시 수집 및 분석 대상 반영)
kw_input_raw = st.sidebar.text_input(
    "📊 분석 키워드 입력", 
    value=st.session_state.active_keywords_str,
    placeholder="여러 키워드는 공백이나 쉼표(,)로 구분하여 입력하세요",
    help="여기에 입력한 단어들이 즉시 분석 대상이 됩니다. '선풍기 핫팩 캠핑' 처럼 나열해 보세요."
)

# 입력된 텍스트를 공백 또는 쉼표 기준으로 분할하여 실제 분석 키워드 리스트 생성
selected_keywords = [k.strip() for k in re.split(r'[,\s]+', kw_input_raw) if k.strip()]

# 세션 상태에 현재 입력값 동기화 (상태 유지용)
st.session_state.active_keywords_str = kw_input_raw

# 3. 날짜 범위 선택기
date_range = st.sidebar.date_input(
    "📅 분석 기간", 
    [datetime.now() - timedelta(days=365), datetime.now()]  # 기본값: 지난 1년
)

st.sidebar.divider()  # 구분선 추가
# 캐시를 강제로 비우고 새로고침하는 버튼
if st.sidebar.button("🧹 전체 캐시 초기화"):
    st.cache_data.clear()
    st.sidebar.success("캐시가 초기화되었습니다.")

# --- 메인 대시보드 화면 구성 ---

st.title("🚀 Naver Real-time Market Intelligence")  # 대시보드 제목
st.markdown("사용자가 입력한 모든 키워드에 대해 네이버 오픈 API로부터 실시간으로 인사이트를 도출합니다.")

# 현재 로드된 데이터 내에서 검색 가능한 전역 검색창
global_q = st.text_input("⚡ 실시간 결과 내 필터링: 현재 화면에 표시된 데이터에서 특정 단어를 즉시 찾습니다.")

# --- 데이터 수집 실행 및 상태바 표시 ---
if len(date_range) == 2 and selected_keywords:
    # 실시간 수집 상태 표시기(Status 바) 생성
    with st.status("🔍 네이버 API 데이터를 실시간으로 가져오는 중...", expanded=False) as status:
        st.write("📈 검색어 트렌드 분석 중...")
        df_trend = fetch_datalab_trend_cached(selected_keywords, date_range[0], date_range[1])
        
        st.write("📱 블로그/포스트 여론 수집 중...")
        df_blog = fetch_all_search_results("blog", selected_keywords)
        
        st.write("📰 뉴스 스트림 분석 중...")
        df_news = fetch_all_search_results("news", selected_keywords)
        
        st.write("🏠 카페 커뮤니티 반응 수집 중...")
        df_cafe = fetch_all_search_results("cafe", selected_keywords)
        
        st.write("🛍️ 쇼핑 시장 및 최저가 데이터 수집 중...")
        df_shop = fetch_all_search_results("shop", selected_keywords)
        
        # 수집 완료 시 상태 메시지 업데이트
        status.update(label="✅ 데이터 수집 완료!", state="complete", expanded=False)
else:
    # 키워드나 기간이 미지정된 경우 안내 메시지 출력
    st.info("사이드바에서 분석할 키워드를 입력하거나 선택해 주세요.")
    st.stop()  # 이후 코드 실행 중단

# --- 전역 검색 필터 적용 함수 ---
def filter_df(df):
    if global_q and not df.empty:
        # 데이터프레임 행 중 검색어를 포함하는 행만 필터링
        mask = df.apply(lambda row: row.astype(str).str.contains(global_q, case=False).any(), axis=1)
        return df[mask]
    return df

# 필터가 적용된 통합 데이터셋 관리
datasets = {
    "Trend": filter_df(df_trend),
    "Blog": filter_df(df_blog),
    "News": filter_df(df_news),
    "Cafe": filter_df(df_cafe),
    "Shop": filter_df(df_shop)
}

# 분석 영역별 탭 메뉴 생성
tabs = st.tabs(["🏠 Overview", "📈 Trends", "🛍️ Shopping", "🗣️ Social & News", "🔍 Data Explorer"])

# 1. Overview(개요) 탭 구성
with tabs[0]:
    st.subheader("📋 실시간 데이터 수집 현황")
    cols = st.columns(len(datasets))  # 데이터셋 갯수만큼 컬럼 생성
    for i, (name, df) in enumerate(datasets.items()):
        cols[i].metric(name, f"{len(df)} rows")  # 각 데이터셋의 행 수 표시
    
    st.divider()
    st.write("**데이터 구조 맛보기 (Data Profiling)**")
    # 상세 조회를 위한 데이터셋 선택 상자
    sel_prof = st.selectbox("분석할 데이터 세트 선택", options=list(datasets.keys()))
    prof_df = datasets[sel_prof]
    if not prof_df.empty:
        cp1, cp2 = st.columns([1, 2])
        cp1.write("데이터 타입 및 결측치")
        # 데이터 타입과 Null 갯수 정보를 보여주는 테이블
        cp1.dataframe(prof_df.dtypes.to_frame(name='Type').join(prof_df.isnull().sum().to_frame(name='Nulls')), use_container_width=True)
        cp2.write("로우 데이터 (상위 5개)")
        cp2.dataframe(prof_df.head(5), use_container_width=True)
    else:
        st.warning("표시할 결과가 없습니다.")

# 2. Trends(트렌드) 탭 구성
with tabs[1]:
    st.subheader("📈 통합검색어 실시간 트렌드")
    df_t = datasets["Trend"]
    if not df_t.empty:
        df_t['date'] = pd.to_datetime(df_t['date'])  # 날짜 형식 변환
        # 라인 차트 생성
        fig_t = px.line(df_t, x='date', y='ratio', color='keyword', 
                       title=f"{', '.join(selected_keywords)} 검색 비중 추이", template="plotly_dark")
        st.plotly_chart(fig_t, use_container_width=True)  # 차트 렌더링
    else:
        st.info("데이터랩 트렌드 결과가 없습니다. (검색량이 적거나 기간이 짧을 수 있습니다.)")

# 3. Shopping(쇼핑) 탭 구성
with tabs[2]:
    st.subheader("🛍️ 쇼핑 카테고리 및 시장 구조")
    df_s = datasets["Shop"]
    if not df_s.empty:
        df_s['lprice'] = pd.to_numeric(df_s['lprice'], errors='coerce')  # 가격 숫자로 변환
        sc1, sc2 = st.columns(2)
        with sc1:
            st.write("**키워드별 쇼핑몰 분포 (Sunburst)**")
            # 선버스트 차트(키워드-쇼핑몰 계층) 시각화
            st.plotly_chart(px.sunburst(df_s, path=['search_keyword', 'mallName'], values='lprice', color='search_keyword'), use_container_width=True)
        with sc2:
            st.write("**카테고리 트리를 통한 시장 탐색 (Tree Map)**")
            s_clean = df_s.dropna(subset=['category1', 'category2', 'category3'])  # 카테고리 누락 데이터 제거
            if not s_clean.empty:
                # 트리맵(카테고리 계층 구조) 시각화
                st.plotly_chart(px.treemap(s_clean, path=['category1', 'category2', 'category3', 'search_keyword'], color='category1'), use_container_width=True)
            else:
                st.write("카테고리 정보가 부족합니다.")
        
        st.write("**최저가 분포 (Box Plot)**")
        # 박스 플롯을 통한 가격 범위 및 이상치 확인
        st.plotly_chart(px.box(df_s, x='search_keyword', y='lprice', color='search_keyword', points="all"), use_container_width=True)
    else:
        st.info("쇼핑 결과가 없습니다.")

# 4. Social & News(소셜 및 뉴스) 탭 구성
with tabs[3]:
    st.subheader("🗣️ 소셜 여론 및 뉴스 키워드")
    s_tabs = st.tabs(["📱 Blog", "🏠 Cafe", "📰 News"])  # 소셜 플랫폼별 내부 탭
    platforms = {"Blog": s_tabs[0], "Cafe": s_tabs[1], "News": s_tabs[2]}
    
    for name, tab in platforms.items():
        with tab:
            df_sub = datasets[name]
            if not df_sub.empty:
                ic1, ic2 = st.columns([1, 2])
                with ic1:
                    st.write("**핵심 키워드 빈도 (상위 30개)**")
                    f_df = get_word_frequency(df_sub['title'])  # 제목 기반 키워드 빈도 분석
                    if not f_df.empty:
                        # 가로 바 차트로 빈도 표시
                        fig_bar = px.bar(f_df, x='count', y='word', orientation='h', color='count', color_continuous_scale='teal')
                        fig_bar.update_layout(yaxis={'categoryorder':'total ascending'})  # 높은 순으로 정렬
                        st.plotly_chart(fig_bar, use_container_width=True)
                with ic2:
                    st.write("**게시글 리스트**")
                    df_sub_v = df_sub[['title', 'description', 'search_keyword']].copy()
                    df_sub_v['title'] = df_sub_v['title'].apply(clean_html)  # 태그 세척
                    df_sub_v['description'] = df_sub_v['description'].apply(clean_html)  # 태그 세척
                    st.dataframe(df_sub_v, use_container_width=True)  # 데이터프레임 출력
            else:
                st.info(f"{name} 결과가 없습니다.")

# 5. Explorer(탐색기) 탭 구성
with tabs[4]:
    st.subheader("🔍 통합 데이터 탐색기")
    # 로우 데이터 전체 조회를 위한 선택 창
    sel_ex = st.selectbox("조회할 데이터 소스", options=list(datasets.keys()), key="ex_final")
    df_ex = datasets[sel_ex]
    st.write(f"현재 검색 조건에 맞는 데이터: **{len(df_ex)}** 건")
    st.dataframe(df_ex, use_container_width=True)  # 데이터 전체 표 출력
    if not df_ex.empty:
        # 엑셀 호환을 위해 utf-8-sig 인코딩으로 CSV 변환
        csv_data = df_ex.to_csv(index=False, encoding='utf-8-sig').encode('utf-8-sig')
        # 다운로드 버튼 제공
        st.download_button("📥 데이터 CSV 다운로드", csv_data, f"naver_{sel_ex}_realtime.csv", "text/csv")

# 화면 하단 푸터 표기
st.divider()
st.caption(f"Powered by Naver Open API | Real-time Analysis Engine | Last Update: {datetime.now().strftime('%H:%M:%S')}")
