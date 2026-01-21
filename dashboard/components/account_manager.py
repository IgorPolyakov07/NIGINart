import streamlit as st
from typing import Dict, Callable
from dashboard.utils.formatters import format_compact, format_percent, format_datetime
def render_account_card(account: Dict, on_toggle: Callable = None):
    status_icon = "🟢" if account.get('is_active') else "🔴"
    status_text = "Активен" if account.get('is_active') else "Неактивен"
    with st.expander(f"{status_icon} {account['display_name']}"):
        col1, col2 = st.columns([3, 1])
        with col1:
            st.write(f"**Платформа:** {account['platform'].title()}")
            st.write(f"**URL:** {account['account_url']}")
            st.write(f"**ID:** `{account['account_id']}`")
        with col2:
            new_status = not account.get('is_active', True)
            button_label = "Деактивировать" if account.get('is_active') else "Активировать"
            button_type = "secondary" if account.get('is_active') else "primary"
            if st.button(button_label, key=f"toggle_{account['id']}", type=button_type):
                if on_toggle:
                    on_toggle(account['id'], new_status)
                    st.rerun()
