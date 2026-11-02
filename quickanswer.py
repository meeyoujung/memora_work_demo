import csv
import io
import re
import streamlit as st
import numpy as np

from PIL import Image
from PIL import ImageOps
from pathlib import Path
# 한글과 영어를 읽는 OCR 모델 준비
@st.cache_resource
def load_ocr_model():
    import easyocr
    return easyocr.Reader(["ko", "en"], gpu=False, verbose=False)

# OCR로 읽은 글자에서 날짜 찾기
def extract_date(text):
    pattern = r"(\d{4})\s*년\s*(\d{1,2})\s*월\s*(\d{1,2})\s*일"

    match = re.search(pattern, text)

    if match:
        year, month, day = map(int, match.groups())

        try:
            from datetime import date
            return date(year, month, day)
        except ValueError:
            return None

    return None

# OCR로 읽은 글자에서 장소 찾기
def extract_place(text):
    pattern = r"장소\s*[:：]\s*(.+?)(?=\s*(?:참석자|준비사항)\s*[:：]|$)"

    match = re.search(pattern, text)

    if match:
        return match.group(1).strip()

    return None

# OCR로 읽은 글자에서 참석자 찾기
def extract_attendees(text):
    pattern = r"참석자\s*[:：]\s*(.+?)(?=\s*(?:준비사항|장소)\s*[:：]|$)"

    match = re.search(pattern, text)

    if match:
        return match.group(1).strip()

    return None

import html

def highlight_keywords(text, keywords):
    safe_text = html.escape(str(text))

    for word in keywords:
        if word.strip():
            safe_word = html.escape(word)
            safe_text = safe_text.replace(
                safe_word,
                f"<strong><u>{safe_word}</u></strong>"
            )

    return safe_text.replace("\n", "<br>")

# 이전 버전 CSV에 제목 열이 없으면 원본 백업 후 새 열 추가
RECORD_FIELDS = ["id", "date", "category", "title", "place", "branch", "attendees", "content"]

def ensure_record_schema():
    """Demo stores records in each visitor's session, not on shared disk."""
    if "demo_records" not in st.session_state:
        st.session_state["demo_records"] = [dict(r) for r in DEMO_RECORDS]
    if "demo_photos" not in st.session_state:
        st.session_state["demo_photos"] = {}

DEMO_RECORDS = [
    {"id":"001","date":"2026-10-21","category":"회의","title":"신제품 기획 회의","place":"본사 회의실","branch":"미확인","attendees":"기획팀","content":"신제품 출시 일정과 다음 주 보고 자료 준비 사항을 확인했다."},
    {"id":"002","date":"2026-10-23","category":"식당","title":"조용한 일식집 예약","place":"예시 일식당","branch":"강남점","attendees":"방문객 2명","content":"조용한 룸이 있는 일식당을 점심 장소로 검토했다."},
    {"id":"003","date":"2026-10-27","category":"예약","title":"출장 교통편 확인","place":"서울역","branch":"미확인","attendees":"출장자 1명","content":"출장 일정과 교통편 예약 확인 사항을 정리했다."},
]

def delete_record(record_id):
    st.session_state["demo_records"] = [r for r in st.session_state["demo_records"] if r["id"] != record_id]
    st.session_state["demo_photos"].pop(str(record_id), None)

st.set_page_config(
    page_title="MEMORA WORK",
    page_icon="💙",
    layout="wide"
)

if "current_page" not in st.session_state:
    st.session_state["current_page"] = "홈"



