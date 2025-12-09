# src/get_price.py
import os
import time
from datetime import datetime
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import requests
from bs4 import BeautifulSoup
import yfinance as yf  # Добавь в requirements.txt

def get_rbf460_price():
    # Попытка 1: The Globe and Mail
    globe_url = "https://www.theglobeandmail.com/investing/markets/funds/RBF460.CF/"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36"
    }
    try:
        response = requests.get(globe_url, headers=headers, timeout=10)
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Ищем цену в возможных местах (расширенный поиск)
        price_elem = (
            soup.find('span', class_='price-value') or
            soup.find('strong', string=lambda t: t and '.' in t and len(t.split('.')[-1]) == 4) or
            soup.find(string=lambda text: text and any(c.isdigit() for c in text) and 'CAD' in text and len(text) < 20)
        )
        if price_elem:
            price = price_elem.get_text(strip=True).replace('CAD', '').replace(',', '').strip()
            if price and '.' in price:
                return price
    except Exception as e:
        print(f"Globe error: {e}")

    # Fallback: Yahoo Finance (надёжный для RBF460.CF)
    try:
        ticker = yf.Ticker("RBF460.TO")  # Yahoo использует .TO для TSX
        info = ticker.info
        hist = ticker.history(period="1d")
        if 'regularMarketPrice' in info:
            return str(info['regularMarketPrice'])[:5]  # Обрезаем до 37.64
        elif not hist.empty:
            return str(hist['Close'].iloc[-1])[:5]
        else:
            return "Цена не найдена (проверьте API)"
    except Exception as e:
        return f"ОШИБКА Fallback: {str(e)[:100]}"

def send_email(price):
    msg = MIMEMultipart()
    msg["From"] = os.getenv("SMTP_USER")
    msg["To"] = "alex.dudin@gmail.com"
    msg["Subject"] = f"RBF460.CF — {price} CAD — {datetime.now().strftime('%d.%m.%Y')}"

    body = f"""
    <h2>Ежедневный отчёт по RBC Select Balanced Portfolio</h2>
    <p><strong>Тикер:</strong> RBF460.CF</p>
    <p style="font-size: 28px; color: #2e86ab;"><strong>{price}</strong> CAD</p>
    <p>Время получения: {datetime.now().strftime('%d %B %Y, %H:%M')} (Toronto time)</p>
    <p><em>Источник: The Globe and Mail / Yahoo Finance (NAV на конец дня)</em></p>
    <hr><small>Автоматический отчёт от GitHub Actions</small>
    """
    msg.attach(MIMEText(body, "html"))

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
        server.login(os.getenv("SMTP_USER"), os.getenv("SMTP_APP_PASSWORD"))
        server.send_message(msg)

if __name__ == "__main__":
    price = get_rbf460_price()
    send_email(price)
    print(f"Готово! Цена RBF460.CF: {price}")
