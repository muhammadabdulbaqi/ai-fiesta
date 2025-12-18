# Cost Calculation Guide

This guide explains how AI Fiesta calculates costs, tracks token usage, and manages user balances.

## Overview

AI Fiesta uses a dual-tracking system:
- **Tokens**: Direct token count from API providers
- **Credits**: Internal currency system for flexible pricing

## Token Calculation

### How Tokens Are Counted

1. **Input Tokens**: Tokens in the user's prompt/message
2. **Output Tokens**: Tokens in the AI model's response
3. **Total Tokens**: Sum of input + output tokens

Token counting is performed by each provider's API, which uses their own tokenization methods:
- OpenAI: Uses tiktoken
- Anthropic: Uses their proprietary tokenizer
- Gemini: Uses Google's tokenizer
- Grok/Perplexity: Uses their respective tokenizers

### Token Costs Per Model

Each model has different input and output token costs (per 1,000 tokens):

| Model | Input Cost (per 1k) | Output Cost (per 1k) |
|-------|---------------------|----------------------|
| GPT-4o-mini | $0.00015 | $0.0006 |
| GPT-3.5-turbo | $0.0005 | $0.0015 |
| GPT-4o | $0.005 | $0.015 |
| GPT-4-turbo | $0.01 | $0.03 |
| Claude 3 Haiku | $0.00025 | $0.00125 |
| Claude 3.5 Sonnet | $0.003 | $0.015 |
| Claude 3 Opus | $0.015 | $0.075 |
| Gemini 2.5 Flash | $0.0001 | $0.0004 |
| Gemini 2.5 Pro | $0.00125 | $0.00375 |
| Grok Beta | $0.001 | $0.003 |
| Perplexity Sonar | $0.0005 | $0.002 |

### Cost Calculation Formula

For each API call:
```
Cost = (Input Tokens / 1000) × Input Cost per 1k + (Output Tokens / 1000) × Output Cost per 1k
```

Example:
- Model: GPT-4o
- Input: 500 tokens
- Output: 1,000 tokens
- Cost = (500/1000) × $0.005 + (1000/1000) × $0.015 = $0.0025 + $0.015 = $0.0175

## Credit System

### Credit Multiplier

Each model has a credit multiplier that determines how many credits are consumed per token:

| Model Tier | Credit Multiplier | Example (1000 tokens) |
|------------|-------------------|----------------------|
| Free models | 0.005 - 0.01 | 5-10 credits |
| Pro models | 0.02 - 0.1 | 20-100 credits |
| Enterprise models | 0.1 - 0.15 | 100-150 credits |

### Premium Model Multiplier

Premium models (GPT-4o, Claude 3.5 Sonnet, etc.) consume **4× credits** compared to their base multiplier.

Example:
- Base multiplier: 0.1 (100 credits per 1000 tokens)
- Premium multiplier: 0.1 × 4 = 0.4 (400 credits per 1000 tokens)

### Credit Calculation Formula

```
Credits Used = Total Tokens × Credit Multiplier × (4 if premium model, else 1)
```

## Subscription Tiers

### Free Tier
- **Tokens**: 10,000 per month
- **Credits**: 5,000 per month
- **Models**: Limited to free-tier models (Gemini Flash, GPT-3.5-turbo, etc.)

### Pro Tier
- **Tokens**: 30,000 per month
- **Credits**: 50,000 per month
- **Models**: Access to most models (GPT-4o, Claude 3.5 Sonnet, etc.)
- **Cost**: $12/month (or $99/year)

### Enterprise Tier
- **Tokens**: 1,000,000 per month
- **Credits**: 1,000,000 per month
- **Models**: All models including premium options
- **Cost**: Custom pricing

## Usage Tracking

### How Usage Is Tracked

1. **Per Message**: Each API call tracks:
   - Input tokens
   - Output tokens
   - Total tokens
   - Cost in USD
   - Credits consumed

2. **Per Conversation**: Aggregates all messages in a conversation

3. **Per User**: Monthly totals reset at the start of each billing cycle

### Deduction Process

When a user sends a message:

1. **Pre-check**: System verifies user has sufficient credits
2. **API Call**: Message is sent to the provider
3. **Token Count**: Provider returns token usage
4. **Cost Calculation**: System calculates USD cost and credits
5. **Deduction**: Credits are deducted from user's balance
6. **Tracking**: Usage is logged in the database

### Balance Updates

- **Real-time**: Token and credit balances update immediately after each message
- **Persistent**: All usage is stored in the database for history and analytics
- **Monthly Reset**: Balances reset to tier limits at the start of each billing cycle

## Cost Optimization Tips

1. **Use Smaller Models**: GPT-4o-mini and Gemini Flash are much cheaper than GPT-4o
2. **Shorter Prompts**: Reduce input tokens by being concise
3. **Set Max Tokens**: Limit output length to control costs
4. **Monitor Usage**: Check your token/credit balance regularly
5. **Choose Right Tier**: Pro tier (30k tokens) is sufficient for most users

## Example Scenarios

### Scenario 1: Free Tier User
- Model: Gemini 2.5 Flash (free)
- Prompt: 200 tokens
- Response: 500 tokens
- **Cost**: $0 (free model)
- **Credits**: 3.5 credits (700 tokens × 0.005)

### Scenario 2: Pro Tier User
- Model: GPT-4o
- Prompt: 1,000 tokens
- Response: 2,000 tokens
- **Cost**: $0.035 USD
- **Credits**: 1,200 credits (3,000 tokens × 0.1 × 4 premium multiplier)

### Scenario 3: Multi-Model Comparison
- 3 models responding to same prompt
- Each uses ~1,000 tokens
- **Total Cost**: Sum of all 3 model costs
- **Total Credits**: Sum of all 3 model credit usage

## Database Storage

All cost data is stored in:
- **messages**: Per-message token and cost data
- **cost_tracker**: Detailed cost breakdown by provider/model
- **api_usage**: Aggregated usage statistics
- **subscriptions**: User balance and limits

## API Cost vs Subscription Cost

- **API Cost**: What we pay to providers (OpenAI, Anthropic, etc.)
- **Subscription Cost**: What users pay to AI Fiesta
- **Margin**: Subscription revenue minus API costs

The subscription model allows us to:
- Offer predictable pricing to users
- Absorb API cost fluctuations
- Provide better value through bundling

## Questions?

For more information, see:
- [Model Pricing Guide](./MODEL_PRICING_GUIDE.md)
- [Usage Limits Guide](./USAGE_LIMITS_GUIDE.md)

