import datetime
import uuid
import streamlit as st
from logics.aossbot import RagBot
from awsmanager.s3_manager import show_presigned_url
from urllib.parse import unquote
from parameters.parameters import (
    ticker_company_name,
    ticker_dict,
    models_list,
    PROXY_TEXT_BUCKET,
    START_YEAR,
)
from parameters.logger import get_logger
from awsmanager.manager import AWSClientSession


logging = get_logger(__name__)

aws_session = AWSClientSession()

st.set_page_config(page_title="ProxyBot App", page_icon="💰", layout="wide")
st.markdown(
    """
    <style>
    .main {
        width: 100%;
        padding-left: 0;
        padding-right: 0;
        padding-top: 1rem;  
    }
    .container {
    margin": "0px !important;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

reduce_header_height_style = """
    <style>
        div.block-container {padding-top:0rem;}
    </style>
"""
st.markdown(reduce_header_height_style, unsafe_allow_html=True)


def inject_custom_css():
    custom_css = """
    <style>
    .special-text {
        color: blue;
        background-color: yellow;
        font-weight: bold;
    }
    </style>
    """
    st.markdown(custom_css, unsafe_allow_html=True)


inject_custom_css()


def on_company_change():
    st.session_state.bot = RagBot()
    st.session_state.messages = [
        {"role": "assistant", "content": st.session_state.bot.greeting()}
    ]
    st.session_state.disabled = False


def on_document_date_change():
    st.session_state.bot = RagBot()
    st.session_state.messages = [
        {"role": "assistant", "content": st.session_state.bot.greeting()}
    ]
    st.session_state.disabled = False


if "selected_model" not in st.session_state:
    st.session_state.selected_model = "anthropic.claude-v2:1"


def on_model_change():
    st.session_state.bot = RagBot()
    st.session_state["selected_model"] = selected_model
    css = """
    <style>
        /* Style the specific dropdown option */
        .st-bl[value="0"] {
        background: linear-gradient(blue); 
        }      
        .st-bl[value="1"] {
        color: #ff0000 !important; /* Red text color for specific value */
        font-weight: bold !important; /* Bold font */
        background: linear-gradient(to right, violet, indigo, blue, green, yellow, orange, red); /* Rainbow-colored background */
        -webkit-background-clip: text; /* Apply background to text */
        -webkit-text-fill-color: transparent; /* Make text transparent */
        }
    </style>
    """
    st.markdown(css, unsafe_allow_html=True)
    st.session_state.disabled = False


# Utility function to clear and reset the session state
def clear_session_state():
    for key in list(st.session_state.keys()):
        del st.session_state[key]


date_range = range(START_YEAR, datetime.date.today().year + 1)
column_one, column_two, column_three, column_four = st.columns([15, 15, 7, 7])

with column_one:
    st.write("# ProxyBot")
with column_two:
    selected_model = st.selectbox(
        label="Model choice",
        options=models_list,
        key="model",
        on_change=on_model_change,
    )
with column_three:
    company = st.selectbox(
        label="Company",
        options=ticker_company_name,
        index=0,
        key="company",
        on_change=on_company_change,
    )
with column_four:
    document_date = st.selectbox(
        label="Date",
        options=date_range,
        index=0,
        key="document_date",
        on_change=on_document_date_change,
    )

if "bot" in st.session_state:
    st.session_state.bot.model = selected_model

if "session_id" not in st.session_state:
    st.session_state.session_id = str(uuid.uuid4())

if "bot" not in st.session_state:
    st.session_state.bot = RagBot()


def disabled(value):
    st.session_state.disabled = value


if "disabled" not in st.session_state:
    disabled(False)

if "messages" not in st.session_state:
    st.session_state["messages"] = [
        {"role": "assistant", "content": st.session_state.bot.greeting()}
    ]

for msg in st.session_state.messages:
    st.chat_message(msg["role"]).markdown(msg["content"], unsafe_allow_html=True)

if prompt := st.chat_input(
    disabled=st.session_state.disabled,
):
    st.session_state.messages.append({"role": "user", "content": prompt})
    st.chat_message("user").write(prompt)
    with st.spinner("Waiting for response"):
        msg = st.session_state.bot.query(
            prompt,
            st.session_state.document_date,
            st.session_state.company,
            st.session_state.model,
        )
        ticker = ticker_dict[st.session_state.company]
        main_sources = msg["source"]
        updated_main_sources = []
        main_sources_dict = {}
        s3_doc_main = f"https://{PROXY_TEXT_BUCKET}.s3.amazonaws.com/{ticker}"
        cut_off_string = len(s3_doc_main) + 1
        for source in main_sources:
            clean_source = source.replace(f"text_data/{ticker}/", "", 1)
            presigned_s3_url = show_presigned_url(
                aws_session, PROXY_TEXT_BUCKET, ticker, clean_source
            )  # .replace(" ", "%20"))
            updated_main_sources.append(presigned_s3_url)
        msg["source"] = updated_main_sources
        main_text_length = len(f"14A_{ticker}_{st.session_state.document_date}_XXX")
        print(f"============{main_text_length}")
        try:
            for url_source in msg["source"]:
                source_text = url_source[
                    cut_off_string : cut_off_string + main_text_length
                ]
                print(f"============{source_text}")
            sources_html = (
                "<ul>"
                + "".join(
                    f"<li><a href='{source}' target='_blank'>{source[cut_off_string:cut_off_string+main_text_length]}</a>: {unquote(source)[cut_off_string:].replace('%20', ' ').rsplit('_', 1)[1].split('_', 4)[-1].replace('.txt', '').split('?AWSAccessKeyId')[0]}</li>"
                    for source in msg["source"]
                )
                + "</ul>"
            )
            # Formatting the complete message with sources included as an* HTML list
            msg_html = f"""
            <div style='background-color: #f0f0f0; padding: 10px; border-radius: 5px;'>
                {msg['answer']}
                <br>
                <br>
                <strong>Sources:</strong>
                {sources_html}
            </div>
            """
        except:
            # Formatting the complete message with sources included as an* HTML list
            msg_html = f"""
            <div style='background-color: #f0f0f0; padding: 10px; border-radius: 5px;'>
                {msg['answer']}
            </div>
            """
        disabled(False)
    st.session_state.messages.append({"role": "assistant", "content": msg_html})
    st.chat_message("assistant").markdown(msg_html, unsafe_allow_html=True)
    st.rerun()

hide_st_style = """
<style>#MainMenu {visibility: visible;}
footer {
    visibility: visible;
}
footer:after {
    content:'Intelligent Rag Chatbot v0.1';
    display:block;
    position:relative;
    color:tomato;
}
<style>
"""
st.markdown(hide_st_style, unsafe_allow_html=True)
