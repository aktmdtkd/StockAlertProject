import streamlit as st
from supabase import create_client, Client

st.set_page_config(page_title="StockSignalBot", page_icon="📈")
st.title("📈 주식 RSI 알람 서비스")
st.markdown("원하는 종목의 RSI 지표가 목표치 이하로 내려가면 이메일로 알려드립니다.")

@st.cache_resource
def init_connection():
    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_KEY"]
    return create_client(url, key)

try:
    supabase = init_connection()
except Exception as e:
    st.error("데이터베이스 연결에 실패했습니다. 관리자에게 문의하세요.")

with st.form("alert_form"):
    st.subheader("새로운 알람 등록")
    
    email = st.text_input("수신 이메일 주소", placeholder="example@gmail.com")
    stock_code = st.text_input("종목 코드 (6자리 숫자)", placeholder="예: 005930")
    target_rsi = st.number_input("목표 RSI (이 수치 이하일 때 알람)", min_value=1, max_value=100, value=30)
    
    submitted = st.form_submit_button("알람 신청하기")

if submitted:
    if email and stock_code:
        try:
            data = {"email": email, "stock_code": stock_code, "target_rsi": target_rsi}
            supabase.table("alerts").insert(data).execute()
            
            st.success(f"✅ 완료! [{stock_code}] 종목의 RSI가 {target_rsi} 이하로 떨어지면 {email}로 알려드릴게요.")
        except Exception as e:
            st.error(f"⚠️ 저장 중 오류가 발생했습니다: {e}")
    else:
        st.warning("이메일과 종목 코드를 모두 입력해 주세요.")
