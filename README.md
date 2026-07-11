# django-generator

> **Tu navaja suiza de scaffolding Django 6.** Un template Copier que produce proyectos production-ready con un solo comando. 30 commits, 4 escenarios auditados, 13 módulos opt-in.

`django-generator` toma 8 decisiones clave (`api`, `admin`, `frontend`,
`persists_sensitive_data`, `include_jobs`, `include_multitenant`, `package_manager`,
`vue_router`) y un JSON con los módulos opt-in, y escupe un proyecto Django 6
listo para `copier update`. **No es Cookiecutter** — usa Copier, que permite
evolucionar proyectos con migrations declarativas en vez de overwrite.

## ¿Cómo se usa?

### Crear un proyecto nuevo

```bash
# Interactivo — te pregunta todo
copier copy /path/to/django-generator /ruta/al/nuevo_proyecto

# Con todas las respuestas por CLI (útil en CI)
copier copy --defaults \
  -d project_name="Mi App" -d project_slug=mi_app \
  -d admin=true -d frontend=true -d frontend_style=server-rendered \
  /path/to/django-generator /ruta/al/nuevo_proyecto

# Con un archivo de respuestas
copier copy --force --trust --data-file answers.yml \
  /path/to/django-generator /ruta/al/nuevo_proyecto
```

### Setup post-generación

```bash
cd /ruta/al/nuevo_proyecto
cp .env.example .env       # editar SECRET_KEY, DATABASE_URL, etc.
uv sync                    # o pip install -e .
uv run python manage.py migrate
uv run pytest              # corre los tests locked-in
uv run python manage.py runserver
```

### Evolucionar un proyecto existente (la killer feature de Copier)

```bash
cd mi_proyecto_existente
copier update
```

Copier compara el estado actual con la versión del template y aplica las
**migrations** (scripts `v0.1_to_v0.2.md` etc.) que vos definas en el template.
Tu código local se respeta — sólo se actualiza lo que cambió.

## Los 3 ejes ortogonales

El generador tiene **3 ejes independientes** que combinás según el proyecto.
Cada eje tiene default y opciones cerradas.

### Eje `api` (opt-in, default OFF)

| Opción | Instala | Default |
|---|---|---|
| `false` (default) | nada | — |
| `true` | `django-ninja`, `pydantic` | monta `apps/api/router.py` en `/api/` |

### Eje `admin` (opt-out, default ON)

| Opción | Instala | Notas |
|---|---|---|
| `false` | nada | ni siquiera `django.contrib.admin` |
| `true` (default) | `django-unfold`, `django-allauth` | Unfold reemplaza al admin estándar; allauth provee login |

**Regla dura**: `django.contrib.admin` jamás aparece como dependencia
default. Cuando `admin=false`, ni siquiera está en `INSTALLED_APPS`.

### Eje `frontend` (opt-in, default OFF)

| Opción | Stack | Notas |
|---|---|---|
| `false` (default) | nada | API-only o scripts |
| `server-rendered` | Preline + HTMX + Alpine + django-cotton + Vite + Tailwind v4 | `templates/cotton/`, `apps/web/` |
| `vue-spa` | Vue 3 + Vite SPA + Preline + django-vite + auth Django-side | `apps/web/vue/`, login contra `/accounts/login/` |

`package_manager`: `npm` (default) | `bun`. **Nunca los dos.**

`vue_router`: `history` (default) | `hash`. Solo aplica a `frontend_style=vue-spa`.

## Los 13 módulos opt-in

Activás los que necesitás como `optional_modules: ["module-foo", "module-bar"]`.
Hay 5 módulos que **activan Fernet automáticamente** (instalación de
`cryptography` + `EncryptedCharField` + `EncryptedJSONField`).

| Módulo | Activa Fernet | Crea apps | Notas |
|---|:-:|---|---|
| `module-secure-endpoints` | ✓ | `apps/core/{idempotency,audit,webhooks}/` | HMAC verifier + Idempotency-Key + AuditLog |
| `module-wompi` | ✓ | `apps/payments/wompi/` | State machine de pagos Colombia |
| `module-ghl` | ✓ | `apps/integrations/ghl/` | OAuth + cliente v2 con retry/backoff |
| `module-supabase` | ✓ | `apps/integrations/supabase/` | anon (lectura) + service_role (mutación) split |
| `module-multitenant` | — | `apps/tenants/` | Sub-opción `isolation=logical` (default) o `schema` |
| `module-realtime` | — | `apps/realtime/` | Channels + channels-redis (cambia ASGI) |
| `module-django-guard` | — | — | Permisos por objeto |
| `module-autologin-tests360` | ✓ | `apps/accounts/autologin/` | Magic-links POST-only (NO GET) |
| `module-debug-toolbar` | — | — | Solo en `local.py`, nunca en producción |
| `module-docker` | — | — | Multi-stage + `USER app` + healthcheck |
| `module-precommit` | — | — | ruff + mypy hooks |
| `module-github-ci` | — | — | CI workflow |

