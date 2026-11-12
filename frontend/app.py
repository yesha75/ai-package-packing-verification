"""Streamlit UI for the FastAPI + YOLO package inspection project.

Run from the repository root:
    python -m streamlit run frontend/app.py
"""
from __future__ import annotations

import os
import sys
from collections import Counter
from datetime import datetime
from html import escape
from pathlib import Path

# Works both with `streamlit run frontend/app.py` and `python -m streamlit ...`.
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import streamlit as st

from frontend.api import APIError, PackageAPI
from frontend.presentation import (
    detection_rows, display_timestamp, item_rows,
    review_reason_summary, summary_stats,
)


st.set_page_config(
    page_title="PackSure | Package Verification",
    page_icon="📦",
    layout="wide",
    initial_sidebar_state="expanded",
)


def render_html_table(rows: list[dict]) -> None:
    """Render safely escaped table HTML without st.dataframe or PyArrow."""
    if not rows:
        st.info("No data available.")
        return

    headers = list(rows[0].keys())
    header_html = "".join(f"<th>{escape(str(key))}</th>" for key in headers)
    body_html = "".join(
        "<tr>" + "".join(
            f"<td>{escape(str(row.get(key, '')))}</td>" for key in headers
        ) + "</tr>"
        for row in rows
    )
    st.markdown(
        '<div class="data-table-wrap"><table class="data-table">'
        f"<thead><tr>{header_html}</tr></thead>"
        f"<tbody>{body_html}</tbody></table></div>",
        unsafe_allow_html=True,
    )


def render_html_bars(items: list[tuple[str, int]], *, empty_label: str = "No data available.") -> None:
    """Render accessible lightweight bars without Streamlit charts/PyArrow."""
    if not items:
        st.info(empty_label)
        return

    largest = max((max(int(count), 0) for _, count in items), default=0) or 1
    parts = []
    for label, count in items:
        count = max(0, int(count))
        width = 100 * count / largest
        parts.append(
            '<div class="bar-item">'
            f'<div class="bar-label"><span>{escape(str(label))}</span><strong>{count:,}</strong></div>'
            '<div class="bar-track">'
            f'<div class="bar-fill" style="width:{width:.1f}%"></div>'
            '</div></div>'
        )
    st.markdown('<div class="bars">' + "".join(parts) + '</div>', unsafe_allow_html=True)


def daily_inspection_counts(records: list[dict]) -> list[tuple[str, int]]:
    """Count recent inspections by UTC calendar day using only the standard library."""
    counts = Counter()
    for record in records:
        raw = record.get("created_at", "")
        if not isinstance(raw, str):
            continue
        try:
            day = datetime.fromisoformat(raw.replace("Z", "+00:00")).date().isoformat()
        except ValueError:
            continue
        counts[day] += 1
    return sorted(counts.items())


st.markdown("""
<style>
    .stApp { background: #f8fafd; }
    .block-container { max-width: 1420px; padding-top: 1.6rem; padding-bottom: 3rem; }
    .hero {
        border: 1px solid #dce6f6;
        background: linear-gradient(112deg, #ffffff 0%, #eef4ff 100%);
        border-radius: 18px; padding: 25px 30px; margin: 4px 0 24px;
    }
    .hero h1 { color: #17366d; font-size: 2.15rem; font-weight: 750; margin: 0 0 5px; }
    .hero p { color: #586b87; margin: 0; font-size: 0.99rem; }
    .eyebrow { color: #285bbf !important; font-size: .78rem !important;
               font-weight: 750; letter-spacing: .13em; margin-bottom: 9px !important; }
    [data-testid="stMetric"] {
        background: #fff; padding: 16px 18px; border-radius: 14px;
        border: 1px solid #e1e9f4; min-height: 112px;
    }
    [data-testid="stMetricLabel"] { color: #5c6e89; }
    [data-testid="stVerticalBlockBorderWrapper"] { border-color: #e4eaf2; }
    .small-note { color: #667992; font-size: .88rem; }
    .rule-label { font-weight: 750; color: #1d3658; }
    .tagline { margin: 4px 0 15px; color: #60738c; }
    .data-table-wrap { overflow-x: auto; width: 100%; margin: 10px 0 18px; }
    .data-table { border-collapse: collapse; width: 100%; font-size: .91rem; background: #fff; }
    .data-table th, .data-table td { border-bottom: 1px solid #e2e8f2;
        padding: 10px 13px; text-align: left; vertical-align: top; }
    .data-table th { background: #eef4ff; color: #1b3c73; font-weight: 700; }
    .data-table tr:nth-child(even) { background: #fafcff; }
    .bar-item { margin: 0 0 16px; }
    .bar-label { display: flex; justify-content: space-between; gap: 12px;
        font-size: .9rem; margin-bottom: 5px; color: #253b5d; }
    .bar-track { height: 14px; background: #e8edf5; border-radius: 6px; overflow: hidden; }
    .bar-fill { height: 100%; background: #2563eb; border-radius: 6px; }
    .bars { margin: 12px 0 20px; }
</style>
""", unsafe_allow_html=True)


