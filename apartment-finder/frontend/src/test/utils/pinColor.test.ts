import { describe, it, expect } from 'vitest';
import { getTagColor } from '../../utils/pinColor';

describe('pinColor util', () => {
  it('returns green for interested', () => {
    expect(getTagColor('interested')).toBe('#22c55e');
  });

  it('returns amber for favourite', () => {
    expect(getTagColor('favourite')).toBe('#f59e0b');
  });

  it('returns blue for applied', () => {
    expect(getTagColor('applied')).toBe('#3b82f6');
  });

  it('returns purple for visited', () => {
    expect(getTagColor('visited')).toBe('#a855f7');
  });

  it('returns red for rejected', () => {
    expect(getTagColor('rejected')).toBe('#ef4444');
  });

  it('returns red for not interested', () => {
    expect(getTagColor('not interested')).toBe('#ef4444');
  });

  it('returns grey for unknown tags', () => {
    expect(getTagColor('random')).toBe('#6b7280');
  });

  it('returns grey for empty tag', () => {
    expect(getTagColor('')).toBe('#6b7280');
  });
});
