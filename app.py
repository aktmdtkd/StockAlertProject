import streamlit as st
from supabase import create_client, Client
import hashlib

st.set_page_config(page_title="StockSignalBot Pro", page_icon="📈", layout="centered")

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

# 세션 상태 초기화
if 'logged_in' not in st.session_state:
    st.session_state['logged_in'] = False
if 'user_email' not in st.session_state:
    st.session_state['user_email'] = ""

st.title("📈 주식 지표 다중 알람 시스템")

INDICATORS = [
    "현재가 (Price)", "거래량 (Volume)",
    "RSI (상대강도지수)", "Stochastic_K (스토캐스틱 K)", "Williams_%R (윌리엄스 R)", "ROC (변화율)", "MFI (자금흐름지수)",
    "MACD_Line", "MACD_Signal", "ADX (평균방향성지수)", 
    "SMA_20 (20일 단순이평)", "SMA_60 (60일 단순이평)", "SMA_120 (120일 단순이평)", "SMA_200 (200일 단순이평)",
    "EMA_20 (20일 지수이평)", "EMA_60 (60일 지수이평)", "Ichimoku_Conversion (일목균형표 전환선)",
    "BB_Upper (볼린저 상단)", "BB_Lower (볼린저 하단)", "ATR (평균진폭)", "Keltner_Upper (켈트너 상단)",
    "OBV (온밸런스볼륨)", "Volume_SMA_20 (20일 평균거래량)"
]

# ==========================================
# 라우팅 로직: 비로그인 상태 (회원가입/로그인 화면)
# ==========================================
if not st.session_state['logged_in']:
    auth_tab1, auth_tab2 = st.tabs(["로그인", "신규 회원가입"])
    
    with auth_tab1:
        with st.form("login_form"):
            login_email = st.text_input("이메일")
            login_pw = st.text_input("비밀번호", type="password")
            login_submit = st.form_submit_button("로그인")
            
            if login_submit:
                if login_email and login_pw:
                    hashed_pw = hash_password(login_pw)
                    response = supabase.table("users_pro").select("*").eq("email", login_email).eq("password", hashed_pw).execute()
                    if response.data:
                        st.session_state['logged_in'] = True
                        st.session_state['user_email'] = login_email
                        st.rerun()
                    else:
                        st.error("이메일이 존재하지 않거나 비밀번호가 일치하지 않습니다.")
                else:
                    st.warning("정보를 모두 입력하십시오.")
                    
    with auth_tab2:
        with st.form("signup_form"):
            signup_email = st.text_input("사용할 이메일")
            signup_pw = st.text_input("사용할 비밀번호", type="password")
            signup_submit = st.form_submit_button("가입하기")
            
            if signup_submit:
                if signup_email and signup_pw:
                    # 중복 이메일 검증
                    check_exist = supabase.table("users_pro").select("email").eq("email", signup_email).execute()
                    if check_exist.data:
                        st.error("이미 가입된 이메일입니다.")
                    else:
                        supabase.table("users_pro").insert({"email": signup_email, "password": hash_password(signup_pw)}).execute()
                        st.success("회원가입 완료! 로그인 탭에서 접속하십시오.")
                else:
                    st.warning("정보를 모두 입력하십시오.")

# ==========================================
# 라우팅 로직: 로그인 상태 (메인 대시보드)
# ==========================================
else:
    col_user, col_logout = st.columns([4, 1])
    with col_user:
        st.write(f"👤 접속 계정: **{st.session_state['user_email']}**")
    with col_logout:
        if st.button("로그아웃"):
            st.session_state['logged_in'] = False
            st.session_state['user_email'] = ""
            st.rerun()

    st.markdown("---")
    main_tab1, main_tab2 = st.tabs(["새로운 알람 등록", "내 알람 관리"])
    user_email = st.session_state['user_email']

    # --- 알람 등록 탭 ---
    with main_tab1:
        with st.form("alert_register_form"):
            st.subheader("조건부 알람 설정")
            stock_code = st.text_input("종목 코드 (예: 005930)")
            
            col1, col2, col3 = st.columns([2, 1, 2])
            with col1:
                indicator = st.selectbox("분석 지표", INDICATORS)
            with col2:
                operator = st.selectbox("조건", ["<=", "<", ">=", ">"])
            with col3:
                target_value = st.number_input("목표 기준값", value=0.0, step=0.1)
                
            submitted = st.form_submit_button("알람 등록 실행")

        if submitted:
            if stock_code:
                # 보안 및 자원 보호: '대기 중(pending)'인 알람 개수만 카운트
                pending_count_res = supabase.table("alerts_pro").select("id", count="exact").eq("email", user_email).eq("status", "pending").execute()
                pending_count = pending_count_res.count if pending_count_res.count else 0
                
                if pending_count >= 10:
                    st.error("⚠️ 대기 중인 알람이 10개에 도달했습니다. 기존 대기 알람을 삭제 후 시도하십시오. (발송 완료된 알람은 개수에 포함되지 않습니다.)")
                else:
                    try:
                        data = {
                            "email": user_email,
                            "password": "***", # 기존 테이블 구조 유지를 위한 더미 데이터
                            "stock_code": stock_code,
                            "indicator": indicator,
                            "operator": operator,
                            "target_value": target_value,
                            "status": "pending"
                        }
                        supabase.table("alerts_pro").insert(data).execute()
                        st.success(f"✅ 등록 완료: [{stock_code}] {indicator} {operator} {target_value} (현재 대기 중: {pending_count + 1}/10)")
                    except Exception as e:
                        st.error(f"데이터베이스 기록 중 오류 발생: {e}")
            else:
                st.warning("종목 코드는 필수 입력 사항입니다.")

    # --- 알람 관리 탭 ---
    def delete_alert(alert_id):
        try:
            supabase.table("alerts_pro").delete().eq("id", alert_id).execute()
            st.success("해당 알람이 영구 삭제되었습니다.")
        except Exception as e:
            st.error(f"삭제 실패: {e}")

    with main_tab2:
        st.subheader("등록된 알람 조회 및 제어")
        
        if st.button("목록 새로고침 🔄"):
            st.rerun()

        response = supabase.table("alerts_pro").select("*").eq("email", user_email).order("created_at", desc=True).execute()
        records = response.data
        
        if not records:
            st.info("등록된 알람 기록이 없습니다.")
        else:
            pending_records = [r for r in records if r['status'] == 'pending']
            sent_records = [r for r in records if r['status'] == 'sent']
            
            st.write(f"📊 **대기 중인 알람: {len(pending_records)} / 10 개** (발송 완료: {len(sent_records)}개)")
            
            for row in records:
                status_icon = "⏳" if row['status'] == 'pending' else "✅"
                with st.expander(f"{status_icon} [{row['status'].upper()}] {row['stock_code']} - {row['indicator']} {row['operator']} {row['target_value']}"):
                    st.write(f"등록 일시: {row['created_at'][:10]}")
                    
                    if row['status'] == 'pending':
                        st.button("이 알람 삭제하기", key=f"del_{row['id']}", on_click=delete_alert, args=(row['id'],))
                    else:
                        st.write("알림이 이미 발송되어 임무가 종료된 기록입니다.")
