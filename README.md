## Clone the repo
git clone any-public-github-repo-that-might-contain-secret
cd this-github-repo-project

## Install the run-scanner hook locally
python secret-not-found/install.py   # copies hook → .git/hooks/run-scanner
# You should see: ✅  Secret scanner installed!

# 3) Trigger a *failing* push
echo "const STRIPE_KEY = 'sk_live_1234567890abcdef';" > leak.js
git add leak.js
git commit -m "intentional secret for test"
git push      # ← scanner runs

#  —— Expected output ——
# 🚨  Secret(s) detected! Push blocked to protect your keys.
# leak.js:1 [Stripe secret]
#   const STRIPE_KEY = 'sk_live_1234567890abcdef';
# ...

# 4) Bypass check (if you really need to)
git push --no-verify    # skips all Git hooks

# 5) Verify *passing* push
git rm leak.js && git commit -m "remove secret"
git push                # should succeed
