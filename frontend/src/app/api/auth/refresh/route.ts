import { NextRequest, NextResponse } from 'next/server';

const DJANGO_URL = process.env.DJANGO_INTERNAL_URL || process.env.INTERNAL_API_URL || 'http://127.0.0.1:8000';

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
      body: JSON.stringify({ refresh: refreshToken, refresh_token: refreshToken }),
    });

    let data: any = null;
    try {
      data = await res.json();
    } catch {
      data = { detail: res.statusText || 'Authentication service error' };
    }

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

    // 3. Return fresh access token and persist rotated refresh token
    const nextRefreshToken = data.refresh || data.refresh_token;
    const response = NextResponse.json({
      access: data.access || data.access_token,
      ...data,
    });

    if (nextRefreshToken) {
      response.cookies.set('refresh_token', nextRefreshToken, {
        httpOnly: true,
        secure: process.env.NODE_ENV === 'production',
        sameSite: 'lax',
        path: '/api/auth/',
        maxAge: 7 * 24 * 60 * 60,
      });
    }

    return response;
  } catch (error) {
    const errorResponse = NextResponse.json(
      { detail: 'Failed to communicate with authentication service' },
      { status: 500 }
    );
    errorResponse.cookies.set('refresh_token', '', {
      httpOnly: true,
      secure: process.env.NODE_ENV === 'production',
      sameSite: 'lax',
      path: '/api/auth/',
      maxAge: 0,
    });
    return errorResponse;
  }
}

