import json
from parameters.parameters import log_files_dict
from parameters.logger import get_logger


logging = get_logger(__name__)

chatbot_log = log_files_dict["chats_log"]
conversation_log = log_files_dict["conversation_log"]
disambiguated_log = log_files_dict["disambiguated_log"]


class BedrockQueries:
    def __init__(self, bedrock_client, model_id):
        self.bedrock_client = bedrock_client
        self.model_id = model_id

    def disambiguate(self, question, conversation_history, company):
        if not conversation_history:
            conversation_history = [
                f"This is a conversation about an upcoming proxy vote for {company} or the general proxy voting process."
            ]
        conversation_history_str = "\n\n".join(conversation_history)

        system_message = "You are a customer service representative and an expert in the corporate proxy voting process.\nYour name is 'ProxyBot'."

        user_message = f"Please read the transctipt of your conversation history with this particular customer in the <CONTEXT> XML tag below. It will refer to you as 'ProxyBot'.\n"
        user_message += (
            f"Then read  the latest customer question in the <QUESTION> tag.\n"
        )
        user_message += f"\n\n<CONTEXT>\n{conversation_history_str}\n</CONTEXT>\n\n<QUESTION>\n{question}\n</QUESTION>\n\n"
        user_message += f"Disambiguate any pronouns and references in the <QUESTION> tag by using the <CONTEXT>.\n"
        user_message += f"""
        Rewrite the <QUESTION> tag in a way that makes it clear without the <CONTEXT> what is being asked, which can be used as a natural language search query to retreive infromation that is required to answer this question.
        Use entity terms that are as specific as possible, listing individuals' names and titles, listing proposal names, numbers and subject matter, etc. to give the search query the best chance of finding the relevant data based on those entity names.
        Provide examples of general terms that make sense in the context of proxy voting. For example, replacing "board memebers" with "board members (e.g. executive management team and non-executive directors  committee chairs)
        If the request is not a question, rephrase it as a quesiton based on the <CONTEXT>.
        Use only the information from the <CONTEXT> tag to do this disambiguation.
        Assume that any references to "you" refer to the system providing this information, not any particular document.
        Assume the company in question is {company} and that the convesation has to do with an upcoming proxy vote of this company's board.
        Rewrite the question using the specific language of a financial lawyer, which would closely match language used in SEC 14A documents.
        If the question relates to the general mechanics of voting, the proxy voting process, the ProxyVote app, corporate actions, shareholder influence, shareholder communcations, common types of issues, ways of voting, and reasons to vote, then prefix your answer with "General proxy voting question:".
        If the quesiton is asking for information about {company} or its proxy vote, then prefix your answer with "Specific question about upcoming proxy vote for {company}:".
        If the question is not a question but a statement that is clarifying or correcting a previous answer, then use the CONTEXT to re-generate the previous question using the new information instead.
        Return the rewritten question, wrapped in a <QUESTION> XML tags, substituting proper names and specific terms for any pronouns and references.
        Do not include any commentary before or after this tag.
        If you can't find enough information to disambiguate, then your answer should be "Instead of answering the question, please tell the user that the question was ambiguous," followed by an explanation of what you find ambiguous about it.
        """
        logging.info(f"Disambiguating question: {question}...")
        with open(disambiguated_log, "w") as log_file:
            log_file.write(
                f"########## DISAMBIGUATION PROMPT: ###############\n{user_message}"
            )
        accept = "application/json"
        contentType = "application/json"
        logging.info(f"Using model: {self.model_id}...")
        messages = [
            {"role": "user", "content": [{"type": "text", "text": user_message}]}
        ]

        prompt_config = {
            "system": system_message,
            "messages": messages,
            "max_tokens": 8000,
            "temperature": 0,
            "anthropic_version": "bedrock-2023-05-31",
            "top_k": 250,
            "top_p": 1,
            "stop_sequences": ["user:"],
        }

        body = json.dumps(prompt_config)
        bedrock_answer = self.bedrock_client.invoke_model(
            body=body, modelId=self.model_id, accept=accept, contentType=contentType
        )
        # loading in the response from bedrock
        response_body = json.loads(bedrock_answer.get("body").read())
        answer = response_body.get("content")[0].get("text")

        logging.info(f"Disambiguated question: {answer.strip()}")
        with open(disambiguated_log, "w") as log_file:
            log_file.write(
                f"########## RETURNING DISAMBIGUATED QUESTION: ###############\n{answer}"
            )
        return answer

    def get_conversation_response(
        self, disambiguated_question, answer_data, conversation_history
    ):

        conversation_history_str = "\n\n".join(conversation_history)

        system_message = """
        You are a customer service representative and an expert in the corporate proxy voting process.
        Your name is 'ProxyBot'.
        When responding, follow the guidelines below:
        1. Only use the information provided in the <INFORMATION> tag to answer the question inside <CHATBOT_USER_QUESTION>. Do not make assumptions beyond what is stated.
        2. If you cannot find the answer in the <INFORMATION> tag, say "I don't know."
        3. In additional to providing the answer, you should also provide a list of the relevant quotes.
        3. If you are asked for information that requires your personal judgement or opinion, say "That's a judgement call." and provide the relevant factual information from the <INFORMATION> tag.
        4. Include as many relevant quotes as possible, but do not repeat any quote more than once.
        5. Do not make any changes to the quoted text, except for line breaks.
        6. Return the quotes, with a bracketed citation containing the document name.
        7. Use the information in <table> tag for a structured response where needed.
        8. Do not repeat your previous answers. If you need to provide additional information, quote new relevant passages.
        9. If the answer is almost identical to your previous one, say "I don't think I understood your question. Can you please explain it in more detail?"
        10. If the <INFORMATION> tag is incomplete, list the missing items.
        11. Do not include preamble, do not summarize the answer, and do not restate the question.
        12. Do not say or use 'tag' or 'tags' in your response.
        13. Give the answer formatted with markdown, and tabulate tables in markdown where necessary.
        14. Do not return information from the <CONVERSATION_HISTORY> tag.
        15. For follow-up questions, do not repeat the question. And say "I don't know" if no answer from the <INFORMATION> tag is available.
        """

        user_message = f"Please read the transctipt of your conversation history with this particular customer in the <CONVERSATION_HISTORY> XML tag below. It will refer to you as 'ProxyBot'.\n"
        user_message += f"Then read the data that has been retrieved from the 14A document using vector search and the customer's question. The data is in the <INFORMATION> XML tag below.\n"
        user_message += f"Then read the latest customer question in the <CHATBOT_USER_QUESTION> tag.\n"
        user_message += f"\n\n<CONVERSATION_HISTORY>\n{conversation_history_str}\n</CONVERSATION_HISTORY>\n\n"
        user_message += f"\n\n<INFORMATION>\n{answer_data}\n</INFORMATION>\n\n"
        user_message += f"\n\n<CHATBOT_USER_QUESTION>\n{disambiguated_question}\n</CHATBOT_USER_QUESTION>\n\n"

        with open(chatbot_log, "w") as log_file:
            log_file.write(
                f"########## CONVERSATION PROMPT: ###############\n{user_message}"
            )

        logging.info(f"Sending conversation question: {disambiguated_question.strip()}")
        accept = "application/json"
        contentType = "application/json"
        logging.info(f"Using model: {self.model_id}...")

        messages = [
            {"role": "user", "content": [{"type": "text", "text": user_message}]}
        ]

        prompt_config = {
            "system": system_message,
            "messages": messages,
            "max_tokens": 8000,
            "temperature": 0,
            "anthropic_version": "",
            "top_k": 250,
            "top_p": 1,
            "stop_sequences": ["user:"],
        }

        body = json.dumps(prompt_config)
        bedrock_answer = self.bedrock_client.invoke_model(
            body=body, modelId=self.model_id, accept=accept, contentType=contentType
        )

        # loading in the response from bedrock
        response_body = json.loads(bedrock_answer.get("body").read())
        answer = response_body.get("content")[0].get("text")
        with open(chatbot_log, "w") as log_file:
            log_file.write(f"########## CONVERSTION ANSWER: ###############\n{answer}")
        return answer
