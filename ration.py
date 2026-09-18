import streamlit as st
import mysql.connector
import pandas as pd

DB_CONFIG = {
    "host": "82.180.143.66",
    "user": "u263681140_students",
    "password": "testStudents@123",
    "database": "u263681140_students"
}

def get_connection():
    return mysql.connector.connect(**DB_CONFIG)

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
    # DISTRIBUTOR DASHBOARD
    if st.session_state["user_role"] == "Distributor":
        st.title("Ration Distributor Dashboard")
        
        tab1, tab2, tab3, tab4 = st.tabs([
            "Register Collector", 
            "Registered Users", 
            "Dispense History", 
            "Approve & Dispense"
        ])

        # Tab 1: Register Collector
        with tab1:
            st.subheader("Register Ration Collector (RationUsers)")
            with st.form("create_collector_form"):
                user_id = st.number_input("User ID (id)", min_value=1, step=1)
                name = st.text_input("Head of Family Name (Name)")
                family_member = st.text_input("Collector Name (FamilyMember)")
                mobile = st.text_input("Mobile Number (Mobile)")
                ration_card_no = st.text_input("Ration Card Number (rationCardNo)")
                adhar_card = st.text_input("Aadhaar Card / Finger ID (AdharCard)")
                password = st.text_input("Password (password)", type="password")
                
                submit_reg = st.form_submit_button("Register to Database")

                if submit_reg:
                    if user_id and name and family_member and mobile and ration_card_no and adhar_card and password:
                        try:
                            conn = get_connection()
                            cursor = conn.cursor()
                            cursor.execute(
                                """INSERT INTO RationUsers 
                                   (id, Name, FamilyMember, Mobile, rationCardNo, AdharCard, password) 
                                   VALUES (%s, %s, %s, %s, %s, %s, %s)""",
                                (int(user_id), name, family_member, mobile, ration_card_no, adhar_card, password)
                            )
                            conn.commit()
                            cursor.close()
                            conn.close()
                            st.success(f"Collector '{family_member}' registered with ID: {user_id}!")
                        except mysql.connector.IntegrityError:
                            st.error(f"Record with ID {user_id} already exists.")
                        except Exception as e:
                            st.error(f"Database error: {e}")
                    else:
                        st.warning("Please fill out all fields.")

        # Tab 2: All Registered Users from RationUsers
        with tab2:
            st.subheader("All Registered Users (RationUsers)")
            try:
                conn = get_connection()
                query_users = "SELECT id, Name, FamilyMember, Mobile, rationCardNo, AdharCard FROM RationUsers ORDER BY id ASC"
                df_users = pd.read_sql(query_users, conn)
                conn.close()

                if not df_users.empty:
                    st.dataframe(df_users, use_container_width=True)
                else:
                    st.info("No registered users found in RationUsers.")
            except Exception as e:
                st.error(f"Error fetching registered users: {e}")

        # Tab 3: Dispense History mapped to RationDispenseHistory schema
        with tab3:
            st.subheader("Ration Distribution History")
            try:
                conn = get_connection()
                query_history = "SELECT id, rationCardNo, collector_name, weight, dispensed_at FROM RationDispenseHistory ORDER BY dispensed_at DESC"
                df_history = pd.read_sql(query_history, conn)
                conn.close()

                if not df_history.empty:
                    st.dataframe(df_history, use_container_width=True)
                else:
                    st.info("No records found in RationDispenseHistory.")
            except Exception as e:
                st.error(f"Error fetching history: {e}")

        # Tab 4: Approval & Dispense with Slider
        with tab4:
            st.subheader("Dispense Ration Approval")
            search_query = st.text_input("Enter Ration Card No, Aadhaar, or User ID")
            
            if search_query:
                conn = get_connection()
                cursor = conn.cursor(dictionary=True)
                cursor.execute(
                    "SELECT * FROM RationUsers WHERE rationCardNo = %s OR AdharCard = %s OR id = %s",
                    (search_query, search_query, search_query)
                )
                user_match = cursor.fetchone()
                cursor.close()
                conn.close()

                if user_match:
                    st.success(f"Record Verified: **{user_match['Name']}**")
                    st.write(f"**ID:** {user_match['id']}")
                    st.write(f"**Collector:** {user_match['FamilyMember']}")
                    st.write(f"**Ration Card No:** {user_match['rationCardNo']}")
                    st.write(f"**Aadhaar:** {user_match['AdharCard']}")

                    # Quantity Slider
                    ration_qty = st.slider("Select Ration Amount (kg)", min_value=1.0, max_value=50.0, value=5.0, step=0.5)

                    if st.button("Approve & Dispense Ration"):
                        try:
                            conn = get_connection()
                            cursor = conn.cursor()
                            cursor.execute(
                                "INSERT INTO RationDispenseHistory (rationCardNo, collector_name, weight) VALUES (%s, %s, %s)",
                                (user_match['rationCardNo'], user_match['FamilyMember'], float(ration_qty))
                            )
                            conn.commit()
                            cursor.close()
                            conn.close()
                            st.balloons()
                            st.success(f"Successfully dispensed {ration_qty} kg to {user_match['FamilyMember']}!")
                        except Exception as e:
                            st.error(f"Error updating dispense history: {e}")
                else:
                    st.error("No record found matching the entered criteria.")

    # CARD HOLDER DASHBOARD
    elif st.session_state["user_role"] == "Card Holder":
        user = st.session_state["user_data"]
        st.title(f"Welcome, {user['Name']}")
        
        st.write(f"**User ID:** {user['id']}")
        st.write(f"**Ration Card No:** {user['rationCardNo']}")
        st.write(f"**Family Member / Collector:** {user['FamilyMember']}")
        st.write(f"**Mobile:** {user['Mobile']}")
        st.write(f"**Aadhaar Number:** {user['AdharCard']}")

        st.subheader("Your Dispensing Records")
        try:
            conn = get_connection()
            query = "SELECT id, rationCardNo, collector_name, weight, dispensed_at FROM RationDispenseHistory WHERE rationCardNo = %s ORDER BY dispensed_at DESC"
            df_user_history = pd.read_sql(query, conn, params=(user['rationCardNo'],))
            conn.close()

            if not df_user_history.empty:
                st.dataframe(df_user_history, use_container_width=True)
            else:
                st.info("No ration collection records found for your card.")
        except Exception as e:
            st.error(f"Error fetching user records: {e}")
