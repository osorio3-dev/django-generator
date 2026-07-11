---
name: django-patterns
description: >
  TRIGGER: trabajando en un proyecto generado por django-generator con
  apps/*/models/*.py, config/settings/*.py, BaseModel, apps.core,
  apps/accounts/User, EncryptedCharField, RateLimitMiddleware, structlog,
  start_feature_app, o cuando el usuario toca patrones Django universales.
  Cubre la capa `base` always-on del generador: BaseModel + soft delete,
  settings split (base/local/production/test), structlog + redact_sensitive_keys,
  RateLimitMiddleware atómico, Fernet conditional, validators de SECRET_KEY /
  ALLOWED_HOSTS / DEBUG, custom User (cuando admin=unfold), EncryptedCharField /
  EncryptedTextField / EncryptedJSONField, AccountAdapter de allauth,
  HMAC verifiers, management commands y logging best-practices.
license: MIT
metadata:
  version: "1.0"
  scope: base
  applies_when: "siempre (capa base activa en todo proyecto generado)"
---

## Cuándo usarla

Estás trabajando en un proyecto generado por este generador y tocás alguno de
estos archivos o símbolos:

- `apps/core/models/base.py` (BaseModel, SoftDeleteQuerySet, GlobalManager)
- `config/settings/base.py.jinja` o `config/settings/{local,production,test}.py.jinja`
- `apps/core/middleware/ratelimit_middleware.py.jinja` (RateLimitMiddleware)
- `apps/core/utils/{logging_config,crypto}.py.jinja`
- `apps/core/models/fields.py.jinja` (EncryptedCharField — sólo si Fernet activo)
- `apps/accounts/models/user.py.jinja` (sólo con `admin=true`)
- `apps/accounts/adapters/account_adapter.py.jinja`
- `apps/core/management/commands/start_feature_app.py.jinja`
- Cualquier modelo que herede de `BaseModel` o manager `objects`/`all_objects`

## Cuándo NO usarla

- Estás tocando `apps/<app>/admin/*` y admin=unfold → usá `unfold-patterns`.
- Estás tocando `templates/cotton/*`, `static/css/main.css`, `apps/web/vite/*` → usá `frontend-patterns`.
- Estás tocando `apps/web/vue/**`, `.vue` files, `apps/web/vue/components/Pages/*` → usá `vue-spa-patterns`.
- Estás tocando módulos específicos (`module-wompi`, `module-ghl`, etc.) → esas skills viven con cada módulo.

## Boundary table

| Concern | Skill responsable |
|---|---|
| BaseModel / soft-delete / models/ | django-patterns |
| Settings split / validadores | django-patterns |
| RateLimitMiddleware atómico | django-patterns |
| structlog + redact_sensitive_keys | django-patterns |
| Fernet conditional | django-patterns |
| EncryptedCharField / EncryptedTextField / EncryptedJSONField | django-patterns (definición) + unfold-patterns (admin rendering) |
| Custom User (email-first) | django-patterns |
| AccountAdapter (allauth) | django-patterns |
| HMAC verifiers | django-patterns |
| Management commands (start_feature_app) | django-patterns |
| UNFOLD dict / ModelAdmin / sidebar | unfold-patterns (no esta) |
| Preline / HTMX / Alpine / cotton / Vite | frontend-patterns (no esta) |
| Vue 3 + vue-router + .vue SFCs | vue-spa-patterns (no esta) |

---

## 1. BaseModel + soft delete

Todos los modelos del proyecto heredan de `BaseModel` (declarado en
`apps/core/models/base.py.jinja`). La implementación concreta aporta:

- `objects` (manager default que EXCLUYE soft-deleted)
- `all_objects` (manager global que incluye soft-deleted)
- `delete()` → soft-delete (setea `deleted_at`)
- `hard_delete()` → borrado físico
- `restore()` → limpia `deleted_at`
- `is_deleted` (property)
- `SoftDeleteQuerySet` con `active()`, `deleted()`, `hard_delete()`, `restore()`

```python
# apps/billing/models/invoice.py
from apps.core.models.base import BaseModel


class Invoice(BaseModel):
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    customer_email = models.EmailField()

    # NO declares objects ni all_objects — los hereda de BaseModel.
```

Convención:

- Queries de UI / API → `MyModel.objects.filter(...)`. Sólo activos.
- Admin / jobs / data recovery → `MyModel.all_objects.filter(deleted_at__isnull=False)` o `MyModel.all_objects.deleted()`.
- Para "borrar definitivamente" → `obj.hard_delete()` o `qs.hard_delete()`.
- Si el manager default devuelve un queryset vacío y no estás en un test, casi
  siempre es un soft-delete filtrado de más.

## 2. Settings split (base / local / production / test)

`config/settings/__init__.py.jinja` detecta `DJANGO_SETTINGS_MODULE` y carga el
módulo correspondiente. Los cuatro entornos:

| Archivo | DEBUG | DB | Notas |
|---|---|---|---|
| `base.py` | env (`_parse_bool_env`) | SQLite por default | infraestructura compartida |
| `local.py` | `True` | SQLite | ALLOWED_HOSTS `["*"]`, email console, LocMemCache |
| `production.py` | `False` (forzado) | PostgreSQL (env) | HSTS, secure cookies, validators |
| `test.py` | `False` | SQLite `:memory:` | `PASSWORD_HASHERS = MD5PasswordHasher` |

`production.py` SIEMPRE valida:

```python
# config/settings/production.py.jinja — invariantes que NO se tocan
_FORBIDDEN_PREFIXES = ("your-secret-key", "django-insecure-", "change-me")
if any(SECRET_KEY.startswith(p) for p in _FORBIDDEN_PREFIXES) or len(SECRET_KEY) < 50:
    raise ImproperlyConfigured("SECRET_KEY ...")


_cleaned_hosts = [h.strip() for h in ALLOWED_HOSTS if h.strip()]
if not _cleaned_hosts:
    raise ImproperlyConfigured("ALLOWED_HOSTS is empty or missing in production.")
```

DEBUG se parsea SIEMPRE via `_parse_bool_env(key)` en cualquier settings file
(acepta `"true"`, `"1"`, `"yes"`, case-insensitive). NUNCA hacer
`DEBUG == "true"` directamente.

## 3. RateLimitMiddleware — SIEMPRE montado

`apps.core.middleware.ratelimit_middleware.RateLimitMiddleware` aparece en
`MIDDLEWARE` por default en `base.py`. Es el bug que el `django-boilerplate-v2`
tenía: definir la clase pero no conectarla. Acá está conectada.

```python
# apps/core/middleware/ratelimit_middleware.py.jinja (default limits)
LIMITS = [
    ("/accounts/login/", 10, 300),    # 10 attempts / 5 min per IP
    ("/accounts/signup/", 5, 300),
    ("/api/", 120, 60),               # only when api=django-ninja
]
```

Para agregar un nuevo límite, editá la lista `LIMITS`. NO crear instancias
nuevas del middleware — eso rompería el orden en MIDDLEWARE y la atomicidad.

Implementación atómica con `cache.add` + `cache.incr` (resistente a race
conditions entre requests concurrentes). SI un path aparece en dos
`LIMITS`, gana la primera coincidencia por orden de declaración.

## 4. structlog con redact automático

`apps/core/utils/logging_config.py.jinja` configura structlog y aplica
`_redact_sensitive` automáticamente. La redacción es por **substring**
case-insensitive sobre las keys.

```python
import structlog

log = structlog.get_logger()

log.info("payment.processed",
         order_id=123,
         amount="100.00",
         card_number="4111-1111-1111-1111")   # → "card_number" redactado a "[REDACTED]"
```

Convención:

- Usá SIEMPRE `structlog.get_logger()` (no `logging.getLogger()`).
- Pasá kwargs nombrados en log calls: el redactor opera sobre keys.
- Para request-scoped context, usá `structlog.contextvars.bind_contextvars(...)`
  en middleware (no en views).
- En producción los logs salen en JSON; en `local.py` van en consola coloreada
  según `DEBUG`.

## 5. Fernet conditional (encryption at rest)

Fernet se auto-activa cuando `copier.yml` tiene:

- `persists_sensitive_data=yes`, OR
- cualquier módulo en `optional_modules` ∈ {`module-secure-endpoints`,
  `module-wompi`, `module-ghl`, `module-supabase`, `module-autologin-tests360`}.

Si NINGÚN trigger dispara, **NO** se incluye `cryptography` ni
`apps/core/models/fields.py.jinja`. No uses EncryptedCharField en proyectos
donde Fernet está apagado — ImportError al cargar `models.fields`.

```python
# apps/payments/models/gateway_config.py (sólo con Fernet activo)
from apps.core.models.fields import EncryptedCharField, EncryptedJSONField
from apps.core.models.base import BaseModel


class GatewayConfig(BaseModel):
    gateway = models.CharField(max_length=50)
    api_key = EncryptedCharField(max_length=255)        # NO DB max_length
    config_blob = EncryptedJSONField(default=dict)
```

`EncryptedCharField` hereda de `models.TextField` (NO `CharField`). El
`max_length` que pasás es **solo un hint para el form widget**, no un límite de
columna. Lo mismo aplica a `EncryptedTextField`. El ciphertext Fernet siempre
empieza con `"gAAAAA"` (version byte 0x80).

`FERNET_ENCRYPTION_KEY` se valida en `base.py.jinja` con `ImproperlyConfigured`
si está vacía cuando Fernet está activo. Generala con:

```bash
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

## 6. Custom User (cuando `admin=true`)

`apps/accounts/models/user.py.jinja` define `User(AbstractUser, BaseModel)`:

- `USERNAME_FIELD = "email"`
- `REQUIRED_FIELDS = []`
- `username = None` (desactivado)
- `display_name`, `avatar` añadidos
- Hereda soft-delete via `BaseModel`
- Manager custom en `apps/accounts/managers.py.jinja` combina
  `DjangoUserManager + SoftDeleteManager`

`AUTH_USER_MODEL = "accounts.User"` se setea en `base.py.jinja` solo cuando
`admin=true`. NO importar `User` directamente en código — usar
`django.contrib.auth.get_user_model()` o `settings.AUTH_USER_MODEL` para
referencias genéricas.

`apps/accounts/adapters/account_adapter.py.jinja` extiende
`DefaultAccountAdapter` para que `delete_user()` haga soft-delete y
`is_active()` rechace usuarios con `deleted_at` no nulo.

## 7. HMAC verifiers (siempre disponibles)

`apps/core/utils/crypto.py.jinja` provee DOS verifiers, independientes de
cualquier módulo:

```python
# Wompi-style: signature embedded in payload
from apps.core.utils.crypto import HMAC_SHA256Verifier

verifier = HMAC_SHA256Verifier(secret=settings.WOMPI_EVENT_SECRET)
is_valid = verifier.verify(request_payload)
```

```python
# Stripe/GHL-style: signature in a header, raw body elsewhere
from apps.core.utils.crypto import RawHMACSHA256Verifier

verifier = RawHMACSHA256Verifier(secret=settings.GHL_WEBHOOK_SECRET)
is_valid = verifier.verify(request.body, request.headers["X-Signature"])
```

SIEMPRE usan `hmac.compare_digest` (constant-time). NUNCA compares con `==`
para secretos. Los modulos `module-secure-endpoints` y `module-wompi`
re-exportan estos helpers desde sus propios `services/verifier.py`.

## 8. Management commands

`apps/core/management/commands/start_feature_app.py.jinja` scaffoldea una
nueva feature app con la estructura canónica:

```bash
python manage.py start_feature_app billing
```

Crea `apps/billing/` con `admin/`, `models/`, `views/`, `services/`, `forms/`,
`tests/` (todos con `__init__.py`), más `apps.py` y `urls.py`. Usá este command
cada vez que sumás una nueva app — no crees la estructura a mano.

## 9. Custom User backend (multitenant)

Si `include_multitenant=true` con `multitenant_isolation=logical` y
`module-django-guard` activos, `AUTHENTICATION_BACKENDS` añade
`guardian.backends.ObjectPermissionBackend` automáticamente. Los permisos por
objeto se manejan via `apps.accounts.models.user.object_permissions` (FK
many-to-many a `auth.Permission`).

---

## Antipatterns del auditor (NO hacer)

| Anti-patrón | Origen | Por qué está excluido | Cómo se ve en el generator |
|---|---|---|---|
| `LoginRateLimitMiddleware` definida pero no en `MIDDLEWARE` | django-boilerplate-v2 | Sin montar, no protege | `base.py.jinja` SIEMPRE lo agrega a MIDDLEWARE. Si lo ves montado a mano, remové — está duplicado. |
| `SECRET_KEY` con fallback hardcoded | inpacto-pagos-ghl (local.py) | Si el .env no carga, Django arranca con clave conocida | `base.py.jinja` usa `os.environ["SECRET_KEY"]` (KeyError si falta) + validator en production.py |
| `ALLOWED_HOSTS = os.environ.get(...).split(",")` → `[""]` | inpacto-pagos-ghl (production.py) | Lista vacía rompe request y desactiva CSRF | `production.py.jinja` valida `_cleaned_hosts` y levanta `ImproperlyConfigured` |
| `DEBUG = os.environ.get("DEBUG") == "true"` case-sensitive | inpacto-pagos-ghl | `"True"` y `"TRUE"` no matchean | Helper `_parse_bool_env()` en TODOS los settings files |
| `EncryptedCharField(models.CharField(max_length=N))` | django-boilerplate-v2 | CharField ignora el parámetro porque la impl real es TextField | `apps/core/models/fields.py.jinja` documenta explícitamente que `max_length` es solo UI hint |
| `from django.contrib.auth.models import User` directo | tests-360, boilerplates viejos | Si después se customiza User, los imports quedan rígidos | Usá `django.contrib.auth.get_user_model()` para referencias genéricas |
| Hacer `tasks/` directory en raíz | boilerplates viejos | Rompe convención `apps/<app>/tasks.py` | Generator NO crea `tasks/` raíz. Django-q2 se invoca como `async_task("apps.<app>.tasks.func_name")` |
| `seed_data` con `admin@example.com / admin` | django-boilerplate-v2 | Credential stuffing obvious | `seed_data.py.jinja` (cuando exista) usa email parametrizable + password con `get_random_secret_key()` |
| Usar EncryptedCharField cuando Fernet está OFF | este generator | ImportError — `apps/core/models/fields.py` no se genera | Verificá que `FERNET_AUTO_ACTIVATE=True` está activo antes de importar |
| Hacer `User.objects.create(...)` directo sin usar el manager combinado | este generator | El manager `UserManager()` combina `create_user` + soft-delete | Usá siempre `User.objects.create_user(...)` o `User.objects.create(...)` — el manager custom se encarga de soft-delete |

---

## Notas específicas de skills colindantes

- Para widgets de Unfold que renderizan EncryptedCharField en admin (ej.
  `UnfoldAdminPasswordToggleWidget`), ver `unfold-patterns`.
- Para django-cotton components que usen formularios con EncryptedCharField en
  frontend, ver `frontend-patterns` (no es patrón habitual — los encrypted
  fields son de admin, no de UI pública).
- Para el secreto `FERNET_ENCRYPTION_KEY` en `.env.example`, los módulos
  `secure-endpoints`, `wompi`, `ghl`, `supabase`, `autologin-tests360` lo
  inyectan automáticamente vía `base.py.jinja`.
