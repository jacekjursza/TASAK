# TASAK Implementation Order

## Phase 1: Critical Fixes (Do First)

### ~~001 - Fix Argument Passing~~ → Merged into 003
**File:** `fix-argument-passing.md`
**Decision:** SKIP - Task 003 solves this properly with curated mode
**Quick workaround if needed:** Add `TASAK_FLAGS = {'clear_cache'}` filter (5 min fix)

### 002 - Handle Server Unavailable ⚡
**File:** `handle-server-unavailable.md`
**Why early:** Better UX, prevents ugly stack traces
**Effort:** Small (2-3 hours)
**Impact:** High - Clean error messages
**Note:** Can simplify - skip the 5-minute cache initially, just do clean errors

---

## Phase 2: Core Architecture (Foundation)

### 003 - Standardize App Interface
**File:** `standardize-app-interface.md` + `argument-handling-architecture.md`
**Why:** Foundation for all other changes
**Effort:** Medium (1 day)
**Impact:** High - Consistent proxy/curated modes
**Note:** These two files overlap - merge into one task

### 004 - Admin Commands (auth/refresh)
**File:** `admin-auth-refresh-implementation.md`
**Why:** Enables schema caching, better auth management
**Effort:** Medium (1 day)
**Impact:** High - Performance improvement, better UX
**Note:** Start with just `refresh` - auth can wait

---

## Phase 3: Performance & Polish

### 005 - MCP Remote Communication
**File:** `mcp-remote-communication-issue.md` + `tasak-service-architecture.md`
**Why:** Atlassian/GitHub/Slack support
**Effort:** Large (2-3 days)
**Impact:** Medium - Enables remote services
**Note:** Implement Process Pool from the start, skip simple subprocess.run

### 006 - MCP Compatibility Notes
**File:** `mcp-compatibility-notes.md`
**Why:** Documentation only
**Effort:** None - already resolved
**Action:** Move to docs/wiki, not a task

---

## Simplifications Suggested

1. **Merge overlapping tasks:**
   - `standardize-app-interface.md` + `argument-handling-architecture.md` → Single task

2. **Simplify server unavailable:**
   - Skip 5-minute cache in v1
   - Just clean error messages
   - Add cache later if needed

3. **Simplify admin commands:**
   - Start with just `tasak admin refresh <app>`
   - Skip auth refactoring initially (current auth works)
   - Add other admin commands later

4. **MCP Remote - go straight to Process Pool:**
   - Don't implement broken subprocess.run version
   - Start with Process Pool immediately

---

## Recommended Sprint Plan

### Week 1: Make it Work
- Monday: 001 (Fix args) + 002 (Server errors)
- Tuesday-Wednesday: 003 (Standardize interface)
- Thursday-Friday: 004 (Admin refresh only)

### Week 2: Make it Fast
- Monday-Wednesday: 005 (MCP Remote with Process Pool)
- Thursday-Friday: Polish, testing, documentation

---

## Files to Rename

```bash
mv fix-argument-passing.md                 001-fix-argument-passing.md
mv handle-server-unavailable.md            002-handle-server-unavailable.md
mv standardize-app-interface.md            003-standardize-app-interface.md
mv admin-auth-refresh-implementation.md    004-admin-commands.md
mv mcp-remote-communication-issue.md       005-mcp-remote-pool.md

# Archive/merge
mv argument-handling-architecture.md       003-standardize-app-interface-appendix.md
mv tasak-service-architecture.md          005-mcp-remote-pool-appendix.md
mv mcp-compatibility-notes.md             ../wiki/
```
