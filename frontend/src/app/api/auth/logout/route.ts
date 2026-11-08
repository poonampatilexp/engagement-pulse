import { NextRequest, NextResponse } from 'next/server';

const DJANGO_URL = process.env.DJANGO_INTERNAL_URL || process.env.INTERNAL_API_URL || 'http://127.0.0.1:8000';

export async function POST(request: NextRequest) {
  try {
    let refreshToken = request.cookies.get('refresh_token')?.value;

    if (!refreshToken) {
      try {
        const body = await request.json();
        refreshToken = body?.refresh || body?.refresh_token;
      } catch {
        // Body may be empty on logout
      }
    }

    if (refreshToken) {
      const authHeader = request.headers.get('authorization');
      await fetch(`${DJANGO_URL}/api/auth/logout/`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          ...(authHeader ? { Authorization: authHeader } : {}),
        },
        body: JSON.stringify({ refresh: refreshToken, refresh_token: refreshToken }),
      });
    }
  } catch {
    // Ignore network errors communicating with backend logout
  }

  const response = NextResponse.json({ success: true });
  response.cookies.set('refresh_token', '', {
    httpOnly: true,
    secure: process.env.NODE_ENV === 'production',
    sameSite: 'lax',
    path: '/api/auth/',
    maxAge: 0,
  });
  return response;
}

