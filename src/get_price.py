# src/get_price.py
import os
import time
from datetime import datetime
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import requests
from bs4 import BeautifulSoup

def get_rbf460_price():
    url = "https://www.theglobeandmail.com/investing/markets/funds/RBF460.CF/"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36"
    }

    try:
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')

        # Ищем текущую цену (NAV) — обычно в <span> или <strong> рядом с "37.XX CAD"
        price_elem = soup.find(string=lambda text: text and 'CAD' in text and any(c.isdigit() for c in text) and len(text) < 20)
        if not price_elem:
            # Альтернатива: ищем по классу или тексту (адаптировано под структуру 2025)
            price_elem = soup.find('span', class_='price-value') or soup.find('strong', string=lambda t: t and '.' in t and len(t.split('.')[-1]) == 4)
        
        if price_elem:
            price_text = price_elem.get_text(strip=True).replace('CAD', '').replace(',', '')
            return price_text
        else:
            return "Цена не найдена (проверьте сайт)"
            
    except Exception as e:
        return f"ОШИБКА Requests: {str(e)[:100]}"


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
    <p><em>Источник: The Globe and Mail (публичные данные NAV)</em></p>
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
