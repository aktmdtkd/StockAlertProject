import FinanceDataReader as fdr
import pandas as pd
import os
import smtplib
import operator
import datetime
from email.message import EmailMessage
from supabase import create_client, Client

# ta 라이브러리의 공식 '클래스' 임포트 (버전 호환성 확보)
from ta.momentum import RSIIndicator, StochasticOscillator, WilliamsRIndicator, ROCIndicator, MFIIndicator
from ta.trend import MACD, ADXIndicator, SMAIndicator, EMAIndicator, IchimokuIndicator
from ta.volatility import BollingerBands, AverageTrueRange, KeltnerChannel
from ta.volume import OnBalanceVolumeIndicator

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

# 클래스 기반 지표 동적 매핑 엔진 (호환성 및 안정성 강화)
def calculate_indicator(df, ind_type):
    try:
        if ind_type == "현재가 (Price)": return df['Close'].iloc[-1]
        elif ind_type == "거래량 (Volume)": return df['Volume'].iloc[-1]
        
        # 모멘텀
        elif ind_type == "RSI (상대강도지수)": return RSIIndicator(close=df['Close'], window=14).rsi().iloc[-1]
        elif ind_type == "Stochastic_K (스토캐스틱 K)": return StochasticOscillator(high=df['High'], low=df['Low'], close=df['Close'], window=14, smooth_window=3).stoch().iloc[-1]
        elif ind_type == "Williams_%R (윌리엄스 R)": return WilliamsRIndicator(high=df['High'], low=df['Low'], close=df['Close'], lbp=14).williams_r().iloc[-1]
        elif ind_type == "ROC (변화율)": return ROCIndicator(close=df['Close'], window=12).roc().iloc[-1]
        elif ind_type == "MFI (자금흐름지수)": return MFIIndicator(high=df['High'], low=df['Low'], close=df['Close'], volume=df['Volume'], window=14).money_flow_index().iloc[-1]
        
        # 추세
        elif ind_type == "MACD_Line": return MACD(close=df['Close']).macd().iloc[-1]
        elif ind_type == "MACD_Signal": return MACD(close=df['Close']).macd_signal().iloc[-1]
        elif ind_type == "ADX (평균방향성지수)": return ADXIndicator(high=df['High'], low=df['Low'], close=df['Close'], window=14).adx().iloc[-1]
        elif ind_type == "SMA_20 (20일 단순이평)": return SMAIndicator(close=df['Close'], window=20).sma_indicator().iloc[-1]
        elif ind_type == "SMA_60 (60일 단순이평)": return SMAIndicator(close=df['Close'], window=60).sma_indicator().iloc[-1]
        elif ind_type == "SMA_120 (120일 단순이평)": return SMAIndicator(close=df['Close'], window=120).sma_indicator().iloc[-1]
        elif ind_type == "SMA_200 (200일 단순이평)": return SMAIndicator(close=df['Close'], window=200).sma_indicator().iloc[-1]
        elif ind_type == "EMA_20 (20일 지수이평)": return EMAIndicator(close=df['Close'], window=20).ema_indicator().iloc[-1]
        elif ind_type == "EMA_60 (60일 지수이평)": return EMAIndicator(close=df['Close'], window=60).ema_indicator().iloc[-1]
        elif ind_type == "Ichimoku_Conversion (일목균형표 전환선)": return IchimokuIndicator(high=df['High'], low=df['Low'], window1=9, window2=26, window3=52).ichimoku_conversion_line().iloc[-1]
        
        # 변동성
        elif ind_type == "BB_Upper (볼린저 상단)": return BollingerBands(close=df['Close'], window=20, window_dev=2).bollinger_hband().iloc[-1]
        elif ind_type == "BB_Lower (볼린저 하단)": return BollingerBands(close=df['Close'], window=20, window_dev=2).bollinger_lband().iloc[-1]
        elif ind_type == "ATR (평균진폭)": return AverageTrueRange(high=df['High'], low=df['Low'], close=df['Close'], window=14).average_true_range().iloc[-1]
        elif ind_type == "Keltner_Upper (켈트너 상단)": return KeltnerChannel(high=df['High'], low=df['Low'], close=df['Close'], window=20).keltner_channel_hband().iloc[-1]
        
        # 거래량
        elif ind_type == "OBV (온밸런스볼륨)": return OnBalanceVolumeIndicator(close=df['Close'], volume=df['Volume']).on_balance_volume().iloc[-1]
        elif ind_type == "Volume_SMA_20 (20일 평균거래량)": return SMAIndicator(close=df['Volume'], window=20).sma_indicator().iloc[-1]
        
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
            
        if len(df) < 200: 
            print(f"[{stock_code}] 과거 데이터 부족 (상장 1년 미만). 일부 지표 연산 불가.")
            continue

        current_value = calculate_indicator(df, ind_type)
            
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