st.markdown("""<style>
@import url('https://cdn.jsdelivr.net/gh/orioncactus/pretendard/dist/web/static/pretendard.css');
:root{--blue:#3478f6;--navy:#112346;--muted:#7486a5;--border:#e2ebf9}
html,body,[data-testid="stApp"],button,input,textarea{font-family:Pretendard,sans-serif!important}
[data-testid="stApp"]{background:#f6f9ff;color:var(--navy)}
[data-testid="stSidebar"]{background:linear-gradient(155deg,#f9fbff,#eef5ff);border-right:1px solid #eaf0fa}
[data-testid="stSidebar"] [data-testid="stVerticalBlock"]{gap:.45rem}
[data-testid="stSidebar"] .stButton>button{justify-content:flex-start;text-align:left;min-height:43px;border:0;border-radius:11px;background:transparent;color:#263b61;padding-left:15px;font-weight:570}
[data-testid="stSidebar"] .stButton>button:hover{background:#e8f0ff;color:#2564d4}
[data-testid="stMainBlockContainer"]{max-width:1150px;padding-top:2.3rem;padding-bottom:5rem}
h1,h2,h3{color:#112346!important;letter-spacing:-.045em!important}h1 a,h2 a,h3 a{display:none!important}
.memora-brand{font-size:16px;font-weight:800;letter-spacing:-.03em;margin:16px 0 30px;color:#122448}.memora-brand span{color:#3879f4;margin-right:8px}
.memora-tag{font-size:11px;font-weight:750;letter-spacing:1.15px;color:#6e83aa;margin:8px 0 12px}
.memora-hero h1{font-size:clamp(42px,4.2vw,59px);font-weight:790;line-height:1.08;margin:0 0 14px;letter-spacing:-.065em!important}
.memora-hero p{color:#687c9c;font-size:15px;margin:0 0 27px}
.memora-page-title{font-size:32px;font-weight:760;margin:0 0 8px}.memora-page-sub{font-size:14px;color:#7486a5;margin:0 0 23px}
.memora-section-row{display:flex;justify-content:space-between;align-items:center;margin:37px 0 15px}.memora-section-row h3{font-size:21px;font-weight:750;margin:0}.memora-section-row small{font-size:12px;color:#6d84ad}
[data-testid="stTextInput"] [data-baseweb="input"]{background:white!important;border:1px solid #dce7f9!important;border-radius:12px!important;min-height:48px;box-shadow:0 4px 16px #1d4b9707}
[data-testid="stTextInput"] input{min-height:46px;padding:10px 15px;color:#23385d!important}
.stButton>button[kind="primary"],[data-testid="stFormSubmitButton"] button[kind="primary"]{background:linear-gradient(100deg,#4a84ff,#2f70ef)!important;color:white!important;border:0!important;box-shadow:0 5px 13px #3e77ed24!important}
.st-key-home_search_button button,.st-key-search_go button{min-height:48px!important;border-radius:12px!important}
.memora-card{background:white;border:1px solid #e6edf8;border-radius:14px;overflow:hidden;box-shadow:0 5px 16px #264e8b08;height:100%;min-height:215px}
.memora-card-photo{height:113px;background:linear-gradient(140deg,#edf4ff,#f9fbff);display:flex;align-items:center;justify-content:center;overflow:hidden}
.memora-card-photo img{width:100%;height:100%;object-fit:cover}.memora-card-placeholder{font-size:30px;color:#a9bfdf}
.memora-card-body{padding:13px 14px 17px}.memora-card-title{font-size:14px;font-weight:730;color:#1b3056;margin:0 0 7px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.memora-card-date{font-size:12px;color:#8192af;margin:0 0 9px}.memora-card-summary{font-size:12px;color:#6d7e9b;line-height:1.6;display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical;overflow:hidden;overflow-wrap:anywhere}
.memora-result{display:flex;gap:16px;align-items:center;background:white;border:1px solid #e9eff8;border-radius:13px;padding:9px 12px;margin:0 0 8px;min-height:86px;box-shadow:0 2px 10px #294c8006}
.memora-result-thumb{width:102px;height:66px;flex:none;background:linear-gradient(140deg,#edf4ff,#f9fbff);border-radius:9px;overflow:hidden;display:flex;align-items:center;justify-content:center;color:#a9bfdf}
.memora-result-thumb img{width:100%;height:100%;object-fit:cover}.memora-result-text{min-width:0;flex:1}.memora-result-title{font-weight:740;font-size:14px;color:#18315a;margin-bottom:4px}.memora-result-meta{font-size:12px;color:#7a8dad;margin-bottom:4px}.memora-result-desc{font-size:12px;color:#657897;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.memora-count{font-size:13px;color:#7186a6;margin:16px 0 12px}.memora-panel{background:#fff;border:1px solid #e8effa;border-radius:16px;padding:18px 20px}
[data-testid="stTabs"] [data-baseweb="tab-list"]{background:#f0f5ff;border-radius:12px;padding:4px;gap:5px}
[data-testid="stTabs"] button[role="tab"]{border-radius:9px!important;flex:1;font-weight:650}
[data-testid="stTabs"] button[aria-selected="true"]{background:white;color:#286cf2!important}
[data-testid="stSelectbox"] [data-baseweb="select"]>div{border-radius:11px;background:white;border-color:#e2ebf9}
[data-testid="stForm"]{background:#fff;border:1px solid #e6edf8;border-radius:16px;padding:20px}
/* v6: 입력 화면 B안 — 여유로운 세로 입력 폼 */
.st-key-add_record_form, .st-key-photo_record_form{max-width:760px;margin:12px auto 0}
.st-key-add_record_form [data-testid="stForm"], .st-key-photo_record_form [data-testid="stForm"]{padding:28px 30px 30px;border-radius:18px;box-shadow:0 5px 20px rgba(38,78,139,.035)}
.st-key-add_record_form [data-testid="stWidgetLabel"], .st-key-photo_record_form [data-testid="stWidgetLabel"]{font-weight:650;color:#23375a}
.st-key-add_record_form textarea, .st-key-photo_record_form textarea{border-radius:12px!important}
.st-key-add_record_form [data-testid="stFormSubmitButton"] button, .st-key-photo_record_form [data-testid="stFormSubmitButton"] button{min-height:49px;border-radius:12px;font-weight:700}

hr{border-color:#eaf0f8!important}
.memora-empty{background:#fff;border:1px solid #e6edf8;border-radius:16px;padding:42px 24px;text-align:center;margin:18px 0 14px}
.memora-empty-icon{width:52px;height:52px;border-radius:16px;background:#f0f5ff;color:#4b80e9;font-size:25px;display:flex;align-items:center;justify-content:center;margin:0 auto 15px}
.memora-empty-title{font-size:17px;font-weight:750;color:#1b3056;margin:0 0 8px}
.memora-empty-desc{font-size:13px;color:#7c8ca7;line-height:1.7;margin:0}
@media(max-width:800px){[data-testid="stMainBlockContainer"]{padding-top:1.2rem}.memora-hero h1{font-size:40px}.memora-card-photo{height:95px}}
</style>""", unsafe_allow_html=True)

