import { NextResponse } from 'next/server';

export function GET() {
  return NextResponse.json({
    name: 'Already Here Field Network OS',
    short_name: 'AH Field OS',
    description: 'Already Here LLC field service command system',
    start_url: '/',
    display: 'standalone',
    background_color: '#050816',
    theme_color: '#050816',
    icons: [
      { src: '/icon.svg', sizes: 'any', type: 'image/svg+xml' }
    ]
  });
}
