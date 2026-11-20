const HF_BACKEND = 'https://apextrade-core-trade-ai-backend.hf.space';

module.exports = async (req, res) => {
  res.setHeader('Access-Control-Allow-Origin', '*');
  res.setHeader('Access-Control-Allow-Methods', 'GET,POST,PUT,DELETE,OPTIONS');
  res.setHeader('Access-Control-Allow-Headers', 'Content-Type, Authorization, X-CSRF-Token, X-Requested-With');
  res.setHeader('Access-Control-Max-Age', '86400');

  if (req.method === 'OPTIONS') {
    return res.status(200).end();
  }

  if (req.method !== 'POST') {
    return res.status(405).json({ error: 'Method Not Allowed' });
  }

  try {
    const response = await fetch(`${HF_BACKEND}/api/chat/chart`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Origin': 'https://trade-ai-beta.vercel.app',
      },
      body: JSON.stringify(req.body),
    });

    response.headers.forEach((value, key) => {
      if (!['content-encoding', 'transfer-encoding'].includes(key.toLowerCase())) {
        res.setHeader(key, value);
      }
    });

    res.setHeader('Access-Control-Allow-Origin', '*');
    const data = await response.arrayBuffer();
    res.status(response.status).send(Buffer.from(data));
  } catch (error) {
    console.error('Proxy error:', error);
    res.status(502).json({ error: 'Bad Gateway', message: error.message });
  }
};