import base64
from datetime import datetime

def safe(value):
    return html.escape(str(value or ""))

def record_photo(record):
    return st.session_state.get("demo_photos", {}).get(str(record.get("id", "")))

def photo_html(record):
    photo = record_photo(record)
    if photo:
        encoded = base64.b64encode(photo).decode("ascii")
        return f'<img src="data:image/png;base64,{encoded}" alt="기록 원본 사진">'
    return '<span class="memora-card-placeholder">▤</span>'

def card_html(record):
    title = safe(record.get("title") or (record.get("place") if record.get("place") not in ("", "미확인") else record.get("category", "업무 기록")))
    return f"""<div class="memora-card"><div class="memora-card-photo">{photo_html(record)}</div><div class="memora-card-body"><div class="memora-card-title">{title}</div><div class="memora-card-date">{safe(record.get('date'))}</div><div class="memora-card-summary">{safe(record.get('content'))}</div></div></div>"""

def result_html(record):
    title = safe(record.get("title") or (record.get("place") if record.get("place") not in ("", "미확인") else record.get("category", "업무 기록")))
    return f"""<div class="memora-result"><div class="memora-result-thumb">{photo_html(record)}</div><div class="memora-result-text"><div class="memora-result-title">{title}</div><div class="memora-result-meta">{safe(record.get('date'))} · {safe(record.get('category'))}</div><div class="memora-result-desc">{safe(record.get('content'))}</div></div><span style="color:#7990b3;font-size:20px">›</span></div>"""

def filtered_records(items, query, category, order):
    words = [w for w in re.sub(r"[,?!]", " ", query).split() if w not in ("찾아줘", "알려줘", "보여줘", "참석한", "참석했던")]
    matches = []
    for r in items:
        if category != "모든 카테고리" and r.get("category") != category:
            continue
        haystack = " ".join(str(r.get(k, "")) for k in ("date", "category", "title", "place", "branch", "attendees", "content"))
        if words and not all(w in haystack for w in words):
            continue
        matches.append(r)
    matches.sort(key=lambda r: r.get("date", ""), reverse=order == "최신순")
    return matches

