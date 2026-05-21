import streamlit as st
from datetime import datetime
from datetime import datetime, timedelta
from supabase import create_client

SUPABASE_URL = st.secrets["SUPABASE_URL"]
SUPABASE_KEY = st.secrets["SUPABASE_KEY"]
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

st.set_page_config(page_title="UM Laundry Tracker", page_icon="🧺", layout="wide")

st.title("🧺 Universiti Malaya Laundry Tracker")

# NEW: Dropdown to choose Kolej Kediaman
selected_kk = st.selectbox(
    "🏢 Choose your Kolej Kediaman:",
    ["KK12", "KK10", "KK1"]
)

st.subheader(f"Real-time machine availability for {selected_kk}")

# UPDATED: Fetch data filtered by the selected KK
def load_machines(kk):
    response = supabase.table('machines').select('*').eq('kk_name', kk).execute()
    return {row['name']: row for row in response.data}

machines = load_machines(selected_kk)
sorted_machines = sorted(machines.items())

if not sorted_machines:
    st.info(f"No washing machines registered for {selected_kk} yet.")
else:
    st.write("### 🧺 Washing Machines")
    col1, col2, col3 = st.columns(3)
    columns = [col1, col2, col3]

    for i, (name, data) in enumerate(sorted_machines):
        col_index = i % 3 
        
        with columns[col_index]:
            with st.container(border=True): 
                if data['status'] == 'available':
                    st.success(f"**{name.replace('_', ' ')}**")
                    st.write("🟢 Ready to use")
                    
                    if st.button(f"🔒 Lock Machine", key=f"lock_{name}_{selected_kk}", use_container_width=True):
                        end_time = datetime.now() + timedelta(minutes=1)
                        supabase.table('machines').update({
                            'status': 'busy',
                            'username': 'Web User',
                            'end_time': end_time.isoformat(),
                            'updated_at': datetime.now().isoformat()
                        }).eq('name', name).eq('kk_name', selected_kk).execute() # Filters by name AND KK
                        st.rerun()
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
                        
                    if st.button(f"🔓 Unlock", key=f"free_{name}_{selected_kk}", use_container_width=True):
                        supabase.table('machines').update({
                            'status': 'available',
                            'username': '',
                            'end_time': None,
                            'updated_at': datetime.now().isoformat()
                        }).eq('name', name).eq('kk_name', selected_kk).execute() # Filters by name AND KK
                        st.rerun()