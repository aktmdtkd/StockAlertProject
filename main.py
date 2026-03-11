import FinanceDataReader as fdr
import pandas as pd
import os
import smtplib
import operator
import datetime
from email.message import EmailMessage
from supabase import create_client, Client

# ta 라이브러리의 각 모듈 임포트
from ta.momentum import rsi, stochastic_oscillator, williams_r, roc, money_flow_index
from ta.trend import macd, macd_signal, adx, sma_indicator, ema_indicator, ichimoku_conversion_line
from ta.volatility import BollingerBands, average_true_range, KeltnerChannel
from ta.volume import on_balance_volume

ops = {
    '<': operator.lt, '<=': operator.le,
    '>': operator.gt, '>=': operator.ge
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

# 지표 동적 매핑 엔진 (수십 개의 if-elif를 대체)
def calculate_indicator(df, ind_type):
    try:
        if ind_type == "현재가 (Price)": return df['Close'].iloc[-1]
        elif ind_type == "거래량 (Volume)": return df['Volume'].iloc[-1]
        
        # 모멘텀
        elif ind_type == "RSI (상대강도지수)": return rsi(df['Close'], window=14).iloc[-1]
        elif ind_type == "Stochastic_K (스토캐스틱 K)": return stochastic_oscillator(high=df['High'], low=df['Low'], close=df['Close'], window=14, smooth_window=3).iloc[-1]
        elif ind_type == "Williams_%R (윌리엄스 R)": return williams_r(high=df['High'], low=df['Low'], close=df['Close'], lbp=14).iloc[-1]
        elif ind_type == "ROC (변화율)": return roc(df['Close'], window=12).iloc[-1]
        elif ind_type == "MFI (자금흐름지수)": return money_flow_index(high=df['High'], low=df['Low'], close=df['Close'], volume=df['Volume'], window=14).iloc[-1]
        
        # 추세
        elif ind_type == "MACD_Line": return macd(df['Close']).iloc[-1]
        elif ind_type == "MACD_Signal": return macd_signal(df['Close']).iloc[-1]
        elif ind_type == "ADX (평균방향성지수)": return adx(high=df['High'], low=df['Low'], close=df['Close'], window=14).iloc[-1]
        elif ind_type == "SMA_20 (20일 단순이평)": return sma_indicator(df['Close'], window=20).iloc[-1]
        elif ind_type == "SMA_60 (60일 단순이평)": return sma_indicator(df['Close'], window=60).iloc[-1]
        elif ind_type == "SMA_120 (120일 단순이평)": return sma_indicator(df['Close'], window=120).iloc[-1]
        elif ind_type == "SMA_200 (200일 단순이평)": return sma_indicator(df['Close'], window=200).iloc[-1]
        elif ind_type == "EMA_20 (20일 지수이평)": return ema_indicator(df['Close'], window=20).iloc[-1]
        elif ind_type == "EMA_60 (60일 지수이평)": return ema_indicator(df['Close'], window=60).iloc[-1]
        elif ind_type == "Ichimoku_Conversion (일목균형표 전환선)": return ichimoku_conversion_line(high=df['High'], low=df['Low'], window1=9, window2=26).iloc[-1]
        
        # 변동성
        elif ind_type == "BB_Upper (볼린저 상단)": return BollingerBands(close=df['Close'], window=20, window_dev=2).bollinger_hband().iloc[-1]
        elif ind_type == "BB_Lower (볼린저 하단)": return BollingerBands(close=df['Close'], window=20, window_dev=2).bollinger_lband().iloc[-1]
        elif ind_type == "ATR (평균진폭)": return average_true_range(high=df['High'], low=df['Low'], close=df['Close'], window=14).iloc[-1]
        elif ind_type == "Keltner_Upper (켈트너 상단)": return KeltnerChannel(high=df['High'], low=df['Low'], close=df['Close'], window=20).keltner_channel_hband().iloc[-1]
        
        # 거래량
        elif ind_type == "OBV (온밸런스볼륨)": return on_balance_volume(close=df['Close'], volume=df['Volume']).iloc[-1]
        elif ind_type == "Volume_SMA_20 (20일 평균거래량)": return sma_indicator(df['Volume'], window=20).iloc[-1]
        
        else: return None
    except Exception as e:
        print(f"지표 계산 오류 ({ind_type}): {e}")
        return None

url: str = os.environ.get("SUPABASE_URL")
key: str = os.environ.get("SUPABASE_KEY")
supabase: Client = create_client(url, key)

response = supabase.table("alerts_pro").select("*").eq("status", "pending").execute()
pending_alerts = response.data

if not pending_alerts:
    print("대기 중인 알람 규칙이 없습니다.")
    exit()

stock_cache = {}
# Lookback Period 최적화: 최근 2년치 데이터만 로드 (장기 이평선 커버용)
start_date = (datetime.datetime.now() - datetime.timedelta(days=730)).strftime('%Y-%m-%d')

for alert in pending_alerts:
    alert_id = alert['id']
    email = alert['email']
    stock_code = alert['stock_code']
    ind_type = alert['indicator']
    op_str = alert['operator']
    target_val = alert['target_value']
    
    try:
        if stock_code not in stock_cache:
            df = fdr.DataReader(stock_code, start_date)
            stock_cache[stock_code] = df
        else:
            df = stock_cache[stock_code]
            
        # 200일 이평선 등을 위해 최소 200행 확보 확인
        if len(df) < 200: 
            print(f"[{stock_code}] 과거 데이터 부족 (상장 1년 미만). 일부 지표 연산 불가.")
            continue

        current_value = calculate_indicator(df, ind_type)
            
        # 레드팀 방어: NaN 값 무결성 검증
        if current_value is None or pd.isna(current_value):
            continue

        compare_func = ops.get(op_str)
        
        if compare_func and compare_func(current_value, target_val):
            subject = f"🚨 [QuantBot] {stock_code} {ind_type} 조건 돌파"
            body = f"종목코드: {stock_code}\n기준 지표: {ind_type}\n현재 수치: {current_value:,.2f}\n설정 조건: {op_str} {target_val:,.2f}\n\n시스템 분석 결과 조건이 충족되었습니다."
            
            send_email(email, subject, body)
            supabase.table("alerts_pro").update({"status": "sent"}).eq("id", alert_id).execute()
            print(f"[{stock_code}] {ind_type} 달성. {email} 전송 완료.")
            
    except Exception as e:
        print(f"[오류] {stock_code} - {ind_type} 처리 중 예외 발생: {e}")

print("분석 사이클 종료.")
