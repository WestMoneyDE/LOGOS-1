import type { Page } from "@playwright/test";

// §59 no page-level horizontal overflow; §60 no clipped key content (text-bearing elements outside their container),
// exceptions: explicitly scrollable containers, graph canvases, intentional line-clamp/ellipsis.
export async function pageOverflow(page: Page): Promise<{ scrollWidth: number; innerWidth: number; overflow: boolean }> {
  return page.evaluate(() => {
    const sw = document.documentElement.scrollWidth, iw = window.innerWidth;
    return { scrollWidth: sw, innerWidth: iw, overflow: sw > iw + 2 };
  });
}

export async function clippedElements(page: Page): Promise<string[]> {
  return page.evaluate(() => {
    const out: string[] = [];
    const scrollable = (el: Element) => { const s = getComputedStyle(el); return /(auto|scroll)/.test(s.overflowX + s.overflowY); };
    const intentional = (el: Element) => { const s = getComputedStyle(el); return s.textOverflow === "ellipsis" || (s as any).webkitLineClamp !== "none" || el.tagName === "SVG" || el.closest("svg") !== null || el.tagName === "PRE" || el.closest("pre") !== null; };
    document.querySelectorAll("h1,h2,h3,p,td,th,dd,dt,li,code,span").forEach((el) => {
      if (!(el as HTMLElement).innerText?.trim()) return;
      if (intentional(el)) return;
      let p: Element | null = el.parentElement; let clippedBy: Element | null = null;
      while (p && p !== document.body) {
        const s = getComputedStyle(p);
        if (s.overflowX === "hidden" || s.overflowY === "hidden") { clippedBy = p; break; }
        if (scrollable(p)) return;           // explicitly scrollable container — allowed
        p = p.parentElement;
      }
      if (!clippedBy) return;
      const r = el.getBoundingClientRect(), c = clippedBy.getBoundingClientRect();
      if (r.right > c.right + 1 || r.bottom > c.bottom + 1 || r.left < c.left - 1) out.push(`${el.tagName.toLowerCase()}: "${(el as HTMLElement).innerText.slice(0, 40)}" clipped by ${clippedBy.tagName.toLowerCase()}.${(clippedBy as HTMLElement).className.toString().slice(0, 40)}`);
    });
    return out.slice(0, 20);
  });
}
