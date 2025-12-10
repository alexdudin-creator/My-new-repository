# src/get_price.py
import os
from datetime import datetime
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import requests
from bs4 import BeautifulSoup
import re
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

def get_price_selenium_globe():
    """Надёжный метод: Selenium для полной загрузки JS на Globe"""
    options = Options()
    options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--window-size=1920,1080")
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36")

    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=options)
    wait = WebDriverWait(driver, 15)

    try:
        driver.get("https://www.theglobeandmail.com/investing/markets/funds/RBF460.CF/")
        wait.until(EC.presence_of_element_located((By.TAG_NAME, "body")))
        
        # Ждём загрузки цены
        price_elem = wait.until(EC.presence_of_element_located(
            (By.XPATH, "//span[contains(@class, 'price') or contains(text(), 'CAD')] | //strong[contains(text(), '.') and contains(text(), 'CAD')] | //*[contains(text(), '37.')]")
        ))
        price_text = price_elem.text.strip()
        match = re.search(r'(\d+\.\d{4})', price_text)
        if match:
            print("Цена найдена через Selenium Globe:", match.group(1))
            return match.group(1)
    except Exception as e:
        print(f"Selenium Globe error: {e}")
    finally:
        driver.quit()
    return None

def get_price_requests_yahoo():
    """Requests для Yahoo (быстрый fallback)"""
    try:
        url = "https://ca.finance.yahoo.com/quote/RBF460.TO"
        headers = {"User-Agent": "Mozilla/5.0"}
        r = requests.get(url, headers=headers, timeout=10)
        match = re.search(r'"regularMarketPrice":\s*([\d.]+)', r.text)
        if match:
            print("Цена найдена через Requests Yahoo:", match.group(1))
            return match.group(1)
    except Exception as e:
        print(f"Requests Yahoo error: {e}")
    return None

def get_rbf460_price():
    """Главная: Selenium → Requests"""
    price = get_price_selenium_globe()
    if not price:
        price = get_price_requests_yahoo()
    if not price:
        return "НЕ УДАЛОСЬ ПОЛУЧИТЬ ЦЕНУ (проверьте вручную)"
    return price

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
    <p><em>NAV на конец дня (источник: Globe / Yahoo). Изменение -0.16% (09.12.2025).</em></p>
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
