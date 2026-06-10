# Runbook — Lab Day 10 (incident tối giản)

---

## Symptom

User / agent trả lời sai nghiệp vụ: ví dụ **"14 ngày"** thay vì **7 ngày** hoàn tiền, hoặc **10 ngày phép năm** thay vì **12 ngày** (HR 2026), hoặc không tìm thấy **access_control_sop**.

---

## Detection

| Metric | Ngưỡng | Nguồn |
|--------|--------|-------|
| `hits_forbidden=true` | eval / grading | `python eval_retrieval.py`, `grading_run.py` |
| `expectation[...] FAIL (halt)` | bất kỳ halt fail | `artifacts/logs/run_*.log` |
| `freshness_check=FAIL` | `age_hours > FRESHNESS_SLA_HOURS` | cuối log pipeline hoặc `etl_pipeline.py freshness` |
| `quarantine_records` spike | tăng đột biến so run trước | manifest JSON |

---

## Diagnosis

| Bước | Việc làm | Kết quả mong đợi |
|------|----------|------------------|
| 1 | Kiểm tra `artifacts/manifests/manifest_<run-id>.json` | `run_id`, `cleaned_records`, `latest_exported_at` khớp log |
| 2 | Mở `artifacts/quarantine/*.csv` — lọc `reason` | Xác định doc_id / rule nào loại nhiều record |
| 3 | Chạy `python eval_retrieval.py --out artifacts/eval/debug.csv` | Dòng `hits_forbidden=yes` hoặc `top1_doc_expected=no` |
| 4 | Thứ tự debug | **Freshness → Volume → Schema → Lineage (run_id)** trước khi đổi model |

---

## Mitigation

1. **Rerun pipeline chuẩn:** `python etl_pipeline.py run --run-id recovery-<timestamp>`
2. **Không dùng `--skip-validate`** trên production path.
3. Nếu inject corruption (Sprint 3): chạy lại run chuẩn để prune vector stale (`embed_prune_removed` trong log).
4. Tạm thời: banner "dữ liệu đang cập nhật" trên agent nếu `freshness_check=FAIL`.

---

## Prevention

1. Giữ **halt** cho: `refund_no_stale_14d_window`, `hr_leave_no_stale_10d_annual`, `required_kb_doc_ids_present`.
2. Đồng bộ **allowlist** `cleaning_rules.py` ↔ `contracts/data_contract.yaml` khi thêm nguồn mới.
3. Đọc cutoff HR từ `HR_LEAVE_MIN_EFFECTIVE_DATE` — không hard-code trong code.
4. Alert Slack `#cs-it-data-alerts` khi pipeline exit ≠ 0 hoặc grading JSONL có `contains_expected=false`.
