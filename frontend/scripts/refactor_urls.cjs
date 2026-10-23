const fs = require('fs');
const path = require('path');

const srcDir = 'c:/Users/aryan/OneDrive/Desktop/trade ai app/frontend/src';

// Create api.js
const apiJsContent = `let base = import.meta.env.VITE_API_URL || "";
if (base && !base.startsWith("http")) {
  base = "https://" + base;
}
if (base.endsWith("/")) {
  base = base.slice(0, -1);
}
export const API_BASE_URL = base;
`;
fs.writeFileSync(path.join(srcDir, 'api.js'), apiJsContent);

// Files to update
const files = [
  'AccountPanel.jsx',
  'App.jsx',
  'HomePanel.jsx',
  'IntroSplash.jsx',
  'JournalPanel.jsx',
  'LoginScreen.jsx',
  'PerformancePanel.jsx',
  'PredictionsPanel.jsx',
  'ScannerPanel.jsx',
  'SignalsPanel.jsx',
  'hooks/useMarketData.js'
];

for (const file of files) {
  const filePath = path.join(srcDir, file);
  if (!fs.existsSync(filePath)) continue;
  
  let content = fs.readFileSync(filePath, 'utf8');
  
  // Add import if not present
  const importPath = file.includes('/') ? '../api' : './api';
  if (!content.includes('import { API_BASE_URL }')) {
    content = `import { API_BASE_URL } from '${importPath}';\n` + content;
  }
  
  // Replace all variations of the fallback
  content = content.replace(/import\.meta\.env\.VITE_API_URL\s*\|\|\s*['"]https?:\/\/[^'"]+['"]/g, 'API_BASE_URL');
  
  fs.writeFileSync(filePath, content);
  console.log('Updated ' + file);
}
