#!/usr/bin/env python3
"""
Giao diện web đơn giản — thử retrieval trên Chroma sau khi chạy pipeline.

  streamlit run retrieval_ui.py

Yêu cầu: đã chạy `python etl_pipeline.py run` ít nhất một lần.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import streamlit as st
from dotenv import load_dotenv

from monitoring.freshness_check import check_manifest_freshness

load_dotenv()

ROOT = Path(__file__).resolve().parent
GRADING_PATH = ROOT / "data" / "grading_questions.json"
TEST_PATH = ROOT / "data" / "test_questions.json"
MANIFEST_DIR = ROOT / "artifacts" / "manifests"
QUAR_DIR = ROOT / "artifacts" / "quarantine"
LOG_DIR = ROOT / "artifacts" / "logs"


@st.cache_resource(show_spinner="Đang tải embedding model & Chroma…")
def get_collection():
    import chromadb
    from chromadb.utils import embedding_functions

    db_path = os.environ.get("CHROMA_DB_PATH", str(ROOT / "chroma_db"))
    collection_name = os.environ.get("CHROMA_COLLECTION", "day10_kb")
    model_name = os.environ.get("EMBEDDING_MODEL", "all-MiniLM-L6-v2")

    client = chromadb.PersistentClient(path=db_path)
    emb = embedding_functions.SentenceTransformerEmbeddingFunction(model_name=model_name)
    col = client.get_collection(name=collection_name, embedding_function=emb)
    return col, db_path, collection_name, model_name


def load_grading_questions() -> List[Dict[str, Any]]:
    if not GRADING_PATH.is_file():
        return []
    return json.loads(GRADING_PATH.read_text(encoding="utf-8"))


def latest_manifest() -> Tuple[Optional[Dict[str, Any]], Optional[Path]]:
    if not MANIFEST_DIR.is_dir():
        return None, None
    files = sorted(MANIFEST_DIR.glob("manifest_*.json"), key=lambda p: p.stat().st_mtime, reverse=True)
    if not files:
        return None, None
    return json.loads(files[0].read_text(encoding="utf-8")), files[0]


def load_test_questions() -> List[Dict[str, Any]]:
    if not TEST_PATH.is_file():
        return []
    return json.loads(TEST_PATH.read_text(encoding="utf-8"))


def render_chunks(docs: List[str], metas: List[Dict[str, Any]], ids: List[str]) -> None:
    if not docs:
        st.warning("Không có kết quả.")
        return
    for i, (doc, meta, cid) in enumerate(zip(docs, metas, ids), start=1):
        with st.expander(f"#{i} · `{meta.get('doc_id', '?')}` · `{cid}`", expanded=(i == 1)):
            st.write(doc)
            st.caption(
                f"effective_date={meta.get('effective_date', '—')} · "
                f"run_id={meta.get('run_id', '—')}"
            )


def query_retrieval(question: str, top_k: int) -> Tuple[List[str], List[Dict[str, Any]], List[str]]:
    col, _, _, _ = get_collection()
    res = col.query(query_texts=[question], n_results=top_k)
    docs = (res.get("documents") or [[]])[0]
    metas = (res.get("metadatas") or [[]])[0]
    ids = (res.get("ids") or [[]])[0]
    return docs, metas, ids


def eval_question(q: Dict[str, Any], docs: List[str], metas: List[Dict[str, Any]]) -> Dict[str, Any]:
    blob = " ".join(docs).lower()
    must_any = [x.lower() for x in q.get("must_contain_any", [])]
    forbidden = [x.lower() for x in q.get("must_not_contain", [])]
    top_doc = (metas[0] or {}).get("doc_id", "") if metas else ""
    want_top1 = (q.get("expect_top1_doc_id") or "").strip()

    return {
        "contains_expected": any(m in blob for m in must_any) if must_any else True,
        "hits_forbidden": any(m in blob for m in forbidden) if forbidden else False,
        "top1_doc_id": top_doc,
        "top1_doc_matches": (top_doc == want_top1) if want_top1 else None,
    }


def status_badge(ok: bool, label_ok: str, label_bad: str) -> str:
    return f"✅ {label_ok}" if ok else f"❌ {label_bad}"


def main() -> None:
    st.set_page_config(
        page_title="Day 10 — Retrieval Demo",
        page_icon="🔍",
        layout="wide",
    )
    st.title("Day 10 Lab — Retrieval UI")
    st.caption("Thử câu hỏi trên vector store sau pipeline ETL · CS + IT Helpdesk")

    try:
        col, db_path, collection_name, model_name = get_collection()
        count = col.count()
    except Exception as exc:
        st.error(
            "Không kết nối được Chroma. Chạy pipeline trước:\n\n"
            "```bash\npython etl_pipeline.py run --run-id day10-final\n```"
        )
        st.exception(exc)
        return

    manifest, manifest_path = latest_manifest()

    with st.sidebar:
        st.header("Cấu hình")
        st.write(f"**Collection:** `{collection_name}`")
        st.write(f"**DB path:** `{db_path}`")
        st.write(f"**Model:** `{model_name}`")
        st.metric("Vectors trong index", count)
        top_k = st.slider("Top-K", min_value=1, max_value=10, value=5)

        if manifest:
            st.divider()
            st.subheader("Manifest gần nhất")
            st.write(f"**run_id:** `{manifest.get('run_id', '—')}`")
            st.write(f"**cleaned:** {manifest.get('cleaned_records', '—')}")
            st.write(f"**quarantine:** {manifest.get('quarantine_records', '—')}")
            st.write(f"**exported_at:** {manifest.get('latest_exported_at', '—')}")
        else:
            st.info("Chưa có manifest trong `artifacts/manifests/`.")

    tab_query, tab_grading, tab_all, tab_pipeline = st.tabs(
        ["Hỏi tự do", "Câu grading", "Chấm 10 câu", "Pipeline"]
    )

    with tab_query:
        st.subheader("Đặt câu hỏi retrieval")
        examples = [
            "Khách hàng có bao nhiêu ngày để yêu cầu hoàn tiền?",
            "Level 4 Admin Access yêu cầu phê duyệt bởi ai?",
            "VPN cho phép kết nối tối đa bao nhiêu thiết bị?",
        ]
        picked = st.selectbox("Ví dụ nhanh", ["— chọn —"] + examples)
        default_q = picked if picked != "— chọn —" else examples[0]
        question = st.text_area("Câu hỏi", value=default_q, height=90)
        if st.button("Tìm kiếm", type="primary", key="btn_free"):
            with st.spinner("Đang query Chroma…"):
                docs, metas, ids = query_retrieval(question.strip(), top_k)
            render_chunks(docs, metas, ids)

    with tab_grading:
        questions = load_grading_questions()
        if not questions:
            st.warning("Không tìm thấy `data/grading_questions.json`.")
        else:
            labels = {f"{q['id']}: {q['question'][:70]}…": q for q in questions}
            choice = st.selectbox("Chọn câu grading", list(labels.keys()))
            q = labels[choice]
            st.write(q["question"])
            if st.button("Chạy retrieval", type="primary", key="btn_grading"):
                with st.spinner("Đang query…"):
                    docs, metas, ids = query_retrieval(q["question"], top_k)
                result = eval_question(q, docs, metas)

                c1, c2, c3 = st.columns(3)
                with c1:
                    st.write(
                        status_badge(
                            result["contains_expected"],
                            "contains_expected",
                            "thiếu keyword kỳ vọng",
                        )
                    )
                with c2:
                    st.write(
                        status_badge(
                            not result["hits_forbidden"],
                            "không hits_forbidden",
                            "có từ cấm trong top-k",
                        )
                    )
                with c3:
                    if result["top1_doc_matches"] is not None:
                        st.write(
                            status_badge(
                                result["top1_doc_matches"],
                                f"top1 = {result['top1_doc_id']}",
                                f"top1 sai ({result['top1_doc_id']})",
                            )
                        )

                if q.get("grading_criteria"):
                    st.caption("Tiêu chí: " + " · ".join(q["grading_criteria"]))

                st.divider()
                render_chunks(docs, metas, ids)

    with tab_all:
        st.subheader("Chấm nhanh 10 câu grading")
        if st.button("Chạy tất cả", type="primary", key="btn_all"):
            with st.spinner("Đang chấm 10 câu…"):
                questions = load_grading_questions()
                rows = []
                for q in questions:
                    docs, metas, _ = query_retrieval(q["question"], top_k)
                    r = eval_question(q, docs, metas)
                    rows.append(
                        {
                            "id": q["id"],
                            "contains_expected": r["contains_expected"],
                            "hits_forbidden": r["hits_forbidden"],
                            "top1_doc_matches": r["top1_doc_matches"],
                            "top1_doc_id": r["top1_doc_id"],
                        }
                    )
                st.session_state["grading_rows"] = rows

        rows = st.session_state.get("grading_rows", [])
        if rows:
            passed = sum(
                1
                for r in rows
                if r["contains_expected"]
                and not r["hits_forbidden"]
                and (r["top1_doc_matches"] is None or r["top1_doc_matches"])
            )
            st.metric("Pass", f"{passed}/{len(rows)}")
            st.dataframe(rows, use_container_width=True, hide_index=True)

        st.divider()
        st.caption("21 câu tự kiểm (test_questions.json)")
        if st.button("Chạy test set", key="btn_test"):
            with st.spinner("Đang eval test set…"):
                test_qs = load_test_questions()
                test_rows = []
                for q in test_qs:
                    docs, metas, _ = query_retrieval(q["question"], top_k)
                    r = eval_question(q, docs, metas)
                    test_rows.append(
                        {
                            "id": q.get("id"),
                            "contains_expected": r["contains_expected"],
                            "hits_forbidden": r["hits_forbidden"],
                            "top1_doc_id": r["top1_doc_id"],
                        }
                    )
                st.session_state["test_rows"] = test_rows

        test_rows = st.session_state.get("test_rows", [])
        if test_rows:
            ok = sum(1 for r in test_rows if r["contains_expected"] and not r["hits_forbidden"])
            st.metric("Test pass", f"{ok}/{len(test_rows)}")
            st.dataframe(test_rows, use_container_width=True, hide_index=True)

    with tab_pipeline:
        st.subheader("Trạng thái pipeline")
        if not manifest or not manifest_path:
            st.warning("Chưa có manifest. Chạy: `python etl_pipeline.py run --run-id day10-final`")
        else:
            sla = float(os.environ.get("FRESHNESS_SLA_HOURS", "24"))
            status, detail = check_manifest_freshness(manifest_path, sla_hours=sla)

            m1, m2, m3, m4 = st.columns(4)
            m1.metric("raw_records", manifest.get("raw_records", "—"))
            m2.metric("cleaned_records", manifest.get("cleaned_records", "—"))
            m3.metric("quarantine_records", manifest.get("quarantine_records", "—"))
            m4.metric("freshness", status)

            st.json(detail)
            with st.expander("Manifest đầy đủ"):
                st.json(manifest)

            quar_files = sorted(QUAR_DIR.glob("quarantine_*.csv"), key=lambda p: p.stat().st_mtime, reverse=True)
            if quar_files:
                st.caption(f"Quarantine mới nhất: `{quar_files[0].name}`")
                import csv
                from collections import Counter

                reasons: Counter[str] = Counter()
                with quar_files[0].open(encoding="utf-8", newline="") as f:
                    for row in csv.DictReader(f):
                        reasons[row.get("reason", "unknown")] += 1
                if reasons:
                    st.bar_chart(dict(reasons.most_common(10)))

            log_files = sorted(LOG_DIR.glob("run_*.log"), key=lambda p: p.stat().st_mtime, reverse=True)
            if log_files:
                with st.expander(f"Log gần nhất: {log_files[0].name}"):
                    tail = log_files[0].read_text(encoding="utf-8").splitlines()[-25:]
                    st.code("\n".join(tail))


if __name__ == "__main__":
    main()
