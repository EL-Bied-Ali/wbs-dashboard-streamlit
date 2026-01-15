# Manual Testing Guide: Server-Side Access Guards

## Prerequisites

1. Have set_plan_status.py ready (helper to modify billing DB)
2. Have 2 test accounts:
   - `active_user@example.com` - for testing active subscriptions
   - `expired_user@example.com` - for testing expired subscriptions

## Test Scenarios

### Scenario 1: Create Project (Active Plan)
**Expected**: Project created successfully

1. Login with `active_user@example.com`
2. Go to Projects page
3. Click "Create project" button/popover
4. Enter project name
5. Click "Create"
6. ✓ Project should be created and appear in list

### Scenario 2: Create Project (Expired Plan)
**Expected**: Error message with lock icon + link to Billing

1. Set `active_user@example.com` plan to expired:
   ```bash
   python scripts/set_plan_status.py active_user@example.com expired
   ```
2. Refresh Projects page (Ctrl+F5 to clear cache)
3. Click "Create project" button/popover
4. Enter project name
5. Click "Create"
6. ✓ Should see error: "🔒 Plan expired: projects are locked..."
7. ✓ Should see "Go to Billing" link
8. ✓ Project should NOT be created

### Scenario 3: Update Project Name (Expired Plan)
**Expected**: Error message with lock icon + link to Billing

1. Ensure `active_user@example.com` is still marked as expired
2. Go to Projects page
3. Click ⚙︎ button on any project
4. Click "Save" after editing name
5. ✓ Should see error: "🔒 Plan expired: projects are locked..."
6. ✓ Project name should NOT be updated

### Scenario 4: Delete Project (Expired Plan)
**Expected**: Error message with lock icon + link to Billing

1. Ensure `active_user@example.com` is still marked as expired
2. Go to Projects page
3. Click ⚙︎ button on any project
4. Click "Delete" button
5. Click "Confirm"
6. ✓ Should see error: "🔒 Plan expired: projects are locked..."
7. ✓ Project should NOT be deleted

### Scenario 5: Upload Excel (Expired Plan)
**Expected**: Error message with lock icon + link to Billing

1. Ensure `active_user@example.com` is still marked as expired
2. Go to a project (Dashboard page)
3. Try to upload Excel file in sidebar
4. ✓ Should see error in sidebar: "🔒 Plan expired..."
5. ✓ "Go to Billing" link should be shown
6. ✓ File should NOT be uploaded

### Scenario 6: Save Mapping (Expired Plan)
**Expected**: Error message with lock icon + link to Billing

1. Ensure `active_user@example.com` is still marked as expired
2. On Dashboard page with existing Excel
3. Click "Edit column mapping"
4. Click "Apply mapping"
5. ✓ Should see error: "🔒 Plan expired..."
6. ✓ "Go to Billing" link should be shown
7. ✓ Mapping should NOT be saved

### Scenario 7: Trial User Can Still Create
**Expected**: Project created successfully (trial users can edit)

1. Create/mark `trial_user@example.com` with status='trialing'
2. Login with trial user
3. Go to Projects page
4. Create a project
5. ✓ Project should be created (trial users allowed to edit)

### Scenario 8: Premium User Can Create
**Expected**: Project created successfully (active subscriptions work)

1. Set `active_user@example.com` plan back to active:
   ```bash
   python scripts/set_plan_status.py active_user@example.com active
   ```
2. Refresh Projects page
3. Create a project
4. ✓ Project should be created

### Scenario 9: UI Bypass Prevention
**Expected**: Server-side guard catches manually modified requests

1. Set user plan to expired
2. Open browser DevTools (F12)
3. Try to manipulate button disabled states (hacky)
4. Attempt to create project
5. ✓ Should still get PermissionError from server (UI guard not enough)

### Scenario 10: Dashboard Access Gate
**Expected**: Redirect to Projects if expired

1. Set user plan to expired
2. Try to access Dashboard directly: `/pages/10_Dashboard.py?project=<id>`
3. ✓ Should see "Trial ended" / "Subscription ended" gate with redirect
4. ✓ Button to go to Projects page shown

## Helper Commands

### Mark User as Expired
```bash
python scripts/set_plan_status.py email@example.com expired
```

### Mark User as Active
```bash
python scripts/set_plan_status.py email@example.com active
```

### Mark User as Trialing
```bash
python scripts/set_plan_status.py email@example.com trialing --days=30
```

### View User Billing Status
```bash
python scripts/set_plan_status.py email@example.com show
```

## Checklist

- [ ] Scenario 1: Create project (active) - ✓ works
- [ ] Scenario 2: Create project (expired) - ✓ shows error
- [ ] Scenario 3: Update project (expired) - ✓ shows error
- [ ] Scenario 4: Delete project (expired) - ✓ shows error
- [ ] Scenario 5: Upload Excel (expired) - ✓ shows error
- [ ] Scenario 6: Save mapping (expired) - ✓ shows error
- [ ] Scenario 7: Trial user can create - ✓ works
- [ ] Scenario 8: Premium user can create - ✓ works
- [ ] Scenario 9: UI bypass prevented - ✓ server catches it
- [ ] Scenario 10: Dashboard gate works - ✓ redirects

## Notes

- All errors should show lock emoji (🔒) + message
- All errors should provide "Go to Billing" link
- Server-side guards are **always** active, even if UI is bypassed
- Access check uses same `allowed` flag as UI
- Failed mutations do NOT update projects.json

## Troubleshooting

**Q: User still can mutate after marking as expired?**
- A: Verify set_plan_status.py correctly updated billing.sqlite
- A: Check that status is 'expired' (not 'trial_ended' or other)
- A: Check that allowed=False in access_status dict

**Q: "Go to Billing" link not showing?**
- A: Check page.py/actions.py - should have `st.page_link("pages/4_Billing.py", label="Go to Billing")`
- A: Verify pages/4_Billing.py exists

**Q: Error shows but project still created?**
- A: Exceptions might not be raised. Check projects.py - assert_can_edit should be called
- A: Check file doesn't have old version (clear cache, restart)

## Integration with Paddle Webhooks

After a Paddle event (subscription.expired, subscription.cancelled, etc.):
1. Webhook handler updates billing.sqlite (status -> 'expired')
2. User refreshes page
3. access_status() reads updated status
4. assert_can_edit() checks and raises PermissionError if needed
5. UI error handler catches and shows message

No special handling needed - happens automatically on next mutation attempt.
