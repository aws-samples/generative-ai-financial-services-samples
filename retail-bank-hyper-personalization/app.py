import streamlit as st
import os
from utils.crm import *
from utils.agent import *
from utils.bedrock import fetch_model_ids
from dill.source import getsource

st.set_page_config(layout="wide")

# Fetch the original list of customers
model_ids = fetch_model_ids()
customers = fetch_customers()
products = fetch_products()
selected_customer = ""

# Initialize session state
session_keys = ['basic_products', 'ai_products', 'generated_contents', 'reviewing_content', 'review_result', 'reviewed']
for key in session_keys:
    if key not in st.session_state:
        st.session_state[key] = [] if key == 'basic_products' or key == 'generated_contents' else None

def reset():
    for key in session_keys:
        st.session_state[key] = [] if key == 'basic_products' or key == 'generated_contents' else None

st.write("# Retail Bank Hyper-Personalization")

col1, col2 = st.columns([1, 2])

with col1:
    st.subheader("Select a Customer")
    
    selected_customer = st.selectbox(
        "Choose a customer",
        tuple(customer["name"] for customer in customers),
        on_change=reset
    )
    # Filter customer by selected_customer's name
    filtered_customer = [customer for customer in customers if customer["name"] == selected_customer][0]
    selected_customer = filtered_customer
    
    if selected_customer:
        st.caption("Customer Profile")
        with st.container(border=True, height=300):
            st.write(selected_customer)
         
        st.caption("Customer Segmentation")   
        with st.container(border=True):
            with st.popover("Basic Model"):
                st.write("Source Code:")
                st.code(getsource(segment_basic))
            st.session_state['basic_segment'] = segment_basic(selected_customer)
            st.write(st.session_state['basic_segment'])

            with st.popover("RFM Model"):
                st.write("Source Code:")
                st.code(getsource(segment_rfm))
            st.session_state['rfm_result'] = segment_rfm(selected_customer)
            st.write(st.session_state['rfm_result'])

                
