"""Middleware for handling root path prefix when behind reverse proxy"""
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import HTMLResponse, Response, RedirectResponse
from app.config import settings
import re


class RootPathMiddleware(BaseHTTPMiddleware):
    """Middleware to add root path prefix to HTML responses when behind reverse proxy"""
    
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        
        # Всегда выводим информацию для отладки
        print(f"[RootPathMiddleware] Запрос: {request.url.path}, ROOT_PATH={settings.ROOT_PATH}, Response type: {type(response).__name__}")
        
        # Если ROOT_PATH настроен, обрабатываем ответы
        if not settings.ROOT_PATH:
            print(f"[RootPathMiddleware] ROOT_PATH не установлен! Пропуск обработки.")
            return response
            
        root_path = settings.ROOT_PATH.rstrip('/')
        
        # Обрабатываем RedirectResponse - добавляем префикс к URL редиректа
        if isinstance(response, RedirectResponse):
            redirect_url = response.headers.get("location", "")
            if redirect_url and redirect_url.startswith("/") and not redirect_url.startswith(("//", "http://", "https://")):
                # Если URL уже содержит ROOT_PATH, не добавляем его повторно
                if root_path and redirect_url.startswith(root_path):
                    print(f"[RootPathMiddleware] Редирект уже содержит ROOT_PATH: {redirect_url}")
                    return response
                # Это внутренний редирект, добавляем префикс
                new_url = f"{root_path}{redirect_url}"
                print(f"[RootPathMiddleware] Редирект: {redirect_url} -> {new_url}")
                response.headers["location"] = new_url
            return response
        
        # Проверяем Content-Type для определения HTML ответов ДО чтения тела
        content_type = response.headers.get("content-type", "").lower()
        
        # Пропускаем не-HTML ответы (CSS, JS, изображения и т.д.) БЕЗ чтения тела
        # Проверяем строго по Content-Type, игнорируя hasattr(response, 'render')
        if content_type:
            # Если Content-Type явно указан и это не HTML, пропускаем
            if "text/html" not in content_type:
                print(f"[RootPathMiddleware] Пропуск: Content-Type={content_type} не является HTML")
                return response
        
        # Проверяем по Content-Type и типу ответа (НЕ используем hasattr для проверки)
        is_html = (
            "text/html" in content_type or
            isinstance(response, HTMLResponse)
        )
        
        # Если Content-Type не указан, но есть метод render, это может быть TemplateResponse
        # Проверяем это только если Content-Type не указан или пустой
        if not content_type and hasattr(response, 'render'):
            is_html = True
        
        # Отладочный вывод
        print(f"[RootPathMiddleware] ROOT_PATH={root_path}, Content-Type={content_type}, is_html={is_html}, response_type={type(response).__name__}, path={request.url.path}")
        
        # Обрабатываем только HTML ответы
        if is_html:
            print(f"[RootPathMiddleware] Начинаем обработку HTML ответа...")
            # Получаем тело ответа
            body = b""
            async for chunk in response.body_iterator:
                body += chunk
            
            # Проверяем, что тело не пустое
            if not body:
                return response
            
            # Декодируем в строку
            try:
                html_content = body.decode('utf-8')
                
                # Проверяем, что это действительно HTML (содержит теги)
                if '<html' not in html_content.lower() and '<!doctype' not in html_content.lower():
                    print(f"[RootPathMiddleware] Пропуск: не HTML контент в теле ответа")
                    # Если это не HTML, создаем новый ответ с оригинальным телом
                    new_headers = dict(response.headers)
                    return Response(
                        content=body,
                        status_code=response.status_code,
                        headers=new_headers,
                        media_type=content_type or "text/html"
                    )
                
                # Заменяем абсолютные пути на пути с префиксом
                # Паттерны для замены в HTML атрибутах (исключаем внешние ссылки, якоря, mailto, tel):
                # Сначала обрабатываем href - самый важный
                # Заменяем href="/path" на href="/cloud2/path", но НЕ href="http://...", href="#", href="mailto:"
                # Используем более простой и надежный паттерн
                def replace_href(match):
                    path = match.group(1)
                    # Проверяем, что это не внешняя ссылка
                    if path.startswith(('http://', 'https://', '//', 'mailto:', 'tel:', '#')):
                        return match.group(0)
                    # Если путь уже содержит root_path, не добавляем его повторно
                    if root_path and path.startswith(root_path):
                        return match.group(0)
                    return f'href="{root_path}{path}"'
                
                # Подсчитываем замены для отладки
                # Паттерн не должен захватывать пути, уже содержащие root_path
                if root_path:
                    # Используем negative lookahead, чтобы не захватывать пути, начинающиеся с root_path
                    href_pattern = rf'href="(/(?!{re.escape(root_path.lstrip("/"))})[^"]+)"'
                else:
                    href_pattern = r'href="(/[^"]+)"'
                href_count_before = len(re.findall(r'href="(/[^"]+)"', html_content))
                html_content = re.sub(
                    href_pattern,
                    replace_href,
                    html_content
                )
                href_count_after = len(re.findall(rf'href="{root_path}/', html_content))
                
                print(f"[RootPathMiddleware] Заменено href: {href_count_before} -> {href_count_after} с префиксом {root_path}")
                # Затем src
                def replace_src(match):
                    path = match.group(1)
                    if path.startswith(('http://', 'https://', '//', 'data:')):
                        return match.group(0)
                    # Если путь уже содержит root_path, не добавляем его повторно
                    if root_path and path.startswith(root_path):
                        return match.group(0)
                    return f'src="{root_path}{path}"'
                
                html_content = re.sub(
                    r'src="(/[^"]+)"',
                    replace_src,
                    html_content
                )
                # Затем action
                def replace_action(match):
                    path = match.group(1)
                    if path.startswith(('http://', 'https://', '//')):
                        return match.group(0)
                    # Если путь уже содержит root_path, не добавляем его повторно
                    if root_path and path.startswith(root_path):
                        return match.group(0)
                    return f'action="{root_path}{path}"'
                
                html_content = re.sub(
                    r'action="(/[^"]+)"',
                    replace_action,
                    html_content
                )
                # CSS url()
                html_content = re.sub(
                    r'url\((/(?!http|https|//|data:)[^)]+)\)',
                    rf'url({root_path}\1)',
                    html_content
                )
                
                # Обработка JavaScript кода внутри <script> тегов
                # Заменяем абсолютные пути в fetch, window.location, и других вызовах
                # НЕ заменяем пути, которые уже содержат ROOT_PATH или root_path
                def replace_js_paths(match):
                    script_attrs = match.group(1)
                    script_content = match.group(2)
                    # Заменяем пути в fetch('/path'), window.location.href='/path', и т.д.
                    # Исключаем внешние ссылки (http://, https://, //) и пути, уже содержащие root_path
                    # Сначала проверяем, не содержит ли скрипт уже root_path или переменную ROOT_PATH
                    if root_path and (root_path in script_content or 'ROOT_PATH' in script_content or 'const ROOT_PATH' in script_content):
                        # Если уже содержит root_path или использует переменную ROOT_PATH, пропускаем замену для этого скрипта
                        return f'<script{script_attrs}>{script_content}</script>'
                    
                    js_patterns = [
                        # fetch('/path') или fetch("/path")
                        (r"fetch\(['\"]/(?!http|https|//)([^'\"]+)['\"]", rf'fetch("{root_path}/\1"'),
                        # fetch(`/path`) в template literals
                        (r"fetch\(`/(?!http|https|//)([^`]+)`", rf'fetch(`{root_path}/\1`'),
                        # '/api/', '/channels/' и т.д. в строках
                        (r"(['\"])/(?!http|https|//)(api|channels|static|login|logout|admin|settings|update|health|docs|openapi\.json)/", rf'\1{root_path}/\2/'),
                        # `/api/` в template literals
                        (r"`/(?!http|https|//)(api|channels|static|login|logout|admin|settings|update|health|docs|openapi\.json)/", rf'`{root_path}/\1/'),
                        # window.location.href='/path'
                        (r"window\.location\.href\s*=\s*['\"]/(?!http|https|//)([^'\"]+)['\"]", rf'window.location.href = "{root_path}/\1"'),
                        # window.location='/path'
                        (r"window\.location\s*=\s*['\"]/(?!http|https|//)([^'\"]+)['\"]", rf'window.location = "{root_path}/\1"'),
                        # location.href='/path'
                        (r"location\.href\s*=\s*['\"]/(?!http|https|//)([^'\"]+)['\"]", rf'location.href = "{root_path}/\1"'),
                    ]
                    for js_pattern, js_replacement in js_patterns:
                        script_content = re.sub(js_pattern, js_replacement, script_content)
                    return f'<script{script_attrs}>{script_content}</script>'
                
                # Обрабатываем содержимое <script> тегов
                html_content = re.sub(r'<script([^>]*)>(.*?)</script>', replace_js_paths, html_content, flags=re.DOTALL)
                
                # Кодируем обратно
                body = html_content.encode('utf-8')
                
                # Создаем новый ответ
                # Копируем все заголовки, но удаляем Content-Length (он будет пересчитан автоматически)
                # и убеждаемся, что Content-Type установлен
                new_headers = dict(response.headers)
                # Удаляем Content-Length, так как размер тела изменился
                new_headers.pop("content-length", None)
                if "content-type" not in new_headers:
                    new_headers["content-type"] = "text/html; charset=utf-8"
                
                print(f"[RootPathMiddleware] Успешно обработан HTML ответ, размер: {len(body)} байт")
                return HTMLResponse(
                    content=body,
                    status_code=response.status_code,
                    headers=new_headers
                )
            except (UnicodeDecodeError, AttributeError) as e:
                # Если не HTML или ошибка декодирования, возвращаем как есть
                print(f"[RootPathMiddleware] Ошибка обработки: {e}")
                import traceback
                traceback.print_exc()
                return response
        else:
            print(f"[RootPathMiddleware] Пропуск: не HTML ответ (is_html={is_html}, has_render={hasattr(response, 'render')})")
        
        return response