def call_or_warn(func, *, default=None):
    try:
        return func()
    except APIError as exc:
        st.error(str(exc))
        return default


def render_metrics(summary: dict) -> None:
    stats = summary_stats(summary)
    a, b, c, d = st.columns(4, gap="medium")
    a.metric("Total inspected", f"{stats['inspected']:,}")
    b.metric("Passed", f"{stats['passed']:,}")
    c.metric("Needs review", f"{stats['needs_review']:,}")
    d.metric("Pass rate", f"{stats['pass_rate']:.1f}%")


def render_image(api: PackageAPI, record: dict, original: bytes | None, suffix: str) -> None:
    image_path = record.get("annotated_image_url", "")
    annotated = None
    if image_path:
        try:
            annotated = api.annotated_image(image_path)
        except APIError as exc:
            st.info(f"Annotated image unavailable: {exc}")

    if original is not None:
        left, right = st.columns(2, gap="large")
        with left:
            st.markdown("**Uploaded image**")
            st.image(original, use_container_width=True)
        with right:
            st.markdown("**YOLO annotated image**")
            if annotated:
                st.image(annotated, use_container_width=True)
            else:
                st.caption("No annotated image is available.")
    elif annotated:
        st.markdown("**YOLO annotated image**")
        st.image(annotated, use_container_width=True)
        st.caption("Original uploads are not persisted by the backend; the annotated image is saved.")

    if annotated:
        safe_filename = Path(str(record.get("filename") or "inspection").replace("\\", "/")).stem
        st.download_button(
            "Download annotated image", data=annotated,
            file_name=f"{safe_filename}_annotated.jpg", mime="image/jpeg",
            key=f"download-image-{suffix}",
        )


def render_inspection(api: PackageAPI, record: dict, checklist_lookup: dict,
                      *, original: bytes | None = None, suffix: str = "result") -> None:
    status = record.get("status", "Unknown")
    st.markdown(f"### {record.get('filename', 'Inspection')}")
    if status == "Pass":
        st.success("PASS — All counted detections match the selected checklist.")
    elif status == "Needs Review":
        st.warning("NEEDS REVIEW — A human inspector should verify this package.")
    else:
        st.info(f"Inspection status: {status}")

    details = st.columns(4)
    details[0].metric("Confident item count", sum(record.get("detected_counts", {}).values()))
    details[1].metric("Missing quantity", sum(record.get("missing", {}).values()))
    details[2].metric("Unexpected quantity", sum(record.get("unexpected", {}).values()) + sum(record.get("excess", {}).values()))
    details[3].metric("Processing", f"{float(record.get('processing_ms', 0))/1000:.2f}s")

    reasons = record.get("reasons") or []
    if reasons:
        st.markdown("**Reasons for review**")
        for reason in reasons:
            st.markdown(f"- {reason}")
    else:
        st.caption("No review reasons were reported by the verification engine.")

    st.caption(f"Checklist: `{record.get('checklist_id', '')}`  |  "
               f"Recorded: {display_timestamp(record.get('created_at', ''))}  |  "
               f"Uncertainty flagged: {'Yes' if record.get('uncertain') else 'No'}")

    render_image(api, record, original, suffix)

    expected = checklist_lookup.get(record.get("checklist_id", ""), {}).get("items", {})
    st.markdown("#### Item-by-item verification")
    rows = item_rows(expected, record.get("detected_counts", {}))
    if rows:
        render_html_table(rows)
    else:
        st.info("No expected or detected item counts available.")

    st.markdown("#### Raw YOLO detections")
    det_rows = detection_rows(record.get("detections", []))
    if det_rows:
        render_html_table(det_rows)
    else:
        st.info("YOLO reported no detections for this image.")
    st.caption("The raw detection table can include predictions below the backend's counting threshold. "
               "The verification engine determines which predictions contribute to counts.")

    with st.expander("Technical JSON response"):
        st.json(record)


