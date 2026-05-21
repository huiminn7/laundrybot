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
machines = load_machines()

cols = st.columns(len(machines))

for i, (name, data) in enumerate(machines.items()):
    with cols[i]:
        if data['status'] == 'available':
            st.success(f"### {name.replace('_', ' ')}")
            st.write("🟢 **Status:** Ready to use")
            st.write("⏱️ **Waiting time:** 0 min")
        else:
            st.error(f"### {name.replace('_', ' ')}")
            st.write("🔴 **Status:** In use")
            if data['end_time']:
                end_time = datetime.fromisoformat(data['end_time'].replace('Z', '+00:00'))
                remaining = int((end_time - datetime.now()).total_seconds() / 60)
                if remaining > 0:
                    st.write(f"⏳ **Done in:** {remaining} minutes")
                    st.write(f"⏰ **Finish at:** {end_time.strftime('%H:%M')}")
            if data['username']:
                st.write(f"👤 **User:** @{data['username']}")

# Refresh button
if st.button("🔄 Refresh Now"):
    st.rerun()

# Add JavaScript for auto-refresh
st.markdown("""
    <script>
        setTimeout(function() {
            window.location.reload();
        }, 30000);
    </script>
    """, unsafe_allow_html=True)