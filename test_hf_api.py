import urllib.request
import json
import time

url = "https://apextrade-core-trade-ai-backend.hf.space/api/login"
data = {
    "username": "apex_head_quant",
    "password": os.getenv("ADMIN_PASSWORD") or "",

}
req = urllib.request.Request(
    url, 
    data=json.dumps(data).encode("utf-8"), 
    headers={"Content-Type": "application/json"},
    method="POST"
)

try:
    with urllib.request.urlopen(req) as response:
        print("LOGIN STATUS:", response.status)
        resp_data = json.loads(response.read().decode("utf-8"))
        print("LOGIN RESPONSE:", resp_data)
        
        session_token = resp_data.get("token")
        if session_token:
            print("\nFetching /api/prices...")
            prices_req = urllib.request.Request(
                "https://apextrade-core-trade-ai-backend.hf.space/api/prices",
                headers={"Cookie": f"apt_token={session_token}"}
            )
            with urllib.request.urlopen(prices_req) as prices_res:
                print("PRICES STATUS:", prices_res.status)
                prices_data = json.loads(prices_res.read().decode("utf-8"))
                print("PRICES DATA:", json.dumps(prices_data, indent=2)[:500] + "... (truncated)")
                
except Exception as e:
    print("ERROR:", e)
    if hasattr(e, "read"):
        print("ERROR DETAILS:", e.read().decode("utf-8"))
