# 🚀 Mushir Sharia Bot - Quick Start Guide

**Your chatbot is LIVE and ready to use!**

---

## ⚡ Instant Access

### 🌐 Use the Chatbot Now

**Direct Link:** https://AElKodsh-mushir-sharia-bot.hf.space/chat

Just open the link and start asking questions about Islamic finance compliance!

---

## 🧪 Quick Verification (30 seconds)

Run this command to verify everything is working:

```bash
python scripts/verify_deployment.py
```

**Expected Output:**
```
✅ ALL CHECKS PASSED (4/4)
🎉 Deployment is fully operational!
```

---

## 💬 Example Queries to Try

### English Queries
1. "What are the requirements for Murabaha transactions?"
2. "Is investing in halal food companies permissible?"
3. "Explain the difference between Murabaha and Musharaka"
4. "What are the disclosure requirements for Islamic financial institutions?"

### Arabic Queries
1. "ما هي متطلبات معاملات المرابحة؟"
2. "هل يجوز الاستثمار في شركات الأغذية الحلال؟"

---

## 📊 Check Space Status

```bash
python scripts/check_hf_space.py
```

**What it checks:**
- ✅ Health endpoint
- ✅ Readiness endpoint
- ✅ Chat interface
- ✅ Local prerequisites

---

## 🧪 Test with API

### Using curl

```bash
curl -X POST https://AElKodsh-mushir-sharia-bot.hf.space/api/v1/query \
  -H "Content-Type: application/json" \
  -d '{
    "query": "What are the key requirements for Murabaha?",
    "context": {"disclaimer_acknowledged": true}
  }'
```

### Using Python

```python
import requests

response = requests.post(
    "https://AElKodsh-mushir-sharia-bot.hf.space/api/v1/query",
    json={
        "query": "What are the key requirements for Murabaha?",
        "context": {"disclaimer_acknowledged": True}
    }
)

print(response.json())
```

---

## 🔧 Troubleshooting

### Space Not Responding?

1. **Check if Space is sleeping:**
   - Visit: https://huggingface.co/spaces/AElKodsh/mushir-sharia-bot
   - Look for "Running" status
   - If sleeping, click to wake it up

2. **Check Space logs:**
   - Visit: https://huggingface.co/spaces/AElKodsh/mushir-sharia-bot/logs
   - Look for errors

3. **Run diagnostics:**
   ```bash
   python scripts/check_hf_space.py
   ```

### Getting Errors?

1. **Verify API key:**
   - Go to Space Settings → Repository Secrets
   - Ensure GEMINI_API_KEY is set

2. **Check Space status:**
   ```bash
   curl https://AElKodsh-mushir-sharia-bot.hf.space/health
   ```

3. **Review logs:**
   - Check Space logs for specific error messages

---

## 📚 Documentation

### Full Guides
- **Deployment Guide:** `HUGGINGFACE_DEPLOYMENT.md`
- **Status Report:** `DEPLOYMENT_STATUS.md`
- **Fixes Applied:** `FIXES_APPLIED.md`

### Scripts
- **Verify Deployment:** `scripts/verify_deployment.py`
- **Check Status:** `scripts/check_hf_space.py`
- **Test Queries:** `scripts/test_space_query.py`
- **Deploy Updates:** `scripts/deploy_to_hf.py`

---

## 🎯 Common Tasks

### Update the Deployment

```bash
# 1. Make your code changes locally
# 2. Test locally
# 3. Deploy to Space
python scripts/deploy_to_hf.py
```

### Monitor Performance

```bash
# Check health
curl https://AElKodsh-mushir-sharia-bot.hf.space/health

# Check readiness
curl https://AElKodsh-mushir-sharia-bot.hf.space/ready

# View metrics
curl https://AElKodsh-mushir-sharia-bot.hf.space/metrics
```

### Test New Features

```bash
# Run comprehensive tests
python scripts/verify_deployment.py

# Test specific queries
python scripts/test_space_query.py
```

---

## 🔗 Important Links

| Resource | URL |
|----------|-----|
| **Chat Interface** | https://AElKodsh-mushir-sharia-bot.hf.space/chat |
| **Space Dashboard** | https://huggingface.co/spaces/AElKodsh/mushir-sharia-bot |
| **Space Logs** | https://huggingface.co/spaces/AElKodsh/mushir-sharia-bot/logs |
| **Space Settings** | https://huggingface.co/spaces/AElKodsh/mushir-sharia-bot/settings |
| **Health Check** | https://AElKodsh-mushir-sharia-bot.hf.space/health |
| **API Docs** | https://AElKodsh-mushir-sharia-bot.hf.space/docs |

---

## 💡 Pro Tips

### 1. Keep Space Awake
- Free tier Spaces sleep after inactivity
- Visit the chat page regularly to keep it active
- Consider upgrading to paid tier for always-on

### 2. Monitor Usage
- Check Space logs daily
- Monitor API quota usage
- Track response times

### 3. Test Before Deploying
- Always test locally first
- Run verification scripts
- Check Space logs after deployment

### 4. Backup Important Data
- Keep local copy of vector database
- Backup corpus files
- Document configuration changes

---

## 🎉 You're All Set!

Your Mushir Sharia Bot is fully operational and ready to answer Islamic finance compliance questions!

**Start using it now:** https://AElKodsh-mushir-sharia-bot.hf.space/chat

---

**Questions or Issues?**
- Check `HUGGINGFACE_DEPLOYMENT.md` for detailed troubleshooting
- Review Space logs for specific errors
- Run `python scripts/check_hf_space.py` for diagnostics

**Happy Chatting! 🚀**
