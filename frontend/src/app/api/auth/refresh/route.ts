import { NextRequest, NextResponse } from 'next/server';

const DJANGO_URL = process.env.DJANGO_INTERNAL_URL || 'http://127.0.0.1:8000';

export async function POST(request: NextRequest) {
  try {
    // 1. Get refresh token from HttpOnly cookie or request body (for API / test clients)
    let refreshToken = request.cookies.get('refresh_token')?.value;

    if (!refreshToken) {
      try {
        const body = await request.json();
        refreshToken = body?.refresh;
      } catch {
        // Request body might be empty when called from browser with cookie
      }
    }

    if (!refreshToken) {
      return NextResponse.json(
        { detail: 'No refresh token provided' },
        { status: 401 }
      );
    }

    // 2. Forward to Django backend
    const res = await fetch(`${DJANGO_URL}/api/auth/refresh/`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ refresh: refreshToken }),
    });

    const data = await res.json();

    if (!res.ok) {
      // If refresh fails (e.g. token expired, blacklisted, or invalid), purge cookie
      const errorResponse = NextResponse.json(data, { status: res.status });
      errorResponse.cookies.set('refresh_token', '', {
        httpOnly: true,
        secure: process.env.NODE_ENV === 'production',
        sameSite: 'lax',
        path: '/api/auth/',
        maxAge: 0,
      });
      return errorResponse;
    }

    // 3. Return fresh access token
    return NextResponse.json(data);
  } catch (error) {
    return NextResponse.json(
      { detail: 'Failed to communicate with authentication service' },
      { status: 500 }
    );
  }
}

