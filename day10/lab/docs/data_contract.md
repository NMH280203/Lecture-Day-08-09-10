# Data contract — Lab Day 10

> Đồng bộ với `contracts/data_contract.yaml` · owner: **CS-IT-Data-Platform**

---

## 1. Nguồn dữ liệu (source map)

| Nguồn | Phương thức ingest | Failure mode chính | Metric / alert |
|-------|-------------------|-------------------|----------------|
| `policy_refund_v4` | Batch CSV export CRM | Chunk stale "14 ngày", typo lặp từ | `expectation[refund_no_stale_14d_window]` halt; `quarantine_records` |
| `sla_p1_2026` | Batch CSV export ticket system | Duplicate chunk SLA, thiếu chunk escalation | `grading gq_d10_06`; đếm `doc_id=sla_p1_2026` trong cleaned |
| `hr_leave_policy` | Batch CSV export HRIS | Xung đột 10 vs 12 ngày phép, ngày hiệu lực cũ | `expectation[hr_leave_no_stale_10d_annual]` halt; env `HR_LEAVE_MIN_EFFECTIVE_DATE` |
| `it_helpdesk_faq` | Batch CSV export KB | Chunk rỗng, duplicate | `quarantine reason=missing_chunk_text` |
| `access_control_sop` | Batch CSV export IAM (mới thêm) | Thiếu trong allowlist baseline → mất retrieval gq_d10_10 | `expectation[required_kb_doc_ids_present]` halt |

---

## 2. Schema cleaned

| Cột | Kiểu | Bắt buộc | Ghi chú |
|-----|------|----------|---------|
| chunk_id | string | Có | Hash ổn định sau clean |
| doc_id | string | Có | Thuộc `allowed_doc_ids` (5 nguồn) |
| chunk_text | string | Có | min 8 ký tự; không chứa marker parser lỗi |
| effective_date | date (ISO) | Có | `YYYY-MM-DD` sau normalize |
| exported_at | datetime | Có | Giữ nguyên từ raw để đo freshness |

---

## 3. Quy tắc quarantine vs drop

| Hành vi | Khi nào | Đích đến |
|---------|---------|----------|
| **Quarantine** | doc_id lạ, ngày lỗi, HR stale, duplicate, text rỗng | `artifacts/quarantine/quarantine_<run-id>.csv` + cột `reason` |
| **Drop (không ghi)** | Không dùng silent drop — mọi loại bỏ đều có reason trong quarantine |
| **Approve merge** | SME Data + owner doc_id xem xét CSV quarantine trước khi sửa allowlist/rule |

---

## 4. Phiên bản & canonical

| doc_id | Source of truth | Versioning |
|--------|-----------------|------------|
| `policy_refund_v4` | `data/docs/policy_refund_v4.txt` | Cửa sổ hoàn tiền **7 ngày làm việc** (v4) |
| `hr_leave_policy` | `data/docs/hr_leave_policy.txt` | Hiệu lực từ `HR_LEAVE_MIN_EFFECTIVE_DATE` (mặc định 2026-01-01); **12 ngày phép năm** cho <3 năm KN |
| `access_control_sop` | `data/docs/access_control_sop.txt` | Level 4 = IT Manager + CISO |
