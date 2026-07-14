```

+----------------------+--------------------------------------+----------------------------+
|        kosongin      |          kosongin du                 |                            |
|                      |                                      | (-split-kiri) (split kanan)|
+----------------------+--------------------------------------+----------------------------+
|                      |                 untuk nmbh tab->  +  |         kosongin           |
|                      |--------------------------------------|----------------------------|
|                      |                                      |                            |
|                      |                                      |                            |
|                      |                                      |                            |
|    dir-panel         |                                      |    kosongin                |
|                      |        Workspace                     |                            |
|                      |                                      |                            |
|                      |                                      |                            |
|                      |                                      |                            |
|                      |                                      |                            |
|                      |                                      |  ------------------------  |
|                      |                                      |  | input bar             | |
|                      |                                      |  ------------------------  |
|                      |                                      |                            |
+----------------------+--------------------------------------+----------------------------+
       ^                                     ^                                ^
       |                                     |                                |
       dir-panel                        workspace                          ai-panel
```


       tolong nama2 panel ini jangan di ubab, apapaun alasan nya. dan yang ada tulisan kosong beneran di kosongin

detail2 panel

### dir-papnel
(project) E-Commerce

├── (folder) frontend
│   ├── (feature) Customer App
│   ├── (feature) Admin Dashboard
│   └── (feature) Landing Page
│
├── (folder) backend
│   │
│   ├── (module) Authentication
│   │   │
│   │   ├── (feature) Login
│   │   │   │
│   │   │   ├── (flow) Validate Credential
│   │   │   │
│   │   │   ├── (flow) Find User
│   │   │   │
│   │   │   ├── (flow) Verify Password
│   │   │   │
│   │   │   ├── (flow) Generate JWT
│   │   │   │
│   │   │   └── (flow) Return Session
│   │   │
│   │   ├── (file) auth_controller.py
│   │   ├── (file) auth_service.py
│   │   └── (file) jwt_service.py
│   │
│   │       ├── (function) login()
│   │       ├── (function) verify_password()
│   │       ├── (function) create_access_token()
│   │       └── (function) create_refresh_token()
│   │
│   ├── (module) Checkout
│   │
│   │   ├── (feature) Charge Payment
│   │   │
│   │   │   ├── (flow) Validate Amount
│   │   │   ├── (flow) Create Payment
│   │   │   ├── (flow) Call Midtrans
│   │   │   ├── (flow) Save Transaction
│   │   │   └── (flow) Notify User
│   │   │
│   │   ├── (file) payment_controller.py
│   │   ├── (file) payment_service.py
│   │   └── (file) midtrans_gateway.py
│   │
│   │       ├── (function) charge()
│   │       ├── (function) refund()
│   │       ├── (function) save_transaction()
│   │       └── (function) send_receipt()
│   │
│   ├── (module) Inventory
│   ├── (module) Notification
│   └── (module) Analytics
│
├── (folder) database
│
└── (folder) ai

### behavior dir panel
user bisa mengklik semua hal yang ada di sini behavior nya
1.jika user klik folder akan expand dan buka file module yang ada di dalam nya tapi ga buka tab di workspace, berlaku untuk semua folder
2.jika user klik file, function yang ada di dalam nya akan terexpand dan akan membuka tab source code file tersebut di workspace
3. jika user klik module function yang di dalam nya akan ter expand dan membuka tab untuk module nya di workspace
4. jika user klik flow, di workspace akan buka tab baru dan memunculkan flow nya. 

### behavior workspace
detail yang ada di workspace
workspace sama seperti ide lain bisa tambah tab 1 tab 1 file/flow
workspace memunculkan source code dan flow


### workspace

flow definition
"Menjelaskan node yang sedang dipilih secara visual."
contoh:
```
di panel kiri user klil
ƒ login()

di workspace muncul tab
+--------------------------------------------------+

                login()

Goal

Authenticate User

---------------------------------------------------

Validate Input

        │

        ▼

Find User

        │

        ▼

Verify Password

        │

        ▼

Generate JWT

        │

        ▼

Return Session

---------------------------------------------------

Functions

✓ verify_password()

✓ create_access_token()

✓ save_session()

---------------------------------------------------

Files

{path}/{dir}/auth_service.py
{path}/{dir}/jwt_service.py

+--------------------------------------------------+

```

untuk source code sama kaya ide pada umumnya memunculkan isi file


### ai-panel
untuk saat ini tambahin input bar aja

### Design
itu adalah website versi dekstop, dan untuk mobile dan table tolong di samakan
warna primary nya #181818(background, workspace), teks/storke/garis/border #E4E4E4, #1F1F1F (dir-panel, ai panel), warna box/input bar #404040

input bar/box/bar/search pake
xs  sm  md  lg   xl    pill     full
4px 6px 8px 12px 16px  9999px    9999px

border 1px

