import requests
from bs4 import BeautifulSoup
import pandas as pd
from datetime import datetime
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import os

URL = "https://www.rbcgam.com/en/ca/products/mutual-funds/RBF460/detail"
FILE_NAME = "rbc460_prices.xlsx"

EMAIL_SENDER = os.getenv("EMAIL_SENDER")
EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD")
EMAIL_RECEIVER = os.getenv("EMAIL_RECEIVER")

SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587


def get_price():
    headers = {"User-Agent": "Mozilla/5.0"}
    response = requests.get(URL, headers=headers)
    soup = BeautifulSoup(response.text, "lxml")

    price_tag = soup.find("span", {"class": "nav-value"})
    if not price_tag:
        return None

    return price_tag.text.strip().replace("$", "")


def send_email(price):
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
        print("Цена не найдена")
        return

    if os.path.exists(FILE_NAME):
        df = pd.read_excel(FILE_NAME)
    else:
        df = pd.DataFrame(columns=["Дата", "Цена"])

    df.loc[len(df)] = [now, price]
    df.to_excel(FILE_NAME, index=False)

    send_email(price)
    print("Успешно:", now, price)


if __name__ == "__main__":
    main()
