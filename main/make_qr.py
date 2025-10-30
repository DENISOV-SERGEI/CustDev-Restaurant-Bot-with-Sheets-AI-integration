import qrcode

# 👉 Сюда вставь ссылку на своего бота с параметром start=interview
bot_link = "https://t.me/Restaurants_LaBella_bot?start=interview"

# Генерация QR-кода
qr = qrcode.make(bot_link)

# Сохраняем файл
qr.save("la_bella_qr.png")

print("✅ QR-код сохранён как la_bella_qr.png")
print(f"📱 Ссылка в QR-коде: {bot_link}")
