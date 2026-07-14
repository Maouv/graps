# Decision Log — Experimental Graps

> **Summary Block:** SSoT seluruh keputusan penting project. Entri terbaru berada paling atas; detail capability/architecture tetap di SSoT terkait dan entri ini merekam keputusan, alasan, serta konsekuensinya.

### DEC-0012: Use full Plan-OS project instance
- **Tanggal:** 2026-07-14
- **Diputuskan oleh:** Maou
- **Konteks/Masalah:** Use full Plan-OS project instance membutuhkan aturan durable lintas feature/task.
- **Opsi yang dipertimbangkan:** mempertahankan perilaku lama, memilih alternatif ad hoc, atau memakai kontrak terstruktur.
- **Keputusan:** Replace the monolithic master-plan model with the official scaffold; retain the old file as a pointer.
- **Alasan:** The prior root document bypassed meaningful entity validation and dependency discovery.
- **Dampak/Konsekuensi:** Project planning becomes indexed, split, and auditable; more files must be maintained.
- **Terkait:** lihat index feature/task dan SSoT design/architecture.

---

### DEC-0011: Use 09-decision-log.md
- **Tanggal:** 2026-07-14
- **Diputuskan oleh:** Maou
- **Konteks/Masalah:** Use 09-decision-log.md membutuhkan aturan durable lintas feature/task.
- **Opsi yang dipertimbangkan:** mempertahankan perilaku lama, memilih alternatif ad hoc, atau memakai kontrak terstruktur.
- **Keputusan:** Resolve the upstream 08/09 naming conflict in favor of the user-selected scaffold filename `09-decision-log.md`.
- **Alasan:** The user explicitly selected option 1 with `09-decision-log.md`.
- **Dampak/Konsekuensi:** All project documents reference this filename.
- **Terkait:** lihat index feature/task dan SSoT design/architecture.

---

### DEC-0010: Vendor Microsoft VS Code Codicons
- **Tanggal:** 2026-07-14
- **Diputuskan oleh:** Maou
- **Konteks/Masalah:** Vendor Microsoft VS Code Codicons membutuhkan aturan durable lintas feature/task.
- **Opsi yang dipertimbangkan:** mempertahankan perilaku lama, memilih alternatif ad hoc, atau memakai kontrak terstruktur.
- **Keputusan:** Use only consumed Codicons SVGs plus retained custom split assets; no runtime CDN or mixed icon library.
- **Alasan:** Consistent lightweight controls, local availability, and explicit attribution.
- **Dampak/Konsekuensi:** Assets and license notice become packaging requirements.
- **Terkait:** lihat index feature/task dan SSoT design/architecture.

---

### DEC-0009: Responsive drawers and overlays
- **Tanggal:** 2026-07-14
- **Diputuskan oleh:** Maou
- **Konteks/Masalah:** Responsive drawers and overlays membutuhkan aturan durable lintas feature/task.
- **Opsi yang dipertimbangkan:** mempertahankan perilaku lama, memilih alternatif ad hoc, atau memakai kontrak terstruktur.
- **Keputusan:** Keep panel identities across breakpoints but present side panels as drawers/overlays on tablet/phone.
- **Alasan:** Three squeezed columns are unusable on mobile.
- **Dampak/Konsekuensi:** Responsive state recovery and 44px touch targets require tests.
- **Terkait:** lihat index feature/task dan SSoT design/architecture.

---

### DEC-0008: Instructor dependency gate
- **Tanggal:** 2026-07-14
- **Diputuskan oleh:** Maou
- **Konteks/Masalah:** Instructor dependency gate membutuhkan aturan durable lintas feature/task.
- **Opsi yang dipertimbangkan:** mempertahankan perilaku lama, memilih alternatif ad hoc, atau memakai kontrak terstruktur.
- **Keputusan:** Plan Instructor + Pydantic validation but install only after exact pin and explicit approval.
- **Alasan:** Structured retries help shape validation, but dependencies cannot be added implicitly.
- **Dampak/Konsekuensi:** AI implementation pauses at the gate if approval is absent.
- **Terkait:** lihat index feature/task dan SSoT design/architecture.

---

### DEC-0007: Project-local .graps storage
- **Tanggal:** 2026-07-14
- **Diputuskan oleh:** Maou
- **Konteks/Masalah:** Project-local .graps storage membutuhkan aturan durable lintas feature/task.
- **Opsi yang dipertimbangkan:** mempertahankan perilaku lama, memilih alternatif ad hoc, atau memakai kontrak terstruktur.
- **Keputusan:** Store graph, architecture overlay, settings, and cache only under the scanned project `.graps/`.
- **Alasan:** Keeps state portable, scoped, and independently invalidatable.
- **Dampak/Konsekuensi:** Scanner must hard-exclude `.graps` and storage writes must be atomic.
- **Terkait:** lihat index feature/task dan SSoT design/architecture.

