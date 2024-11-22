from utils.bedrock import invoke_bedrock
import datetime
import json
import os
import time
import re


# Get the absolute path of the current script
script_dir = os.path.dirname(os.path.abspath(__file__))

def fetch_customers():
    with open(os.path.join(script_dir, "../data/customers.json")) as f:
        return json.load(f)

def fetch_products():
    with open(os.path.join(script_dir, "../data/products.json")) as f:
        return json.load(f)

def segment_basic(customer):
    segments = []

    age = customer['demographics']['age']
    income = customer['demographics']['annualIncome']
    channels = customer['behavioral']['transactionPatterns']['channels']
    life_stage = customer['lifeStage']

    # Age-based segmentation
    if age < 35:
        segments.append('young_professionals')
    elif 35 <= age < 60:
        segments.append('families')
    else:
        segments.append('pre_retirees')

    # Income-based segmentation
    if income > 100000:
        segments.append('high_income')
    else:
        segments.append('low_income')

    # Technology usage segmentation
    if "Mobile App" in channels or "Online Banking" in channels:
        segments.append('tech_savvy')
    else:
        segments.append('traditional')

    # Life stage segmentation
    segments.append(life_stage.lower().replace(" ", "_"))

    return segments

def segment_rfm(customer):
    def get_recency_score(last_transaction_date):
        today = datetime.date.today()
        last_transaction_date = datetime.datetime.strptime(last_transaction_date, '%Y-%m-%d').date()
        days_since_last_transaction = (today - last_transaction_date).days
        if days_since_last_transaction <= 30:
            return 5
        elif days_since_last_transaction <= 90:
            return 4
        elif days_since_last_transaction <= 180:
            return 3
        elif days_since_last_transaction <= 365:
            return 2
        else:
            return 1

    def get_frequency_score(transactions_ttm):
        if transactions_ttm >= 360:
            return 5
        elif transactions_ttm >= 180:
            return 4
        elif transactions_ttm >= 90:
            return 3
        elif transactions_ttm >= 36:
            return 2
        else:
            return 1

    def get_monetary_score(total_assets, profitability):
        monetary_value = total_assets * profitability
        if monetary_value >= 1000000:
            return 5
        elif monetary_value >= 500000:
            return 4
        elif monetary_value >= 250000:
            return 3
        elif monetary_value >= 100000:
            return 2
        else:
            return 1

    def get_segment(r, f, m):
        score = r * 100 + f * 10 + m
        if score >= 444:
            return "Loyal"
        elif score >= 434:
            return "Potential Loyalist"
        elif score >= 421:
            return "Recent Customers"
        elif score >= 324:
            return "Need Attention"
        elif score >= 223:
            return "About to Sleep"
        elif score >= 314:
            return "At Risk"
        elif score >= 112:
            return "Hibernating"
        else:
            return "Lost"

    recency_score = get_recency_score(customer['behavioral']['lastTransactionDate'])
    frequency_score = get_frequency_score(customer['behavioral']['numberOfTransactionTTM'])
    monetary_score = get_monetary_score(customer['customerLifetimeValue']['totalAssetsUnderManagement'],
                                        customer['customerLifetimeValue']['profitability'])

    segment = get_segment(recency_score, frequency_score, monetary_score)
    rfm_score = f"{recency_score}{frequency_score}{monetary_score}"

    return {
        "segment": segment,
        "rfm_score": rfm_score
    }
    

