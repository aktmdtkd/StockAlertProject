import FinanceDataReader as fdr
from ta.momentum import rsi
import os
import smtplib
from email.message import EmailMessage
from supabase import create_client, Client

# 이메일 발송 함수 (받는 사람 변수 추가)
def send_email(to_email, subject, body):
    user = os.environ.get('EMAIL_USER')
    pw = os.environ.get('EMAIL_PW')
    
    msg = EmailMessage()
    msg['Subject'] = subject
    msg['From'] = f"StockSignalBot <{user}>"
    msg['To'] = to_email
    msg.set_content(body)
    
    with smtplib.SMTP_SSL('smtp.gmail.com', 465) as smtp:
        smtp.login(user, pw)
        smtp.send_message(msg)

url: str = os.environ.get("SUPABASE_URL")
key: str = os.environ.get("SUPABASE_KEY")
supabase: Client = create_client(url, key)

response = supabase.table("alerts").select("*").execute()
alert_list = response.data

if not alert_list:
    print("DB에 등록된 알람이 없습니다. 작업을 종료합니다.")
    exit()

print(f"총 {len(alert_list)}개의 알람 설정을 DB에서 불러왔습니다.")

for alert in alert_list:
    user_email = alert['email']
    stock_code = alert['stock_code']
    target_rsi = alert['target_rsi']
    
    try:
        df = fdr.DataReader(stock_code)
        df['RSI'] = rsi(df['Close'], window=14)
        current_rsi = df['RSI'].iloc[-1]
        
        print(f"[{stock_code}] 현재 RSI: {current_rsi:.2f} (목표: {target_rsi} 이하)")

        if current_rsi <= target_rsi:
            subject = f"🚨 [StockSignalBot] {stock_code} 매수 신호"
            body = f"요청하신 종목({stock_code})의 RSI가 {current_rsi:.2f}로 설정하신 목표값({target_rsi}) 이하로 내려왔습니다!\n\n시장 상황을 확인해 보세요."
            
            send_email(user_email, subject, body)
            print(f"  -> {user_email} 님에게 알람 발송 완료!")
            
    except Exception as e:
        print(f"[{stock_code}] 처리 중 오류 발생: {e}")

print("모든 알람 처리가 완료되었습니다.")