---

### DEC-0006: Structural scan always active
- **Tanggal:** 2026-07-14
- **Diputuskan oleh:** Maou
- **Konteks/Masalah:** Structural scan always active membutuhkan aturan durable lintas feature/task.
- **Opsi yang dipertimbangkan:** mempertahankan perilaku lama, memilih alternatif ad hoc, atau memakai kontrak terstruktur.
- **Keputusan:** Separate mandatory structural scanning from default-ON optional AI Enrichment.
- **Alasan:** The product must remain useful without provider/key/network.
- **Dampak/Konsekuensi:** Every API/UI flow needs a technical-label fallback.
- **Terkait:** lihat index feature/task dan SSoT design/architecture.

---

### DEC-0005: Hybrid flow with explicit confidence
- **Tanggal:** 2026-07-14
- **Diputuskan oleh:** Maou
- **Konteks/Masalah:** Hybrid flow with explicit confidence membutuhkan aturan durable lintas feature/task.
- **Opsi yang dipertimbangkan:** mempertahankan perilaku lama, memilih alternatif ad hoc, atau memakai kontrak terstruktur.
- **Keputusan:** Start with Python direct-call `call_sequence`; represent branches and uncertainty explicitly.
- **Alasan:** Static analysis is not complete runtime execution.
- **Dampak/Konsekuensi:** UI and docs must not claim full control flow without structural support.
- **Terkait:** lihat index feature/task dan SSoT design/architecture.

---

### DEC-0004: Feature is semantic metadata
- **Tanggal:** 2026-07-14
- **Diputuskan oleh:** Maou
- **Konteks/Masalah:** Feature is semantic metadata membutuhkan aturan durable lintas feature/task.
- **Opsi yang dipertimbangkan:** mempertahankan perilaku lama, memilih alternatif ad hoc, atau memakai kontrak terstruktur.
- **Keputusan:** Do not make business capability a mandatory core hierarchy entity.
- **Alasan:** Capability inference can fail without invalidating structural navigation.
- **Dampak/Konsekuensi:** Capabilities live in validated module enrichment or user override.
- **Terkait:** lihat index feature/task dan SSoT design/architecture.

---

### DEC-0003: Deterministic module identity
- **Tanggal:** 2026-07-14
- **Diputuskan oleh:** Maou
- **Konteks/Masalah:** Deterministic module identity membutuhkan aturan durable lintas feature/task.
- **Opsi yang dipertimbangkan:** mempertahankan perilaku lama, memilih alternatif ad hoc, atau memakai kontrak terstruktur.
- **Keputusan:** Derive modules from language package/workspace/crate rules with folder fallback.
- **Alasan:** Stable structural boundaries cannot depend on probabilistic AI output.
- **Dampak/Konsekuensi:** AI may label/group views but cannot replace canonical IDs.
- **Terkait:** lihat index feature/task dan SSoT design/architecture.

---

### DEC-0002: Exact explorer click contract
- **Tanggal:** 2026-07-14
- **Diputuskan oleh:** Maou
- **Konteks/Masalah:** Exact explorer click contract membutuhkan aturan durable lintas feature/task.
- **Opsi yang dipertimbangkan:** mempertahankan perilaku lama, memilih alternatif ad hoc, atau memakai kontrak terstruktur.
- **Keputusan:** Folder toggles only; file opens source; module opens overview; function and flow open flow tabs.
- **Alasan:** Predictable navigation prevents source/flow ambiguity.
- **Dampak/Konsekuensi:** Every tree and tab test uses this contract.
- **Terkait:** lihat index feature/task dan SSoT design/architecture.

---

### DEC-0001: Structural graph is source of truth
- **Tanggal:** 2026-07-14
- **Diputuskan oleh:** Maou
- **Konteks/Masalah:** Structural graph is source of truth membutuhkan aturan durable lintas feature/task.
- **Opsi yang dipertimbangkan:** mempertahankan perilaku lama, memilih alternatif ad hoc, atau memakai kontrak terstruktur.
- **Keputusan:** Parser/scanner own IDs, hierarchy, edges, order, branch metadata, and confidence; AI is semantic overlay only.
- **Alasan:** Deterministic topology is inspectable and supports full fallback.
- **Dampak/Konsekuensi:** Semantic output must reference allowlisted structural IDs and cannot mutate graph truth.
- **Terkait:** lihat index feature/task dan SSoT design/architecture.

---
