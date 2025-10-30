import os
print("Текущая рабочая директория:", os.getcwd())


import gspread
from google.oauth2.service_account import Credentials

# Укажем область доступа
scope = ["https://www.googleapis.com/auth/spreadsheets"]

# Подключаем сервисный аккаунт
creds = Credentials.from_service_account_file("../service_account.json", scopes=scope)

# Авторизация через gspread
client = gspread.authorize(creds)

# Пример: подключаемся к таблице по URL
sheet = client.open_by_url("https://docs.google.com/spreadsheets/d/1-GDbnvoZnJz29nNHZm31rufV2nqLlC03CygjhoQ8PsM/edit#gid=0")

worksheet = sheet.sheet1

# Тестовая запись
worksheet.append_row(["Тест", "Работает!"])

print("✅ Данные успешно добавлены в Google Sheets!")
