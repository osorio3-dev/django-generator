# Changelog — django-generator

Historial de implementación por phase. Cada phase agrega un commit (o un set de
commits) y queda locked detrás de un tag conceptual.

---

## v0.1.0 — MVP Copier template (2026-07-11)

Branch: `feat/mvp-copier-template`. **30 commits**, listos para `copier update`.

### Phase 3a — Base layer + admin=unfold (commits 1-9)

Foundation. Base + 3 ejes (`api`, `admin`, `frontend`) + Django 6 + BaseModel
+ soft-delete + Fernet conditional + structlog + RateLimitMiddleware atómico.

1. `feat(generator): scaffold copier.yml with 24 questions from DESIGN §9`
2. `feat(generator): base project skeleton — pyproject + manage + pytest + makefile + env`
3. `feat(generator): settings split (base/local/production/test) + urls + wsgi/asgi`
4. `feat(generator): apps/core skeleton — BaseModel + middleware + logging + commands`
5. `feat(generator): apps/accounts conditional on admin=unfold — email-first User`
6. `test(generator): 3 smoke tests asserting the locked-in contracts`
7. `chore(generator): apps/__init__.py so apps/ is a Python package`
8. `feat(generator): isolate UNFOLD settings in config/settings/unfold.py`
9. `feat(generator): monkey-patch admin.site with UnfoldAdminSite`

**Decisiones locked**:
- `RateLimitMiddleware` SIEMPRE en `MIDDLEWARE` (bug del `django-boilerplate-v2` corregido).
- `DEBUG` parsing case-insensitive (`true`/`1`/`yes`).
- `SECRET_KEY` validator en `production.py` rechaza prefijos inseguros.
- `ALLOWED_HOSTS` strict — `production.py` levanta `ImproperlyConfigured` si la lista queda vacía.
- Custom `User` email-first (`USERNAME_FIELD="email"`, `username=None`) SOLO cuando `admin=unfold`.
- Fernet se activa automáticamente via `persists_sensitive_data=yes` o módulos sensibles.

### Phase 3b — Unfold settings aislado (commits 10-12)

`config/settings/unfold.py` separado de `base.py` para que toda la config
de branding (SIDEBAR, TABS, colores) viva en un archivo que el usuario puede
customizar sin tocar la infraestructura. Importado via `from config.settings
import unfold` en `base.py.jinja`.

10. `test(generator): assert UNFOLD integration contracts`
11. `feat(generator): vue_router question + frontend package/vite manifests`
12. `feat(generator): apps/web — landing, dashboard, health_frontend views`

### Phase 3c — Frontend axis (commits 13-15)

Eje `frontend` con dos estilos mutuamente excluyentes:

13. `feat(generator): templates for server-rendered (base + cotton)`
14. `feat(generator): settings + URL wiring for the frontend axis`
15. `test(generator): locked-in contracts for the frontend axis`

- **server-rendered**: Preline + HTMX + Alpine + django-cotton + Vite + Tailwind v4 CSS-first.
- **vue-spa**: Vue 3 + Vite SPA + Preline + django-vite + auth Django-side via allauth.
- Login.vue único (NO demo Vue components, per DESIGN §6.5).
- `vue_router`: `history` (default) | `hash`.
- `package_manager`: `npm` (default) | `bun` — NUNCA ambos lockfiles.

### Phase 3d — 13 opt-in modules (commits 16-25)

Foundation + 9 módulos + 4 infra flags:

16. `feat(generator): foundation for 13 opt-in modules`
17. `feat(generator): module-secure-endpoints`
18. `feat(generator): module-multitenant (logical + schema)`
19. `feat(generator): module-wompi`
20. `feat(generator): module-ghl`
21. `feat(generator): module-supabase`
22. `feat(generator): module-realtime`
23. `feat(generator): module-django-guard`
24. `feat(generator): module-autologin-tests360`
25. `feat(generator): module-docker + test_module_infra_files`

