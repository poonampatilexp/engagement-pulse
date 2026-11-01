import { NextRequest, NextResponse } from 'next/server';

const DJANGO_URL = process.env.DJANGO_INTERNAL_URL || process.env.INTERNAL_API_URL || 'http://127.0.0.1:8000';

export async function POST(request: NextRequest) {
  try {
    const body = await request.json();
    const res = await fetch(`${DJANGO_URL}/api/auth/login/`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(body),
    });

    const data = await res.json();
    if (!res.ok) {
      return NextResponse.json(data, { status: res.status });
    }

    const { access, refresh, user } = data;
    const response = NextResponse.json({ access, user });

    // Store refresh token strictly in HttpOnly cookie
    response.cookies.set('refresh_token', refresh, {
      httpOnly: true,
      secure: process.env.NODE_ENV === 'production',
      sameSite: 'lax',
      path: '/api/auth/',
      maxAge: 7 * 24 * 60 * 60, // 7 days (matches backend lifetime)
    });

    return response;
  } catch (error) {
    return NextResponse.json(
      { detail: 'Internal authentication proxy error' },
      { status: 500 }
    );
  }
}

