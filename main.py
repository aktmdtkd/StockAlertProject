import FinanceDataReader as fdr
import pandas_ta as ta
import os
import smtplib
from email.message import EmailMessage

def send_email(subject, body):
    user = os.environ.get('EMAIL_USER')
    pw = os.environ.get('EMAIL_PW')
    
    msg = EmailMessage()
    msg['Subject'] = subject
    msg['From'] = f"StockSignalBot <{user}>"
    msg['To'] = user
    msg.set_content(body)
    
    with smtplib.SMTP_SSL('smtp.gmail.com', 465) as smtp:
        smtp.login(user, pw)
        smtp.send_message(msg)

target_stock = '005930'

df = fdr.DataReader(target_stock)
df['RSI'] = ta.rsi(df['Close'], length=14)
current_rsi = df['RSI'].iloc[-1]

print(f"삼성전자 현재 RSI: {current_rsi:.2f}")

if current_rsi <= 70:
    subject = f"🚨 [StockSignalBot] 삼성전자 지표 알람"
    body = f"삼성전자의 RSI가 {current_rsi:.2f}입니다. 설정을 확인하세요."
    send_email(subject, body)
    print("알람 메일 발송 완료!")
