import datetime
from parameters.logger import get_logger
from data_pipeline.search import get_index_response
from awsmanager.bedrock import bedrock_client
from logics.aossqueries import BedrockQueries
from parameters.parameters import (
    log_files_dict,
    ticker_dict,
    aoss_parameters_dict,
    local_run,
)


logging = get_logger(__name__)

chatbot_log = log_files_dict["chats_log"]
conversation_log = log_files_dict["conversation_log"]
disambiguated_log = log_files_dict["disambiguated_log"]
answer_timing_log = log_files_dict["answer_timing_log"]


class RagBot:
    def __init__(self):
        self.conversation_history = []
        self.separator_chatbot = f"{'-'*40} PROXY BOT:"
        self.separator_user = f"{'-'*40} USER:"

    def query(self, user_input, date, company, model_id):
        start_time = datetime.datetime.now()
        bedrock_queries = BedrockQueries(bedrock_client, model_id)
        disambiguated_question = bedrock_queries.disambiguate(
            user_input, self.conversation_history, company
        )
        disambiguate_time = datetime.datetime.now()
        context, source, index_response = get_index_response(
            disambiguated_question,
            date,
            ticker=ticker_dict[company],
            local_run=local_run,
            search_size=aoss_parameters_dict["search_size"],
        )
        logging.info(f"CONTEXT: {context}")
        answer_data = context
        retreive_time = datetime.datetime.now()
        with open(chatbot_log, "w") as log_file:
            log_file.write(f"{self.separator_user}{user_input}")
        with open(conversation_log, "w") as conversation_log_file:
            if answer_data:
                response = bedrock_queries.get_conversation_response(
                    disambiguated_question, answer_data, self.conversation_history
                )
                question_answer_internal = f"{self.separator_user}{user_input}\n(WHICH I UNDERSTAND TO MEAN: {disambiguated_question})\n{self.separator_chatbot}{response}"
                question_answer_external = f"{self.separator_user}{user_input}\n{self.separator_chatbot}{response}"
                self.conversation_history.append(question_answer_external)
                conversation_log_file.write(question_answer_internal)
                answer_time = datetime.datetime.now()
                seconds_to_disambiguate = (disambiguate_time - start_time).seconds
                seconds_to_retreive = (retreive_time - disambiguate_time).seconds
                seconds_to_summarize = (answer_time - retreive_time).seconds
                seconds_total = (answer_time - start_time).seconds
                timing = f"\TOTAL TIME: {seconds_total} SECONDS; DISAMBIGUATION TOOK {seconds_to_disambiguate} SECONDS; RETREIVAL TOOK {seconds_to_retreive} SECONDS; SUMMARIZATION TOOK {seconds_to_summarize} SECONDS"
                print(timing)
                conversation_log_file.write(timing)
                with open(answer_timing_log, "a") as log_file:
                    log_file.write(
                        f'{datetime.datetime.now()},{seconds_total},{seconds_to_disambiguate},{seconds_to_retreive},{seconds_to_summarize},"{user_input}"","{disambiguated_question}"'
                    )
            else:
                response = "No information found on query in provided documents."
                source = ["No source info."]
                index_response = "No index response."
        answer_payload = {
            "answer": response,
            "source": source,
            "index_response": index_response,
        }
        return answer_payload

    def greeting(self):
        return "Hello! I'm ProxyBot. What would you like to know about this vote or the proxy voting process in general?"
