PLAN DE TEST - ACCESS CONTROL PAR PLAN

Contexte:
- access_status retourne: allowed (bool), status (trialing/active), trial_end, days_left, plan_end
- Pages: 0_Projects.py (liste), 10_Dashboard.py (travail)
- Actions: Create, Update, Delete bloquées si expired
- Navigation via URL bloquée si expired

Fichiers modifiés:
1. access_guard.py (nouveau): Guard central avec get_access_status_for_user, check_access_or_redirect
2. projects_page/actions.py: Ajout param can_edit à open_create_popover, project_actions_popover
3. projects_page/page.py: Passer can_edit à open_create_popover, project_actions_popover, afficher is_locked
4. pages/10_Dashboard.py: Import access_guard, vérifier gate avant d'afficher le Dashboard

SCÉNARIO 1: TRIAL ACTIF (days_left > 0)
=====================
1. Depuis terminal: sqlite3 artifacts/billing.sqlite "UPDATE accounts SET plan_status='trialing' WHERE email='test@example.com';"
2. Login avec test@example.com
3. Sur Projects: Bouton "Create project" ACTIF
4. Cliquer Create -> Popover apparaît, form valide
5. Créer un projet -> Succès
6. Cliquer ⚙︎ sur un projet -> Rename + Delete disponibles
7. Renommer -> Succès
8. Supprimer -> Succès
9. Accès Dashboard: OK, page charge normalement
Résultat: ✓ Tous les boutons actifs, pas d'avertissement

SCÉNARIO 2: PREMIUM ACTIF (plan_end > now)
===========================================
1. sqlite3 artifacts/billing.sqlite "UPDATE accounts SET plan_status='active', plan_end='2026-12-31T23:59:59Z' WHERE email='test@example.com';"
2. Recharger page (F5)
3. Sur Projects: Badge "Premium", plan_meta "Ends Dec 31, 2026"
4. Bouton "Create project" ACTIF
5. Créer projet -> Succès
6. Accès Dashboard: OK
Résultat: ✓ Tous les boutons actifs, badge Premium visible

SCÉNARIO 3: TRIAL EXPIRÉ (days_left = 0 ou trial_end < now)
============================================================
1. sqlite3 artifacts/billing.sqlite "UPDATE accounts SET plan_status='trialing', trial_end='2025-01-01T00:00:00Z' WHERE email='test@example.com';"
2. Recharger page (F5)
3. Sur Projects page:
   - Badge "Trial ended", plan_meta "Ended Jan 01, 2025"
   - Message rouge: "Your plan is expired. Projects are locked."
   - Bouton "Create project" DISABLED (grisé), tooltip "Your plan is expired. Upgrade to create projects."
4. Cliquer sur une carte de projet -> Card affiche "Trial ended" overlay
5. Pas d'accès au ⚙︎ pour modifier
6. Tentative accès Dashboard via URL: ?project=proj_xxx
   - Affiche erreur: "Your plan is expired. Dashboard is locked."
   - Page redirige automatiquement vers 0_Projects.py
   - "active_project_id" vidé de st.session_state
Résultat: ✓ Tous les boutons désactivés, message d'erreur clair, redirection Dashboard bloquée

SCÉNARIO 4: SUBSCRIPTION EXPIRED (plan_status='active' mais plan_end < now)
===========================================================================
1. sqlite3 artifacts/billing.sqlite "UPDATE accounts SET plan_status='active', plan_end='2025-01-01T00:00:00Z' WHERE email='test@example.com';"
2. Recharger page (F5)
3. Sur Projects page:
   - Badge "Subscription ended", plan_meta "Ended Jan 01, 2025"
   - Message rouge: "Your plan is expired. Projects are locked."
   - Bouton "Create project" DISABLED
4. Pas d'accès aux actions ⚙︎
5. Tentative Dashboard: Redirection + erreur
Résultat: ✓ Comportement identique au trial expiré

SCÉNARIO 5: TRIAL EXPIRANT BIENTÔT (days_left <= 3)
===================================================
1. sqlite3 artifacts/billing.sqlite "UPDATE accounts SET plan_status='trialing', trial_end='$(date -u -d "+2 days" +%Y-%m-%dT%H:%M:%SZ)' WHERE email='test@example.com';"
2. Recharger
3. Sur Projects page:
   - Badge "Trial", plan_meta "2 days left"
   - MAIS: Avertissement jaune: "Your trial expires in 2 day(s). Upgrade now"
   - Bouton "Create project" ACTIF (trial toujours valide)
4. Tous les boutons fonctionnent normalement
5. Dashboard accessible
Résultat: ✓ Warning visible, accès non bloqué

SCÉNARIO 6: ACCÈS DIRECT PAR URL AVEC PARAMÈTRE project (Anti-contournement)
=============================================================================
1. User expiré (trial_end < now ou plan_end < now)
2. Ouvrir URL directement: https://app.com/Dashboard?project=proj_123
3. Page Dashboard commence à charger mais:
   - Check access_status avant render
   - Erreur: "Your plan is expired. Dashboard is locked."
   - Redirection automatique vers 0_Projects.py
   - session_state["active_project_id"] vidé
4. URL n'a PAS changé le comportement (pas de contournement possible)
Résultat: ✓ Sécurité URL respectée

SCÉNARIO 7: CRÉER UTILISATEUR NEUF SANS ACCOUNT (trial par défaut)
==================================================================
1. Login nouvel utilisateur via Google (pas d'account créé yet)
2. get_account_by_email retourne None
3. access_status(None) retourne {"allowed": True, "status": "unknown", ...}
4. Sur Projects: can_edit=True, boutons actifs
5. Créer projet -> ensure_account crée un compte avec plan_status="trialing"
6. trial_end auto-défini à maintenant + 15 jours
7. Boutons restent actifs
Résultat: ✓ Nouvel user démarre en trial, accès complet

RESET DES DONNÉES POUR TESTS
=============================
Pour restaurer une DB propre:
1. rm artifacts/billing.sqlite artifacts/projects.json
2. rm -rf artifacts/projects/
3. Redémarrer l'app (ensure_account recréera la DB à la connexion)

SIMULATION LOCALE SANS SQLITE
=============================
Pour tester sans modifier la DB directement:
1. Dans auth_google.py _post_login, avant return user:
   user["plan_status"] = os.environ.get("TEST_PLAN_STATUS", "trialing")
   user["trial_end_override"] = os.environ.get("TEST_TRIAL_END")
2. Dans access_guard.py get_access_status_for_user:
   if user.get("plan_status"):
       gate["status"] = user["plan_status"]
       if user.get("trial_end_override"):
           gate["trial_end"] = parse(user["trial_end_override"])
3. Lancer avec:
   TEST_PLAN_STATUS=trialing TEST_TRIAL_END="2025-01-01T00:00:00Z" streamlit run pages/0_Router.py

VÉRIFICATION DES LOGS
====================
- Pour debug: AUTH_DEBUG_UI=1 streamlit run ... pour voir access_status dict
- Vérifier logs créent projet: "CREATED project <id> owner_id=..."
- Vérifier migrations: look for "MIGRATED ... PROJECTS TO acct:sub:..."
