const manual = '仍可手动保存此来源。';
const unavailable = `此版本未提供在线采集，或服务暂时不可用。${manual}`;

/** Collect notebook text only. The caller keeps its curated evidence on failure. */
export async function collectSource(url) {
  if (globalThis.location?.hostname?.endsWith('.github.io')) {
    throw new Error('GitHub Pages 版支持手动摘录。打开来源原文后，可将需要的内容保存到手记。');
  }
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), 20_000);
  let response, data;
  try {
    response = await fetch('/api/collect', {
      method: 'POST', headers: { 'Content-Type': 'application/json', Accept: 'application/json' },
      body: JSON.stringify({ url }), signal: controller.signal, redirect: 'error',
    });
    if (/^application\/json(?:\s*;|$)/i.test(response.headers.get('content-type') ?? '')) {
      data = await response.json();
    }
  } catch {
    if (controller.signal.aborted) throw new Error(`在线采集超时。${manual}`);
    throw new Error(`暂时无法连接在线采集服务。${manual}`);
  } finally { clearTimeout(timer); }
  if (!response.ok) {
    const message = data?.error?.message;
    // Static hosts can return their own JSON/HTML error pages.
    throw new Error(typeof message === 'string' && message.endsWith(manual) ? message : unavailable);
  }
  if (!data || ![data.title, data.excerpt, data.retrievedAt, data.url].every(v => typeof v === 'string' && v.trim()) ||
      !Number.isFinite(Date.parse(data.retrievedAt)) || !/^https:\/\//.test(data.url) || data.sourceUrl !== url) {
    throw new Error(unavailable);
  }
  const dates = [data.publishedAt && `发布日期：${data.publishedAt}`, data.updatedAt && `更新日期：${data.updatedAt}`];
  const excerpt = [data.excerpt, ...dates].filter(Boolean).join('\n');
  return { title: data.title, excerpt, retrievedAt: data.retrievedAt, url: data.url };
}
