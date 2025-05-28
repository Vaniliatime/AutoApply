import streamlit as st
from openai import OpenAI
from io import BytesIO
from reportlab.pdfgen import canvas
from PyPDF2 import PdfReader, PdfWriter
import textwrap
import csv
from datetime import datetime
import os
import pandas as pd
import time
import io
from st_aggrid import AgGrid, GridOptionsBuilder, GridUpdateMode, JsCode
from dotenv import load_dotenv
load_dotenv()
import os


st.set_page_config(
    page_title="AutoApply", 
    layout="wide",
    page_icon="💼",
)

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# ---------- UTILITIES ----------

def load_profile():
    try:
        with open("profile.txt", "r", encoding="utf-8") as f:
            return f.read().strip()
    except FileNotFoundError:
        return ""

def build_prompt(description, company=None, position=None):
    profile = load_profile()
    intro = "Write a formal, concise English cover letter (~300–350 words), starting with 'Dear Hiring Manager'. "
    intro += "Do not include personal data (name, address, contact info, or date). "
    intro += "Do not include any closing phrases like 'Sincerely' or your name – the signature is already embedded in the PDF template. "
    intro += "Do not invent or assume any certifications or qualifications the candidate does not explicitly possess. "
    intro += "If a required certification (e.g. ITIL) is not listed, do NOT claim it. "
    intro += "Focus on support-related experience, bug reproduction, user assistance, ticketing, documentation, and teamwork. "
    intro += "Tailor it to the job description below.\n\n"
    if profile:
        intro += (
            "Below is a summary of the candidate’s background, skills and experience. "
            "Use it to inform the content of the letter, but do not copy or repeat it directly. "
            "Instead, synthesize and paraphrase it naturally into the context of the job description.\n\n"
            f"{profile}\n\n"
        )
    base = intro
    if company and position:
        base += f"You are applying for the position of '{position}' at '{company}'.\n\n"
    elif position:
        base += f"You are applying for the position of '{position}'.\n\n"
    base += (
        "Write a formal, concise cover letter (~300–350 words) tailored to the job description below. "
        "Highlight support-related experience, bug reproduction, user assistance, ticketing, documentation, and teamwork.\n\n"
        f"Job Description:\n{description.strip()}"
    )
    return base

def generate_letter(prompt, model_name):
    response = client.chat.completions.create(
        model=model_name,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.7,
    )
    tokens = response.usage.total_tokens
    content = response.choices[0].message.content.strip()
    return content, tokens

def remove_signature_block(text: str) -> str:
    lines = [line.strip() for line in text.strip().split("\n") if line.strip()]
    signature_triggers = ["sincerely", "kind regards", "best regards", "warm regards", "yours faithfully", "regards", "best", "thank you", "with gratitude"]
    for i in range(len(lines)-1, max(0, len(lines)-4), -1):
        if any(trigger in lines[i].lower() for trigger in signature_triggers):
            return "\n".join(lines[:i]).strip()
    return "\n".join(lines)

def estimate_cost(tokens, model):
    if model == "gpt-3.5-turbo":
        return round(tokens * 0.0015 / 1000, 4)
    elif model == "gpt-4":
        prompt_tokens = tokens * 0.4
        completion_tokens = tokens * 0.6
        cost = (prompt_tokens * 0.03 + completion_tokens * 0.06) / 1000
        return round(cost, 4)
    return 0.0

def wrap_text(text, width=90):
    wrapped_lines = []
    for paragraph in text.split("\n"):
        wrapped_lines.extend(textwrap.wrap(paragraph, width=width))
        wrapped_lines.append("")
    return wrapped_lines

def create_overlay_wrapped(text):
    text = text.strip()
    wrapped_lines = wrap_text(text, width=90)
    packet = BytesIO()
    can = canvas.Canvas(packet, pagesize=(595.27, 841.89))
    x, y = 60, 640
    for line in wrapped_lines:
        can.drawString(x, y, line)
        y -= 14
        if y < 100:
            break
    can.save()
    packet.seek(0)
    return packet

