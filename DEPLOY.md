# Deploy FCKTHEMUSIC to GitHub Pages (2 minutes)

## Quick Deploy

```bash
# 1. Create GitHub repo
gh repo create fckthemusic --public --source=. --push

# 2. Enable Pages
gh api repos/:owner/fckthemusic/pages -X POST -f source[branch]=main -f source[path]=/

# 3. Done! Live at: https://yourusername.github.io/fckthemusic/
```

## Manual (No CLI)

1. **Create repo** at github.com/new → name: `fckthemusic` → Public
2. **Upload files**: Drag `index.html` and `_config.yml` to repo
3. **Settings** → Pages → Source: "Deploy from branch" → `main` / `/ (root)` → Save
4. **Wait 1-2 min** → Green checkmark → Visit your URL

## Custom Domain (Optional)

1. Add `CNAME` file with your domain:
   ```
   fckthemusic.com
   ```
2. DNS: Add CNAME → `yourusername.github.io`
3. Repo Settings → Pages → Custom domain → Enter domain → Enforce HTTPS

## API Configuration

**Edit `index.html` line 12:**
```javascript
const API_BASE = 'https://your-api.up.railway.app'; // Your Railway/Render URL
```

**Or use relative paths** if hosting API on same domain.

## File Structure

```
fckthemusic/
├── index.html      # Main app (self-contained)
├── _config.yml     # GitHub Pages config
├── CNAME           # Optional custom domain
└── DEPLOY.md       # This file
```

## Features Built-In

- 📱 Mobile-first, PWA installable
- 🎵 Search + download MP3s
- 💾 Save to Files (iOS/Android)
- 🔔 Toast notifications
- 🌙 Dark theme, haptic feedback
- ⚡ Zero dependencies, single file
- 🔒 No tracking, no cookies

## Test Locally

```bash
# Python
python -m http.server 8000

# Node
npx serve .

# PHP
php -S localhost:8000
```
Open `http://localhost:8000` on phone (same WiFi) or use `ngrok http 8000` for HTTPS.