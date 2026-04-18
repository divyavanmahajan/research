import type { PagesFunction } from '@cloudflare/workers-types';
import { scrapeUrl } from '../_shared/qasa';

function isQasaUrl(url: string): boolean {
  try {
    const parsed = new URL(url);
    return parsed.hostname === 'qasa.se' || parsed.hostname.endsWith('.qasa.se');
  } catch {
    return false;
  }
}

export const onRequestGet: PagesFunction = async (context) => {
  const { searchParams } = new URL(context.request.url);
  const url = searchParams.get('url');
  if (!url) return Response.json({ error: 'url query parameter is required' }, { status: 400 });
  if (!isQasaUrl(url)) return Response.json({ error: 'url must be a qasa.se URL' }, { status: 400 });
  try {
    const listing = await scrapeUrl(url);
    return Response.json(listing);
  } catch (err) {
    return Response.json({ error: (err as Error).message }, { status: 502 });
  }
};
