import os
files = [
    r'backend\signals.py',
    r'frontend\src\App.jsx',
    r'frontend\src\HomePanel.jsx',
    r'frontend\src\PerformancePanel.jsx',
    r'frontend\src\PredictionsPanel.jsx',
    r'frontend\src\SignalsPanel.jsx'
]
for f in files:
    with open(f, 'r', encoding='utf-8') as file:
        content = file.read()
    content = content.replace('BHARTIARTEL', 'BHARTIARTL')
    with open(f, 'w', encoding='utf-8') as file:
        file.write(content)
    print(f'Fixed {f}')
