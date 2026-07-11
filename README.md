# django-generator

> Template Copier que genera proyectos Django 6 listos para `copier update`.

Genera proyectos con BaseModel + soft-delete, settings split, structlog,
RateLimitMiddleware atómico, custom User email-first (cuando `admin=unfold`),
y todas las convenciones locked-in del design doc.

## Cómo usar

### Crear un proyecto

```bash
copier copy /path/to/django-generator /path/to/nuevo_proyecto
```

Te va a preguntar:

- `project_name` — nombre legible
- `project_slug` — snake_case (se usa para el nombre de carpeta)
- `author_name` — default "Gentleman Programming"
- `python_version` — 3.12 | 3.13
- `database` — postgresql (default) | sqlite
- `api` — sí/no (django-ninja)
- `admin` — sí/no (Unfold si sí)
- `frontend` — sí/no (Preline+HTMX+Alpine si sí)
- `persists_sensitive_data` — activa Fernet
- `include_jobs` — django-q2
- `include_multitenant` / `include_docker` / `include_precommit` / `include_github_actions` / `include_debug_toolbar` / `include_playwright`
- `optional_modules` — JSON list con los 13 módulos opt-in

Con `--defaults` toma todos los defaults:

```bash
copier copy --defaults /path/to/django-generator /path/to/nuevo_proyecto
```

### Después de generar

```bash
cd nuevo_proyecto
cp .env.example .env        # editar SECRET_KEY y DB_*
uv sync                     # o pip install -e .
uv run python manage.py migrate
uv run pytest               # 3 tests incluidos
```

### Actualizar el template en un proyecto existente

```bash
cd mi_proyecto_existente
copier update
```

Las respuestas originales están en `.copier-answers.yml`.

## MVP scope actual

✅ Base layer + admin=unfold / admin=none funcionando end-to-end.
✅ Settings split (base / local / production / test) con SECRET_KEY y
   ALLOWED_HOSTS validators en producción.
✅ RateLimitMiddleware SIEMPRE en MIDDLEWARE (el bug que tenía
   django-boilerplate-v2).
✅ DEBUG parsing case-insensitive (`true`/`1`/`yes` en cualquier case).
✅ Custom User email-first + AccountAdapter + UserAdmin cuando admin=unfold.
✅ Fernet conditional activado por `persists_sensitive_data=yes`.

## Próximas fases

- Phase 3b: `config/settings/unfold.py` aislado + UNFOLD dict completo.
- Phase 3c: `apps/web/` con Preline + HTMX + Alpine + django-cotton (server-rendered)
  y Vue 3 SPA.
- Phase 3d: los 13 módulos opt-in (wompi, ghl, supabase, multitenant, etc.).
- Phase 3e: `module-debug-toolbar` / `module-docker` / `module-precommit` /
  `module-github-ci`.
- Skills del generador (`django-patterns`, `unfold-patterns`, `frontend-patterns`,
  `vue-spa-patterns`).

## Cómo validar este template

```bash
# Test rápido — genera un proyecto y verifica que check + pytest pasan
copier copy --defaults -d project_name=Test -d project_slug=test_app \
  . /tmp/test_app

cd /tmp/test_app
cp .env.example .env
uv venv .venv && uv pip install --python .venv/bin/python -e .
uv run make check   # debe decir "0 issues"
uv run make test    # debe decir "3 passed"
```

## Estructura del repo

```
django-generator/
├── copier.yml              # Schema de preguntas (locked en DESIGN.md §9)
├── pyproject.toml.jinja    # Deps condicionales (api/admin/frontend/jobs/Fernet)
├── manage.py.jinja
├── pytest.ini.jinja
├── README.md.jinja         # README en español para proyectos generados
├── Makefile.jinja          # make check / test / migrate / etc.
├── .editorconfig           # Estático (no .jinja)
├── .gitignore              # Estático
├── .env.example.jinja      # Vars por ambiente, condicional a las respuestas
├── apps/
│   ├── core/               # SIEMPRE generado
│   │   ├── models/base.py.jinja
│   │   ├── middleware/ratelimit_middleware.py.jinja
│   │   ├── utils/logging_config.py.jinja
│   │   ├── management/commands/start_feature_app.py.jinja
│   │   └── views/health.py.jinja
│   └── {% if admin %}accounts{% endif %}/   # SÓLO cuando admin=unfold
│       ├── models/user.py.jinja
│       ├── adapters/account_adapter.py.jinja
│       ├── admin/user_admin.py.jinja
│       └── migrations/0001_initial.py.jinja
├── config/
│   ├── settings/{base,local,production,test,__init__}.py.jinja
│   ├── urls.py.jinja
│   ├── wsgi.py.jinja
│   └── asgi.py.jinja
└── tests/
    ├── conftest.py.jinja
    └── test_health.py.jinja  # 3 tests: health + middleware + DEBUG parser
```

## Convenciones del template

- **`.jinja` suffix** para todo archivo que necesita templating.
- **`.editorconfig` y `.gitignore` sin `.jinja`** — son estáticos (mismo contenido
  para todos los proyectos).
- **Directorios condicionales** se nombran con `{% if var %}name{% endif %}` —
  ver `apps/{% if admin %}accounts{% endif %}/`.
- **`copier.yml` excluye** sus propios archivos (DESIGN.md, README.md, CHANGELOG.md,
  scripts/, .agents/) para no copiarlos a los proyectos generados.

## Licencia

MIT — Gentleman Programming