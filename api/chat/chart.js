const HF_BACKEND = 'https://apextrade-core-trade-ai-backend.hf.space';
const https = require('https');

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
    const url = new URL(`${HF_BACKEND}/api/chat/chart`);
    const postData = JSON.stringify(req.body);
    const options = {
      hostname: url.hostname,
      path: url.pathname + url.search,
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Origin': 'https://trade-ai-beta.vercel.app',
        'Content-Length': Buffer.byteLength(postData),
      },
    };

    const response = await new Promise((resolve, reject) => {
      const hfReq = https.request(options, (hfRes) => {
        let data = '';
        hfRes.on('data', (chunk) => { data += chunk; });
        hfRes.on('end', () => resolve({ status: hfRes.statusCode, headers: hfRes.headers, data }));
      });
      hfReq.on('error', reject);
      hfReq.write(postData);
      hfReq.end();
    });

    Object.entries(response.headers).forEach(([key, value]) => {
      if (!['content-encoding', 'transfer-encoding'].includes(key.toLowerCase())) {
        res.setHeader(key, value);
      }
    });

    res.setHeader('Access-Control-Allow-Origin', '*');
    res.status(response.status).send(response.data);
  } catch (error) {
    console.error('Proxy error:', error);
    res.status(502).json({ error: 'Bad Gateway', message: error.message });
  }
};