/**
 * Accessibility utilities for Portfolio site.
 * Provides WCAG 2.1 AA compliance helpers.
 */

/**
 * Calculate the relative luminance of a hex color.
 * Based on WCAG 2.1 definition: https://www.w3.org/TR/WCAG21/#dfn-relative-luminance
 */
export function relativeLuminance(hex: string): number {
  const rgb = parseInt(hex.replace("#", ""), 16);
  const r = ((rgb >> 16) & 0xff) / 255;
  const g = ((rgb >> 8) & 0xff) / 255;
  const b = (rgb & 0xff) / 255;

  const toLinear = (c: number) =>
    c <= 0.03928 ? c / 12.92 : ((c + 0.055) / 1.055) ** 2.4;

  return 0.2126 * toLinear(r) + 0.7152 * toLinear(g) + 0.0722 * toLinear(b);
}

/**
 * Calculate contrast ratio between two colors.
 * Returns a value between 1 and 21.
 * WCAG AA requires >= 4.5 for normal text, >= 3.0 for large text.
 */
export function contrastRatio(foreground: string, background: string): number {
  const l1 = relativeLuminance(foreground);
  const l2 = relativeLuminance(background);
  const lighter = Math.max(l1, l2);
  const darker = Math.min(l1, l2);
  return (lighter + 0.05) / (darker + 0.05);
}

/**
 * Check if a color pair meets WCAG AA contrast requirements.
 */
export function meetsContrastAA(
  foreground: string,
  background: string,
  isLargeText = false,
): boolean {
  const ratio = contrastRatio(foreground, background);
  return isLargeText ? ratio >= 3.0 : ratio >= 4.5;
}

/**
 * Generate a skip-to-content link for keyboard navigation.
 * Should be the first focusable element on the page.
 */
export function createSkipLink(targetId: string): string {
  return `<a href="#${targetId}" class="sr-only focus:not-sr-only focus:absolute focus:top-4 focus:left-4 focus:z-50 focus:px-4 focus:py-2 focus:bg-white focus:text-black focus:rounded">Skip to content</a>`;
}
