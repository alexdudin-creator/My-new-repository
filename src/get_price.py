# src/get_price.py
import os
import re
import requests
from datetime import datetime
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

def get_from_rbc():
    try:
        r = requests.get("https://www.rbcgam.com/_assets-custom/include/get-nav-price.php?fund=RBF460", timeout=10)
        data = r.json()
        nav = data.get("nav")
        if nav and float(nav) > 10:
            return f"{float(nav):.4f}"
    except:
        pass
    return "—"

def get_from_yahoo():
    try:
        r = requests.get("https://ca.finance.yahoo.com/quote/RBF460.TO", 
                        headers={"User-Agent": "Mozilla/5.0"}, timeout=12)
        match = re.search(r'"regularMarketPrice":\s*{"raw":([3-9][0-9]\.\d+)', r.text)
        if match:
            return match.group(1)
        match = re.search(r'(\d{2}\.\d{4})', r.text)
        if match and 30 < float(match.group(1)) < 50:
            return match.group(1)
    except:
        pass
    return "—"

def get_from_globe():
    try:
        r = requests.get("https://www.theglobeandmail.com/investing/markets/funds/RBF460.CF/",
                        headers={"User-Agent": "Mozilla/5.0"}, timeout=12)
        matches = re.findall(r'\b([3][0-9]\.\d{4})\b', r.text)
        if matches:
            from collections import Counter
            return Counter(matches).most_common(1)[0][0]
    except:
        pass
    return "—"

def choose_best_price(rbc, yahoo, globe):
    candidates = []
    if rbc != "—": candidates.append((float(rbc), "RBC (официальный)"))
    if yahoo != "—": candidates.append((float(yahoo), "Yahoo Finance"))
    if globe != "—": candidates.append((float(globe), "The Globe and Mail"))

    if not candidates:
        return "НЕ УДАЛОСЬ ПОЛУЧИТЬ ЦЕНУ", "—"

    # Приоритет: RBC → Yahoo → Globe
    candidates.sort(key=lambda x: ["RBC (официальный)", "Yahoo Finance", "The Globe and Mail"].index(x[1]))
    best_price = f"{candidates[0][0]:.4f}"
    best_source = candidates[0][1]
    return best_price, best_source

def send_email(rbc, yahoo, globe, final_price, final_source):
    msg = MIMEMultipart("alternative")
    msg["From"] = os.getenv("SMTP_USER")
    msg["To"] = "alex.dudin@gmail.com"
    msg["Subject"] = f"RBF460.CF — {final_price} CAD — {datetime.now().strftime('%d.%m.%Y')}"

    html = f"""
    <h2>Ежедневный отчёт по RBC Select Balanced Portfolio</h2>
    <p><strong>Тикер:</strong> RBF460.CF</p>
    <p style="font-size: 36px; color: #2e86ab; margin: 20px 0;"><strong>{final_price} CAD</strong></p>
    <p><em>Источник, которому мы доверяем сегодня: <strong>{final_source}</strong></em></p>

    <hr style="margin: 25px 0;">

    <h3>Что вернул каждый источник:</h3>
    <table style="width:100%; border-collapse: collapse; font-size: 15px;">
        <tr style="background:#f0f8ff;">
            <td style="padding:10px; font-weight:bold;">RBC GAM (официальный)</td>
            <td style="padding:10px;"><strong>{rbc}</strong> CAD</td>
        </tr>
        <tr>
            <td style="padding:10px; font-weight:bold;">Yahoo Finance</td>
            <td style="padding:10px;"><strong>{yahoo}</strong> CAD</td>
        </tr>
        <tr style="background:#f0f8ff;">
            <td style="padding:10px; font-weight:bold;">The Globe and Mail</td>
            <td style="padding:10px;"><strong>{globe}</strong> CAD</td>
        </tr>
    </table>

    <p style="margin-top: 25px; color:#666;">
        Время получения: {datetime.now().strftime('%d %B %Y, %H:%M')} (Toronto time)<br>
        Автоматический отчёт • GitHub Actions
    </p>
    """

    msg.attach(MIMEText(html, "html"))

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
        server.login(os.getenv("SMTP_USER"), os.getenv("SMTP_APP_PASSWORD"))
        server.send_message(msg)

if __name__ == "__main__":
    rbc   = get_from_rbc()
    yahoo = get_from_yahoo()
    globe = get_from_globe()

    final_price, final_source = choose_best_price(rbc, yahoo, globe)

    send_email(rbc, yahoo, globe, final_price, final_source)
    print(f"Письмо отправлено. Итоговая цена: {final_price} CAD ({final_source})")
