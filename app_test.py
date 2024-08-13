import re
import streamlit as st
import tempfile
import json
from langchain.document_loaders import PyPDFLoader, Docx2txtLoader
from faker import Faker
import spacy
import pandas as pd
from io import BytesIO
import zipfile
import os

fake = Faker()

nlp = spacy.load("en_core_web_sm")


mappings = {}


def save_mappings():
    with open("mappings.json", "w") as file:
        json.dump(mappings, file, indent=4)
    # st.write("Mappings saved: ", mappings)

def delete_previous_files():
    files_to_delete = ["mappings.json", "anonymized_text.txt", "anonymized_file.zip"]
    for file in files_to_delete:
        try:
            if os.path.exists(file):
                os.remove(file)
        except PermissionError as e:
            st.warning(f"Could not delete {file}: {e}")

def validate_entity(entity_type, value):
    """
    Validate detected entity to ensure it belongs to the correct category.
    """
    doc = nlp(value)
    for ent in doc.ents:
        if entity_type == "Name" and ent.label_ == "PERSON":
            return True
        if entity_type == "Location" and ent.label_ in ["GPE", "LOC"]:
            return True
    return False

def replace_with_fake_data(text):
    patterns = {
        # Process address patterns first to avoid name overriding
        "Address": r"\b(\d+\s[A-Za-z0-9\s,.]+(?:St|Rd|Ave|Blvd|Ln|Dr|Ct|Pl|Sq|Ter|Way)(?:,\s[A-Za-z\s]+,\s[A-Z]{2}\s\d{5}))\b",  # Improved Address pattern
        "Name": r"\b([A-Z][a-z]+(?:\s[A-Z][a-z]+)?)\b",  # Adjusted regex for names (first, middle, last)
        "US_Driving_License": r"\b[A-Z]{1,2}\d{7,8}\b",  # US driving license number (simplified)
        "US_SSN": r"\b(\d{3}-\d{2}-\d{4})\b",  # US Social Security Number
        "DOB": r"\b((?:0[1-9]|1[0-2])/(?:0[1-9]|[12][0-9]|3[01])/\d{4})\b",  # Date of Birth in MM/DD/YYYY format
        "Employee_ID": r"\b(?:Employee ID[:\s\-]*|EID[:\s\-]*|EMP[:\s\-]*)(\w{2,10}-?\d{3,8})\b",  # Employee ID (various formats)
        "IP_Address": r"\b((?:\d{1,3}\.){3}\d{1,3})\b",  # IPv4 address
        "Credit_Card": r"\b(?:\d{4}[-\s]?){3}\d{4}|\d{16}\b", # Credit Card number
        "CVV": r"\b(?:CVV[:\s\-]*)?(\d{3,4})\b",  # CVV code (3-4 digits)
        "Email": r"\b([A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,7})\b",  # Email address
        "Phone_Number": r"\b((?:\(?\d{3}\)?[-\s.]?)?\d{3}[-\s.]?\d{4})\b",  # US Phone number
        "Credit_Expiry": r"\b(0[1-9]|1[0-2])/([0-9]{2}|[0-9]{4})\b",  # Credit Card Expiry Date
        "IBAN_Code": r"\b[A-Z]{2}\d{2}\s?[A-Z0-9]{4}\s?[A-Z0-9]{4}\s?[A-Z0-9]{4}\s?[A-Z0-9]{4}\s?[A-Z0-9]{0,4}\b",  # Improved IBAN Code pattern
        "Crypto_Wallet": r"\b[13][a-km-zA-HJ-NP-Z1-9]{25,34}\b",  # Cryptocurrency Wallet Address
        "Passport": r"\b[A-Z0-9]{9}\b",  # Passport number (simplified)
        "US_ITIN": r"\b\d{3}-\d{2}-\d{4}\b",  # US ITIN
        "URLs": r"\bhttps?:\/\/[^\s/$.?#].[^\s]*\b",  # URLs
        "NRIC": r"\b[A-Z]{1}\d{7}[A-Z]{1}\b",  # NRIC number (Singapore example)
    }

    processed_text = text

    for label, pattern in patterns.items():
        matches = re.finditer(pattern, text)
        for match in matches:
            value = match.group(0)

            if label == "Name" and not validate_entity("Name", value):
                continue  # Skip replacement if not validated as a name

            if label == "Location" and not validate_entity("Location", value):
                continue  # Skip replacement if not validated as a location

            if value not in mappings:
                # Generate a fake value and store it in mappings
                if label == "Name":
                    fake_value = fake.name()
                elif label == "Location":
                    fake_value = fake.city()
                elif label == "US_Driving_License":
                    fake_value = fake.bothify(text="??#######")
                elif label == "US_SSN":
                    fake_value = fake.ssn()
                elif label == "DOB":
                    fake_value = fake.date_of_birth(minimum_age=18, maximum_age=90).strftime('%m/%d/%Y')
                elif label == "Address":
                    fake_value = fake.address().replace('\n', ', ')
                elif label == "Employee_ID":
                    fake_value = fake.bothify(text="EID######")
                elif label == "IP_Address":
                    fake_value = fake.ipv4()
                elif label == "Credit_Card":
                    fake_value = fake.credit_card_number()
                elif label == "CVV":
                    fake_value = fake.credit_card_security_code()
                elif label == "Email":
                    fake_value = fake.email()
                elif label == "Phone_Number":
                    fake_value = fake.phone_number()
                elif label == "Credit_Expiry":
                    fake_value = fake.credit_card_expire()
                elif label == "IBAN_Code":
                    fake_value = fake.iban()
                elif label == "Crypto_Wallet":
                    fake_value = fake.bothify(text="1#########################")
                elif label == "Passport":
                    fake_value = fake.bothify(text="#########")
                elif label == "US_ITIN":
                    fake_value = fake.ssn()
                elif label == "URLs":
                    fake_value = fake.url()
                elif label == "NRIC":
                    fake_value = fake.bothify(text="S#######D")

                mappings[value] = fake_value
            else:
                fake_value = mappings[value]

            # Replace the value in the processed_text
            processed_text = processed_text.replace(value, fake_value)

    save_mappings()  # Save mappings to file
    return processed_text


