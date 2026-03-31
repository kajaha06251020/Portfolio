import { describe, it, expect } from "vitest";

/**
 * Accessibility utility tests
 * Ensures ARIA attributes and keyboard navigation work correctly.
 */

function getAriaLabel(element: { getAttribute: (name: string) => string | null }): string | null {
  return element.getAttribute("aria-label");
}

function isKeyboardNavigable(element: { tabIndex: number }): boolean {
  return element.tabIndex >= 0;
}

function getContrastRatio(fg: string, bg: string): number {
  const luminance = (hex: string): number => {
    const rgb = parseInt(hex.slice(1), 16);
    const r = ((rgb >> 16) & 0xff) / 255;
    const g = ((rgb >> 8) & 0xff) / 255;
    const b = (rgb & 0xff) / 255;
    const toLinear = (c: number) => (c <= 0.03928 ? c / 12.92 : ((c + 0.055) / 1.055) ** 2.4);
    return 0.2126 * toLinear(r) + 0.7152 * toLinear(g) + 0.0722 * toLinear(b);
  };
  const l1 = luminance(fg);
  const l2 = luminance(bg);
  const lighter = Math.max(l1, l2);
  const darker = Math.min(l1, l2);
  return (lighter + 0.05) / (darker + 0.05);
}

describe("accessibility utilities", () => {
  describe("getAriaLabel", () => {
    it("returns aria-label when present", () => {
      const el = { getAttribute: (name: string) => (name === "aria-label" ? "Close menu" : null) };
      expect(getAriaLabel(el)).toBe("Close menu");
    });

    it("returns null when aria-label is missing", () => {
      const el = { getAttribute: () => null };
      expect(getAriaLabel(el)).toBeNull();
    });
  });

  describe("isKeyboardNavigable", () => {
    it("returns true for tabIndex >= 0", () => {
      expect(isKeyboardNavigable({ tabIndex: 0 })).toBe(true);
      expect(isKeyboardNavigable({ tabIndex: 1 })).toBe(true);
    });

    it("returns false for tabIndex < 0", () => {
      expect(isKeyboardNavigable({ tabIndex: -1 })).toBe(false);
    });
  });

  describe("getContrastRatio", () => {
    it("returns 21:1 for black on white", () => {
      const ratio = getContrastRatio("#000000", "#ffffff");
      expect(ratio).toBeCloseTo(21, 0);
    });

    it("returns 1:1 for same colors", () => {
      const ratio = getContrastRatio("#336699", "#336699");
      expect(ratio).toBeCloseTo(1, 0);
    });

    it("meets WCAG AA for sufficient contrast", () => {
      const ratio = getContrastRatio("#1a1a2e", "#e0e0e0");
      expect(ratio).toBeGreaterThan(4.5);
    });
  });
});
