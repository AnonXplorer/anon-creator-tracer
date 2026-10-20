# Anon Creator Tracer

Finds who created an anoncoin.it token (Solana or Robinhood Chain) at the wallet level, plus every other token that
creator account launched. It uses public data only: anoncoin's public API, the Solana and Robinhood public RPCs,
Blockscout and DexScreener. No API keys. One file, Python 3.9+ standard library only.

```bash
python3 tracer.py <contract> --utc --md-dir out --img out/img --json                      # Fast scan
python3 tracer.py <contract> --utc --md-dir out --img out/img --json --deep --all-claims  # Full scan
python3 tracer.py                                                                          # warm the caches only
```

Output: one JSON object per token on stdout. `card` has the values for the result layout; the rest is the full
evidence. The tool also writes `out/creator_<username>.md` (the token table only) and `out/img/<SYMBOL>.png`.

## Files
- `tracer.py`: the tracer.
- `platform_wallets.json`: the curated seed list of platform, relayer, program, launchpad-config, exchange and bridge
  wallets. If the file is missing, the tracer falls back to a built-in copy.

Runtime files in the work dir (the folder that holds tracer.py, or `--workdir`). These are local and never part of the repo:
- `learned_platform_wallets.json`: auto-detected platform wallets, with evidence. Do not overwrite it on updates.
- `feed_robinhood.jsonl`, `feed_state.json`, `cache.json`: caches. The first run takes about 1 minute longer while
  the Robinhood feed is paged.

## Method
- Solana: creator = the Meteora DBC pool `creator` (bytes 104-136), cross-checked with account 2 of
  InitializeVirtualPool. A creator-role transfer is reported.
- Robinhood: creator = the only non-platform beneficiary (~42.98%) of the anoncoin fee split. It is never the tx sender,
  the bundler or the migration operator 0x3412f1a0….
- Account coins: the Robinhood public feed by userId, plus DBC pools of the account's Solana wallet, plus fee splits
  naming its EVM wallet. Every on-chain hit is confirmed by the public record's userId.
- CTO fee recipients are reported separately. They never replace the creator.
- Auto-learning: a wallet that pays for, sends or signs launches, or takes a fee share, across launches of 3 or more
  distinct creator accounts is added as `platform (auto-detected)`. A wallet is never learned if it is a sole fee-split
  beneficiary, a record creator wallet, or a resolved pool creator. If the resolved creator matches a platform wallet,
  the result is flagged with Confidence Low.

Results identify wallets, not people.

## Pinned release and integrity
Bots should download from the tag, not from `main`, and check the SHA-256 of each file (listed in `SHA256SUMS`):
```bash
B=https://raw.githubusercontent.com/AnonXplorer/anon-creator-tracer/v1.0.0
curl -fsSLO $B/tracer.py && curl -fsSLO $B/platform_wallets.json && curl -fsSL $B/SHA256SUMS | sha256sum -c
```
Any change to `tracer.py` or `platform_wallets.json` needs a new tag and new hashes.

## License
MIT. See `LICENSE`.
