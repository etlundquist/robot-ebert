from llama_index.prompts import PromptTemplate, ChatPromptTemplate, PromptType


CONDENSE_QUESTION_PROMPT = PromptTemplate("""
Your goal is to interactively help the user find relevant movies based on a sequence of search queries in the form of chat messages.
Given the MESSAGE_HISTORY and CURRENT_MESSAGE below, rewrite the CURRENT_MESSAGE into a STANDALONE_QUERY that captures all relevant information from the user's messages.
The STANDALONE_QUERY should only include search/query terms from the user's messages - do not add extra search terms.
Remove search/query terms from earlier user messages that have been contradicted by later user messages so the STANDALONE_QUERY is coherent.
Your response should be optimized for submission to a semantic search query engine.

MESSAGE_HISTORY:
{chat_history}

CURRENT_MESSAGE:
{question}

STANDALONE_QUERY:
""")

TEXT_QA_PROMPT = PromptTemplate("""
Your goal is to help the user interact with a semantic search engine to find relevant movies.
The search engine matches the user's query against the following movie attributes: genres, keywords, director, actors, plot overview
The search engine has returned a list of RECOMMENDED_MOVIES based on the user's SEARCH_QUERY below.
Please respond with the following information:

1. The SEARCH_QUERY in quotation marks
2. Suggestions to further improve the user's search query

Your suggestions can include:
- asking the user to include additional keywords and/or movie attributes that the current SEARCH_QUERY does not contain
- asking the user to be more specific with parts of the current SEARCH_QUERY that are too vague or unhelpful

Your suggestions can be based on information from the RECOMMENDED_MOVIES below or your own knowledge.
Include 1-3 suggestions in your response, only including relevant suggestions that you think will improve results.
Do not include suggestions based on negations or exclusions - the search engine cannot handle these requests.

Follow the format of this example response:
```
Here are the top results for "crime drama".

To further refine your search here are some suggestions:
- narrow down the type of crime, for example "white-collor" or "mafia", to better fit your desired plot elements
- include a preference for the tone or style, such as "neo-noir" or "action-packed", to better match the atmosphere of the movie you're interested in
- specify a desired director or list of actors
```

SEARCH_QUERY:
{query_str}

RECOMMENDED_MOVIES:
{context_str}

Response:
""")
