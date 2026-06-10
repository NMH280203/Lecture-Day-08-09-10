# Báo Cáo Nhóm — Lab Day 10: Data Pipeline & Data Observability

**Tên nhóm:** Nhóm CS-IT Data Pipeline  
**Thành viên:**
| Tên | Vai trò (Day 10) | Email |
|-----|------------------|-------|
| Thành viên A | Ingestion / Raw Owner | a@lab.local |
| Thành viên B | Cleaning & Quality Owner | b@lab.local |
| Thành viên C | Embed & Idempotency Owner | c@lab.local |
| Thành viên D | Monitoring / Docs Owner | d@lab.local |

**Ngày nộp:** 2026-06-10  
**Repo:** `Lecture-Day-08-09-10/day10/lab`  
**run_id chính:** `day10-final`

---

## 1. Pipeline tổng quan

Nguồn raw là `data/raw/policy_export_dirty.csv` (247 dòng) mô phỏng export từ 5 hệ thống: refund, SLA, FAQ, HR, access control — kèm export lỗi (`invalid_doc_*`, `legacy_*`). Pipeline baseline chỉ allowlist 4 doc_id nên **bỏ sót `access_control_sop`** và chưa xử lý đủ xung đột HR 10 vs 12 ngày phép.

Luồng: **ingest → clean (`transform/cleaning_rules.py`) → validate (`quality/expectations.py`) → embed Chroma (`day10_kb`) → manifest + freshness**. Mỗi bước ghi log với `run_id` trong `artifacts/logs/run_<run-id>.log`.

**Lệnh chạy một dòng:**

```bash
cd day10/lab && source .venv/bin/activate && python etl_pipeline.py run --run-id day10-final && python grading_run.py --out artifacts/eval/grading_run.jsonl
```

---

## 2. Cleaning & expectation

### 2a. Bảng metric_impact

| Rule / Expectation mới | Trước | Sau / khi inject | Chứng cứ |
|------------------------|-------|------------------|----------|
| `access_control_sop` allowlist | `missing=['access_control_sop']` halt | 5/5 doc present | `expectation[required_kb_doc_ids_present]` OK |
| `quarantine_hr_stale_10d_content` | HR chunk "10 ngày" trong index | 0 violation sau clean | `hr_leave_no_stale_10d_annual` OK; `gq_d10_09` pass |
| `strip_unclear_content_prefix` | Chunk HR 12 ngày bị prefix parser | 1 row `rows_with_12d=1` | cleaned row #35 → 12 ngày phép |
| `enrich_p1_escalation_topic_prefix` | `gq_d10_06` contains_expected=false | true sau enrich | `grading_run.jsonl` gq_d10_06 |
| inject `--no-refund-fix` | `violations=1` refund 14 ngày | eval `hits_forbidden=yes` | `after_inject_bad.csv` q_refund_window |

**Rule mới (≥3):** strip_unclear_content_prefix, quarantine_hr_stale_10d_content, normalize_repeated_lam_viec, strip_bang_prefix, enrich_p1_escalation_topic_prefix.

**Expectation mới (≥2):** required_kb_doc_ids_present (halt), no_unclear_content_marker (halt), hr_leave_has_12d_annual (warn).

**Ví dụ halt:** lần đầu chạy thiếu `access_control_sop` → `required_kb_doc_ids_present` FAIL → sửa allowlist → rerun exit 0.

---

## 3. Before / after retrieval

**Inject:** `python etl_pipeline.py run --run-id inject-bad --no-refund-fix --skip-validate`  
→ `artifacts/eval/after_inject_bad.csv`: `q_refund_window` có `hits_forbidden=yes` (top-k còn "14 ngày làm việc").

**Sau fix:** `python etl_pipeline.py run --run-id day10-final`  
→ `artifacts/eval/after_fix_eval.csv`: cùng câu `hits_forbidden=no`, top-1 là "7 ngày làm việc".

**Grading:** `artifacts/eval/grading_run.jsonl` — 10/10 câu pass (`python instructor_quick_check.py`).

---

## 4. Freshness & monitoring

SLA: `FRESHNESS_SLA_HOURS=24` đo tại **publish** (`contracts/data_contract.yaml`). Manifest `day10-final` → **FAIL** vì `exported_at` mẫu từ 2026-04-10 (~1471h tuổi). Ghi nhận trong `docs/runbook.md`: FAIL hợp lý cho snapshot lab; production dùng timestamp thực.

---

## 5. Liên hệ Day 09

Cùng corpus `data/docs/` với Day 09. Collection tách `day10_kb` để tránh phá index multi-agent đang dev. Sau Day 10 pass, có thể set `CHROMA_COLLECTION=day10_kb` trong Day 09 để retrieval worker đọc corpus đã clean.

---

## 6. Rủi ro còn lại

- Embedding semantic vẫn có thể rank sai nếu thiếu rule enrich topic.
- Chưa có alert tự động Slack — chỉ kênh cấu hình trong contract.
- Freshness một boundary — chưa đo ingest vs publish riêng.

---

## Peer review (3 câu)

1. **Rerun có duplicate vector không?** Không — upsert `chunk_id` + `embed_prune_removed` trong log `run_day10-final.log`.
2. **Freshness đo ở đâu?** `latest_exported_at` trong manifest sau embed; lệnh `etl_pipeline.py freshness --manifest …`.
3. **Record quarantine đi đâu?** `artifacts/quarantine/quarantine_<run-id>.csv` với cột `reason` — không silent drop.
