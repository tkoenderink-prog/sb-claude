'use client'

import { useState, useEffect } from 'react'

/**
 * Hook for client-side date formatting that avoids hydration mismatches.
 * Returns empty string during SSR/initial render, then shows formatted date after hydration.
 */
export function useClientDate(
  dateInput: string | Date | undefined | null,
  formatFn: (date: Date) => string = (d) => d.toLocaleString()
): string {
  const [formatted, setFormatted] = useState<string>('')

  useEffect(() => {
    if (dateInput) {
      const date = typeof dateInput === 'string' ? new Date(dateInput) : dateInput
      setFormatted(formatFn(date))
    }
  }, [dateInput, formatFn])

  return formatted
}

/**
 * Format time only (e.g., "5:30:00 PM")
 */
export function useClientTime(dateInput: string | Date | undefined | null): string {
  return useClientDate(dateInput, (d) => d.toLocaleTimeString())
}

/**
 * Format date and time (e.g., "12/21/2025, 5:30:00 PM")
 */
export function useClientDateTime(dateInput: string | Date | undefined | null): string {
  return useClientDate(dateInput, (d) => d.toLocaleString())
}
