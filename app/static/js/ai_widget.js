(() => {
  // Получаем root_path из глобальной переменной или используем пустую строку
  const getRootPath = () => {
    if (typeof window !== 'undefined' && window.ROOT_PATH) {
      return window.ROOT_PATH;
    }
    // Пытаемся определить из текущего URL
    const pathname = window.location.pathname;
    if (pathname.startsWith('/cloud2')) {
      return '/cloud2';
    }
    return '';
  };
  
  const ROOT_PATH = getRootPath();
  console.log('[AIWidgetManager] Инициализация, ROOT_PATH:', ROOT_PATH);
  
  // Функция для добавления root_path к абсолютным путям
  const apiUrl = (path) => {
    if (!path) return path;
    // Если путь уже содержит root_path, не добавляем его снова
    if (ROOT_PATH && path.startsWith(ROOT_PATH)) {
      console.log('[AIWidgetManager] Путь уже содержит ROOT_PATH:', path);
      return path;
    }
    // Если путь начинается с /, добавляем root_path
    if (path.startsWith('/')) {
      const fullPath = ROOT_PATH + path;
      console.log('[AIWidgetManager] Добавлен ROOT_PATH:', path, '->', fullPath);
      return fullPath;
    }
    console.log('[AIWidgetManager] Относительный путь (без изменений):', path);
    return path;
  };
  
  const DEFAULT_SELECTORS = {
    serviceList: '#ai-service-list',
    activeServiceLabel: '#ai-active-service-label',
    frame: '#ai-service-frame',
    prompt: {
      common: '#ai-prompt-common',
      html: '#ai-prompt-html',
      css: '#ai-prompt-css',
      js: '#ai-prompt-js',
    },
    userRequest: '#ai-user-request',
    fullPrompt: '#ai-full-prompt',
    rebuildFullPrompt: '#ai-rebuild-full-prompt',
    response: {
      raw: '#ai-response-raw',
      html: '#ai-response-html',
      css: '#ai-response-css',
      js: '#ai-response-js',
    },
    versionComment: '#ai-version-comment',
    applyButton: '#ai-apply-response',
    parseButton: '#ai-parse-response',
    clearButton: '#ai-clear-response',
    refreshButton: '#ai-refresh-prompt',
    copyButtons: '[data-ai-copy]',
    refine: {
      feedback: '#ai-refine-feedback',
      generateButton: '#ai-generate-refine',
      result: '#ai-refine-result',
    },
    versions: {
      container: '#widget-version-list',
      emptyState: '#widget-version-empty',
      refreshButton: '#ai-refresh-versions',
    },
    hiddenInputs: {
      serviceId: '#ai_service_id_input',
      promptUsed: '#prompt_used_input',
      versionComment: '#version_comment_input',
    },
    form: '#widgetForm',
    htmlTextarea: 'textarea[name="html_code"]',
    cssTextarea: 'textarea[name="css_code"]',
    jsTextarea: 'textarea[name="js_code"]',
    widgetTypeSelect: '#widgetTypeSelect',
  };

  const AIWidgetManager = {
    init(options = {}) {
      if (this._initialized) return;
      this._initialized = true;
      this.config = {
        mode: 'create',
        channelId: null,
        widgetId: null,
        formId: 'widgetForm',
        selectors: DEFAULT_SELECTORS,
        ...options,
      };

      this.state = {
        services: [],
        activeService: null,
        prompt: null,
      };

      this.cacheElements();
      this.bindEvents();
      this.fetchServices();

      if (this.config.mode === 'edit' && this.config.widgetId) {
        this.loadVersions();
        this.bindVersionActions();
        this.bindRefineActions();
      }
    },

    cacheElements() {
      const sel = this.config.selectors;
      this.elements = {
        serviceList: document.querySelector(sel.serviceList),
        activeServiceLabel: document.querySelector(sel.activeServiceLabel),
        frame: document.querySelector(sel.frame),
      openNewTab: document.querySelector('#ai-open-new-tab'),
        prompt: {
          common: document.querySelector(sel.prompt.common),
          html: document.querySelector(sel.prompt.html),
          css: document.querySelector(sel.prompt.css),
          js: document.querySelector(sel.prompt.js),
        },
      userRequest: document.querySelector(sel.userRequest),
      fullPrompt: document.querySelector(sel.fullPrompt),
      rebuildFullPrompt: document.querySelector(sel.rebuildFullPrompt),
        response: {
          raw: document.querySelector(sel.response.raw),
          html: document.querySelector(sel.response.html),
          css: document.querySelector(sel.response.css),
          js: document.querySelector(sel.response.js),
        },
        versionComment: document.querySelector(sel.versionComment),
        applyButton: document.querySelector(sel.applyButton),
        parseButton: document.querySelector(sel.parseButton),
        clearButton: document.querySelector(sel.clearButton),
        refreshButton: document.querySelector(sel.refreshButton),
        copyButtons: Array.from(document.querySelectorAll(sel.copyButtons)),
        refine: {
          feedback: document.querySelector(sel.refine.feedback),
          generateButton: document.querySelector(sel.refine.generateButton),
          result: document.querySelector(sel.refine.result),
        },
        versions: {
          container: document.querySelector(sel.versions.container),
          emptyState: document.querySelector(sel.versions.emptyState),
          refreshButton: document.querySelector(sel.versions.refreshButton),
        },
        hiddenInputs: {
          serviceId: document.querySelector(sel.hiddenInputs.serviceId),
          promptUsed: document.querySelector(sel.hiddenInputs.promptUsed),
          versionComment: document.querySelector(sel.hiddenInputs.versionComment),
        },
        form: document.querySelector(`#${this.config.formId}`) || document.querySelector(sel.form),
        htmlTextarea: document.querySelector(sel.htmlTextarea),
        cssTextarea: document.querySelector(sel.cssTextarea),
        jsTextarea: document.querySelector(sel.jsTextarea),
        widgetTypeSelect: document.querySelector(sel.widgetTypeSelect),
      };
    },

    bindEvents() {
      if (this.elements.copyButtons) {
        this.elements.copyButtons.forEach((button) => {
          button.addEventListener('click', () => {
            const target = button.getAttribute('data-ai-copy');
            this.copyToClipboard(target);
          });
        });
      }

      if (this.elements.parseButton) {
        this.elements.parseButton.addEventListener('click', () => this.handleParse());
      }

      if (this.elements.clearButton) {
        this.elements.clearButton.addEventListener('click', () => this.clearResponse());
      }

      if (this.elements.applyButton) {
        this.elements.applyButton.addEventListener('click', () => this.applyResponse());
      }

      if (this.elements.refreshButton) {
        this.elements.refreshButton.addEventListener('click', () => this.loadPrompt(true));
      }

      if (this.elements.versions.refreshButton) {
        this.elements.versions.refreshButton.addEventListener('click', () => this.loadVersions());
      }

      if (this.elements.rebuildFullPrompt) {
        this.elements.rebuildFullPrompt.addEventListener('click', () => this.loadPrompt(true));
      }

      if (this.elements.userRequest) {
        this.elements.userRequest.addEventListener('input', () => this.debouncedBuild());
      }
    },

    debouncedBuild: (() => {
      let t;
      return function() {
        clearTimeout(t);
        t = setTimeout(() => this.loadPrompt(true), 500);
      };
    })(),

    async fetchServices() {
      if (!this.config.channelId || !this.elements.serviceList) return;
      try {
        const path = `/api/channels/${this.config.channelId}/ai/services`;
        const url = apiUrl(path);
        console.log('[AIWidgetManager] Загрузка сервисов:', { path, url, ROOT_PATH: ROOT_PATH || '(пусто)' });
        const response = await fetch(url);
        console.log('[AIWidgetManager] Ответ сервера:', { status: response.status, statusText: response.statusText, contentType: response.headers.get('content-type') });
        if (!response.ok) {
          const errorText = await response.text();
          console.error('[AIWidgetManager] Ошибка ответа:', errorText.substring(0, 200));
          throw new Error(`Не удалось загрузить список сервисов: ${response.status} ${response.statusText}`);
        }
        const text = await response.text();
        console.log('[AIWidgetManager] Текст ответа:', text.substring(0, 200));
        if (!text.trim()) {
          throw new Error('Пустой ответ от сервера');
        }
        let services;
        try {
          services = JSON.parse(text);
        } catch (jsonError) {
          console.error('[AIWidgetManager] Ошибка парсинга JSON:', jsonError, 'Текст:', text.substring(0, 500));
          throw new Error(`Ошибка парсинга JSON: ${jsonError.message}. Ответ: ${text.substring(0, 100)}`);
        }
        this.state.services = services;
        this.renderServiceButtons();
      } catch (error) {
        console.error('[AIWidgetManager] Ошибка загрузки сервисов:', error);
        this.elements.serviceList?.insertAdjacentHTML(
          'beforeend',
          `<span class="text-danger small">${error.message}</span>`
        );
      }
    },

    renderServiceButtons() {
      if (!this.elements.serviceList) return;
      this.elements.serviceList.innerHTML = '';
      if (!this.state.services.length) {
        this.elements.serviceList.innerHTML = '<span class="text-muted small">Нет доступных сервисов. Добавьте их в настройках администратора.</span>';
        return;
      }

      this.state.services.forEach((service, index) => {
        const button = document.createElement('button');
        button.type = 'button';
        button.className = 'btn btn-outline-primary btn-sm';
        button.textContent = service.name;
        button.dataset.alias = service.alias;
        button.addEventListener('click', () => this.activateService(service));
        this.elements.serviceList.appendChild(button);
        if (index === 0) {
          this.activateService(service);
        }
      });
    },

    activateService(service) {
      this.state.activeService = service;
      if (this.elements.activeServiceLabel) {
        this.elements.activeServiceLabel.textContent = service.name;
        this.elements.activeServiceLabel.classList.remove('bg-secondary');
        this.elements.activeServiceLabel.classList.add('bg-primary');
      }

      if (this.elements.frame) this.elements.frame.src = service.url;
      if (this.elements.openNewTab) this.elements.openNewTab.href = service.url;

      Array.from(this.elements.serviceList?.children || []).forEach((btn) => {
        btn.classList.toggle('btn-primary', btn.dataset.alias === service.alias);
        btn.classList.toggle('btn-outline-primary', btn.dataset.alias !== service.alias);
      });

      this.loadPrompt();
    },

    async loadPrompt(force = false) {
      if (!this.state.activeService || !this.config.channelId) {
        if (!this.state.activeService) {
          alert('Сначала выберите сервис ИИ из списка выше.');
        }
        return;
      }
      if (!force && this._loadingPrompt) return;

      try {
        this._loadingPrompt = true;
        const params = new URLSearchParams({ service_alias: this.state.activeService.alias });
        if (this.config.widgetId) {
          params.set('widget_id', this.config.widgetId);
        }
        const userRequest = (this.elements.userRequest?.value || '').trim();
        if (userRequest) params.set('user_request', userRequest);
        const url = apiUrl(`/api/channels/${this.config.channelId}/widgets/prompt?${params.toString()}`);
        const response = await fetch(url);
        if (!response.ok) {
          const errorText = await response.text();
          throw new Error(`Не удалось получить предпромпт: ${response.status} ${errorText.substring(0, 100)}`);
        }
        const text = await response.text();
        if (!text.trim()) {
          throw new Error('Пустой ответ от сервера');
        }
        let data;
        try {
          data = JSON.parse(text);
        } catch (jsonError) {
          console.error('Ошибка парсинга JSON:', jsonError, 'Ответ:', text.substring(0, 200));
          throw new Error(`Ошибка парсинга ответа сервера: ${jsonError.message}. Проверьте, что ROOT_PATH настроен правильно.`);
        }
        this.state.prompt = data.prompt;
        this.writePromptToUI();
        if (this.elements.fullPrompt) this.elements.fullPrompt.value = data.full_prompt || '';
      } catch (error) {
        console.error('Ошибка загрузки промпта:', error);
        alert(`Ошибка: ${error.message}`);
        if (this.elements.fullPrompt) {
          this.elements.fullPrompt.value = `Ошибка загрузки промпта: ${error.message}`;
        }
      } finally {
        this._loadingPrompt = false;
      }
    },

    writePromptToUI() {
      if (!this.state.prompt) return;
      const { prompt } = this.state;
      const { common, html, css, js } = prompt;
      if (this.elements.prompt.common) this.elements.prompt.common.value = common || '';
      if (this.elements.prompt.html) this.elements.prompt.html.value = html || '';
      if (this.elements.prompt.css) this.elements.prompt.css.value = css || '';
      if (this.elements.prompt.js) this.elements.prompt.js.value = js || '';
    },

    copyToClipboard(selector) {
      const element = document.querySelector(selector);
      if (!element) return;
      element.select?.();
      navigator.clipboard.writeText(element.value || element.textContent || '').catch(() => {
        console.warn('Не удалось скопировать текст.');
      });
    },

    handleParse() {
      if (!this.state.activeService) {
        alert('Сначала выберите сервис ИИ из списка выше.');
        return;
      }
      if (!this.elements.response.raw) return;
      const rawText = this.elements.response.raw.value || '';
      if (!rawText.trim()) {
        alert('Вставьте ответ ИИ, прежде чем распарсить.');
        return;
      }

      try {
        const parsed = this.parseAiResponse(rawText);
        if (!parsed.html && !parsed.css && !parsed.js) {
          alert('Не удалось автоматически распарсить ответ. Убедитесь, что ответ содержит кодовые блоки с метками ```html, ```css, ```js или разделы HTML:, CSS:, JS:');
          return;
        }
        if (this.elements.response.html) this.elements.response.html.value = parsed.html || '';
        if (this.elements.response.css) this.elements.response.css.value = parsed.css || '';
        if (this.elements.response.js) this.elements.response.js.value = parsed.js || '';
      } catch (error) {
        console.error('Ошибка парсинга ответа:', error);
        alert(`Ошибка парсинга: ${error.message}`);
      }
    },

    parseAiResponse(raw) {
      const blocks = { html: '', css: '', js: '' };
      const regex = /```(\w+)?\s*([\s\S]*?)```/g;
      let match;
      while ((match = regex.exec(raw)) !== null) {
        const lang = (match[1] || '').toLowerCase();
        const content = (match[2] || '').trim();
        if (!content) continue;
        if (lang.includes('html')) blocks.html = content;
        else if (lang.includes('css')) blocks.css = content;
        else if (lang.includes('js') || lang.includes('javascript') || lang.includes('ts')) blocks.js = content;
      }

      if (!blocks.html || !blocks.css || !blocks.js) {
        // Попробуем альтернативный формат: строки HTML:, CSS:, JS:
        const simpleRegex = /(HTML|CSS|JS)\s*[:=]\s*([\s\S]*?)(?=(HTML|CSS|JS)\s*[:=]|$)/gi;
        let m;
        while ((m = simpleRegex.exec(raw)) !== null) {
          const key = m[1].toLowerCase();
          const content = (m[2] || '').trim();
          if (key === 'html') blocks.html = blocks.html || content;
          if (key === 'css') blocks.css = blocks.css || content;
          if (key === 'js') blocks.js = blocks.js || content;
        }
      }

      return blocks;
    },

    clearResponse() {
      if (this.elements.response.raw) this.elements.response.raw.value = '';
      if (this.elements.response.html) this.elements.response.html.value = '';
      if (this.elements.response.css) this.elements.response.css.value = '';
      if (this.elements.response.js) this.elements.response.js.value = '';
    },

    applyResponse() {
      if (!this.elements.form) {
        alert('Форма не найдена.');
        return;
      }

      if (!this.ensureHtmlMode()) {
        alert('Чтобы вставить код, переключите тип виджета на HTML.');
        return;
      }

      const html = this.elements.response.html?.value || '';
      const css = this.elements.response.css?.value || '';
      const js = this.elements.response.js?.value || '';

      if (!html.trim() && !css.trim() && !js.trim()) {
        alert('Нет распарсенного кода для вставки.');
        return;
      }

      if (this.elements.htmlTextarea) this.elements.htmlTextarea.value = html;
      if (this.elements.cssTextarea) this.elements.cssTextarea.value = css;
      if (this.elements.jsTextarea) this.elements.jsTextarea.value = js;

      if (this.elements.hiddenInputs.serviceId && this.state.activeService) {
        this.elements.hiddenInputs.serviceId.value = this.state.activeService.id;
      }

      if (this.elements.hiddenInputs.promptUsed) {
        const payload = {
          ...this.state.prompt,
          service_alias: this.state.activeService?.alias,
        };
        this.elements.hiddenInputs.promptUsed.value = JSON.stringify(payload);
      }

      if (this.elements.hiddenInputs.versionComment) {
        const customComment = this.elements.versionComment?.value?.trim();
        this.elements.hiddenInputs.versionComment.value = customComment || `Авто генерация через ${this.state.activeService?.name || 'ИИ'}`;
      }

      if (this.elements.versionComment) {
        this.elements.versionComment.classList.add('is-valid');
        setTimeout(() => this.elements.versionComment?.classList.remove('is-valid'), 2000);
      }

      this.elements.applyButton?.classList.add('btn-success');
      this.elements.applyButton?.classList.remove('btn-outline-success');
      this.elements.applyButton && (this.elements.applyButton.innerHTML = '<i class="bi bi-check-circle"></i> Вставлено');

      setTimeout(() => {
        if (this.elements.applyButton) {
          this.elements.applyButton.innerHTML = '<i class="bi bi-download"></i> Вставить в форму';
        }
      }, 2500);
    },

    ensureHtmlMode() {
      if (!this.elements.widgetTypeSelect) return true;
      if (this.elements.widgetTypeSelect.value !== 'html') {
        this.elements.widgetTypeSelect.value = 'html';
        if (typeof window.toggleWidgetType === 'function') {
          window.toggleWidgetType();
        }
      }
      return this.elements.widgetTypeSelect.value === 'html';
    },

    bindRefineActions() {
      const { feedback, generateButton, result } = this.elements.refine;
      if (!generateButton) return;
      generateButton.addEventListener('click', async () => {
        if (!this.state.activeService) {
          alert('Выберите сервис ИИ.');
          return;
        }
        const feedbackText = feedback?.value?.trim();
        if (!feedbackText) {
          alert('Опишите, что нужно уточнить.');
          return;
        }

        if (!this.config.widgetId) {
          alert('Сохраните виджет, чтобы использовать уточнение.');
          return;
        }

        try {
          const url = apiUrl(`/api/channels/${this.config.channelId}/widgets/${this.config.widgetId}/prompt/refine`);
          const response = await fetch(url, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
              service_alias: this.state.activeService.alias,
              original_prompt: this.elements.prompt.common?.value || '',
              previous_response: this.elements.response.raw?.value || '',
              feedback: feedbackText,
            }),
          });
          if (!response.ok) throw new Error('Не удалось построить уточняющий промпт');
          const data = await response.json();
          if (result) {
            result.value = data.prompt;
            result.scrollIntoView({ behavior: 'smooth', block: 'center' });
          }
        } catch (error) {
          alert(error.message);
        }
      });
    },

    async loadVersions() {
      if (!this.config.widgetId || !this.elements.versions.container) return;
      try {
        const url = apiUrl(`/api/channels/${this.config.channelId}/widgets/${this.config.widgetId}/versions`);
        const response = await fetch(url);
        if (!response.ok) throw new Error('Не удалось загрузить историю версий');
        const versions = await response.json();
        this.renderVersions(versions);
      } catch (error) {
        console.error(error);
        if (this.elements.versions.container) {
          this.elements.versions.container.innerHTML = `<div class="text-danger small">${error.message}</div>`;
        }
      }
    },

    renderVersions(versions) {
      if (!this.elements.versions.container) return;
      if (!versions.length) {
        if (this.elements.versions.container)
          this.elements.versions.container.innerHTML = '<div class="text-muted small">История версий пока пуста.</div>';
        return;
      }

      const list = document.createElement('div');
      list.className = 'list-group';
      versions.forEach((version) => {
        const item = document.createElement('div');
        item.className = 'list-group-item d-flex justify-content-between align-items-start';
        item.dataset.versionId = version.id;
        item.innerHTML = `
          <div>
            <div class="fw-semibold">Версия #${version.id} · ${new Date(version.created_at).toLocaleString()}</div>
            <div class="small text-muted">${version.comment || 'Комментарий отсутствует'}</div>
          </div>
          <div class="btn-group btn-group-sm">
            <button type="button" class="btn btn-outline-secondary" data-action="preview" data-version-id="${version.id}">
              <i class="bi bi-eye"></i>
            </button>
            <button type="button" class="btn btn-outline-danger" data-action="restore" data-version-id="${version.id}">
              <i class="bi bi-arrow-counterclockwise"></i>
            </button>
          </div>
        `;
        list.appendChild(item);
      });

      this.elements.versions.container.innerHTML = '';
      this.elements.versions.container.appendChild(list);
    },

    bindVersionActions() {
      if (!this.elements.versions.container) return;
      this.elements.versions.container.addEventListener('click', async (event) => {
        const button = event.target.closest('button[data-action]');
        if (!button) return;
        const versionId = button.dataset.versionId;
        if (!versionId) return;

        if (button.dataset.action === 'restore') {
          const confirmed = confirm('Откатить виджет к выбранной версии?');
          if (!confirmed) return;
          await this.restoreVersion(versionId);
        } else if (button.dataset.action === 'preview') {
          await this.previewVersion(versionId);
        }
      });
    },

    async restoreVersion(versionId) {
      try {
        const url = apiUrl(`/api/channels/${this.config.channelId}/widgets/${this.config.widgetId}/versions/${versionId}/restore`);
        const response = await fetch(url, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ comment: `Откат через UI (${versionId})` }),
        });
        if (!response.ok) throw new Error('Не удалось откатить версию');
        const widget = await response.json();
        if (this.elements.htmlTextarea) this.elements.htmlTextarea.value = widget.html_code || '';
        if (this.elements.cssTextarea) this.elements.cssTextarea.value = widget.css_code || '';
        if (this.elements.jsTextarea) this.elements.jsTextarea.value = widget.js_code || '';
        if (this.elements.widgetTypeSelect) this.elements.widgetTypeSelect.value = 'html';
        if (typeof window.toggleWidgetType === 'function') window.toggleWidgetType();
        this.loadVersions();
        alert('Виджет откатан к выбранной версии.');
      } catch (error) {
        alert(error.message);
      }
    },

    async previewVersion(versionId) {
      try {
        const url = apiUrl(`/api/channels/${this.config.channelId}/widgets/${this.config.widgetId}/versions/${versionId}`);
        const response = await fetch(url);
        if (!response.ok) throw new Error('Не удалось загрузить версию');
        const version = await response.json();
        this.openPreviewModal(version);
      } catch (error) {
        alert(error.message);
      }
    },

    openPreviewModal(version) {
      const modal = document.getElementById('versionPreviewModal');
      if (!modal) {
        alert('Модальное окно предпросмотра не найдено.');
        return;
      }
      if (typeof bootstrap === 'undefined' || !bootstrap.Modal) {
        alert('Библиотека Bootstrap недоступна для открытия модального окна.');
        return;
      }
      modal.querySelector('[data-preview-html]').textContent = version.html_code || '';
      modal.querySelector('[data-preview-css]').textContent = version.css_code || '';
      modal.querySelector('[data-preview-js]').textContent = version.js_code || '';
      modal.querySelector('[data-preview-meta]').textContent = `Версия #${version.id} · ${new Date(version.created_at).toLocaleString()} · ${version.comment || 'Без комментария'}`;
      const bootstrapModal = new bootstrap.Modal(modal);
      bootstrapModal.show();
    },
  };

  window.AIWidgetManager = AIWidgetManager;
})();

