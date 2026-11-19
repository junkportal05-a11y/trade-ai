import subprocess, time, os
proc = subprocess.Popen(
    ['cmd', '/c', 'cd C:\\Users\\aryan\\OneDrive\\Desktop\\app\\projects\\trade.ai\\backend && python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 > server.log 2>&1'],
    cwd='C:\\Users\\aryan\\OneDrive\\Desktop\\app\\projects\\trade.ai\\backend'
)
print('Server PID:', proc.pid)
time.sleep(5)
if proc.poll() is None:
    print('Server is running in background')
else:
    print('Server exited')
    with open('server.log', 'r') as f:
        print(f.read())