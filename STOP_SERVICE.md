# Как остановить сервис myapp.service

## Проблема
Сервис продолжает перезапускаться даже после `systemctl stop`.

## Решение

1. **Отключите автоматический перезапуск:**
   ```bash
   systemctl disable myapp.service
   ```

2. **Остановите сервис:**
   ```bash
   systemctl stop myapp.service
   ```

3. **Проверьте статус:**
   ```bash
   systemctl status myapp.service
   ```

4. **Если сервис всё ещё перезапускается, проверьте конфигурацию:**
   ```bash
   cat /etc/systemd/system/myapp.service
   ```

5. **Если в конфигурации есть `Restart=always` или `Restart=on-failure`, отредактируйте файл:**
   ```bash
   sudo nano /etc/systemd/system/myapp.service
   ```
   
   Найдите строку `Restart=` и измените на:
   ```
   Restart=no
   ```
   
   Или удалите строку `Restart=` полностью.

6. **Перезагрузите конфигурацию systemd:**
   ```bash
   sudo systemctl daemon-reload
   ```

7. **Остановите сервис снова:**
   ```bash
   systemctl stop myapp.service
   ```

8. **Проверьте, что сервис остановлен:**
   ```bash
   systemctl status myapp.service
   # Должно быть: Active: inactive (dead)
   ```

## Если ничего не помогает

1. **Убейте процесс вручную:**
   ```bash
   # Найдите процесс
   ps aux | grep "run.py\|python.*cloudtest\|python.*CloudTest"
   
   # Убейте процесс (замените PID на реальный)
   kill -9 <PID>
   ```

2. **Удалите сервис полностью:**
   ```bash
   sudo systemctl stop myapp.service
   sudo systemctl disable myapp.service
   sudo rm /etc/systemd/system/myapp.service
   sudo systemctl daemon-reload
   ```

