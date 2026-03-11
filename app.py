import streamlit as st
from supabase import create_client, Client
import pandas as pd
import hashlib

st.set_page_config(page_title="StockSignalBot Pro", page_icon="📈", layout="centered")

# 단방향 암호화 함수
def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

@st.cache_resource
def init_connection():
    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_KEY"]
    return create_client(url, key)

try:
    supabase = init_connection()
except Exception as e:
    st.error("데이터베이스 연결 실패.")
    st.stop()

st.title("📈 주식 지표 다중 알람 시스템")

tab1, tab2 = st.tabs(["새로운 알람 등록", "내 알람 관리"])

# 확장된 분석 지표 리스트
INDICATORS = [
    "현재가 (Price)", "RSI", "MACD", "SMA_20 (20일 이평선)", "SMA_60 (60일 이평선)", 
    "BB_Upper (볼린저 상단)", "BB_Lower (볼린저 하단)", "ATR (변동성)"
]

# ==========================================
# 탭 1: 알람 등록
# ==========================================
with tab1:
    with st.form("alert_register_form"):
        st.subheader("조건부 알람 설정")
        col1, col2 = st.columns(2)
        with col1:
            email = st.text_input("수신 이메일")
            stock_code = st.text_input("종목 코드 (예: 005930)")
        with col2:
            password = st.text_input("관리용 비밀번호 (PIN)", type="password")
            
        st.markdown("---")
        col3, col4, col5 = st.columns([2, 1, 2])
        with col3:
            indicator = st.selectbox("분석 지표", INDICATORS)
        with col4:
            operator = st.selectbox("조건", ["<=", "<", ">=", ">"])
        with col5:
            target_value = st.number_input("목표 기준값", value=0.0, step=0.1)
            
        submitted = st.form_submit_button("알람 등록 실행")

    if submitted:
        if email and password and stock_code:
            # 1. 현재 사용자의 등록된 알람 개수 확인 (보안 및 자원 보호)
            existing = supabase.table("alerts_pro").select("id").eq("email", email).execute()
            if len(existing.data) >= 10:
                st.error("⚠️ 한 계정당 최대 10개의 알람만 등록할 수 있습니다. '내 알람 관리'에서 기존 알람을 삭제 후 시도하십시오.")
            else:
                try:
                    data = {
                        "email": email,
                        "password": hash_password(password), # 평문 대신 해시값 저장
                        "stock_code": stock_code,
                        "indicator": indicator,
                        "operator": operator,
                        "target_value": target_value,
                        "status": "pending"
                    }
                    supabase.table("alerts_pro").insert(data).execute()
                    st.success(f"✅ 등록 완료: [{stock_code}]의 {indicator} 값이 {target_value} {operator} 일 때 메일을 발송합니다.")
                except Exception as e:
                    st.error(f"데이터베이스 기록 중 오류 발생: {e}")
        else:
            st.warning("이메일, 비밀번호, 종목 코드는 필수 입력 사항입니다.")

# ==========================================
# 탭 2: 알람 관리 (로그인 및 삭제)
# ==========================================
def delete_alert(alert_id):
    try:
        supabase.table("alerts_pro").delete().eq("id", alert_id).execute()
        st.success("해당 알람이 영구 삭제되었습니다.")
    except Exception as e:
        st.error(f"삭제 실패: {e}")

with tab2:
    st.subheader("등록된 알람 조회 및 제어")
    
    with st.form("login_form"):
        login_email = st.text_input("가입 이메일")
        login_pw = st.text_input("비밀번호", type="password")
        login_submit = st.form_submit_button("알람 목록 조회")
        
    if login_submit:
        if not login_email or not login_pw:
            st.warning("이메일과 비밀번호를 입력하십시오.")
        else:
            hashed_pw = hash_password(login_pw)
            response = supabase.table("alerts_pro").select("*").eq("email", login_email).eq("password", hashed_pw).execute()
            records = response.data
            
            if not records:
                st.info("일치하는 알람 기록이 없거나 비밀번호가 틀렸습니다.")
            else:
                st.write(f"📊 **현재 등록된 알람: {len(records)} / 10 개**")
                for row in records:
                    with st.expander(f"[{row['status'].upper()}] {row['stock_code']} - {row['indicator']} {row['operator']} {row['target_value']}"):
                        st.write(f"등록 일시: {row['created_at'][:10]}")
                        st.write(f"상태: {'대기중 (Pending)' if row['status'] == 'pending' else '발송 완료 (Sent)'}")
                        
                        if row['status'] == 'pending':
                            st.button("이 알람 삭제하기", key=f"del_{row['id']}", on_click=delete_alert, args=(row['id'],))