def empty_state(icon, title, description):
    """데이터가 없는 화면에 공통으로 표시하는 안내 카드."""
    st.markdown(
        '<div class="memora-empty">'
        f'<div class="memora-empty-icon">{safe(icon)}</div>'
        f'<div class="memora-empty-title">{safe(title)}</div>'
        f'<p class="memora-empty-desc">{safe(description)}</p>'
        '</div>',
        unsafe_allow_html=True,
    )

def detail_panel(record, prefix):
    rid = str(record.get("id", ""))
    with st.expander("상세 내용 · 관리", expanded=False):
        st.write("**제목:**", record.get("title") or "(제목 없음)")
        st.write("**날짜:**", record.get("date", ""))
        st.write("**종류:**", record.get("category", ""))
        st.write("**장소:**", record.get("place", ""))
        st.write("**지점:**", record.get("branch", ""))
        if record.get("attendees"):
            st.write("**참석자:**", record["attendees"])
        st.write("**업무 내용:**", record.get("content", ""))
        p = record_photo(record)
        if p:
            st.image(p, width=330)
        if st.session_state.get("delete_target") == rid:
            st.warning("이 기록을 정말 삭제할까요?")
            yes, no = st.columns(2)
            if yes.button("삭제 확인", key=f"{prefix}_yes_{rid}"):
                delete_record(rid)
                st.session_state["delete_target"] = None
                st.rerun()
            if no.button("취소", key=f"{prefix}_no_{rid}"):
                st.session_state["delete_target"] = None
                st.rerun()
        elif st.button("기록 삭제", key=f"{prefix}_delete_{rid}"):
            st.session_state["delete_target"] = rid
            st.rerun()

with st.sidebar:
    st.markdown('<div class="memora-brand"><span>♥</span> MEMORA WORK</div>', unsafe_allow_html=True)
    menus = [("홈", ":material/home:"), ("기록 검색", ":material/search:"), ("새 기록", ":material/add:"), ("전체 기록", ":material/description:")]
    for name, icon in menus:
        label = "새 기록 추가" if name == "새 기록" else name
        if st.button(label, icon=icon, use_container_width=True, type="primary" if st.session_state["current_page"] == name else "secondary", key=f"nav_{name}"):
            st.session_state["current_page"] = name
            st.rerun()

ensure_record_schema()
records = st.session_state["demo_records"]
photo_links = {}
st.sidebar.caption("체험용 · 기록은 이 브라우저 세션에서만 유지됩니다. 실제 업무 자료를 업로드하지 마세요.")

page = st.session_state["current_page"]
if page == "홈":
    st.markdown('<div class="memora-hero"><div class="memora-tag">YOUR PERSONAL WORKSPACE</div><h1>Make your work<br>unforgettable.</h1><p>흩어진 업무 기록을 검색 가능한 기억으로.</p></div>', unsafe_allow_html=True)
    search_col, button_col = st.columns([5.4, 1], gap="small", vertical_alignment="bottom")
    with search_col:
        home_query = st.text_input("홈 검색", placeholder="⌕   예: 김 부장이 참석한 회의 찾아줘", label_visibility="collapsed", key="home_query")
    with button_col:
        clicked = st.button("검색하기", type="primary", icon=":material/search:", use_container_width=True, key="home_search_button")
    if clicked:
        st.session_state["search_query"] = home_query
        st.session_state["search_active"] = True
        st.session_state["current_page"] = "기록 검색"
        st.rerun()
    st.markdown('<div class="memora-section-row"><h3>최근 업무 기록</h3><small>RECENT RECORDS</small></div>', unsafe_allow_html=True)
    recent = sorted(records, key=lambda r:r.get("date", ""), reverse=True)[:4]
    if not recent:
        empty_state("✦", "아직 저장된 업무 기록이 없어요", "첫 번째 업무 기록을 추가하고, 필요한 순간 다시 찾아보세요.")
        if st.button("+ 첫 기록 추가하기", type="primary", key="home_first_record"):
            st.session_state["current_page"] = "새 기록"
            st.rerun()
    else:
        cols = st.columns(4, gap="medium")
        for col, rec in zip(cols, recent):
            with col:
                st.markdown(card_html(rec), unsafe_allow_html=True)
        st.write("")
        if st.button("전체보기 →", key="go_archive"):
            st.session_state["current_page"] = "전체 기록"
            st.rerun()

