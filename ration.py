import streamlit as st
import mysql.connector
import pandas as pd

# Database configuration
DB_CONFIG = {
    "host": "82.180.143.66",
    "user": "u263681140_students",
    "password": "testStudents@123",
    "database": "u263681140_students"
}

def get_connection():
    return mysql.connector.connect(**DB_CONFIG)

def init_tables():
    conn = get_connection()
    cursor = conn.cursor()
    # Table for collectors registered by finger_id
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS RationCollectors (
            id INT AUTO_INCREMENT PRIMARY KEY,
            finger_id VARCHAR(50) UNIQUE,
            rationCardNo VARCHAR(50),
            head_of_family VARCHAR(50),
            collector_name VARCHAR(50),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    # Table for dispensing history
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS RationDispenseHistory (
            id INT AUTO_INCREMENT PRIMARY KEY,
            rationCardNo VARCHAR(50),
            collector_name VARCHAR(50),
            amount_kg FLOAT,
            dispensed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    cursor.close()
    conn.close()

init_tables()

# Session State Initialization
if "authenticated" not in st.session_state:
    st.session_state["authenticated"] = False
if "user_role" not in st.session_state:
    st.session_state["user_role"] = None
if "user_data" not in st.session_state:
    st.session_state["user_data"] = None

# Sidebar Authentication
st.sidebar.title("Login Module")

if not st.session_state["authenticated"]:
    role = st.sidebar.selectbox("Login As", ["Ration Distributor", "Ration Card Holder"])
    
    if role == "Ration Distributor":
        dist_user = st.sidebar.text_input("Distributor Username")
        dist_pass = st.sidebar.text_input("Distributor Password", type="password")
        if st.sidebar.button("Login"):
            # Default distributor credentials
            if dist_user == "admin" and dist_pass == "admin123":
                st.session_state["authenticated"] = True
                st.session_state["user_role"] = "Distributor"
                st.rerun()
            else:
                st.sidebar.error("Invalid distributor credentials")

    elif role == "Ration Card Holder":
        card_no = st.sidebar.text_input("Ration Card No")
        card_pass = st.sidebar.text_input("Password", type="password")
        if st.sidebar.button("Login"):
            conn = get_connection()
            cursor = conn.cursor(dictionary=True)
            cursor.execute(
                "SELECT * FROM RationUsers WHERE rationCardNo = %s AND password = %s",
                (card_no, card_pass)
            )
            user = cursor.fetchone()
            cursor.close()
            conn.close()

            if user:
                st.session_state["authenticated"] = True
                st.session_state["user_role"] = "Card Holder"
                st.session_state["user_data"] = user
                st.rerun()
            else:
                st.sidebar.error("Invalid card number or password")
else:
    st.sidebar.write(f"Logged in as: **{st.session_state['user_role']}**")
    if st.sidebar.button("Logout"):
        st.session_state["authenticated"] = False
        st.session_state["user_role"] = None
        st.session_state["user_data"] = None
        st.rerun()

# Main Application Views
if not st.session_state["authenticated"]:
    st.info("Please log in using the sidebar to proceed.")
else:
    # ----------------------------------------------------
    # DISTRIBUTOR DASHBOARD
    # ----------------------------------------------------
    if st.session_state["user_role"] == "Distributor":
        st.title("Ration Distributor Dashboard")
        
        tab1, tab2, tab3 = st.tabs(["Register Collector", "Dispense History", "Approve & Dispense"])

        # Tab 1: Collector Registration
        with tab1:
            st.subheader("Create Ration Collector Account")
            with st.form("create_collector_form"):
                finger_id = st.text_input("Fingerprint Scanner ID / Biometric ID")
                ration_no = st.text_input("Ration Card Number")
                head_name = st.text_input("Head of Family Name")
                collector_name = st.text_input("Ration Collector Name")
                submit_reg = st.form_submit_button("Register Collector")

                if submit_reg:
                    if finger_id and ration_no and head_name and collector_name:
                        try:
                            conn = get_connection()
                            cursor = conn.cursor()
                            cursor.execute(
                                """INSERT INTO RationCollectors 
                                   (finger_id, rationCardNo, head_of_family, collector_name) 
                                   VALUES (%s, %s, %s, %s)""",
                                (finger_id, ration_no, head_name, collector_name)
                            )
                            conn.commit()
                            cursor.close()
                            conn.close()
                            st.success(f"Collector {collector_name} registered successfully with Finger ID: {finger_id}!")
                        except mysql.connector.IntegrityError:
                            st.error("This Finger ID is already mapped to an account.")
                        except Exception as e:
                            st.error(f"Database error: {e}")
                    else:
                        st.warning("Please fill out all fields.")

        # Tab 2: Dispense History
        with tab2:
            st.subheader("Ration Distribution Logs")
            conn = get_connection()
            df_history = pd.read_sql("SELECT * FROM RationDispenseHistory ORDER BY dispensed_at DESC", conn)
            conn.close()

            if not df_history.empty:
                st.dataframe(df_history, use_container_width=True)
            else:
                st.info("No distribution records found yet.")

        # Tab 3: Approval & Dispense with Slider
        with tab3:
            st.subheader("Dispense Ration via Fingerprint Scan")
            input_finger_id = st.text_input("Enter/Scan Finger ID for Verification")
            
            if input_finger_id:
                conn = get_connection()
                cursor = conn.cursor(dictionary=True)
                cursor.execute("SELECT * FROM RationCollectors WHERE finger_id = %s", (input_finger_id,))
                collector = cursor.fetchone()
                cursor.close()
                conn.close()

                if collector:
                    st.success(f"Collector Verified: **{collector['collector_name']}**")
                    st.write(f"**Ration Card No:** {collector['rationCardNo']}")
                    st.write(f"**Head of Family:** {collector['head_of_family']}")

                    # Quantity Slider
                    ration_qty = st.slider("Select Ration Amount (kg)", min_value=1.0, max_value=50.0, value=5.0, step=0.5)

                    if st.button("Approve & Dispense Ration"):
                        conn = get_connection()
                        cursor = conn.cursor()
                        cursor.execute(
                            "INSERT INTO RationDispenseHistory (rationCardNo, collector_name, amount_kg) VALUES (%s, %s, %s)",
                            (collector['rationCardNo'], collector['collector_name'], ration_qty)
                        )
                        conn.commit()
                        cursor.close()
                        conn.close()
                        st.balloons()
                        st.success(f"Successfully dispensed {ration_qty} kg to {collector['collector_name']}!")
                else:
                    st.error("No registered collector found for this Finger ID.")

    # ----------------------------------------------------
    # CARD HOLDER DASHBOARD
    # ----------------------------------------------------
    elif st.session_state["user_role"] == "Card Holder":
        user = st.session_state["user_data"]
        st.title(f"Welcome, {user['Name']}")
        
        st.write(f"**Ration Card No:** {user['rationCardNo']}")
        st.write(f"**Family Member:** {user['FamilyMember']}")
        st.write(f"**Mobile:** {user['Mobile']}")
        st.write(f"**Aadhaar Number:** {user['AdharCard']}")

        st.subheader("Your Dispensing Records")
        conn = get_connection()
        query = "SELECT * FROM RationDispenseHistory WHERE rationCardNo = %s ORDER BY dispensed_at DESC"
        df_user_history = pd.read_sql(query, conn, params=(user['rationCardNo'],))
        conn.close()

        if not df_user_history.empty:
            st.dataframe(df_user_history, use_container_width=True)
        else:
            st.info("No ration collection records found for your card.")
