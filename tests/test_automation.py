"""
Простой тест для проверки сохранения выходных полей
"""
import requests
import time

BASE_URL = "http://127.0.0.1:8000"

def test_output_fields():
    print("=" * 60)
    print("  ТЕСТ: Сохранение выходных полей")
    print("=" * 60)
    
    channel_id = input("\nВведите ID канала (Enter для 1): ").strip() or "1"
    api_key = input("Введите Write API Key: ").strip()
    
    if not api_key:
        print("❌ API ключ обязателен!")
        return
    
    print("\n⚠️  Убедитесь, что у канала есть правило:")
    print("   IF field1 > 5 THEN field2 = decrement - 1")
    input("\nНажмите Enter для продолжения...")
    
    # Запрос 1
    print("\n📤 Запрос 1: field1=10, field2=10")
    r = requests.get(f"{BASE_URL}/update", params={
        "api_key": api_key,
        "field1": 10,
        "field2": 10
    })
    print(f"   Entry ID: {r.text}")
    time.sleep(1)
    
    # Проверка 1
    r = requests.get(f"{BASE_URL}/channels/{channel_id}/feeds.json?results=1")
    if r.status_code == 200:
        feed = r.json()['feeds'][0]
        print(f"   Результат: field1={feed['field1']}, field2={feed['field2']}")
        print(f"   ✅ Ожидалось field2=9, получено: {feed['field2']}")
    
    # Запрос 2
    print("\n📤 Запрос 2: field1=10 (БЕЗ field2)")
    r = requests.get(f"{BASE_URL}/update", params={
        "api_key": api_key,
        "field1": 10
    })
    print(f"   Entry ID: {r.text}")
    time.sleep(1)
    
    # Проверка 2
    r = requests.get(f"{BASE_URL}/channels/{channel_id}/feeds.json?results=1")
    if r.status_code == 200:
        feed = r.json()['feeds'][0]
        field2 = feed['field2']
        print(f"   Результат: field1={feed['field1']}, field2={field2}")
        
        if field2 == 8:
            print(f"   ✅ УСПЕХ! field2=8 (сохранилось предыдущее значение)")
        elif field2 == -1:
            print(f"   ❌ ОШИБКА! field2=-1 (не сохранилось)")
        else:
            print(f"   ⚠️  Неожиданное значение: {field2}")

if __name__ == "__main__":
    try:
        test_output_fields()
    except Exception as e:
        print(f"\n❌ Ошибка: {e}")

