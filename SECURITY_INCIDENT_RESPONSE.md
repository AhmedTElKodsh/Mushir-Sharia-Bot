# 🚨 Security Incident Response - API Key Leak

**Date**: 2026-05-12  
**Status**: 🔴 ACTIVE - Immediate action required  
**Severity**: HIGH

---

## What Happened

Your **old Gemini API key** was accidentally committed to git and pushed to GitHub:
- Key: `AIzaSyBWy14J6SnLqmb2MHAmcT46sNV2ittDbLg`
- Repository: https://github.com/AhmedTElKodsh/Mushir-Sharia-Bot
- Files affected: `GEMINI_SETUP.md`, `HUGGINGFACE_DEPLOYMENT.md`
- Commits: e090ed6, 68e8e42

**Good news**: Your `.env` file was never committed (properly gitignored ✅)

---

## ⚡ IMMEDIATE ACTIONS (Do Now!)

### 1. Revoke the Leaked API Key (5 minutes)

**Google Gemini API Key:**
1. Go to: https://aistudio.google.com/apikey
2. Find key: `AIzaSyBWy14J6SnLqmb2MHAmcT46sNV2ittDbLg`
3. Click **Delete** or **Revoke**
4. Generate a new API key
5. Update your `.env` file with the new key

**Why this matters:** Anyone who cloned your repo can use this key to make API calls on your account, costing you money.

### 2. Check for Unauthorized Usage

1. Go to: https://console.cloud.google.com/apis/dashboard
2. Check recent API usage for unusual spikes
3. Look for requests you didn't make

### 3. Commit the Fix

The leaked key has been removed from `HUGGINGFACE_DEPLOYMENT.md`. Now commit and push:

```bash
git add HUGGINGFACE_DEPLOYMENT.md
git commit -m "security: remove leaked API key from documentation"
git push origin main
```

---

## 🔒 LONG-TERM ACTIONS (Do This Week)

### 1. Scrub Git History (Advanced)

The leaked key is still in git history. To completely remove it:

**Option A: BFG Repo-Cleaner (Recommended)**
```bash
# Install BFG
# Download from: https://rtyley.github.io/bfg-repo-cleaner/

# Clone a fresh copy
git clone --mirror https://github.com/AhmedTElKodsh/Mushir-Sharia-Bot.git

# Remove the key from all commits
java -jar bfg.jar --replace-text passwords.txt Mushir-Sharia-Bot.git

# Force push (WARNING: This rewrites history!)
cd Mushir-Sharia-Bot.git
git reflog expire --expire=now --all
git gc --prune=now --aggressive
git push --force
```

**Option B: git-filter-repo**
```bash
pip install git-filter-repo

git filter-repo --replace-text <(echo "AIzaSyBWy14J6SnLqmb2MHAmcT46sNV2ittDbLg==>REDACTED")
git push --force
```

⚠️ **WARNING**: Force pushing rewrites history. Coordinate with any collaborators first!

### 2. Set Up Secret Scanning

**GitHub Secret Scanning (Free for public repos):**
1. Go to: https://github.com/AhmedTElKodsh/Mushir-Sharia-Bot/settings/security_analysis
2. Enable "Secret scanning"
3. Enable "Push protection" (prevents future leaks)

**Pre-commit Hook:**
```bash
# Install pre-commit
pip install pre-commit

# Create .pre-commit-config.yaml
cat > .pre-commit-config.yaml << 'EOF'
repos:
  - repo: https://github.com/Yelp/detect-secrets
    rev: v1.4.0
    hooks:
      - id: detect-secrets
        args: ['--baseline', '.secrets.baseline']
EOF

# Install hooks
pre-commit install
```

### 3. Rotate All Secrets

Even though only the Gemini key was leaked, rotate everything as a precaution:

- ✅ Gemini API Key (already done)
- ⚠️ HuggingFace Token (starts with `hf_`)
  - Go to: https://huggingface.co/settings/tokens
  - Revoke and create new token
  - Update `.env`

---

## 📋 Prevention Checklist

### ✅ Already Done
- [x] `.env` is in `.gitignore`
- [x] `.env.example` has placeholder values
- [x] Removed leaked key from current files

### 🔲 To Do
- [ ] Revoke leaked Gemini API key
- [ ] Generate new Gemini API key
- [ ] Update `.env` with new key
- [ ] Check Google Cloud Console for unauthorized usage
- [ ] Commit and push the fix
- [ ] Enable GitHub secret scanning
- [ ] Set up pre-commit hooks
- [ ] Scrub git history (optional but recommended)
- [ ] Rotate HuggingFace token (precautionary)

---

## 🎓 Lessons Learned

### What Went Wrong
1. API key was hardcoded in documentation files (`GEMINI_SETUP.md`, `HUGGINGFACE_DEPLOYMENT.md`)
2. Files were committed without review
3. No pre-commit hooks to catch secrets

### Best Practices Going Forward

**1. Never Hardcode Secrets**
```markdown
# ❌ BAD
GEMINI_API_KEY=AIzaSyBWy14J6SnLqmb2MHAmcT46sNV2ittDbLg

# ✅ GOOD
GEMINI_API_KEY=your-api-key-here
```

**2. Use Placeholders in Documentation**
```markdown
# ✅ GOOD
Get your API key from: https://aistudio.google.com/apikey
Then add it to .env:
GEMINI_API_KEY=<your-key-here>
```

**3. Review Before Committing**
```bash
# Always check what you're committing
git diff --cached

# Look for patterns like "AIza", "sk-", "hf_"
git diff --cached | grep -E "(AIza|sk-|hf_|ghp_)"
```

**4. Use Environment Variables Everywhere**
```python
# ✅ GOOD
api_key = os.getenv("GEMINI_API_KEY")

# ❌ BAD
api_key = "AIzaSyBWy14J6SnLqmb2MHAmcT46sNV2ittDbLg"
```

---

## 📞 Support Resources

- **Google Cloud Security**: https://cloud.google.com/security-command-center
- **GitHub Security**: https://docs.github.com/en/code-security
- **OWASP Secrets Management**: https://cheatsheetseries.owasp.org/cheatsheets/Secrets_Management_Cheat_Sheet.html

---

## ✅ Resolution Checklist

Once you've completed all actions:

- [ ] Old API key revoked
- [ ] New API key generated and working
- [ ] No unauthorized usage detected
- [ ] Fix committed and pushed
- [ ] GitHub secret scanning enabled
- [ ] Pre-commit hooks installed
- [ ] Team notified (if applicable)
- [ ] This incident documented

**Sign off**: _________________  
**Date**: _________________

---

**Remember**: This is a learning opportunity. Everyone makes mistakes. The important thing is to respond quickly and put safeguards in place to prevent it from happening again.
