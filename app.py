import streamlit as st
import pdfplumber
import re
import pandas as pd
from io import BytesIO
import time

# Configure page settings
st.set_page_config(page_title="Court Doc Analyzer", layout="wide")

# Custom CSS for styling
st.markdown("""
<style>
    .reportview-container { background: #f0f2f6; }
    .sidebar .sidebar-content { background: #ffffff; }
    h2 { color: #2a3f5f; }
    .stProgress > div > div > div { background-color: #2a3f5f; }
</style>
""", unsafe_allow_html=True)


def extract_court_details(text):
    """Extract detailed case information from text"""
    patterns = {
        'case_numbers': [
            r'CASE NO\.?\s*:\s*([^\n]+)',
            r'Civil Appeal No\.?\s*([^\n]+)',
            r'Appeal \(civil\) (\d+ of \d{4})'
        ],
        'petitioners': [
            r'PETITIONER:\s*([^\n]+)',
            r'Appellant:\s*([^\n]+)',
            r'In the matter of:\s*([^\n]+)'
        ],
        'respondents': [
            r'RESPONDENT:\s*([^\n]+)',
            r'Versus\s*([^\n]+)',
            r'v\.\s*([^\n]+)'
        ],
        'dates': [
            r'DATE OF JUDGMENT:\s*([^\n]+)',
            r'Date:\s*(\d{1,2}/\d{1,2}/\d{4})',
            r'Judgment delivered on:\s*([^\n]+)'
        ],
        'background': [
            r'JUDGMENT\n([\s\S]*?)(?=\n\d+\.)',
            r'BACKGROUND:\s*([\s\S]*?)(?=\n[A-Z]{3,}:)',
            r'The facts of the case are as follows:\s*([\s\S]*?)(?=\n\w+ \w+:)'
        ]
    }

    results = {
        'case_numbers': set(),
        'petitioners': set(),
        'respondents': set(),
        'dates': set(),
        'background': ''
    }

    # Extract multi-pattern fields
    for field in ['case_numbers', 'petitioners', 'respondents', 'dates']:
        for pattern in patterns[field]:
            matches = re.findall(pattern, text, re.IGNORECASE)
            if matches:
                results[field].update(m.strip() for m in matches if m.strip())

    # Extract background (take first match)
    for pattern in patterns['background']:
        match = re.search(pattern, text, re.DOTALL | re.IGNORECASE)
        if match:
            results['background'] = ' '.join(match.group(1).split())
            break

    # Convert sets to sorted lists
    for field in ['case_numbers', 'petitioners', 'respondents', 'dates']:
        results[field] = sorted(results[field]) if results[field] else ['Not found']

    return results


def process_pdf(file):
    """Process individual PDF file"""
    with pdfplumber.open(file) as pdf:
        text = "\n".join(page.extract_text() for page in pdf.pages if page.extract_text())
    return extract_court_details(text)


def main():
    st.title("Court Document Processing System")
    st.markdown("---")

    # File upload in sidebar
    with st.sidebar:
        st.header("Upload Documents")
        uploaded_files = st.file_uploader(
            "Select PDF files",
            type="pdf",
            accept_multiple_files=True,
            help="Upload multiple court documents in PDF format"
        )

    if uploaded_files:
        # Initialize session state
        if 'processed_data' not in st.session_state:
            st.session_state.processed_data = []

        # Process files with progress
        progress_bar = st.progress(0)
        status_text = st.empty()

        for i, uploaded_file in enumerate(uploaded_files):
            try:
                # Process PDF
                status_text.info(f"Processing {uploaded_file.name}... ({i + 1}/{len(uploaded_files)})")
                result = process_pdf(uploaded_file)

                # Store results
                st.session_state.processed_data.append({
                    'filename': uploaded_file.name,
                    **result
                })

                # Update progress
                progress_bar.progress((i + 1) / len(uploaded_files))
                time.sleep(0.1)

            except Exception as e:
                st.error(f"Error processing {uploaded_file.name}: {str(e)}")

        status_text.success("Processing completed!")
        progress_bar.empty()

        # Display results
        st.markdown("## Processing Results")
        for idx, data in enumerate(st.session_state.processed_data):
            with st.expander(f"Document {idx + 1}: {data['filename']}", expanded=True):
                col1, col2 = st.columns(2)

                with col1:
                    st.markdown("**Case Details**")
                    st.table({
                        "Field": ["Case Numbers", "Petitioners", "Respondents", "Dates"],
                        "Value": [
                            "\n".join(data['case_numbers']),
                            "\n".join(data['petitioners']),
                            "\n".join(data['respondents']),
                            "\n".join(data['dates'])
                        ]
                    })

                with col2:
                    st.markdown("**Case Background**")
                    st.write(data['background'] if data['background'] else "No background found")

        # Download section
        st.markdown("---")
        st.markdown("### Download Results")
        df = pd.DataFrame(st.session_state.processed_data)

        # Export options
        col1, col2 = st.columns(2)
        with col1:
            csv = df.to_csv(index=False).encode('utf-8')
            st.download_button(
                label="Download CSV",
                data=csv,
                file_name="court_cases.csv",
                mime="text/csv"
            )

        with col2:
            excel_buffer = BytesIO()
            df.to_excel(excel_buffer, index=False)
            st.download_button(
                label="Download Excel",
                data=excel_buffer.getvalue(),
                file_name="court_cases.xlsx",
                mime="application/vnd.ms-excel"
            )


if __name__ == "__main__":
    main()
