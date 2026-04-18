const express = require('express');
const cors = require('cors');
const { scrapeUrl, scrapeSearch } = require('./scrapers/qasa');

const app = express();
const PORT = process.env.PORT || 3001;

app.use(cors({ origin: 'http://localhost:5173' }));
app.use(express.json());

function isQasaUrl(url) {
  try {
    const parsed = new URL(url);
    return parsed.hostname === 'qasa.se' || parsed.hostname.endsWith('.qasa.se');
  } catch {
    return false;
  }
}

app.get('/api/health', (_req, res) => {
  res.json({ status: 'ok' });
});

app.get('/api/scrape', async (req, res) => {
  const { url } = req.query;
  if (!url) return res.status(400).json({ error: 'url query parameter is required' });
  if (!isQasaUrl(url)) return res.status(400).json({ error: 'url must be a qasa.se URL' });

  try {
    const listing = await scrapeUrl(url);
    res.json(listing);
  } catch (err) {
    res.status(502).json({ error: err.message });
  }
});

app.get('/api/search', async (req, res) => {
  const { city, minPrice, maxPrice, minSize, maxSize, rooms } = req.query;
  try {
    const results = await scrapeSearch({ city, minPrice, maxPrice, minSize, maxSize, rooms });
    res.json({ results });
  } catch (err) {
    res.status(502).json({ error: err.message });
  }
});

if (require.main === module) {
  app.listen(PORT, () => console.log(`Backend running on http://localhost:${PORT}`));
}

module.exports = app;
