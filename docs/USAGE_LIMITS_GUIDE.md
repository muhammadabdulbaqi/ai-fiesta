# Usage Limits & What Happens at 100%

This guide explains what happens when you reach your token/credit limits (100% usage).

## Understanding Your Limits

Each subscription tier has two types of limits:

### 1. **Token Limits** (per month)
- **Free:** 5,000 tokens/month
- **Pro:** 100,000 tokens/month  
- **Enterprise:** 1,000,000 tokens/month

### 2. **Credit Limits** (per month)
- **Free:** 5,000 credits/month
- **Pro:** 50,000 credits/month
- **Enterprise:** 1,000,000 credits/month

## What Happens When You Reach 100%

### Scenario 1: Credits Reach 100% (Most Common)

**What happens:**
- ❌ **New chat requests are blocked** with error: `"Insufficient credits"` (HTTP 402)
- ✅ **You can still view** existing conversations
- ✅ **You can still browse** the interface
- ❌ **You cannot send new messages** until credits are added

**Error message you'll see:**
```
Insufficient credits
Need ~X credits
```

**How to fix:**
1. **Upgrade your subscription** (Pro or Enterprise get more credits)
2. **Wait for monthly reset** (credits reset at the start of each billing period)
3. **Admin can add credits** (if you have admin access)

### Scenario 2: Tokens Reach 100%

**What happens:**
- ⚠️ **Token limit is a soft limit** - it's tracked but doesn't block requests
- ✅ **You can still use the service** (credits are the hard limit)
- 📊 **Usage percentage shows 100%+** in the UI
- ⚠️ **Admin dashboard** will show you've exceeded your tier's token limit

**Note:** Tokens are tracked for reporting, but **credits are what actually block requests**.

## How Usage is Calculated

### Credit Usage Formula:
```
Credits Needed = (Estimated Tokens + Max Completion Tokens) × Model Credit Multiplier
```

**Example:**
- Prompt: ~500 tokens
- Max completion: 1000 tokens
- Model: GPT-4o (multiplier: 0.1)
- **Credits needed:** (500 + 1000) × 0.1 = **150 credits**

### Token Usage:
- Each request consumes tokens based on:
  - **Prompt tokens:** Length of your input
  - **Completion tokens:** Length of AI response
  - **Total tokens:** Sum of both

## Checking Your Usage

### In the Frontend:
1. **Sidebar:** Shows your subscription tier
2. **Admin Dashboard:** `/admin` shows detailed usage stats
3. **API Response:** Subscription endpoints return `percentage_used`

### Via API:
```bash
# Get your subscription info
GET /users/me/subscription
Authorization: Bearer <your-jwt-token>
```

Response includes:
```json
{
  "tier": "free",
  "tokens_used": 4500,
  "tokens_limit": 5000,
  "credits_remaining": 2000,
  "credits_limit": 5000,
  "percentage_used": 90.0
}
```

## What Happens During a Request

### Before Request:
1. ✅ System checks if you have enough credits
2. ✅ System checks if your subscription is active
3. ✅ System checks if the model is allowed for your tier

### If Credits Insufficient:
```python
# Backend code (chat.py)
if subscription.credits_remaining < needed:
    raise HTTPException(status_code=402, detail="Insufficient credits")
```

**Result:** Request is rejected **before** calling the AI provider (saves money!)

### If Credits Sufficient:
1. ✅ Request proceeds
2. ✅ AI provider is called
3. ✅ Response is streamed to you
4. ✅ Credits are deducted after successful completion
5. ✅ Tokens are tracked
6. ✅ Cost is recorded

## Monthly Reset

**When:** At the start of each billing period (typically monthly)

**What resets:**
- ✅ `tokens_used` → 0
- ✅ `credits_remaining` → `credits_limit` (full credits restored)
- ❌ `tokens_limit` and `credits_limit` stay the same (based on tier)

**Note:** The reset logic needs to be implemented (currently manual or via admin).

## Subscription Tiers Comparison

| Feature | Free | Pro | Enterprise |
|---------|------|-----|------------|
| **Tokens/Month** | 5,000 | 100,000 | 1,000,000 |
| **Credits/Month** | 5,000 | 50,000 | 1,000,000 |
| **Rate Limit** | 5/min | 60/min | 500/min |
| **Models** | 2 | 6 | All |
| **Cost** | $0 | $19.99 | $199.99 |

## Error Codes

### 402 Payment Required (Insufficient Credits)
```json
{
  "detail": "Insufficient credits"
}
```
**Action:** Upgrade subscription or wait for reset

### 403 Forbidden (Model Not Allowed)
```json
{
  "detail": "Model gpt-4o not allowed"
}
```
**Action:** Upgrade to a tier that includes this model

### 403 Forbidden (Inactive Subscription)
```json
{
  "detail": "Subscription inactive"
}
```
**Action:** Contact admin to activate subscription

## Best Practices

1. **Monitor Usage:** Check your usage percentage regularly
2. **Upgrade Early:** Don't wait until you hit 100% to upgrade
3. **Use Efficient Models:** Free tier models (Gemini Flash, GPT-3.5) use fewer credits
4. **Optimize Prompts:** Shorter prompts = fewer tokens = fewer credits

## Admin Actions

If you're an admin, you can:

1. **Add Credits:**
   ```bash
   POST /admin/subscriptions/{user_id}/add-credits
   Body: { "credits": 10000 }
   ```

2. **Upgrade Subscription:**
   ```bash
   POST /admin/subscriptions/{user_id}/upgrade
   Body: { "tier": "pro" }
   ```

3. **View All Usage:**
   ```bash
   GET /admin/usage
   ```

## FAQ

**Q: What if I'm at 99% and send a request that needs 2%?**
A: If you have enough credits, it will work. The system checks before processing.

**Q: Can I go over 100%?**
A: For tokens, yes (soft limit). For credits, no - requests are blocked.

**Q: Do credits reset automatically?**
A: Currently, reset logic needs to be implemented. Admins can manually reset or add credits.

**Q: What's the difference between tokens and credits?**
A: 
- **Tokens:** Actual AI model usage (tracked for reporting)
- **Credits:** Internal currency that blocks requests (hard limit)

**Q: Can I use multiple models in one request?**
A: Yes! Each model response consumes credits separately.

