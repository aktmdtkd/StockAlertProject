import FinanceDataReader as fdr
from ta.momentum import rsi
from ta.trend import macd
import pandas as pd
import os
import smtplib
import operator
from email.message import EmailMessage
from supabase import create_client, Client

# 1. 안전한 연산자 매핑 딕셔너리 (보안/효율성)
ops = {
    '<': operator.lt,
    '<=': operator.le,
    '>': operator.gt,
    '>=': operator.ge
}

def send_email(to_email, subject, body):
    user = os.environ.get('EMAIL_USER')
    pw = os.environ.get('EMAIL_PW')
    
    msg = EmailMessage()
    msg['Subject'] = subject
    msg['From'] = f"StockSignalBot Pro <{user}>"
    msg['To'] = to_email
    msg.set_content(body)
    
    with smtplib.SMTP_SSL('smtp.gmail.com', 465) as smtp:
        smtp.login(user, pw)
        smtp.send_message(msg)

# 2. Supabase 연결
url: str = os.environ.get("SUPABASE_URL")
key: str = os.environ.get("SUPABASE_KEY")
supabase: Client = create_client(url, key)

# 3. '대기중(pending)' 상태인 알람만 검출
response = supabase.table("alerts_pro").select("*").eq("status", "pending").execute()
pending_alerts = response.data

if not pending_alerts:
    print("현재 대기 중인 알람 규칙이 없습니다. 프로세스를 종료합니다.")
    exit()

print(f"총 {len(pending_alerts)}개의 대기 중인 알람을 분석합니다.")

# 4. 종목 데이터 캐싱 공간 (API 호출 최적화 방어 로직)
stock_cache = {}

for alert in pending_alerts:
    alert_id = alert['id']
    email = alert['email']
    stock_code = alert['stock_code']
    ind_type = alert['indicator']
    op_str = alert['operator']
    target_val = alert['target_value']
    
    try:
        # 데이터 로드 (캐시 우선 확인)
        if stock_code not in stock_cache:
            df = fdr.DataReader(stock_code)
            stock_cache[stock_code] = df
        else:
            df = stock_cache[stock_code]
            
        # 데이터 부족 시 스킵
        if len(df) < 60: 
            continue

        # 지표 동적 할당
        current_value = None
        if ind_type == 'RSI':
            current_value = rsi(df['Close'], window=14).iloc[-1]
        elif ind_type == 'MACD':
            current_value = macd(df['Close']).iloc[-1]
        elif ind_type == 'SMA_20':
            current_value = df['Close'].rolling(window=20).mean().iloc[-1]
        elif ind_type == 'SMA_60':
            current_value = df['Close'].rolling(window=60).mean().iloc[-1]
        else:
            print(f"[경고] 지원하지 않는 지표 규격: {ind_type}")
            continue
            
        # NaN(결측치) 방어 로직
        if pd.isna(current_value):
            continue

        print(f"[{stock_code}] {ind_type}: {current_value:.2f} (설정 조건: {op_str} {target_val})")

        # 조건 평가 객체 호출
        compare_func = ops.get(op_str)
        
        # 5. 조건 일치 시 트랜잭션 실행
        if compare_func and compare_func(current_value, target_val):
            # 5-1. 이메일 발송 (액추에이터 작동)
            subject = f"🚨 [StockSignalBot Pro] {stock_code} {ind_type} 지표 도달 경보"
            body = f"종목코드: {stock_code}\n현재 {ind_type} 수치: {current_value:.2f}\n설정 조건: {op_str} {target_val}\n\n시스템이 해당 조건의 도달을 확인했습니다. 시장 대응을 준비하십시오."
            
            send_email(email, subject, body)
            print(f"  -> {email} 수신자에게 경보 발송 완료.")
            
            # 5-2. DB 상태 업데이트 (생명주기 마감 처리)
            # 메일 발송이 성공적으로 끝난 후(직렬화)에만 DB를 업데이트하여 무결성 유지
            supabase.table("alerts_pro").update({"status": "sent"}).eq("id", alert_id).execute()
            print(f"  -> DB 데이터(ID: {alert_id}) 상태 'sent' 로 전이 완료.")
            
    except Exception as e:
        print(f"[오류] {stock_code} 데이터 처리 중 시스템 예외 발생: {e}")

print("분석 사이클이 종료되었습니다.")
