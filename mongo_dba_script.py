import os
import google.generativeai as genai
from dotenv import load_dotenv
import streamlit as st
import pymongo
import pandas as pd
import matplotlib.pyplot as plt
import json



## Load environment variables
load_dotenv()

GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')
# MongoDB connection details
MONGO_TEST_URL = os.getenv('MONGO_TEST_URL')
MONGO_PROD_URL = os.getenv('MONGO_PROD_URL')


# Configure Google Gemini API
genai.configure(api_key=GEMINI_API_KEY)

# Choose a Gemini model.



# Initialize MongoDB client
def get_mongo_client(instance):
    if instance == "test":
        return pymongo.MongoClient(MONGO_TEST_URL)
    elif instance == "prod":
        return pymongo.MongoClient(MONGO_PROD_URL)
    else:
        raise ValueError("Invalid instance type. Use 'test' or 'prod'.")
    
def get_database_schema(db):
    schema = {}
    for collection_name in db.list_collection_names():
        collection = db[collection_name]
        document = collection.find_one(projection={"_id": 0})
        if document:
            schema[collection_name] = list(document.keys())
    return schema

def extract_json(llm_response):
  """
  Extracts the JSON part from an LLM response enclosed between ```json and ```.

  Args:
    llm_response: The LLM response string.

  Returns:
    The extracted JSON string, or None if no JSON is found.
  """
  try:
    start_index = llm_response.index("```json") + len("```json")
    end_index = llm_response.index("```", start_index)
    json_str = llm_response[start_index:end_index].strip()
    return json.loads(json_str)  # Parse the JSON string
  except ValueError:
    return None  # No JSON found or invalid JSON
  

def extract_python(llm_response):
  """
  Extracts the python part from an LLM response enclosed between ```python and ```.

  Args:
    llm_response: The LLM response string.

  Returns:
    The extracted python, or None if no python is found.
  """
  try:
    start_index = llm_response.index("```python") + len("```python")
    end_index = llm_response.index("```", start_index)
    python_str = llm_response[start_index:end_index].strip()
    return python_str  # Parse the JSON string
  except ValueError:
    return None

# Function to convert natural language query to MongoDB query using Gemini
def generate_mongo_query(natural_language_query, db, collection):
    
    sys_instr_mongo = """ You are an expert Senior Data engineer with expertise in MongoDB and PyMongo. You will be given the mongoDB database name, collection name as well as the database schema. 
    The database is of the application mapping research and hold many relevant application data like user data, user behaviour and many more.
    The user will ask a question related to the data in the collection. The name of the collection(given to you) should give you some hint on the type of data that is being asked of. Like, 'users' 
    hold registered users data from the applpication. Be mindful of the field names so that the query uses correct names. You can get the proper list of fields from the database schemaprovided to you. 
    You should return the python code that uses pymongo to query the database according to the user's request. 
    All the necessary libraries are imported, and also the mongo client connections are made. So DO NOT include the mongo client connection or library import code. You can start the code from here-
    `db = client["mongoDB"]
    collection = db[collection_name]` 

    The code should: 
    1) Perform the query or aggregation required.
    2) Print the results
    3) Store the final results under a variable named `final_df`
    4) There should not be any other output other than `final_df`

    Make sure the code is valid Python. 
    Do NOT include anything else other than the code.
    """

    model = genai.GenerativeModel(model_name="gemini-2.0-flash-exp",system_instruction=sys_instr_mongo)
    schema = get_database_schema(db)
    prompt = f"""The user query is - {natural_language_query}
            The database name is {db} & the collection name is {collection}
            The data base schema is - {schema}
    """
    response = model.generate_content(contents=prompt)
    #query = json.loads(response.text) 
    return response.text

# # Function to execute code
def execute_mongo_code(code_snippet, client, db, collection):
    """
    Executes a Python code snippet that presumably uses the global 'collection' variable.
    We'll define a local namespace that the code is executed in,
    so it can safely set a 'final_df' variable there.
    """
    safe_builtins = {
        "list": list,
        "dict": dict,
        "bool": bool,
        "str": str,
        "int": int,
        "print":print
        # etc., add what is needed
    }
    local_vars = {
        "client": client,
        "db": db,
        "collection": collection,
        "results": None
    }

    try:
        # Evaluate in a restricted environment (disable built-ins, etc.)
        exec(code_snippet, {}, local_vars)
        # The snippet is expected to set local_vars["results"] to the final data
        return local_vars.get("final_df")
    except Exception as e:
        print(f"Error executing code: {str(e)}")
        return None

  

# # Function to convert natural language query to Python code for chart generation using Gemini
# def generate_chart_code(natural_language_query, dataframe):
#     prompt = f"Generate Python code using matplotlib to create a chart based on the following natural language query and the given pandas DataFrame:\n\nQuery: {natural_language_query}\n\nDataFrame:\n{dataframe.head()}\n\nReturn only the Python code."
#     response = model.generate_content(prompt)
#     return response.text

# Streamlit app
def main():
    st.title("MongoDB Query and Visualization App")

    # Sidebar for instance selection
    instance = st.sidebar.selectbox("Select Instance", ["test", "prod"])
    client = get_mongo_client(instance)

    # Input for database and collection names
    db_name = st.selectbox("Enter Database Name",options=client.list_database_names())


    if db_name:
        db = client[db_name]
        collection_name = st.selectbox("Enter Collection Name", options=db.list_collection_names())
        if collection_name:
            collection = db[collection_name]

        
            # Input for natural language query
            query = st.text_input("Enter your query in natural language")

            if query:
                try:
                    # Generate MongoDB query
                    result = generate_mongo_query(query, db, collection)
                    print(result)
                    final_df = execute_mongo_code(extract_python(result),client, db, collection)
                    
                    st.write(final_df)

                    #     # # Chart generation
                    #     # chart_query = st.text_input("Enter a natural language query to generate a chart")
                    #     # if chart_query:
                    #     #     try:
                    #     #         chart_code = generate_chart_code(chart_query, df)
                    #     #         st.write(f"Generated Chart Code: `{chart_code}`")

                    #     #         # Execute chart code
                    #     #         exec(chart_code)
                    #     #         st.pyplot(plt)
                    #     #     except Exception as e:
                    #     #         st.error(f"Error generating chart: {e}")
                    # else:
                    #     st.warning("No data found for the given query.")
                except Exception as e:
                    st.error(f"Error executing query: {e}")

if __name__ == "__main__":
    main()