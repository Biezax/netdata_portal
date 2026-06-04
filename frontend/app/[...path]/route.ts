import { NextRequest, NextResponse } from 'next/server';
import { proxyToBackend, resolveAssetBackendPath } from '../lib/backendProxy';

export async function GET(
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
  const backendPath = resolveAssetBackendPath(request, pathParts);
  if (!backendPath) {
    return new NextResponse(null, { status: 404 });
  }

  return proxyToBackend(request, backendPath);
}
