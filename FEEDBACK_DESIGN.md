# User Feedback System - Design Doc

## Problem
Users want to report corrections like "curry contains pork" but we need to prevent:
- Malicious users spreading false information
- Spam/trolling
- Security vulnerabilities

## Safe Approach: Admin-Moderated Feedback

### How it works:
1. User sends feedback via `/feedback` command
2. Bot forwards it to YOU (admin) on Telegram
3. You review and decide if it's valid
4. If valid, you manually update a `corrections.json` file
5. Bot includes corrections in future analysis

### Implementation:

```python
# User sends: /feedback Curry at Professor cafeteria has pork
# Bot sends to admin chat:
"""
📝 New Feedback
From: @username (ID: 123456)
Message: Curry at Professor cafeteria has pork
Time: 2024-12-18 10:30

Reply /approve or /reject
"""
```

### Why this is safe:
✅ Human verification (you approve)
✅ No automatic database changes
✅ Audit trail (who reported what)
✅ Can ban trolls by ID

### Alternative: View-Only Feedback
- Users can send feedback
- Bot just logs it to a file
- You review periodically
- No automatic changes to menu analysis

## Recommendation
Start with **view-only logging** - simple and safe. Add admin approval later if needed.

Would you like me to implement this?
