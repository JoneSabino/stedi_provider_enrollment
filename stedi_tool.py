# stedi_tool.py
import streamlit as st
import requests
import re
import pandas as pd
from typing import Any

# --- Stedi API Logic ---

def find_existing_provider(api_key: str, npi: str) -> str | None:
    """Checks if a provider exists by searching for their NPI."""
    endpoint_url: str = "https://enrollments.us.stedi.com/2024-09-01/providers"
    headers: dict[str, str] = {"Authorization": api_key}
    params: dict[str, str] = {"filter": npi}
    
    try:
        response = requests.get(endpoint_url, headers=headers, params=params)
        response.raise_for_status()
        data: dict[str, Any] = response.json()
        
        if data.get("items") and data["items"][0].get("npi") == npi:
            return data["items"][0].get("id")
        return None
    except requests.exceptions.RequestException:
        return None

def create_stedi_provider(api_key: str, provider_details: dict[str, str], contact_details: dict[str, str]) -> dict[str, Any]:
    """Calls the Stedi API to create a new provider."""
    endpoint_url: str = "https://enrollments.us.stedi.com/2024-09-01/providers"
    headers: dict[str, str] = {"Authorization": api_key, "Content-Type": "application/json"}
    payload: dict[str, Any] = {
        "name": provider_details["name"],
        "npi": provider_details["npi"],
        "taxIdType": provider_details["taxIdType"],
        "taxId": provider_details["taxId"],
        "contacts": [contact_details]
    }
    
    try:
        response = requests.post(endpoint_url, headers=headers, json=payload)
        response.raise_for_status()
        return {"success": True, "data": response.json()}
    except requests.exceptions.RequestException as e:
        error_message: str = str(e)
        if e.response is not None:
            try:
                error_details: dict[str, Any] = e.response.json()
                error_message = error_details.get('message', e.response.text)
            except ValueError:
                error_message = e.response.text
        return {"success": False, "error": error_message}

def find_existing_enrollment(api_key: str, npi: str, payer_id: str) -> bool:
    """Checks if an enrollment exists for a given NPI and Payer ID."""
    endpoint_url: str = "https://enrollments.us.stedi.com/2024-09-01/enrollments"
    headers: dict[str, str] = {"Authorization": api_key}
    params: dict[str, str] = {"providerNpis": npi, "payerIds": payer_id}

    try:
        response = requests.get(endpoint_url, headers=headers, params=params)
        response.raise_for_status()
        data: dict[str, Any] = response.json()
        return bool(data.get("items"))
    except requests.exceptions.RequestException:
        return False

def create_stedi_enrollment(api_key: str, provider_id: str, payer_id: str, user_email: str, contact_details: dict[str, str], transactions_to_enroll: list[str]) -> dict[str, Any]:
    """Calls the Stedi API to create an enrollment for a provider."""
    endpoint_url: str = "https://enrollments.us.stedi.com/2024-09-01/enrollments"
    headers: dict[str, str] = {"Authorization": api_key, "Content-Type": "application/json"}
    
    transactions_payload: dict[str, dict[str, bool]] = {key: {"enroll": True} for key in transactions_to_enroll}
    payload: dict[str, Any] = {
        "provider": {"id": provider_id},
        "payer": {"idOrAlias": payer_id},
        "userEmail": user_email,
        "primaryContact": contact_details,
        "transactions": transactions_payload,
        "source": "API",
        "status": "SUBMITTED"
    }
    
    try:
        response = requests.post(endpoint_url, headers=headers, json=payload)
        response.raise_for_status()
        return {"success": True, "data": response.json()}
    except requests.exceptions.RequestException as e:
        error_message: str = str(e)
        if e.response is not None:
            try:
                error_details: dict[str, Any] = e.response.json()
                error_message = error_details.get('message', e.response.text)
            except ValueError:
                error_message = e.response.text
        return {"success": False, "error": error_message}

# --- Streamlit User Interface ---

st.set_page_config(layout="wide", page_title="Stedi Onboarding Tool")
st.title("🚀 Stedi Provider Onboarding Tool")

col1, col2 = st.columns(2)

with col1:
    st.header("1. Configuration")
    st.subheader("API and Payer Details")
    api_key: str = st.text_input("Stedi API Key", type="password")
    payer_id: str = st.text_input(
        "Payer ID",
        help="You can find the Payer ID on the [Stedi Payer Network page](https://www.stedi.com/healthcare/network)."
    )
    user_email: str = st.text_input("Your Email for Notifications", help="Stedi will use this email for enrollment status updates.")

    st.subheader("Transaction Types to Enroll")
    st.info("Select transaction types for this batch.")
    
    transaction_options: dict[str, str] = {
        "835 Claim Payments (ERAs)": "claimPayment", "837P Professional Claims": "professionalClaimSubmission",
        "270 Eligibility Checks": "eligibilityCheck", "276 Claim Status": "claimStatus",
        "837I Institutional Claims": "institutionalClaimSubmission", "837D Dental Claims": "dentalClaimSubmission",
    }
    
    selected_transactions: list[str] = [
        transaction_options[key] for key in transaction_options 
        if st.checkbox(key, value=True if key == "835 Claim Payments (ERAs)" else False)
    ]