if page == "기록 검색":
    st.markdown('<h1 class="memora-page-title">기록 검색</h1><p class="memora-page-sub">필요한 업무 기록을 언제든 다시 찾아보세요.</p>', unsafe_allow_html=True)
    left, right = st.columns([5.4, 1], gap="small", vertical_alignment="bottom")
    with left:
        query = st.text_input("검색어", value=st.session_state.pop("search_query", ""), placeholder="⌕   예: 프로젝트 일정, 김 부장, 마케팅 회의", label_visibility="collapsed", key="search_query_input")
    with right:
        go = st.button("검색하기", type="primary", icon=":material/search:", use_container_width=True, key="search_go")
    if go:
        st.session_state["search_active"] = True
    f1, f2, f3 = st.columns([1.3, 1.3, 1])
    with f1:
        date_filter = st.selectbox("기간", ["모든 기간", "최근 7일", "최근 30일", "최근 1년"], label_visibility="collapsed", key="search_date")
    with f2:
        cat = st.selectbox("카테고리", ["모든 카테고리"] + sorted(set(r.get("category", "기타") for r in records)), label_visibility="collapsed", key="search_category")
    with f3:
        order = st.selectbox("정렬", ["최신순", "오래된순"], label_visibility="collapsed", key="search_order")
    if st.session_state.get("search_active", False) or cat != "모든 카테고리":
        found = filtered_records(records, query, cat, order)
        if date_filter != "모든 기간":
            from datetime import date, timedelta
            days = {"최근 7일":7, "최근 30일":30, "최근 1년":365}[date_filter]
            threshold = date.today() - timedelta(days=days)
            def in_range(r):
                try: return date.fromisoformat(r.get("date", "")) >= threshold
                except ValueError: return False
            found = [r for r in found if in_range(r)]
        st.markdown(f'<div class="memora-count">검색 결과 {len(found)}개</div>', unsafe_allow_html=True)
        if not found:
            empty_state("⌕", "검색 결과가 없어요", "검색어를 바꾸거나 기간·카테고리 조건을 조정해 보세요.")
        for rec in found:
            st.markdown(result_html(rec), unsafe_allow_html=True)
            detail_panel(rec, "search")
    else:
        empty_state("⌕", "어떤 업무 기록을 찾고 계신가요?", "제목, 장소, 참석자 또는 업무 내용으로 검색해 보세요.")

if page == "전체 기록":
    st.markdown('<h1 class="memora-page-title">전체 업무 기록</h1><p class="memora-page-sub">지금까지 저장한 모든 업무 기록을 확인하고 관리하세요.</p>', unsafe_allow_html=True)
    query = st.text_input("기록 검색", placeholder="⌕   기록 검색하기...", label_visibility="collapsed", key="archive_query")
    a, b, c = st.columns([1.3, 1.3, 1])
    with a:
        period = st.selectbox("기간", ["모든 기간", "최근 7일", "최근 30일", "최근 1년"], label_visibility="collapsed", key="archive_period")
    with b:
        cat = st.selectbox("카테고리", ["모든 카테고리"] + sorted(set(r.get("category", "기타") for r in records)), label_visibility="collapsed", key="archive_cat")
    with c:
        order = st.selectbox("정렬", ["최신순", "오래된순"], label_visibility="collapsed", key="archive_order")
    found = filtered_records(records, query, cat, order)
    if period != "모든 기간":
        from datetime import date, timedelta
        threshold = date.today() - timedelta(days={"최근 7일":7,"최근 30일":30,"최근 1년":365}[period])
        def in_range(r):
            try: return date.fromisoformat(r.get("date", "")) >= threshold
            except ValueError: return False
        found = [r for r in found if in_range(r)]
    st.markdown(f'<div class="memora-count">총 {len(found)}개의 기록</div>', unsafe_allow_html=True)
    if not found:
        if not records:
            empty_state("▤", "아직 저장된 기록이 없어요", "새 기록을 추가하면 이곳에서 한눈에 확인할 수 있어요.")
            if st.button("+ 첫 기록 추가하기", type="primary", key="archive_first_record"):
                st.session_state["current_page"] = "새 기록"
                st.rerun()
        else:
            empty_state("⌕", "조건에 맞는 기록이 없어요", "검색어를 지우거나 필터를 변경해 보세요.")
    for start in range(0, len(found), 4):
        cols = st.columns(4, gap="medium")
        for col, rec in zip(cols, found[start:start+4]):
            with col:
                st.markdown(card_html(rec), unsafe_allow_html=True)
                detail_panel(rec, "archive")