### Phase 3e — Infra flags + 4 SKILL.md files (commits 26-30)

26. `feat(generator): module-precommit`
27. `feat(generator): module-github-ci`
28. `feat(generator): module-debug-toolbar test + validation script`
29. `fix(generator): vue-spa structure + missing api app + DEBUG in test settings`
30. `feat(generator): add 4 SKILL.md files for generated projects`

Commit 29 arregla gaps detectados en Phase 4 verification:
- `apps/web/vue/` ahora respeta el negative contract (DESIGN §15): solo Login.vue.
- `apps/web/vite/` se omite cuando `frontend_style=vue-spa`.
- `apps/api/router.py` agregado (DESIGN §6.2 lo llamaba, faltaba la implementación).
- `apps/core/models/fields.py` filename conditional (no se genera archivo vacío cuando Fernet está inactivo).
- `config/settings/test.py` usa `DEBUG=True` para que django-vite no requiera manifest.json.
- `config/settings/__init__.py` autodetecta pytest via el trailing segment de `DJANGO_SETTINGS_MODULE`.

### Phase 4 — Final verification (este commit)

- 4 escenarios auditados validados end-to-end: copier copy + manage.py check + pytest.
- `README.md` definitivo (Spanish, con 6 ejemplos, 4 skills, 13 módulos).
- `CHANGELOG.md` (este archivo).
- 30 commits totales sobre `feat/mvp-copier-template`.

---

## Compatibilidad

- **Python**: 3.12 (default) | 3.13
- **Django**: 6.0
- **Copier**: >= 9.0 (usa `_migrations`, `_subdirectory`, etc.)
- **uv**: cualquier versión reciente (probado con 0.11.x)

## Upgrade path

Cuando agregues features en este template, **no rompas proyectos existentes**.
Tres reglas:

1. Módulos nuevos: agregá como opt-in en `optional_modules`. Proyectos viejos
   no los activan automáticamente.
2. Cambios en `base.py`: agregá migration script en `_migrations/v0.X_to_v0.Y.md`.
3. Archivos deprecados: renombrá con `.deprecated.jinja` por una versión,
   eliminá al release siguiente, documentá en CHANGELOG.

## Negative contract (lo que JAMÁS se genera)

Per DESIGN §15 — anti-patrones explícitos que el generador rechaza:

- `primevue`, `primeicons`, `@primevue/themes/aura` en JS
- `inertia-django` en Python
- `bun.lock` Y `package-lock.json` simultáneos
- `tasks/` en la raíz del proyecto
- `apps/demo/`, `apps/example/`, o cualquier app de ejemplo
- `apps/web/vue/components/HelloWorld.vue` ni `DashboardDemo.vue`
- AutoLogin endpoint con `@require_http_methods(["GET"])` (solo vía `module-autologin-tests360` con POST)
- `seed_data` con valores hardcoded (`admin@example.com`, `Universum_2026*`)
- `SECRET_KEY` fallback hardcoded en cualquier settings file
- `DEBUG` parsing con `== "true"` case-sensitive
- `ALLOWED_HOSTS` con default `[""]` o `["*"]` en `production.py`
- `django.contrib.admin.ModelAdmin` como clase base (debe ser `unfold.admin.ModelAdmin` cuando `admin=unfold`)
- `django-debug-toolbar` en `base.py` o `local.py` por defecto
- `LoginRateLimitMiddleware` definida pero no en `MIDDLEWARE`
- `SIDES_NAV` legacy en Unfold settings
- Vue demo components con imports de PrimeVue
- `pyproject.toml` con `name="django-boilerplate-v2"` (debe ser el slug)
- Dockerfile corriendo como root, sin HEALTHCHECK, con `COPY . /app` mal armado
- `docker-compose.yml` con `POSTGRES_PASSWORD=postgres` hardcoded

## Skill Resolution

Skill Resolution: paths-injected — loaded listed skill paths