const HF_BACKEND = 'https://apextrade-core-trade-ai-backend.hf.space';

module.exports = async (req, res) => {
  // Set CORS headers
  res.setHeader('Access-Control-Allow-Origin', '*');
  res.setHeader('Access-Control-Allow-Methods', 'GET,POST,PUT,DELETE,OPTIONS');
  res.setHeader('Access-Control-Allow-Headers', 'Content-Type, Authorization, X-CSRF-Token, X-Requested-With');
  res.setHeader('Access-Control-Max-Age', '86400');

  // Handle preflight
  if (req.method === 'OPTIONS') {
    return res.status(200).end();
  }

  // Build target URL
  const slug = req.query.slug ? req.query.slug.join('/') : '';
  const targetUrl = `${HF_BACKEND}/api/${slug}`;
  
  // Forward query parameters
  const queryString = new URLSearchParams(req.query).toString()
    .replace('slug=', '') // Remove slug param
    .replace(/&$/, '');
  const finalUrl = queryString ? `${targetUrl}?${queryString}` : targetUrl;

  try {
    // Prepare headers to forward
    const forwardHeaders = { ...req.headers };
    delete forwardHeaders.host;
    delete forwardHeaders['content-length'];
    delete forwardHeaders['transfer-encoding'];
    delete forwardHeaders['connection'];

    // Fetch from HF backend
    const response = await fetch(finalUrl, {
      method: req.method,
      headers: forwardHeaders,
      body: ['GET', 'HEAD'].includes(req.method) ? undefined : JSON.stringify(req.body),
    });

    // Copy response headers
    response.headers.forEach((value, key) => {
      if (!['content-encoding', 'transfer-encoding'].includes(key.toLowerCase())) {
        res.setHeader(key, value);
      }
    });

    // Ensure CORS on proxied response
    res.setHeader('Access-Control-Allow-Origin', '*');
    
    // Send response
    const data = await response.arrayBuffer();
    res.status(response.status).send(Buffer.from(data));
  } catch (error) {
    console.error('Proxy error:', error);
    res.status(502).json({ error: 'Bad Gateway', message: error.message });
  }
};