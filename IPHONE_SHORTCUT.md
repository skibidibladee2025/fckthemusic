# iPhone Shortcut Setup for MP3Juice API

## Option 1: Manual Shortcut Creation (Recommended)

Create this shortcut in the **Shortcuts** app on your iPhone:

### Shortcut: "MP3Juice Search & Download"

**Actions (in order):**

1. **Ask for Input**
   - Type: Text
   - Prompt: "Enter song or artist name:"
   - Placeholder: "e.g., never gonna give you up"
   - Variable: `SearchQuery`

2. **Get Contents of URL** (Search)
   - URL: `https://YOUR_SERVER_URL/search`
   - Method: POST
   - Request Body: JSON
     ```json
     {
       "query": "SearchQuery",
       "max_results": 5
     }
     ```
   - Headers: `Content-Type: application/json`
   - Variable: `SearchResults`

3. **Get Dictionary Value** (Extract results array)
   - Key: `results`
   - From: `SearchResults`
   - Variable: `ResultsList`

4. **Choose from List**
   - List: `ResultsList`
   - Display: `title`
   - Select Multiple: Off
   - Variable: `SelectedSong`

5. **Get Dictionary Value** (Extract download URL)
   - Key: `download_url`
   - From: `SelectedSong`
   - Variable: `DownloadURL`

6. **Get Dictionary Value** (Extract title for filename)
   - Key: `title`
   - From: `SelectedSong`
   - Variable: `SongTitle`

7. **Get Contents of URL** (Download)
   - URL: `https://YOUR_SERVER_URL/download?url=DownloadURL&filename=SongTitle`
   - Method: GET
   - Variable: `MP3File`

8. **Save File**
   - File: `MP3File`
   - Location: Ask Where to Save
   - Overwrite: Ask

---

## Option 2: Quick Download Shortcut

### Shortcut: "MP3Juice Quick Download"

For when you already know the download URL (from search results).

**Actions:**

1. **Ask for Input**
   - Type: Text
   - Prompt: "Paste download URL:"
   - Variable: `DownloadURL`

2. **Ask for Input**
   - Type: Text
   - Prompt: "Filename (optional):"
   - Variable: `Filename`

3. **Get Contents of URL**
   - URL: `https://YOUR_SERVER_URL/download?url=DownloadURL&filename=Filename`
   - Method: GET
   - Variable: `MP3File`

4. **Save File**
   - File: `MP3File`
   - Location: Ask Where to Save

---

## Option 3: Share Sheet Shortcut (Best for Safari/YouTube)

### Shortcut: "Download from MP3Juice"

**Receiving:** URLs, Text

**Actions:**

1. **If** `ShortcutInput` contains "youtube.com" OR "youtu.be" OR "soundcloud.com"
   - **Get Contents of URL** (Extract video ID or pass directly)
   - **Run Shortcut**: "MP3Juice Search & Download" with query from URL

2. **Otherwise**
   - **Run Shortcut**: "MP3Juice Search & Download" with `ShortcutInput` as query

---

## Server URL Configuration

Replace `YOUR_SERVER_URL` with your deployed API URL:

| Platform | Example URL |
|----------|-------------|
| **Railway** | `https://mp3juice-api.up.railway.app` |
| **Render** | `https://mp3juice-api.onrender.com` |
| **Fly.io** | `https://mp3juice-api.fly.dev` |
| **Local (ngrok)** | `https://abc123.ngrok.io` |
| **Local (Tailscale)** | `http://your-machine.tailnet.ts.net:8000` |

---

## Free Hosting Options

### 1. Railway (Easiest - $5 credit/month free)
```bash
# Install Railway CLI
npm install -g @railway/cli

# Login and deploy
railway login
railway init
railway up
```
Or: Connect GitHub repo at railway.app → auto-deploys on push

### 2. Render (Free tier, spins down after inactivity)
1. Push code to GitHub
2. Connect repo at render.com
3. Select "Web Service" → Docker
4. Free plan: 750 hrs/month, auto-sleeps after 15 min inactivity

### 3. Fly.io (Free allowance: 3 shared-cpu VMs)
```bash
flyctl launch --dockerfile Dockerfile
flyctl deploy
```

### 4. Google Cloud Run (2M requests/month free)
```bash
gcloud run deploy mp3juice-api --source . --platform managed --region us-central1 --allow-unauthenticated
```

### 5. Local + ngrok (For testing only)
```bash
# Terminal 1: Run server
python server.py

# Terminal 2: Expose publicly
ngrok http 8000
# Copy the https://xxx.ngrok.io URL
```

---

## API Endpoints for Shortcuts

| Action | Endpoint | Method | Parameters |
|--------|----------|--------|------------|
| Search | `/search` | POST | `{ "query": "...", "max_results": 5 }` |
| Download | `/download` | GET | `?url=DOWNLOAD_URL&filename=NAME` |
| Health | `/health` | GET | - |

**Search Response:**
```json
{
  "query": "...",
  "total_results": 4,
  "results": [
    {
      "index": 1,
      "title": "Song Name",
      "source": "YouTube",
      "size_mb": "3.69MB",
      "duration": "00:04:02",
      "download_url": "https://...",
      "video_id": "dQw4w9WgXcQ"
    }
  ]
}
```

---

## Tips

- **Shortcut permissions**: Allow "Untrusted Shortcuts" in Settings → Shortcuts → Advanced
- **Background downloads**: Use "Get Contents of URL" with "Show More" → "Wait for Response"
- **Large files**: The server streams, but iOS shortcuts may timeout on very large files (>50MB)
- **Metadata**: MP3s include ID3 tags (title, artist from filename)

---

## Troubleshooting

| Issue | Fix |
|-------|-----|
| "Could not connect" | Check server URL, ensure HTTPS for production |
| "Timeout" | Increase timeout in shortcut, or use smaller max_results |
| "No results" | Try different search terms, check server logs |
| "File won't play" | Ensure downloading .mp3, not .html error page |

---

## Security Note

This API has no authentication. For personal use:
- Deploy on platform with IP allowlist (Railway, Fly.io support this)
- Or add simple API key header check in `server.py`
- Don't expose publicly without auth if concerned about abuse