states = [
    "Alabama", "Alaska", "Arizona", "Arkansas", "California", "Colorado",
    "Connecticut", "Delaware", "Florida", "Georgia", "Hawaii", "Idaho",
    "Illinois", "Indiana", "Iowa", "Kansas", "Kentucky", "Louisiana",
    "Maine", "Maryland", "Massachusetts", "Michigan", "Minnesota",
    "Mississippi", "Missouri", "Montana", "Nebraska", "Nevada",
    "New Hampshire", "New Jersey", "New Mexico", "New York",
    "North Carolina", "North Dakota", "Ohio", "Oklahoma", "Oregon",
    "Pennsylvania", "Rhode Island", "South Carolina", "South Dakota",
    "Tennessee", "Texas", "Utah", "Vermont", "Virginia", "Washington",
    "West Virginia", "Wisconsin", "Wyoming"
]


def process_csv_or_excel(file_obj, file_type):
    if file_type == 'csv':
        df = pd.read_csv(file_obj, nrows=1000)
    elif file_type == 'xlsx':
        df = pd.read_excel(file_obj, nrows=1000)

    # Convert numeric-like columns to strings
    for col in df.columns:
        if df[col].dtype == 'object':
            df[col] = df[col].astype(str)
        elif df[col].dtype in ['int64', 'float64']:
            df[col] = df[col].apply(lambda x: str(x) if not pd.isnull(x) else x)

    # anonymization process
    df_anonymized = df.applymap(lambda x: replace_with_fake_data(str(x)) if isinstance(x, str) else x)

    return df_anonymized


# Save anonymized CSV/Excel
def save_anonymized_file(df=None, text=None, original_file_name=None, file_type=None):
    with BytesIO() as buffer:
        with zipfile.ZipFile(buffer, 'w') as zip_file:
            if df is not None:
                if file_type == 'csv':
                    anonymized_file_name = f"anonymized_{original_file_name}"
                    df.to_csv(anonymized_file_name, index=False)
                    zip_file.writestr(anonymized_file_name, df.to_csv(index=False))
                elif file_type == 'xlsx':
                    anonymized_file_name = f"anonymized_{original_file_name}.xlsx"
                    with BytesIO() as excel_buffer:
                        df.to_excel(excel_buffer, index=False, engine='openpyxl')
                        zip_file.writestr(anonymized_file_name,excel_buffer.getvalue())

            if text is not None:
                zip_file.writestr("anonymized_text.txt", text)

            # Save the mappings.json file inside the zip
            save_mappings()
            with open("mappings.json", "r") as mappings_file:
                zip_file.writestr("mappings.json", mappings_file.read())

        # Set the buffer position to the beginning
        buffer.seek(0)

        # Provide a download button for the zip file
        st.download_button(
            label="Download Anonymized File and Mappings",
            data=buffer.getvalue(),
            file_name=f"anonymized_{original_file_name}.zip",
            mime="application/zip"
        )

def get_chunks(file_obj, file_type):
    with tempfile.NamedTemporaryFile(delete=False) as temp_file:
        temp_path = temp_file.name
        temp_file.write(file_obj.read())

    if file_type == 'pdf':
        loader = PyPDFLoader(temp_path)
    elif file_type in ['docx', 'doc']:
        loader = Docx2txtLoader(temp_path)
    # elif file_type in ['xlsx', 'xls']:
    #     loader = UnstructuredExcelLoader(temp_path)
    else:
        return []

    chunks = loader.load_and_split()
    return chunks


# Streamlit UI
st.title("PII Detection")

final_chunks = []
docs = st.file_uploader("Upload your files here and click on Process",
                        type=['docx', 'doc', 'pdf', 'csv', 'xlsx', 'xls'], accept_multiple_files=True)
# Streamlit dropdown with search enabled
selected_state = st.selectbox("Select a State", options=states)

if st.button("Process"):
    # delete_previous_files()
    if docs:
        with st.spinner("Processing files..."):
            for f_obj in docs:
                file_type = f_obj.name.split('.')[-1].lower()

                if file_type in ['pdf', 'docx', 'doc']:
                    chunks = get_chunks(f_obj, file_type)
                    final_chunks.extend(chunks)
                elif file_type in ['csv', 'xlsx', 'xls']:
                    df_anonymized = process_csv_or_excel(f_obj, file_type)
                    st.subheader(f"Anonymized Data - {f_obj.name}")
                    st.dataframe(df_anonymized)
                    save_anonymized_file(df=df_anonymized, original_file_name=f_obj.name, file_type=file_type)
                    st.success("File processed successfully!!")

            if final_chunks:
                full_text = "\n".join([chunk.page_content for chunk in final_chunks])
                mask = replace_with_fake_data(full_text)
                st.subheader("Anonymized Text")
                st.text_area("Anonymized Text", mask, height=300)
                st.success("Files processed successfully!")

                # Save and download anonymized text along with mappings.json
                save_anonymized_file(text=mask, original_file_name="anonymized_text")
    else:
        st.error("Please upload at least one document.")

