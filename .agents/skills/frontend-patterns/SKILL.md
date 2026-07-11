---
name: frontend-patterns
description: >
  TRIGGER: trabajando en un proyecto generado con frontend=server-rendered
  (el default cuando frontend=true), en templates/cotton/**/*.html, en
  templates/base.html.jinja, en apps/web/vite/entry.js,
  apps/web/vite/style.css, en apps/web/urls.py / views/landing.py / views/dashboard.py,
  o cuando el usuario toca Preline, HTMX (hx-get, hx-post, hx-target, hx-swap),
  Alpine.js (x-data, x-show, x-on:click), django-cotton (<c-ui.button>),
  django-vite (vite_asset, vite_hmr_client), Vite 6, o Tailwind v4 CSS-first.
  Cubre SOLO el stack server-rendered: Preline UI + HTMX + Alpine.js +
  django-cotton + Vite + Tailwind v4 CSS-first. NO cubre Vue 3 / vue-router /
  apps/web/vue/** (eso es vue-spa-patterns).
license: MIT
metadata:
  version: "1.0"
  scope: frontend
  applies_when: "frontend=true AND frontend_style=server-rendered"
---

## Cuándo usarla

Estás en un proyecto generado por este generator con `frontend=true` y
`frontend_style=server-rendered`. Tocás alguno de estos archivos:

- `templates/base.html.jinja` o `templates/cotton/**/*.html`
- `apps/web/vite/entry.js` y `apps/web/vite/style.css`
- `apps/web/urls.py.jinja` / `apps/web/views/{landing,dashboard}.py.jinja`
- `package.json` (Preline, HTMX, Alpine, Vite, Tailwind v4)
- `vite.config.ts.jinja` (cuando `frontend_style=server-rendered`)
- Cualquier `<c-...>` django-cotton component, o `hx-*` / `x-*` attributes

## Cuándo NO usarla

- **Si `frontend=false`**: NO existe `templates/`, NO hay package.json,
  NO hay Vite. Esta skill es irrelevante. NO instales Vite ni Preline a mano.
- **Si `frontend=vue-spa`**: usá `vue-spa-patterns` para Vue 3 +
  Composition API + vue-router + .vue SFCs. Algo de Vite/django-vite/Tailwind
  v4 es común pero las templates NO son django-cotton, NO hay HTMX/Alpine en
  el cliente. El entry JS vive en `apps/web/vue/main.js` (no en
  `apps/web/vite/entry.js`).
- **Si estás en admin (`unfold`)**: ver `unfold-patterns`. Los assets de Unfold
  (`STYLES`, `SCRIPTS` en `unfold.py.jinja`) cargan `css/dist.css` /
  `js/preline.js` desde `static/dist/`, pero el frontend público NO entra acá.

## Boundary table

| Concern | Skill responsable |
|---|---|
| django-cotton components (`<c-ui.button>`, slots, `c-vars`) | frontend-patterns |
| HTMX (`hx-get`, `hx-post`, `hx-target`, `hx-swap`) | frontend-patterns |
| Alpine.js (`x-data`, `x-show`, `x-on:click`) | frontend-patterns |
| Tailwind v4 CSS-first (`@theme` blocks) | frontend-patterns |
| django-vite (`{% vite_asset %}`) | frontend-patterns |
| Vite build/dev workflow | frontend-patterns |
| Preline UI como library de componentes | frontend-patterns |
| `HSStaticMethods.autoInit()` re-init después de swaps | frontend-patterns |
| Modal Preline ↔ HTMX, CSRF en HTMX | frontend-patterns |
| `templates/base.html.jinja` + `templates/cotton/` | frontend-patterns |
| `.vue` SFCs / Vue Router / Composition API | vue-spa-patterns (no esta) |
| UNFOLD dict / admin custom | unfold-patterns (no esta) |
| Settings split / BaseModel | django-patterns (no esta) |

---

## 1. Layout del frontend server-rendered

```
templates/
├── base.html.jinja                    # layout raíz, django-vite injection
└── cotton/
    ├── ui/                            # transversales (button, card, modal, alert, input)
    ├── layout/                        # navbar, sidebar, container
    └── forms/                         # field, label, error

