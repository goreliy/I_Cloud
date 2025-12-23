#!/usr/bin/env python3
"""
Независимый запуск стресс-теста
Не требует запущенного сервера для настройки
"""
import sys
import os
import subprocess
import sqlite3
from pathlib import Path


def get_channels():
    """Получить список каналов из БД"""
    db_path = Path("ibolid.db")
    if not db_path.exists():
        print("❌ База данных не найдена!")
        print("   Сначала запустите сервер: python run.py")
        return []
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT c.id, c.name, c.description, ak.key
            FROM channels c
            LEFT JOIN api_keys ak ON c.id = ak.channel_id AND ak.type = 'write' AND ak.is_active = 1
            ORDER BY c.id
        """)
        
        channels = cursor.fetchall()
        conn.close()
        return channels
    except Exception as e:
        print(f"❌ Ошибка чтения БД: {e}")
        return []


def main():
    print("=" * 80)
    print("🚀 СТРЕСС-ТЕСТ - Независимый запуск")
    print("=" * 80)
    print()
    
    # Получить каналы
    channels = get_channels()
    
    if not channels:
        print("❌ Нет доступных каналов!")
        print("   Создайте канал через веб-интерфейс")
        sys.exit(1)
    
    # Показать доступные каналы
    print("Доступные каналы:")
    print()
    for ch_id, name, desc, api_key in channels:
        status = "✅" if api_key else "⚠️  (нет API ключа)"
        print(f"  [{ch_id}] {name} {status}")
        if desc:
            print(f"      {desc}")
        if api_key:
            print(f"      Write API Key: {api_key}")
        print()
    
    # Выбор канала
    print("-" * 80)
    while True:
        try:
            channel_id = input("Введите ID канала для теста: ").strip()
            channel_id = int(channel_id)
            
            # Найти канал
            channel = next((c for c in channels if c[0] == channel_id), None)
            if not channel:
                print("❌ Канал не найден! Попробуйте снова.")
                continue
            
            if not channel[3]:
                print("❌ У канала нет Write API ключа!")
                continue
            
            api_key = channel[3]
            break
        except ValueError:
            print("❌ Введите число!")
        except KeyboardInterrupt:
            print("\n\nОтменено пользователем")
            sys.exit(0)
    
    # Параметры теста
    print()
    print("-" * 80)
    print("Параметры теста:")
    print()
    
    # Workers
    while True:
        try:
            workers_input = input("Количество воркеров [10]: ").strip()
            workers = int(workers_input) if workers_input else 10
            if 1 <= workers <= 1000:
                break
            print("❌ Должно быть от 1 до 1000")
        except ValueError:
            print("❌ Введите число!")
    
    # RPS
    while True:
        try:
            rps_input = input("Запросов в секунду (RPS) [100]: ").strip()
            rps = int(rps_input) if rps_input else 100
            if 1 <= rps <= 100000:
                break
            print("❌ Должно быть от 1 до 100000")
        except ValueError:
            print("❌ Введите число!")
    
    # Duration
    while True:
        try:
            duration_input = input("Длительность в секундах [60]: ").strip()
            duration = int(duration_input) if duration_input else 60
            if 1 <= duration <= 3600:
                break
            print("❌ Должно быть от 1 до 3600 (1 час)")
        except ValueError:
            print("❌ Введите число!")
    
    # URL
    url_input = input("URL сервера [http://localhost:8000]: ").strip()
    url = url_input if url_input else "http://localhost:8000"
    
    # Предупреждение
    print()
    print("=" * 80)
    print("⚠️  ВНИМАНИЕ!")
    print("=" * 80)
    total_requests = rps * duration
    print(f"  Будет отправлено примерно {total_requests:,} запросов")
    print(f"  Это создаст большую нагрузку на сервер")
    print()
    
    if rps > 1000 or workers > 50:
        print("  ⚠️  ВЫСОКАЯ НАГРУЗКА!")
        print(f"     RPS: {rps}, Workers: {workers}")
        print("     Это может перегрузить сервер!")
        print()
    
    confirm = input("Продолжить? (yes/no): ").strip().lower()
    if confirm not in ['yes', 'y', 'да', 'д']:
        print("\nТест отменен")
        sys.exit(0)
    
    # Запуск теста
    print()
    print("=" * 80)
    print("🚀 ЗАПУСК ТЕСТА...")
    print("=" * 80)
    print()
    
    cmd = [
        sys.executable,
        'tests/stress_test.py',
        '--url', url,
        '--channel', str(channel_id),
        '--api-key', api_key,
        '--workers', str(workers),
        '--rps', str(rps),
        '--duration', str(duration)
    ]
    
    try:
        result = subprocess.run(cmd)
        sys.exit(result.returncode)
    except KeyboardInterrupt:
        print("\n\nТест прерван пользователем")
        sys.exit(130)
    except Exception as e:
        print(f"\n❌ Ошибка запуска: {e}")
        sys.exit(1)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nОтменено пользователем")
        sys.exit(0)

