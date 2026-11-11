const protectedMedia = (() => {
  const host = 'https://downloads.whitenoisechoir.com';
  const siteKey = '0x4AAAAAAF8gZh-xEgWUNBmX';
  const sessionUrl = host + '/session';
  let turnstileScript;
  let sessionRequest;
  let expiresAt = 0;

  function loadTurnstile() {
    if (window.turnstile) return Promise.resolve(window.turnstile);
    if (!turnstileScript) {
      turnstileScript = new Promise((resolve, reject) => {
        const script = document.createElement('script');
        script.src = 'https://challenges.cloudflare.com/turnstile/v0/api.js?render=explicit';
        script.async = true;
        const fail = () => {
          clearTimeout(timeout);
          script.remove();
          reject(Error('Không tải được xác minh Cloudflare. Vui lòng thử lại.'));
        };
        const timeout = setTimeout(fail, 15000);
        script.onload = () => {
          clearTimeout(timeout);
          if (window.turnstile) resolve(window.turnstile);
          else fail();
        };
        script.onerror = fail;
        document.head.append(script);
      }).catch(error => {
        turnstileScript = undefined;
        throw error;
      });
    }
    return turnstileScript;
  }

  function request(url, options) {
    return fetch(url, {credentials: 'include', ...options});
  }

  async function verifyBrowser() {
    const turnstile = await loadTurnstile();
    const container = document.getElementById('media-verification');
    let widget;
    let timeout;
    try {
      const token = await new Promise((resolve, reject) => {
        const failed = () => reject(Error('Xác minh chưa hoàn tất. Vui lòng thử lại.'));
        timeout = setTimeout(failed, 120000);
        widget = turnstile.render(container, {
          sitekey: siteKey,
          action: 'media_access',
          appearance: 'interaction-only',
          retry: 'never',
          callback: resolve,
          'error-callback': failed,
          'expired-callback': failed,
          'timeout-callback': failed,
        });
      });
      const response = await request(sessionUrl, {
        method: 'POST',
        body: token,
        signal: AbortSignal.timeout(12000),
      });
      if (!response.ok) throw Error('Không xác minh được quyền tải. Vui lòng thử lại.');
      return response.json();
    } finally {
      clearTimeout(timeout);
      if (widget !== undefined) turnstile.remove(widget);
    }
  }

  async function openSession() {
    let response;
    try {
      response = await request(sessionUrl, {signal: AbortSignal.timeout(12000)});
    } catch {
      throw Error('Không kết nối được với kho âm thanh. Vui lòng thử lại.');
    }
    if (!response.ok && response.status !== 401) {
      throw Error('Kho âm thanh đang tạm thời không sẵn sàng. Vui lòng thử lại.');
    }
    const session = response.ok ? await response.json() : await verifyBrowser();
    expiresAt = session.expiresAt * 1000;
    if (!Number.isFinite(expiresAt)) throw Error('Không nhận được phiên tải hợp lệ.');
  }

  async function ready() {
    if (expiresAt > Date.now() + 1000) return;
    if (!sessionRequest) {
      sessionRequest = openSession().finally(() => { sessionRequest = undefined; });
    }
    await sessionRequest;
  }

  function urlFor(key, name) {
    const url = new URL('/media/' + key.split('/').map(encodeURIComponent).join('/'), host);
    if (name !== undefined) url.searchParams.set('download', name);
    return url.href;
  }

  async function fetchRecording(key) {
    await ready();
    const url = urlFor(key);
    const options = {signal: AbortSignal.timeout(45000)};
    let response = await request(url, options);
    if (response.status === 401) {
      expiresAt = 0;
      await ready();
      response = await request(url, {signal: AbortSignal.timeout(45000)});
    }
    return response;
  }

  return {
    manages: key => typeof key === 'string' && key.startsWith('asset-library/'),
    ready,
    urlFor,
    fetchRecording,
  };
})();