def render_recent_table(records: list[dict]) -> None:
    if not records:
        st.info("No saved inspections yet. Run an inspection to populate history.")
        return
    rows = [
        {"Time (UTC)": display_timestamp(r.get("created_at", "")),
         "Filename": r.get("filename", ""),
         "Checklist": r.get("checklist_id", ""),
         "Status": r.get("status", ""),
         "Objects counted": sum(r.get("detected_counts", {}).values()),
         "Duration (s)": round(float(r.get("processing_ms", 0)) / 1000, 2)}
        for r in records
    ]
    render_html_table(rows)


# Connection settings live in the sidebar so they can be changed without editing code.
with st.sidebar:
    st.markdown("## 📦 PackSure")
    st.caption("PACKAGE QUALITY CONTROL")
    st.divider()
    st.markdown("**Backend connection**")
    base_url = st.text_input(
        "FastAPI URL",
        value=os.getenv("API_BASE_URL", "http://127.0.0.1:8000"),
        help="Use the host and port running uvicorn. For a local project, use http://127.0.0.1:8000.",
    )

try:
    api = PackageAPI(base_url)
    health = api.health()
    checklists = api.checklists()
    summary = api.summary()
except APIError as exc:
    st.sidebar.error("Backend disconnected")
    st.error(str(exc))
    st.info("Start FastAPI in another terminal, then refresh this page.")
    st.code("uvicorn backend.main:app --reload", language="powershell")
    st.stop()

with st.sidebar:
    st.success("Connected to FastAPI")
    models_by_checklist = health.get("models_by_checklist", {})
    if models_by_checklist:
        st.caption("Model by checklist: " + "; ".join(
            f"{checklist_id} → {weights}"
            for checklist_id, weights in models_by_checklist.items()
        ))
    else:
        st.caption("Model configured: " + str(health.get("model_weights", "unknown")))
    st.divider()
    st.markdown("**How it works**")
    st.caption("1. Choose a packing checklist\n\n2. Upload package images\n\n3. Run YOLO verification\n\n4. Review results and export")
    st.divider()
    st.caption("Decision support only. A Pass is based on model predictions, not a guarantee of physical packing accuracy.")

st.markdown("""
<div class="hero">
  <p class="eyebrow">AI-POWERED QUALITY CONTROL</p>
  <h1>Package Packing Verification</h1>
  <p>Inspect packed orders, compare detected items with expected quantities, and route uncertain cases for human review.</p>
</div>
""", unsafe_allow_html=True)
render_metrics(summary)
st.write("")

if not checklists:
    st.error("No valid checklists were returned. Check config/checklists.json in your backend project.")
    st.stop()

checklist_lookup = {c["id"]: c for c in checklists}
recent_records = call_or_warn(lambda: api.inspections(limit=100), default=[])

inspect_tab, history_tab, analytics_tab = st.tabs([
    "🔍 Inspect packages", "🕘 Inspection history", "📊 Analytics & export",
])

with inspect_tab:
    st.subheader("New inspection")
    left, right = st.columns([1, 1], gap="large")
    with left:
        selected_id = st.selectbox(
            "Expected packing checklist", options=list(checklist_lookup),
            format_func=lambda cid: f"{checklist_lookup[cid]['name']} ({cid})",
        )
        checklist = checklist_lookup[selected_id]
        st.caption("Required items and quantities")
        render_html_table([
            {"Item class": name.title(), "Expected quantity": n}
            for name, n in checklist["items"].items()
        ])
    with right:
        mode = st.radio("Inspection mode", ["Single image", "Batch images"], horizontal=True)
        st.info("Upload JPG, PNG or WEBP images. Limit: 10 MB per file; batch size: up to 10 images.")
        st.caption("For best results, use a clear top-down photo with visible, minimally overlapping items.")

    is_batch = mode == "Batch images"
    if is_batch:
        uploads = st.file_uploader("Upload package photos", type=["jpg", "jpeg", "png", "webp"],
                                   accept_multiple_files=True, key="package_upload_batch")
    else:
        single = st.file_uploader("Upload a package photo", type=["jpg", "jpeg", "png", "webp"],
                                  accept_multiple_files=False, key="package_upload_single")
        uploads = [single] if single is not None else []

    if uploads:
        st.markdown(f"**Selected images: {len(uploads)}**")
        preview_cols = st.columns(min(len(uploads), 3))
        for idx, uploaded in enumerate(uploads[:6]):
            with preview_cols[idx % len(preview_cols)]:
                st.image(uploaded.getvalue(), caption=uploaded.name, use_container_width=True)
        if len(uploads) > 6:
            st.caption(f"+ {len(uploads)-6} more files selected")

    valid_upload = bool(uploads) and len(uploads) <= 10 and all(
        0 < f.size <= 10 * 1024 * 1024 for f in uploads
    )
    if uploads and not valid_upload:
        st.error("Choose 1–10 nonempty images, each no larger than 10 MB.")

    if st.button("Run AI inspection", type="primary", disabled=not valid_upload, use_container_width=True):
        prepared = [(f.name, f.getvalue()) for f in uploads]
        try:
            with st.spinner("Running YOLO detection and packing verification. The first inference may take longer..."):
                if is_batch:
                    results = api.inspect_batch(prepared, selected_id)
                else:
                    results = [api.inspect_one(prepared[0][0], prepared[0][1], selected_id)]
            st.session_state["latest_results"] = results
            st.session_state["latest_original_images"] = [raw for _, raw in prepared]
            st.session_state["latest_api_url"] = api.base_url
            st.session_state["latest_checklist"] = selected_id
            st.success(f"Inspection complete — {len(results)} image(s) processed and saved to backend history.")
        except (APIError, ValueError) as exc:
            st.error(str(exc))

    latest = st.session_state.get("latest_results", [])
    if latest and st.session_state.get("latest_api_url") == api.base_url:
        st.divider()
        st.subheader("Latest inspection results")
        n_pass = sum(r.get("status") == "Pass" for r in latest)
        st.caption(f"{len(latest)} inspected · {n_pass} passed · {len(latest)-n_pass} need review")
        idx = st.selectbox(
            "Choose result to examine", list(range(len(latest))),
            format_func=lambda i: f"{latest[i].get('filename','Image '+str(i+1))} — {latest[i].get('status', 'Unknown')}",
            key="latest_result_select",
        )
        originals = st.session_state.get("latest_original_images", [])
        original = originals[idx] if idx < len(originals) else None
        render_inspection(api, latest[idx], checklist_lookup,
                          original=original, suffix=f"latest-{latest[idx].get('id',idx)}")
    else:
        st.caption("Submit images above to see inspection results, visual annotations, and a detailed rule breakdown.")

