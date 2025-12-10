# src/get_price.py
import os
from datetime import datetime
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import requests
from bs4 import BeautifulSoup
import re

def get_rbf460_price():
    # Источник 1: The Globe and Mail
    url = "https://www.theglobeandmail.com/investing/markets/funds/RBF460.CF/"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36"
    }

    try:
        response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')

        # Расширенный поиск цены (проверяем больше селекторов)
        price_elem = (
            soup.find('span', {'data-testid': 'price-value'}) or
            soup.find('strong', string=lambda t: t and re.match(r'\d+\.\d{4}', str(t))) or
            soup.find('td', string=lambda t: t and 'NAV' in str(t).upper()) or
            next((el for el in soup.find_all('span') if re.search(r'\d+\.\d{4}', el.get_text())), None) or
            next((el for el in soup.find_all(string=lambda text: text and re.search(r'(\d+\.\d{4})\s*CAD', str(text)))), None)
        )

        if price_elem:
            price_text = str(price_elem).strip().replace('CAD', '').replace(',', '').replace('$', '')
            match = re.search(r'(\d+\.\d{4})', price_text)
            if match:
                return match.group(1)

    except Exception as e:
        print(f"Globe error: {e}")

    # Источник 2: Yahoo Finance (fallback, всегда свежий NAV)
    yahoo_url = "https://ca.finance.yahoo.com/quote/RBF460.TO"
    try:
        response = requests.get(yahoo_url, headers=headers, timeout=15)
        response.raise_for_status()
        # Ищем в JSON внутри скрипта или в тексте
        match = re.search(r'"regularMarketPrice":\s*([\d.]+)', response.text)
        if not match:
            match = re.search(r'(\d+\.\d{4})\s*CAD', response.text)
        if match:
            return str(round(float(match.group(1)), 4))
    except Exception as e:
        print(f"Yahoo error: {e}")

    # Если ничего не найдено — ошибка (без хардкода)
    return f"ОШИБКА: Цена не найдена (проверьте сайт; fallback недоступен)"

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
    <p><em>Источник: The Globe and Mail / Yahoo Finance (NAV на конец дня). Если ошибка — проверьте вручную.</em></p>
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