def merge_with_template(overlay_stream, template_path, file_name):
    template = PdfReader(template_path)
    overlay = PdfReader(overlay_stream)
    output = PdfWriter()
    base_page = template.pages[0]
    base_page.merge_page(overlay.pages[0])
    output.add_page(base_page)
    final_output = BytesIO()
    output.write(final_output)
    final_output.seek(0)
    os.makedirs("cover-letters", exist_ok=True)
    base_path = os.path.join("cover-letters", file_name)
    counter = 1
    final_path = base_path
    while os.path.exists(final_path):
        name, ext = os.path.splitext(base_path)
        final_path = f"{name}_{counter}{ext}"
        counter += 1
    with open(final_path, "wb") as f:
        f.write(final_output.getbuffer())
    return final_output, final_path

def save_to_applications(title, company, location, work_type, url, source, status, notes):
    filename = "applications_history.csv"
    now = datetime.now().strftime("%Y-%m-%d")
    row = {
        "title": title,
        "company": company,
        "location": location,
        "work_type": work_type,
        "url": url,
        "date_applied": now,
        "source": source,
        "status": status,
        "notes": notes
    }
    columns = list(row.keys())
    if os.path.exists(filename):
        df = pd.read_csv(filename)
    else:
        df = pd.DataFrame(columns=columns)
    df = pd.concat([df, pd.DataFrame([row])], ignore_index=True)
    df.to_csv(filename, index=False)

# ---------- UI TABS ----------

tab2, tab3, tab1 = st.tabs(["➕ Manualy Add Entry", "📚 History + Edit", "📄 Cover Letter Generator"])

with tab1:
    st.subheader("Generate Cover Letter (PDF)")

    # --- CZYSZCZENIE FORMULARZA PRZED RENDEREM ---
    if st.session_state.get("clear_cl_form", False):
        st.session_state["cl_company"] = ""
        st.session_state["cl_location"] = ""
        st.session_state["cl_source_choice"] = "LinkedIn"
        st.session_state["cl_custom_source"] = ""
        st.session_state["cl_position"] = ""
        st.session_state["cl_url"] = ""
        st.session_state["cl_work_type"] = "remote"
        st.session_state["cl_status"] = "applied"
        st.session_state["cl_notes"] = ""
        st.session_state["cl_description"] = ""
        st.session_state["cl_model_choice"] = "gpt-4"
        st.session_state["clear_cl_form"] = False
        st.rerun()

    # --- Ustaw domyślne wartości przy starcie ---
    for k, v in {
        "cl_company": "",
        "cl_location": "",
        "cl_source_choice": "LinkedIn",
        "cl_custom_source": "",
        "cl_position": "",
        "cl_url": "",
        "cl_work_type": "remote",
        "cl_status": "applied",
        "cl_notes": "",
        "cl_description": "",
        "cl_model_choice": "gpt-4"
    }.items():
        if k not in st.session_state:
            st.session_state[k] = v

    with st.form("cover_letter_form"):
        model_choice = st.selectbox("Model", ["gpt-4", "gpt-3.5-turbo"], key="cl_model_choice")

        col1, col2 = st.columns(2)
        with col1:
            company = st.text_input("Company name", key="cl_company")
            location = st.text_input("Location (optional)", key="cl_location")
            source_options = ["LinkedIn", "JustJoinIT", "NoFluffJobs", "Pracuj.pl", "RemoteOK", "SimplyHired", "Other"]
            source_choice = st.selectbox("Source", source_options, key="cl_source_choice")
            custom_source = st.text_input("If Other, type your source", key="cl_custom_source") if source_choice == "Other" else ""
        with col2:
            position = st.text_input("Job title", key="cl_position")
            url = st.text_input("Job URL (optional)", key="cl_url")
            work_type = st.selectbox("Work type", ["remote", "hybrid", "onsite"], key="cl_work_type")
        source = custom_source if source_choice == "Other" else source_choice

        status = st.selectbox("Status", ["applied", "saved", "rejected", "declined by me"], index=["applied", "saved", "rejected", "declined by me"].index(st.session_state["cl_status"]), key="cl_status")
        notes = st.text_area("Notes (optional)", key="cl_notes")
        description = st.text_area("Paste the job description here", height=250, key="cl_description")

        col_save, col_clear = st.columns([1, 15])
        with col_save:
            submitted = st.form_submit_button("Generate PDF")
        with col_clear:
            clear = st.form_submit_button("🧹 Clear form")

    # --- Po kliknięciu czyść: ustaw flagę! ---
    if clear:
        st.session_state["clear_cl_form"] = True
        st.rerun()

    if submitted and description.strip():
        prompt = build_prompt(description, company, position)
        with st.spinner("Generating letter..."):
            letter, token_count = generate_letter(prompt, model_choice)
            letter = remove_signature_block(letter)
            cost = estimate_cost(token_count, model_choice)

        filename = f"Cover_Letter_{company or 'Unknown'}.pdf"
        overlay = create_overlay_wrapped(letter)
        pdf_bytes, final_path = merge_with_template(overlay, "template.pdf", filename)

        st.success("✅ Letter generated!")
        st.code(letter, language="markdown")
        st.download_button("📥 Download PDF", pdf_bytes, file_name=filename, mime="application/pdf")

        save_to_applications(position, company, location, work_type, url, source, status, f"PDF: {filename}")


