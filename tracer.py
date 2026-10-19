#!/usr/bin/env python3
"""Anon Creator Tracker: on-chain creator trace for anoncoin.it tokens (Solana Meteora DBC / Robinhood Chain Doppler).
python3 tracer.py <addr>... [--deep --all-claims] [--md-dir DIR] [--img DIR] [--json] [--no-funding] [--workdir DIR]
Stdlib only. Caches live in the work dir (default: this file's folder). Times are UTC."""
import argparse, base64, concurrent.futures as cf, datetime as dt, fcntl, gzip, hashlib, json, os, re, sys, tempfile, threading, time
import urllib.error, urllib.parse, urllib.request

SOL_RPC = os.environ.get("SOL_RPC", "https://api.mainnet-beta.solana.com")
RH_RPC = os.environ.get("RH_RPC", "https://rpc.mainnet.chain.robinhood.com")
BS = "https://robinhoodchain.blockscout.com"
API = "https://api.anoncoin.it/v1/feeds"
UA = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"
DBC = "dbcij3LWUppWqq96dh6gJWwBifmcGfLSB5D4DuSMaqN"
DAMM = "cpamdpZCGKUy5JxQXB4dcpGPiikHawvSWAd6mEn1sGG"
PARTNER = "BKPxAdgwPHXE3ZPZt5XsAovDgUaUufHgZnSAZ3eRWQNW"
OPERATOR = "0x3412f1a0477af054a01ac44aec8a6a300c14bbf5"
ENTRY = "0x0000000071727de22e5e9d8baf0edac6f37da032"
FEE_C = "0x5f9eb5f6726fe88d5e39867967f5b833d2fa3215"
FEE_T = "0x0c90f8fcadd900399eb6c30bc91ec4531380b92bc2c4c364675528b1d30601e2"
AIRLOCK = "0xeb7c034704ef8dcd2d32324c1545f62fb4ad0862"
T_CREATE = "0x68ff1cfc"
T_USEROP = "0x49628fd1471006c1482da88028e9ce4dbb080b815c9b0344d39e5a8e6ec1419f"
T_BEFORE = "0xbb47ee3e183a558b1a2ff0874b079f3fc5478b7454eacf2bfc5af2ff5878f972"
EVM = re.compile(r"^0x[0-9a-fA-F]{40}$")
THRESH = 3  # auto-learn: a wallet seen across launches of >= 3 distinct creator accounts is platform infrastructure
# built-in platform list (chain|address|type|label); 'exchange'/'bridge' only label funding sources
_PW = """s|BVP3Um6aomdUkH1cRrVTHUJNCPbHrzYsyEwpHyHV5dn7|platform|anoncoin.it fee payer (2025)
s|7AbRGzM3NBvvUXi7j1Mga2SraTfjpPBMzGpyHcXSzV3v|platform|anoncoin.it fee payer (2026)
s|dbcij3LWUppWqq96dh6gJWwBifmcGfLSB5D4DuSMaqN|program|Meteora DBC program
s|6EF8rrecthR5Dkzon8Nwu78hRvfCKubJ14M5uBEwF6P|program|pump.fun bonding curve program
s|TSLvdd1pWpHVjahSpsvCXUbgwsL3JAcvokwaKt1eokM|platform|pump.fun mint authority
s|CebN5WGQ4jvEPvsVU4EoHEpgzq1VV7AbicfhtW4xC9iM|platform|pump.fun fee recipient
s|39azUYFWPz3VHgKCf3VChUwbpURdCHRxjWVowf5jUJjg|platform|pump.fun migration wallet
s|pAMMBay6oceH9fJKBRHGP5D4bD4sWpmSwMn52FMfXEA|program|PumpSwap AMM program
s|LanMV9sAd7wArD4vJFi2qDdfnVhFxYSUg6eADduJ3uj|program|Raydium LaunchLab program
s|5Q544fKrFoe6tsEbD7S8EmxGTJYAKtTVhAW5Q5pge4j1|program|Raydium AMM authority
s|11111111111111111111111111111111|program|System program
s|TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA|program|SPL Token program
s|TokenzQdBNbLqP5VEhdkAS6EPFLC1PHnBqCXEpPxuEb|program|SPL Token-2022 program
s|ComputeBudget111111111111111111111111111111|program|Compute Budget program
s|metaqbxxUerdq28cj1RbAWkYQm3ybzjb6a8bt518x1s|program|Metaplex Token Metadata program
s|ATokenGPvbdGVxr1b2hvZbsiqW5xWH25efTNsLJA8knL|program|Associated Token program
s|5tzFkiKscXHK5ZXCGbXZxdw7gTjjD1mBwuoFbhUvuAi9|exchange|Binance hot wallet
s|9WzDXwBbmkg8ZTbNMqUxvQRAyrZzDsGYdLVL9zYtAWWM|exchange|Binance hot wallet
s|2ojv9BAiHUrvsm9gxDe7fJSzbNZSJcxZvf8dqmWGHG8S|exchange|Binance hot wallet
s|H8sMJSCQxfKiFTCfDR3DUMLPwcRbM61LGFJ8N4dK3WjS|exchange|Coinbase hot wallet
s|2AQdpHJ2JpcEgPiATUXjQxA8QmafFegfQwSLWSprPicm|exchange|Coinbase hot wallet
s|GJRs4FwHtemZ5ZE9x3FNvJ8TMwitKTh21yxdRPqn7npE|exchange|Coinbase hot wallet
s|5VCwKtCXgCJ6kit5FybXjvriW3xELsFDhYrPSqtJNmcD|exchange|OKX hot wallet
s|AC5RDfQFmDS1deWZos921JfqscXdByf8BKHs5ACWjtW2|exchange|Bybit hot wallet
s|FWznbcNXWQuHTawe9RxvQ2LdCENssh12dsznf4RiouN5|exchange|Kraken hot wallet
s|BmFdpraQhkiDQE6SnfG5omcA1VwzqfXrwtNYBwWTymy6|exchange|KuCoin hot wallet
s|u6PJ8DtQuPFnfmwHbGFULQ4u4EgjDiyYKjVEsynXq2w|exchange|Gate.io hot wallet
s|ASTyfSima4LLAdDgoFGkgqoKowG1LZFDr9fAQrg7iaJZ|exchange|MEXC hot wallet
s|A77HErqtfN1hLLpvZ9pCtu66FEtM8BveoaKbbMoZ4RiR|exchange|Bitget hot wallet
s|88xTWZMeKfiTgbfEmPLdsUCQcZinwUfk25EBQZ21XMAZ|exchange|HTX hot wallet
s|wormDTUJ6AWPNvk59vGQbDvGJmqbDTdgWgAqcLBCgUb|bridge|Wormhole token bridge program
s|src5qyZHqTqecJV4aY6Cb6zDZLMDzrDKKezs22MPHr4|bridge|deBridge DLN source program
s|dst5MGcFPoBeREFAA5E3tU5ij8m5uVYwkzkSAbsLbNo|bridge|deBridge DLN destination program
s|GybkUNYVNk1FZMt9myAfvpSVgoKBgaueMTvszwBN4qYx|launchpad-config|anoncoin.it DBC pool config
s|8MEtrexHRv8on2wECEsTsBwK42X1sdeVnzdavY54VgQK|launchpad-config|anoncoin.it DBC pool config
s|FGjhZNK7GC6NQyLAE8JS22piSEZorTy8wiAehWyW4V4K|launchpad-config|anoncoin.it DBC pool config
s|AR31BcWNDVPBngGbgMjiFDfAGVcRBGUjU5fkbCtYHr7b|launchpad-config|anoncoin.it DBC pool config
r|0x0312f70169d6919a6e54c0c9b67ea554986e4980|relayer|anoncoin ERC-4337 bundler
r|0x0000000071727de22e5e9d8baf0edac6f37da032|program|ERC-4337 EntryPoint v0.7
r|0xeb7c034704ef8dcd2d32324c1545f62fb4ad0862|program|Doppler Airlock
r|0x1b37d3a72082029c44b35b604ea473617580b69a|program|Doppler token factory
r|0x3be8b97fd0e713b5abe0649fa830223b6b4bc599|program|DopplerERC20V1 implementation
r|0x5f9eb5f6726fe88d5e39867967f5b833d2fa3215|platform|anoncoin/Doppler fee contract
r|0x4e3468951d49f2eea976ed0d6e75ffcb44a9a544|program|Doppler initializer/hook
r|0x8366a39cc670b4001a1121b8f6a443a643e40951|program|Uniswap v4-style pool manager
r|0x0000000000000000000000000000000000000000|program|zero address
r|0x3412f1a0477af054a01ac44aec8a6a300c14bbf5|relayer|anoncoin migration operator
r|0x08d0973f2967709e97fb477f5904e2e3652b2077|relayer|ERC-4337 bundler (anoncoin launches)
r|0xd8a823e4e416df7a8bfa412ae06f5d5639a1db4d|platform|fee-split platform share (~42.98%)
r|0xf52b350de41ac7fbf3412f34683dc2e8f1153207|platform|fee-split protocol share (~14.05%)
r|0x5512144047c2d55297c8470b93e8da87864617cd|relayer|ERC-4337 bundler (anoncoin launches)
r|0x8e3435ad7c1183bc0e34f9ec34ea3423182e1c67|relayer|ERC-4337 bundler (anoncoin launches)
r|0x13c2e85715d8f6fcd48518eccd74ee1dc272ecb8|relayer|ERC-4337 bundler (anoncoin launches)
r|0x9c93024e1dc88d7557075cba3f408c3a8a83e675|relayer|ERC-4337 bundler (anoncoin launches)
r|0x4a449c256d6e20ebe79e595db5a4f63824a9bf5f|relayer|ERC-4337 bundler (anoncoin launches)
r|0xf22e13f4fecf19c17cd142b58a3ed3fbfc361ff5|relayer|ERC-4337 bundler (anoncoin launches)
r|0x85875e3cbde7ead57a9b206db3b71ed2efc4ab91|relayer|ERC-4337 bundler (anoncoin launches)"""
PLAT = {"solana": {}, "robinhood": {}}
for _l in _PW.splitlines():
    _c, _a, _t, _lb = _l.split("|")
    PLAT["solana" if _c == "s" else "robinhood"][_a] = {"type": _t, "label": _lb}
EXCL_SOL, EXCL_EVM = set(), set()


def load_platform(path):
    """Merge platform_wallets.json (curated seed, same format as the repo file) into the built-in list."""
    d = jload(path, {})
    for c in PLAT:
        for a, v in (d.get(c) or {}).items():
            if isinstance(v, dict) and v.get("type"):
                PLAT[c][a.lower() if c == "robinhood" else a] = {"type": v["type"], "label": v.get("label", "")}
    EXCL_SOL.update(PLAT["solana"]); EXCL_EVM.update(PLAT["robinhood"], {OPERATOR})
    return bool(d)
LEARNED = {"solana": {}, "robinhood": {}}
W = None
PL = threading.Lock()
STATS = {}


