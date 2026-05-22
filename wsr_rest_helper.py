import json
import os
import sys
import urllib.request
import urllib.error

RUNTIME_JSON = os.path.expandvars(
    r"%LOCALAPPDATA%\Wall Street Raider\runtime.json"
)

def get_rest_port():
    with open(RUNTIME_JSON, "r", encoding="utf-8") as f:
        data = json.load(f)
    return data["rest_port"]

def do_request(method, path, headers=None, body=None):
    port = get_rest_port()
    url = f"http://127.0.0.1:{port}{path}"

    if body is not None and not isinstance(body, (bytes, bytearray)):
        body = json.dumps(body).encode("utf-8")
        headers = dict(headers or {})
        headers.setdefault("Content-Type", "application/json")

    req = urllib.request.Request(
        url=url,
        data=body,
        headers=headers or {},
        method=method,
    )

    try:
        with urllib.request.urlopen(req) as resp:
            resp_body = resp.read()
            content_type = resp.headers.get("Content-Type", "")
            try:
                if "application/json" in content_type:
                    parsed_body = json.loads(resp_body.decode("utf-8"))
                else:
                    parsed_body = resp_body.decode("utf-8", errors="replace")
            except Exception:
                parsed_body = resp_body.decode("utf-8", errors="replace")

            return {
                "ok": True,
                "status": resp.status,
                "headers": dict(resp.headers.items()),
                "body": parsed_body,
            }

    except urllib.error.HTTPError as e:
        resp_body = e.read()
        content_type = e.headers.get("Content-Type", "") if e.headers else ""
        try:
            if "application/json" in content_type:
                parsed_body = json.loads(resp_body.decode("utf-8"))
            else:
                parsed_body = resp_body.decode("utf-8", errors="replace")
        except Exception:
            parsed_body = resp_body.decode("utf-8", errors="replace")

        return {
            "ok": False,
            "status": e.code,
            "headers": dict(e.headers.items()) if e.headers else {},
            "body": parsed_body,
        }

    except Exception as e:
        return {
            "ok": False,
            "status": None,
            "headers": {},
            "body": str(e),
        }

def main():
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue

        try:
            msg = json.loads(line)
            method = msg.get("method", "GET").upper()
            path = msg["path"]
            headers = msg.get("headers")
            body = msg.get("json", msg.get("body"))

            result = do_request(method, path, headers=headers, body=body)
        except Exception as e:
            result = {
                "ok": False,
                "status": None,
                "headers": {},
                "body": str(e),
            }

        sys.stdout.write(json.dumps(result) + "\n")
        sys.stdout.flush()

if __name__ == "__main__":
    main()