with history_tab:
    st.subheader("Previous inspections")
    st.caption("Read-only history from the backend SQLite database. Most recent 100 inspections are shown here.")
    status_filter = st.selectbox("Filter by status", ["All", "Pass", "Needs Review"], key="status_filter")
    text_filter = st.text_input("Search filename", placeholder="e.g. package_01", key="filename_filter")
    filtered = [r for r in recent_records
                if (status_filter == "All" or r.get("status") == status_filter)
                and text_filter.lower() in r.get("filename", "").lower()]
    render_recent_table(filtered)
    if filtered:
        ids = [r["id"] for r in filtered]
        by_id = {r["id"]: r for r in filtered}
        selected_record_id = st.selectbox(
            "Open a saved inspection", ids,
            format_func=lambda key: f"{by_id[key].get('filename','Image')} · {by_id[key].get('status','Unknown')} · {display_timestamp(by_id[key].get('created_at',''))}",
            key="history_record_select",
        )
        st.divider()
        render_inspection(api, by_id[selected_record_id], checklist_lookup,
                          suffix=f"history-{selected_record_id}")

with analytics_tab:
    st.subheader("Inspection analytics")
    st.caption("Overall status counts are from all inspections stored by FastAPI; trends below use only the latest 100 records.")
    stats = summary_stats(summary)
    c1, c2 = st.columns(2, gap="large")
    with c1:
        st.markdown("**Overall decision distribution**")
        render_html_bars([
            ("Pass", stats["passed"]),
            ("Needs Review", stats["needs_review"]),
        ])
    with c2:
        st.markdown("**Recent review reasons**")
        reasons = review_reason_summary(recent_records)
        if reasons:
            render_html_table([
                {"Review reason": label, "Occurrences": amount}
                for label, amount in reasons
            ])
        else:
            st.info("No reasons for review have been recorded yet.")

    if recent_records:
        st.markdown("**Recent inspection volume by day (UTC)**")
        render_html_bars(daily_inspection_counts(recent_records))

    st.divider()
    st.markdown("### Export inspection results")
    st.caption("Download all saved inspection records as a CSV file, including decisions, counts, and review reasons.")
    if st.button("Prepare CSV export", key="prepare_csv"):
        try:
            st.session_state["export_csv"] = api.export_csv()
            st.session_state["csv_api_url"] = api.base_url
        except APIError as exc:
            st.error(str(exc))
    csv_bytes = st.session_state.get("export_csv")
    if csv_bytes and st.session_state.get("csv_api_url") == api.base_url:
        st.download_button("Download inspection_results.csv", data=csv_bytes,
                           file_name="inspection_results.csv", mime="text/csv", type="primary")

st.divider()
st.caption("PackSure · Academic decision-support prototype · FastAPI + YOLOv8 + Streamlit · Human review remains essential")
