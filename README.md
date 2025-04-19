## Clone the repo
```bash
git clone any-public-github-repo-that-might-contain-secret
cd this-github-repo-project
```

## Install the run-scanner hook locally
```bash 
python3 secret-not-found/install.py   # copies hook → .git/hooks/run-scanner
```

You should see: ✅  Secret scanner installed!

## Trigger a *failing* push
```bash
echo "const STRIPE_KEY = 'sk_live_1234567890abcdef';" > leak.js
git add leak.js
git commit -m "intentional secret for test"
git push      # ← scanner runs
```
