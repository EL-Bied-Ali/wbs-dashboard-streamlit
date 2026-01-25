# Server-Side Guards Implementation Summary

## Overview
Added comprehensive server-side guards to prevent mutations when user's billing plan expires, even if UI is bypassed.

## Architecture
1. **Core Guard**: `access_guard.assert_can_edit(user)` raises `PermissionError` if plan expired
2. **Protected Mutations**: All CRUD operations now accept optional `user` param and verify access
3. **UI Handlers**: All handlers wrapped with try/except to catch `PermissionError` and show Billing link

## Protected Mutations

### Projects CRUD (projects.py)
- ✅ `create_project(user=user)` - Checks access before creating
- ✅ `update_project(user=user)` - Checks access before updating
- ✅ `delete_project(user=user)` - Checks access before deleting
- ✅ `assign_projects_to_owner(user=user)` - Checks access before assigning

### File Operations (projects.py)
- ✅ `store_project_upload(user=user)` - Checks access before accepting upload
- ✅ `persist_project_mapping(user=user)` - Checks access before saving mapping

## UI Handlers with PermissionError Handling

### Projects Page (projects_page/actions.py)
- ✅ `open_create_dialog()` - Dialog with try/except, link to Billing
- ✅ `open_create_popover()` - Popover with try/except, link to Billing  
- ✅ `project_actions_popover()` - Update/delete with try/except, link to Billing

### Dashboard (pages/10_Dashboard.py)
- ✅ Excel upload handler - try/except with st.sidebar.error + Billing link
- ✅ Mapping save handler - try/except with st.error + Billing link
- ✅ Project assignment (init) - try/except with st.error + Billing link

### WBS App (wbs_app/wbs_app.py)
- ✅ Excel upload handler - try/except with st.sidebar.error + Billing link
- ✅ Mapping save handler - try/except with st.error + Billing link

## User Parameter Flow

```
Projects Page (user from require_login)
  ├─> open_create_popover(user=user)
  │    └─> create_project(user=user)
  │         └─> assert_can_edit(user) ✓
  │
  ├─> project_actions_popover(user=user)
  │    ├─> update_project(user=user)
  │    │    └─> assert_can_edit(user) ✓
  │    └─> delete_project(user=user)
  │         └─> assert_can_edit(user) ✓
  │
  └─> assign_projects_to_owner(user=user)
       └─> assert_can_edit(user) ✓

Dashboard (user from require_login)
  ├─> _store_project_upload(user=user)
  │    └─> store_project_upload(user=user)
  │         └─> assert_can_edit(user) ✓
  │
  └─> persist_project_mapping(user=user)
       └─> update_project(user=user)
            └─> assert_can_edit(user) ✓
```

## Error Handling Pattern

All mutations wrapped in try/except:

```python
try:
    result = mutation_function(..., user=user)
    # success flow
except PermissionError as e:
    st.error(f"🔒 {str(e)}")
    st.page_link("pages/4_Billing.py", label="Go to Billing")
```

## Validation Checklist

- [ ] Create project - fails when expired
- [ ] Update project - fails when expired  
- [ ] Delete project - fails when expired
- [ ] Upload Excel - fails when expired
- [ ] Save mapping - fails when expired
- [ ] Assign projects - fails when expired
- [ ] All errors show lock emoji + link to Billing
- [ ] Trial users can still mutate (status='trialing', allowed=true)
- [ ] Premium users can still mutate (status='active', allowed=true)
- [ ] Expired users cannot mutate (status='expired' or 'trialing' with trial_end passed)

## Test Command

```python
# Mark a user's plan as expired
python scripts/set_plan_status.py <email> expired

# Then try to create/update/delete projects - should fail with PermissionError
```

## Notes

- `allow` default is `True` for backward compatibility (non-billing users can still use app)
- Guard checks `plan_state.get("allowed", True)` - same logic as UI
- Server guard uses `assert_can_edit(user)` which calls `access_status()` internally
- All wrapper functions (_store_project_upload in Dashboard/wbs_app) accept user param and pass through
