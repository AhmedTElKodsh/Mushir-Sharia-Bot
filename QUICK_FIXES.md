# ⚡ Quick Fixes for Mushir Sharia Bot

**Priority**: CRITICAL  
**Time to implement**: 30 minutes

---

## 🔴 Issue #1: Gemini API 503/429 Errors

**Problem**: 67% of queries fail with "503 Service Unavailable" or "429 Too Many Requests"

**Root Cause**: 
- Free tier rate limit: 15 requests/minute
- Google's servers occasionally overloaded (503)
- No retry logic with proper backoff

**Quick Fix** (5 minutes):

Add exponential backoff with jitter to `src/chatbot/llm_client.py`:

```python
import random
import time

def generate(self, prompt: str) -> str:
    model = self._model or self._build_model()
    last_error = None
    
    for attempt in range(self.max_retries):
        try:
            response = model.generate_content(
                prompt,
                request_options={"timeout": self.timeout_seconds},
            )
            text = getattr(response, "text", None)
            if not text or not text.strip():
                raise LLMResponseError("Gemini returned an empty response")
            return text.strip()
            
        except LLMResponseError:
            raise
            
        except Exception as exc:
            last_error = exc
            error_str = str(exc).lower()
            
            # Check if it's a rate limit or service unavailable error
            if "503" in error_str or "429" in error_str or "quota" in error_str:
                if attempt < self.max_retries - 1:
                    # Exponential backoff with jitter
                    base_wait = 2 ** attempt
                    jitter = random.uniform(0, 1)
                    wait_time = base_wait + jitter
                    print(f"⏳ Gemini API error (attempt {attempt + 1}/{self.max_retries}). Waiting {wait_time:.1f}s...")
                    self._sleep(wait_time)
                    continue
                else:
                    raise LLMRateLimitError(f"Gemini quota or rate limit error after {self.max_retries} attempts: {exc}") from exc
            else:
                # Non-rate-limit error, fail fast
                raise LLMResponseError(f"Gemini generation failed: {exc}") from exc
    
    raise LLMResponseError(f"Gemini generation failed after {self.max_retries} attempts: {last_error}")
```

**Test**:
```bash
python -c "from src.chatbot.llm_client import GeminiClient; client = GeminiClient(); print(client.generate('Say hello'))"
```

---

## 🟡 Issue #2: No Logging

**Problem**: Can't debug issues without logs

**Quick Fix** (2 minutes):

Add to `src/api/main.py` (after imports):

```python
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/mushir.log'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)
```

Create logs directory:
```bash
mkdir logs
```

---

## 🟡 Issue #3: Corpus Coverage Unknown

**Problem**: Don't know if AAOIFI standards cover user queries

**Quick Fix** (3 minutes):

Test corpus coverage:

```bash
python -c "
import chromadb
client = chromadb.PersistentClient(path='./chroma_db_multilingual')
collection = client.get_collection('aaoifi_standards')
print(f'Total chunks: {collection.count()}')

# Test queries
queries = [
    'murabaha cost disclosure',
    'halal food investment',
    'Islamic finance equity',
    'Sharia compliant stocks'
]

for query in queries:
    results = collection.query(query_texts=[query], n_results=3)
    print(f'\nQuery: {query}')
    print(f'Top score: {results[\"distances\"][0][0]:.3f}')
    print(f'Sample: {results[\"documents\"][0][0][:100]}...')
"
```

---

## 🟢 Issue #4: Browser Interface Not Tested

**Problem**: Haven't verified the chat UI works

**Quick Fix** (5 minutes):

1. Open browser: http://127.0.0.1:8000/chat

2. Open browser console (F12)

3. Try this query:
   ```
   What does AAOIFI require for murabaha transactions?
   ```

4. Check for:
   - ✅ Query submits
   - ✅ "Thinking..." message appears
   - ✅ Response streams in
   - ✅ Citations appear
   - ✅ No JavaScript errors in console

5. If it fails:
   - Check server logs
   - Check browser console for errors
   - Try again (503 errors are intermittent)

---

## 🔧 Implementation Script

Run all fixes at once:

```bash
# 1. Add exponential backoff (manual edit required)
# Edit src/chatbot/llm_client.py and add the code above

# 2. Create logs directory
mkdir logs

# 3. Test corpus coverage
python -c "
import chromadb
client = chromadb.PersistentClient(path='./chroma_db_multilingual')
collection = client.get_collection('aaoifi_standards')
print(f'✅ ChromaDB connected: {collection.count()} chunks')
"

# 4. Test Gemini API
python -c "
from src.chatbot.llm_client import GeminiClient
client = GeminiClient()
try:
    response = client.generate('Say hello in one word')
    print(f'✅ Gemini API working: {response}')
except Exception as e:
    print(f'❌ Gemini API error: {e}')
"

# 5. Restart server
# Kill existing process and restart
taskkill /F /IM python.exe
python -m uvicorn src.api.main:app --reload

# 6. Test in browser
start http://127.0.0.1:8000/chat
```

---

## ✅ Success Criteria

After implementing these fixes:

- [ ] Gemini API success rate >80% (up from 33%)
- [ ] Logs directory created with mushir.log file
- [ ] Corpus coverage tested and documented
- [ ] Browser interface tested and working
- [ ] No JavaScript errors in browser console
- [ ] At least 3 successful queries in a row

---

## 📊 Expected Improvements

| Metric | Before | After | Improvement |
|--------|--------|-------|-------------|
| Query Success Rate | 33% | >80% | +47% |
| Average Retries | 0 | 1-2 | Better reliability |
| Debugging Capability | None | Full logs | Infinite |
| Browser Testing | Unknown | Verified | Known state |

---

## 🎯 Next Steps After Quick Fixes

1. **Monitor for 1 hour**
   - Watch logs for errors
   - Track success rate
   - Note any new issues

2. **Document findings**
   - Update BROWSER_TEST_RESULTS.md
   - Note any remaining issues
   - Plan next iteration

3. **Consider upgrades**
   - Gemini paid tier ($0.016/query)
   - Redis caching (reduce LLM calls)
   - Fallback LLM (OpenAI GPT-4)

---

**Time to implement**: 30 minutes  
**Expected impact**: High  
**Risk**: Low (all changes are additive)