**Trigger de Fernet** (cualquiera activa): `persists_sensitive_data=yes`
OR cualquiera de los 5 marcados ✓ arriba.

## 6 ejemplos comunes

### 1. Landing pura (b2bcg-equivalent)

```yaml
# answers.yml
project_name: Test Landing
project_slug: test_landing
admin: false
frontend: true
frontend_style: server-rendered
package_manager: npm
persists_sensitive_data: false
```

### 2. Multi-tenant con magic-links (tests-360-equivalent)

```yaml
project_name: Test Multitenant
project_slug: test_mt
admin: true
persists_sensitive_data: true
include_multitenant: true
multitenant_isolation: logical
optional_modules:
  - module-multitenant
  - module-django-guard
  - module-autologin-tests360
```

### 3. Payments + integraciones (inpacto-pagos-ghl slice)

```yaml
project_name: Test Pagos
project_slug: test_pagos
admin: true
api: true
frontend: true
frontend_style: server-rendered
persists_sensitive_data: true
include_multitenant: true
multitenant_isolation: logical
optional_modules:
  - module-secure-endpoints
  - module-wompi
  - module-ghl
  - module-multitenant
```

### 4. Vue SPA standalone

```yaml
project_name: Test Vue
project_slug: test_vue
admin: true
frontend: true
frontend_style: vue-spa
vue_router: history
package_manager: bun
```

### 5. API-only (Django-Ninja, sin UI)

```yaml
project_name: My API
project_slug: my_api
api: true
admin: false
frontend: false
optional_modules:
  - module-secure-endpoints
  - module-docker
  - module-github-ci
```

### 6. Backoffice Unfold con jobs y CI

```yaml
project_name: My Backoffice
project_slug: my_backoffice
admin: true
include_jobs: true
jobs_backend: orm
optional_modules:
  - module-docker
  - module-precommit
  - module-github-ci
  - module-debug-toolbar
```

## Actualizar proyectos existentes

```bash
cd mi_proyecto
copier update
```

Copier usa 3 cosas:

1. `.copier-answers.yml` (generado automáticamente en `copier copy`) — las
   respuestas originales del usuario.
2. `_commit` o `version` en el `copier.yml` del template — el "tag" del template.
3. `_migrations/*.md` — scripts de migración entre versiones.

Si el template subió de v0.1 a v0.2, Copier aplica `v0.1_to_v0.2.md` antes
de re-aplicar. **Conflictos en archivos que vos customizaste localmente** se
resuelven vía 3-way merge; los cambios incompatibles se promptan al usuario.

## Skills del generador

Cuando generás un proyecto, las 4 skills del template se inyectan a
`.agents/skills/` del proyecto generado:

| Skill | Cuándo aplica | Cubre |
|---|---|---|
| `django-patterns` | siempre (base) | BaseModel, soft delete, settings split, custom User, Fernet, structlog, RateLimitMiddleware atómico |
| `unfold-patterns` | `admin=unfold` | SIDEBAR (no SIDES_NAV), @action/@display, filtros nativos, encrypted fields en admin: SIEMPRE `exclude` |
| `frontend-patterns` | `frontend != none` | Preline + HTMX + Alpine + cotton + Vite + Tailwind v4 CSS-first |
| `vue-spa-patterns` | `frontend=vue-spa` | Vue 3 + Vite SPA + Preline + django-vite + auth Django-side (NO JWT, NO localStorage) |

Las skills son **read-only** en el proyecto generado. Si necesitás
extenderlas, copialas y versionálas localmente.

## Estado de validación

- **30 commits** sobre `feat/mvp-copier-template`.
- **4 escenarios auditados** validados contra los proyectos reales de origen:
  - `b2bcg` (Test Landing) — server-rendered puro, sin admin
  - `tests-360` (Test Multitenant) — unfold + multitenant logical + autologin
  - `inpacto-pagos-ghl` (Test Pagos) — admin + api + frontend + secure/wompi/ghl/multitenant
  - `vue-spa` (Test Vue) — admin + frontend vue-spa con bun
