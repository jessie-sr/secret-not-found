## Clone this repo to local
```bash
git clone https://github.com/jessie-sr/secret-not-found.git
```

## Clone the target public github repo to be scanned
```bash
git clone target-repo-url
cd target-repo
```

For example:
```bash
git clone https://github.com/yux-m/secret_not_found_test.git
cd secret_not_found_test
```

## Run the scan (at the directory one level higher than secret-not-found)
```bash 
bash secret-not-found/scan.sh
```

## (Optional) Trigger a *failing* push
```bash
echo "const STRIPE_KEY = 'sk_live_12345678901234567890abcd';" > leak.js
git add leak.js
git commit -m "intentional secret for test"
bash secret-not-found/scan.sh
```

The push should fail and you should see something like:
```
🚨  Secret(s) detected! Push blocked to protect your keys.

leak.js:1 [Stripe secret]
  const STRIPE_KEY = 'sk_live_12345678901234567890abcd';

leak.js:1 [High entropy]
  const STRIPE_KEY = 'sk_live_12345678901234567890abcd';

👉  Bypass (not recommended): git push --no-verify

❌ Secret scanner found potentially sensitive data. Push blocked.
error: failed to push some refs to 'https://github.com/yux-m/secret_not_found_test.git'
```