with tab2:
    st.subheader("Manual Entry")

    source_options = [
        "LinkedIn", "JustJoinIT", "NoFluffJobs", "Pracuj.pl", "RemoteOK", "SimplyHired", "Other"
    ]

    # Czyszczenie pól jeśli była flaga (to się dzieje PRZED renderem formularza)
    if st.session_state.get("clear_manual_form", False):
        st.session_state["manual_title"] = ""
        st.session_state["manual_company"] = ""
        st.session_state["manual_location"] = ""
        st.session_state["manual_work"] = "remote"
        st.session_state["manual_url"] = ""
        st.session_state["manual_source_select"] = source_options[0]
        st.session_state["manual_source_custom"] = ""
        st.session_state["manual_status"] = "applied"
        st.session_state["manual_notes"] = ""
        st.session_state["clear_manual_form"] = False

    with st.form(key="manual_add_form", clear_on_submit=False):
        col1, col2 = st.columns(2)
        with col1:
            title = st.text_input("Job Title", key="manual_title")
            company = st.text_input("Company", key="manual_company")
            location = st.text_input("Location", key="manual_location")
        with col2:
            work_type = st.selectbox("Work Type", ["remote", "hybrid", "onsite"], key="manual_work")
            url = st.text_input("Job URL", key="manual_url")
            source_select = st.selectbox("Source", source_options, key="manual_source_select")
            source_custom = ""
            if source_select == "Other":
                source_custom = st.text_input("Enter custom source", key="manual_source_custom")
        status = st.selectbox("Application Status", ["applied", "saved", "rejected", "declined by me"], key="manual_status")
        notes = st.text_area("Notes", key="manual_notes")

        # Przyciski obok siebie – proporcje 1:1:4, więc są razem, reszta odstęp
        col_save, col_clean, col_spacer = st.columns([1, 1, 20])
        with col_save:
            submitted_manual = st.form_submit_button("💾 Save")
        with col_clean:
            clear_pressed = st.form_submit_button("🧹 Clean")

        # Obsługa czyszczenia oraz zapisu
        if clear_pressed:
            st.session_state["clear_manual_form"] = True
            st.rerun()

        if submitted_manual:
            source = source_custom if source_select == "Other" else source_select
            save_to_applications(
                title, company, location, work_type, url, source, status, notes
            )
            st.success("Application saved to history.")
            st.session_state["clear_manual_form"] = True
            st.rerun()

