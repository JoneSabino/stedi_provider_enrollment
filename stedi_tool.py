# stedi_tool.py
import streamlit as st
import requests
import re

# --- Stedi API Logic ---

def create_stedi_provider(api_key, provider_details, contact_details):
    """
    Calls the Stedi API to create a new provider.
    """
    endpoint_url = "https://enrollments.us.stedi.com/2024-09-01/providers"
    
    headers = {
        "Authorization": api_key,
        "Content-Type": "application/json"
    }
    
    payload = {
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
        error_message = str(e)
        if e.response is not None:
            try:
                error_details = e.response.json()
                error_message = error_details.get('message', e.response.text)
            except ValueError:
                error_message = e.response.text
        return {"success": False, "error": error_message}

def create_stedi_enrollment(api_key, provider_id, payer_id, user_email, contact_details, transactions_to_enroll):
    """
    Calls the Stedi API to create an enrollment for a provider.
    """
    endpoint_url = "https://enrollments.us.stedi.com/2024-09-01/enrollments"
    
    headers = {
        "Authorization": api_key,
        "Content-Type": "application/json"
    }
    
    # Build the 'transactions' object based on user's selections
    transactions_payload = {
        key: {"enroll": True} for key in transactions_to_enroll
    }

    # Payload structure from the documentation
    payload = {
        "provider": {"id": provider_id},
        "payer": {"idOrAlias": payer_id},
        "userEmail": user_email,
        "primaryContact": contact_details,
        "transactions": transactions_payload,
        "source": "API",
        "status": "SUBMITTED" # Automatically submit the enrollment
    }
    
    try:
        response = requests.post(endpoint_url, headers=headers, json=payload)
        response.raise_for_status()
        return {"success": True, "data": response.json()}
    except requests.exceptions.RequestException as e:
        error_message = str(e)
        if e.response is not None:
            try:
                error_details = e.response.json()
                error_message = error_details.get('message', e.response.text)
            except ValueError:
                error_message = e.response.text
        return {"success": False, "error": error_message}

# --- Streamlit User Interface ---

st.set_page_config(layout="wide", page_title="Stedi Onboarding Tool")
st.title("🚀 Stedi Provider Onboarding Tool")

# --- UI Column Layout ---
col1, col2 = st.columns(2)

with col1:
    st.header("1. Configuration")
    st.subheader("API and Payer Details")
    api_key = st.text_input("Stedi API Key", type="password")
    payer_id = st.text_input("Payer ID")
    user_email = st.text_input("Your Email for Notifications", help="Stedi will use this email to send you updates about the enrollment status.")

    st.subheader("Transaction Types to Enroll")
    st.info("Select all transaction types you want to enroll providers in for this batch.")
    
    # Transaction types from the API documentation
    transaction_options = {
        "835 Claim Payments (ERAs)": "claimPayment",
        "837P Professional Claims": "professionalClaimSubmission",
        "270 Eligibility Checks": "eligibilityCheck",
        "276 Claim Status": "claimStatus",
        "837I Institutional Claims": "institutionalClaimSubmission",
        "837D Dental Claims": "dentalClaimSubmission",
    }
    
    selected_transactions = [
        transaction_options[key] for key in transaction_options 
        if st.checkbox(key, value=True if key == "835 Claim Payments (ERAs)" else False)
    ]

with col2:
    st.header("2. Default Contact")
    st.info("This contact will be used for all providers in the list below.")
    contact_first_name = st.text_input("Contact First Name", "John")
    contact_last_name = st.text_input("Contact Last Name", "Doe")
    contact_email = st.text_input("Contact Email", "john.doe@example.com")
    contact_phone = st.text_input("Contact Phone", "555-555-5555")
    contact_address1 = st.text_input("Street Address 1", "123 Main St")
    contact_city = st.text_input("City", "Anytown")
    contact_state = st.text_input("State (2-letter abbr.)", "CA")
    contact_zip = st.text_input("Zip Code", "12345")


st.header("3. Provider List")
provider_data_input = st.text_area(
    "Enter one provider per line: Name, NPI, Tax ID",
    height=200,
    placeholder="Example Clinic, 1999999992, 555123456\nAnother Hospital; 1888888881; 123456789"
)
tax_id_type = st.radio(
    "Tax ID Type for all providers in this batch:",
    ("EIN", "SSN"),
    horizontal=True
)

st.header("4. Run and Monitor")
if st.button("Start Onboarding Process", type="primary"):
    # --- Input Validation ---
    contact_details = {
        "firstName": contact_first_name, "lastName": contact_last_name,
        "email": contact_email, "phone": contact_phone,
        "streetAddress1": contact_address1, "city": contact_city,
        "state": contact_state, "zipCode": contact_zip
    }
    
    is_config_valid = all([api_key, payer_id, user_email, provider_data_input])
    is_contact_valid = all(contact_details.values())
    
    if not is_config_valid or not is_contact_valid or not selected_transactions:
        st.error("⚠️ Please fill in all fields and select at least one transaction type.")
    else:
        # --- Data Parsing ---
        lines = provider_data_input.strip().split('\n')
        providers_to_process = []
        for i, line in enumerate(lines):
            if not line.strip(): continue
            parts = re.split(r'[;,]', line.strip(), 2)
            if len(parts) == 3:
                providers_to_process.append({
                    'name': parts[0].strip(), 'npi': parts[1].strip(),
                    'taxId': parts[2].strip(), 'taxIdType': tax_id_type
                })
            else:
                st.warning(f"Skipping line {i+1} due to invalid format: '{line}'")

        if providers_to_process:
            st.info(f"Found {len(providers_to_process)} providers to process.")
            progress_bar = st.progress(0, text="Starting Process...")
            status_log = st.container()
            
            for i, provider in enumerate(providers_to_process):
                progress_text = f"Processing provider {i+1} of {len(providers_to_process)}: {provider['name']}"
                progress_bar.progress((i + 1) / len(providers_to_process), text=progress_text)
                
                with status_log:
                    st.markdown(f"--- \n\n**Processing:** `{provider['name']}` (NPI: {provider['npi']})")
                
                # --- Step 1: Create Provider ---
                create_response = create_stedi_provider(api_key, provider, contact_details)

                if create_response['success']:
                    provider_id = create_response['data'].get('id')
                    with status_log:
                        st.success(f"✅ Provider '{provider['name']}' created successfully! (ID: {provider_id})")

                    # --- Step 2: Create Enrollment ---
                    enroll_response = create_stedi_enrollment(
                        api_key, provider_id, payer_id, user_email, contact_details, selected_transactions
                    )
                    if enroll_response['success']:
                        enrollment_id = enroll_response['data'].get('id')
                        with status_log:
                            st.success(f"✅ Enrollment for '{provider['name']}' submitted! (Enrollment ID: {enrollment_id})")
                    else:
                         with status_log:
                            st.error(f"❌ Enrollment failed for '{provider['name']}': {enroll_response['error']}")
                else: # Failed to create provider
                    with status_log:
                        st.error(f"❌ Failed to create provider '{provider['name']}': {create_response['error']}")
            
            st.balloons()
            st.header("🎉 Process Complete!")