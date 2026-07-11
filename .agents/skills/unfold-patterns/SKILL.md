---
name: unfold-patterns
description: >
  TRIGGER: trabajando en un proyecto generado con admin=true, en apps/*/admin/*.py,
  en config/settings/unfold.py.jinja, en UNFOLD dict, en unfold.admin.ModelAdmin,
  en SIDEBAR / TABS, en @action / @display de unfold, en
  unfold.contrib.filters, en UnfoldAdminSite, o en AuditLog dentro del admin.
  Cubre SOLO patrones específicos de django-unfold en este generator:
  UNFOLD dict aislado en config/settings/unfold.py, SIDEBAR (nunca SIDES_NAV),
  TABS, ModelAdmin extendiendo unfold.admin.ModelAdmin, los 4 tipos de @action,
  @display labels, filtros nativos (ChoicesDropdownFilter, RelatedDropdownFilter,
  RangeDateFilter, AutocompleteSelectFilter, FieldTextFilter), widgets seguros
  para EncryptedCharField, monkey-patch de UnfoldAdminSite en config/urls.py.jinja,
  y cómo AuditLog / secure-endpoints se ven en admin.
license: MIT
metadata:
  version: "1.0"
  scope: admin
  applies_when: "admin=true (default). NO aplicar si admin=false."
---

## Cuándo usarla

Estás en un proyecto generado por este generator donde `admin=true` y tocás:

- `config/settings/unfold.py.jinja` (el dict UNFOLD aislado)
- `apps/accounts/admin/user_admin.py.jinja` o cualquier otro `apps/<app>/admin/*.py`
- `config/urls.py.jinja` (la sección del monkey-patch `UnfoldAdminSite`)
- `django-unfold`, `unfold.admin`, `unfold.decorators`, `unfold.contrib.*` imports
- `@action(...)`, `@display(...)`, `ChoicesDropdownFilter`, etc.
- AuditLog (`apps/core/audit/models.py.jinja`) expuesto en admin

## Cuándo NO usarla

- **Si `admin=false`**: esta skill NO aplica. Unfold no se instala,
  `django.contrib.admin` ni siquiera está en `INSTALLED_APPS`. Verificá
  `config/settings/base.py.jinja` — si `DJANGO_APPS` no incluye
  `django.contrib.admin`, esta skill es irrelevante. Usá `django-patterns` para
  el resto.
- **Si estás tocando `templates/cotton/` o `static/css/main.css`**: pertenece
  a `frontend-patterns`.
- **Patrones Django genéricos** (BaseModel, settings split, RateLimitMiddleware,
  structlog, EncryptedCharField semantics): ver `django-patterns`. Esta skill NO
  los repite.

## Boundary table

| Concern | Skill responsable |
|---|---|
| UNFOLD dict + SIDEBAR + TABS + COLORS + COMMAND + LOGIN | unfold-patterns |
| `unfold.admin.ModelAdmin` base class | unfold-patterns |
| `@action`, `@display`, filtros nativos | unfold-patterns |
| `UnfoldAdminSite` monkey-patch en `config/urls.py` | unfold-patterns |
| AuditLog + django_q en sidebar | unfold-patterns |
| EncryptedCharField en admin forms | unfold-patterns (UNIQUE aquí) |
| BaseModel / soft-delete | django-patterns (no esta) |
| Settings split / Fernet activation | django-patterns |
| EncryptedCharField (definición) | django-patterns |
| HTMX/Alpine/cotton/Preline | frontend-patterns (no esta) |
| Vue SFCs / vue-router | vue-spa-patterns (no esta) |

---

## 1. UNFOLD dict aislado en `config/settings/unfold.py.jinja`

El dict `UNFOLD` vive en `config/settings/unfold.py.jinja`. Sólo se genera
cuando `admin=true`. `base.py.jinja` lo importa al final con:

```python
# config/settings/base.py.jinja (sólo si admin=true)
from config.settings import unfold  # noqa: E402
UNFOLD = unfold.UNFOLD
```

Si necesitás cambiar branding, sidebar, tabs, colores, login, command palette,
**editá sólo `unfold.py.jinja`**. NO lo mezcles en `base.py.jinja`. Eso
mantiene el settings file de infraestructura limpio y evita que el import se
rompa en `local.py`/`test.py` (que heredan de `base.py`).

### Secciones disponibles en este generator

| Key | Propósito | Ejemplo |
|---|---|---|
| `SITE_TITLE` / `SITE_HEADER` / `SITE_SUBHEADER` / `SITE_URL` | branding | `"{{ project_name }}"` |
| `SITE_FAVICONS` | favicons múltiples | `[]` (extensibles vía overrides del proyecto) |
| `LOGIN` | pantalla de login custom | `{"redirect_url": "/admin/", "logo": []}` |
| `SIDEBAR` | navegación lateral | ver §2 |
| `TABS` | tabs superiores | ver §3 |
| `COLORS` | paleta OKLCH/hex | `{"primary": "#3b82f6", ...}` |
| `STYLES` / `SCRIPTS` | assets compilados cuando hay frontend | `["css/dist.css"]`, `["js/preline.js"]` |
| `ENVIRONMENT` | callable que devuelve badge | `_environment` |
| `COMMAND` | cmd+k palette (disable cuando prod) | `_disable_command_in_production` |
| `SHOW_HISTORY` / `EDITABLE_INLINES` | flags | ambos `True` |

**`SIDES_NAV` está prohibido.** Es la versión legacy de Unfold; el
`django-boilerplate-v2` aún la aceptaba. Acá solo se acepta `SIDEBAR`. Si tu
proyecto la trae, está mal portado — reemplazá todos los `SIDES_NAV` por
`SIDEBAR` (la estructura interna es idéntica).

## 2. SIDEBAR — grupos + items

```python
# config/settings/unfold.py.jinja (extracto)
"SIDEBAR": {
    "show_search": True,
    "show_all_applications": False,
    "navigation": [
        {
            "title": "Usuarios",
            "icon": "people",            # Material Symbols name
            "separator": True,           # separador arriba
            "collapsible": True,
            "items": [
                {"title": "Usuarios", "icon": "person", "link": "/admin/accounts/user/"},
                {"title": "Grupos", "icon": "group", "link": "/admin/auth/group/"},
            ],
        },
        # Grupo "Task Queue" sólo si include_jobs=true
        # Grupo "Tenants" sólo si include_multitenant=true
    ],
},
```

Cada item acepta: `title`, `icon`, `link`, `badge` (callable o str),
`permission` (callable o str), `active` (callable para highlight dinámico).

## 3. TABS

```python
"TABS": [
    {"title": "Dashboard", "icon": "dashboard", "link": "/admin/", "items": []},
],
```

El generator emite un único tab ("Dashboard") por default. Para agregar más
tabs cuando el proyecto tenga vistas custom, agregalas en
`config/settings/unfold.py.jinja` (no en `base.py`).

## 4. ModelAdmin — SIEMPRE `unfold.admin.ModelAdmin`

```python
# apps/<app>/admin/<feature>_admin.py
from django.contrib import admin
from unfold.admin import ModelAdmin

from apps.<app>.models import MyModel


@admin.register(MyModel)
class MyModelAdmin(ModelAdmin):
    list_display = ("name", "is_active", "created_at")
    list_filter = ("is_active",)
    search_fields = ("name",)
    ordering = ("-created_at",)
```

**Reglas**:

- NUNCA extender `django.contrib.admin.ModelAdmin`. Eso dejaría a Unfold sin
  tema y rompería la integración.
- El base class correcto es `unfold.admin.ModelAdmin` (re-exportado también
  desde `unfold import ModelAdmin`).
- Para actions/display/filters, importá SIEMPRE desde `unfold.decorators`,
  `unfold.enums`, `unfold.contrib.filters.admin`.
- El admin sigue aceptando TODAS las opciones estándar de Django
  (`list_display`, `fieldsets`, `readonly_fields`, etc.) — Unfold las honra y
  las estilea.

## 5. `@action` — 4 ubicaciones

```python
from unfold.decorators import action
from unfold.enums import ActionVariant


@action(
    description="Aprobar",
    icon="check_circle",
    variant=ActionVariant.SUCCESS,
    permissions=["change"],  # Django permission name
)
def approve_record(self, request, object_id):
    # ... business logic ...
    return None  # re-render de la página (None) o HttpResponse
```

| Atributo del ModelAdmin | Ubicación en UI | Firma |
|---|---|---|
| `actions_list` | top del changelist | `(self, request, **kwargs)` |
| `actions_row` | por fila del changelist | `(self, request, object_id)` |
| `actions_detail` | top del changeform | `(self, request, object_id)` |
| `actions_submit_line` | junto a "Save" | `(self, request, obj)` |

`variant` viene de `unfold.enums.ActionVariant` (default, primary, success,
info, warning, danger). NUNCA `variant="success"` como string — usar el enum.

## 6. `@display` — labels por valor

```python
from unfold.decorators import display


@display(
    description="Estado",
    label={
        "draft": "warning",
        "published": "success",
        "archived": "danger",
    },
    ordering="status",
)
def status_display(self, obj):
    return obj.status
```

Opciones útiles: `boolean=True` (renderiza check/cross), `image=True`,
`header=True` (sub-table header), `empty_value="-"`. Colores disponibles:
`default, primary, success, info, warning, danger`.

## 7. Filtros nativos de Unfold

```python
from unfold.contrib.filters.admin import (
    ChoicesDropdownFilter,
    RelatedDropdownFilter,
    RangeDateFilter,
    AutocompleteSelectFilter,
    FieldTextFilter,
)


@admin.register(Deal)
class DealAdmin(ModelAdmin):
    list_filter = [
        "status",                                    # default Unfold-styled
        ("status", ChoicesDropdownFilter),            # dropdown explícito
        ("customer", RelatedDropdownFilter),
        ("owner", AutocompleteSelectFilter),          # requiere search_fields en su admin
        ("title", FieldTextFilter()),
        ("created_at", RangeDateFilter),
    ]
    list_filter_sheet = True
    list_filter_submit = False
```

`AutocompleteSelectFilter` requiere que el ModelAdmin del modelo relacionado
declare `search_fields`. Sin eso, la vista falla con `ImproperlyConfigured`.

## 8. `UnfoldAdminSite` monkey-patch en `config/urls.py.jinja`

Ocurre ANTES de registrar cualquier ModelAdmin:

```python
# config/urls.py.jinja (extracto, sólo si admin=true)
from django.contrib import admin
from unfold.sites import UnfoldAdminSite

admin.site.__class__ = UnfoldAdminSite

from allauth.account.decorators import secure_admin_login
admin.site.login = secure_admin_login(admin.site.login)
```

Si el orden se invierte (registrar ModelAdmin antes del monkey-patch), Unfold
queda inactivo para esas vistas — un bug clásico al customizar admin. NO
mover este bloque.

## 9. EncryptedCharField en admin — excluir SIEMPRE

`EncryptedCharField`, `EncryptedTextField`, `EncryptedJSONField` se
desencriptan al leer del ORM. Si aparecen en un form admin, un usuario con
permiso `change_xxx` ve el secreto en texto plano.

```python
# apps/payments/admin/gateway_admin.py
from unfold.admin import ModelAdmin


@admin.register(GatewayConfig)
class GatewayConfigAdmin(ModelAdmin):
    exclude = ("api_key", "webhook_secret")  # ← NUNCA listar en fieldsets/add_fieldsets
    readonly_fields = ("gateway", "environment")
```

Cuando necesites permitir ROTAR un secreto sin mostrar el viejo:

```python
from unfold.contrib.forms.widgets import UnfoldAdminPasswordToggleWidget


@admin.register(GatewayConfig)
class GatewayConfigAdmin(ModelAdmin):
    formfield_overrides = {
        EncryptedCharField: {
            "widget": UnfoldAdminPasswordToggleWidget(
                attrs={"autocomplete": "off", "placeholder": "••••••••"},
            ),
        },
    }
    fieldsets = (
        (None, {"fields": ("gateway", "environment", "api_key", "webhook_secret")}),
    )
```

El widget `UnfoldAdminPasswordToggleWidget` es de `unfold.contrib.forms`
(instalado por default en este generator). Si tu admin tiene Encrypted*Fields
y NO excluís + widget, tenés una vulnerabilidad de disclosure.

## 10. AuditLog + secure-endpoints en admin

Si `module-secure-endpoints` está activo, `apps.core.audit.models.AuditLog`
está en `INSTALLED_APPS`. Para exponerlo en el sidebar del admin:

```python
# apps/core/audit/admin.py (crear manualmente — el generator NO lo crea)
from django.contrib import admin
from unfold.admin import ModelAdmin

from apps.core.audit.models import AuditLog


@admin.register(AuditLog)
class AuditLogAdmin(ModelAdmin):
    list_display = ("created_at", "actor_id", "action", "entity_type", "entity_id")
    list_filter = ("action", "entity_type")
    search_fields = ("entity_type", "entity_id", "actor_id")
    ordering = ("-created_at",)
    readonly_fields = tuple(f.name for f in AuditLog._meta.fields)
    # No list_editable, no add permission (append-only)
    def has_add_permission(self, request):
        return False
    def has_delete_permission(self, request, obj=None):
        return False
    def has_change_permission(self, request, obj=None):
        return False
```

Agregá el grupo en `config/settings/unfold.py.jinja` bajo `SIDEBAR`:

```python
{
    "title": "Auditoría",
    "icon": "history",
    "separator": True,
    "collapsible": True,
    "items": [
        {"title": "AuditLog", "icon": "fact_check", "link": "/admin/audit/auditlog/"},
    ],
},
```

## 11. django-q2 en sidebar (sólo `include_jobs=true`)

El `unfold.py.jinja` ya incluye el grupo "Tareas Programadas" cuando
`include_jobs=yes`. NO lo declares a mano — ya está. Si querés cambiar los
labels, editá ese grupo en `unfold.py.jinja`.

---

## Antipatterns del auditor (NO hacer)

| Anti-patrón | Origen | Por qué está excluido | Mitigación |
|---|---|---|---|
| Extender `django.contrib.admin.ModelAdmin` | boilerplates viejos | Sin Unfold, no hay tema | SIEMPRE `from unfold.admin import ModelAdmin` |
| Usar `SIDES_NAV` legacy | django-boilerplate-v2 | Deprecated en Unfold | Sólo `SIDEBAR`. Si tenés `SIDES_NAV`, migrá ahora. |
| EncryptedCharField en `fieldsets` sin `exclude` ni readonly | inpacto-pagos-ghl | Disclosure: cualquier user con `change_*` ve el secreto | Usá `exclude=` o `UnfoldAdminPasswordToggleWidget` |
| `variant="success"` como string en `@action` | django-boilerplate-v2 | String es frágil frente a renames del enum | `variant=ActionVariant.SUCCESS` |
| Monkey-patch de `UnfoldAdminSite` DESPUÉS de `@admin.register(...)` | django-boilerplate-v2 | ModelAdmins ya quedaron registrados con la clase default | El monkey-patch vive en `config/urls.py.jinja` ANTES de cualquier import que registre admins |
| Definir el dict `UNFOLD` en `base.py.jinja` directamente | boilerplates viejos | Mezcla infraestructura con branding | Mantener aislado en `config/settings/unfold.py.jinja` |
| `@admin.register(Foo)` con `class FooAdmin(admin.ModelAdmin)` | este generator | Queda sin tema Unfold | `class FooAdmin(unfold.admin.ModelAdmin)` |
| AuditLog editable en admin (allow change/delete) | inpacto-pagos-ghl | Append-only es la garantía legal | Override `has_add_permission`, `has_change_permission`, `has_delete_permission` para devolver `False` |
| Hardcodear icon strings en lugar de usar el dict del design | boilerplates viejos | Inconsistencia visual | Mantener el set de Material Symbols declarado en `unfold.py.jinja` |

---

## Lo que NO está cubierto acá

- Detrás de la pantalla de login custom (`UNFOLD["LOGIN"]`) hay markup Preline
  que vive en `static/js/preline.js` cuando `frontend=server-rendered`. Para
  customizar copy/illustrations, ver `frontend-patterns` §"Form patterns".
- Si `module-multitenant` está activo con `multitenant_isolation=logical`:
  `TenantMiddleware` (`apps.tenants.middleware.TenantMiddleware`) corre antes
  de las vistas de admin, así que los `TenantAwareModelMixin` filtran por
  organización. Para el superuser escape hatch, ver
  `apps/tenants/middleware.py.jinja` (sólo `is_superuser=True` con audit).
- Mensajes del command palette (`UNFOLD["COMMAND"]`): para agregar entradas
  custom, ver docs de Unfold. Acá sólo documentamos `_disable_command_in_production()`.