def recommend_products_basic(customer, products, basic_segment, rfm_result):

    # Get RFM segment
    rfm_result = segment_rfm(customer)
    rfm_segment = rfm_result['segment']
    rfm_score = rfm_result['rfm_score']
    
    recommended_products = []
    
    # Recommendation logic based on segments
    if basic_segment == "Young Savers":
        recommended_products.extend([
            products[0]['products'][2],  # Target Savings Plan
            products[2]['products'][1]   # Platinum Card
        ])
    elif basic_segment == "Affluent Professionals":
        recommended_products.extend([
            products[2]['products'][0],  # Visa Infinite Card
            products[3]['products'][1]   # Prosperity Booster Whole Life Plan
        ])
    elif basic_segment == "Growing Families":
        recommended_products.extend([
            products[1]['products'][3],  # Mortgage Services
            products[3]['products'][2]   # Personal Accident Insurance Plan
        ])
    elif basic_segment == "Pre-Retirement Planners":
        recommended_products.extend([
            products[3]['products'][0],  # Forest Insurance Plan
            products[0]['products'][0]   # Fixed Deposit
        ])
    elif basic_segment == "Established Retirees":
        recommended_products.extend([
            products[0]['products'][0],  # Fixed Deposit
            products[3]['products'][1]   # Prosperity Booster Whole Life Plan
        ])
    elif basic_segment == "High-Net-Worth Individuals":
        recommended_products.extend([
            products[2]['products'][0],  # Visa Infinite Card
            products[3]['products'][0]   # Forest Insurance Plan
        ])
    elif basic_segment == "Credit Builders":
        recommended_products.extend([
            products[2]['products'][1],  # Platinum Card
            products[1]['products'][0]   # Easy Cash Personal Loan
        ])
    elif basic_segment == "Small Business Owners":
        recommended_products.extend([
            products[1]['products'][1],  # Perfect Fit Personal Loan
            products[2]['products'][0]   # Visa Infinite Card
        ])
    
    # Additional recommendations based on RFM segment
    if rfm_segment in ["Loyal", "Potential Loyalist"]:
        recommended_products.append(products[3]['products'][1])  # Prosperity Booster Whole Life Plan
    elif rfm_segment in ["Need Attention", "About to Sleep"]:
        recommended_products.append(products[0]['products'][2])  # Target Savings Plan
    elif rfm_segment in ["At Risk", "Hibernating", "Lost"]:
        recommended_products.append(products[1]['products'][2])  # Balance Transfer Personal Loan
    
    # Deduplicate recommendations
    recommended_products = list({product['name']: product for product in recommended_products}.values())
    
    return recommended_products

def recommend_products_ai(selected_model, customer, products, basic_segment, rfm_result):
    output_format = '''
    {
        recommended_products: [
            {
                "name": "Product Name",
                "description": "Product Description",
                "features": ["Feature 1", "Feature 2", ...],
                "benefits": ["Benefit 1", "Benefit 2", ...],
                "eligibility": ["Eligibility 1", "Eligibility 2", ...],
                "specialOffers": ["Special Offer 1", "Special Offer 2", ...]
            },
            ...
        ],
        reasons: [
            "Reason 1",
            "Reason 2",
            ...
        ]
    }
    '''
    
    prompt = f'''
    <customer_profile>
    {customer}
    </customer_profile>
    
    <product_catalog>
    {products}
    </product_catalog>

    <customer_segment>
        <basic_segment>{basic_segment}</basic_segment>
        <rfm_segment>{rfm_result['segment']}</rfm_segment>
    </customer_segment>

    With given customer profile and product catalog, recommend TWO most suitable products for the customer, and explain the reasons.
    Return the result in json format enclosed <json> tag, without prefix or suffix.
    
    Following is the expected output format:
    <json>
    {output_format}
    </json>
    '''
    
    max_attempts = 1
    for attempt in range(max_attempts):
        try:
            res = invoke_bedrock(selected_model, prompt)
            print(res)
            
            # Extract JSON content enclosed in <json> tags
            match = re.search(r'<json>(.*?)</json>', res, re.DOTALL)
            if match:
                json_content = match.group(1)
                parsed_response = json.loads(json_content)
                return parsed_response
            else:
                raise ValueError("No JSON content found in response")
        except (json.JSONDecodeError, ValueError, Exception) as e:
            if attempt < max_attempts - 1:
                time.sleep(1)  # Wait for 1 second before retrying
            else:
                return {"error": "Failed to get a valid response after 3 attempts", "details": str(e)}