with col2:
    
    st.subheader("Hyper-Personalization")
    
    selected_model = st.selectbox(
        "Choose a Model",
        model_ids
    )

    tab1, tab2 = st.tabs(["✏️ Generate", "🔍 Review"])

    with tab1:
        col1, col2 = st.columns([2, 2])

        with col1:
            st.caption("Recommend Products")
            with st.expander("Products Catalog", expanded=True):
                    # Create tabs for each product category
                    categories = [product['category'] for product in products]
                    tabs = st.tabs(categories)
                    
                    for i, tab in enumerate(tabs):
                        with tab:
                            category_products = products[i]['products']
                            with st.container(border=False, height=300):
                                for product in category_products:
                                    st.subheader(product['name'])
                                    st.write(product['description'])
                                    st.write(f"**Features:**")
                                    st.write(", ".join(product['features']))
                                    st.write("**Benefits:**")
                                    st.write(", ".join(product['benefits']))
                                    st.write(f"**Eligibility:** {product['eligibility']}")
                                    st.write(f"**Special Offers:** {product['specialOffers']}")
                                    st.write("---")
            with st.container(border=True):
                                
                if st.button("🤖 Generate Recommendations"):
                    with st.spinner("Generating recommendations..."):   
                        st.session_state['basic_products'] = recommend_products_basic(selected_customer, products, st.session_state.get('basic_segment'), st.session_state.get('rfm_result'))
                        st.session_state['ai_products'] = recommend_products_ai(selected_model, selected_customer, products, st.session_state.get('basic_segment'), st.session_state.get('rfm_result'))            

                if st.session_state['basic_products']:
                    with st.popover("Basic Engine"):
                        st.write("Source Code:")
                        st.code(getsource(recommend_products_basic))
                    st.write([product["name"] for product in st.session_state['basic_products']])

                if st.session_state['ai_products']:
                    with st.popover("AI Engine"):
                        st.write("Source Code:")
                        st.code(getsource(recommend_products_ai))
                    st.write([product["name"] for product in st.session_state['ai_products']['recommended_products']])
                    with st.expander("Reasons"):
                        st.write(st.session_state['ai_products']['reasons'])

                        
        with col2:
            st.caption('Generate Hyper-Personalized Message')
            with st.container(border=True):
                # Generate content only when the button is clicked
                
                if st.session_state['basic_products'] and st.session_state['ai_products']:
                    products = st.session_state['basic_products'] + st.session_state['ai_products']['recommended_products']                   
                    
                    # Deduplicate products
                    # Initialize a list to store unique products
                    unique_products = []

                    # Initialize a set to keep track of product names
                    seen_names = set()

                    # Iterate through the products list
                    for product in products:
                        if product['name'] not in seen_names:
                            unique_products.append(product)
                            seen_names.add(product['name'])
                    products = unique_products
                    
                    with st.popover("Instruct Prompt"):
                        st.code(getsource(generate_content))
                        
                    content_format = st.radio(
                        "Content Format",
                        ["App Push Message", "Email"],
                        index=0,
                        on_change=lambda c=[], i=i: st.session_state.update({'generated_contents': []})
                    )    
                    
                    if st.button("🤖 Generate marketing content by LLM"):
                        
                        st.session_state['generated_contents'] = []
                        st.session_state['generated_format'] = content_format
                        
                        for (i, product) in enumerate(products):
                            with st.spinner(f"Generating content..."):
                                content = generate_content(selected_model, selected_customer, st.session_state['basic_segment'], st.session_state['rfm_result'], product, '', content_format)
                                st.session_state['generated_contents'].append(content)
                                
                                # Display Generated Content
                                with st.container(border=True):
                                    st.caption(f"Product {i+1} - {product['name']}")
                                    st.write(f"**Title:** {content['title']}")
                                    st.write(f"**Body**:")
                                    with st.container(border=True, height=250):
                                        st.html(content['body'])
                                    with st.popover("Explanation"):
                                        st.write(content['explanation'])
                                    if st.button(f"Copy to Review", type="primary", key=f"review_{i}", on_click=lambda c=content, i=i: st.session_state.update({'reviewing_content': c, 'review_result': None})):
                                        pass
                    else:
                        # Display previously generated contents
                        for i, content in enumerate(st.session_state['generated_contents']):
                            with st.container(border=True):
                                st.caption(f"Product {i+1} - {product['name']}")
                                st.write(f"**Title:** {content['title']}")
                                st.write(f"**Body**:")
                                with st.container(border=True, height=250):
                                    st.html(content['body'])
                                with st.popover("Explanation"):
                                    st.write(content['explanation'])
                                if st.button(f"Copy to Review", type="primary", key=f"review_{i}", on_click=lambda c=content, i=i: st.session_state.update({'reviewing_content': c, 'review_result': None})):
                                    pass
                else:
                    st.write("Please generate recommendations first.")

    with tab2:
        col1, col2 = st.columns([2, 2])
        with col1:
            st.caption("Reviewing Content")
            final_content = st.session_state.get('reviewing_content')
            if final_content:
                final_content = {
                    'title': final_content['title'],
                    'body': final_content['body'],
                }
                with st.container(border=True):
                    st.write(f"**Title:** {final_content['title']}")
                    st.write(f"**Body:**")
                    st.html(final_content['body'])
            else:
                st.write("Please copy the generated content to review first.")
        with col2:
            st.caption("Review Result")
            if st.session_state['reviewing_content']:                
                script_dir = os.path.dirname(os.path.abspath(__file__))

                with st.expander("Guidelines"):
                    with open(os.path.join(script_dir, "docs/sample_brand_messaging_guideline.md"), 'r') as file:
                        st.download_button('Brand Guideline', file)
                        
                    with open(os.path.join(script_dir, "docs/sample_compliant_guideline.md"), 'r') as file:
                        st.download_button('Compliant Guideline', file)               
                
                with st.container(border=True):
                    with st.popover("Instruct Prompt"):
                        st.code(getsource(review_content))
                    if st.button("🤖 Review content by LLM"):
                        with st.spinner('Reviewing content...'):
                            st.session_state['review_result'] = review_content(selected_model, final_content, st.session_state['reviewed'])

                    if st.session_state['review_result']:                           
                        if st.session_state['review_result']['result'] == "Rejected":
                            icon = "❌"
                        else:
                            icon = "✅"
                        st.info(st.session_state['review_result']['result'], icon=icon)
                        with st.popover("Feedback"):
                            st.write(st.session_state['review_result']['feedbacks'])
                            
                        if st.session_state['review_result']['result'] == "Rejected":
                            if st.button("Regenerate based on feedback", type="primary"):
                                with st.spinner('Regenerating content...'):
                                    st.session_state['reviewing_content'] = generate_content(selected_model, selected_customer, st.session_state['basic_segment'], st.session_state['rfm_result'], final_content, st.session_state['review_result']['feedbacks'], st.session_state['generated_format'])
                                    st.session_state['reviewed'] = True
                                    st.session_state['review_result'] = None
                                    st.rerun()
            else:
                st.write("Please copy the generated content to review first.")
