import { NextResponse } from 'next/server'

/**
 * Identity endpoint - confirms this is the Second Brain app.
 * Used to detect if wrong server is running on port 3000.
 */
export async function GET() {
  return NextResponse.json({
    app: 'second-brain-dashboard',
    version: '0.1.0',
    timestamp: new Date().toISOString(),
  })
}
