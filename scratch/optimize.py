import os
import re
import subprocess

file_path = 'backend/historical_simulator.py'

for score in [5, 6, 7, 8, 9]:
    print(f"\n=================================")
    print(f"RUNNING WITH MIN SCORE: {score}")
    print(f"=================================\n")
    
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
        
    content = re.sub(r"abs\(result\.get\('score', 0\)\) >= \d+", f"abs(result.get('score', 0)) >= {score}", content)
    
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(content)
        
    # We must also clean the __main__ block which I mangled earlier
    # Let's fix that
    with open(file_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()
        
    new_lines = []
    skip = False
    for line in lines:
        if 'for min_score in' in line:
            skip = True
        if skip and 'asyncio.run' in line:
            new_lines.append("        simulator = HistoricalSimulator()\n")
            new_lines.append("        asyncio.run(simulator.simulate(start, end, atr_multiplier=1.0, rr_target=2.0))\n")
            skip = False
            continue
        if not skip:
            new_lines.append(line)
            
    with open(file_path, 'w', encoding='utf-8') as f:
        f.writelines(new_lines)
        
    subprocess.run(["python", file_path, "--phase1"])