with tab3:
    st.subheader("📚 Full Application History")
    history_file = "applications_history.csv"
    columns = ["title", "company", "location", "work_type", "url", "date_applied", "source", "status", "notes"]
    sources_default = ["LinkedIn", "JustJoinIT", "Pracuj.pl", "NoFluffJobs", "RemoteOK", "Remotive", "Referral", "Other"]

    if os.path.exists(history_file):
        df = pd.read_csv(history_file)
    else:
        df = pd.DataFrame(columns=columns)

    # --- AUTOMATYCZNY UPDATE STATUSU NA "no response" PO 30 DNIACH ---
    if not df.empty:
        now = datetime.now()
        changed = False
        for idx, row in df.iterrows():
            try:
                date_applied = datetime.strptime(str(row["date_applied"]), "%Y-%m-%d")
                # Aktualizuj tylko, jeśli status to "applied" lub "saved"
                if row["status"] in ["applied", "saved"]:
                    if now - date_applied > timedelta(days=30):
                        df.at[idx, "status"] = "no response"
                        changed = True
            except Exception:
                pass
        if changed:
            df.to_csv(history_file, index=False)


        # SEARCH nad tabelą
    search_query = st.text_input("🔎 Search by any field", "")

    def filter_df(df, query):
        if not query:
            return df
        query = query.lower()
        mask = (
            df["title"].astype(str).str.lower().str.contains(query, na=False) |
            df["company"].astype(str).str.lower().str.contains(query, na=False) |
            df["location"].astype(str).str.lower().str.contains(query, na=False) |
            df["notes"].astype(str).str.lower().str.contains(query, na=False) |
            df["source"].astype(str).str.lower().str.contains(query, na=False) |
            df["work_type"].astype(str).str.lower().str.contains(query, na=False) |
            df["url"].astype(str).str.lower().str.contains(query, na=False) |
            df["date_applied"].astype(str).str.lower().str.contains(query, na=False) |
            df["status"].astype(str).str.lower().str.contains(query, na=False)
        )
        return df[mask]

    if not df.empty:
        df_display = df.copy()
        df_display.insert(0, 'ID', df_display.index)
        # USUŃ url z widoku tabeli!
        aggrid_cols = ["ID", "title", "company", "location", "work_type", "date_applied", "source", "status", "notes"]
        df_filtered = filter_df(df_display, search_query)

        # --- AgGrid TABLE without URL + kolorowanie statusu ---
        st.markdown("### Click on a row to edit")
        # JS do kolorowania statusów, dodano 'no response'
        status_color_js = JsCode("""
            function(params) {
                if (params.value == 'applied') {
                    return {'color': 'white', 'color': '#28a745', 'fontWeight': 'bold'};
                }
                if (params.value == 'rejected') {
                    return {'color': 'white', 'color': '#dc3545', 'fontWeight': 'bold'};
                }
                if (params.value == 'interview') {
                    return {'color': 'black', 'color': '#FFFF00', 'fontWeight': 'bold'};
                }
                if (params.value == 'declined by me') {
                    return {'color': 'white', 'color': '#007bff', 'fontWeight': 'bold'};
                }
                if (params.value == 'no response') {
                    return {'color': 'white', 'color': '#FFA500', 'fontWeight': 'bold'};
                }
                return {};
            }
        """)
        
        gb = GridOptionsBuilder.from_dataframe(df_filtered[aggrid_cols])
        gb.configure_default_column(groupable=False, editable=False)
        gb.configure_column("ID", header_name="ID", pinned="left")
        gb.configure_column(
            "status",
            header_name="Status",
            cellStyle=status_color_js,
        )
        gb.configure_selection(selection_mode="single", use_checkbox=False)
        grid_options = gb.build()

        grid_response = AgGrid(
            df_filtered[aggrid_cols],
            gridOptions=grid_options,
            update_mode=GridUpdateMode.MODEL_CHANGED,
            allow_unsafe_jscode=True,
            theme="streamlit",
            height=800,
        )

        selected_idx = None
        row = None

        selected_rows = grid_response["selected_rows"]
        if isinstance(selected_rows, pd.DataFrame) and not selected_rows.empty:
            row = selected_rows.iloc[0].to_dict()
        elif isinstance(selected_rows, list) and len(selected_rows) > 0:
            row = selected_rows[0]

        if row is not None and "ID" in row and row["ID"] is not None:
            try:
                selected_idx = int(float(row["ID"]))
            except Exception:
                selected_idx = None

        # --- Export to Excel pod tabelą ---
        excel_buffer = io.BytesIO()
        df_filtered[["ID"] + columns].to_excel(excel_buffer, index=False, engine="openpyxl")
        excel_buffer.seek(0)
        st.download_button(
            label="⬇️ Export to Excel",
            data=excel_buffer,
            file_name="applications_export.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

        # --- Kopiuj URL BUTTON pod tabelą, po wybraniu rekordu ---
        if selected_idx is not None and selected_idx in df_filtered.index:
            record_url = df_filtered.loc[selected_idx, "url"]
            st.markdown("#### Copy URL:")
            st.code(record_url, language=None)

        # --- FORMULARZ EDYCJI ---
        df_filtered_int_id = df_filtered.copy()
        df_filtered_int_id["ID_INT"] = df_filtered_int_id["ID"].apply(lambda x: int(float(x)) if pd.notnull(x) else -9999)

        if selected_idx is not None and selected_idx in df_filtered_int_id["ID_INT"].values:
            record = df_filtered_int_id[df_filtered_int_id["ID_INT"] == selected_idx].iloc[0]
            with st.form(f"edit_any_record_form_{selected_idx}", clear_on_submit=True):
                st.markdown(f"**Editing record ID {selected_idx}**")
                col1, col2 = st.columns(2)
                with col1:
                    new_title = st.text_input("Position", value=record["title"], key=f"edit_title_{selected_idx}")
                    new_company = st.text_input("Company Name", value=record["company"], key=f"edit_company_{selected_idx}")
                    new_location = st.text_input("Location", value=record["location"], key=f"edit_location_{selected_idx}")
                    new_work_type = st.selectbox(
                        "Work Mode", ["remote", "hybrid", "onsite", "other"],
                        index=["remote", "hybrid", "onsite", "other"].index(str(record["work_type"])),
                        key=f"edit_worktype_{selected_idx}"
                    )
                with col2:
                    new_url = st.text_input("URL", value=record["url"], key=f"edit_url_{selected_idx}")
                    new_source_choice = st.selectbox(
                        "Source", sources_default,
                        index=sources_default.index(str(record["source"])) if record["source"] in sources_default else len(sources_default)-1,
                        key=f"edit_source_{selected_idx}"
                    )
                    new_source = new_source_choice if new_source_choice != "Other" else st.text_input(
                        "Custom source", value=record["source"], key=f"edit_other_source_{selected_idx}"
                    )
                    new_status = st.selectbox(
                        "Status", ["applied", "interview", "offer", "rejected", "declined by me", "no response"],
                        index=["applied", "interview", "offer", "rejected", "declined by me", "no response"].index(str(record["status"])),
                        key=f"edit_status_{selected_idx}"
                    )
                    new_notes = st.text_area(
                        "Notes", value=record["notes"] if pd.notnull(record["notes"]) else "", key=f"edit_notes_{selected_idx}"
                    )
                new_date_applied = st.text_input("Date applied (YYYY-MM-DD)", value=record["date_applied"], key=f"edit_date_{selected_idx}")

                col_save, col_delete = st.columns([1, 1])
                with col_save:
                    submitted = st.form_submit_button("💾 Save changes")
                with col_delete:
                    delete_requested = st.form_submit_button("🗑 Delete record")

                if delete_requested:
                    df.drop(index=selected_idx, inplace=True)
                    df.to_csv(history_file, index=False)
                    st.success(f"Record ID {selected_idx} deleted!")
                    st.rerun()

                if submitted:
                    df.at[selected_idx, "title"] = new_title
                    df.at[selected_idx, "company"] = new_company
                    df.at[selected_idx, "location"] = new_location
                    df.at[selected_idx, "work_type"] = new_work_type
                    df.at[selected_idx, "url"] = new_url
                    df.at[selected_idx, "source"] = new_source
                    df.at[selected_idx, "status"] = new_status
                    df.at[selected_idx, "notes"] = new_notes
                    df.at[selected_idx, "date_applied"] = new_date_applied
                    df.to_csv(history_file, index=False)
                    st.success(f"Record ID {selected_idx} updated!")
                    st.rerun()
        else:
            st.info("Click on a row to edit.")
    else:
        st.info("No applications to display.")