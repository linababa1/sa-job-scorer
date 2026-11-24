import io
from pathlib import Path
import pandas as pd
import streamlit as st
from docx import Document
import fitz  # pymupdf

from db import init_db, add_job, list_jobs, update_status, delete_job, wipe_all, STATUSES
from scorer import score_job

DATA = Path("data")
DATA.mkdir(exist_ok=True)
CV_PATH = DATA / "cv.txt"

st.set_page_config(page_title="SA Job Scorer", page_icon="🇿🇦", layout="wide")
init_db()

def extract_text(uploaded) -> str:
    name = uploaded.name.lower()
    data = uploaded.read()
    if name.endswith(".pdf"):
        doc = fitz.open(stream=data, filetype="pdf")
        return "\n".join(p.get_text() for p in doc)
    if name.endswith(".docx"):
        d = Document(io.BytesIO(data))
        return "\n".join(p.text for p in d.paragraphs)
    return data.decode("utf-8", errors="ignore")

# ---------- Sidebar ----------
with st.sidebar:
    st.header("Your CV")
    uploaded = st.file_uploader("Upload CV (PDF / DOCX / TXT)", type=["pdf", "docx", "txt"])
    if uploaded is not None:
        text = extract_text(uploaded)
        if text.strip():
            CV_PATH.write_text(text)
            st.success("CV saved locally.")
        else:
            st.error("Could not extract text from that file.")

    cv_text = CV_PATH.read_text() if CV_PATH.exists() else ""
    if cv_text:
        with st.expander("Preview CV text"):
            st.text(cv_text[:1500] + ("..." if len(cv_text) > 1500 else ""))
    else:
        st.warning("Upload your CV to start scoring.")

    st.divider()
    st.caption("🔒 All data stored locally. Only sent to your configured LLM.")
    if st.button("🗑️ Delete my CV and history", use_container_width=True):
        if CV_PATH.exists():
            CV_PATH.unlink()
        wipe_all()
        st.success("Wiped.")
        st.rerun()

# ---------- Tabs ----------
st.title("🇿🇦 SA Job Scorer")
tab_score, tab_track = st.tabs(["📝 Score a job", "📊 My applications"])

# ===== Tab 1: Score a job =====
with tab_score:
    st.subheader("Paste a job description")
    target_role = st.selectbox(
        "What role are you targeting right now?",
        ["Data Analyst", "Business Analyst", "Data Scientist", "Customer Service", "Marketing", "Other"]
    )
    jd_text = st.text_area("Job description", height=250,
        placeholder="Paste the full JD here (from PNet, Careers24, CareerJunction, LinkedIn, etc.)")
    
    col1, col2 = st.columns([1, 3])
    with col1:
        save_to_tracker = st.checkbox("Save to tracker", value=True)
    with col2:
        run = st.button("🔍 Score this job", type="primary", disabled=not (cv_text and jd_text.strip()))

    if run:
        with st.spinner("Scoring..."):
            try:
                result = score_job(cv_text, jd_text, target_role)
            except Exception as e:
                st.error(f"Scoring failed: {e}")
                st.stop()

            if save_to_tracker:
                job_id = add_job(jd_text, result)
                st.caption(f"Saved to tracker (id {job_id}).")

        # ---------- Result display ----------
        score = result.get("overall_score", 0)
        verdict = result.get("verdict", "—")
        badge = {"Strong match": "🟢", "Worth applying": "🟡", "Borderline": "🟠", "Skip": "🔴"}.get(verdict, "⚪")

        st.markdown(f"### {badge} {score}/100 — {verdict}")
        st.markdown(f"*{result.get('one_line_summary','')}*")
        st.markdown(f"**{result.get('job_title','?')}** at **{result.get('company','?')}**")

        friendly = result.get("entry_level_friendly")
        years = result.get("years_required") or "not stated"
        if friendly is True:
            st.success(f"✅ **Entry-level friendly.** Experience required: {years}")
        elif friendly is False:
            st.error(f"🚩 **Not entry-level.** Experience required: {years} — likely a waste of time.")
        else:
            st.warning(f"⚠️ **Entry-level status unclear.** Experience required: {years}")

        c1, c2, c3, c4 = st.columns(4)
        dims = result.get("dimensions", {})
        c1.metric("Title fit", dims.get("title_alignment", "—"))
        c2.metric("Experience", dims.get("experience_relevance", "—"))
        c3.metric("Seniority", dims.get("seniority_fit", "—"))
        c4.metric("Skills", dims.get("skills_coverage", "—"))

        if result.get("seniority_note"):
            st.info(f"**Seniority:** {result['seniority_note']}")

        ca, cb = st.columns(2)
        with ca:
            st.markdown("#### ✅ Strengths")
            for s in result.get("top_strengths", []):
                st.markdown(f"- {s}")
        with cb:
            st.markdown("#### ⚠️ Gaps")
            for g in result.get("top_gaps", []):
                st.markdown(f"- {g}")

        with st.expander("Met vs missing requirements"):
            cc, cd = st.columns(2)
            with cc:
                st.markdown("**Met**")
                for r in result.get("requirements_met", []):
                    st.markdown(f"- {r}")
            with cd:
                st.markdown("**Missing**")
                for r in result.get("requirements_missing", []):
                    st.markdown(f"- {r}")

# ===== Tab 2: Applications tracker =====
with tab_track:
    st.subheader("Your scored jobs")
    jobs = list_jobs()
    if not jobs:
        st.info("Nothing here yet. Score a job to populate the tracker.")
    else:
        df = pd.DataFrame(jobs)
        df["score"] = df["overall_score"]
        df["entry"] = df["entry_level_friendly"].map({1: "✅", 0: "🚩"})
        df["created"] = pd.to_datetime(df["created_at"]).dt.strftime("%Y-%m-%d")

        fc1, fc2, fc3 = st.columns(3)
        with fc1:
            status_filter = st.multiselect("Status", STATUSES, default=STATUSES)
        with fc2:
            min_score = st.slider("Minimum score", 0, 100, 0)
        with fc3:
            only_entry = st.checkbox("Entry-level friendly only", value=False)

        view = df[df["status"].isin(status_filter) & (df["score"] >= min_score)].copy()
        if only_entry:
            view = view[view["entry_level_friendly"] == 1]
        view = view.sort_values("created_at", ascending=False)

        st.dataframe(
            view[["id", "created", "job_title", "company", "score", "verdict", "entry", "years_required", "status"]],
            use_container_width=True, hide_index=True
        )

        st.divider()
        st.markdown("### Update a job")
        if not view.empty:
            chosen_id = st.selectbox(
                "Job", view["id"].tolist(),
                format_func=lambda i: f"#{i} — {view.loc[view['id']==i,'job_title'].iloc[0]} ({view.loc[view['id']==i,'score'].iloc[0]}/100)"
            )
            row = view[view["id"] == chosen_id].iloc[0]

            u1, u2 = st.columns(2)
            with u1:
                new_status = st.selectbox("Status", STATUSES, index=STATUSES.index(row["status"]))
            with u2:
                new_notes = st.text_area("Notes", value=row.get("notes") or "", height=100)

            b1, b2 = st.columns(2)
            with b1:
                if st.button("💾 Save changes", type="primary", use_container_width=True):
                    update_status(int(chosen_id), new_status, new_notes)
                    st.success("Saved.")
                    st.rerun()
            with b2:
                if st.button("🗑️ Delete this job", use_container_width=True):
                    delete_job(int(chosen_id))
                    st.rerun()

            with st.expander("Original JD"):
                st.text(row["jd_text"][:5000])