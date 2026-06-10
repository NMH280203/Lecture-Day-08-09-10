# Báo cáo cá nhân — Lab Day 10

**Họ tên:** Nguyễn Mạnh Hiếu
**Vai trò:** Cleaning & Quality Owner  
**run_id tham chiếu:** `day10-final`

---

## Phần phụ trách

File `transform/cleaning_rules.py` — functions `clean_rows`, `_hr_leave_min_effective_date`, rules quarantine HR stale và strip prefix. File `quality/expectations.py` — expectations `required_kb_doc_ids_present`, `no_unclear_content_marker`, `hr_leave_has_12d_annual`.

---

## Một quyết định kỹ thuật

Chọn **halt** cho `required_kb_doc_ids_present` thay vì warn: nếu thiếu `access_control_sop` trong cleaned, agent vẫn chạy nhưng grading `gq_d10_10` fail âm thầm. Halt buộc sửa allowlist trước khi embed — phù hợp quality gate trước tốn chi phí vector index. Cutoff HR đọc từ env `HR_LEAVE_MIN_EFFECTIVE_DATE` thay vì hard-code để đổi version qua contract mà không sửa code.

---

## Một sự cố / anomaly

Phát hiện `gq_d10_06` fail dù chunk escalation P1 đã có trong cleaned CSV: retrieval top-5 không chứa "10 phút" vì chunk SLA generic "15 phút / 4 giờ" rank cao hơn. **Fix:** rule `enrich_p1_escalation_topic_prefix` thêm tiền tố "Ticket P1 auto escalation SLA —" vào chunk Escalation P1. Evidence: `grading_run.jsonl` dòng `gq_d10_06` chuyển `contains_expected` từ false → true.

---

## Before / after

Log inject: `expectation[refund_no_stale_14d_window] FAIL (halt) :: violations=1` trong `artifacts/logs/run_inject-bad.log`.  
CSV: `after_inject_bad.csv` — `q_refund_window,hits_forbidden=yes` vs `after_fix_eval.csv` — `hits_forbidden=no`.

---

## Cải tiến 2 giờ tiếp theo

Thêm freshness tại **2 boundary** (ingest timestamp vs `run_timestamp` publish) và ghi cả hai vào manifest để đạt bonus monitoring trong SCORING.md.
