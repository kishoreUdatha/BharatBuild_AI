# CLI browser login — frontend handoff

`bharatbuild login --browser` starts a one-shot HTTP listener on
`127.0.0.1:<random port>` and opens:

```
https://bharatbuild.ai/login?cli_port=<port>&cli_state=<nonce>
```

The CLI half is implemented and tested (`src/api/browser-login.ts`). It waits
for the login page to hand the token back. **Until the patch below ships, the
flow times out after 3 minutes** — nothing is listening on the web side.

## What the login page must do

After a successful login, if `cli_port` is present in the query string, POST the
token to the loopback listener instead of (or in addition to) redirecting.

```ts
// frontend/src/app/login/page.tsx — after login succeeds and you hold the token

const params   = new URLSearchParams(window.location.search);
const cliPort  = params.get("cli_port");
const cliState = params.get("cli_state");

if (cliPort && cliState) {
  try {
    await fetch(`http://127.0.0.1:${cliPort}/callback`, {
      method:  "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        state:         cliState,          // REQUIRED — CLI rejects a mismatch
        token:         accessToken,       // whatever your login response calls it
        refresh_token: refreshToken,      // optional
        email:         user.email,        // optional
        name:          user.name,         // optional
        tier:          user.tier,         // optional
        user_id:       user.id,           // optional
      }),
    });
    // The CLI replies with a "you can close this tab" page; it also closes
    // itself after ~2s. Skip the usual dashboard redirect in CLI mode.
    return;
  } catch {
    // Loopback unreachable — fall through to the normal web redirect so the
    // user is still logged in on the website.
  }
}
```

### Notes

- **`state` is mandatory.** The CLI compares it with `timingSafeEqual` and
  returns 403 on a mismatch without ending its wait, so a wrong or forged nonce
  cannot authenticate a session. Verified by test.
- **Cross-origin is expected.** The page is on `https://bharatbuild.ai`, the
  listener on `http://127.0.0.1:<port>`. The CLI sends
  `Access-Control-Allow-Origin: *` and handles the `OPTIONS` preflight.
- Mixed content: a `fetch()` from HTTPS to `http://127.0.0.1` is explicitly
  allowed by browsers (loopback is a
  [potentially trustworthy origin](https://w3c.github.io/webappsec-secure-contexts/#is-origin-trustworthy)).
  This is the same mechanism `gh auth login` and `vercel login` use.
- A `GET /callback?state=…&token=…` fallback also works if the page can only
  redirect rather than `fetch`.

## Testing before deploy

Run the CLI with the URL printed instead of launched:

```
bharatbuild login --browser --no-browser-open
```

Copy the `cli_port` and `cli_state` from the printed URL, then simulate the page:

```bash
curl -X POST http://127.0.0.1:<port>/callback \
  -H 'Content-Type: application/json' \
  -d '{"state":"<state>","token":"<a real token>"}'
```

The CLI validates the token against `/api/v1/auth/me` before storing it, so a
junk token is rejected rather than silently saved.
