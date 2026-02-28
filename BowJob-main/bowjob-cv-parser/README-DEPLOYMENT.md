# Deployment Guide - Free Platforms (No Credit Card Required)

This guide covers deploying the CV Parser API to free platforms that don't require a credit card.

## Option 1: Fly.io (RECOMMENDED)

**Why:** Best free tier, easy Docker deployment, 3 free apps

### Steps:

```bash
# 1. Install flyctl
curl -L https://fly.io/install.sh | sh

# 2. Login/signup
flyctl auth signup

# 3. Launch app
cd /path/to/CV-Parser
flyctl launch
# Say YES to copy configuration
# Say NO to PostgreSQL database
# Say NO to Redis
# Say YES to deploy now

# 4. Set API key
flyctl secrets set OPENAI_API_KEY="sk-proj-your-key-here"

# 5. Deploy
flyctl deploy

# 6. Get your URL
flyctl status
```

**Access your API:**
- API: `https://cv-parser-api.fly.dev`
- Docs: `https://cv-parser-api.fly.dev/docs`
- Health: `https://cv-parser-api.fly.dev/health`

---

## Option 2: Koyeb

**Why:** Simple UI, automatic deployments from GitHub

### Steps:

1. **Sign up:** https://app.koyeb.com (use GitHub)
2. **Create Service:**
   - Click "Create Web Service"
   - Select "GitHub" → Connect your repository
   - Build: Docker
   - Port: 8000
3. **Environment Variables:**
   - Add `OPENAI_API_KEY` with your key
4. **Deploy**

---

## Option 3: Hugging Face Spaces

**Why:** Perfect for AI/ML apps, unlimited public spaces

### Steps:

1. **Sign up:** https://huggingface.co
2. **Create Space:**
   - Go to https://huggingface.co/new-space
   - Name: `cv-parser-api`
   - SDK: Docker
   - Visibility: Public
3. **Push your code:**
   ```bash
   git remote add hf https://huggingface.co/spaces/YOUR_USERNAME/cv-parser-api
   git push hf main
   ```
4. **Add Secret:**
   - Space Settings → Repository secrets
   - Name: `OPENAI_API_KEY`
   - Value: Your API key

---

## Option 4: Deta Space

**Why:** Completely free, very easy to use

### Steps:

```bash
# 1. Install Space CLI
curl -fsSL https://get.deta.dev/space-cli.sh | sh

# 2. Login
space login

# 3. Create new project
space new

# 4. Set environment variable
space secrets set OPENAI_API_KEY="sk-proj-your-key-here"

# 5. Push and deploy
space push
```

---

## Comparison

| Platform | Free Tier | Requires Card? | Deployment | Best For |
|----------|-----------|----------------|------------|----------|
| **Fly.io** | 3 apps, 256MB RAM | ❌ No | CLI (easy) | Docker apps |
| **Koyeb** | 1 web service | ❌ No | UI (easiest) | GitHub deployments |
| **Hugging Face** | Unlimited public | ❌ No | Git push | AI/ML projects |
| **Deta Space** | Unlimited | ❌ No | CLI | Quick deploys |

---

## Recommended: Fly.io

Fly.io is recommended because:
- ✅ No credit card required
- ✅ Easy Docker deployment (you already have Dockerfile)
- ✅ 3 free apps (256MB RAM each)
- ✅ Automatic HTTPS
- ✅ Good documentation

---

## Testing Your Deployment

After deployment, test with:

```bash
# Replace with your deployed URL
curl https://your-app.fly.dev/health

# Test parsing
curl -X POST https://your-app.fly.dev/parse \
  -F "file=@path/to/cv.pdf"
```

---

## Troubleshooting

**App crashes on startup:**
- Make sure you set `OPENAI_API_KEY` environment variable
- Check logs: `flyctl logs` (Fly.io)

**Out of memory:**
- Reduce PDF file size
- Use a platform with more RAM (upgrade or use another free service)

**API key not working:**
- Verify the key is set correctly
- Use `flyctl secrets list` to check (Fly.io)
