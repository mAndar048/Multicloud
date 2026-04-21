"""Streamlit UI for CloudPilot conversation flow."""

import os
import time

import requests
import streamlit as st

BASE_URL = os.getenv("CLOUDPILOT_API_URL", "http://127.0.0.1:8000")


def _backend_is_available() -> bool:
    try:
        response = requests.get(f"{BASE_URL}/health", timeout=2)
        return response.status_code == 200
    except requests.RequestException:
        return False


def _show_backend_start_hint() -> None:
    st.info(
        "Backend API is not reachable. Start it in another terminal with:\n"
        "python -m uvicorn cloudpilot.main:app --host 127.0.0.1 --port 8000 --reload"
    )


def home():
    """Home screen: input description and credentials."""
    st.title("CloudPilot - Multi-Cloud Infrastructure Automation")
    st.write("Describe your infrastructure needs in plain English, and we'll deploy it for you.")

    if _backend_is_available():
        st.success(f"Backend connected: {BASE_URL}")
    else:
        _show_backend_start_hint()

    description = st.text_input(
        "What do you want to deploy?",
        placeholder="e.g., deploy a static website for 1000 users on AWS"
    )

    st.subheader("Cloud Credentials")
    st.write("Provide credentials for the clouds you want to use. You can leave others empty.")

    col1, col2, col3 = st.columns(3)

    with col1:
        st.subheader("AWS")
        aws_access_key = st.text_input("Access Key ID", type="password", key="aws_key")
        aws_secret = st.text_input("Secret Access Key", type="password", key="aws_secret")

    with col2:
        st.subheader("GCP")
        gcp_json = st.text_area("Service Account JSON", height=100, key="gcp_json")

    with col3:
        st.subheader("DigitalOcean")
        do_token = st.text_input("API Token", type="password", key="do_token")

    credentials = {
        "aws": {"access_key": aws_access_key, "secret_key": aws_secret},
        "gcp": {"service_account_json": gcp_json},
        "digitalocean": {"api_token": do_token}
    }

    if st.button("Start Deployment", type="primary"):
        if not description.strip():
            st.error("Please describe what you want to deploy.")
            return

        payload = {"initial_input": description, "credentials": credentials}

        try:
            response = requests.post(f"{BASE_URL}/session/start", json=payload, timeout=10)
            response.raise_for_status()
            data = response.json()

            if "session_id" not in data:
                st.error("Failed to create session: No session ID returned from server.")
                return

            st.session_state.session_id = data["session_id"]
            if "question" in data:
                st.session_state.question = data["question"]
                st.session_state.screen = "conversation"
            elif data.get("ready"):
                st.session_state.screen = "confirm"
            else:
                st.session_state.screen = "confirm"
            st.rerun()

        except requests.RequestException as e:
            st.error(f"Failed to start session: {e}")
            _show_backend_start_hint()


def conversation():
    """Conversation screen: answer questions one by one."""
    st.title("Let's Clarify Your Requirements")

    if "question" not in st.session_state or not st.session_state.question:
        st.error("No question available. Please start a new session.")
        if st.button("🔄 Start Over"):
            st.session_state.clear()
            st.session_state.screen = "home"
            st.rerun()
        return

    question = st.session_state.question
    st.subheader(question.get("prompt", "Answer the question"))

    options = question.get("options", [])
    
    if not options:
        st.warning("No options available for this question.")
        if st.button("🔄 Start Over"):
            st.session_state.clear()
            st.session_state.screen = "home"
            st.rerun()
        return

    # Limit columns to max 3 for better layout, minimum 1
    num_cols = max(1, min(len(options), 3))
    cols = st.columns(num_cols)

    for i, option in enumerate(options):
        col_index = i % num_cols
        with cols[col_index]:
            if st.button(option.get("label", option.get("value", "Option")), key=f"option_{i}"):
                payload = {"answer": option.get("value", str(option))}

                try:
                    response = requests.post(
                        f"{BASE_URL}/session/{st.session_state.session_id}/answer",
                        json=payload,
                        timeout=10
                    )
                    response.raise_for_status()
                    data = response.json()

                    if data.get("ready"):
                        st.session_state.screen = "confirm"
                    else:
                        if "question" in data:
                            st.session_state.question = data["question"]
                    st.rerun()

                except requests.RequestException as e:
                    st.error(f"Failed to submit answer: {e}")


