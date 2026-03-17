# doc-summary — Examples

## Meeting notes

**Input**: Weekly sync notes — release delayed to next Friday, backend migration blocked on DB approval, front-end testing complete.

**Output**:
```markdown
## Summary
The weekly sync confirmed a one-week release delay and an unresolved backend blocker.

## Key Points
- Release pushed to next Friday
- Backend migration blocked pending DB team approval
- Front-end testing complete and ready

## Action Items
- [ ] Ping DB team for approval status (owner: backend lead)
```

---

## Technical document

**Input**: Auth service spec — JWT-based, 1-hour expiry, refresh token in HttpOnly cookie, no password storage.

**Output**:
```markdown
## Summary
The auth service uses JWTs with short expiry and refresh tokens stored in secure cookies.

## Key Points
- Access tokens expire in 1 hour
- Refresh token stored in HttpOnly cookie
- No passwords stored server-side

## Notable Details
- Token signing algorithm: RS256
- Logout invalidates refresh token immediately
```