- **19 combinaciones módulo ON/OFF** testeadas vía `scripts/validate_modules.py`.
- **manage.py check + pytest** verdes en los 4 escenarios.

## Estructura del repo

```
django-generator/                              ← el generador (no el generado)
├── copier.yml                                 ← schema de preguntas (locked en DESIGN §9)
├── DESIGN.md (externo)                        ← 1013 líneas, fuente de verdad
├── README.md                                  ← este archivo
├── CHANGELOG.md                               ← historial de phases
├── pyproject.toml.jinja                       ← deps condicionales
├── manage.py.jinja
├── pytest.ini.jinja
├── Makefile.jinja
├── .editorconfig                              ← estático (sin .jinja)
├── .gitignore
├── .env.example.jinja
├── apps/
│   ├── core/                                  ← siempre generado
│   ├── accounts/                              ← solo si admin=unfold
│   ├── web/                                   ← solo si frontend=true
│   ├── api/                                   ← solo si api=true
│   ├── tenants/                               ← solo si include_multitenant
│   ├── payments/wompi/                        ← solo si module-wompi
│   └── integrations/{ghl,supabase}/           ← solo si module-{ghl,supabase}
├── config/
│   ├── settings/{base,local,production,test,__init__,unfold}.py.jinja
│   ├── urls.py.jinja
│   └── {asgi,wsgi}.py.jinja
├── tests/                                     ← tests del template
├── scripts/validate_modules.py                ← matrix de validación
├── templates/
│   ├── base.html.jinja                        ← solo si frontend=true
│   └── cotton/{ui,layout,forms}/              ← solo si frontend=server-rendered
├── static/{js,css}/                           ← solo si frontend=server-rendered
└── .agents/skills/                            ← 4 SKILL.md files
```

## Convenciones del template

- `.jinja` suffix en todo archivo que necesita templating.
- `.editorconfig`, `.gitignore` sin `.jinja` (estáticos).
- **Directorios condicionales**: `apps/{% if admin %}accounts{% endif %}/` —
  el directorio entero se omite cuando la condición es falsa.
- **Archivos condicionales**: nombre con `{% if cond %}foo{% endif %}.jinja` —
  el archivo no se genera cuando la condición es falsa (218 char max por el
  límite de ext4).
- `copier.yml _exclude` lista los archivos que NO se copian al proyecto
  generado (este README, DESIGN.md, CHANGELOG.md, scripts/, .agents/, .git/).

## Cómo validar el template

```bash
# Validación completa de los 4 escenarios (necesita Python 3.12 + uv)
python3 scripts/validate_modules.py

# Validación de un solo escenario
python3 -c "
import json, subprocess
answers = {
  'project_name': 'Test', 'project_slug': 'test_app',
  'admin': True, 'frontend': True, 'frontend_style': 'server-rendered',
}
with open('/tmp/ans.yml', 'w') as f:
    for k, v in answers.items():
        f.write(f'{k}: {json.dumps(v) if isinstance(v, bool) else v}\n')
subprocess.run(['copier', 'copy', '--force', '--trust', '--data-file', '/tmp/ans.yml', '.', '/tmp/test_app'])
"
cd /tmp/test_app
cp .env.example .env
echo 'SECRET_KEY=xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx' >> .env
uv venv .venv --python /usr/bin/python3.12
uv pip install --python .venv/bin/python -e . pytest pytest-django model-bakery
DEBUG=true DJANGO_SETTINGS_MODULE=config.settings.test \
  .venv/bin/python manage.py check
DEBUG=true DJANGO_SETTINGS_MODULE=config.settings.test DJANGO_ENVIRONMENT=test \
  SECRET_KEY=xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx \
  .venv/bin/python -m pytest tests/ -q
```

## Licencia

MIT — Gentleman Programming.

## Referencias

- [DESIGN.md](../django-generator-design/DESIGN.md) — fuente de verdad (1013 líneas)
- [Copier docs](https://copier.readthedocs.io/) — `copier copy`, `copier update`
- [django-unfold](https://github.com/unfoldadmin/django-unfold) — admin por defecto
- [django-cotton](https://github.com/wrabit/django-cotton) — componentes server-rendered