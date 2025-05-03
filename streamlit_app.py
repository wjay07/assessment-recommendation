import streamlit as st
import requests

st.title("Assessment Recommendation Demo")

query = st.text_input("Enter your requirement (e.g., logical aptitude test, remote personality assessment, etc.)")

if st.button("Get Recommendations") and query:
    with st.spinner("Querying API..."):
        response = requests.post(
            "https://assessment-recommendation-cadp.onrender.com/recommend",
            json={"query": query}
        )
        if response.status_code == 200:
            data = response.json().get("recommended_assessments", [])
            if not data:
                st.warning("No recommendations found.")
            for i, item in enumerate(data, 1):
                st.subheader(f"{i}. {item['description']}")
                st.markdown(f"- **Type**: {', '.join(item['test_type'])}")
                st.markdown(f"- **Duration**: {item['duration']} min")
                st.markdown(f"- **Remote**: {item['remote_support']}")
                st.markdown(f"- **Adaptive Support**: {item['adaptive_support']}")
                st.markdown(f"[Open Link]({item['url']})")
                st.markdown("---")
        else:
            st.error("API error: " + str(response.status_code))