if page == "새 기록":
    st.markdown('<h1 class="memora-page-title">새 기록 추가</h1><p class="memora-page-sub">지금의 업무를 기록하고, 나중에 다시 찾아보세요.</p>', unsafe_allow_html=True)
    tab1, tab2 = st.tabs(["✏️ 직접 입력", "📷 사진으로 추가"])
    with tab1:
        with st.form("add_record_form", clear_on_submit=True):
            title = st.text_input("제목", placeholder="예: 11월 마케팅 회의")
            rec_date = st.date_input("날짜")
            category = st.selectbox("카테고리", ["식당", "회의", "예약", "일정", "기타"])
            place = st.text_input("장소", placeholder="예: 본사 3층 회의실")
            attendees = st.text_input("참석자", placeholder="예: 김 부장, 이 대리")
            branch = st.text_input("지점 (선택)", placeholder="예: 강남점 · 해당 없으면 비워두세요")
            content = st.text_area("내용", placeholder="업무 내용을 자세히 기록해 주세요...", height=165)
            submitted = st.form_submit_button("기록 저장하기", type="primary", use_container_width=True)
            if submitted:
                if not content.strip():
                    st.warning("업무 내용을 입력해 주세요.")
                else:
                    next_id = max((int(r["id"]) for r in records if str(r.get("id", "")).isdigit()), default=0) + 1
                    row = {"id":f"{next_id:03d}","date":str(rec_date),"category":category,"title":title.strip(),"place":place.strip() or "미확인","branch":branch.strip() or "미확인","attendees":attendees.strip(),"content":content.strip()}
                    st.session_state["demo_records"].append(row)
                    st.success("업무 기록이 저장됐어요! 💙")
    with tab2:
        st.write("📸 종이 다이어리, 포스트잇, 출력물 사진을 등록해 보세요.")
        st.caption("데모 전용: 개인정보·실제 회사 자료는 업로드하지 마세요. OCR 첫 실행은 시간이 걸릴 수 있습니다.")

        uploaded_file = st.file_uploader(
            "업무 기록 사진 첨부",
            type=["png", "jpg", "jpeg"]
        )

        if uploaded_file is not None:
                # 사진 방향 자동 보정
                preview_image = Image.open(
                    io.BytesIO(uploaded_file.getvalue())
                )

                preview_image = ImageOps.exif_transpose(preview_image)

                # 새로운 사진을 업로드하면 회전 각도 초기화
                photo_id = hash(uploaded_file.getvalue())

                if st.session_state.get("rotation_photo_id") != photo_id:
                    st.session_state["rotation_photo_id"] = photo_id
                    st.session_state["rotation_angle"] = 0

                # 사진 회전 버튼
                col1, col2 = st.columns(2)

                with col1:
                    if st.button("↩️ 왼쪽으로 90도"):
                        st.session_state["rotation_angle"] += 90

                with col2:
                    if st.button("↪️ 오른쪽으로 90도"):
                        st.session_state["rotation_angle"] -= 90

                # 선택한 각도로 사진 회전
                rotated_image = preview_image.rotate(
                    st.session_state["rotation_angle"],
                    expand=True
                )

                st.image(
                    rotated_image,
                    caption="첨부한 사진 (방향 조정 가능)"
                )
                # 다른 사진을 업로드하면 이전 OCR 결과 초기화
                current_photo = uploaded_file.getvalue()
                photo_id = str(hash(current_photo))

                if st.session_state.get("current_photo_id") != photo_id:
                    st.session_state["current_photo_id"] = photo_id
                    st.session_state["photo_content"] = ""
                    st.session_state["photo_title"] = ""
                    st.session_state["photo_place"] = ""
                    st.session_state["photo_attendees"] = ""

                st.info("AI가 읽은 내용을 확인하고 수정한 뒤 저장해 주세요.")

                # OCR 버튼
                if st.button("🤖 AI로 글자 읽기"):
                    with st.spinner("AI가 사진 속 글자를 읽고 있어요..."):
                        try:
                            image = rotated_image.convert("RGB")
                            reader = load_ocr_model()

                            detected_text = reader.readtext(
                                np.array(image),
                                detail=0,
                                paragraph=True
                            )

                            recognized_text = "\n".join(detected_text)

                            # OCR 결과에서 날짜 자동 추출
                            detected_date = extract_date(recognized_text)

                            if detected_date is not None:
                                st.session_state["photo_date"] = detected_date

                            st.session_state["photo_content"] = recognized_text

                            # OCR 결과에서 업무 종류 자동 분류
                            if "회의" in recognized_text:
                                st.session_state["photo_category"] = "회의"

                            # OCR 결과에서 장소 자동 추출
                            detected_place = extract_place(recognized_text)

                            if detected_place is not None:
                                st.session_state["photo_place"] = detected_place
                        
                            # OCR 결과에서 참석자 자동 추출
                            detected_attendees = extract_attendees(recognized_text)

                            if detected_attendees is not None:
                                st.session_state["photo_attendees"] = detected_attendees

                            if recognized_text.strip():
                                st.success("사진 속 글자 인식이 완료됐어요! 🎉")
                            else:
                                st.warning(
                                    "글자를 찾지 못했어요. 직접 입력해 주세요."
                                )

                        except Exception as error:
                            st.error(
                                f"글자 인식 중 오류가 발생했어요: {error}"
                            )

                # 사진 기록 입력 양식 — 직접 입력과 동일한 세로 배치
                with st.form("photo_record_form"):
                    photo_title = st.text_input("제목", placeholder="예: 주간 회의", key="photo_title")
                    photo_date = st.date_input("날짜", key="photo_date")
                    photo_category = st.selectbox(
                        "카테고리", ["식당", "회의", "예약", "일정", "기타"], key="photo_category"
                    )
                    photo_place = st.text_input("장소", placeholder="예: 본사 3층 회의실", key="photo_place")
                    photo_attendees = st.text_input(
                        "참석자", placeholder="예: 김 부장, 이 대리", key="photo_attendees"
                    )
                    photo_branch = "미확인"  # 기존 사진 기록의 지점 저장 방식 유지
                    photo_content = st.text_area(
                        "AI가 읽은 업무 내용 (수정 가능)",
                        key="photo_content",
                        height=165
                    )
                    photo_source = st.selectbox(
                        "원본 유형", ["종이 다이어리", "포스트잇", "출력 일정표", "기타"]
                    )
                    photo_submitted = st.form_submit_button(
                        "사진과 기록 저장하기", type="primary", use_container_width=True
                    )

                # 기록 저장: 방문자별 세션에만 보관
                if photo_submitted:
                    if not photo_content.strip():
                        st.warning("업무 내용을 입력해 주세요.")
                    else:
                        output_buffer = io.BytesIO()
                        rotated_image.convert("RGB").save(output_buffer, format="PNG")
                        next_id = max((int(r["id"]) for r in records if str(r.get("id", "")).isdigit()), default=0) + 1
                        new_record = {
                            "id": f"{next_id:03d}", "date": str(photo_date),
                            "category": photo_category, "title": photo_title.strip(),
                            "place": photo_place.strip() or "미확인", "branch": "미확인",
                            "attendees": photo_attendees.strip(), "content": photo_content.strip()
                        }
                        st.session_state["demo_records"].append(new_record)
                        st.session_state["demo_photos"][new_record["id"]] = output_buffer.getvalue()
                        st.success(f"업무 기록 {new_record['id']}번과 사진이 저장됐어요! 🎉")
