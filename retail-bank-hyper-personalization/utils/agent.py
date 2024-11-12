import json
import re
import os

from utils.bedrock import invoke_bedrock

# Get the absolute path of the current script
script_dir = os.path.dirname(os.path.abspath(__file__))

def generate_content(selected_model, customer, basic_segment, rfm_result, product, feedback, content_format, retry_limit=5):
    expected_output = ''
    sample_message = ''
    
    if content_format == "Email":
        expected_output = '''
        <xml>
            <title>{15 words title}</title>
            <body>{HTML content with details and links}</body>
            <explanation>{"Explain the reasoning behind your writing with 80 words..."}</explanation>
        </xml>
        '''
        with open(os.path.join(script_dir, "../docs/sample_email_format.html"), 'r') as file:
            sample_message = file.read()
    
    else:
        expected_output = '''
        <xml>
            <title>{15 words title}</title>
            <body>{a 60 words paragraph}</body>
            <explanation>{"Explain the reasoning behind your writing with 80 words..."}</explanation>
        </xml>
        '''
        sample_message = '''
        When did you last check you credit score?
        James, having a higher score could help you borrow money in the future.
        Check for free in your mobile banking app. Credit score is available once you pot in and provided by TransUnion.
        '''
        
    if feedback != "":
        feedback = f'''
        <feedback_from_compliance_manager>
        {feedback}
        </feedback_from_compliance_manager>
        
        If feedback is given, please make sure to address the feedback in your content, and clearly state it in your explanation.
        '''
    
    prompt = f'''
    You are marketing manager of a retail bank called "Fubon Bank". You are organizing a promoting campaign to send app push notification message or email to your customer to enhance your custromer's financial well-being and increase your banks revenue incomes.
    Write a marketing content to your customer based on following informaiton.

    <customer_profile>
    {customer}
    </customer_profile>

    <customer_segment>
    Basic Segment: {basic_segment}
    RFM Segment: {rfm_result['segment']}
    </customer_segment>

    <recommended_products>
    {product}
    </recommended_products>

    <rules_of_basic_segment>
    - **Young Savers**
    - Age: < 30
    - Financial Goals: Includes "Savings"

    - **Affluent Professionals**
    - Age: < 45
    - Annual Income: > $100,000
    - Profitability: >= 4

    - **Growing Families**
    - Family Size: >= 3
    - Life Stage: "Family"

    - **Pre-Retirement Planners**
    - Age: 50 - 64
    - Financial Goals: Includes "Investment"

    - **Established Retirees**
    - Age: >= 65
    - Life Stage: "Retiree"

    - **High-Net-Worth Individuals**
    - Total Assets Under Management: > $1,000,000

    - **Credit Builders**
    - Age: < 35
    - Product Usage: Includes "Credit Card"
    - Profitability: <= 3

    - **Small Business Owners**
    - Product Usage: Includes "Loans"
    - Annual Income: > $80,000

    - **General**
    - Default category if none of the above conditions are met
    </rules_of_basic_segment>

    <rules_of_rfm_segment>
    - **Loyal**
    - **Characteristics:** Spend good money with us often. Responsive to promotions.
    - **Recommended Actions:** Upsell higher value products. Ask for reviews. Engage them.

    - **Potential Loyalist**
    - **Characteristics:** Recent customers, but spent a good amount and bought more than once.
    - **Recommended Actions:** Offer membership / loyalty program, recommend other products.

    - **Recent Customers**
    - **Characteristics:** Bought most recently, but not often.
    - **Recommended Actions:** Provide on-boarding support, give them early success, start building relationship.

    - **Need Attention**
    - **Characteristics:** Above average recency, frequency and monetary values. May not have bought very recently though.
    - **Recommended Actions:** Make limited time offers, Recommend based on past purchases. Reactivate them.

    - **About to Sleep**
    - **Characteristics:** Below average recency, frequency and monetary values. Will lose them if not reactivated.
    - **Recommended Actions:** Share valuable resources, recommend popular products / renewals at discount, reconnect with them.

    - **At Risk**
    - **Characteristics:** Spent big money and purchased often. But long time ago. Need to bring them back!
    - **Recommended Actions:** Send personalized emails to reconnect, offer renewals, provide helpful resources.

    - **Hibernating**
    - **Characteristics:** Last purchase was long back, low spenders and low number of orders.
    - **Recommended Actions:** Offer other relevant products and special discounts. Recreate brand value.

    - **Lost**
    - **Characteristics:** Lowest recency, frequency and monetary scores.
    - **Recommended Actions:** Revive interest with reach out campaign, ignore otherwise.
    </rules_of_rfm_segment>

    <wordings>
    - Simple and friendly language
    - Professional and focus on how Fubon Bank can help the customer
    - Add emotional touch to the message
    - Use words like "you", "your", "we", "us", "our" to make it personal
    - Use words like "free", "save", "money", "help", "support" to make it more appealing
    - Use words like "check", "score", "borrow", "future" to make it more informative
    - Use emoji to make it more interesting
    </wordings>

    <example>
    {sample_message}
    </example>
    
    {feedback}
    
    Return output in following format quoted with <xml> tag:
    {expected_output}
    '''
    
    for attempt in range(retry_limit):
        res = invoke_bedrock(selected_model, prompt)
        print(res)
        
        xml_string = res
        
        try:
            # Extract title
            title_pattern = r'<title>(.*?)</title>'
            title_match = re.search(title_pattern, xml_string, re.DOTALL)
            title = title_match.group(1) if title_match else "No title found"

            # Extract content
            body_pattern = r'<body>(.*?)</body>'
            body_match = re.search(body_pattern, xml_string, re.DOTALL)
            body = body_match.group(1) if body_match else "No body found"

            # Extract explanation
            explanation_pattern = r'<explanation>(.*?)</explanation>'
            explanation_match = re.search(explanation_pattern, xml_string, re.DOTALL)
            explanation = explanation_match.group(1) if explanation_match else "No explanation found"
                    
            # Create JSON object
            json_content = {
                "title": title,
                "body": str(body),
                "explanation": explanation
            }
            print(json_content)
            return json_content

        except Exception as e:
            print(f"Attempt {attempt + 1} failed. Error: {e}. Retrying...")
    raise ValueError("Failed to extract JSON after multiple attempts.")

