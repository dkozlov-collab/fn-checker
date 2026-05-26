import asyncio
import aiohttp
import gspread
import time

# --- НАСТРОЙКИ ---
# Вставь свою ссылку между кавычками:
SHEET_URL = "https://docs.google.com/spreadsheets/d/1nfVOSaSV66tHJWLnN40SuC10uC9NQmrgubNDRVYX1L8/edit?gid=572312672#gid=572312672"

CODES_TO_CHECK = ["0031", "0032", "0034", "0035", "0036", "0037", "0003", "0163", "0203"]
FN_NAMES = {
    "0031": "ФН-15 (1.1)", "0032": "ФН-36 (1.1)", "0034": "ФН-15 (1.2)",
    "0035": "ФН-36 (1.2)", "0036": "ФН-15 (исп. 3)", "0037": "ФН-36 (исп. 3)",
    "0003": "Centerm K-10", "0163": "Aisino A90", "0203": "Centerm K-9"
}

async def check_fn_universal(serial_number):
    clean_number = str(serial_number).strip()
    # URL сервиса проверки ККТ
    url = "https://kkt-online.nalog.ru/lkip.html"
    headers = {"User-Agent": "Mozilla/5.0", "X-Requested-With": "XMLHttpRequest"}
    
    for code in CODES_TO_CHECK:
        params = {"query": "/fn/model/check", "factory_number": clean_number, "model_code": code}
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, params=params, headers=headers, ssl=False, timeout=5) as response:
                    if response.status == 200:
                        data = await response.json()
                        status = data.get("check_status", 0)
                        res_text = str(data.get("check_result", ""))
                        
                        # Если статус 1 - значит ФН найден и он корректен
                        if status == 1:
                            name = FN_NAMES.get(code, f"код {code}")
                            return ".❌️НЕ ЗАРЕГИСТРИРОВАН", name
                        # Если в тексте ответа есть фраза об использовании
                        elif "уже используется" in res_text or "зарегистрирован" in res_text.lower():
                            name = FN_NAMES.get(code, f"код {code}")
                            return " ✅️ЗАРЕГИСТРИРОВАН", name
        except: 
            continue
            
    return "⛔ НЕ НАЙДЕН", "Отсутствует в реестре"

async def run_bot():
    print("========================================")
    print("🚀 БОТ-ПРОВЕРЩИК ФН ЗАПУЩЕН")
    print("Режим: Автоматическое слежение за таблицей")
    print("========================================\n")

    while True:
        try:
            # Подключение
            gc = gspread.service_account(filename='credentials.json')
            sh = gc.open_by_url(SHEET_URL)
            ws = sh.sheet1
            
            # Читаем колонки
            fn_numbers = ws.col_values(1)  # Колонка A
            status_values = ws.col_values(2) # Колонка B
            
            print(f"[{time.strftime('%H:%M:%S')}] Проверка таблицы... Строк: {len(fn_numbers)}")

            for i, num in enumerate(fn_numbers):
                row_index = i + 1 
                
                # Пропускаем заголовок
                if row_index == 1 and not str(num).isdigit():
                    continue

                # Если в колонке B (Статус) уже что-то написано — пропускаем
                if len(status_values) >= row_index and status_values[i].strip() != "":
                    continue

                num = str(num).strip()
                if len(num) >= 10 and num.isdigit():
                    print(f"🔎 Нашел новый ФН: {num}. Проверяю в базе ФНС...")
                    
                    status_text, model_name = await check_fn_universal(num)
                    
                    # Записываем результат в B и C
                    ws.update(range_name=f'B{row_index}:C{row_index}', values=[[status_text, model_name]])
                    
                    print(f"   ✅ Статус: {status_text} | Модель: {model_name}")
                    await asyncio.sleep(2) # Небольшая пауза между запросами

            print("😴 Всё проверил. Жду 60 секунд до следующего круга...")
            await asyncio.sleep(60)

        except Exception as e:
            print(f"❌ Ошибка подключения или таблицы: {e}")
            print("Попробую снова через 20 секунд...")
            await asyncio.sleep(20)
if __name__ == "__main__":
    try:
        asyncio.run(run_bot())
    except KeyboardInterrupt:
        print("\nБот остановлен пользователем.")