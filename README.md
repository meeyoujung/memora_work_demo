# MEMORA WORK — 심사용 체험 버전

- 기존 원본과 별도인 **공개 데모**입니다.
- 샘플 데이터는 모두 가상 예시입니다.
- 직접 입력, 사진 업로드/회전, OCR, 검색, 삭제 기능을 체험할 수 있습니다.
- 모든 입력 기록 및 사진은 방문자별 Streamlit 세션 메모리에만 저장됩니다. 새 세션/서버 재시작 시 사라집니다. 영구 보관용이 아닙니다.
- 실제 회사 업무 자료, 개인 정보, 비밀 문서를 업로드하지 마세요.
- EasyOCR는 최초 실행 시 모델 파일을 내려받으며 무료 클라우드의 메모리/시간 제한으로 실패할 수 있습니다.

## 배포
1. GitHub에 새 저장소 `memora-work-demo`를 생성하고 이 폴더 **안의 파일들만** 업로드하세요. (원본 CSV, 사진, .venv 업로드 금지)
2. https://share.streamlit.io/ 에 GitHub로 로그인하고 **Create app** → 저장소 선택 → main file path `quickanswer.py` → Deploy.
3. Python 3.12를 선택할 수 있다면 3.12로 설정하세요.
4. 발급된 주소에서 입력/검색/사진/OCR을 확인한 후 제출하세요.

## 로컬 실행
`pip install -r requirements.txt` 다음 `streamlit run quickanswer.py`
