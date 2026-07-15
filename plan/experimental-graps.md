```

+----------------------+--------------------------------------+----------------------------+
|        kosongin      |          kosongin dulu               |                            |
|                      |                                      | (-split-kiri) (split kanan)|
+----------------------+--------------------------------------+----------------------------+
|    explorer          |                 untuk nmbh tab->  +  |         Ai                 |
|----------------------|--------------------------------------|----------------------------|
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
├── (folder) database'
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

