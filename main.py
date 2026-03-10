import FinanceDataReader as fdr
from ta.momentum import rsi
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

stocks = {'005930': '삼성전자', '000660': 'SK하이닉스'}

for code, name in stocks.items():
    df = fdr.DataReader(code)
    
    df['RSI'] = rsi(df['Close'], window=14)
    current_rsi = df['RSI'].iloc[-1]
    
    print(f"[{name}] 현재 RSI: {current_rsi:.2f}")

    if current_rsi <= 70:
        subject = f"🚨 [StockSignalBot] {name} 매수 신호"
        body = f"{name}({code})의 RSI가 {current_rsi:.2f}로 설정값 이하입니다."
        send_email(subject, body)
        print(f"{name} 알람 발송 완료")
