# AI Fiesta Frontend Development Roadmap

## 🚨 Phase 1: Fix Critical Streaming Bug (HIGH PRIORITY)

### Problem Analysis
**Symptom:** Text is duplicating and splitting mid-word during SSE streaming
```
"The fastest human inThe fastest human in the world is the world is Usain Bolt Usain Bolt..."
```

**Likely Causes:**
1. **Double event emission** - Same chunk being sent twice from backend
2. **Buffer flushing issue** - SSE chunks not properly delimited
3. **React state race condition** - Multiple setState calls overlapping
4. **Chunk boundary splitting** - Words split across SSE message boundaries

### Debug Steps

#### Step 1: Test with `test_client.html` (Isolate backend)
- Open `http://localhost:8000/test_client.html`
- Send same prompt and observe raw SSE chunks
- Check browser DevTools Network tab → EventStream
- **If duplicates appear here:** Backend issue
- **If clean here:** Frontend React issue

#### Step 2: Backend Investigation (`app/routers/chat.py`)
**File:** `app/routers/chat.py` line 200-300 (stream_chat endpoint)

Check for:
```python
# Look for double yield
async for chunk in provider.stream_generate(...):
    # Is this yielding twice?
    payload = json.dumps({"type": "chunk", "content": chunk_text})
    yield f"data: {payload}\n\n"  # ← Check if called twice
```

**Potential fixes:**
- Add logging: `print(f"Yielding chunk: {chunk_text}")`
- Ensure no duplicate async iteration
- Check `emulate_stream_text()` in `app/utils/stream_emulation.py`

#### Step 3: Frontend Investigation (`hooks/use-chat-sse.ts`)
**File:** `hooks/use-chat-sse.ts` line 50-100

Check for:
```typescript
// State update race condition
setMessages((prev) => {
  const updated = [...prev]
  updated[updated.length - 1].content += data.content || ""  // ← Concatenating twice?
  return updated
})
```

**Potential fixes:**
- Add console.log before setState
- Use functional update pattern (already doing this ✓)
- Check if multiple SSE listeners registered

#### Step 4: SSE Parser Issue
**File:** `hooks/use-chat-sse.ts` line 70-90

```typescript
// Buffer handling
buffer += decoder.decode(value, { stream: true })
const events = buffer.split("\n\n")
buffer = events.pop() || ""
```

**Check:**
- Are events being parsed multiple times?
- Is `buffer` accumulating old data?

### Action Items
- [ ] Test in `test_client.html` first
- [ ] Add logging to backend `stream_chat()` 
- [ ] Add console.log to frontend `use-chat-sse.ts`
- [ ] Compare raw SSE events vs rendered UI
- [ ] Test with different models (Gemini, OpenAI, Anthropic)

---

## 🎯 Phase 2: Multi-Model Toggle Feature (MEDIUM PRIORITY)

### Goal
Enable users to select multiple models and stream responses simultaneously.

### UI Design
```
┌─────────────────────────────────────────────────────┐
│ 🎉 AI Fiesta                          Tokens: 500   │
│                                                      │
│ Active Models:                                       │
│ ┌──────────────┐ ┌──────────────┐ ┌──────────────┐ │
│ │ GPT-4     ⚫ │ │ Gemini    ⚫ │ │ Claude    ⚪ │ │
│ │ OpenAI       │ │ Google       │ │ Anthropic    │ │
│ └──────────────┘ └──────────────┘ └──────────────┘ │
└─────────────────────────────────────────────────────┘
```

### Implementation Plan

#### Step 1: Create Toggle Component
**New file:** `components/model-toggle.tsx`

```typescript
interface ModelToggleProps {
  availableModels: Model[]
  enabledModels: string[]
  onToggle: (modelId: string) => void
  userTier: string
}

export function ModelToggle({ availableModels, enabledModels, onToggle, userTier }) {
  // Filter models by user tier
  // Display as chips with toggle switches
  // Show provider logo/icon
}
```

#### Step 2: Update Chat Page State
**File:** `app/page.tsx`

```typescript
// Replace single model state
const [selectedModel, setSelectedModel] = useState("")

// With multi-model state
const [enabledModels, setEnabledModels] = useState<string[]>(["gemini-2.5-flash"])

const toggleModel = (modelId: string) => {
  setEnabledModels(prev => 
    prev.includes(modelId) 
      ? prev.filter(m => m !== modelId)
      : [...prev, modelId]
  )
}
```

#### Step 3: Backend Multi-Model Endpoint
**File:** `app/routers/chat.py`

**Option A:** Send parallel requests from frontend
```typescript
// Frontend handles multiple SSE connections
enabledModels.forEach(model => {
  sendMessage(prompt, model, ...)
})
```

