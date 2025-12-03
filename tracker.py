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
    chrome_options.add_argument("--headless=new")
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

        # Ждём якорь "NAV $"
        WebDriverWait(driver, 30).until(
            EC.presence_of_element_located((By.XPATH, "//*[contains(text(), 'NAV $')]"))
        )

        # Находим якорь
        anchor = driver.find_element(By.XPATH, "//*[contains(text(), 'NAV $')]")
        print(f"Найден якорь: '{anchor.text.strip()}'")

        # Ищем цену в следующем sibling-элементе (текущая структура сайта)
        try:
            price_element = anchor.find_element(By.XPATH, "following-sibling::*[1]")
            price_text = price_element.text.strip()
            print(f"Цена из sibling: '{price_text}'")
            # Проверяем, что это число
            import re
            match = re.match(r'^[\d.,]+$', price_text)
            if match:
                price = re.sub(r',', '', price_text)  # Убираем запятые
                print(f"✅ Извлечена цена: {price}")
                return price
            else:
                raise ValueError("Sibling не содержит число")
        except Exception as sibling_err:
            print(f"Sibling не найден: {sibling_err}. Fallback на полный текст...")

        # Fallback: полный текст секции + regex
        section = driver.find_element(By.XPATH, "//*[contains(text(), 'NAV $')]/ancestor::*[contains(@class, 'detail') or contains(@class, 'fund')]")
        full_text = section.text
        print(f"Полный текст секции: {full_text[:200]}...")  # Обрезаем для лога
        match = re.search(r'NAV \$([\d.,]+)', full_text)
        if match:
            price = match.group(1).replace(',', '')
            print(f"✅ Цена из fallback: {price}")
            return price
        else:
            print("Не удалось распарсить даже из fallback")
            return None

    except TimeoutException:
        print("Таймаут: элемент NAV не появился за 30 сек")
        driver.save_screenshot("timeout_error.png")
        return None
    except Exception as e:
        print("Общая ошибка:", e)
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
