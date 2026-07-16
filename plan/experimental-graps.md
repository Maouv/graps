```

+----------------------+--------------------------------------+----------------------------+
|  make it empty first             make it empty first                                     |
|                                                               (-split-kiri) (split kanan)|
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


       Please don't change the names of these panels, whatever the reason. And leave the blank fields blank.

### detail2 panel

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

### 'dir' panel behavior Users can interact with the items displayed here; the behaviors are as follows: 1. Clicking a folder expands it to reveal the module files inside without opening a tab in the workspace; this applies to all folders. 2. Clicking a file expands it to show its internal functions and opens a source code tab for that file in the workspace. 3. Clicking a module expands it to show its internal functions and opens a tab for that module in the workspace. 4. Clicking a flow opens a new tab in the workspace and displays the flow.

### Workspace behavior Details regarding the workspace: Like other IDEs, the workspace supports multiple tabs, with each tab representing a single file or flow. The workspace displays source code and flows.

### workspace

flow definition
"Visually describes the currently selected node."
```
in dir panel when user klik
ƒ login()

while summon on workspace
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

ource code the same as the idea in general to display the contents of the file, like other IDE (integrated development evironment)

### ai-panel
t stay as it is now

### Design
This is the desktop version of the website, and for mobile and tablet, please match the primary color #181818 (background, workspace), text/stroke/line/border #E4E4E4, #1F1F1F (dir-panel, ai panel), color

input bar/box/bar/search use
xs  sm  md  lg   xl    pill     full
4px 6px 8px 12px 16px  9999px    9999px

border 1px

### Icon split
The "split" icon here functions as a panel toggle (for the directory panel and AI panel). I have provided two icons; the difference lies in their "selected" and "unselected" states. The behavior is as follows: If the user selects the icon, `split-horizontal-right-select.svg` is used. If the user deselects it, `split-horizontal-right-unselect.svg` is used. The workflow is: clicking switches it to the "selected" state, and clicking again switches it to the "unselected" state. By the way, the icons I provided are specifically for the AI ​​panel (on the right); for the directory panel (on the left), those same two icons need to be flipped via code, and they must remain separate. Please refer to the layout.

~/graps/graps/public/icon

