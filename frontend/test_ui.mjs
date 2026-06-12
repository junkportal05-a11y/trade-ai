import puppeteer from 'puppeteer';

(async () => {
  try {
    const res = await fetch('http://127.0.0.1:8000/api/login', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ username: 'apex_head_quant', password: 'password123' })
    });
    const data = await res.json();
    console.log('Login response:', data);

    const browser = await puppeteer.launch({
      executablePath: 'C:\\Users\\aryan\\.cache\\puppeteer\\chrome\\win64-149.0.7827.115\\chrome-win64\\chrome.exe'
    });
    const page = await browser.newPage();
    page.on('console', msg => console.log('PAGE LOG:', msg.text()));
    await page.setViewport({width: 1280, height: 800});
    
    await page.goto('http://localhost:5173/');
    await page.evaluate((token, user) => {
      localStorage.setItem('apt_token', token);
      localStorage.setItem('is_logged_in', 'true');
      localStorage.setItem('apex_user', user);
      localStorage.setItem('last_morning_brief', new Date().toDateString());
    }, data.token, data.username);
    
    await page.reload();
    
    await new Promise(resolve => setTimeout(resolve, 5000));
    
    // Click the ACKNOWLEDGE button to dismiss the modal
    await page.evaluate(() => {
      const ackBtn = Array.from(document.querySelectorAll('button, div, span, a')).find(
        e => e.textContent.includes('ACKNOWLEDGE') || e.textContent.includes('Acknowledge')
      );
      if (ackBtn) {
        ackBtn.click();
        console.log("Clicked ACKNOWLEDGE button");
      } else {
        console.log("ACKNOWLEDGE button not found");
      }
    });

    await new Promise(resolve => setTimeout(resolve, 2000));

    // Click the CHART navigation tab
    await page.evaluate(() => {
      const el = Array.from(document.querySelectorAll('button')).find(
        e => e.textContent.includes('CHART') || e.textContent.includes('chart')
      );
      if (el) {
        el.click();
        console.log("Clicked CHART element:", el.tagName, el.textContent);
      } else {
        console.log("Could not find CHART element");
      }
    });

    // Wait for chart and historical data to render
    await new Promise(resolve => setTimeout(resolve, 8000));
    
    await page.screenshot({path: 'C:\\Users\\aryan\\.gemini\\antigravity\\brain\\05ec5ace-c85d-4380-8b8c-6b7aadd5ae1b\\chart_screenshot.png'});
    console.log('Screenshot saved to artifacts');
    await browser.close();
  } catch (err) {
    console.error(err);
  }
})();
