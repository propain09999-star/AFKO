# repo-curator

Watches a downloads folder, classifies new files with a local Ollama
model, and routes them into curated git repos — creating a new repo
once enough related files pile up.

## Setup (Termux / proot-distro Ubuntu)

```bash
pip install requests pyyaml --break-system-packages
```

Edit `config.yaml`:
- `watch_dir` — folder to watch (e.g. `~/storage/downloads`)
- `repos_base` — where your local repos live
- `new_repo_threshold` — how many unmatched files on one topic before
  a new repo gets created automatically
- `require_confirmation` — keep `true` until you trust the classifier;
  it'll stage the file and ping your ntfy.sh topic instead of pushing
- `ntfy_topic` — your ntfy.sh topic name for confirmation pings

## Run

```bash
python watch_ingest.py
```

Runs forever, polling `watch_dir` every `poll_seconds`. Safe to kill
and restart — it tracks already-seen files in
`~/repo-curator-staging/seen.json`.

## How it decides where a file goes

1. `classify.py` sends the file's text + your existing repo names to
   Ollama, asking for a repo slug, one-line summary, and tags.
2. `router.py` checks if that slug matches an existing repo:
   - Yes → goes straight in.
   - No → counted in a staging tally. Once `new_repo_threshold` files
     land on the same new slug, `create_repo()` `git init`s a real
     repo for it.
3. `curate.py` moves the file into `<repo>/files/`, appends a line to
   `<repo>/INDEX.md` with date + summary + tags, then commits (and
   pushes, unless `require_confirmation` is on).

## Confirmation mode

With `require_confirmation: true`, curate.py stages the change and
sends an ntfy.sh push instead of auto-pushing. To confirm and push:

```bash
python curate.py --push ~/repos/<repo-slug>
```

## Notes

- Only plain-text-ish files (`.txt .md .csv .json .py .log`) get their
  content read for classification; everything else is classified by
  filename alone (still gets sorted, just with less context).
- tinyllama's 2048-token window means file content is truncated to
  ~4000 characters before classification — same truncation strategy
  as `local_chat.py`.
- Git push assumes your PAT/SSH auth is already set up per repo.