**Option B:** Create backend endpoint (RECOMMENDED)
```python
@router.post("/stream/chat/multi")
async def stream_chat_multi(request: Request):
    """
    Accept multiple models and stream all responses.
    
    Response format:
    data: {"type": "chunk", "model": "gpt-4", "content": "..."}
    data: {"type": "chunk", "model": "gemini-2.5-flash", "content": "..."}
    data: {"type": "done", "model": "gpt-4", "tokens_used": 100}
    """
    # Implementation: asyncio.gather() to stream multiple models
```

#### Step 4: UI Layout for Multiple Responses
**File:** `components/multi-model-response.tsx`

**Layout Options:**

**Option A: Side-by-side columns**
```
┌─────────────────┬─────────────────┬─────────────────┐
│ GPT-4           │ Gemini          │ Claude          │
├─────────────────┼─────────────────┼─────────────────┤
│ Response text   │ Response text   │ Response text   │
│ streaming...    │ streaming...    │ streaming...    │
└─────────────────┴─────────────────┴─────────────────┘
```

**Option B: Stacked cards** (RECOMMENDED - better for mobile)
```
┌───────────────────────────────────────┐
│ 🤖 GPT-4                              │
│ Response text streaming...            │
└───────────────────────────────────────┘

┌───────────────────────────────────────┐
│ ✨ Gemini                             │
│ Response text streaming...            │
└───────────────────────────────────────┘
```

#### Step 5: Token/Credit Tracking
- Track usage per model
- Show individual model costs
- Deduct credits for each model separately

### Action Items
- [ ] Create `components/model-toggle.tsx`
- [ ] Update `app/page.tsx` with multi-model state
- [ ] Create `POST /stream/chat/multi` endpoint
- [ ] Create `components/multi-model-response.tsx`
- [ ] Update `hooks/use-chat-sse.ts` for multi-model
- [ ] Add per-model cost tracking

---

## 🧹 Phase 3: Clean Up UI / Add Missing APIs (LOW PRIORITY)

### Option A: Remove Unimplemented Features

**File:** `components/sidebar.tsx`

Remove or comment out:
```typescript
// Remove these until APIs exist:
- Avatars button (line 40)
- Projects button (line 47)
- Games button (line 54)
- Yesterday history (line 65)
```

**Keep only:**
- New Chat
- Admin link
- Settings (configure later)

### Option B: Implement Conversation APIs

#### Backend APIs Needed

**File:** `app/routers/chat.py`

```python
@router.post("/conversations/")
async def create_conversation(user_id: str):
    """Create new conversation"""
    pass

@router.get("/conversations/{user_id}")
async def list_conversations(user_id: str):
    """List user's conversations"""
    pass

@router.get("/conversations/{conv_id}/messages")
async def get_messages(conv_id: str):
    """Get messages in conversation"""
    pass

@router.delete("/conversations/{conv_id}")
async def delete_conversation(conv_id: str):
    """Delete conversation"""
    pass
```

#### Frontend Updates

**File:** `components/sidebar.tsx`

```typescript
const [conversations, setConversations] = useState([])

useEffect(() => {
  // Fetch user's conversations
  fetch(`/conversations/${userId}`)
    .then(res => res.json())
    .then(setConversations)
}, [])

// Display in "Yesterday" section
{conversations.map(conv => (
  <button onClick={() => loadConversation(conv.id)}>
    {conv.title || conv.first_message}
  </button>
))}
```

### Recommendation
**Go with Option A** - Remove features for now. Add conversation APIs in Phase 4 after multi-model works.

---

## 📋 Summary Timeline

### Week 1
- [ ] **Day 1-2:** Fix streaming duplication bug
- [ ] **Day 3-4:** Test across all providers (Gemini, OpenAI, Anthropic)

### Week 2
- [ ] **Day 1-2:** Create model toggle component
- [ ] **Day 3-4:** Implement multi-model streaming backend
- [ ] **Day 5:** Multi-model UI layout

### Week 3
- [ ] **Day 1-2:** Clean up sidebar (remove unimplemented features)
- [ ] **Day 3:** Polish and testing
- [ ] **Day 4-5:** Buffer for bug fixes

---

## 🎯 Next Immediate Action

**START HERE:** Fix the streaming bug first before building new features.

1. Open `test_client.html`
2. Send a test prompt
3. Open browser DevTools → Network → EventStream
4. Look for duplicate chunks
5. Report back findings 

Finding: Doesn't happen on test_client.html -> likely frontend issue

Once streaming is stable, we build multi-model toggle.