# src/get_price.py
import os
import time
from datetime import datetime
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

def get_rbf460_price():
    options = Options()
    options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_argument("--disable-extensions")
    options.add_argument("--disable-plugins")
    options.add_argument("--disable-images")
    options.add_argument("--window-size=1920,1080")
    options.add_argument("user-agent=Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/130.0 Safari/537.36")

    driver = webdriver.Chrome(options=options)
    wait = WebDriverWait(driver, 30)

    try:
        driver.get("https://www.theglobeandmail.com/auth/sign-in/")
        time.sleep(4)

        # Логин
        wait.until(EC.element_to_be_clickable((By.NAME, "email"))).send_keys(os.getenv("GLOBE_EMAIL"))
        driver.find_element(By.CSS_SELECTOR, "button[type='submit']").click()

        # Пароль
        wait.until(EC.element_to_be_clickable((By.NAME, "password"))).send_keys(os.getenv("GLOBE_PASSWORD"))
        driver.find_element(By.CSS_SELECTOR, "button[type='submit']").click()

        # Ждём полной авторизации и переходим в Watchlist
        driver.get("https://www.theglobeandmail.com/investing/markets/watchlist/#/my-watchlist")
        time.sleep(10)  # даём время на загрузку всех скриптов

        # Ждём появления строки с RBF460.CF
        price_element = wait.until(EC.visibility_of_element_located(
            (By.XPATH, "//td[contains(text(),'RBF460.CF')]//following-sibling::td[3]//span")
        ))
        price = price_element.text.strip().replace(",", "")

        return price

    except Exception as e:
        return f"ОШИБКА Selenium: {str(e)[:200]}"
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
    <p style="font-size: 28px; color: #2e86ab;"><strong>{price}</strong> CAD</p>
    <p>Время получения: {datetime.now().strftime('%d %B %Y, %H:%M')} (Toronto time)</p>
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
