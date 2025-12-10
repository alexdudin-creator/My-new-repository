# src/get_price.py
import os
import re
import requests
from datetime import datetime
from bs4 import BeautifulSoup
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

def get_price_from_globe():
    """Источник 1: The Globe and Mail"""
    try:
        url = "https://www.theglobeandmail.com/investing/markets/funds/RBF460.CF/"
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
        r = requests.get(url, headers=headers, timeout=12)
        if r.status_code != 200:
            return None

        # Ищем все возможные варианты цены
        patterns = [
            r'"priceValue":"([\d.]+)"',
            r'data-testid="price-value">([\d.]+)',
            r'NAV\s*</span>\s*<span[^>]*>([\d.]+)',
            r'([\d.]{6,8})\s*CAD'
        ]
        for pattern in patterns:
            match = re.search(pattern, r.text)
            if match:
                price = match.group(1)
                if len(price.split('.')[-1]) >= 3:  # хотя бы 3 знака после точки
                    return price
    except:
        pass
    return None


def get_price_from_yahoo():
    """Источник 2: Yahoo Finance (самый стабильный для mutual funds)"""
    try:
        url = "https://ca.finance.yahoo.com/quote/RBF460.TO"
        headers = {"User-Agent": "Mozilla/5.0"}
        r = requests.get(url, headers=headers, timeout=12)
        if r.status_code != 200:
            return None

        # Yahoo хранит цену в JSON внутри <script>
        match = re.search(r'"regularMarketPrice":\{.*?"raw":([\d.]+)', r.text)
        if not match:
            match = re.search(r'"regularMarketPrice":([\d.]+)', r.text)
        if match:
            return match.group(1)

        # Альтернативный поиск в тексте
        match = re.search(r'RBF460\.TO.*?([\d]+\.\d{4})', r.text, re.DOTALL)
        if match:
            return match.group(1)
    except:
        pass
    return None


def get_price_from_rbc():
    """Источник 3: Официальный JSON от RBC (самый точный, но иногда медленно)"""
    try:
        url = "https://www.rbcgam.com/_assets-custom/include/get-nav-price.php?fund=RBF460"
        r = requests.get(url, timeout=10)
        if r.status_code == 200:
            import json
            data = r.json()
            if 'nav' in data:
                return str(round(float(data['nav']), 4))
    except:
        pass
    return None


def get_rbf460_price():
    """Главная функция — возвращает актуальную цену или честную ошибку"""
    
    # Пробуем по очереди
    price = get_price_from_yahoo()      # ← Самый стабильный — ставим первым!
    if not price:
        price = get_price_from_globe()
    if not price:
        price = get_price_from_rbc()

    if price and re.match(r'^\d+\.\d{3,}$', price):
        return price

    # Если ничего не нашли — честно говорим об этом
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
    <p><em>Источник: Yahoo Finance → Globe → RBC GAM</em></p>
    <hr><small>Автоматический отчёт • GitHub Actions</small>
    """
    msg.attach(MIMEText(body, "html"))

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
        server.login(os.getenv("SMTP_USER"), os.getenv("SMTP_APP_PASSWORD"))
        server.send_message(msg)


if __name__ == "__main__":
    price = get_rbf460_price()
    send_email(price)
    print(f"Отчёт отправлен: {price} CAD")