apps/web/vite/
├── entry.js                            # JS entry de Vite
└── style.css                           # CSS entry de Vite

vite.config.ts.jinja                    # input -> apps/web/vite/entry.js
                                       # plugins -> tailwindcss
package.json.jinja                     # scripts: dev/build, deps: preline + htmx.org + alpinejs
```

El entry JS vive SIEMPRE en `apps/web/vite/entry.js`, y ese entry importa
`apps/web/vite/style.css`. **NO** crear una segunda entrada en `static/js/` o
`static/css/`: server-rendered usa un solo entry point bajo `apps/web/vite/`.

```html
<!-- templates/base.html.jinja (extracto) -->
{% load django_vite %}
<!DOCTYPE html>
<html lang="es" class="h-full">
<head>
  ...
  {% vite_hmr_client %}        {# inyecta HMR solo si DEBUG=True #}
  {% vite_asset 'apps/web/vite/entry.js' %}
  ...
</head>
<body>
  {% block navbar %}<c-layout.navbar></c-layout.navbar>{% endblock %}
  <main class="flex-1">{% block content %}{% endblock %}</main>
  {% block footer %}...{% endblock %}
</body>
</html>
```

`DJANGO_VITE["default"]["dev_mode"]` se setea a `DEBUG` en
`config/settings/base.py.jinja`. En `DEBUG=True` django-vite sirve assets
desde el dev server de Vite (puerto 5173). En `DEBUG=False` lee
`static/dist/manifest.json`.

## 2. Preline UI como library (NO daisyUI, NO PrimeVue)

Preline se importa vía npm y provee componentes HTML + Tailwind v4 + plugins JS.
El generator pre-configura el CSS y la inicialización:

```css
/* apps/web/vite/style.css */
@import "tailwindcss";
@import "preline/preline.css";

@theme {
  --color-primary-50:  #eff6ff;
  --color-primary-500: #3b82f6;
  --color-primary-600: #2563eb;
  --color-primary-700: #1d4ed8;
}
```

Inicialización en `apps/web/vite/entry.js`:

```javascript
import 'preline';
import Alpine from 'alpinejs';
import collapse from '@alpinejs/collapse';

window.Alpine = Alpine;
Alpine.plugin(collapse);
Alpine.start();

// Preline JS components (modals, dropdowns, tooltips) need HSStaticMethods.
if (window.HSStaticMethods) {
  window.HSStaticMethods.autoInit();
}
```

Y en `base.html.jinja` (o el layout final), el listener crítico:

```html
<script>
  // HTMX swaps inyectan HTML nuevo que contiene componentes Preline.
  // Hay que re-inicializarlos, sino dropdowns/modals no funcionan.
  document.body.addEventListener('htmx:afterSwap', () => {
    if (window.HSStaticMethods) window.HSStaticMethods.autoInit();
  });
</script>
```

Sin este listener, un modal Preline cargado vía HTMX abre pero sus handlers
(escape, focus trap, click outside) no están conectados.

## 3. django-cotton — componentes por dominio

Los componentes cotton viven en `templates/cotton/`, organizados por dominio
funcional (NO por tipo técnico):

```
templates/cotton/
├── ui/             # transversales: button, card, modal, alert, input
├── layout/         # navbar, sidebar, container
├── forms/          # field, label, error (composables de input)
└── <domain>/       # ej: billing/, surveys/ — encapsulado del dominio
```

Reglas:

1. **1 componente = 1 archivo**. NO agrupar variantes en un mismo archivo.
2. **Dominio > tipo**: `templates/cotton/billing/invoice_row.html` — no
   `templates/cotton/rows/invoice.html`.
3. **Prefijo `_` para internos**: `_loading.html` es consumido por otros
   componentes, no se invoca desde page templates.
4. **`ui/`** solo para transversales (button, card, modal, input, alert).
5. **Máximo 2 niveles**: si necesitás 3, el componente está mal diseñado.

Cada componente emite una línea `<c-vars ...>` con defaults y slots
opcionales. Ejemplo del `button.html.jinja` generado:

```html
<!-- templates/cotton/ui/button.html (extracto) -->
<c-vars variant="primary" size="md" type="button"
        hx_get="" hx_post="" hx_target="" hx_swap="innerHTML" />

<button
  type="{{ type|default('button') }}"
  class="inline-flex items-center justify-center gap-x-2 font-medium rounded-lg border border-transparent transition
    {% if variant == 'primary' %} bg-blue-600 text-white hover:bg-blue-700 {% elif variant == 'danger' %} bg-red-600 text-white hover:bg-red-700 {% else %} bg-blue-600 text-white hover:bg-blue-700 {% endif %}
    {% if size == 'sm' %} px-3 py-2 text-sm {% else %} px-4 py-3 text-sm {% endif %}"
  {% if hx_get %}hx-get="{{ hx_get }}"{% endif %}
  {% if hx_post %}hx-post="{{ hx_post }}"{% endif %}
  {% if hx_target %}hx-target="{{ hx_target }}"{% endif %}
  ...
>
  {{ slot }}
</button>
```

Uso:

```html
{% load cotton %}
<c-ui.button variant="primary" hx_post="{% url 'billing:invoice_create' %}"
             hx_target="#invoice-list" hx_swap="beforeend">
  Crear factura
</c-ui.button>
```

Slots nombrados:

```html
<!-- templates/cotton/ui/card.html -->
<c-vars />
<div class="bg-white border border-gray-200 shadow-sm rounded-xl {{ class|default:'' }}">
  {% if header %}
  <div class="px-6 py-4 border-b">{{ header }}</div>
  {% endif %}
  <div class="p-6">{{ slot }}</div>
  {% if footer %}
  <div class="px-6 py-4 border-t">{{ footer }}</div>
  {% endif %}
</div>
```

```html
<c-ui.card>
  <c-slot name="header"><h3 class="text-lg font-semibold">Título</h3></c-slot>
  <p>Contenido</p>
  <c-slot name="footer">
    <c-ui.button variant="ghost">Cancelar</c-ui.button>
    <c-ui.button variant="primary">Aceptar</c-ui.button>
  </c-slot>
</c-ui.card>
```

## 4. Componentes cotton pre-construidos (los emite el generator)

| Componente | Path | Props notables |
|---|---|---|
| `c-ui.button` | `templates/cotton/ui/button.html` | `variant`, `size`, `hx_get`, `hx_post`, `hx_target`, `hx_swap`, `disabled` |
| `c-ui.card` | `templates/cotton/ui/card.html` | slots `header`/`footer` |
| `c-ui.modal` | `templates/cotton/ui/modal.html` | `header`, slot principal, Alpine `x-data="{open:false}"` |
| `c-ui.input` | `templates/cotton/ui/input.html` | passthrough a `<input>` |
| `c-ui.alert` | `templates/cotton/ui/alert.html` | `variant` (info/success/warning/danger) |
| `c-layout.navbar` | `templates/cotton/layout/navbar.html` | slot para links |
| `c-layout.sidebar` | `templates/cotton/layout/sidebar.html` | slot para navegación |
| `c-layout.container` | `templates/cotton/layout/container.html` | `class` |
| `c-forms.field` | `templates/cotton/forms/field.html` | `label`, `error`, `help_text`, slot |
| `c-forms.label` | `templates/cotton/forms/label.html` | `for` |
| `c-forms.error` | `templates/cotton/forms/error.html` | `errors` |

**No agregar más componentes UI a `cotton/ui/`** salvo que sean transversales.
Para algo específico de dominio, creá `templates/cotton/<domain>/`.

## 5. Modal = Preline ↔ HTMX ↔ Alpine

El `c-ui.modal` usa Alpine para toggle y HTMX para el contenido. El modal se
abre cuando termina un HTMX swap exitoso, vía `@htmx:after-request`:

```html
<c-ui.modal header="Nueva factura">
  <c-slot name="trigger">
    <c-ui.button variant="primary">Crear factura</c-ui.button>
  </c-slot>

  <div id="modal-body" x-data="{ open: false }">
    <form hx-post="{% url 'billing:invoice_create' %}"
          hx-target="#invoice-list"
          hx-swap="beforeend"
          @htmx:after-request="if(event.detail.successful) open = false">
      {% csrf_token %}
      <c-forms.field label="Cliente" id="id_customer">
        <input type="text" name="customer" id="id_customer"
               class="py-3 px-4 block w-full border-gray-200 rounded-lg text-sm
                      focus:border-blue-500 focus:ring-blue-500
                      dark:bg-neutral-900 dark:border-neutral-700 dark:text-neutral-400"
               required>
      </c-forms.field>
      <div class="flex justify-end gap-2 mt-4">
        <c-ui.button variant="ghost" @click="open = false">Cancelar</c-ui.button>
        <c-ui.button variant="primary" type="submit">Guardar</c-ui.button>
      </div>
    </form>
  </div>
</c-ui.modal>
```

Patrón crítico: Alpine `x-data="{ open: false }"` controla visibilidad; HTMX
postea con `hx-target` apuntando a un contenedor externo (la lista de
facturas), NO al modal — el modal sólo se cierra cuando el POST tuvo éxito
(`event.detail.successful`).

## 6. HTMX — CSRF y parciales

CSRF en HTMX requiere el token dentro del form:

```html
<form hx-post="{% url 'billing:invoice_create' %}"
      hx-target="#invoice-list"
      hx-swap="beforeend">
  {% csrf_token %}                    {# emite <input name=csrfmiddlewaretoken> #}
  ...
</form>
```

Opcionalmente con header (cuando el endpoint no es un form):

```html
<button hx-post="{% url 'billing:invoice_refresh' %}"
        hx-headers='{"X-CSRFToken": "{{ csrf_token }}"}'>
  Refrescar
</button>
```

`django-htmx` agrega `HtmxMiddleware` cuando `frontend=true`. Eso expone
`request.htmx` en views para devolver fragments vs full pages:

```python
# apps/billing/views.py (extracto)
from django.shortcuts import render


def invoice_list_partial(request):
    invoices = Invoice.objects.all()[:50]
    if request.htmx:                      # sólo el fragmento
        return render(request, "billing/_invoice_list.html",
                      {"invoices": invoices})
    return render(request, "billing/invoice_list.html",
                  {"invoices": invoices})
```

## 7. Build pipeline — Vite 6 + Tailwind v4 CSS-first

```json
// package.json.jinja (extracto, frontend_style=server-rendered)
{
  "scripts": {
    "dev": "vite",
    "build": "vite build",
    "preview": "vite preview",
    "type-check": "tsc --noEmit"
  },
  "dependencies": {
    "preline": "^2.6.0",
    "htmx.org": "^2.0.4",
    "alpinejs": "^3.14.0",
    "@alpinejs/collapse": "^3.14.0"
  },
  "devDependencies": {
    "vite": "^6.0.0",
    "@tailwindcss/vite": "^4.0.0",
    "tailwindcss": "^4.0.0",
    "typescript": "^5.6.0"
  }
}
```

`packageManager` se setea según `package_manager` en `copier.yml`:
`npm@10.5.0` o `bun@1.3.14`. **NUNCA** ambos lockfiles
(`package-lock.json` + `bun.lockb`) en el mismo proyecto — son excluyentes.

```typescript
// vite.config.ts.jinja (frontend_style=server-rendered)
import { defineConfig } from 'vite';
import tailwindcss from '@tailwindcss/vite';
import { resolve } from 'path';

export default defineConfig({
  plugins: [tailwindcss()],
  resolve: { alias: { '@': resolve(__dirname, './static') } },
  build: {
    manifest: 'manifest.json',
    outDir: 'static/dist',
    emptyOutDir: true,
    rollupOptions: { input: resolve(__dirname, 'apps/web/vite/entry.js') },
  },
  server: { host: '0.0.0.0', port: 5173, strictPort: true },
});
```

Workflow:

- `npm run dev` / `bun run dev` → HMR en http://localhost:5173.
  `request.DEBUG=True` → django-vite sirve desde ese dev server.
- `npm run build` / `bun run build` → output en `static/dist/` con
  `manifest.json` + assets. `DEBUG=False` → django-vite lee el manifest.
- `dist/` está gitignorado. Solo se versiona el source (`apps/web/vite/`).

## 8. Tailwind v4 — CSS-first, sin `tailwind.config.js`

Tailwind v4 NO usa `tailwind.config.js`. Toda la config vive en bloques
`@theme` dentro de `apps/web/vite/style.css`:

```css
@import "tailwindcss";
@import "preline/preline.css";

@theme {
  --color-primary: #3b82f6;
  --color-secondary: #64748b;
  --font-display: "Inter", sans-serif;
  --spacing-page: 2rem;
}

@layer base {
  html { font-family: var(--font-display); }
}

@media (prefers-color-scheme: dark) {
  /* dark mode via `dark:` prefix y prefers-color-scheme */
}
```

Cualquier `@theme { ... }` extension se aplica automáticamente a las
utilidades de Tailwind. NO crear un `tailwind.config.js` adicional.

---

## Antipatterns del auditor (NO hacer)

| Anti-patrón | Origen | Por qué está excluido | Mitigación |
|---|---|---|---|
| Usar `daisyUI` / `@plugin "daisyui"` | boilerplates viejos | El generator fija Preline. Mezclar libs crea conflictos | Preline + Tailwind v4 + `@theme` blocks |
| Usar `inertia-django` / `@inertiajs/vue3` | django-boilerplate-v2 | El generator NO hace SPA-inertia | Server-rendered se mantiene server-side; SPA Vue es standalone (vue-spa-patterns) |
| Crear `templates/cotton/{inputs,buttons,modals}/` por tipo | boilerplates viejos | El grouping del generator es por dominio | `templates/cotton/<domain>/<component>.html` |
| Importar `from "primevue/button"` o similar | django-boilerplate-v2 | PrimeVue v4 rompe imports; fuera de scope | Para UI, Preline + Tailwind v4. Para Vue, ver `vue-spa-patterns` |
| Crear `static/js/components/` con Vue/React files | boilerplates viejos | Esto NO es server-rendered | UI server-rendered = cotton + HTML. Si necesitás Vue, frontend_style=vue-spa |
| `<c-ui.button variant="danger" id="123">` con `id` hardcodeado | tests-360 | IDs duplicados rompen aria + scripts | `<c-ui.button id="btn-create-invoice">` con nombres semánticos |
| `{% vite_asset 'static/js/main.js' %}` en server-rendered | entry legacy | Cuando server-rendered, el entry único es `apps/web/vite/entry.js` | `{% vite_asset 'apps/web/vite/entry.js' %}` — el path coincide con `vite.config.ts` |
| `package-lock.json` + `bun.lockb` coexistiendo | inpacto-ghl-integrations, b2bcg | Conflictos de resolución | Jinja conditional: `package_manager=...` ⇒ sólo uno |
| Crear `tasks/` directory en raíz | boilerplates viejos | Rompe convención `apps/<app>/tasks.py` | Generator NO crea `tasks/` raíz |
| `HSStaticMethods.autoInit()` sin listener `htmx:afterSwap` | tests-360 | Modals Preline en respuestas HTMX no abren | Ver §2 |
| Crear una segunda entrada Vite en `static/js/` o `static/css/` | mal port | Duplica el pipeline y desincroniza django-vite | Mantener JS/CSS source bajo `apps/web/vite/` |
| Usar `<script src="{% static 'js/preline.js' %}">` con path customizado | b2bcg | django-vite ya emite el script tag correcto | `{% vite_asset 'apps/web/vite/entry.js' %}` — Preline se importa adentro |

---

## Lo que NO está cubierto acá

- Para configuración del UNFOLD `STYLES`/`SCRIPTS` que cargan
  `static/dist/css/dist.css` y `static/dist/js/preline.js` cuando hay admin
  + frontend, ver `unfold-patterns` §1.
- Para `.vue` SFC files, Composition API, vue-router, ver `vue-spa-patterns`.
- Para tasks en segundo plano disparados desde vistas HTMX, ver
  `django-patterns` §"RateLimitMiddleware" (las views POST a `/api/*` ya están
  rate-limited por default).
- Para servir el build de Vite en producción con WhiteNoise, ver
  `config/settings/base.py.jinja` (`STORAGES["staticfiles"]` =
  `CompressedStaticFilesStorage`). Los assets de `static/dist/` se sirven vía
  WhiteNoise igual que cualquier static.
