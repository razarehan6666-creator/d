# Arifah Demo Website

A local, Instagram-inspired **independent demonstration**. It is not affiliated with Instagram and does not access Instagram or Google accounts.

## Requirements
- Python 3.10+
- pip

## Run locally (Windows PowerShell)

```powershell
cd arifah_demo
py -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
$env:SECRET_KEY = "replace-this-with-a-long-random-secret"
flask --app app init-db
flask --app app create-admin admin@example.com
flask --app app run
```

Open http://127.0.0.1:5000

On macOS/Linux, activate the environment with:
```bash
source .venv/bin/activate
```

## Fictional demo login
- Email: `annie@gmail.com` (fixed on the demo login page)
- Password: `DemoPass123!` (local test password only)

You can override the demo password before running `init-db` by setting `DEMO_PASSWORD`.

## Administrator
Create an admin with `flask --app app create-admin YOUR_EMAIL`. The command securely prompts for a password. Then visit `/admin/login`.

The dashboard shows demo-account metadata and login outcomes. It never records submitted passwords. It supports deleting the demo account and clearing activity records.

## Custom URL
The path `/` is the demo login page. A URL such as `/ARIFAH/` can be added by configuring a route or web-server rewrite if you control a domain. You cannot make the real `instagram.com` domain point to this app; only Instagram can control that domain. Use a domain you own, and label the page as a demo.

## Security notes
- Passwords are stored as Werkzeug password hashes, not plaintext.
- Login forms use CSRF protection.
- Session cookies are HTTP-only and SameSite=Lax.
- For HTTPS hosting, set `COOKIE_SECURE=1`, use a strong random `SECRET_KEY`, and configure HTTPS at the hosting provider.
- This starter is intended for local learning. Before public deployment, add rate limiting, backups, monitoring, and a production WSGI server.


## Deploy to Render

1. Upload this project to a GitHub repository.
2. In Render, choose **New + → Blueprint** and connect that repository.
3. Render reads `render.yaml` and creates the web service.
4. Set `DEMO_PASSWORD` in the Render environment settings to a new fictional demo password.
5. Deploy, then open the `onrender.com` URL shown by Render.

The first deploy creates the demo database and the fictional `annie@gmail.com` account. The default local password is used only if `DEMO_PASSWORD` is not configured; set your own value on Render.

**Important storage limitation:** This starter uses SQLite. Render's default filesystem for a web service is ephemeral, so SQLite data can be lost when the service is redeployed or restarted. For durable public use, attach a paid persistent disk and set `DATABASE_PATH` to a file on that disk, or migrate the app to a managed PostgreSQL database before relying on saved records.

The real `instagram.com` domain cannot be redirected by you. Use the Render URL or a custom domain that you own.
## Deploy to Render

1. Push this project folder to a GitHub repository.
2. In Render, choose **New + → Blueprint** and connect that repository.
3. Render reads `render.yaml` and prepares the web service.
4. Before creating/deploying, set these secret environment variables when prompted:
   - `DEMO_PASSWORD`: choose a fictional demo-only password.
   - `ADMIN_EMAIL`: choose your administrator email.
   - `ADMIN_PASSWORD`: choose a strong, unique administrator password.
5. Deploy. Render will provide a public `onrender.com` URL.

This Blueprint uses a persistent disk for the SQLite database, so it requires a Render service plan that supports persistent disks. Do not remove the disk if you want to keep the database. Use a domain you own for a custom URL; you cannot route the real instagram.com domain to this project.