def et(ts=None, iso=None):
    if ts is not None:
        d = dt.datetime.fromtimestamp(ts, dt.timezone.utc)
    elif iso:
        d = dt.datetime.fromisoformat(iso.replace("Z", "+00:00"))
    else:
        return ""
    return d.astimezone(dt.timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")


def short(a, n=4):
    return f"{a[:n]}…{a[-n:]}" if a and len(a) > 2 * n + 1 else (a or "")


def wpath(n):
    return os.path.join(W, n)


# ---------------------------------------------------------------- HTTP / RPC
class Lim:
    def __init__(s, rps):
        s.iv, s.lk, s.nx = 1.0 / rps, threading.Lock(), 0.0

    def wait(s):
        with s.lk:
            t = max(time.monotonic(), s.nx); s.nx = t + s.iv
        if t > time.monotonic():
            time.sleep(max(0, t - time.monotonic()))


LIM = {"sol": Lim(8), "rh": Lim(12), "anon": Lim(4), "dex": Lim(2), "bs": Lim(3)}
_ML, _MLK = {}, threading.Lock()


def mlim(m):
    with _MLK:
        return _ML.setdefault(m, Lim(3.5))


class Blocked(Exception):
    pass


def http_json(url, data=None, headers=None, lims=(), retries=7, timeout=45, stat=None):
    h = {"User-Agent": UA, "Accept": "application/json", "Accept-Encoding": "gzip", **(headers or {})}
    body = None
    if data is not None:
        body = json.dumps(data).encode(); h["Content-Type"] = "application/json"
    err = None
    for i in range(retries):
        for l in lims:
            l.wait()
        if stat:
            with PL:
                STATS[stat] = STATS.get(stat, 0) + 1
        try:
            with urllib.request.urlopen(urllib.request.Request(url, body, h), timeout=timeout) as r:
                raw = r.read()
                if r.headers.get("Content-Encoding") == "gzip":
                    raw = gzip.decompress(raw)
            try:
                return json.loads(raw)
            except ValueError:
                if b"Just a moment" in raw[:3000] or b"challenge-platform" in raw[:5000]:
                    raise Blocked("Cloudflare challenge")
                raise
        except urllib.error.HTTPError as e:
            err = e
            if e.code == 403 and b"loudflare" in (e.read()[:3000] or b""):
                raise Blocked("Cloudflare 403")
            if e.code in (429, 500, 502, 503, 504):
                time.sleep(min(30, 1.5 * 2 ** i)); continue
            if e.code == 404:
                return None
            raise
        except Blocked:
            raise
        except Exception as e:
            err = e; time.sleep(min(20, 1.5 * (i + 1)))
    raise RuntimeError(f"request failed after {retries} tries: {url[:90]}: {err}")


def sol(method, params):
    for i in range(6):
        o = http_json(SOL_RPC, {"jsonrpc": "2.0", "id": 1, "method": method, "params": params}, lims=(LIM["sol"], mlim(method)), stat="sol")
        if "error" in o:
            m = str(o["error"])
            if "429" in m or "Too many" in m or "rate" in m.lower() or "-32005" in m:
                time.sleep(2 * (i + 1)); continue
            raise RuntimeError(f"Solana {method}: {m[:200]}")
        return o["result"]
    raise RuntimeError(f"Solana {method}: rate limited")


def rh(method, params):
    o = http_json(RH_RPC, {"jsonrpc": "2.0", "id": 1, "method": method, "params": params}, lims=(LIM["rh"],), stat="rh")
    if "error" in o:
        raise RuntimeError(f"Robinhood {method}: {str(o['error'])[:200]}")
    return o["result"]


def anon(params):
    return http_json(API + "?" + urllib.parse.urlencode(params), headers={"Referer": "https://anoncoin.it/", "Origin": "https://anoncoin.it"},
                     lims=(LIM["anon"],), timeout=40, retries=5, stat="anoncoin")


BS_BLOCKED = []


def bs(path):
    if BS_BLOCKED:
        raise Blocked("Blockscout blocked earlier")
    LIM["bs"].wait()
    try:
        return http_json(BS + path, headers={"Accept": "application/json, text/plain, */*", "Referer": BS + "/"}, retries=6, stat="blockscout")
    except Blocked:
        BS_BLOCKED.append(1); raise


# ---------------------------------------------------------------- files
class FLock:
    def __init__(s, p):
        s.p = p

    def __enter__(s):
        s.f = open(s.p, "a+"); t0 = time.time()
        while True:
            try:
                fcntl.flock(s.f, fcntl.LOCK_EX | fcntl.LOCK_NB); return s
            except BlockingIOError:
                if time.time() - t0 > 300:
                    raise TimeoutError("lock busy " + s.p)
                time.sleep(0.5)

    def __exit__(s, *a):
        fcntl.flock(s.f, fcntl.LOCK_UN); s.f.close()


def awrite(path, text):
    fd, tmp = tempfile.mkstemp(dir=os.path.dirname(path) or ".", prefix=".tmp_")
    try:
        with os.fdopen(fd, "w") as f:
            f.write(text); f.flush(); os.fsync(f.fileno())
        os.chmod(tmp, 0o644); os.replace(tmp, path)
    except BaseException:
        if os.path.exists(tmp):
            os.unlink(tmp)
        raise


def jload(p, d):
    try:
        with open(p) as f:
            return json.load(f)
    except Exception:
        return d


# ---------------------------------------------------------------- anoncoin records
def num(v):
    if isinstance(v, dict) and "$numberDecimal" in v:
        v = v["$numberDecimal"]
    if v is None or isinstance(v, bool):
        return None
    if isinstance(v, (int, float)):
        return float(v)
    try:
        t = str(v).strip().replace("$", "").replace(",", "").replace(" ", "").replace("US", "")
        m = {"k": 1e3, "m": 1e6, "b": 1e9, "t": 1e12}.get(t[-1:].lower())
        x = float(t[:-1] if m else t) * (m or 1)
        return x if x == x and abs(x) != float("inf") else None
    except (TypeError, ValueError):
        return None


def slim(m):
    tk = m.get("token") or {}; md = m.get("metaData") or {}; mig = tk.get("robinhoodMigration") or {}; cto = md.get("cto") or {}
    u = m.get("userId") if isinstance(m.get("userId"), dict) else {"_id": m.get("userId")}
    addr = tk.get("address") or m.get("tokenAddress") or ""
    chain = m.get("chainType") or tk.get("chainType") or md.get("chainType") or ("robinhood" if EVM.match(addr) else "solana" if addr else None)
    cr, src = tk.get("createdAt") or m.get("createdAt"), "record"
    if not cr and re.match(r"^[0-9a-f]{24}$", m.get("_id", "")):
        cr, src = dt.datetime.fromtimestamp(int(m["_id"][:8], 16), dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"), "objectid"
    r = {"_id": m.get("_id"), "chain": chain, "address": addr, "name": tk.get("name") or m.get("tickerName") or m.get("title"),
         "symbol": tk.get("symbol") or m.get("tickerSymbol"), "createdAt": cr, "createdAtSource": src if cr else None, "txHash": tk.get("txHash"),
         "userId": u.get("_id"), "userName": u.get("userName") or m.get("userName"), "walletAddress": u.get("walletAddress"),
         "devWalletAddress": md.get("devWalletAddress"), "creatorAddress": ((tk.get("fee") or {}).get("attribution") or {}).get("creatorAddress"),
         "sourceMint": mig.get("sourceMint"), "migrationRole": mig.get("role"), "destination": (mig.get("destination") or {}).get("address"),
         "ctoWallet": cto.get("walletAddress"), "ctoIsDefaultCreator": cto.get("isDefaultCreator"), "ctoUpdatedOn": cto.get("updatedOn"),
         "ctoElectionId": cto.get("electionId"), "ctoWinnerFeeSol": tk.get("ctoWinnerFeeSol"), "isMigrated": tk.get("isMigrated"),
         "prevUserId": (tk.get("royalty") or {}).get("prevUserId")}
    lv = tk.get("liveValuation") or {}; mt = tk.get("metrics") or {}; pr = lv.get("pricing") or {}
    if lv or tk.get("marketCap") is not None:
        a = num(lv.get("marketCapUsd")) if lv else num(tk.get("marketCap")); ath = num(lv.get("marketCapAthUsd"))
        r.update(mcapUsd=a, mcapAthUsd=ath if ath is not None else num(tk.get("marketCapATH")),
                 mcapAthSource="liveValuation" if ath is not None else "token.marketCapATH" if num(tk.get("marketCapATH")) is not None else None,
                 mcapProvisional=lv.get("provisional"), mcapValuationTime=lv.get("valuationTime"), athComplete=lv.get("athComplete"),
                 athBucketSeconds=lv.get("athBucketSeconds"), athBucketStart=lv.get("athBucketStart"),
                 athAt=mt.get("athAt") or (dt.datetime.fromtimestamp(lv["athTime"] / 1000, dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ") if lv.get("athTime") else None),
                 mcapPriceStale=tk.get("priceStale") or (pr.get("status") == "stale") or None)
    return r


FEED_KEEP = ("_id", "chain", "address", "name", "symbol", "createdAt", "createdAtSource", "txHash", "userId", "userName", "walletAddress",
             "devWalletAddress", "creatorAddress", "sourceMint", "migrationRole", "destination", "foundVia", "creatorAddressOnchain")


def feed_rows():
    rows = {}
    try:
        with open(wpath("feed_robinhood.jsonl")) as f:
            for l in f:
                try:
                    r = json.loads(l); rows[r["_id"]] = r
                except Exception:
                    pass
    except FileNotFoundError:
        pass
    return rows


def feed_write(rows):
    awrite(wpath("feed_robinhood.jsonl"), "".join(json.dumps({k: r.get(k) for k in FEED_KEEP}, separators=(",", ":")) + "\n" for r in rows.values()))


def refresh_feed(force, max_age):
    """Robinhood part of the public global feed (chainType=robinhood): gives userId <-> EVM creator wallet. Solana coins come
    from on-chain DBC scans of the account's Solana wallet, each confirmed by the public single-coin record."""
    st = wpath("feed_state.json")
    with FLock(wpath(".feed.lock")):
        age = time.time() - jload(st, {}).get("t", 0); rows = feed_rows()
        if not force and age < max_age:
            return rows, f"fresh ({age:.0f}s old)"
        known, nt, pages, new = set(rows), None, 0, 0
        while pages < 2000:
            d = (anon({"chainType": "robinhood", "limit": 50, **({"nextToken": nt} if nt else {})}) or {}).get("data") or {}
            docs = d.get("docs") or []; pages += 1
            hit = sum(m.get("_id") in known for m in docs)
            for m in docs:
                r = slim(m); o = rows.get(r["_id"]) or {}
                new += r["_id"] not in rows
                for k in ("foundVia", "creatorAddressOnchain"):
                    if o.get(k) and not r.get(k):
                        r[k] = o[k]
                rows[r["_id"]] = r
            nt = d.get("nextToken")
            if (known and docs and hit == len(docs)) or not nt or not docs or d.get("hasMore") is False:
                break
        if new:
            feed_write(rows)
        awrite(st, json.dumps({"t": time.time(), "pages": pages}))
        return rows, f"refreshed {pages} page(s), {new} new"


class Cache:
    def __init__(s):
        s.lk = threading.RLock(); s.d = jload(wpath("cache.json"), {})
        for k in ("tx_token", "block_ts", "dex", "ath"):
            s.d.setdefault(k, {})
        s.d.setdefault("fee_split", {"to_block": -1, "logs": []})

    def save(s):
        with s.lk, FLock(wpath(".cache.lock")):
            disk = jload(wpath("cache.json"), {}); d = s.d
            for k in ("tx_token", "block_ts"):
                d[k] = {**(disk.get(k) or {}), **d[k]}
            dd = dict(disk.get("dex") or {})
            for u, v in d["dex"].items():
                if u not in dd or dd[u]["t"] < v["t"]:
                    dd[u] = v
            d["dex"] = {u: v for u, v in dd.items() if time.time() - v["t"] < 86400}
            da = dict(disk.get("ath") or {})
            for k, v in d["ath"].items():
                if ath_better(v, da.get(k)):
                    da[k] = v
            d["ath"] = da
            if (disk.get("fee_split") or {}).get("to_block", -1) > d["fee_split"]["to_block"]:
                d["fee_split"] = disk["fee_split"]
            awrite(wpath("cache.json"), json.dumps(d, separators=(",", ":")))


C = None
ATHF = ("mcapAthUsd", "mcapAthSource", "athAt", "athBucketStart", "athBucketSeconds", "athComplete")


def ath_val(e):
    try:
        v = float((e or {}).get("mcapAthUsd"))
        return v if v > 0 else None
    except (TypeError, ValueError):
        return None


def ath_better(n, o):
    nv, ov = ath_val(n), ath_val(o)
    return nv is not None and (ov is None or nv > ov or (nv == ov and (n.get("seenAt") or 0) >= (o.get("seenAt") or 0)))


def ath_merge(c):
    """anoncoin sometimes returns an empty ATH history: never replace the last good ATH (kept in cache.json)."""
    k = c["address"].lower(); fr = {f: c.get(f) for f in ATHF}; fr["seenAt"] = time.time()
    with C.lk:
        o = C.d["ath"].get(k)
        if ath_val(fr) is not None and ath_better(fr, o):
            C.d["ath"][k] = fr; return
        if ath_val(o) is None or ath_val(fr) == ath_val(o):
            return
    for f in ATHF:
        c[f] = o.get(f)
    c["athCached"], c["athCachedAt"] = True, o.get("seenAt")


class Records:
    def __init__(s, rows):
        s.rows = rows; s.by = {r["address"].lower(): r for r in rows.values() if r.get("address")}
        s.fresh, s.new, s.lk, s.infl = {}, {}, threading.Lock(), {}

    def cached(s, a):
        return s.by.get((a or "").lower())

    def lookup(s, addr):
        k = addr.lower()
        with s.lk:
            if k in s.fresh:
                return s.fresh[k]
            ev = s.infl.get(k); own = ev is None
            if own:
                ev = s.infl[k] = threading.Event()
        if not own:
            ev.wait(); return s.fresh.get(k)
        res = raw = None
        try:
            for att in range(3):
                got = None
                for cand in (dict.fromkeys([addr, k]) if EVM.match(addr) else [addr]):
                    try:
                        d = (anon({"tickerSymbol": cand, "limit": 1}) or {}).get("data") or {}
                    except Exception:
                        continue
                    got = next(((slim(m), m) for m in d.get("docs") or [] if (slim(m)["address"] or "").lower() == k), None)
                    if got:
                        break
                if got and (res is None or got[0].get("mcapUsd") is not None or res.get("mcapUsd") is None) \
                        and not (res is not None and res.get("mcapAthUsd") is not None and got[0].get("mcapAthUsd") is None):
                    res, raw = got
                lv = ((raw or {}).get("token") or {}).get("liveValuation") or {}
                if res is None or lv.get("supplyPending") or (res.get("mcapUsd") is not None and (lv or att >= 1)):
                    break   # also retry once when the record came back without liveValuation (transient; ATH then missing/legacy)
                time.sleep(0.8 * (att + 1))
            if res is not None:
                md = raw.get("metaData") or {}; tk = raw.get("token") or {}
                if res.get("mcapUsd") is None:
                    res["mcapError"] = "anoncoin record had no valuation (" + ("supply pending" if (tk.get("liveValuation") or {}).get("supplyPending") else "3 tries") + ")"
                res["royaltySharesPresent"] = bool(md.get("royaltyShares"))
                res["ctoElectionActive"] = raw["ctoElection"].get("isActive") if isinstance(raw.get("ctoElection"), dict) else None
                res["image"] = next((x.get("thumbnailUrl") for x in raw.get("media") or [] if isinstance(x, dict) and x.get("thumbnailUrl")), None) \
                    or f"https://cdn.anoncoin.it/{res['_id']}/image.png"
                o = s.cached(k) or {}
                for kk in ("foundVia", "creatorAddressOnchain"):
                    if o.get(kk) and not res.get(kk):
                        res[kk] = o[kk]
            with s.lk:
                s.fresh[k] = res
                if res is not None:
                    if res["_id"] not in s.rows and res["chain"] == "robinhood":
                        s.new[res["_id"]] = res
                    s.rows[res["_id"]] = res; s.by[k] = res
        finally:
            ev.set()
        return res

    def user_coins(s, uid):
        with s.lk:
            return {r["address"].lower(): r for r in s.rows.values() if r.get("userId") == uid and r.get("address")}


# ---------------------------------------------------------------- platform-wallet auto-learning
class Learn:
    """Persisted in learned_platform_wallets.json. A wallet that pays/sends/signs launch txs, or receives a fee share,
    across launches of >= THRESH distinct creator accounts is platform infrastructure, never a creator. Wallets seen as a
    resolved creator (DBC pool creator, sole fee-split beneficiary, record creator wallet) are never learned."""
    def __init__(s):
        s.lk = threading.RLock(); s.p = wpath("learned_platform_wallets.json"); d = jload(s.p, {})
        s.wallets = {c: dict((d.get("wallets") or {}).get(c) or {}) for c in PLAT}
        s.obs = {c: {a: {"c": set(v["c"]), "m": list(v["m"])} for a, v in ((d.get("observations") or {}).get(c) or {}).items()} for c in PLAT}
        s.creators = {c: set((d.get("creators") or {}).get(c) or []) for c in PLAT}
        s.new = []; s.apply()

    def apply(s):
        for c in PLAT:
            LEARNED[c] = dict(s.wallets[c])

    def creator(s, chain, w):
        if w:
            with s.lk:
                s.creators[chain].add(w.lower() if chain == "robinhood" else w)

    def observe(s, chain, w, who, mint):
        if not w or not who:
            return
        w = w.lower() if chain == "robinhood" else w
        if w in PLAT[chain] or w in s.wallets[chain] or w in EXCL_EVM:
            return
        with s.lk:
            o = s.obs[chain].setdefault(w, {"c": set(), "m": []}); o["c"].add(who)
            if mint and mint not in o["m"] and len(o["m"]) < 5:
                o["m"].append(mint)

    def add(s, chain, w, ev):
        with s.lk:
            if w in s.wallets[chain] or w in s.creators[chain]:
                return
            s.wallets[chain][w] = {"type": "platform (auto-detected)", "evidence": {**ev, "learned_at": et(ts=time.time())}}
            s.new.append({"chain": chain, "wallet": w, **ev}); s.apply()

    def evaluate(s, guard=()):
        for chain in PLAT:
            for w, o in list(s.obs[chain].items()):
                if len(o["c"]) >= THRESH and w not in guard:
                    s.add(chain, w, {"source": "launch tx fee payer/sender/signer", "distinct_creators": len(o["c"]), "example_mints": o["m"][:3]})

    def save(s):
        with s.lk, FLock(wpath(".learn.lock")):
            d = jload(s.p, {})
            for c in PLAT:
                s.wallets[c] = {**((d.get("wallets") or {}).get(c) or {}), **s.wallets[c]}
                for a, v in ((d.get("observations") or {}).get(c) or {}).items():
                    o = s.obs[c].setdefault(a, {"c": set(), "m": []}); o["c"] |= set(v["c"]); o["m"] = list(dict.fromkeys(o["m"] + v["m"]))[:5]
                s.creators[c] |= set((d.get("creators") or {}).get(c) or [])
            awrite(s.p, json.dumps({"threshold": THRESH, "wallets": s.wallets,
                                    "observations": {c: {a: {"c": sorted(v["c"]), "m": v["m"]} for a, v in s.obs[c].items()} for c in s.obs},
                                    "creators": {c: sorted(v) for c, v in s.creators.items()}}, indent=1))


L = None


def np_of(bens, frm=""):
    """Non-platform fee-split beneficiaries -> (candidates, learned wallets removed, fell back to learned)."""
    a = [x.lower() for x, _ in bens if x.lower() not in EXCL_EVM and x.lower() != frm]
    b = [x for x in a if x not in LEARNED["robinhood"]]
    return (b, [x for x in a if x not in b], False) if b else (a, a, bool(a))


# ---------------------------------------------------------------- Solana
B58 = "123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz"


def b58e(b):
    n = int.from_bytes(b, "big"); s = ""
    while n:
        n, r = divmod(n, 58); s = B58[r] + s
    return "1" * (len(b) - len(b.lstrip(b"\0"))) + s


def b58d(s):
    n = 0
    for c in s:
        n = n * 58 + B58.index(c)
    return b"\0" * (len(s) - len(s.lstrip("1"))) + (n.to_bytes((n.bit_length() + 7) // 8, "big") if n else b"")


_P = 2 ** 255 - 19; _D = (-121665 * pow(121666, _P - 2, _P)) % _P; _I = pow(2, (_P - 1) // 4, _P)


def on_curve(b):
    y = int.from_bytes(b, "little") & ((1 << 255) - 1)
    if y >= _P:
        return False
    u = (y * y - 1) % _P; v = (_D * y * y + 1) % _P; x2 = u * pow(v, _P - 2, _P) % _P
    if x2 == 0:
        return True
    x = pow(x2, (_P + 3) // 8, _P)
    if (x * x - x2) % _P:
        x = x * _I % _P
    return (x * x - x2) % _P == 0


def pda(seeds, prog):
    for bump in range(255, -1, -1):
        h = hashlib.sha256(b"".join(seeds) + bytes([bump]) + b58d(prog) + b"ProgramDerivedAddress").digest()
        if not on_curve(h):
            return b58e(h)


def is_sol(a):
    try:
        return bool(re.fullmatch(r"[1-9A-HJ-NP-Za-km-z]{32,44}", a)) and len(b58d(a)) == 32
    except ValueError:
        return False


TXC, _TXL = {}, threading.Lock()


def sol_tx(sig, enc="json"):
    with _TXL:
        if (sig, enc) in TXC:
            return TXC[(sig, enc)]
    tx = None
    for i in range(3):  # the public RPC sometimes answers null for a tx that exists; never cache a null
        tx = sol("getTransaction", [sig, {"encoding": enc, "maxSupportedTransactionVersion": 0}])
        if tx is not None:
            with _TXL:
                TXC[(sig, enc)] = tx
            break
        time.sleep(1.0 * (i + 1))
    return tx


def keys_of(tx):
    m = tx["transaction"]["message"]; la = tx["meta"].get("loadedAddresses") or {}
    return m["accountKeys"] + la.get("writable", []) + la.get("readonly", [])


def gpa(prog, size, off, key, sl):
    return sol("getProgramAccounts", [prog, {"encoding": "base64", "dataSlice": sl, "filters": [{"dataSize": size}, {"memcmp": {"offset": off, "bytes": key}}]}])


def pool_of_mint(mint):
    out = []
    for a in gpa(DBC, 424, 136, mint, {"offset": 72, "length": 96}):
        d = base64.b64decode(a["account"]["data"][0])
        out.append({"pool": a["pubkey"], "config": b58e(d[:32]), "creator": b58e(d[32:64])})
    return out


def mints_of_creator(w):
    return {b58e(base64.b64decode(a["account"]["data"][0])) for a in gpa(DBC, 424, 104, w, {"offset": 136, "length": 32})}


def parse_init(tx, mint, who=None):
    """(creator, ix) if tx is InitializeVirtualPool* of mint (account 2 = creator, 3 = mint). Records payer/signers for learning."""
    if not tx:
        return None, None
    name = next((l.split("Instruction: ")[1] for l in tx["meta"].get("logMessages") or [] if "Instruction: InitializeVirtualPool" in l), None)
    if not name:
        return None, None
    k = keys_of(tx)
    for ix in tx["transaction"]["message"]["instructions"]:
        acc = [k[i] for i in ix["accounts"]]
        if k[ix["programIdIndex"]] == DBC and len(acc) > 3 and acc[3] == mint:
            L.creator("solana", acc[2])
            for sg in k[:tx["transaction"]["message"]["header"]["numRequiredSignatures"]]:
                if sg not in (acc[2], acc[3]):
                    L.observe("solana", sg, who or acc[2], mint)
            return acc[2], name
    return None, None


def sigs_all(a, pages=10):
    out, before = [], None
    for _ in range(pages):
        s = sol("getSignaturesForAddress", [a, {"limit": 1000, **({"before": before} if before else {})}])
        out += s
        if len(s) < 1000:
            return out, True
        before = s[-1]["signature"]
    return out, False


def ixs_of(tx):
    x = list(tx["transaction"]["message"]["instructions"])
    for i in tx["meta"].get("innerInstructions") or []:
        x += i["instructions"]
    return x


def label(chain, w):
    lab = PLAT[chain].get(w) or LEARNED[chain].get(w)
    return f"KNOWN {lab['type'].upper()}: {lab.get('label', '')}" if lab else None


def sol_funding(w):
    s, comp = sigs_all(w)
    if not s:
        return {"wallet": w, "result": "wallet has no transactions on Solana (custodial wallet that never transacted)"}
    old = [x for x in reversed(s) if not x.get("err")][:40]; res = {"wallet": w}
    if not comp:
        res["note"] = "wallet has >10000 signatures; walk capped, the earliest transfer may be older"
    for i in range(0, len(old), 4):
        b = old[i:i + 4]
        with cf.ThreadPoolExecutor(4) as ex:
            txs = list(ex.map(lambda x: sol_tx(x["signature"], "jsonParsed"), b))
        for x, tx in zip(b, txs):
            for ix in (ixs_of(tx) if tx else []):
                p = ix.get("parsed")
                if not isinstance(p, dict) or ix.get("program") != "system":
                    continue
                f = p.get("info", {}); dst = f.get("destination") or f.get("newAccount"); src = f.get("source"); lam = f.get("lamports")
                if dst == w and src and src != w and lam and lam >= 1_000_000:
                    res.update(amount=lam / 1e9, unit="SOL", sender=src, time=et(ts=tx.get("blockTime")), tx=x["signature"],
                               sender_flag=label("solana", src) or "unlabeled")
                    return res
    res["result"] = "no incoming SOL system transfer (>= 0.001 SOL) in the wallet's 40 oldest txs"
    return res


# ---------------------------------------------------------------- Robinhood
RCC, _RCL = {}, threading.Lock()


def receipt(h):
    with _RCL:
        if h in RCC:
            return RCC[h]
    r = rh("eth_getTransactionReceipt", [h])
    with _RCL:
        RCC[h] = r
    return r


def block_ts(bn):
    n = str(int(bn, 16) if isinstance(bn, str) else int(bn))
    with C.lk:
        v = C.d["block_ts"].get(n)
    if v is None:
        v = int(rh("eth_getBlockByNumber", [hex(int(n)), False])["timestamp"], 16)
        with C.lk:
            C.d["block_ts"][n] = v
    return v


def dsplit(data):
    w = bytes.fromhex(data[2:]); ws = [w[i:i + 32] for i in range(0, len(w), 32)]
    o = int.from_bytes(ws[0], "big") // 32; n = int.from_bytes(ws[o], "big")
    return [("0x" + ws[o + 1 + 2 * i][12:].hex(), int.from_bytes(ws[o + 2 + 2 * i], "big")) for i in range(n)]


def airlock(rc):
    return next(("0x" + l["data"][26:66].lower() for l in rc["logs"] if l["address"].lower() == AIRLOCK and l["topics"][0].startswith(T_CREATE)), None)


def split_of(rc, who=None):
    """Fee split of a launch receipt -> (creator|None, non-platform list, bens, token, shape, learned removed, fell back)."""
    frm = (rc.get("from") or "").lower(); to = (rc.get("to") or "").lower()
    shape = (f"native ERC-4337 handleOps, bundler {frm}" if to == ENTRY else "migration/operator bundle() from 0x3412f1a0…" if frm == OPERATOR
             else f"tx from {frm} to {to}")
    tok = airlock(rc)
    for l in rc["logs"]:
        if l["address"].lower() == FEE_C and l["topics"][0] == FEE_T:
            bens = dsplit(l["data"]); np_, lr, fb = np_of(bens, frm); c = np_[0] if len(np_) == 1 else None
            L.observe("robinhood", frm, who or c, tok)
            if c and not fb:
                L.creator("robinhood", c)
            return c, np_, bens, tok, shape, lr, fb
    return None, [], [], tok, shape, [], False


def first_log(a, lo, hi):
    try:
        lg = rh("eth_getLogs", [{"fromBlock": hex(lo), "toBlock": hex(hi), "address": a}])
    except RuntimeError:
        if hi - lo < 1000:
            raise
        lg = None
    if lg is None or len(lg) >= 10000:
        m = (lo + hi) // 2
        return first_log(a, lo, m) or first_log(a, m + 1, hi)
    return min(lg, key=lambda l: (int(l["blockNumber"], 16), int(l["logIndex"], 16))) if lg else None


def creation_tx(a):
    try:
        d = bs(f"/api?module=contract&action=getcontractcreation&contractaddresses={a}")
        if d and d.get("result"):
            return d["result"][0]["txHash"], "Blockscout getcontractcreation"
    except Exception:
        pass
    head = int(rh("eth_blockNumber", []), 16)
    for s in range(0, head + 1, 10_000_000):
        l = first_log(a, s, min(s + 9_999_999, head))
        if l:
            return l["transactionHash"], "earliest token log via eth_getLogs"
    return None, None


def userop_senders(rc, addr):
    out, cur = [], []
    for l in rc["logs"]:
        t0 = l["topics"][0] if l["topics"] else ""; ent = l["address"].lower() == ENTRY
        if ent and t0 == T_BEFORE:
            cur = []
        elif ent and t0 == T_USEROP:
            if any(x["address"].lower() == addr or (x["address"].lower() == AIRLOCK and x["topics"][0].startswith(T_CREATE) and "0x" + x["data"][26:66].lower() == addr) for x in cur):
                out.append("0x" + l["topics"][2][-40:].lower())
            cur = []
        else:
            cur.append(l)
    return out


def rh_funding(w):
    res = {"wallet": w}; c = []
    try:
        for act, kind in (("txlist", "transaction"), ("txlistinternal", "internal")):
            d = bs(f"/api?module=account&action={act}&address={w}&sort=asc&page=1&offset=200") or {}
            t = next((t for t in d.get("result") or [] if (t.get("to") or "").lower() == w and int(t.get("value") or 0) > 0), None)
            if t:
                c.append((int(t["timeStamp"]), t["from"].lower(), int(t["value"]), t.get("hash") or t.get("transactionHash"), kind))
    except Blocked:
        res["result"] = "Blockscout blocked by Cloudflare; funding trace unavailable"; return res
    if not c:
        try:
            bal = int(rh("eth_getBalance", [w, "latest"]), 16) / 1e18; nonce = int(rh("eth_getTransactionCount", [w, "latest"]), 16)
        except Exception:
            bal = nonce = None
        res["result"] = (f"no incoming ETH ever (balance {bal} ETH, nonce {nonce}); the wallet acts only through ERC-4337 user operations "
                         "whose gas the platform sponsors, so there is no funding hop to follow on-chain")
        return res
    ts, frm, val, h, kind = min(c); flag = label("robinhood", frm) or "not a known exchange/bridge/platform wallet"
    try:
        if (rh("eth_getTransactionByHash", [h]) or {}).get("type") in ("0x64", "0x65", "0x68", "0x69"):
            flag = "BRIDGE: Arbitrum-Orbit L1->L2 deposit; sender is the aliased L1 address"
    except Exception:
        pass
    res.update(amount=val / 1e18, unit="ETH", sender=frm, time=et(ts=ts), tx=h, kind=kind, sender_flag=flag)
    return res


GUARD_EVM = set()


class FeeSplits:
    """All fee-split events of the fee contract (whole chain), cached incrementally; also feeds fee-share learning."""
    def __init__(s):
        s.lk = threading.Lock(); s.synced = False; s.secs = None

    def sync(s):
        with s.lk:
            if s.synced:
                return
            t0 = time.time(); fs = C.d["fee_split"]; head = int(rh("eth_blockNumber", []), 16)
            rg = [(a, min(a + 4_999_999, head)) for a in range(fs["to_block"] + 1, head + 1, 5_000_000)]

            def get(r):
                lo, hi = r
                try:
                    return rh("eth_getLogs", [{"address": FEE_C, "topics": [FEE_T], "fromBlock": hex(lo), "toBlock": hex(hi)}])
                except Exception:
                    if hi - lo < 50_000:
                        raise
                    m = (lo + hi) // 2
                    return get((lo, m)) + get((m + 1, hi))
            new = []
            with cf.ThreadPoolExecutor(6) as ex:
                for lg in ex.map(get, rg):
                    for l in lg:
                        try:
                            new.append([l["transactionHash"], int(l["blockNumber"], 16), [[a, b] for a, b in dsplit(l["data"])]])
                        except Exception:
                            pass
            with C.lk:
                seen = {x[0] for x in fs["logs"]}; fs["logs"] += [x for x in new if x[0] not in seen]; fs["to_block"] = head
            s.learn(); s.synced = True; s.secs = round(time.time() - t0, 1)

    def learn(s):
        """A fee-share recipient that sits next to >= THRESH distinct other beneficiaries and is never a split's sole
        non-platform beneficiary (= never anyone's creator) and never a record creatorAddress is auto-learned as platform."""
        co, n, sole, ex = {}, {}, set(), {}
        for h, bn, bens in C.d["fee_split"]["logs"]:
            np_ = [a.lower() for a, _ in bens if a.lower() not in EXCL_EVM]
            if len(np_) == 1:
                sole.add(np_[0])
            for a in np_:
                n[a] = n.get(a, 0) + 1; co.setdefault(a, set()).update(b for b in np_ if b != a)
                if len(ex.setdefault(a, [])) < 2:
                    ex[a].append(h)
        for a, others in co.items():
            if len(others) >= THRESH and a not in sole | GUARD_EVM and a not in LEARNED["robinhood"]:
                toks = []
                for h in ex[a]:
                    try:
                        toks.append(s.token_of(h))
                    except Exception:
                        pass
                L.add("robinhood", a, {"source": "fee-split co-beneficiary next to distinct creators, never a sole beneficiary",
                                       "count": n[a], "distinct_creators": len(others), "example_mints": [t for t in toks if t], "example_txs": ex[a]})

    def matches(s, creators):
        s.sync(); cs = {c.lower() for c in creators}; out = {}
        for h, bn, bens in C.d["fee_split"]["logs"]:
            np_ = np_of(bens)[0]
            if cs.intersection(np_):
                out[h] = np_
        return out

    def token_of(s, h):
        with C.lk:
            t = C.d["tx_token"].get(h)
        if t is None:
            t = airlock(receipt(h)) or ""
            with C.lk:
                C.d["tx_token"][h] = t
        return t or None


FS = FeeSplits()


# ---------------------------------------------------------------- per coin + portfolio
def coin_onchain(r, wallets):
    notes, flags = [], []; h = r.get("txHash"); sy = r["symbol"]
    try:
        if r["chain"] == "robinhood":
            if not h:
                h, how = creation_tx(r["address"].lower())
                if h:
                    r["txHashOnchain"] = h; notes.append(f"{sy}: record has no txHash; launch tx {h} from {how}")
            if not h:
                notes.append(f"{sy} {r['address']}: record has no launch txHash; block time / creation creator not checked"); return notes, flags
            rc = receipt(h); c, np_, bens, tok, shape, lr, fb = split_of(rc, r.get("userId"))
            r["blockTime"] = block_ts(rc["blockNumber"]); r["launchShape"] = shape; r["creatorAddressOnchain"] = c
            if len(np_) > 1:
                flags.append(f"{sy} {r['address']}: fee split has {len(np_)} non-platform beneficiaries {np_}; creator not unique")
            if not np_:
                notes.append(f"{sy} {r['address']}: no anoncoin fee split in tx {h}")
            if fb:
                flags.append(f"{sy}: fee-split creator {c} is an auto-detected platform wallet")
            if c and r.get("creatorAddress") and c != r["creatorAddress"].lower():
                flags.append(f"{sy}: record creatorAddress {r['creatorAddress']} != on-chain fee-split creator {c}")
            if tok and tok != r["address"].lower():
                flags.append(f"{sy}: launch tx {h} created {tok}, not {r['address']}")
        else:
            if not h:
                notes.append(f"{sy} {r['address']}: record has no launch txHash; block time / creation creator not checked"); return notes, flags
            tx = sol_tx(h)
            if not tx:
                notes.append(f"{sy}: launch tx {h} not found on Solana RPC"); return notes, flags
            r["blockTime"] = tx.get("blockTime"); c, name = parse_init(tx, r["address"], r.get("userId"))
            if c:
                r["creationCreator"] = c
                if c not in wallets:
                    notes.append(f"{sy} {r['address']}: creation-tx creator {c} is not this account's wallet; creator role was transferred in later (ON-CHAIN)")
            else:
                notes.append(f"{sy}: record txHash {h} is not an InitializeVirtualPool tx for this mint; creation creator not verified")
    except Exception as e:
        notes.append(f"{sy}: block-time lookup failed ({str(e)[:120]})")
    return notes, flags


def dexscreener(coins):
    sc = [r for r in coins if r["chain"] == "solana" and r.get("address")]; notes = []
    for i in range(0, len(sc), 30):
        ch = sc[i:i + 30]; url = "https://api.dexscreener.com/tokens/v1/solana/" + ",".join(r["address"] for r in ch)
        with C.lk:
            c = C.d["dex"].get(url)
        if c and time.time() - c["t"] < 600:
            d = c["d"]
        else:
            try:
                d = http_json(url, lims=(LIM["dex"],), retries=4, timeout=30, stat="dexscreener")
                with C.lk:
                    C.d["dex"][url] = {"t": time.time(), "d": d}
            except Exception as e:
                notes.append(f"DexScreener batch failed: {str(e)[:80]}"); continue
        best = {}
        for p in d or []:
            a = (p.get("baseToken") or {}).get("address")
            if a and p.get("marketCap") is not None and ((p.get("liquidity") or {}).get("usd") or 0) >= ((best.get(a, {}).get("liquidity") or {}).get("usd") or -1):
                best[a] = p
        for r in ch:
            p = best.get(r["address"])
            if p:
                r["dsMcapUsd"] = num(p.get("marketCap")); r["dsPair"] = p.get("pairAddress")
    return notes


class Portfolios:
    def __init__(s, recs, pool):
        s.recs, s.ex, s.lk, s.f = recs, pool, threading.Lock(), {}

    def get(s, uid):
        with s.lk:
            f = s.f.get(uid); own = f is None
            if own:
                f = s.f[uid] = cf.Future()
        if own:
            try:
                f.set_result(s.build(uid))
            except BaseException as e:
                f.set_exception(e)
        return f.result()

    def build(s, uid):
        """Coins of the account: Robinhood feed rows with this userId + DBC pools of its Solana wallet(s) + fee splits naming its
        EVM creator wallet(s) + migration links; every on-chain hit is confirmed by its public record's userId."""
        t0 = time.time(); R = s.recs; notes, flags, conf, scanned = [], [], {}, set()
        for _ in range(3):
            mine = R.user_coins(uid)
            wallets = {r["walletAddress"] for r in mine.values() if r.get("walletAddress")} | \
                      {r["devWalletAddress"] for r in mine.values() if r.get("devWalletAddress") and not EVM.match(r["devWalletAddress"])}
            cands = {}; tw = sorted(wallets - scanned); scanned |= set(tw)
            rc = [r for r in mine.values() if r["chain"] == "robinhood" and "rc:" + r["address"].lower() not in scanned]
            scanned |= {"rc:" + r["address"].lower() for r in rc}
            fw = {w: s.ex.submit(mints_of_creator, w) for w in tw}; fr = [s.ex.submit(coin_onchain, r, wallets) for r in rc]
            for w, f in fw.items():
                try:
                    ms = f.result(); notes.append(f"Meteora DBC pools with creator {w}: {len(ms)}")
                    for m in ms:
                        cands.setdefault(m, f"DBC creator {w}"); conf.setdefault(m.lower(), f"ON-CHAIN: current Meteora DBC pool creator {w}")
                except Exception as e:
                    notes.append(f"DBC scan for {w} failed: {e}")
            for f in fr:
                n, fl = f.result(); notes += n; flags += fl
            evm = ({r["creatorAddress"].lower() for r in mine.values() if r.get("creatorAddress")} |
                   {r["creatorAddressOnchain"] for r in mine.values() if r.get("creatorAddressOnchain")}) - EXCL_EVM
            en = {e for e in evm if "evm:" + e not in scanned}; scanned |= {"evm:" + e for e in en}
            if en:
                try:
                    m = FS.matches(en); toks = {}
                    for h, tok in zip(list(m), s.ex.map(FS.token_of, list(m))):
                        if tok:
                            toks[tok] = h
                            if len(m[h]) > 1:
                                flags.append(f"fee split of {tok} (tx {h}) has {len(m[h])} non-platform beneficiaries {m[h]}; creator not unique")
                    notes.append(f"Robinhood fee-split creator matches for {sorted(en)}: {len(toks)}")
                    for t, h in toks.items():
                        cands.setdefault(t, f"fee-split beneficiary, tx {h}"); conf.setdefault(t.lower(), f"ON-CHAIN: fee-split creator beneficiary, tx {h}")
                except Exception as e:
                    notes.append(f"Robinhood fee-split scan failed: {e}")
            for r in mine.values():
                for a in (r.get("sourceMint"), r.get("destination")):
                    if a:
                        cands.setdefault(a, "robinhoodMigration link")
            todo = []
            for a, why in cands.items():
                if a.lower() in mine:
                    continue
                c = R.cached(a)
                if c is None:
                    todo.append((a, why))
                elif c.get("userId") != uid:
                    notes.append(f"{a} ({why}) is on anoncoin under a DIFFERENT userId {c['userId']} ({c.get('userName')})")
            added = 0
            for (a, why), r in zip(todo, s.ex.map(lambda x: R.lookup(x[0]), todo)):
                if r and r["userId"] == uid:
                    added += 1
                    if r["chain"] == "robinhood" or "migration" in why:
                        r["foundVia"] = why   # the full Robinhood feed is cached, so a miss there means 'not in public feed'
                elif r:
                    notes.append(f"{a} ({why}) is on anoncoin under a DIFFERENT userId {r['userId']} ({r['userName']})")
                else:
                    notes.append(f"{a} ({why}) has no anoncoin record via public lookup")
            if not added:
                break
        return {"coins": R.user_coins(uid), "notes": notes, "flags": flags, "confirmed": conf, "secs": round(time.time() - t0, 1)}


# ---------------------------------------------------------------- deep stage
def classify(w, creators, cto, holder=None):
    if w in creators:
        return "creator"
    if w == PARTNER:
        return "partner (platform; anoncoin DBC config fee_claimer)"
    if cto and w == cto:
        return "CTO winner (creator-fee redirect)"
    if holder and w == holder:
        return "outside LP (position holder)"
    lab = PLAT["solana"].get(w) or LEARNED["solana"].get(w)
    return f"known {lab['type']}: {lab.get('label', '')}" if lab else "REDIRECT (not the position holder)"


def claim_recipients(tx):
    """Value receivers of a ClaimPositionFee tx; excludes a platform fee payer, created accounts (rent) and signer tips."""
    m = tx["transaction"]["message"]; keys = [k["pubkey"] if isinstance(k, dict) else k for k in m["accountKeys"]]
    signers = {k["pubkey"] for k in m["accountKeys"] if isinstance(k, dict) and k.get("signer")}
    payer = keys[0] if keys[0] in EXCL_SOL or keys[0] in LEARNED["solana"] else None
    created, tips, closes = set(), {}, set()
    for ins in ixs_of(tx):
        p = ins.get("parsed")
        if not isinstance(p, dict):
            continue
        f = p.get("info") or {}
        if p.get("type") in ("createAccount", "createAccountWithSeed"):
            created.add(f.get("newAccount"))
        elif ins.get("program") == "system" and p.get("type") == "transfer" and f.get("source") in signers:
            tips[f.get("destination")] = tips.get(f.get("destination"), 0) + int(f.get("lamports") or 0)
        elif p.get("type") == "closeAccount" and f.get("destination"):
            closes.add(f["destination"])
    me = tx["meta"]; ti = {t["accountIndex"] for t in (me.get("preTokenBalances") or []) + (me.get("postTokenBalances") or [])}; got = {}
    for i, (a, b) in enumerate(zip(me["preBalances"], me["postBalances"])):
        if i < len(keys) and i not in ti and keys[i] != payer and keys[i] not in created and b - a - tips.get(keys[i], 0) > 0:
            got.setdefault(keys[i], {})["SOL"] = (b - a - tips.get(keys[i], 0)) / 1e9
    pt = {t["accountIndex"]: t for t in me.get("preTokenBalances") or []}
    for t in me.get("postTokenBalances") or []:
        a = float(t["uiTokenAmount"].get("uiAmount") or 0); b = float(((pt.get(t["accountIndex"]) or {}).get("uiTokenAmount") or {}).get("uiAmount") or 0)
        if a > b and t.get("owner") and t["owner"] != payer:
            got.setdefault(t["owner"], {})[t["mint"]] = a - b
    for d in closes:
        if d != payer:
            got.setdefault(d, {})
    return got


def is_claim(tx):
    return bool(tx) and not tx["meta"].get("err") and any("Instruction: ClaimPositionFee" in l for l in tx["meta"].get("logMessages") or [])


def scan_position(pos, creators, cto, samples, allc):
    """Fee recipients of one DAMM v2 position from its own txs: even sample + bisection at recipient switches (or all)."""
    s, comp = sigs_all(pos["position"], 20); s = [x for x in reversed(s) if not x.get("err")]
    n = len(s); pos["txs"] = n; pos["sigs_complete"] = comp; cache, lk = {}, threading.Lock()

    def at(i):
        with lk:
            if i in cache:
                return cache[i]
        tx = sol_tx(s[i]["signature"], "jsonParsed"); g = claim_recipients(tx) if is_claim(tx) else None
        v = (frozenset(g), g, tx) if g is not None else (None, None, tx)
        with lk:
            cache[i] = v
        return v
    if not n:
        pos.update(claims_read=0, recipients={}, switches=[], mode="no txs"); return pos
    k = max(2, min(samples, n))
    idx = list(range(n)) if allc else sorted({round(j * (n - 1) / (k - 1)) for j in range(k)})
    with cf.ThreadPoolExecutor(4) as ex:
        list(ex.map(at, idx))
    pts = {i for i in idx if at(i)[0] is not None}
    if not allc:
        for rg in (range(n), range(n - 1, -1, -1)):
            for pr, i in enumerate(rg):
                if pr > 25:
                    break
                if at(i)[0] is not None:
                    pts.add(i); break

        def near(lo, hi):
            m = (lo + hi) // 2
            for d in range(20):
                for j in (m + d, m - d):
                    if lo < j < hi and at(j)[0] is not None:
                        return j
        o = sorted(pts); st = [(o[j], o[j + 1]) for j in range(len(o) - 1) if at(o[j])[0] != at(o[j + 1])[0]]
        while st:
            lo, hi = st.pop()
            m = near(lo, hi) if hi - lo > 1 else None
            if m is None:
                continue
            pts.add(m)
            if at(m)[0] != at(lo)[0]:
                st.append((lo, m))
            if at(m)[0] != at(hi)[0]:
                st.append((m, hi))
    pos["created_by_migration"] = any("MigrationDammV2" in l for l in ((at(0)[2] or {}).get("meta") or {}).get("logMessages") or [])
    seen = sorted(i for i in pts if at(i)[0] is not None); rec, sw, prev = {}, [], None
    for i in seen:
        rs, g, tx = at(i); t = et(ts=tx["blockTime"])
        for w in rs:
            e = rec.setdefault(w, {"class": classify(w, creators, cto, pos.get("holder")), "claims_read": 0, "sol_in_claims_read": 0.0, "first_seen": t})
            e["claims_read"] += 1; e["sol_in_claims_read"] = round(e["sol_in_claims_read"] + (g.get(w) or {}).get("SOL", 0.0), 4); e["last_seen"] = t
        if prev is not None and rs != prev:
            sw.append({"time": t, "tx": s[i]["signature"], "from": sorted(prev), "to": sorted(rs)})
        prev = rs
    unread = sum(1 for v in cache.values() if v[2] is None)
    if unread:
        pos["txs_unreadable"] = unread
    pos.update(claims_read=len(seen), recipients=rec, switches=sw,
               mode="all position txs read" if allc else f"{len(cache)} of {n} position txs read (sample + bisection)")
    return pos


def damm(mint, creators, cto, samples, allc, ex):
    """DAMM v2 pools holding the mint; only pools with a creator/partner position (the migration pool) are scanned."""
    pools = [a["pubkey"] for off in (168, 200) for a in gpa(DAMM, 1112, off, mint, {"offset": 0, "length": 0})]; out = []
    for p in dict.fromkeys(pools):
        poss = []
        for a in gpa(DAMM, 408, 8, p, {"offset": 0, "length": 200}):
            b = base64.b64decode(a["account"]["data"][0]); nft = b58e(b[40:72])
            poss.append({"position": a["pubkey"], "nft_mint": nft, "nft_account": pda([b"position_nft_account", b58d(nft)], DAMM),
                         "liquidity": {k: str(int.from_bytes(b[o:o + 16], "little")) for k, o in (("unlocked", 152), ("vested", 168), ("permanently_locked", 184))}})
        if poss:
            for x, acc in zip(poss, sol("getMultipleAccounts", [[x["nft_account"] for x in poss], {"encoding": "jsonParsed"}])["value"]):
                try:
                    x["holder"] = acc["data"]["parsed"]["info"]["owner"]
                except Exception:
                    x["holder"] = None
                hc = classify(x["holder"], creators, cto) if x["holder"] else "unknown"
                x["holder_class"] = "outside LP" if hc.startswith("REDIRECT") else hc
        if not [x for x in poss if x.get("holder") in creators | {PARTNER}]:
            out.append({"pool": p, "migration_pool": False, "positions": len(poss)}); continue
        out.append({"pool": p, "migration_pool": True, "positions": list(ex.map(lambda x: scan_position(x, creators, cto, samples, allc), poss))})
    return out


def find_transfers(pool, old, cur):
    """TransferPoolCreator txs: only txs in both the pool's and the old/new creator's signature lists are read."""
    ps, pc = sigs_all(pool, 20); pset = {x["signature"]: x for x in ps if not x.get("err")}; found, read = {}, 0
    for who in dict.fromkeys([old, cur]):
        for x in sorted((pset[y["signature"]] for y in sigs_all(who, 5)[0] if y["signature"] in pset), key=lambda x: x.get("blockTime") or 0)[:40]:
            if x["signature"] in found:
                continue
            tx = sol_tx(x["signature"]); read += 1
            if not tx or not any("Instruction: TransferPoolCreator" in l for l in tx["meta"].get("logMessages") or []):
                continue
            k = keys_of(tx)
            for ix in tx["transaction"]["message"]["instructions"]:
                acc = [k[i] for i in ix["accounts"]]
                if k[ix["programIdIndex"]] == DBC and acc and acc[0] == pool and len(acc) > 3:
                    found[x["signature"]] = {"tx": x["signature"], "time": et(ts=tx.get("blockTime")), "bt": tx.get("blockTime") or 0,
                                             "from": acc[2], "to": acc[3], "fee_payer": k[0]}
        ch = sorted(found.values(), key=lambda f: f["bt"])
        if ch and ch[0]["from"] == old and ch[-1]["to"] == cur:
            break
    ch = sorted(found.values(), key=lambda f: f["bt"])
    ok = bool(ch) and ch[0]["from"] == old and ch[-1]["to"] == cur and all(ch[i]["to"] == ch[i + 1]["from"] for i in range(len(ch) - 1))
    return {"transfers": ch, "chain_complete": ok, "pool_txs": len(ps), "pool_sigs_complete": pc, "txs_read": read}


# ---------------------------------------------------------------- tracer
class Tracer:
    def __init__(s, a, recs):
        s.a, s.recs, s.ex = a, recs, cf.ThreadPoolExecutor(12); s.pf = Portfolios(recs, s.ex)

    def sol_creator(s, addr, rec, fpool, res):
        pools = fpool.result(); cr = {}
        if not pools:
            res["flags"].append("no Meteora DBC pool for this mint (not an anoncoin Solana launch?)"); return cr
        p = pools[0]; cr.update(pool=p["pool"], config=p["config"], current=p["creator"]); h = rec and rec.get("txHash"); c = name = tx = None
        uid = rec and rec.get("userId")
        if h:
            tx = sol_tx(h); c, name = parse_init(tx, addr, uid)
            if c:
                cr["creation_tx"], cr["creation_tx_source"] = h, "record txHash, verified on-chain as this mint's InitializeVirtualPool"
        if not c:
            ps, comp = sigs_all(p["pool"], 30)
            o = ps[-1]["signature"] if ps else None; tx = sol_tx(o) if o else None; c, name = parse_init(tx, addr, uid)
            cr["creation_tx"], cr["creation_tx_source"] = o, "DBC pool's oldest signature" + ("" if comp else " (walk capped)")
        cr.update(creation_creator=c, creation_ix=name, creation_block_time=tx and tx.get("blockTime"), transferred=bool(c and c != p["creator"]),
                  creator=p["creator"], evidence=f"ON-CHAIN: current Meteora DBC pool creator (pool {p['pool']}, bytes 104-136)")
        if cr["transferred"]:
            res["flags"].append(f"creator role TRANSFERRED: creation creator {c} (account 2 of {name}, tx {cr['creation_tx']}) != current pool creator {p['creator']}")
        if c is None:
            res["flags"].append("creation creator not verified (no InitializeVirtualPool found)")
        if p["creator"] in EXCL_SOL or p["creator"] in LEARNED["solana"]:
            cr["platform_creator"] = True
            res["flags"].append(f"PLATFORM CREATOR: current pool creator {p['creator']} is a known or auto-detected platform wallet")
        else:
            L.creator("solana", p["creator"])
        if rec and rec.get("walletAddress") and rec["walletAddress"] != p["creator"]:
            res["flags"].append(f"record walletAddress {rec['walletAddress']} != current pool creator {p['creator']}")
        if len(pools) > 1:
            res["flags"].append(f"{len(pools)} DBC pools for this mint; used {p['pool']}")
        return cr

    def rh_creator(s, addr, rec, res):
        cr = {}; h, how = (rec["txHash"], "record txHash") if rec and rec.get("txHash") else creation_tx(addr)
        if not h:
            res["flags"].append("launch tx not found"); return cr
        rc = receipt(h)
        try:
            FS.sync()   # learned fee-share wallets must be known before the creator is picked
        except Exception as e:
            res["notes"].append(f"fee-split sync failed: {e}")
        c, np_, bens, tok, shape, lr, fb = split_of(rc, rec and rec.get("userId")); tot = sum(x for _, x in bens) or 1
        cr.update(launch_tx=h, launch_tx_source=how, shape=shape, fee_split=[[x.lower(), y] for x, y in bens], non_platform=np_, creator=c,
                  launch_block_time=block_ts(rc["blockNumber"]),
                  evidence="ON-CHAIN: the only non-platform beneficiary of fee-split event 0x0c90f8fc… from fee contract 0x5f9e…3215 (address-sorted)")
        if c:
            cr["creator_share_pct"] = round(100 * dict((x.lower(), y) for x, y in bens)[c] / tot, 2); cr["creator_position"] = [x.lower() for x, _ in bens].index(c)
        if lr and not fb:
            res["flags"].append(f"auto-detected platform wallet(s) {lr} excluded from the fee split before picking the creator")
        if fb:
            cr["platform_creator"] = True
            res["flags"].append(f"PLATFORM CREATOR: only auto-detected platform wallet(s) {np_} remain in the fee split; creator not reliable")
        if len(np_) != 1:
            res["flags"].append(f"fee split has {len(np_)} non-platform beneficiaries {np_}; creator not unique, check manually")
        if tok and tok != addr:
            res["flags"].append(f"launch tx {h} created {tok}, not this token")
        if (rc.get("to") or "").lower() == ENTRY:
            us = userop_senders(rc, addr)
            if us:
                cr["userop_sender"] = us[0]
                if c and us[0] != c:
                    res["flags"].append(f"userOp sender {us[0]} != fee-split creator {c}")
        if rec and rec.get("creatorAddress") and c and rec["creatorAddress"].lower() != c:
            res["flags"].append(f"record creatorAddress {rec['creatorAddress']} != fee-split creator {c}")
        if rec and not rec.get("creatorAddress"):
            res["notes"].append("record has no creatorAddress; creator taken from the launch tx's fee split")
        return cr

    def quick(s, addr):
        t0 = time.time(); a = s.a
        res = {"input": addr, "chain": "robinhood" if EVM.match(addr) else "solana", "flags": [], "notes": [], "timings": {}}
        if res["chain"] == "robinhood":
            addr = res["input"] = addr.lower()
        elif not is_sol(addr):
            res["error"] = "neither a 0x Robinhood address nor a base58 Solana address"; return res
        frec = s.ex.submit(s.recs.lookup, addr)
        fpool = s.ex.submit(pool_of_mint, addr) if res["chain"] == "solana" else None
        s.ex.submit(FS.sync)
        rec = frec.result(); res["timings"]["record"] = round(time.time() - t0, 1)
        if not rec:
            res["notes"].append("no anoncoin record via the public single-coin lookup (not an anoncoin coin?)")
        res["record"] = rec and {k: rec.get(k) for k in ("name", "symbol", "userId", "userName", "walletAddress", "devWalletAddress", "creatorAddress", "txHash",
                                                          "ctoWallet", "ctoIsDefaultCreator", "ctoUpdatedOn", "ctoWinnerFeeSol", "ctoElectionActive", "prevUserId",
                                                          "royaltySharesPresent", "isMigrated", "sourceMint", "migrationRole", "destination", "image")}
        cr = res["creator"] = s.sol_creator(addr, rec, fpool, res) if res["chain"] == "solana" else s.rh_creator(addr, rec, res)
        res["timings"]["creator"] = round(time.time() - t0, 1)
        ff = s.ex.submit(sol_funding if res["chain"] == "solana" else rh_funding, cr["creator"]) if cr.get("creator") and not a.no_funding else None
        if rec and rec.get("userId"):
            pf = s.pf.get(rec["userId"]); coins = list(pf["coins"].values())
            wallets = {r["walletAddress"] for r in coins if r.get("walletAddress")}
            fl = [s.ex.submit(s.recs.lookup, r["address"]) for r in coins]
            fo = [s.ex.submit(coin_onchain, r, wallets) for r in coins if r["chain"] == "solana" or not r.get("blockTime")]
            notes, flags = list(pf["notes"]), list(pf["flags"])
            for f in fo:
                n, x = f.result(); notes += n; flags += x
            fresh = {r["address"].lower(): r for r in (f.result() for f in fl) if r}; out = []
            for r in coins:
                c = dict(r); fr = fresh.get(r["address"].lower())
                if fr:
                    for k in ("ctoWallet", "ctoIsDefaultCreator", "ctoUpdatedOn", "ctoElectionId", "ctoWinnerFeeSol", "isMigrated", "prevUserId", "sourceMint",
                              "migrationRole", "destination", "royaltySharesPresent", "ctoElectionActive", "mcapError", "image"):
                        c[k] = fr.get(k, c.get(k))
                    c.update({k: v for k, v in fr.items() if k.startswith(("mcap", "ath"))})
                else:
                    c["mcapError"] = "single-coin lookup failed"
                ath_merge(c)
                if c["chain"] == "solana" and (c.get("destination") or c.get("migrationRole")) and not c.get("foundVia"):
                    c["foundVia"] = "robinhoodMigration source (migration-campaign coins are left out of the public feed)"
                c["explorer"] = f"{BS}/token/{c['address'].lower()}" if c["chain"] == "robinhood" else f"https://solscan.io/token/{c['address']}"
                c["onchainEvidence"] = pf["confirmed"].get(r["address"].lower()); out.append(c)
            notes += dexscreener(out)
            res["portfolio"] = {"coins": out, "notes": list(dict.fromkeys(notes)), "flags": list(dict.fromkeys(flags)), "build_secs": pf["secs"]}
        if ff:
            try:
                res["funding"] = ff.result()
            except Exception as e:
                res["funding"] = {"wallet": cr.get("creator"), "result": f"funding lookup failed: {str(e)[:120]}"}
        tg = []
        if rec:
            if rec.get("ctoWallet") or rec.get("ctoWinnerFeeSol") or rec.get("ctoIsDefaultCreator") is False:
                tg.append("CTO in record")
            if rec.get("prevUserId"):
                tg.append("royalty.prevUserId in record")
            if rec.get("sourceMint") or rec.get("migrationRole") or rec.get("destination"):
                tg.append("robinhoodMigration in record")
        if cr.get("transferred"):
            tg.append("pool creator != creation creator (transfer)")
        if a.deep:
            tg.append("--deep")
        res["deep_triggers"] = tg; res["timings"]["quick_total"] = round(time.time() - t0, 1)
        return res

    def deep(s, res):
        t0 = time.time(); d = {}; rec = s.recs.fresh.get(res["input"].lower()) or {}; cr = res.get("creator") or {}
        if res["chain"] == "solana" and cr.get("pool"):
            cs = {x for x in (cr.get("current"), rec.get("walletAddress")) if x}
            if cr.get("creation_creator") and cr["creation_creator"] != cr.get("current"):
                try:
                    d["transfer"] = find_transfers(cr["pool"], cr["creation_creator"], cr["current"])
                except Exception as e:
                    d["transfer"] = {"error": str(e)[:200]}
            try:
                d["damm_v2"] = damm(res["input"], cs, rec.get("ctoWallet"), s.a.claim_samples, s.a.all_claims, s.ex)
            except Exception as e:
                d["damm_v2"] = {"error": str(e)[:200]}
        if res["chain"] == "robinhood" and rec.get("sourceMint"):
            src = rec["sourceMint"]
            try:
                ps = pool_of_mint(src); sr = s.recs.lookup(src)
                d["migration_source"] = {"sourceMint": src, "dbc_creator": ps[0]["creator"] if ps else None, "record_userName": sr and sr.get("userName"),
                                         "same_account": bool(sr and sr.get("userId") == rec.get("userId"))}
            except Exception as e:
                d["migration_source"] = {"error": str(e)[:200]}
        d["secs"] = round(time.time() - t0, 1)
        return d


# ---------------------------------------------------------------- output
def usd(v):
    return None if v is None else f"${v / 1e6:,.2f}M" if v >= 1e6 else f"${v / 1e3:,.1f}k" if v >= 1e3 else f"${v:,.0f}"


def mcap_cells(c):
    if c.get("mcapUsd") is not None:
        now = usd(c["mcapUsd"]) + " (anoncoin"; vt = c.get("mcapValuationTime")
        if vt and time.time() * 1000 - vt > 86400e3:
            now += f", last trade {et(ts=vt / 1000)[:10]}"
        now += (", provisional" if c.get("mcapProvisional") else "") + (", price stale" if c.get("mcapPriceStale") else "") + ")"
        if c.get("dsMcapUsd") is not None:
            now += f"; DexScreener {usd(c['dsMcapUsd'])}"
    elif c.get("dsMcapUsd") is not None:
        now = usd(c["dsMcapUsd"]) + " (DexScreener; anoncoin record has none)"
    else:
        now = "— (" + (c.get("mcapError") or "no anoncoin valuation" + ("; not on DexScreener" if c["chain"] == "solana" else "; no public DEX index prices it")) + ")"
    if c.get("mcapAthUsd") is not None:
        ath = usd(c["mcapAthUsd"]) + " (anoncoin"
        if c.get("athAt"):
            ath += f", {et(iso=c['athAt'])[:10]}"
        elif c.get("athBucketStart") and c.get("athBucketSeconds"):
            ath += f", {int(c['athBucketSeconds']) // 86400}-day bucket from {et(ts=c['athBucketStart'] / 1000)[:10]}"
        ath += (", history incomplete" if c.get("athComplete") is False else "") + (", legacy marketCapATH" if c.get("mcapAthSource") == "token.marketCapATH" else "")
        ath += (", cached" + (f" {et(ts=c['athCachedAt'])[:10]}" if c.get("athCachedAt") else "") if c.get("athCached") else "") + ")"
    else:
        ath = "— (" + (c.get("mcapError") or "no ATH in anoncoin record") + ")"
    return now, ath


def tsof(c):
    if c.get("blockTime"):
        return c["blockTime"]
    try:
        return dt.datetime.fromisoformat((c.get("createdAt") or "").replace("Z", "+00:00")).timestamp()
    except Exception:
        return 0


def md_table(res):
    coins = res["portfolio"]["coins"]; ws = {c["walletAddress"] for c in coins if c.get("walletAddress")}; bt = any(c.get("blockTime") for c in coins)
    L_ = ["| Token | Chain | Created (UTC) | Mcap now | ATH mcap | Note | Link |", "|---|---|---|---|---|---|---|"]
    for ch, title, link in (("robinhood", "Robinhood Chain", "Blockscout"), ("solana", "Solana", "Solscan")):
        for c in sorted([c for c in coins if c["chain"] == ch], key=tsof):
            n = []
            if c.get("ctoWallet"):
                n.append(f"CTO fees → {short(c['ctoWallet'])}")
            if c.get("creationCreator") and c["creationCreator"] not in ws:
                n.append(f"creator moved from {short(c['creationCreator'])}")
            if c.get("foundVia"):
                n.append("not in public feed")
            if c["address"].lower() == res["input"].lower():
                n.append("**token you asked about**")
            when = et(ts=c["blockTime"]) if c.get("blockTime") else et(iso=c["createdAt"]) + (" *record*" if bt else "")
            L_.append(f"| {c['name']} ({c['symbol']}) | {title} | {when} | {' | '.join(mcap_cells(c))} | {'; '.join(n)} | [{link}]({c['explorer']}) |")
    return "\n".join(L_) + f"\n\n<!-- generated by tracer.py {et(ts=time.time())} -->\n"


def card(res):
    """Pre-filled values for the locked result layout (plain text)."""
    rec = res.get("record") or {}; cr = res.get("creator") or {}; coins = (res.get("portfolio") or {}).get("coins") or []
    CH = {"solana": "Solana", "robinhood": "Robinhood"}; inp = res["input"].lower()
    me = next((c for c in coins if c["address"].lower() == inp), {})
    bt = cr.get("creation_block_time") or cr.get("launch_block_time") or me.get("blockTime")
    fmt = lambda t, y=True: dt.datetime.fromtimestamp(t, dt.timezone.utc).strftime("%b %-d, %Y, %H:%M UTC" if y else "%b %-d")
    flags = list(dict.fromkeys(res["flags"] + (res.get("portfolio") or {}).get("flags", [])))
    doubt = [f for f in flags if not f.startswith("creator role TRANSFERRED")]
    unconf = [c["symbol"] for c in coins if not c.get("onchainEvidence")]
    if not cr.get("creator") or cr.get("platform_creator") or not rec:
        conf = "Low"; why = ("creator not determined on-chain" if not cr.get("creator") else
                             "resolved creator is a known or auto-detected platform wallet" if cr.get("platform_creator") else "no anoncoin record")
    elif doubt or unconf or cr.get("transferred"):
        conf = "Medium"; why = "; ".join(x for x in (f"{len(unconf)} token(s) only platform-record: {', '.join(unconf[:8])}" if unconf else "",
                                                     "creator role transferred" if cr.get("transferred") else "", "flags need review" if doubt else "") if x)
    else:
        conf, why = "High", "creator and every listed token confirmed on-chain"
    sol_w = sorted({c["walletAddress"] for c in coins if c.get("walletAddress")} or ({rec["walletAddress"]} if rec.get("walletAddress") else set()))
    rh_w = sorted({(c.get("creatorAddressOnchain") or c.get("creatorAddress") or "").lower() for c in coins if c["chain"] == "robinhood"} - {""})
    if res["chain"] == "robinhood" and cr.get("creator") and cr["creator"] not in rh_w:
        rh_w.append(cr["creator"])
    on = {c["creatorAddressOnchain"] for c in coins if c.get("creatorAddressOnchain")} | {cr.get("creator"), cr.get("current")}
    on |= {c["onchainEvidence"].rsplit(" ", 1)[-1] for c in coins if (c.get("onchainEvidence") or "").startswith("ON-CHAIN: current Meteora")}
    lab = lambda w: f"{w} ({'on-chain' if w in on else 'platform record'})"
    f = res.get("funding") or {}
    fund = (f"first incoming {f.get('amount')} {f.get('unit')} from {f['sender']} ({f.get('sender_flag')}) on {f.get('time')}, tx {f.get('tx')}" if f.get("sender")
            else (f.get("result") or "not checked") + (f" ({f['note']})" if f.get("note") else ""))
    ct = []
    if rec.get("ctoWallet") or rec.get("ctoWinnerFeeSol"):
        ct.append(f"CTO: creator fees go to CTO winner {rec.get('ctoWallet')} (platform record" + (f", since {et(iso=rec['ctoUpdatedOn'])}" if rec.get("ctoUpdatedOn") else "") + "); creator unchanged")
    d = res.get("deep") or {}; trs = (d.get("transfer") or {}).get("transfers") or []
    ct += [f"creator role transferred {t['from']} -> {t['to']} on {t['time']} (on-chain, tx {t['tx']})" for t in trs]
    if cr.get("transferred") and not trs:
        ct.append(f"creator role transferred from {cr.get('creation_creator')} to {cr.get('creator')} (on-chain; transfer tx not located)")
    red = sorted({w for pl in (d.get("damm_v2") if isinstance(d.get("damm_v2"), list) else []) if pl.get("migration_pool") for p in pl["positions"]
                  for w, e in (p.get("recipients") or {}).items() if e["class"].startswith(("REDIRECT", "CTO"))})
    unr = sum(p.get("txs_unreadable") or 0 for pl in (d.get("damm_v2") if isinstance(d.get("damm_v2"), list) else []) if isinstance(pl.get("positions"), list) for p in pl["positions"])
    if unr:
        flags = list(flags) + [f"{unr} DAMM v2 position tx(s) could not be read from the RPC; claim counts are a lower bound"]
    if red:
        ct.append(f"creator-fee claims redirected to {', '.join(red)} (on-chain, DAMM v2 position claims)")
    ct += [f"other token {c['symbol']}: CTO fees to {c['ctoWallet']} (platform record)" for c in coins if c.get("ctoWallet") and c["address"].lower() != inp]
    item = lambda c: f"{c['name']} (${c['symbol']}), {CH[c['chain']]}"
    now = lambda c: usd(c.get("mcapUsd")) or usd(c.get("dsMcapUsd")) or "n/a"
    top = sorted([c for c in coins if c.get("mcapAthUsd") is not None], key=lambda c: -c["mcapAthUsd"])[:5]
    return {"name": rec.get("name") or me.get("name"), "symbol": rec.get("symbol") or me.get("symbol"), "blockchain": CH.get(res["chain"]),
            "launched": fmt(bt) if bt else None, "contract": res["input"], "mcap_now": now(me) if me else "n/a",
            "ath": usd(me.get("mcapAthUsd")) or "n/a", "confidence": conf, "confidence_reason": why, "creator_username": rec.get("userName"),
            "robinhood_wallet": ", ".join(map(lab, rh_w)) or None, "solana_wallet": ", ".join(map(lab, sol_w)) or None,
            "funding": fund, "cto_or_transfer": "; ".join(ct) or "none found",
            "created_tokens": {"total": len(coins), "solana": sum(c["chain"] == "solana" for c in coins), "robinhood": sum(c["chain"] == "robinhood" for c in coins)},
            "top_aths": [f"{item(c)}, ATH {usd(c['mcapAthUsd'])}, now {now(c)}" for c in top],
            "latest_launches": [f"{item(c)}, {fmt(tsof(c), False) if tsof(c) else '?'}, now {now(c)}, ATH {usd(c.get('mcapAthUsd')) or 'n/a'}"
                                for c in sorted(coins, key=tsof, reverse=True)[:5]],
            "flags": flags, "md_file": res.get("md"), "image": res.get("image_file")}


def card_text(c):
    t = c["created_tokens"]
    L_ = [f"{c['name']} (${c['symbol']})", f"Blockchain: {c['blockchain']}", f"Launched: {c['launched']}", f"Contract: {c['contract']}", "",
          f"Mcap now: {c['mcap_now']}", f"ATH: {c['ath']}", f"Confidence: {c['confidence']} ({c['confidence_reason']})", "",
          f"Creator: {c['creator_username']}", f"Robinhood wallet: {c['robinhood_wallet']}", f"Solana wallet: {c['solana_wallet']}",
          f"Funding: {c['funding']}", f"CTO or creator transfer: {c['cto_or_transfer']}", "",
          f"Created tokens: {t['total']} ({t['solana']} on Solana, {t['robinhood']} on Robinhood)", "Top ATHs:"]
    L_ += [f"{i}. {x}" for i, x in enumerate(c["top_aths"], 1)] + ["Latest launches:"] + [f"{i}. {x}" for i, x in enumerate(c["latest_launches"], 1)]
    return "\n".join(L_ + [f"FLAG: {x}" for x in c["flags"]] + [f"md: {c['md_file']}  image: {c['image']}"])


def get_image(res, d):
    rec = res.get("record") or {}
    if not rec.get("image"):
        return
    os.makedirs(d, exist_ok=True); p = os.path.join(d, re.sub(r"[^A-Za-z0-9_-]", "_", rec.get("symbol") or res["input"][:8]) + ".png")
    try:
        with urllib.request.urlopen(urllib.request.Request(rec["image"], headers={"User-Agent": UA, "Referer": "https://anoncoin.it/"}), timeout=30) as r:
            b = r.read()
        if len(b) > 100:
            with open(p, "wb") as f:
                f.write(b)
            res["image_file"] = p
    except Exception as e:
        res["notes"].append(f"image download failed: {str(e)[:80]}")


def write_out(res, a, used):
    rec = res.get("record") or {}
    if res.get("portfolio") and a.md_dir:
        os.makedirs(a.md_dir, exist_ok=True); u = rec.get("userName") or rec.get("userId") or res["input"][:6]
        base = used.setdefault(res["input"], f"creator_{u}" + (f"_{res['input'][:6]}" if f"creator_{u}" in used.values() else ""))
        res["md"] = os.path.join(a.md_dir, base + ".md"); awrite(res["md"], md_table(res))
    res["card"] = card(res)
    if a.md_dir and a.json and res.get("md"):
        awrite(res["md"][:-3] + ".json", json.dumps(res, indent=1, default=str))


def main():
    global W, C, L
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("addrs", nargs="*", help="token addresses; none = only warm the caches (feed + fee splits)")
    ap.add_argument("--deep", action="store_true", help="always run the deep stage (Full scan)")
    ap.add_argument("--all-claims", action="store_true", help="deep: read every DAMM v2 position tx (Full scan)")
    ap.add_argument("--claim-samples", type=int, default=8)
    ap.add_argument("--md-dir"); ap.add_argument("--img", help="download the token image to DIR/<SYMBOL>.png")
    ap.add_argument("--json", action="store_true", help="stdout = one JSON object per token; text cards go to stderr")
    ap.add_argument("--no-funding", action="store_true"); ap.add_argument("--refresh", action="store_true")
    ap.add_argument("--max-age", type=int, default=300); ap.add_argument("--workers", type=int, default=4)
    ap.add_argument("--workdir", default=os.environ.get("ANON_TRACKER_DIR") or os.path.dirname(os.path.abspath(__file__)))
    ap.add_argument("--utc", action="store_true", help="accepted for compatibility (times are always UTC)")
    a = ap.parse_args(); W = os.path.abspath(a.workdir); os.makedirs(W, exist_ok=True); T0 = time.time()
    seed = load_platform(wpath("platform_wallets.json"))
    out = sys.stderr if a.json else sys.stdout

    def emit(x):
        with PL:
            print(x, file=out, flush=True)
    try:
        rows, how = refresh_feed(a.refresh, a.max_age)
    except Exception as e:
        rows, how = feed_rows(), f"refresh FAILED ({str(e)[:100]}); using the cache as is"
    emit(f"[feed] {len(rows)} Robinhood coins cached; {how}; {time.time() - T0:.1f}s")
    GUARD_EVM.update((r.get(k) or "").lower() for r in rows.values() for k in ("creatorAddress", "creatorAddressOnchain"))
    emit(f"[platform] {len(PLAT['solana'])} Solana + {len(PLAT['robinhood'])} Robinhood known wallets" + ("" if seed else " (no platform_wallets.json in the work dir; built-in list only)"))
    C = Cache(); L = Learn(); recs = Records(rows); tr = Tracer(a, recs)
    if not a.addrs:
        FS.sync(); L.save(); C.save()
        emit(f"[warm] caches ready in {time.time() - T0:.1f}s; auto-detected platform wallets: {sum(len(v) for v in L.wallets.values())}"); return
    addrs = list(dict.fromkeys(x.strip() for x in a.addrs if x.strip())); results, used = {}, {}
    outer = cf.ThreadPoolExecutor(max(1, min(a.workers, len(addrs)))); futs = {outer.submit(tr.quick, x): x for x in addrs}; dfut = {}
    for f in cf.as_completed(futs):
        x = futs[f]
        try:
            res = f.result()
        except Exception as e:
            res = {"input": x, "chain": "?", "error": f"{type(e).__name__}: {e}", "timings": {}, "flags": [], "notes": []}
        results[x] = res
        if res.get("deep_triggers"):
            dfut[outer.submit(tr.deep, res)] = x
    for f in cf.as_completed(dfut):
        res = results[dfut[f]]
        try:
            res["deep"] = f.result()
        except Exception as e:
            res["deep"] = {"error": f"{type(e).__name__}: {e}"}
        res["timings"]["deep"] = res["deep"].get("secs")
    outer.shutdown(); tr.ex.shutdown(wait=False)
    L.evaluate(GUARD_EVM | {r.get("walletAddress") for r in recs.rows.values()} | {(r.get("creatorAddress") or "").lower() for r in recs.rows.values()})
    try:
        L.save()
    except Exception as e:
        emit(f"[learn] save failed: {e}")
    lrn = {"threshold_distinct_creators": THRESH, "learned_this_scan": L.new, "new_platform_wallets_learned": bool(L.new),
           "total_auto_detected": sum(len(v) for v in L.wallets.values()), "file": L.p}
    for x in addrs:
        res = results[x]; res["platform_learning"] = lrn; res["timings"]["total"] = round(time.time() - T0, 1)
        if "error" in res:
            emit(f"ERROR {x}: {res['error']}")
        else:
            if a.img:
                get_image(res, a.img)
            try:
                write_out(res, a, used)
            except Exception as e:
                res["notes"].append(f"writing outputs failed: {type(e).__name__}: {e}")
            emit(card_text(res["card"]) + "\n")
        if a.json:
            with PL:
                print(json.dumps(res, default=str), flush=True)
    try:
        if recs.new:
            with FLock(wpath(".feed.lock")):
                rr = feed_rows(); rr.update({k: v for k, v in recs.new.items() if k not in rr}); feed_write(rr)
        C.save()
    except Exception as e:
        emit(f"[cache] save failed: {e}")
    emit(f"[done] {len(addrs)} token(s) in {time.time() - T0:.1f}s; fee-split sync {FS.secs}s; learned this scan: {len(L.new)}; requests: "
         + ", ".join(f"{k} {v}" for k, v in sorted(STATS.items())))


if __name__ == "__main__":
    main()
