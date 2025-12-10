# src/get_price.py
import os
import re
import requests
from datetime import datetime
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# Файл для хранения предыдущей цены
PRICE_FILE = "/tmp/last_rbf460_price.txt"

def get_current_price():
    url = "https://www.theglobeandmail.com/investing/markets/funds/RBF460.CF/"
    headers = {"User-Agent": "Mozilla/5.0"}
    
    try:
        r = requests.get(url, headers=headers, timeout=15)
        r.raise_for_status()
        
        # Ищем все числа вида 37.4008 (от 30 до 45 CAD)
        matches = re.findall(r'\b([3-4][0-9]\.\d{4})\b', r.text)
        if matches:
            # Берём самое частое (самое надёжное)
            from collections import Counter
            price = Counter(matches).most_common(1)[0][0]
            return float(price)
    except:
        pass
    
    return None

def read_previous_price():
    if os.path.exists(PRICE_FILE):
        try:
            with open(PRICE_FILE, "r") as f:
                return float(f.read().strip())
        except:
            pass
    return None

def save_current_price(price):
    try:
        with open(PRICE_FILE, "w") as f:
            f.write(str(price))
    except:
        pass  # в GitHub Actions /tmp — нормально

def send_email(current_price, change_cad=None, change_pct=None):
    msg = MIMEMultipart("alternative")
    msg["From"] = os.getenv("SMTP_USER")
    msg["To"] = "alex.dudin@gmail.com"
    msg["Subject"] = f"RBF460.CF — {current_price:.4f} CAD — {datetime.now().strftime('%d.%m.%Y')}"

    change_text = ""
    if change_cad is not None:
        sign = "+" if change_cad >= 0 else ""
        color = "#2e86ab" if change_cad >= 0 else "#d32f2f"
        change_text = f"""
        <p style="font-size: 18px; margin: 15px 0;">
            Изменение: <span style="color:{color}; font-weight:bold;">{sign}{change_cad:.4f} CAD ({sign}{change_pct:.2f}%)</span>
        </p>
        """

    html = f"""
    <h2>Ежедневный отчёт по RBC Select Balanced Portfolio</h2>
    <p><strong>Тикер:</strong> RBF460.CF</p>
    <p style="font-size: 38px; color: #2e86ab; margin: 25px 0; font-weight: bold;">{current_price:.4f} CAD</p>
    {change_text}
    <p><em>Источник: The Globe and Mail • NAV на конец дня</em></p>
    <p>Время получения: {datetime.now().strftime('%d %B %Y, %H:%M')} (Toronto time)</p>
    <hr>
    <small>Автоматический отчёт • GitHub Actions</small>
    """

    msg.attach(MIMEText(html, "html"))

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
        server.login(os.getenv("SMTP_USER"), os.getenv("SMTP_APP_PASSWORD"))
        server.send_message(msg)

if __name__ == "__main__":
    current_price = get_current_price()
    
    if current_price is None:
        final_price = "НЕ УДАЛОСЬ ПОЛУЧИТЬ ЦЕНУ"
        send_email(final_price)
        print("Ошибка: цена не найдена")
    else:
        prev_price = read_previous_price()
        change_cad = None
        change_pct = None
        
        if prev_price is not None:
            change_cad = current_price - prev_price
            change_pct = (change_cad / prev_price) * 100
        
        save_current_price(current_price)
        send_email(current_price, change_cad, change_pct)
        print(f"Успех! Цена: {current_price:.4f} CAD")
