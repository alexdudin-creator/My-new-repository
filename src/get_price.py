# src/get_price.py
import os
import time
import smtplib
from datetime import datetime
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException

def get_rbf460_price():
    options = Options()
    options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--window-size=1920,1080")
    options.add_experimental_option("excludeSwitches", ["enable-automation"])

    driver = webdriver.Chrome(options=options)
    wait = WebDriverWait(driver, 20)

    try:
        driver.get("https://www.theglobeandmail.com/auth/sign-in/")
        time.sleep(3)

        # Email
        wait.until(EC.presence_of_element_located((By.NAME, "email"))).send_keys(os.getenv("GLOBE_EMAIL"))
        driver.find_element(By.CSS_SELECTOR, "button[type='submit']").click()

        # Password
        wait.until(EC.presence_of_element_located((By.NAME, "password"))).send_keys(os.getenv("GLOBE_PASSWORD"))
        driver.find_element(By.CSS_SELECTOR, "button[type='submit']").click()

        # Переход в Watchlist
        driver.get("https://www.theglobeandmail.com/investing/markets/watchlist/")
        time.sleep(8)

        # Поиск RBF460.CF
        row = wait.until(EC.presence_of_element_located(
            (By.XPATH, "//td[contains(text(), 'RBF460.CF')]//parent::tr")
        ))
        price = row.find_element(By.XPATH, ".//td[4]//span").text.strip()

        return price.replace(",", "")

    except Exception as e:
        return f"ОШИБКА: {str(e)}"
    finally:
        driver.quit()

def send_email(price):
    msg = MIMEMultipart()
    msg["From"] = os.getenv("SMTP_USER")
    msg["To"] = "alex.dudin@gmail.com"
    msg["Subject"] = f"RBF460.CF — {price} CAD — {datetime.now().strftime('%d.%m.%Y')}"

    body = f"""
    <h2>Ежедневный отчёт по RBC Select Balanced Portfolio</h2>
    <p><strong>Тикер:</strong> RBF460.CF</p>
    <p style="font-size: 28px; color: #2e86ab;"><strong>{price} CAD</strong></p>
    <p>Время получения: {datetime.now().strftime('%d %B %Y, %H:%M')} (Toronto time)</p>
    <hr>
    <small>Автоматический отчёт от GitHub Actions</small>
    """
    msg.attach(MIMEText(body, "html"))

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
        server.login(os.getenv("SMTP_USER"), os.getenv("SMTP_APP_PASSWORD"))
        server.send_message(msg)

if __name__ == "__main__":
    print("Запуск получения цены RBF460.CF...")
    price = get_rbf460_price()
    send_email(price)
    print(f"Цена {price} — отчёт отправлен на alex.dudin@gmail.com")
