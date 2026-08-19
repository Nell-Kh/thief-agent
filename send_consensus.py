"""Send yamanagh's Section-10 'series_consensus' envelope; retry until accepted (max ~3 min)."""
import json, sys, time
sys.path.insert(0, "src")
from police_thief.infra.http_transport import McpHttpTransport
url, result_path, sender = sys.argv[1], sys.argv[2], (sys.argv[3] if len(sys.argv) > 3 else "thief")
r = json.load(open(result_path, encoding="utf-8"))
env = {"sender": sender, "records": [], "result_claim": "series_consensus",
       "consensus_sha": r["mutual_agreement"]["sha256"]}
print("sending:", json.dumps(env))
deadline = time.time() + 180
attempt = 0
while True:
    attempt += 1
    t = McpHttpTransport(url, timeout=30)
    try:
        print(f"attempt {attempt}: reply =", t.send("submit_audit", env)); break
    except Exception as e:
        print(f"attempt {attempt}: {type(e).__name__}: {str(e)[:120]}")
        if time.time() > deadline: print("gave up after 3 min"); break
        time.sleep(5)
    finally:
        try: t.close()
        except Exception: pass
