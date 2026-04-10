# 🚀 Naver Market Intelligence Dashboard

네이버 검색 및 데이터랩 API를 활용한 실시간 시즌 가전 및 트렌드 분석 대시보드입니다.

## 🌟 주요 기능
- **실시간 키워드 분석**: 입력 즉시 트렌드 및 검색 결과 업데이트
- **고급 시각화**: Plotly 기반 트리맵, 선버스트 차트 제공
- **데이터 프로파일링**: 수집 데이터의 기술 통계 및 구조 분석
- **전역 필터링**: 수천 건의 결과 내 실시간 단어 검색

## 🛠️ Streamlit Cloud 배포 시 주의사항 (Secrets 설정)

본 프로젝트는 보안을 위해 네이버 API ID와 Secret을 **Streamlit Secrets** 기능을 통해 관리합니다. 배포 시 아래 단계를 따라 자격 증명을 입력해주세요.

1.  **Streamlit Cloud 대시보드**에 접속합니다.
2.  배포된 앱의 **Settings > Secrets** 탭으로 이동합니다.
3.  아래 내용을 복사하여 입력하고 저장합니다.

```toml
NAVER_CLIENT_ID = "여기에_당신의_클라이언트_ID_입력"
NAVER_CLIENT_SECRET = "여기에_당신의_클라이언트_시크릿_입력"
```

## 📦 구성 파일 확인
- `app.py`: 메인 대시보드 소스 코드 (한국어 주석 포함)
- `requirements.txt`: 배포 필수 의존성 라이브러리 목록
- `.gitignore`: 보안 파일(.env 등) 업로드 방지 설정

---
Developed by Antigravity AI Engine | [Naver Open API](https://developers.naver.com/main/) 기반
