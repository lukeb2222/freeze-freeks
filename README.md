# FREEZE FREEKS

Crunch Like a Freek.™ — site for the FREEZE FREEKS freeze-dried candy company.

Matte-black brand site with an email list ("The Freek List") and a contact form,
backed by a zero-dependency Python server. No e-commerce — customers reach out
to get candy.

## Run

```
python3 server.py
```

- Site: http://localhost:8787
- Admin dashboard (signups + candy requests): http://localhost:8787/admin

Signups land in `signups.json`, contact messages in `messages.json` (both
gitignored — customer data stays local).

## Real product photos

Drop photos into `public/img/` and they automatically replace the canvas-drawn
candy: `hero.jpg`, `skittles.jpg`, `jr-original.jpg`, `gummy-worms.jpg`,
`sour-patch-watermelon.jpg`.

## Note

`/admin` has no authentication — fine on localhost, add a login before hosting
publicly.
