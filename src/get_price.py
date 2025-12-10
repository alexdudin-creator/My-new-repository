# src/get_price.py
import os
from datetime import datetime
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import requests
from bs4 import BeautifulSoup
import re

def get_price_from_globe():
    """Парсинг Globe (основной)"""
    url = "https://www.theglobeandmail.com/investing/markets/funds/RBF460.CF/"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36"
    }
    try:
        r = requests.get(url, headers=headers, timeout=15)
        r.raise_for_status()
        soup = BeautifulSoup(r.text, 'html.parser')
        
        # Поиск по тексту страницы (расширенный)
        text = r.text
        patterns = [
            r'"priceValue":"(\d+\.\d{4})"',  # JSON в скрипте
            r'(\d+\.\d{4})\s*CAD',  # Прямой текст
            r'NAV.*?(\d+\.\d{4})',  # NAV контекст
            r'Last Update.*?(\d+\.\d{4})'  # Обновление
        ]
        for pattern in patterns:
            match = re.search(pattern, text)
            if match:
                return match.group(1)
    except Exception as e:
        print(f"Globe error: {e}")
    return None

def get_price_from_yahoo():
    """Парсинг Yahoo (fallback 1)"""
    url = "https://ca.finance.yahoo.com/quote/RBF460.TO"
    headers = {"User-Agent": "Mozilla/5.0"}
    try:
        r = requests.get(url, headers=headers, timeout=15)
        r.raise_for_status()
        # JSON в скрипте
        match = re.search(r'"regularMarketPrice":\s*(\d+\.\d{4})', r.text)
        if match:
            return match.group(1)
        # Альтернатива
        match = re.search(r'(\d+\.\d{4})\s*CAD', r.text)
        if match:
            return match.group(1)
    except Exception as e:
        print(f"Yahoo error: {e}")
    return None

def get_price_from_rbc():
    """RBC JSON (fallback 2)"""
    url = "https://www.rbcgam.com/_assets-custom/include/get-nav-price.php?fund=RBF460"
    try:
        r = requests.get(url, timeout=10)
        r.raise_for_status()
        import json
        data = r.json()
        if 'nav' in data and isinstance(data['nav'], (int, float)):
            return str(round(float(data['nav']), 4))
    except Exception as e:
        print(f"RBC error: {e}")
    return None

def get_rbf460_price():
    """Главная: пробуем по приоритету"""
    price = get_price_from_globe()
    if not price:
        price = get_price_from_yahoo()
    if not price:
        price = get_price_from_rbc()
    if price and re.match(r'^\d+\.\d{3,}$', price):
        print(f"Цена найдена: {price}")
        return price
    return "НЕ УДАЛОСЬ ПОЛУЧИТЬ ЦЕНУ (проверьте вручную)"

def send_email(price):
    msg = MIMEMultipart()
    msg["From"] = os.getenv("SMTP_USER")
    msg["To"] = "alex.dudin@gmail.com"
    msg["Subject"] = f"RBF460.CF — {price} CAD — {datetime.now().strftime('%d.%m.%Y')}"

    color = "#d32f2f" if "НЕ УДАЛОСЬ" in price else "#2e86ab"
    body = f"""
    <h2>Ежедневный отчёт по RBC Select Balanced Portfolio</h2>
    <p><strong>Тикер:</strong> RBF460.CF</p>
    <p style="font-size: 32px; color: {color}; margin: 15px 0;"><strong>{price}</strong> CAD</p>
    <p>Время получения: {datetime.now().strftime('%d %B %Y, %H:%M')} (Toronto time)</p>
    <p><em>NAV на конец дня (источник: Globe / Yahoo / RBC). Если ошибка — проверьте вручную.</em></p>
    <hr><small>Автоматический отчёт • GitHub Actions</small>
    """
    msg.attach(MIMEText(body, "html"))

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
        server.login(os.getenv("SMTP_USER"), os.getenv("SMTP_APP_PASSWORD"))
        server.send_message(msg)

if __name__ == "__main__":
    price = get_rbf460_price()
    send_email(price)
    print(f"Готово! Цена RBF460.CF: {price}")
