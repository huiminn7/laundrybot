import streamlit as st
from datetime import datetime
from supabase import create_client

# Supabase credentials (use Streamlit secrets)
SUPABASE_URL = st.secrets["SUPABASE_URL"]
SUPABASE_KEY = st.secrets["SUPABASE_KEY"]

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

st.set_page_config(page_title="Laundry Tracker", page_icon="🧺", layout="wide")

st.title("🧺 FCSIT Dorm Laundry Tracker")
st.subheader("Real-time machine availability")

# Auto-refresh every 30 seconds
auto_refresh = st.empty()
auto_refresh.caption("Auto-refreshes every 30 seconds")

# Fetch data from Supabase
def load_machines():
    response = supabase.table('machines').select('*').execute()
    return {row['name']: row for row in response.data}

# Display machines
# Display machines in a 3-column grid for better mobile viewing
machines = load_machines()

# Sort machines so they appear in order (Washer_1, Washer_2, etc.)
sorted_machines = sorted(machines.items())

st.write("### 🧺 Washing Machines")

# Create a grid layout (3 columns wide)
col1, col2, col3 = st.columns(3)
columns = [col1, col2, col3]

for i, (name, data) in enumerate(sorted_machines):
    # This math assigns the machine to the correct column (0, 1, or 2)
    col_index = i % 3 
    
    with columns[col_index]:
        # Using a container makes it look like a nice card
        with st.container(border=True): 
            if data['status'] == 'available':
                st.success(f"**{name.replace('_', ' ')}**")
                st.write("🟢 Ready to use")
            else:
                st.error(f"**{name.replace('_', ' ')}**")
                st.write("🔴 In use")
                if data['end_time']:
                    end_time = datetime.fromisoformat(data['end_time'].replace('Z', '+00:00'))
                    remaining = int((end_time - datetime.now()).total_seconds() / 60)
                    if remaining > 0:
                        st.write(f"⏳ Done in {remaining} mins")
                if data['username']:
                    st.caption(f"👤 @{data['username']}")

# Refresh button
st.divider()
if st.button("🔄 Refresh Now", use_container_width=True):
    st.rerun()

# Auto-refresh JavaScript
st.markdown("""
    <script>
        setTimeout(function() {
            window.location.reload();
        }, 30000);
    </script>
    """, unsafe_allow_html=True)
