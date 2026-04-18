import { describe, it, expect } from 'vitest';
import { extractHomeId } from '../../utils/urlParser';

describe('urlParser util', () => {
  it('extracts ID from valid qasa.com URL', () => {
    const url = 'https://qasa.com/se/en/home/1348599';
    expect(extractHomeId(url)).toBe('1348599');
  });

  it('extracts ID from valid qasa.se URL', () => {
    const url = 'https://qasa.se/home/1348599';
    expect(extractHomeId(url)).toBe('1348599');
  });

  it('extracts ID from URL with www', () => {
    const url = 'https://www.qasa.com/se/en/home/1348599';
    expect(extractHomeId(url)).toBe('1348599');
  });

  it('extracts ID from URL with slug/trailing path', () => {
    const url = 'https://qasa.com/se/en/home/1348599/modern-apartment';
    expect(extractHomeId(url)).toBe('1348599');
  });

  it('returns null for invalid domain', () => {
    const url = 'https://example.com/home/1348599';
    expect(extractHomeId(url)).toBeNull();
  });

  it('returns null for URL missing numeric ID', () => {
    const url = 'https://qasa.com/se/en/home/abc';
    expect(extractHomeId(url)).toBeNull();
  });

  it('returns null for empty string', () => {
    expect(extractHomeId('')).toBeNull();
  });
});