def confirm():
    """Confirm screen: show summary and confirm deployment."""
    st.title("Ready to Deploy")

    if "session_id" not in st.session_state:
        st.error("No active session. Please start over.")
        if st.button("🔄 Start Over"):
            st.session_state.clear()
            st.session_state.screen = "home"
            st.rerun()
        return

    st.write("Based on your inputs, we're ready to deploy your infrastructure.")
    # TODO: Show terraform plan summary when available

    col1, col2 = st.columns(2)

    with col1:
        if st.button("🚀 Deploy Now", type="primary"):
            try:
                response = requests.post(
                    f"{BASE_URL}/session/{st.session_state.session_id}/deploy",
                    timeout=10
                )
                response.raise_for_status()
                data = response.json()

                st.session_state.job_id = data["job_id"]
                st.session_state.screen = "deploying"
                st.rerun()

            except requests.RequestException as e:
                st.error(f"Failed to start deployment: {e}")

    with col2:
        if st.button("✏️ Edit Answers"):
            st.session_state.screen = "conversation"
            st.rerun()


def deploying():
    """Deploying screen: show progress and live logs."""
    st.title("🚀 Deploying Your Infrastructure")

    if "job_id" not in st.session_state:
        st.error("No deployment job found. Please start over.")
        if st.button("🔄 Start Over"):
            st.session_state.clear()
            st.session_state.screen = "home"
            st.rerun()
        return

    job_id = st.session_state.job_id
    log_placeholder = st.empty()
    status_placeholder = st.empty()

    try:
        response = requests.get(f"{BASE_URL}/job/{job_id}/status", timeout=10)
        response.raise_for_status()
        data = response.json()

        status = data.get("status", "UNKNOWN")
        logs = data.get("logs", [])

        status_placeholder.subheader(f"Status: {status}")

        if logs:
            log_placeholder.code("\n".join(str(log) for log in logs), language="text")

        if status == "SUCCESS":
            st.session_state.output_url = data.get("output_url", "N/A")
            st.session_state.screen = "done"
            st.rerun()
        elif status == "FAILED":
            st.error("❌ Deployment failed. Check logs above.")
            col1, col2 = st.columns(2)
            with col1:
                if st.button("🔄 Try Again"):
                    st.session_state.screen = "confirm"
                    st.rerun()
            with col2:
                if st.button("🏠 Home"):
                    st.session_state.clear()
                    st.session_state.screen = "home"
                    st.rerun()
        else:
            # Still deploying - show auto-refresh note
            st.info("Deployment in progress... Page will update automatically.")
            time.sleep(3)
            st.rerun()

    except requests.RequestException as e:
        st.error(f"Failed to check deployment status: {e}")
        if st.button("🔄 Retry"):
            st.rerun()
        if st.button("🏠 Home"):
            st.session_state.clear()
            st.session_state.screen = "home"
            st.rerun()


def done():
    """Done screen: show results and options."""
    st.title("✅ Deployment Complete!")

    output_url = st.session_state.get("output_url", "N/A")
    st.success(f"Your infrastructure is live at: {output_url}")

    if output_url != "N/A":
        st.markdown(f"[🌐 Open Application]({output_url})")

    st.subheader("What would you like to do next?")

    col1, col2, col3 = st.columns(3)

    with col1:
        if st.button("🔄 Deploy Another"):
            st.session_state.clear()
            st.session_state.screen = "home"
            st.rerun()

    with col2:
        if st.button("🗑️ Destroy This Deployment"):
            if "session_id" not in st.session_state:
                st.error("No active session to destroy.")
                return
            try:
                response = requests.post(
                    f"{BASE_URL}/session/{st.session_state.session_id}/destroy",
                    timeout=10
                )
                response.raise_for_status()
                data = response.json()
                st.info(f"Destroy job started: {data.get('job_id', 'Unknown')}")
            except requests.RequestException as e:
                st.error(f"Failed to start destroy: {e}")

    with col3:
        if st.button("📋 View Logs"):
            if "job_id" in st.session_state:
                st.session_state.screen = "deploying"
                st.rerun()
            else:
                st.warning("No deployment logs available.")


# Main app logic
if "screen" not in st.session_state:
    st.session_state.screen = "home"

if st.session_state.screen == "home":
    home()
elif st.session_state.screen == "conversation":
    conversation()
elif st.session_state.screen == "confirm":
    confirm()
elif st.session_state.screen == "deploying":
    deploying()
elif st.session_state.screen == "done":
    done()
