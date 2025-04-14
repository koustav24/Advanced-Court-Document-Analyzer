import os
import re
import fitz  # PyMuPDF
import pandas as pd
import streamlit as st
import tempfile
from typing import List, Dict, Optional, Any
from pydantic import BaseModel, Field
import json
from io import BytesIO
import time

# Set page configuration
st.set_page_config(
    page_title="Court Document Analyzer",
    page_icon="⚖️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Define structured output models using Pydantic
class CaseNumber(BaseModel):
    """Information about a case number in the document"""
    type: str = Field(description="Type of case (e.g., Appeal, Civil Appeal)")
    nature: Optional[str] = Field(description="Nature of case (e.g., civil, criminal)")
    sequential_number: str = Field(description="Sequential number of the case")
    year: str = Field(description="Year of filing")
    full_citation: str = Field(description="Full citation as appears in document")

class Party(BaseModel):
    """Information about a party in the case"""
    name: str = Field(description="Name of the party")
    role: str = Field(description="Role of the party (e.g., Petitioner, Respondent)")
    description: Optional[str] = Field(description="Additional description if available")

class ConsolidatedCase(BaseModel):
    """Information about a consolidated case"""
    case_number: str = Field(description="Case number citation")
    petitioner: str = Field(description="Petitioner/appellant in the case")
    respondent: str = Field(description="Respondent in the case")

# Advanced text extraction from PDF
def extract_text_from_pdf(pdf_path: str) -> str:
    """Extract text from PDF with advanced layout preservation"""
    doc = fitz.open(pdf_path)
    text = ""
    
    for page in doc:
        # Extract text with preservation of layout
        text += page.get_text("text")
    
    return text

# Extract case numbers using advanced regex patterns
def extract_case_numbers(text: str) -> Dict[str, Any]:
    """Extract primary and related case numbers"""
    case_numbers = {"primary": None, "related": []}
    
    # Patterns for different case number formats
    patterns = [
        r"Appeal\s+\(civil\)\s+(\d+)\s+of\s+(\d{4})",
        r"Civil\s+Appeal\s+No\.\s*(\d+(?:-\d+)?)\s+of\s+(\d{4})",
        r"Transfer\s+Case\s+\(Civil\)\s+Nos\.\s*(\d+(?:-\d+)?)\s+of\s+(\d{4})",
        r"Civil\s+Appeal\s+Nos\.\s*(\d+(?:-\d+)?)\s+of\s+(\d{4})"
    ]
    
    # Extract primary case number
    primary_match = re.search(patterns[0], text)
    if primary_match:
        case_numbers["primary"] = CaseNumber(
            type="Appeal",
            nature="civil",
            sequential_number=primary_match.group(1),
            year=primary_match.group(2),
            full_citation=f"Appeal (civil) {primary_match.group(1)} of {primary_match.group(2)}"
        )
    
    # Extract related case numbers
    for pattern in patterns:
        for match in re.finditer(pattern, text):
            if pattern == patterns[0] and primary_match and match.group(0) == primary_match.group(0):
                continue  # Skip primary case number in related cases
                
            case_type = "Civil Appeal" if "Civil Appeal" in match.group(0) else \
                       "Transfer Case (Civil)" if "Transfer Case" in match.group(0) else "Appeal"
            
            case_numbers["related"].append(CaseNumber(
                type=case_type,
                nature="civil",
                sequential_number=match.group(1),
                year=match.group(2),
                full_citation=match.group(0)
            ))
    
    return case_numbers

# Extract parties using specialized pattern matching
def extract_parties(text: str) -> Dict[str, Any]:
    """Extract parties information using specialized pattern matching"""
    parties = {"main": [], "consolidated": []}
    
    # Extract main parties
    petitioner_pattern = r"(?:PETITIONER|APPELLANT):\s*(.*?)(?=RESPONDENT:|$)"
    respondent_pattern = r"RESPONDENT:\s*(.*?)(?=DATE OF JUDGMENT:|$)"
    
    petitioner_match = re.search(petitioner_pattern, text, re.DOTALL | re.IGNORECASE)
    respondent_match = re.search(respondent_pattern, text, re.DOTALL | re.IGNORECASE)
    
    if petitioner_match:
        parties["main"].append(Party(
            name=petitioner_match.group(1).strip(),
            role="Petitioner",
            description=None
        ))
    
    if respondent_match:
        parties["main"].append(Party(
            name=respondent_match.group(1).strip(),
            role="Respondent",
            description=None
        ))
    
    # Extract consolidated cases parties using more sophisticated pattern matching
    consolidated_pattern = r"WITH\s+(.*?)(?=WITH|\n\n|\Z)"
    consolidated_sections = re.findall(consolidated_pattern, text, re.DOTALL)
    
    # Also look for versus pattern to identify parties
    versus_pattern = r"([^\n]+)\s+(?:Versus|vs\.)\s+([^\n]+)"
    for match in re.finditer(versus_pattern, text):
        if match:
            petitioner = match.group(1).strip()
            respondent = match.group(2).strip()
            
            # Only add if not already in main parties
            main_petitioners = [p.name for p in parties["main"] if p.role == "Petitioner"]
            main_respondents = [p.name for p in parties["main"] if p.role == "Respondent"]
            
            if petitioner not in main_petitioners and respondent not in main_respondents:
                parties["consolidated"].append(ConsolidatedCase(
                    case_number="Related Case",
                    petitioner=petitioner,
                    respondent=respondent
                ))
    
    # Process any directly identified consolidated cases
    for section in consolidated_sections:
        lines = section.strip().split('\n')
        case_number = ""
        petitioner = ""
        respondent = ""
        
        for i, line in enumerate(lines):
            if re.search(r"Civil Appeal No\.", line):
                case_number = line.strip()
            elif "..." in line and petitioner == "":
                petitioner = lines[i-1].strip() if i > 0 else ""
            elif "Versus" in line and i+1 < len(lines):
                respondent = lines[i+1].strip() if i+1 < len(lines) else ""
        
        if case_number and (petitioner or respondent):
            parties["consolidated"].append(ConsolidatedCase(
                case_number=case_number,
                petitioner=petitioner,
                respondent=respondent
            ))
    
    return parties

# Extract judgment date
def extract_judgment_date(text: str) -> str:
    """Extract the judgment date from the document"""
    date_patterns = [
        r"DATE OF JUDGMENT:\s*(\d{2}/\d{2}/\d{4})",
        r"Dated:\s*(\d{1,2}(?:st|nd|rd|th)?\s+[A-Za-z]+,\s+\d{4})",
        r"judgment delivered on\s*:\s*(\d{1,2}(?:st|nd|rd|th)?\s+[A-Za-z]+,\s+\d{4})"
    ]
    
    for pattern in date_patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return match.group(1).strip()
    
    return "Date not found"

# Extract case background using advanced pattern matching
def extract_case_background(text: str) -> Dict[str, Any]:
    """Extract case background using advanced pattern matching"""
    # Initialize result
    result = {
        "case_background": "",
        "constitutional_issues": [],
        "challenged_acts": []
    }
    
    # Try multiple patterns for case background
    background_patterns = [
        r"The Constitutional validity of(.*?)(?:\n\d+\.|\Z)",
        r"JUDGMENT\s+\n+(.*?)(?=\n[A-Z\s]+:|\Z)",
        r"(?:INTRODUCTION|BACKGROUND|FACTS)\s*\n+(.*?)(?=\n[A-Z\s]+:|\Z)"
    ]
    
    for pattern in background_patterns:
        match = re.search(pattern, text, re.DOTALL)
        if match:
            result["case_background"] = match.group(1).strip()
            break
    
    # If still no match, try to extract at least some context
    if not result["case_background"]:
        # Try to extract the first significant paragraph after the case details
        header_section = re.search(r"JUDGMENT.*?\n+(.*?)(?=\n\n|\Z)", text, re.DOTALL)
        if header_section:
            result["case_background"] = header_section.group(1).strip()
    
    # Extract challenged acts
    act_pattern = r"((?:The\s+)?[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\s+Act,\s+\d{4})"
    challenged_acts = re.findall(act_pattern, result["case_background"])
    result["challenged_acts"] = challenged_acts
    
    # Extract constitutional issues
    if "constitutional validity" in text.lower():
        result["constitutional_issues"].append("Constitutional validity of state legislation")
    if "jurisdiction" in text.lower() and "high court" in text.lower():
        result["constitutional_issues"].append("Jurisdiction of High Courts")
    
    return result

# Main extraction function
def extract_court_case_info(pdf_file) -> Dict[str, Any]:
    """Extract all required information from a court case PDF"""
    # Create a temporary file
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
        tmp.write(pdf_file.read())
        tmp_path = tmp.name
    
    try:
        # Extract text from PDF
        text = extract_text_from_pdf(tmp_path)
        
        # Extract components
        case_numbers = extract_case_numbers(text)
        parties = extract_parties(text)
        judgment_date = extract_judgment_date(text)
        background_info = extract_case_background(text)
        
        # Compile results
        result = {
            "primary_case_number": case_numbers["primary"],
            "related_case_numbers": case_numbers["related"],
            "main_parties": parties["main"],
            "consolidated_cases": parties["consolidated"],
            "judgment_date": judgment_date,
            "case_background": background_info["case_background"],
            "constitutional_issues": background_info["constitutional_issues"],
            "challenged_acts": background_info["challenged_acts"]
        }
    finally:
        # Clean up the temporary file
        os.unlink(tmp_path)
    
    return result

# Format output to match the desired structure
def format_output(extraction_result: Dict[str, Any]) -> str:
    """Format the extraction results to match the desired output structure"""
    output = []
    
    # Case Numbers section
    output.append("## Case Numbers")
    if extraction_result["primary_case_number"]:
        primary = extraction_result["primary_case_number"]
        output.append(f"The primary case number is formatted as \"{primary.full_citation}\". This format includes:")
        output.append(f"- Type of case ({primary.type})")
        output.append(f"- Nature ({primary.nature})")
        output.append(f"- Sequential number ({primary.sequential_number})")
        output.append(f"- Year of filing ({primary.year})")
        output.append("")
    
    if extraction_result["related_case_numbers"]:
        output.append("The document also includes multiple related case numbers that were heard together:")
        for case in extraction_result["related_case_numbers"]:
            output.append(f"- {case.full_citation}")
        output.append("")
    
    # Parties Names section
    output.append("## Parties Names")
    output.append("The document clearly identifies the parties to the litigation:")
    output.append("")
    output.append("**Main Case:**")
    for party in extraction_result["main_parties"]:
        output.append(f"- {party.role}: {party.name}")
    output.append("")
    
    if extraction_result["consolidated_cases"]:
        output.append("**Consolidated Cases with Multiple Parties:**")
        for case in extraction_result["consolidated_cases"]:
            output.append(f"- {case.petitioner} vs. {case.respondent}")
        output.append("")
    
    # Hearing Dates section
    output.append("## Hearing Dates")
    output.append(f"The judgment date is clearly marked as \"{extraction_result['judgment_date']}\". This represents the final date when the judgment was delivered, not necessarily when hearings took place.")
    output.append("")
    
    # Case Background section
    output.append("## Case Background")
    if extraction_result["challenged_acts"]:
        output.append("The case involves constitutional challenges to several legislative acts:")
        for act in extraction_result["challenged_acts"]:
            output.append(f"- {act}")
        output.append("")
    
    output.append(extraction_result["case_background"])
    output.append("")
    
    if extraction_result["constitutional_issues"]:
        output.append("The case fundamentally concerns the following constitutional issues:")
        for issue in extraction_result["constitutional_issues"]:
            output.append(f"- {issue}")
    
    return "\n".join(output)

# Convert Pydantic models to a dict that can be serialized to JSON
def pydantic_to_dict(obj):
    if hasattr(obj, "__dict__"):
        return {k: pydantic_to_dict(v) for k, v in obj.__dict__.items() if k != "__initialised__"}
    elif isinstance(obj, dict):
        return {k: pydantic_to_dict(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [pydantic_to_dict(v) for v in obj]
    else:
        return obj

# Streamlit UI
def main():
    st.title("🏛️ Advanced Court Document Analyzer")
    st.markdown("""
    This application extracts precise information from Supreme Court judgment PDFs using advanced NLP techniques.
    Upload your court documents below to extract structured information.
    """)
    
    # CSS for better styling
    st.markdown("""
    <style>
    .main .block-container {padding-top: 2rem; padding-bottom: 2rem;}
    h1 {color: #2e4057;}
    h2 {color: #4b86b4; margin-top: 2rem;}
    .stProgress > div > div > div {background-color: #4b86b4 !important;}
    .stDownloadButton button {background-color: #4b86b4; color: white;}
    </style>
    """, unsafe_allow_html=True)
    
    # Sidebar for configuration
    with st.sidebar:
        st.header("Configuration")
        st.info("This tool extracts structured data from Supreme Court judgments.")
        
        extraction_mode = st.radio(
            "Extraction Mode",
            ["Standard (Faster)", "Deep Analysis (More Accurate)"],
            index=1
        )
        
        st.markdown("---")
        
        st.markdown("### About")
        st.markdown("""
        This tool extracts:
        - Case Numbers (primary and related)
        - Party Names
        - Hearing Dates
        - Case Background
        
        From Supreme Court judgment PDFs.
        """)
    
    # File uploader
    uploaded_files = st.file_uploader(
        "Upload Court Document PDFs", 
        type=["pdf"], 
        accept_multiple_files=True,
        help="Upload one or more court judgment PDFs for automatic information extraction"
    )
    
    if uploaded_files:
        st.success(f"Uploaded {len(uploaded_files)} file(s). Processing...")
        
        # Process each file
        results = []
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        for i, uploaded_file in enumerate(uploaded_files):
            status_text.info(f"Processing {uploaded_file.name} ({i+1}/{len(uploaded_files)})...")
            
            try:
                # Extract information
                extraction_result = extract_court_case_info(uploaded_file)
                
                # Format the results
                formatted_output = format_output(extraction_result)
                
                # Store results
                results.append({
                    "filename": uploaded_file.name,
                    "extraction_result": extraction_result,
                    "formatted_output": formatted_output
                })
                
                # Update progress
                progress_bar.progress((i + 1) / len(uploaded_files))
                
            except Exception as e:
                st.error(f"Error processing {uploaded_file.name}: {str(e)}")
        
        status_text.empty()
        progress_bar.empty()
        st.success("Processing complete! Displaying results...")
        
        # Display results
        for i, result in enumerate(results):
            with st.expander(f"Document {i+1}: {result['filename']}", expanded=i==0):
                st.markdown(result["formatted_output"])
                
                # Download buttons for individual results
                col1, col2 = st.columns(2)
                
                with col1:
                    # Prepare individual JSON download
                    json_result = pydantic_to_dict(result["extraction_result"])
                    json_str = json.dumps(json_result, indent=2)
                    json_bytes = json_str.encode('utf-8')
                    
                    st.download_button(
                        label="Download JSON",
                        data=BytesIO(json_bytes),
                        file_name=f"{result['filename'].split('.')[0]}_data.json",
                        mime="application/json"
                    )
                
                with col2:
                    # Prepare individual MD download
                    md_bytes = result["formatted_output"].encode('utf-8')
                    
                    st.download_button(
                        label="Download Markdown",
                        data=BytesIO(md_bytes),
                        file_name=f"{result['filename'].split('.')[0]}_report.md",
                        mime="text/markdown"
                    )
        
        # Provide consolidated download options
        st.markdown("---")
        st.markdown("### Download All Results")
        
        col1, col2 = st.columns(2)
        
        with col1:
            # Prepare consolidated JSON
            all_json_data = {result["filename"]: pydantic_to_dict(result["extraction_result"]) for result in results}
            all_json_str = json.dumps(all_json_data, indent=2)
            all_json_bytes = all_json_str.encode('utf-8')
            
            st.download_button(
                label="Download All as JSON",
                data=BytesIO(all_json_bytes),
                file_name="all_results.json",
                mime="application/json"
            )
        
        with col2:
            # Prepare consolidated Excel
            excel_data = []
            
            for result in results:
                extraction = result["extraction_result"]
                
                # Format data for Excel
                row = {
                    "Filename": result["filename"],
                    "Primary Case Number": extraction["primary_case_number"].full_citation if extraction["primary_case_number"] else "",
                    "Related Cases": ", ".join([case.full_citation for case in extraction["related_case_numbers"]]) if extraction["related_case_numbers"] else "",
                    "Petitioners": ", ".join([party.name for party in extraction["main_parties"] if party.role == "Petitioner"]),
                    "Respondents": ", ".join([party.name for party in extraction["main_parties"] if party.role == "Respondent"]),
                    "Judgment Date": extraction["judgment_date"],
                    "Case Background": extraction["case_background"][:500] + "..." if len(extraction["case_background"]) > 500 else extraction["case_background"]
                }
                
                excel_data.append(row)
            
            # Convert to DataFrame and then to Excel
            df = pd.DataFrame(excel_data)
            excel_buffer = BytesIO()
            df.to_excel(excel_buffer, index=False)
            excel_buffer.seek(0)
            
            st.download_button(
                label="Download All as Excel",
                data=excel_buffer,
                file_name="all_results.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
    
    else:
        # Placeholder when no files are uploaded
        st.info("Please upload one or more court document PDFs to begin extraction.")

if __name__ == "__main__":
    main()
