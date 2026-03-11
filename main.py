import FinanceDataReader as fdr
from ta.momentum import rsi
from ta.trend import macd
from ta.volatility import BollingerBands, average_true_range
import pandas as pd
import os
import smtplib
import operator
from email.message import EmailMessage
from supabase import create_client, Client

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

url: str = os.environ.get("SUPABASE_URL")
key: str = os.environ.get("SUPABASE_KEY")
supabase: Client = create_client(url, key)

response = supabase.table("alerts_pro").select("*").eq("status", "pending").execute()
pending_alerts = response.data

if not pending_alerts:
    print("대기 중인 알람 규칙이 없습니다.")
    exit()

stock_cache = {}

for alert in pending_alerts:
    alert_id = alert['id']
    email = alert['email']
    stock_code = alert['stock_code']
    ind_type = alert['indicator']
    op_str = alert['operator']
    target_val = alert['target_value']
    
    try:
        if stock_code not in stock_cache:
            df = fdr.DataReader(stock_code)
            stock_cache[stock_code] = df
        else:
            df = stock_cache[stock_code]
            
        if len(df) < 60: 
            continue

        # 확장된 지표 동적 할당 로직
        current_value = None
        
        if ind_type == "현재가 (Price)":
            current_value = df['Close'].iloc[-1]
        elif ind_type == "RSI":
            current_value = rsi(df['Close'], window=14).iloc[-1]
        elif ind_type == "MACD":
            current_value = macd(df['Close']).iloc[-1]
        elif ind_type == "SMA_20 (20일 이평선)":
            current_value = df['Close'].rolling(window=20).mean().iloc[-1]
        elif ind_type == "SMA_60 (60일 이평선)":
            current_value = df['Close'].rolling(window=60).mean().iloc[-1]
        elif ind_type == "BB_Upper (볼린저 상단)":
            indicator_bb = BollingerBands(close=df['Close'], window=20, window_dev=2)
            current_value = indicator_bb.bollinger_hband().iloc[-1]
        elif ind_type == "BB_Lower (볼린저 하단)":
            indicator_bb = BollingerBands(close=df['Close'], window=20, window_dev=2)
            current_value = indicator_bb.bollinger_lband().iloc[-1]
        elif ind_type == "ATR (변동성)":
            current_value = average_true_range(high=df['High'], low=df['Low'], close=df['Close'], window=14).iloc[-1]
        else:
            print(f"[경고] 미지원 지표: {ind_type}")
            continue
            
        if pd.isna(current_value):
            continue

        compare_func = ops.get(op_str)
        
        if compare_func and compare_func(current_value, target_val):
            subject = f"🚨 [StockSignalBot] {stock_code} {ind_type} 조건 도달"
            body = f"종목코드: {stock_code}\n기준 지표: {ind_type}\n현재 수치: {current_value:.2f}\n설정 조건: {op_str} {target_val}\n\n시스템 분석 결과 조건이 충족되었습니다."
            
            send_email(email, subject, body)
            supabase.table("alerts_pro").update({"status": "sent"}).eq("id", alert_id).execute()
            print(f"[{stock_code}] {email} 전송 및 DB 상태 업데이트 완료.")
            
    except Exception as e:
        print(f"[오류] {stock_code} 처리 중 예외 발생: {e}")

print("분석 사이클 종료.")