with col2:
    st.header("2. Default Contact")
    st.info("This contact is used for all providers in the list.")
    contact_first_name: str = st.text_input("Contact First Name", "John")
    contact_last_name: str = st.text_input("Contact Last Name", "Doe")
    contact_email: str = st.text_input("Contact Email", "john.doe@example.com")
    contact_phone: str = st.text_input("Contact Phone", "555-555-5555")
    contact_address1: str = st.text_input("Street Address 1", "123 Main St")
    contact_city: str = st.text_input("City", "Anytown")
    contact_state: str = st.text_input("State (2-letter abbr.)", "CA")
    contact_zip: str = st.text_input("Zip Code", "12345")

st.header("3. Provider List")
provider_data_input: str = st.text_area("Enter one provider per line: Name, NPI, Tax ID", height=200, placeholder="Example Clinic, 1999999992, 555123456\nAnother Hospital; 1888888881; 123456789")
tax_id_type: str = st.radio("Tax ID Type for all providers:", ("EIN", "SSN"), horizontal=True)

st.header("4. Run and Monitor")
if st.button("Start Onboarding Process", type="primary"):
    contact_details: dict[str, str] = {"firstName": contact_first_name, "lastName": contact_last_name, "email": contact_email, "phone": contact_phone, "streetAddress1": contact_address1, "city": contact_city, "state": contact_state, "zipCode": contact_zip}
    
    if not all([api_key, payer_id, user_email, provider_data_input]) or not all(contact_details.values()) or not selected_transactions:
        st.error("⚠️ Please fill in all fields and select at least one transaction type.")
    else:
        lines: list[str] = provider_data_input.strip().split('\n')
        providers_to_process: list[dict[str, str]] = [{'name': parts[0].strip(), 'npi': parts[1].strip(), 'taxId': parts[2].strip(), 'taxIdType': tax_id_type} for line in lines if line.strip() and len(parts := re.split(r'[;,]', line.strip(), 2)) == 3]

        if providers_to_process:
            st.info(f"Found {len(providers_to_process)} providers to process.")
            progress_bar = st.progress(0, text="Starting Process...")
            status_log = st.container()
            summary_data: list[list[str]] = []

            for i, provider in enumerate(providers_to_process):
                progress_bar.progress((i + 1) / len(providers_to_process), text=f"Processing {i+1}/{len(providers_to_process)}: {provider['name']}")
                
                with status_log:
                    st.markdown(f"--- \n**Processing:** `{provider['name']}` (NPI: {provider['npi']})")
                
                provider_status: str
                enrollment_status: str
                details: str
                
                provider_id: str | None = find_existing_provider(api_key, provider['npi'])
                if provider_id:
                    with status_log:
                        st.info(f"ℹ️ Provider found. Using ID: {provider_id}")
                    provider_status = "Found"
                else:
                    create_response = create_stedi_provider(api_key, provider, contact_details)
                    if create_response['success']:
                        provider_id = create_response['data'].get('id')
                        with status_log:
                            st.success(f"✅ Provider created successfully! (ID: {provider_id})")
                        provider_status = "Created"
                    else:
                        error_msg: str = create_response['error']
                        with status_log:
                            st.error(f"❌ Failed to create provider: {error_msg}")
                        summary_data.append([provider['name'], provider['npi'], "Error", "Skipped", error_msg])
                        continue

                if provider_id:
                    if find_existing_enrollment(api_key, provider['npi'], payer_id):
                        with status_log:
                            st.warning(f"⚠️ Enrollment already exists. Skipped.")
                        enrollment_status, details = "Skipped (Exists)", "N/A"
                    else:
                        enroll_response = create_stedi_enrollment(api_key, provider_id, payer_id, user_email, contact_details, selected_transactions)
                        if enroll_response['success']:
                            enrollment_id: str = enroll_response['data'].get('id')
                            with status_log:
                                st.success(f"✅ Enrollment submitted! (ID: {enrollment_id})")
                            enrollment_status, details = "Submitted", enrollment_id
                        else:
                            error_msg = enroll_response['error']
                            with status_log:
                                st.error(f"❌ Enrollment failed: {error_msg}")
                            enrollment_status, details = "Error", error_msg
                summary_data.append([provider['name'], provider['npi'], provider_status, enrollment_status, details])

            st.header("🎉 Process Complete!")
            st.subheader("Summary Report")
            summary_df: pd.DataFrame = pd.DataFrame(summary_data, columns=["Provider Name", "NPI", "Provider Status", "Enrollment Status", "Details/ID"])
            st.dataframe(summary_df, use_container_width=True)

