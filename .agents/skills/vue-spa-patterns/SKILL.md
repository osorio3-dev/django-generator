---
name: vue-spa-patterns
description: >
  TRIGGER: trabajando en un proyecto generado con frontend=vue-spa, en
  apps/web/vue/**/*.vue, apps/web/vue/main.js (router + mount), en App.vue,
  en components/Pages/*, en components/Shared/*, o cuando el usuario toca
  Vue 3 Composition API con <script setup>, vue-router (history o hash),
  definesProps/defineEmits en Vue, useFetch / $fetch a Django Ninja,
  Preline via class="..." en templates Vue, o CSRF handling cuando
  frontend=vue-spa + admin=unfold (auth Django-side via allauth).
  Cubre SOLO Vue 3 standalone SPA con Vite + Preline + django-vite + auth
  Django-side (allauth). NO cubre Inertia, NO PrimeVue/Quasar/Vuetify,
  NO Vuex/Pinia por defecto, NO Nuxt/SSR.
license: MIT
metadata:
  version: "1.0"
  scope: frontend
  applies_when: "frontend=true AND frontend_style=vue-spa"
---

## Cuándo usarla

Estás en un proyecto generado por este generator con `frontend=true` y
`frontend_style=vue-spa`. Tocás alguno de estos archivos o símbolos:

- `apps/web/vue/main.js` (mount + router)
- `apps/web/vue/router.js` (vue-router config)
- `apps/web/vue/components/App.vue`
- `apps/web/vue/components/Pages/*.vue` (`Home.vue`, `Dashboard.vue`, ...)
- `apps/web/vue/components/Shared/*.vue` (`Navbar.vue`, `Footer.vue`)
- `<script setup>` con `defineProps`, `defineEmits`, `ref`, `computed`
- `vue-router` (history/hash modes)
- `templates/vue_spa.html.jinja` (el shell que Django renderiza)
- Cualquier import de `'vue'` o `'vue-router'`

## Cuándo NO usarla

- **Si `frontend=false`**: el generator NO crea `apps/web/vue/`, NO hay
  `vue-router`, NO hay `templates/vue_spa.html`. Esta skill es irrelevante.
- **Si `frontend=server-rendered`**: usá `frontend-patterns`. El server-
  rendered usa django-cotton + HTMX + Alpine (NO Vue). NO importes Vue acá.
- **Si el usuario pide Inertia, PrimeVue, Nuxt, SSR**: este generator NO
  hace ninguna de esas cosas. Decí que no aplica y redirigí a
  `frontend-patterns` (server-rendered) o sugerí un build distinto.
- **Si estás tocando settings del proyecto** (BaseModel, RateLimitMiddleware,
  Fernet, EncryptedCharField): ver `django-patterns`.
- **Si admin=unfold**: ver `unfold-patterns` para el admin. Esta skill es
  estrictamente para el SPA cliente; auth vive Django-side.

## Boundary table

| Concern | Skill responsable |
|---|---|
| Vue 3 + Composition API + `<script setup>` | vue-spa-patterns |
| `vue-router` (history o hash) | vue-spa-patterns |
| Estructura `apps/web/vue/components/{Shared,Pages}/` | vue-spa-patterns |
| `defineProps` / `defineEmits` con TypeScript | vue-spa-patterns |
| Composables (useAuth, useFetch, useApi) | vue-spa-patterns |
| API client hacia Django Ninja (`/api/...`) | vue-spa-patterns |
| Auth Django-side via allauth (`/accounts/login/`) | vue-spa-patterns |
| Preline via `class="..."` en templates Vue | vue-spa-patterns |
| CSRF cookie + `X-CSRFToken` header | vue-spa-patterns |
| Catch-all de `vue_spa.html` en `config/urls.py` | vue-spa-patterns |
| django-cotton / HTMX / Alpine | frontend-patterns (no esta) |
| UNFOLD / ModelAdmin / sidebar | unfold-patterns (no esta) |
| Settings split / BaseModel / Fernet | django-patterns (no esta) |

---

## 1. Layout del frontend vue-spa

```
apps/web/vue/
├── main.js                                 # mount App + router
├── components/
│   ├── App.vue                             # <router-view> + Navbar + Footer
│   ├── Shared/
│   │   ├── Navbar.vue
│   │   └── Footer.vue
│   └── Pages/
│       ├── Home.vue
│       └── Dashboard.vue

templates/
└── vue_spa.html.jinja                      # shell que Django renderiza (con django-vite)

config/urls.py.jinja                        # catch-all para SPA (excluye /api/, /admin/, /accounts/)
```

A diferencia del server-rendered, acá:

- **NO** hay `templates/cotton/`.
- **NO** hay `static/js/main.js` (el entry JS vive en `apps/web/vite/entry.js`).
- **NO** hay `static/css/main.css` (vivía acá también, ahora en
  `apps/web/vite/style.css.jinja`).
- El shell del SPA es `templates/vue_spa.html.jinja` (NO `base.html.jinja`).

## 2. `templates/vue_spa.html.jinja` y el catch-all

`templates/vue_spa.html.jinja`:

```html
{% raw %}{% load django_vite %}<!DOCTYPE html>{% endraw %}
<html lang="es" class="h-full">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{% raw %}{% block title %}{% endraw %}{{ project_name }}{% raw %}{% endblock %}{% endraw %}</title>
  {% raw %}{% vite_hmr_client %}{% endraw %}
  {% raw %}{% vite_asset 'apps/web/vite/entry.js' %}{% endraw %}
  {% raw %}{% block extra_head %}{% endblock %}{% endraw %}
</head>
<body class="min-h-full">
  <div id="app"></div>
</body>
</html>
```

El catch-all vive en `config/urls.py.jinja` y EXCLUYE explícitamente rutas
del backend:

```python
# config/urls.py.jinja (frontend=vue-spa, extracto)
from django.urls import re_path
from django.views.generic import TemplateView

urlpatterns += [
    re_path(
        r"^(?!api/|admin/|accounts/|static/|health/|.*\.).*$",
        TemplateView.as_view(template_name="vue_spa.html"),
        name="vue_spa_catchall",
    ),
]
```

Patrones excluidos (deben caer a su router Django):

| Prefijo | Atendido por |
|---|---|
| `/api/` | `apps.api.router.api` (cuando `api=django-ninja`) |
| `/admin/` | `admin.site.urls` (Unfold) |
| `/accounts/` | `apps.accounts.urls` + `allauth.urls` |
| `/static/` | WhiteNoise (assets compilados) |
| `/health/` | `apps.core.views.health.health_check` |
| `.*\.` | archivos con extensión → WhiteNoise |

Si tu SPA necesita rutas adicionales pero NO querés que Django las sirva como
HTML (ej: `/media/foo.png` cae a WhiteNoise), agregalas al regex.

## 3. `main.js` — mount + router

```javascript
// apps/web/vite/main.js (vue-spa)
import { createApp } from 'vue';
{% if vue_router == 'hash' %}
import { createRouter, createWebHashHistory } from 'vue-router';
{% else %}
import { createRouter, createWebHistory } from 'vue-router';
{% endif %}
import App from './components/App.vue';
import Home from './components/Pages/Home.vue';
import Dashboard from './components/Pages/Dashboard.vue';
import 'preline';

const projectName = {{ project_name | tojson }};

const router = createRouter({
  history: {% if vue_router == 'hash' %}createWebHashHistory(){% else %}createWebHistory(){% endif %},
  routes: [
    { path: '/', component: Home, name: 'home', props: { projectName } },
    { path: '/dashboard', component: Dashboard, name: 'dashboard' },
  ],
});

const app = createApp(App, { brand: projectName });
app.use(router);
app.mount('#app');
```

## 4. Router — history vs hash

`vue_router` en `copier.yml` controla el modo:

| Modo | URLs resultantes | Cuándo usar |
|---|---|---|
| `history` | `/about`, `/dashboard` | default. Requiere que Django/red sirva 404 → `vue_spa.html` (catch-all ya lo hace) |
| `hash` | `/#/about`, `/#/dashboard` | cuando el hosting NO redirige 404 a la app (ej: S3+CloudFront, GitHub Pages sin rewrites) |

**Default es `history`** porque el generator emite el catch-all en
`config/urls.py.jinja`. Si deployás detrás de un static-only host sin esa
redirección, cambiá `vue_router=hash`.

## 5. Estructura de componentes

```vue
<!-- apps/web/vue/components/App.vue -->
<template>
  <Navbar :brand="brand" />
  <main class="container mx-auto px-4 py-8">
    <router-view />
  </main>
  <Footer :brand="brand" />
</template>

<script setup lang="ts">
import Navbar from './Shared/Navbar.vue';
import Footer from './Shared/Footer.vue';

defineProps<{
  brand: string;
}>();
</script>
```

```vue
<!-- apps/web/vue/components/Pages/Dashboard.vue -->
<template>
  <section class="space-y-6">
    <h1 class="text-2xl font-bold">Dashboard</h1>
    <div class="grid grid-cols-1 md:grid-cols-3 gap-4">
      <article v-for="card in cards" :key="card.id"
               class="bg-white border rounded-xl p-4 shadow-sm
                      dark:bg-neutral-800 dark:border-neutral-700">
        <h2 class="font-semibold">{{ card.title }}</h2>
        <p class="text-sm text-gray-600 dark:text-neutral-400">{{ card.body }}</p>
      </article>
    </div>
  </section>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue';

interface Card { id: number; title: string; body: string }

const cards = ref<Card[]>([]);
const loading = ref(true);

onMounted(async () => {
  const response = await fetch('/api/cards/', { credentials: 'include' });
  cards.value = await response.json();
  loading.value = false;
});
</script>
```

Reglas de organización:

- **`Shared/`**: componentes reutilizables entre páginas (Navbar, Footer,
  Button.vue custom, Modal.vue custom).
- **`Pages/`**: una entrada por ruta del router. El nombre del archivo = nombre
  del componente en `resolve:` de vue-router.
- **NO** crees `apps/web/vue/components/Demo`, `HelloWorld.vue`, ni rutas
  `/demo` o `/playground`. El generator no los emite (esos son tentaciones,
  nofeatures).
- **Sin Vuex/Pinia por default**. Estado compartido va en composables locales
  (`useXxxStore()`) o `provide/inject`. Si necesitás store global real,
  pedilo explícitamente — `vue-spa-patterns` lo trata como opt-in.

## 6. Props, emits, TypeScript

```vue
<!-- apps/web/vue/components/Shared/Modal.vue -->
<script setup lang="ts">
interface Props {
  open: boolean;
  title: string;
}
interface Emits {
  (e: 'close'): void;
  (e: 'confirm', payload: { id: number }): void;
}

const props = defineProps<Props>();
const emit = defineEmits<Emits>();

function onConfirm() {
  emit('confirm', { id: Date.now() });
}
</script>

<template>
  <Transition name="fade">
    <div v-if="props.open" class="fixed inset-0 z-[80] flex items-center justify-center
                                    bg-gray-900/50 backdrop-blur-sm"
         @click.self="emit('close')">
      <div class="bg-white dark:bg-neutral-800 rounded-xl shadow-xl p-6 max-w-lg w-full">
        <h2 class="text-lg font-semibold mb-4">{{ props.title }}</h2>
        <slot />
        <button @click="onConfirm"
                class="mt-4 px-4 py-2 bg-blue-600 text-white rounded-lg">
          Confirmar
        </button>
      </div>
    </div>
  </Transition>
</template>
```

Uso:

```vue
<Modal :open="showConfirm" title="¿Seguro?" @close="showConfirm = false"
       @confirm="onConfirm">
  <p class="text-gray-600">Esta acción no se puede deshacer.</p>
</Modal>
```

## 7. Composables para estado compartido

```typescript
// apps/web/vue/composables/useAuth.ts
import { ref, computed } from 'vue';

interface User { id: number; email: string; display_name: string }

const user = ref<User | null>(null);
const isAuthenticated = computed(() => user.value !== null);

export function useAuth() {
  async function fetchUser() {
    const response = await fetch('/api/me/', { credentials: 'include' });
    user.value = response.ok ? await response.json() : null;
  }
  async function login(email: string, password: string) {
    // POST contra allauth (Django-side), ver §8
    const response = await fetch('/accounts/login/', {
      method: 'POST',
      credentials: 'include',
      headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
      body: new URLSearchParams({ email, password, csrfmiddlewaretoken: getCSRF() }),
    });
    if (response.ok) await fetchUser();
  }
  function logout() {
    return fetch('/accounts/logout/', { method: 'POST',
                                        headers: { 'X-CSRFToken': getCSRF() } });
  }
  return { user, isAuthenticated, fetchUser, login, logout };
}
```

```typescript
// apps/web/vue/composables/useApi.ts
const BASE = import.meta.env.VITE_API_BASE_URL || '/api';

export function useApi() {
  function getCSRF(): string {
    const match = document.cookie.match(/csrftoken=([^;]+)/);
    return match ? match[1] : '';
  }
  async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
    const response = await fetch(`${BASE}${path}`, {
      credentials: 'include',
      ...init,
      headers: {
        'Content-Type': 'application/json',
        'X-CSRFToken': getCSRF(),
        ...init.headers,
      },
    });
    if (!response.ok) throw new Error(`${response.status} ${response.statusText}`);
    return response.json();
  }
  return {
    get: <T>(path: string) => request<T>(path),
    post: <T>(path: string, body: unknown) =>
      request<T>(path, { method: 'POST', body: JSON.stringify(body) }),
  };
}
```

## 8. Auth Django-side via allauth

El login NO vive en Vue. Vive en allauth (Django-side) en
`/accounts/login/` (POST). Vue sólo postea el form y deja que Django maneje
session + redirect:

```typescript
// apps/web/vue/composables/useAuth.ts (extracto de login)
async function login(email: string, password: string): Promise<boolean> {
  const form = new FormData();
  form.set('email', email);
  form.set('password', password);
  form.set('csrfmiddlewaretoken', getCSRF());

  const response = await fetch('/accounts/login/', {
    method: 'POST',
    credentials: 'include',
    body: form,                             // NO Content-Type — FormData nativo
  });
  // allauth responde 200 con la página siguiente o 302 según allauth config
  return response.redirected || response.ok;
}
```

Si querés un form de login Vue "single page", podés usar la SPA para
renderizar `<form>` y postear al endpoint allauth. NO implementes JWT custom
— allauth ya maneja session, CSRF, rate limit (vía RateLimitMiddleware del
generator, ver `django-patterns`).

`apps/accounts/urls.py.jinja` y `apps/accounts/adapters/account_adapter.py.jinja`
configuran allauth (sólo si `admin=true`). Para ver el detalle de cómo
allauth respeta soft-delete, ver `django-patterns` §6.

## 9. CSRF handling

CSRF en Vue lee de la cookie (`csrftoken`) y la manda en `X-CSRFToken` para
requests no-GET:

```typescript
function getCSRF(): string {
  const match = document.cookie.match(/csrftoken=([^;]+)/);
  return match ? decodeURIComponent(match[1]) : '';
}

await fetch('/api/orders/', {
  method: 'POST',
  credentials: 'include',
  headers: {
    'Content-Type': 'application/json',
    'X-CSRFToken': getCSRF(),
  },
  body: JSON.stringify({ items: [...] }),
});
```

Django responde 403 si falta el header en requests no-GET. Hacé SIEMPRE fetch
con `credentials: 'include'` para que la cookie viaje cross-origin o
same-origin.

> **Gotcha vue-spa + admin=unfold**: en dev (Vite en :5173, Django en :8000)
> el browser NO manda la cookie `csrftoken` porque son distintos origins.
> Solución: configurá `CORS_ALLOWED_ORIGINS` con `http://localhost:5173` y
> `CSRF_TRUSTED_ORIGINS` con el mismo. Documentado en DESIGN.md §R-06.

## 10. Preline en templates Vue — `class="..."` SOLAMENTE

Preline JS plugins NO funcionan dentro de un template Vue sin reinicializar
`HSStaticMethods` en cada cambio de vista. Por convención, en Vue usamos
**solo los estilos/tamaños de Preline** vía `class`, y re-implementamos la
interactividad nativa del browser (`v-if`, `@click`, transitions).

```vue
<button class="inline-flex items-center justify-center gap-x-2 font-medium
               rounded-lg border border-transparent bg-blue-600 text-white
               hover:bg-blue-700 focus:bg-blue-700 px-4 py-3 text-sm"
        @click="open = true">
  Crear orden
</button>

<div v-if="open"
     class="fixed inset-0 z-[80] bg-gray-900/50 backdrop-blur-sm
            flex items-center justify-center p-4"
     @click.self="open = false">
  <div class="bg-white dark:bg-neutral-800 rounded-xl shadow-xl p-6 max-w-lg w-full">
    <slot />
  </div>
</div>
```

NO hagas:

```vue
<!-- ❌ NO USES class="hs-overlay" ni otros atributos hs-* -->
<dialog id="my-modal" class="hs-overlay">...
```

`hs-*` requiere Preline JS auto-init que no se mantiene estable a través de
mount/unmount de Vue. Usá `v-if` + `class` + tu propio transition de Vue.

## 11. Build pipeline — Vite 6

```json
// package.json.jinja (frontend_style=vue-spa, extracto)
{
  "scripts": {
    "dev": "vite",
    "build": "vite build",
    "preview": "vite preview",
    "type-check": "vue-tsc --noEmit"
  },
  "dependencies": {
    "preline": "^2.6.0",
    "vue": "^3.5.0",
    "vue-router": "^4.4.0"
  },
  "devDependencies": {
    "vite": "^6.0.0",
    "@vitejs/plugin-vue": "^5.2.0",
    "@tailwindcss/vite": "^4.0.0",
    "tailwindcss": "^4.0.0",
    "typescript": "^5.6.0",
    "vue-tsc": "^2.1.0"
  }
}
```

```typescript
// vite.config.ts.jinja (frontend_style=vue-spa)
import { defineConfig } from 'vite';
import vue from '@vitejs/plugin-vue';
import { resolve } from 'path';

export default defineConfig({
  plugins: [vue()],
  resolve: { alias: { '@': resolve(__dirname, './apps/web/vite') } },
  build: {
    manifest: 'manifest.json',
    outDir: 'static/dist',
    emptyOutDir: true,
    rollupOptions: { input: resolve(__dirname, 'apps/web/vite/entry.js') },
  },
  server: { host: '0.0.0.0', port: 5173, strictPort: true },
});
```

Mismo workflow que server-rendered (build → `static/dist/manifest.json` →
django-vite lo lee cuando `DEBUG=False`).

---

## Antipatterns del auditor (NO hacer)

| Anti-patrón | Origen | Por qué está excluido | Mitigación |
|---|---|---|---|
| `import { createApp, h } from "vue"; ... createInertiaApp({...})` | django-boilerplate-v2 | Inertia rompe el SPA standalone y mete acoplamiento | Acá `createApp(App).use(router).mount(...)` sin Inertia |
| `import PrimeVue from "primevue/config";` | django-boilerplate-v2 | PrimeVue v4 rompe imports; fuera de scope | Preline solo vía `class="..."`. Para tablas avanzadas, pedí explícitamente |
| `class="hs-overlay"` / `data-hs-overlay` | tests-360, b2bcg | Preline JS no se reinicializa entre mounts de Vue | `v-if` + transitions nativas de Vue |
| Crear `apps/web/vue/components/HelloWorld.vue` | boilerplates viejos | Demo files son tentación, nofeatures | Cada `.vue` que agregues resuelve un caso del proyecto. Sin HelloWorld. |
| `apps/web/vue/views/DashboardDemo.vue` o rutas `/demo` | boilerplates viejos | Mismo problema | Si querés probar, agregalo como página real con una ruta de tu dominio |
| Implementar JWT custom en Vue en lugar de allauth | inpacto-pagos-ghl | allauth ya da session, CSRF, rate limit | `fetch('/accounts/login/', {method: 'POST', ...})` con `credentials: 'include'` |
| `Pinia` / `Vuex` por default | django-boilerplate-v2 (modismos viejos) | El generator no lo instala | composables (`useXxx`) o `provide/inject`. Si necesitás store real: pedirlo. |
| `<script src="https://unpkg.com/vue@3">` | inpacto-ghl-integrations | Cargar Vue desde CDN rompe HMR y bundling | Todo Vue via `import { ... } from 'vue'` desde npm |
| `createRouter({ history: createWebHashHistory() })` por default | inpacto-ghl-integrations | Default `vue_router=history`. Hash mode es opt-in para hosts sin rewrites | Verifica `vue_router` en `copier.yml`; usá history si tenés catch-all Django |
| `import Vue from 'vue'` (Vue 2 style) | inpacto-pagos-ghl | Vue 2 EOL, incompatible con Vite moderno | `import { createApp, ref, ... } from 'vue'` (named imports) |
| `import Login from '@/components/Pages/Login.vue'` con Vuex actions | inpacto-pagos-ghl | Acopla features al store innecesariamente | composables pequeños, `provide/inject` cuando aplique |
| Hardcodear `http://localhost:8000` en fetch calls | tests-360 | No funciona cross-Vite-dev-server | Usá `import.meta.env.VITE_API_BASE_URL` con `.env.local` |
| `apps/web/vite/components/` con files .vue (no .js) cuando server-rendered | boilerplates viejos | server-rendered NO usa Vue | Si ves esta carpeta, es mal porte del template |
| `package-lock.json` + `bun.lockb` coexistiendo | inpacto-ghl-integrations, b2bcg | Conflictos de versión | `package_manager=npm|bin`, sólo uno |

---

## Lo que NO está cubierto acá

- **SSR / Nuxt / SSR-hydrated Vue**: fuera de scope. El generator emite un
  SPA client-only. Si necesitás SSR, es una decisión arquitectónica — el
  generator no la cubre.
- **PrimeVue / Quasar / Vuetify**: excluidos explícitamente por design.
  Pide el reemplazo antes de agregar dependencias.
- **Server-side templates django-cotton**: ver `frontend-patterns`. Mezclar
  Vue + django-cotton en el mismo request es un anti-patrón (server-rendered
  o vue-spa, no ambos).
- **Settings Django-side (BaseModel, RateLimit, Fernet, UNFOLD)**: ver
  `django-patterns` y `unfold-patterns`.
- **Tests E2E con Playwright**: `include_playwright=true` activa `@playwright/test`
  en `package.json.jinja`. Para tests E2E del SPA, usar `page.goto('/')` y
  ejercitar componentes Vue — fuera del scope de esta skill.