### Icon split
icon split di sini berfungsi sebagai open panel (dir panel dan ai panel)
terdapat 2 icon yang saya berikan, pembeda nya hanya select dan uselect. 
behaviornya 
jika user klik (select) pake icon
split-horizontal-right-select.svg
jika user tidak select (unselect maka pake icon
split-horizontal-right-unselect.svg

flownya jika user penct -> berubah ke selelct jika user pencet lagi berubah ke -> unselect

btw icon yang aku kasih cuma untuk ai-panel yaitu kanan, untuk kiri dir-panel 2 icon tadi harus di flip menggunakan code dan mereka harus bepisah. liat layout

icon ada di
~/graps/graps/public/icon

## Struktur Plan Wajib

Plan implementasi experimental Graps dibagi menjadi 17 section (`§0` sampai `§16`):

| Section | Nama | Isi utama |
|---|---|---|
| §0 | Keputusan Final | Semua keputusan yang sudah disepakati dan tidak perlu diperdebatkan ulang. |
| §1 | Goal, Scope, dan Non-goals | Tujuan implementasi, batas cakupan, dan hal yang sengaja ditunda. |
| §2 | Terminologi dan Source of Truth | Definisi project, module, file, function, route, flow, structural data, dan semantic data. |
| §3 | Architecture Overview | Pipeline scanner → parser → knowledge graph → AI enrichment → architecture map → UI. |
| §4 | Data Model dan Schema | Kontrak data untuk project, module, file, function, route, flow, dan enrichment. |
| §5 | Structural Scanner | Scan file/folder/package serta ekstraksi AST, classes, functions, imports, routes, comments, annotations, decorators, dan call sites. |
| §6 | Module Resolution | Aturan folder/package sebagai structural boundary serta AI grouping suggestion tanpa menghilangkan boundary asli. |
| §7 | Hybrid Flow Engine | Structural call order, branch, confidence, unresolved calls, dan semantic label dari AI. |
| §8 | AI Enrichment | Instructor, Pydantic schema, validation, retries, cache, fallback, dan larangan AI mengubah structural truth. |
| §9 | Storage dan Cache | Penyimpanan per project di `{scan_root}/.graps`, graph hash, incremental refresh, dan scan exclusion. |
| §10 | Settings dan Scan Behavior | Structural scan selalu aktif, AI Enrichment default ON, behavior OFF/no-key/failure, dan command `/scan`. |
| §11 | Backend dan API Contracts | Endpoint, request/response schema, status scan, source retrieval, settings, dan error states. |
| §12 | Frontend Layout dan Interaction | `dir-panel`, `workspace`, `ai-panel`, explorer, source/flow/module tabs, resize, dan panel toggle. |
| §13 | Design System | Color tokens, spacing, border, Microsoft VS Code Codicons, responsive behavior, dan accessibility. |
| §14 | Per-file Change Map | File baru, file yang diubah, file yang dihapus, serta file yang tidak boleh disentuh. |
| §15 | Implementation Phases | Urutan implementasi, dependency, migration, packaging, dan cleanup strategy. |
| §16 | Tests dan Acceptance Criteria | Unit, integration, UI, responsive, fallback, failure cases, dan definisi selesai yang terukur. |

Scanner dan AI wajib tetap menjadi section terpisah. Structural flow dan semantic label juga tidak boleh digabung. Data schema harus diselesaikan sebelum implementasi UI.

## Inventory Fitur Baru

Total scope terdiri dari 20 capabilities: 15 user-facing features dan 5 backend foundations. Microsoft VS Code Codicons adalah bagian design system, bukan fitur terpisah.

### User-facing Features (15)

1. Three-panel application shell.
2. `dir-panel` explorer.
3. `workspace` sebagai area utama.
4. `ai-panel` dengan input bar.
5. Panel open/close menggunakan split icons.
6. Resizable left and right panels.
7. Responsive layout dengan mental model desktop yang sama pada desktop, tablet, dan mobile.
8. Folder/package/module tree.
9. Expandable file dan function hierarchy.
10. Source-code tabs.
11. Function flow tabs.
12. Module overview tabs.
13. VS Code-like tab lifecycle, deduplication, close behavior, overflow, dan persistence.
14. Settings untuk AI Enrichment dengan default ON.
15. Input command `/scan` untuk manual refresh.

### Backend Foundations (5)

16. Automatic structural project scan yang selalu aktif tanpa AI.
17. Extended knowledge graph untuk classes, functions, routes, calls, packages, dan unresolved edges.
18. Structural module resolution dengan optional AI grouping suggestion.
19. Hybrid flow engine: structural order dari static analysis dan semantic labels dari AI.
20. Project-local incremental storage dan cache di `{scan_root}/.graps`.

### Requirement Wajib, Bukan Fitur Terpisah

- Instructor + Pydantic untuk structured AI output.
- Semantic validation terhadap structural IDs, edges, dan order.
- AI OFF, missing API key, invalid response, dan provider failure fallback ke structural labels.
- AI tidak boleh membuat edge, mengubah urutan, atau menghapus structural node.
- Microsoft VS Code Codicons sebagai satu-satunya icon system; asset dipilih dan disimpan lokal, tanpa runtime CDN.
- Accessibility, keyboard support, `aria-label`, dan touch target minimal 44px.
- Structural graph hashing dan selective re-enrichment hanya untuk module yang berubah.
- Empty reserved layout regions tetap benar-benar kosong sampai ada keputusan fitur.
- Loading, scan status, empty state, dan error state.
- Path traversal protection dan `.graps` otomatis dikecualikan dari scan.

## Fase Implementasi

20 capabilities di atas dikerjakan dalam empat fase dependency-driven:

1. **Foundation** — schema, scanner, knowledge graph, storage, dan cache.
2. **Intelligence** — module resolution, structural flow, Instructor AI enrichment, validation, dan fallback.
3. **Application UI** — tiga panel, explorer, workspace, tabs, settings, input bar, dan Codicons.
4. **Hardening** — responsive behavior, persistence, accessibility, tests, packaging, dan failure handling.

Capability count bukan task count. Saat dipecah menjadi engineering task yang dapat diuji, scope diperkirakan menjadi sekitar 30–40 task dan harus diurutkan berdasarkan dependency.