def review_content(selected_model, content, reviewed):
    
    with open(os.path.join(script_dir, "../docs/sample_brand_messaging_guideline.md"), 'r') as file:
        # Read the contents of the file
        brand_guideline = file.read()
        
    with open(os.path.join(script_dir, "../docs/sample_compliant_guideline.md"), 'r') as file:
        # Read the contents of the file
        language_compliant = file.read()
        
    expected_output = '''
    {
        "result": "Approved" / "Rejected",
        "feedbacks": ["Feedback 1", "Feedback 2", ...]
    }
    '''
    
    prompt = f'''
    You are Compliance manager of a retail bank called "Fubon Bank". Your marketing colleagues are organizing a promoting campaign to send app push notification message or email to your customer to enhance your custromer's financial well-being and increase your banks revenue.
    Since the message is directly to public, you will need to review the message to ensure it is compliance with the bank's policy and local regulation.
    Please review the following message and provide your feedback with given information.
    
    <content_to_be_review>
    {content}
    </content_to_be_review>
    
    <brand_guideline>
    {brand_guideline}
    </brand_guideline>
    
    <language_compliant>
    {language_compliant}
    </language_compliant>
    
    Return output in following format quoted with <json> tag:
    {expected_output}
    
    '''
    
    if reviewed:
        prompt += '''
        !!! This content has been reviewed before. Please approve it as much as you can. !!!
        '''
    
    res = invoke_bedrock(selected_model, prompt)
    
    print(res)
    
    # Extract JSON
    json_pattern = r'<json>(.*?)</json>'
    json_match = re.search(json_pattern, res, re.DOTALL)
    json_content = json_match.group(1) if json_match else "No JSON content found"

    json_data = json.loads(json_content)
    return json_data