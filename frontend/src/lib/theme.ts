import * as React from "react";

const KEYS = ["ink", "ink-2", "muted", "rule", "rule-2", "paper", "paper-2", "cotton", "print", "board", "paid", "success", "error", "ig", "li", "x"] as const;
export type ThemeColors = Record<(typeof KEYS)[number], string>;

function read(): ThemeColors {
  const cs = getComputedStyle(document.documentElement);
  return Object.fromEntries(KEYS.map((k) => [k, cs.getPropertyValue(`--color-${k}`).trim()])) as ThemeColors;
}

/* SVG chart attributes can't resolve CSS variables reliably, so charts read the resolved
   token values and re-render when the theme changes. */
export function useThemeColors(): ThemeColors {
  const [c, setC] = React.useState<ThemeColors>(read);
  React.useEffect(() => {
    const update = () => setC(read());
    const mo = new MutationObserver(update);
    mo.observe(document.documentElement, { attributes: true, attributeFilter: ["data-theme"] });
    const mq = window.matchMedia("(prefers-color-scheme: light)");
    mq.addEventListener("change", update);
    return () => { mo.disconnect(); mq.removeEventListener("change", update); };
  }, []);
  return c;
}

export const platformColor = (c: ThemeColors, p: string) => (p === "instagram" ? c.ig : p === "linkedin" ? c.li : c.x);
