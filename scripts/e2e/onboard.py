"""Onboard a fresh HA instance and set up Plant Manager. Prints an access token."""

import json, os, sys, time, urllib.parse, urllib.request

BASE = os.environ.get("HA_URL", "http://localhost:8124")
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "out")
CLIENT = BASE + "/"


def req(method, path, data=None, token=None, form=False):
    body = None
    headers = {}
    if data is not None:
        if form:
            body = urllib.parse.urlencode(data).encode()
            headers["Content-Type"] = "application/x-www-form-urlencoded"
        else:
            body = json.dumps(data).encode()
            headers["Content-Type"] = "application/json"
    if token:
        headers["Authorization"] = f"Bearer {token}"
    r = urllib.request.Request(BASE + path, data=body, headers=headers, method=method)
    with urllib.request.urlopen(r, timeout=30) as resp:
        text = resp.read().decode()
        return json.loads(text) if text else None


for _ in range(120):
    try:
        req("GET", "/api/onboarding")
        break
    except Exception:
        time.sleep(2)

steps = req("GET", "/api/onboarding")
if not next(s for s in steps if s["step"] == "user")["done"]:
    code = req(
        "POST",
        "/api/onboarding/users",
        {
            "client_id": CLIENT,
            "name": "Test",
            "username": "test",
            "password": "test1234",
            "language": "en",
        },
    )["auth_code"]
else:
    print("already onboarded", file=sys.stderr)
    sys.exit(1)
tokens = req(
    "POST",
    "/auth/token",
    {"grant_type": "authorization_code", "code": code, "client_id": CLIENT},
    form=True,
)
token = tokens["access_token"]
req("POST", "/api/onboarding/core_config", {}, token)
req("POST", "/api/onboarding/analytics", {}, token)
req(
    "POST",
    "/api/onboarding/integration",
    {"client_id": CLIENT, "redirect_uri": CLIENT + "?auth_callback=1"},
    token,
)

flow = req("POST", "/api/config/config_entries/flow", {"handler": "plant_manager"}, token)
result = req("POST", f"/api/config/config_entries/flow/{flow['flow_id']}", {}, token)
print("flow:", result["type"], file=sys.stderr)
os.makedirs(OUT, exist_ok=True)
json.dump({"tokens": tokens}, open(os.path.join(OUT, "tokens.json"), "w"))
print(token)
