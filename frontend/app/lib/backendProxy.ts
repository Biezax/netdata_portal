import { NextRequest, NextResponse } from 'next/server';

const BACKEND_URL = process.env.BACKEND_URL || 'http://netdata-portal-backend:8000';
const BACKEND_API_PATHS = new Set(['hosts', 'alerts', 'proxy']);
const PROXY_HOST_COOKIE = 'netdata_proxy_host';
const LOCAL_ONLY_PATHS = new Set([
  '_next',
  'favicon.ico',
  'robots.txt',
  'manifest.json',
  'sitemap.xml',
  '__nextjs_original-stack-frame',
]);

export async function proxyToBackend(request: NextRequest, backendPath: string) {
  const searchParams = request.nextUrl.searchParams.toString();
  const targetUrl = `${BACKEND_URL}/api/${backendPath}${searchParams ? `?${searchParams}` : ''}`;

  try {
    const headers: Record<string, string> = {
      Accept: request.headers.get('accept') || '*/*',
      'User-Agent': 'Netdata-Aggregator-Frontend/1.0',
    };

    const contentType = request.headers.get('content-type');
    if (contentType) {
      headers['Content-Type'] = contentType;
    }

    const options: RequestInit = {
      method: request.method,
      headers,
      redirect: 'manual',
    };

    if (request.method !== 'GET' && request.method !== 'HEAD') {
      options.body = await request.text();
    }

    const response = await fetch(targetUrl, options);
    const responseHeaders = new Headers();
    response.headers.forEach((value, key) => {
      if (!['content-encoding', 'content-length', 'transfer-encoding'].includes(key.toLowerCase())) {
        responseHeaders.set(key, value);
      }
    });

    const proxyHost = getProxyHostFromBackendPath(backendPath);
    if (proxyHost && shouldPersistProxyHost(request, backendPath, response)) {
      responseHeaders.append(
        'Set-Cookie',
        `${PROXY_HOST_COOKIE}=${encodeURIComponent(proxyHost)}; Path=/; SameSite=Lax; HttpOnly`
      );
    }

    return new NextResponse(request.method === 'HEAD' ? null : response.body, {
      status: response.status,
      statusText: response.statusText,
      headers: responseHeaders,
    });
  } catch (error) {
    console.error('[Proxy] Error:', error);
    return NextResponse.json(
      { error: 'Failed to proxy request', details: String(error) },
      { status: 502 }
    );
  }
}

export function resolveApiBackendPath(request: NextRequest, pathParts: string[]) {
  const firstPart = pathParts[0];
  const path = joinPathParts(request, pathParts);

  if (BACKEND_API_PATHS.has(firstPart)) {
    return path;
  }

  const host = getProxyHostFromReferer(request) || getProxyHostFromCookie(request);
  return host ? `proxy/${encodeURIComponent(host)}/api/${path}` : path;
}

export function resolveAssetBackendPath(request: NextRequest, pathParts: string[]) {
  if (shouldSkipAssetProxy(request, pathParts)) {
    return null;
  }

  const host = getProxyHostFromReferer(request) || getProxyHostFromCookie(request);
  return host ? `proxy/${encodeURIComponent(host)}/${joinPathParts(request, pathParts)}` : null;
}

function getProxyHostFromReferer(request: NextRequest) {
  const referer = request.headers.get('referer');
  if (!referer) {
    return null;
  }

  try {
    const refererPath = new URL(referer).pathname;
    const match = refererPath.match(/^\/api\/proxy\/([^/]+)\//);
    return match ? decodeURIComponent(match[1]) : null;
  } catch {
    return null;
  }
}

function getProxyHostFromCookie(request: NextRequest) {
  const value = request.cookies.get(PROXY_HOST_COOKIE)?.value;
  if (!value) {
    return null;
  }

  try {
    return decodeURIComponent(value);
  } catch {
    return null;
  }
}

function getProxyHostFromBackendPath(backendPath: string) {
  const match = backendPath.match(/^proxy\/([^/]+)(?:\/|$)/);
  return match ? decodeURIComponent(match[1]) : null;
}

function shouldSkipAssetProxy(request: NextRequest, pathParts: string[]) {
  const firstPart = pathParts[0];
  if (!firstPart || LOCAL_ONLY_PATHS.has(firstPart)) {
    return true;
  }

  if (request.headers.get('rsc') === '1' || request.headers.has('next-router-prefetch')) {
    return true;
  }

  const accept = request.headers.get('accept') || '';
  return request.headers.get('sec-fetch-mode') === 'navigate' || accept.includes('text/html');
}

function shouldPersistProxyHost(request: NextRequest, backendPath: string, response: Response) {
  if (request.method !== 'GET' && request.method !== 'HEAD') {
    return false;
  }

  const dashboardPath = /^proxy\/[^/]+\/v3\/?$/.test(backendPath);
  const acceptsHtml = (request.headers.get('accept') || '').includes('text/html');
  const returnsHtml = (response.headers.get('content-type') || '').includes('text/html');
  return dashboardPath && (acceptsHtml || returnsHtml);
}

function joinPathParts(request: NextRequest, pathParts: string[]) {
  const path = pathParts.join('/');
  return request.nextUrl.pathname.endsWith('/') && path ? `${path}/` : path;
}
