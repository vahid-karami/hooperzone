import { describe, it, expect } from 'vitest';
import { readFileSync } from 'node:fs';
import { resolve } from 'node:path';

// Read from disk: vitest replaces imported CSS with an empty module.
const css = readFileSync(resolve(process.cwd(), 'src/styles/design-tokens.css'), 'utf8');

describe('page fade (.route-view)', () => {
  // Every page is rendered inside .route-view. If its animation keeps a transform after it
  // ends (fill-mode forwards/both), position: fixed children are placed against the page
  // instead of the screen: the size guide opened far down the page on phones and the sticky
  // buy bar sat at the very end of it.
  it('does not keep a transform after the animation ends', () => {
    const rule = css.match(/\.route-view\s*\{([^}]*)\}/)[1];
    expect(rule).toMatch(/animation:/);
    expect(rule).not.toMatch(/\b(both|forwards)\b/);
    expect(rule).not.toMatch(/transform|filter|will-change|contain|perspective/);
  });
});
