import { NextRequest, NextResponse } from 'next/server';

const BACKEND_URL = process.env.BACKEND_URL || 'http://netdata-portal-backend:8000';

export async function GET(
  request: NextRequest,
  { params }: { params: Promise<{ path: string[] }> }
) {
  const { path } = await params;
  return proxyRequest(request, path);
}

export async function POST(
  request: NextRequest,
  { params }: { params: Promise<{ path: string[] }> }
) {
  const { path } = await params;
  return proxyRequest(request, path);
}

export async function HEAD(
  request: NextRequest,
  { params }: { params: Promise<{ path: string[] }> }
) {
  const { path } = await params;
  return proxyRequest(request, path);
}

async function proxyRequest(request: NextRequest, pathParts: string[]) {
  const path = pathParts.join('/');
  const searchParams = request.nextUrl.searchParams.toString();
  const targetUrl = `${BACKEND_URL}/api/${path}${searchParams ? `?${searchParams}` : ''}`;

  console.log('[Proxy] Backend URL:', BACKEND_URL);
  console.log('[Proxy] Target URL:', targetUrl);

  try {
    const headers: Record<string, string> = {
      'Accept': '*/*',
      'User-Agent': 'Netdata-Aggregator-Frontend/1.0',
    };

    const options: RequestInit = {
      method: request.method,
      headers,
    };

    if (request.method !== 'GET' && request.method !== 'HEAD') {
      options.body = await request.text();
    }

    const response = await fetch(targetUrl, options);
    const data = await response.arrayBuffer();

    const responseHeaders = new Headers();
    response.headers.forEach((value, key) => {
      if (!['content-encoding', 'content-length', 'transfer-encoding'].includes(key.toLowerCase())) {
        responseHeaders.set(key, value);
      }
    });

    return new NextResponse(data, {
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
