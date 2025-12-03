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
from selenium.common.exceptions import TimeoutException, NoSuchElementException

# Настройки
URL = "https://www.rbcgam.com/en/ca/products/mutual-funds/RBF460/detail"
FILE_NAME = "rbc460_prices.xlsx"

EMAIL_SENDER = os.getenv("EMAIL_SENDER")
EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD")
EMAIL_RECEIVER = os.getenv("EMAIL_RECEIVER")
SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587


def get_price():
    """Получаем NAV фонда через Selenium + webdriver-manager"""
    chrome_options = Options()
    chrome_options.add_argument("--headless=new")  # новый headless, стабильнее
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--window-size=1920,1080")
    chrome_options.add_argument("--disable-blink-features=AutomationControlled")
    chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
    chrome_options.add_experimental_option("useAutomationExtension", False)

    driver = webdriver.Chrome(options=chrome_options)

    try:
        driver.get(URL)
        print("Страница загружена, ждём NAV...")

        # Ждём любой элемент, содержащий "NAV $" (более надёжно)
        WebDriverWait(driver, 20).until(
            EC.presence_of_element_located((By.XPATH, "//*[contains(text(), 'NAV $')]"))
        )

        # Ищем все элементы с "NAV $", берём первый видимый
        elements = driver.find_elements(By.XPATH, "//*[contains(text(), 'NAV $')]")
        for el in elements:
            if el.is_displayed():
                text = el.text.strip()
                break
        else:
            # fallback — ищем по data-attribute или классу, если вдруг поменяли текст
            text = driver.find_element(By.CSS_SELECTOR, "[data-testid*='nav'], [class*='nav'], [class*='Nav']") \
                         .text

        # Извлекаем число после $
        import re
        match = re.search(r'NAV \$([\d.,]+)', text)
        if match:
            price = match.group(1).replace(',', '')  # убираем запятые в тысячах
            return price
        else:
            print("Не удалось распарсить цену из:", text)
            return None

    except TimeoutException:
        print("Таймаут: элемент NAV не появился за 20 сек")
        driver.save_screenshot("timeout_error.png")
        return None
    except Exception as e:
        print("Ошибка при парсинге:", e)
        driver.save_screenshot("error.png")
        return None
    finally:
        driver.quit()


def send_email(price):
    if not all([EMAIL_SENDER, EMAIL_PASSWORD, EMAIL_RECEIVER]):
        print("Не заданы переменные для email")
        return

    msg = MIMEMultipart()
    msg["From"] = EMAIL_SENDER
    msg["To"] = EMAIL_RECEIVER
    msg["Subject"] = f"RBF460 NAV = {price} CAD"

    body = f"""\
Обновление цены фонда RBC Canadian Equity Fund (RBF460)

Дата и время: {datetime.now().strftime('%Y-%m-%d %H:%M')} (UTC)
NAV: {price} CAD

Скрипт отработал успешно.
"""
    msg.attach(MIMEText(body, "plain", "utf-8"))

    try:
        server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
        server.starttls()
        server.login(EMAIL_SENDER, EMAIL_PASSWORD)
        server.send_message(msg)
        server.quit()
        print("Email отправлен")
    except Exception as e:
        print("Ошибка отправки email:", e)


def main():
    print("Запуск трекера RBF460...")
    price = get_price()

    if price is None:
        print("Цена не получена — выходим")
        return

    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # Сохраняем в Excel
    if os.path.exists(FILE_NAME):
        df = pd.read_excel(FILE_NAME)
    else:
        df = pd.DataFrame(columns=["Дата", "Цена"])

    # Добавляем новую строку
    new_row = pd.DataFrame({"Дата": [now], "Цена": [float(price)]})
    df = pd.concat([df, new_row], ignore_index=True)

    df.to_excel(FILE_NAME, index=False)
    print(f"Записано: {now} — {price} CAD")

    # Отправляем email
    send_email(price)


if __name__ == "__main__":
    main()
