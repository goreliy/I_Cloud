"""
Stress test for IBolid Cloud
Асинхронный стресс-тест с настраиваемыми параметрами
"""
import asyncio
import aiohttp
import time
import random
import argparse
import json
import sys
from datetime import datetime
from collections import defaultdict
from typing import Dict, List


class StressTest:
    """Класс для проведения стресс-тестирования"""
    
    def __init__(self, 
                 base_url: str,
                 channel_id: int,
                 api_key: str,
                 workers: int,
                 rps: int,
                 duration: int):
        self.base_url = base_url.rstrip('/')
        self.channel_id = channel_id
        self.api_key = api_key
        self.workers = workers
        self.rps = rps
        self.duration = duration
        
        self.stats = {
            'total': 0,
            'success': 0,
            'failed': 0,
            'latencies': [],
            'errors': defaultdict(int),
            'status_codes': defaultdict(int)
        }
        
        self.running = True
    
    async def send_request(self, session: aiohttp.ClientSession) -> None:
        """Отправить один запрос с рандомными данными"""
        # Генерация рандомных значений для всех полей
        params = {
            'api_key': self.api_key,
            'field1': round(random.uniform(0, 100), 2),
            'field2': round(random.uniform(0, 100), 2),
            'field3': round(random.uniform(0, 100), 2),
            'field4': round(random.uniform(0, 100), 2),
            'field5': round(random.uniform(0, 100), 2),
            'field6': round(random.uniform(0, 100), 2),
            'field7': round(random.uniform(0, 100), 2),
            'field8': round(random.uniform(0, 100), 2),
        }
        
        start_time = time.time()
        
        try:
            async with session.post(
                f"{self.base_url}/update",
                params=params,
                timeout=aiohttp.ClientTimeout(total=30)
            ) as response:
                latency = time.time() - start_time
                self.stats['latencies'].append(latency)
                self.stats['status_codes'][response.status] += 1
                
                if response.status == 200:
                    self.stats['success'] += 1
                else:
                    self.stats['failed'] += 1
                    error_text = await response.text()
                    self.stats['errors'][f"HTTP_{response.status}"] += 1
                
                self.stats['total'] += 1
                
        except asyncio.TimeoutError:
            latency = time.time() - start_time
            self.stats['failed'] += 1
            self.stats['errors']['TimeoutError'] += 1
            self.stats['total'] += 1
            self.stats['latencies'].append(latency)
        except aiohttp.ClientError as e:
            latency = time.time() - start_time
            self.stats['failed'] += 1
            self.stats['errors'][type(e).__name__] += 1
            self.stats['total'] += 1
            self.stats['latencies'].append(latency)
        except Exception as e:
            latency = time.time() - start_time
            self.stats['failed'] += 1
            self.stats['errors'][f'Unknown_{type(e).__name__}'] += 1
            self.stats['total'] += 1
            self.stats['latencies'].append(latency)
    
    async def worker(self, worker_id: int) -> None:
        """Воркер для отправки запросов"""
        connector = aiohttp.TCPConnector(limit=100)  # Лимит соединений
        async with aiohttp.ClientSession(connector=connector) as session:
            requests_sent = 0
            start_time = time.time()
            
            while self.running and (time.time() - start_time) < self.duration:
                # Отправить запрос
                await self.send_request(session)
                requests_sent += 1
                
                # Контроль RPS (requests per second)
                elapsed = time.time() - start_time
                if elapsed > 0:
                    target_requests = int(elapsed * (self.rps / self.workers))
                    
                    if requests_sent > target_requests:
                        # Ждем для контроля RPS
                        wait_time = (requests_sent / (self.rps / self.workers)) - elapsed
                        if wait_time > 0:
                            await asyncio.sleep(wait_time)
                    else:
                        # Минимальная задержка между запросами
                        await asyncio.sleep(0.001)
    
    async def monitor(self, start_time: float) -> None:
        """Мониторинг в реальном времени"""
        last_total = 0
        
        while self.running and (time.time() - start_time) < self.duration:
            await asyncio.sleep(1)
            
            elapsed = time.time() - start_time
            total = self.stats['total']
            current_rps = (total - last_total)  # RPS за последнюю секунду
            avg_rps = total / elapsed if elapsed > 0 else 0
            
            if self.stats['latencies']:
                recent_latencies = self.stats['latencies'][-100:]  # Последние 100
                avg_latency = sum(recent_latencies) / len(recent_latencies)
            else:
                avg_latency = 0
            
            success_rate = (self.stats['success'] / total * 100) if total > 0 else 0
            
            print(f"\r[{int(elapsed):3d}s] "
                  f"Total: {total:6d} | "
                  f"Success: {self.stats['success']:6d} ({success_rate:5.1f}%) | "
                  f"Failed: {self.stats['failed']:5d} | "
                  f"RPS: {current_rps:4.0f} (avg: {avg_rps:6.1f}) | "
                  f"Latency: {avg_latency*1000:6.1f}ms", 
                  end='', flush=True)
            
            last_total = total
    
    async def run(self) -> Dict:
        """Запустить тест"""
        print("=" * 80)
        print("STRESS TEST START")
        print("=" * 80)
        print(f"Configuration:")
        print(f"  Base URL:     {self.base_url}")
        print(f"  Channel ID:   {self.channel_id}")
        print(f"  Workers:      {self.workers}")
        print(f"  Target RPS:   {self.rps}")
        print(f"  Duration:     {self.duration}s")
        print(f"  Total target: {self.rps * self.duration} requests")
        print("-" * 80)
        
        start_time = time.time()
        
        try:
            # Запустить воркеры и мониторинг
            tasks = [
                self.monitor(start_time),
                *[self.worker(i) for i in range(self.workers)]
            ]
            
            await asyncio.gather(*tasks)
            
        except KeyboardInterrupt:
            print("\n\n[!] Test interrupted by user")
            self.running = False
            await asyncio.sleep(0.5)  # Дать воркерам завершиться
        
        total_time = time.time() - start_time
        
        # Вывести результаты
        results = self.print_results(total_time)
        
        return results
    
    def print_results(self, total_time: float) -> Dict:
        """Вывести результаты тестирования"""
        print("\n\n" + "=" * 80)
        print("STRESS TEST RESULTS")
        print("=" * 80)
        
        # Основные метрики
        print(f"\nTotal requests:     {self.stats['total']:,}")
        print(f"Successful:         {self.stats['success']:,} ({self.stats['success']/self.stats['total']*100:.1f}%)" if self.stats['total'] > 0 else "Successful:         0")
        print(f"Failed:             {self.stats['failed']:,} ({self.stats['failed']/self.stats['total']*100:.1f}%)" if self.stats['total'] > 0 else "Failed:             0")
        print(f"Duration:           {total_time:.2f}s")
        
        # RPS метрики
        actual_rps = self.stats['total'] / total_time if total_time > 0 else 0
        print(f"\nActual RPS:         {actual_rps:.2f}")
        print(f"Target RPS:         {self.rps}")
        print(f"Efficiency:         {actual_rps/self.rps*100:.1f}%" if self.rps > 0 else "Efficiency:         N/A")
        
        # Latency метрики
        if self.stats['latencies']:
            latencies_ms = [l * 1000 for l in self.stats['latencies']]
            latencies_ms.sort()
            
            avg_latency = sum(latencies_ms) / len(latencies_ms)
            min_latency = min(latencies_ms)
            max_latency = max(latencies_ms)
            p50 = latencies_ms[len(latencies_ms) // 2]
            p95 = latencies_ms[int(len(latencies_ms) * 0.95)]
            p99 = latencies_ms[int(len(latencies_ms) * 0.99)]
            
            print(f"\nLatency (ms):")
            print(f"  Average:          {avg_latency:.2f}ms")
            print(f"  Min:              {min_latency:.2f}ms")
            print(f"  Max:              {max_latency:.2f}ms")
            print(f"  P50 (median):     {p50:.2f}ms")
            print(f"  P95:              {p95:.2f}ms")
            print(f"  P99:              {p99:.2f}ms")
        
        # HTTP Status codes
        if self.stats['status_codes']:
            print(f"\nHTTP Status Codes:")
            for code, count in sorted(self.stats['status_codes'].items()):
                print(f"  {code}:              {count:,}")
        
        # Ошибки
        if self.stats['errors']:
            print(f"\nErrors:")
            for error, count in sorted(self.stats['errors'].items(), key=lambda x: x[1], reverse=True):
                print(f"  {error}:            {count:,}")
        
        # Создать результаты для сохранения
        results = {
            'timestamp': datetime.now().isoformat(),
            'config': {
                'base_url': self.base_url,
                'channel_id': self.channel_id,
                'workers': self.workers,
                'target_rps': self.rps,
                'duration': self.duration
            },
            'results': {
                'total': self.stats['total'],
                'success': self.stats['success'],
                'failed': self.stats['failed'],
                'actual_rps': actual_rps,
                'duration': total_time,
                'avg_latency_ms': avg_latency if self.stats['latencies'] else 0,
                'min_latency_ms': min_latency if self.stats['latencies'] else 0,
                'max_latency_ms': max_latency if self.stats['latencies'] else 0,
                'p50_latency_ms': p50 if self.stats['latencies'] else 0,
                'p95_latency_ms': p95 if self.stats['latencies'] else 0,
                'p99_latency_ms': p99 if self.stats['latencies'] else 0,
                'status_codes': dict(self.stats['status_codes']),
                'errors': dict(self.stats['errors'])
            }
        }
        
        # Сохранить в JSON
        filename = f"stress_test_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, ensure_ascii=False)
        
        print(f"\n{'='*80}")
        print(f"Results saved to: {filename}")
        print(f"{'='*80}\n")
        
        return results


def main():
    """CLI entry point"""
    parser = argparse.ArgumentParser(
        description='Stress test for IBolid Cloud API',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
Examples:
  # Basic test (100 RPS, 10 workers, 60 seconds)
  python tests/stress_test.py --api-key YOUR_KEY
  
  # High load test (1000 RPS, 50 workers, 120 seconds)
  python tests/stress_test.py --api-key YOUR_KEY --rps 1000 --workers 50 --duration 120
  
  # Maximum load test (10000 RPS, 100 workers, 60 seconds)
  python tests/stress_test.py --api-key YOUR_KEY --rps 10000 --workers 100
        '''
    )
    
    parser.add_argument('--url', default='http://localhost:8000', 
                        help='Base URL (default: http://localhost:8000)')
    parser.add_argument('--channel', type=int, default=2, 
                        help='Channel ID (default: 2)')
    parser.add_argument('--api-key', required=True, 
                        help='Write API key для канала (обязательно)')
    parser.add_argument('--workers', type=int, default=10, 
                        help='Количество параллельных воркеров: 1-1000 (default: 10)')
    parser.add_argument('--rps', type=int, default=100, 
                        help='Запросов в секунду (RPS): 1-100000 (default: 100)')
    parser.add_argument('--duration', type=int, default=60, 
                        help='Длительность теста в секундах: 1-3600 (default: 60)')
    
    args = parser.parse_args()
    
    # Валидация параметров
    errors = []
    if not 1 <= args.workers <= 1000:
        errors.append("Количество воркеров должно быть от 1 до 1000")
    
    if not 1 <= args.rps <= 100000:
        errors.append("RPS должен быть от 1 до 100000")
    
    if not 1 <= args.duration <= 3600:
        errors.append("Длительность должна быть от 1 до 3600 секунд (1 час)")
    
    if errors:
        print("Ошибки валидации:")
        for error in errors:
            print(f"  - {error}")
        sys.exit(1)
    
    # Предупреждения для высоких нагрузок
    if args.rps > 1000 or args.workers > 50:
        print("\n" + "!" * 80)
        print("ВНИМАНИЕ: Высокая нагрузка!")
        print(f"  RPS: {args.rps}, Workers: {args.workers}")
        print("  Это может перегрузить сервер и вызвать ошибки.")
        print("  Рекомендуется начинать с малых значений (RPS=100, Workers=10)")
        print("!" * 80)
        
        response = input("\nПродолжить? (yes/no): ")
        if response.lower() not in ['yes', 'y', 'да']:
            print("Тест отменен")
            sys.exit(0)
    
    # Создать и запустить тест
    test = StressTest(
        base_url=args.url,
        channel_id=args.channel,
        api_key=args.api_key,
        workers=args.workers,
        rps=args.rps,
        duration=args.duration
    )
    
    try:
        results = asyncio.run(test.run())
        
        # Вывести рекомендации
        print("\nРекомендации:")
        success_rate = results['results']['success'] / results['results']['total'] * 100 if results['results']['total'] > 0 else 0
        
        if success_rate < 95:
            print("  [!] Низкий процент успешных запросов (<95%)")
            print("      Рекомендация: уменьшите RPS или увеличьте количество воркеров сервера")
        
        if results['results']['avg_latency_ms'] > 1000:
            print("  [!] Высокая средняя задержка (>1000ms)")
            print("      Рекомендация: оптимизируйте БД запросы или увеличьте ресурсы сервера")
        
        if results['results']['actual_rps'] < results['config']['target_rps'] * 0.8:
            print("  [!] Не достигнут целевой RPS (<80% от цели)")
            print("      Рекомендация: сервер не справляется с нагрузкой")
        
        if success_rate >= 99 and results['results']['avg_latency_ms'] < 100:
            print("  [✓] Отличная производительность!")
            print("      Сервер работает стабильно")
        
        sys.exit(0)
        
    except KeyboardInterrupt:
        print("\n\nТест прерван пользователем")
        sys.exit(130)
    except Exception as e:
        print(f"\n\nОшибка выполнения теста: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()


