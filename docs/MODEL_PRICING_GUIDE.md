# Model Pricing Guide

This guide provides information about the best models for different use cases based on price, performance, and features.

## Overview

AI Fiesta supports multiple LLM providers, each offering different models at various price points. This guide helps you choose the right models for your needs.

## Provider Comparison

### OpenAI

**Best for:** General-purpose tasks, code generation, creative writing

| Model | Input Cost (per 1M tokens) | Output Cost (per 1M tokens) | Best Use Case |
|-------|---------------------------|----------------------------|---------------|
| GPT-4o-mini | $0.15 | $0.60 | Budget-friendly, fast responses |
| GPT-3.5-turbo | $0.50 | $1.50 | General purpose, good balance |
| GPT-4o | $2.50 | $10.00 | High-quality, complex tasks |
| GPT-4.1 | $5.00 | $15.00 | Advanced reasoning, premium quality |

**Recommendation:** Start with `gpt-4o-mini` for cost-effective general use, upgrade to `gpt-4o` for higher quality.

### Anthropic (Claude)

**Best for:** Long context, analysis, safety-critical applications

| Model | Input Cost (per 1M tokens) | Output Cost (per 1M tokens) | Best Use Case |
|-------|---------------------------|----------------------------|---------------|
| Claude 3 Haiku | $0.25 | $1.25 | Fast, cost-effective |
| Claude 3 Sonnet | $3.00 | $15.00 | Balanced performance |
| Claude 3 Opus | $15.00 | $75.00 | Premium quality, complex tasks |

**Recommendation:** Use `claude-3-haiku` for quick tasks, `claude-3-sonnet` for detailed analysis.

### Google Gemini

**Best for:** Multimodal tasks, free tier users, general purpose

| Model | Input Cost (per 1M tokens) | Output Cost (per 1M tokens) | Best Use Case |
|-------|---------------------------|----------------------------|---------------|
| Gemini 2.5 Flash | FREE | FREE | Free tier, fast responses |
| Gemini 2.0 Flash | FREE | FREE | Free tier, good quality |
| Gemini 2.5 Pro | $0.50 | $1.50 | Higher quality, paid tier |
| Gemini Pro Latest | $0.50 | $1.50 | Latest features |

**Recommendation:** `gemini-2.5-flash` is excellent for free tier users. `gemini-2.5-pro` offers better quality for paid users.

### Grok (X/Twitter)

**Best for:** Real-time information, Twitter/X integration, conversational AI

| Model | Input Cost (per 1M tokens) | Output Cost (per 1M tokens) | Best Use Case |
|-------|---------------------------|----------------------------|---------------|
| Grok Beta | $0.10 | $0.30 | Early access, experimental |
| Grok 2 | $0.20 | $0.60 | Improved version |

**Recommendation:** Use for real-time information needs and Twitter/X context.

### Perplexity

**Best for:** Research, citations, up-to-date information

| Model | Input Cost (per 1M tokens) | Output Cost (per 1M tokens) | Best Use Case |
|-------|---------------------------|----------------------------|---------------|
| Perplexity Sonar | $0.20 | $0.80 | Research, citations |
| Perplexity Sonar Pro | $0.50 | $2.00 | Advanced research |

**Recommendation:** Use for research tasks requiring citations and up-to-date information.

## Cost Comparison by Use Case

### Budget-Conscious Users (Free Tier)

1. **Gemini 2.5 Flash** - FREE, fast, good quality
2. **Gemini 2.0 Flash** - FREE, alternative option
3. **Grok Beta** - Very low cost ($0.10/$0.30)

**Best Choice:** Gemini 2.5 Flash for free tier users

### General Purpose (Balanced Cost/Quality)

1. **GPT-4o-mini** - $0.15/$0.60 - Excellent balance
2. **Claude 3 Haiku** - $0.25/$1.25 - Fast and capable
3. **Gemini 2.5 Pro** - $0.50/$1.50 - Good quality

**Best Choice:** GPT-4o-mini for most general tasks

### High Quality (Premium)

1. **GPT-4o** - $2.50/$10.00 - Top-tier quality
2. **Claude 3 Sonnet** - $3.00/$15.00 - Excellent analysis
3. **Gemini 2.5 Pro** - $0.50/$1.50 - Good value

**Best Choice:** GPT-4o for premium quality at reasonable cost

### Research & Citations

1. **Perplexity Sonar** - $0.20/$0.80 - Best for research
2. **Perplexity Sonar Pro** - $0.50/$2.00 - Advanced research

**Best Choice:** Perplexity Sonar for research tasks

## Cost Optimization Tips

1. **Use Flash/Mini models for simple tasks** - Save 80-90% on costs
2. **Batch similar requests** - Combine multiple questions into one prompt
3. **Set max_tokens limits** - Prevent unnecessarily long responses
4. **Use appropriate model tiers** - Don't use premium models for simple tasks
5. **Monitor usage** - Track token and credit usage regularly

## Model Selection Strategy

### For Multi-Chat Mode

When comparing multiple models, use:
- **Budget comparison:** Gemini 2.5 Flash, GPT-4o-mini, Claude 3 Haiku
- **Quality comparison:** GPT-4o, Claude 3 Sonnet, Gemini 2.5 Pro
- **Specialized:** Perplexity Sonar (research), Grok Beta (real-time)

### For Super Fiesta Mode

Choose based on your primary need:
- **Cost-effective:** Gemini 2.5 Flash (FREE)
- **Balanced:** GPT-4o-mini
- **High quality:** GPT-4o or Claude 3 Sonnet
- **Research:** Perplexity Sonar

## Subscription Tier Recommendations

### Free Tier
- Focus on Gemini models (free)
- Use Grok Beta for low-cost options
- Limited to free-tier models

### Pro Tier
- Access to GPT-4o-mini, Claude 3 Haiku
- Gemini Pro models
- Good balance of cost and quality

### Enterprise Tier
- Full access to all models
- GPT-4o, Claude 3 Opus
- Best for production workloads

## Example Cost Scenarios

### Scenario 1: Daily Chat (100 messages/day, ~500 tokens each)
- **Gemini 2.5 Flash:** FREE
- **GPT-4o-mini:** ~$0.03/day (~$0.90/month)
- **GPT-4o:** ~$0.13/day (~$3.90/month)

### Scenario 2: Research Project (50 queries, ~2000 tokens each)
- **Perplexity Sonar:** ~$0.10
- **GPT-4o:** ~$0.25
- **Claude 3 Sonnet:** ~$0.30

### Scenario 3: Code Generation (200 requests, ~1000 tokens each)
- **GPT-4o-mini:** ~$0.04
- **GPT-4o:** ~$0.50
- **Claude 3 Sonnet:** ~$0.60

## Notes

- Prices are approximate and may vary by provider
- Free tier models (Gemini) have rate limits
- Credit costs in AI Fiesta are calculated based on token usage
- Monitor your usage in the admin dashboard
- Consider your subscription tier when selecting models

## Additional Resources

- Check your current subscription tier in the sidebar
- View token usage in the header
- Monitor costs in the admin dashboard
- Contact support for custom pricing options

