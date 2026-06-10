# Quality report — Lab Day 10 (nhóm)

**run_id:** `day10-final`  
**Ngày:** 2026-06-10

---

## 1. Tóm tắt số liệu

| Chỉ số | Trước (baseline chưa sửa) | Sau (`day10-final`) | Ghi chú |
|--------|---------------------------|---------------------|---------|
| raw_records | 247 | 247 | `policy_export_dirty.csv` |
| cleaned_records | ~20 (thiếu access_control) | **34** | Thêm allowlist + rules HR/SOP |
| quarantine_records | ~180 | **213** | Tăng do quarantine HR 10 ngày + invalid doc |
| Expectation halt? | Có (thiếu doc / stale refund) | **Không** — tất cả halt pass |

---

## 2. Before / after retrieval (bắt buộc)

**Câu hỏi then chốt:** `q_refund_window`  
**Trước (inject-bad, `after_inject_bad.csv`):** `hits_forbidden=yes` — top-1 preview chứa *"14 ngày làm việc"*.  
**Sau (`after_fix_eval.csv`):** `hits_forbidden=no` — top-1 preview *"7 ngày làm việc"*.

**HR versioning — `q_hr_annual_leave_under3`:**  
**Trước:** `contains_expected=yes`, `hits_forbidden=no` (inject không ảnh hưởng HR).  
**Sau:** `contains_expected=yes`, top-1 *"12 ngày phép năm theo chính sách 2026"* — rule `quarantine_hr_stale_10d_content` loại bản 2025.

**Grading:** `artifacts/eval/grading_run.jsonl` — 10/10 câu `gq_d10_01`…`gq_d10_10` pass (`instructor_quick_check.py` exit 0).

---

## 3. Freshness & monitor

- Lệnh: `python etl_pipeline.py freshness --manifest artifacts/manifests/manifest_day10-final.json`
- Kết quả: **FAIL** — `age_hours≈1471`, `sla_hours=24`, `latest_exported_at=2026-04-10T00:00:00`
- **Giải thích:** snapshot CSV mẫu cố ý cũ; SLA 24h áp cho *dữ liệu publish* trong lab. Production sẽ dùng timestamp export thực hoặc nới SLA khi replay historical data.

---

## 4. Corruption inject (Sprint 3)

- Lệnh: `python etl_pipeline.py run --run-id inject-bad --no-refund-fix --skip-validate`
- **Hỏng gì:** tắt rule fix 14→7 ngày; embed dù chunk stale còn "14 ngày".
- **Phát hiện:** `expectation[refund_no_stale_14d_window] FAIL`; eval `q_refund_window` → `hits_forbidden=yes`.
- **Khôi phục:** rerun `day10-final` → expectation pass, eval sạch.

---

## 5. Hạn chế & việc chưa làm

- Chưa tích hợp Great Expectations / pydantic validate schema (chỉ custom expectations).
- Freshness chỉ đo 1 boundary (publish); chưa log riêng ingest_done vs index_visible.
- Chưa nối trực tiếp collection Day 09 — cần cấu hình `CHROMA_COLLECTION` thủ công.
