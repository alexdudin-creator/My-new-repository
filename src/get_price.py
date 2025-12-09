# src/get_price.py
import os
from datetime import datetime
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
import pandas as pd
import yfinance as yf
import requests
from bs4 import BeautifulSoup
import re

def get_current_price():
    # Сначала пробуем yfinance — самый надёжный источник
    try:
        ticker = yf.Ticker("RBF460.TO")
        hist = ticker.history(period="2d")
        if not hist.empty:
            return round(hist['Close'].iloc[-1], 4)
    except:
        pass

    # Fallback на Globe
    try:
        url = "https://www.theglobeandmail.com/investing/markets/funds/RBF460.CF/"
        headers = {"User-Agent": "Mozilla/5.0"}
        r = requests.get(url, headers=headers, timeout=15)
        soup = BeautifulSoup(r.text, 'html.parser')
        match = re.search(r'(\d+\.\d{4})\s*CAD', soup.get_text())
        if match:
            return float(match.group(1))
    except:
        pass

    return 37.73  # последняя известная

def get_history_30_days():
    try:
        ticker = yf.Ticker("RBF460.TO")
        df = ticker.history(period="40d")  # чуть больше, чтобы точно 30 торговых дней
        if df.empty:
            raise Exception("No data")
        df = df[['Close']].copy()
        df = df.sort_index().tail(30)  # последние 30 записей
        df['Дата'] = df.index.strftime('%d.%m.%Y')
        df['Цена (CAD)'] = df['Close'].round(4)
        df['Изменение, CAD'] = df['Close'].diff()
        df['Изменение, %'] = (df['Close'].pct_change() * 100).round(2)
        df = df[['Дата', 'Цена (CAD)', 'Изменение, CAD', 'Изменение, %']]
        df.iloc[0, 2:] = 0  # первая строка — без изменения
        df.iloc[0, 3] = 0.00
        return df
    except Exception as e:
        print(f"Ошибка получения истории: {e}")
        # Резервный вариант — пустая таблица с текущей ценой
        today = datetime.now().strftime('%d.%m.%Y')
        price = get_current_price()
        data = {
            'Дата': [today],
            'Цена (CAD)': [price],
            'Изменение, CAD': [0],
            'Изменение, %': [0.00]
        }
        return pd.DataFrame(data)

def create_excel_file(df):
    today_str = datetime.now().strftime('%d.%m.%Y')
    filename = f"RBF460_history_{today_str}.xlsx"
    
    with pd.ExcelWriter(filename, engine='openpyxl') as writer:
        df.to_excel(writer, sheet_name='RBF460.CF', index=False)
        worksheet = writer.sheets['RBF460.CF']
        # Форматирование
        from openpyxl.styles import Font, Alignment, PatternFill
        header_font = Font(bold=True, color="FFFFFF")
        header_fill = PatternFill(start_color="2e86ab", end_color="2e86ab", fill_type="solid")
        for cell in worksheet[1]:
            cell.font = header_font
            cell.fill = header_fill
            cell.alignment = Alignment(horizontal="center")
        # Автоширина колонок
        for column in worksheet.columns:
            max_length = 0
            column_letter = column[0].column_letter
            for cell in column:
                try:
                    if len(str(cell.value)) > max_length:
                        max_length = len(str(cell.value))
                except:
                    pass
            adjusted_width = min(max_length + 2, 50)
            worksheet.column_dimensions[column_letter].width = adjusted_width

    return filename

def send_email_with_excel(excel_filename, current_price):
    msg = MIMEMultipart()
    msg["From"] = os.getenv("SMTP_USER")
    msg["To"] = "alex.dudin@gmail.com"
    msg["Subject"] = f"RBF460.CF — {current_price} CAD — {datetime.now().strftime('%d.%m.%Y')}"

    html = f"""
    <h2>Ежедневный отчёт по RBC Select Balanced Portfolio</h2>
    <p><strong>Тикер:</strong> RBF460.CF</p>
    <p style="font-size: 32px; color: #2e86ab; margin: 15px 0;"><strong>{current_price}</strong> CAD</p>
    <p>Время получения: {datetime.now().strftime('%d %B %Y, %H:%M')} (Toronto time)</p>
    <p>Во вложении — история цен за последние 30 дней в Excel.</p>
    <hr>
    <small>Автоматический отчёт от GitHub Actions • Источник: Yahoo Finance</small>
    """

    msg.attach(MIMEText(html, "html"))

    # Прикрепляем Excel
    with open(excel_filename, "rb") as attachment:
        part = MIMEBase("application", "octet-stream")
        part.set_payload(attachment.read())
        encoders.encode_base64(part)
        part.add_header(
            "Content-Disposition",
            f"attachment; filename= {excel_filename}"
        )
        msg.attach(part)

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
        server.login(os.getenv("SMTP_USER"), os.getenv("SMTP_APP_PASSWORD"))
        server.send_message(msg)

if __name__ == "__main__":
    current_price = get_current_price()
    df = get_history_30_days()
    excel_file = create_excel_file(df)
    send_email_with_excel(excel_file, current_price)
    print(f"Отчёт с Excel отправлен! Цена: {current_price} CAD")
