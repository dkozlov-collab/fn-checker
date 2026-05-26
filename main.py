import asyncio
import aiohttp
import gspread
import time
import os
import json

# --- НАСТРОЙКИ ---
SHEET_URL = "https://docs.google.com/spreadsheets/d/1nfVOSaSV66tHJWLnN40SuC10uC9NQmrgubNDRVYX1L8/edit?gid=572312672#gid=572312672"

CODES_TO_CHECK = ["0031", "0032", "0034", "0035", "0036", "0037", "0003", "0163", "0203"]
FN_NAMES = {
    "0031": "ФН-15 (1.1)", "0032": "ФН-36 (1.1)", "0034": "ФН-15 (1.2)",
    "0035": "ФН-36 (1.2)", "0036": "ФН-15 (исп. 3)", "0037": "ФН-36 (исп. 3)",
    "0003": "Centerm K-10", "0163": "Aisino A90", "0203": "Centerm K-9"
}

async def check_fn_universal(session, serial_number):
    clean_number = str(serial_number).strip()
    url = "https://kkt-online.nalog.ru/lkip.html"
    headers = {"User-Agent": "Mozilla/5.0", "X-Requested-With": "XMLHttpRequest"}
    
    for code in CODES_TO_CHECK:
        params = {"query": "/fn/model/check", "factory_number": clean_number, "model_code": code}
        try:
            async with session.get(url, params=params, headers=headers, ssl=False, timeout=5) as response:
                if response.status == 200:
                    data = await response.json()
                    res_text = str(data.get("check_result", "")).lower()
                    
                    if "включен в реестр" in res_text:
                        if "не зарегистрирован" in res_text:
                            return "❌ НЕ ЗАРЕГИСТРИРОВАН", FN_NAMES.get(code, f"код {code}")
                        else:
                            return "✅ ЗАРЕГИСТРИРОВАН", FN_NAMES.get(code, f"код {code}")
        except:
            continue
    return "⛔️ НЕ НАЙДЕН", "Отсутствует в реестре"

async def run_bot():
    print("🚀 БОТ-ПРОВЕРЩИК ФН ЗАПУЩЕН")
    
    # Инициализация Gspread через переменные среды (для GitHub Actions)
    # Если переменная GOOGLE_CREDENTIALS есть, используем её, если нет — файл
    if 'GOOGLE_CREDENTIALS' in os.environ:
        creds = json.loads(os.environ['GOOGLE_CREDENTIALS'])
        gc = gspread.service_account_from_dict(creds)
    else:
        gc = gspread.service_account(filename='credentials.json')
        
    sh = gc.open_by_url(SHEET_URL)
    ws = sh.sheet1
    
    async with aiohttp.ClientSession() as session:
        while True:
            try:
                fn_numbers = ws.col_values(1)
                status_values = ws.col_values(2)
                
                print(f"[{time.strftime('%H:%M:%S')}] Проверка таблицы...")

                for i, num in enumerate(fn_numbers):
                    row_index = i + 1
                    if row_index == 1 or (len(status_values) > i and status_values[i].strip() != ""):
                        continue

                    num = str(num).strip()
                    if len(num) >= 10 and num.isdigit():
                        print(f"🔎 Проверяю: {num}...")
                        status_text, model_name = await check_fn_universal(session, num)
                        ws.update(range_name=f'B{row_index}:C{row_index}', values=[[status_text, model_name]])
                        await asyncio.sleep(2)

                await asyncio.sleep(60)
            except Exception as e:
                print(f"❌ ОШИБКА: {e}")
                await asyncio.sleep(20)

if __name__ == "__main__":
    try:
        asyncio.run(run_bot())
    except KeyboardInterrupt:
        print("\nБот остановлен.")
