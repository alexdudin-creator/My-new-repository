import os
import time
from datetime import datetime
import pandas as pd
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# Настройки
URL = "https://www.rbcgam.com/en/ca/products/mutual-funds/RBF460/detail"
FILE_NAME = "rbc460_prices.xlsx"

EMAIL_SENDER = os.getenv("EMAIL_SENDER")
EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD")
EMAIL_RECEIVER = os.getenv("EMAIL_RECEIVER")

SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587

def get_price():
    """Получаем цену NAV через Selenium"""
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")

    driver = webdriver.Chrome(options=chrome_options)
    driver.get(URL)

    try:
        # Ждём появления элемента с NAV (по тексту "NAV $")
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.XPATH, "//*[contains(text(),'NAV $')]"))
        )
        # Находим текст элемента
        element = driver.find_element(By.XPATH, "//*[contains(text(),'NAV $')]")
        text = element.text
        # Извлекаем число из строки "NAV $37.5962"
        price = text.split("$")[1].strip()
    except Exception as e:
        print("❌ Цена не найдена:", e)
        price = None
    finally:
        driver.quit()

    return price

def send_email(price):
    """Отправка Email"""
    msg = MIMEMultipart()
    msg["From"] = EMAIL_SENDER
    msg["To"] = EMAIL_RECEIVER
    msg["Subject"] = "Цена фонда RBC460"

    body = f"Цена фонда RBC460 на {datetime.now().strftime('%Y-%m-%d %H:%M')}:\n{price} CAD"
    msg.attach(MIMEText(body, "plain"))

    server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
    server.starttls()
    server.login(EMAIL_SENDER, EMAIL_PASSWORD)
    server.send_message(msg)
    server.quit()

def main():
    price = get_price()
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    if price is None:
        return

    if os.path.exists(FILE_NAME):
        df = pd.read_excel(FILE_NAME)
    else:
        df = pd.DataFrame(columns=["Дата", "Цена"])

    df.loc[len(df)] = [now, price]
    df.to_excel(FILE_NAME, index=False)

    send_email(price)
    print(f"✅ Успешно: {now}, Цена: {price}")

if __name__ == "__main__":
    main()
