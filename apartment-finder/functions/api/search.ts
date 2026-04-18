import type { PagesFunction } from '@cloudflare/workers-types';
import { scrapeSearch, type SearchParams } from '../_shared/qasa';

export const onRequestGet: PagesFunction = async (context) => {
  const { searchParams } = new URL(context.request.url);

  const params: SearchParams = {
    city: searchParams.get('city') ?? undefined,
    minPrice: searchParams.get('minPrice') ?? undefined,
    maxPrice: searchParams.get('maxPrice') ?? undefined,
    minSize: searchParams.get('minSize') ?? undefined,
    maxSize: searchParams.get('maxSize') ?? undefined,
    rooms: searchParams.get('rooms') ?? undefined,
  };

  try {
    const results = await scrapeSearch(params);
    return Response.json({ results });
  } catch (err) {
    return Response.json({ error: (err as Error).message }, { status: 502 });
  }
};
