import openai
import json
import os
import stockinfo

class GPTlib():
    def __init__(self, history_max=16):
        openai.api_key = os.getenv('OPENAI_API_KEY')
        self.history = []
        self.history_max = history_max
        self.system_prompt = """
        You give information about stocks.  You can look up the ticker symbol stocks,
        or you can give quotes for stocks.  You use the functions lookup_ticker to convert
        company names into ticker symbols, and get_quote to retrieve the latest pricing
        information about a stock.
        
        You do not answer questions about any other subject.
        """

        self.funcs = [
            {
                "name": "lookup_ticker",
                "description": """Use this function to find the ticker symbol for a company""",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "company": {
                            "type": "string",
                            "description": 'The name of the company to look up the ticker symbol for',
                        }
                    },
                    "required": ["company"],
                },
            },
            {
                "name": "get_quote",
                "description": 'This function returns the current pricing information (i.e., quote) for a given stock given its ticker symbol',
                "parameters": {
                    "type": "object",
                    "properties": {
                        "ticker": {
                            "type": "string",
                            "description": 'The ticker symbol of the company to look up',
                        }
                    },
                    "required": ["ticker"],
                },
            },
        ]

    def execute_function_call(self,message):
        if message["function_call"]["name"] == "lookup_ticker":
            company = json.loads(message["function_call"]["arguments"])["company"]
            return stockinfo.lookup_ticker(company)
        elif message["function_call"]["name"] == "get_quote":
            ticker = json.loads(message["function_call"]["arguments"])["ticker"]
            return stockinfo.get_quote(ticker)
        else:
            results = f"Error: function {message['function_call']['name']} does not exist"
        return results

    def call_gpt(self,messages):
        p_model = "gpt-3.5-turbo"
        p_temperature = 0.0

        try:
            resp = openai.ChatCompletion.create(model=p_model, temperature=p_temperature, messages=messages,
                                                functions=self.funcs)
        except openai.error.ServiceUnavailableError:
            resp = {
                "choices": [{
                    "index": 0,
                    "message": {
                        "role": "assistant",
                        "content": "I'm very sorry, but OpenAI is overloaded at the moment.  Please ask again",
                    },
                    "finish_reason": "stop"
                }]
            }

        return resp

    def call_gpt_handle_functions(self, inbound_message):

        if inbound_message[-1]["role"] == "user":
            print(f'--To-GPT--> {inbound_message[-1]["content"]}')
        else:
            print(f'--To-GPT--> {inbound_message[-1]["name"]} returned {inbound_message[-1]["content"]}')

        #   Step 1: call GPT ...
        response = self.call_gpt(inbound_message)

        #   Step 2: is this a regular response (ie, not a function_call)
        message = response["choices"][0]["message"]

        if message.get("function_call") is None:
            print(f'<---Back--- {str(message["content"])}')
            return response

        # Step 3: Handle a function call

        #   Generate a summary of the function call data (to keep history as small as possible)
        short_resp = {
                    "role": "assistant",
                    "content": None,
                    "function_call": {
                        "name": message["function_call"]["name"],
                        "arguments": message["function_call"]["arguments"]
                    }
                }

        fargs = message["function_call"]["arguments"].replace("\n","")
        print(f'<---Back--- {message["function_call"]["name"]}({fargs})')

        # Save it in our history as well as current working structure for later
        self.history.append(short_resp)
        inbound_message.append(short_resp)

        # Perform the function call
        results = self.execute_function_call(message)

        # Generate the entry in the history for the response
        func_results = {"role": "function", "name": message["function_call"]["name"], "content": results}

        # Add the response of the function call to the history
        self.history.append(func_results)

        # Add it to our next call too
        inbound_message.append(func_results)

        # And now (tail-) recurse to either get a response or yet another function call (it happens!)
        return self.call_gpt_handle_functions(inbound_message)

    # This is the main entry point where we have some text we want to feed to a gpt completion
    def ask_gpt(self,user):

        # Append the new message to our history; this will add it to the outbound request too
        self.history.append({"role": "user", "content": user})

        # Build up the messages structure for GPT
        messages = [{"role": "system", "content": self.system_prompt}]

        # Add in what's gone on before (and our latest user question)
        for h in self.history:
            messages.append(h)

        # When this returns, we're guaranteed a non-function call response
        # as all intermediate function work has been handled.
        response = self.call_gpt_handle_functions(messages)

        answer = response.choices[0].message["content"]
        self.history.append({"role": "assistant", "content": answer})

        # Trim back our history
        self.history = self.history[-self.history_max:]

        return answer
