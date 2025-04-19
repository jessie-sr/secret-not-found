Assuming we are outside the directory secret-not-found

## Clone the public github repo that might contain secret
```bash
git clone target-repo-url
cd target-repo
```

For example:
```bash
git clone https://github.com/yux-m/secret_not_found_test.git
cd secret_not_found_test
````

(And now we have 2 directories under current directory: secret-not-found and target-repo)

## Install the run-scanner hook locally
```bash 
python3 ../secret-not-found/install.py   # copies hook → .git/hooks/run-scanner
```

You should see: ✅  Secret scanner installed!

## Trigger a *failing* push
```bash
echo "const STRIPE_KEY = 'sk_live_12345678901234567890abcd';" > leak.js
git add leak.js
git commit -m "intentional secret for test"
git push      # ← scanner runs
```
