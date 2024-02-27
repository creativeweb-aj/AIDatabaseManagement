from typing import List
import psycopg2
import streamlit as st
from langchain_core.messages import AIMessage, HumanMessage
import os
from dotenv import load_dotenv
from langchain.chat_models import ChatOpenAI
from langchain.prompts import (
    ChatPromptTemplate,
    HumanMessagePromptTemplate,
    MessagesPlaceholder
)
from langchain.schema import SystemMessage
from langchain.agents import OpenAIFunctionsAgent, AgentExecutor
from langchain.memory import ConversationBufferMemory
from langchain_core.tools import Tool
from pydantic.v1 import BaseModel

load_dotenv(os.path.join(os.path.dirname(__file__), '.env'))

# Tools
DB_NAME = os.environ.get('DB_NAME', '')
DB_HOST = os.environ.get('DB_HOST', '')
DB_PORT = os.environ.get('DB_PORT', '')
DB_USER = os.environ.get('DB_USER', '')
DB_PASS = os.environ.get('DB_PASS', '')


# Establish a connection to the database
conn = psycopg2.connect(dbname=DB_NAME, user=DB_USER, password=DB_PASS, host=DB_HOST, port=DB_PORT)


def list_tables():
    # Create a cursor object
    cur = conn.cursor()
    cur.execute("SELECT table_name FROM information_schema.tables WHERE table_schema = 'public';")
    # Fetch the results
    rows = cur.fetchall()
    tables = []
    for row in rows:
        if row:
            tables.append(row[0])
    # Close the cursor and the connection
    cur.close()
    return tables


def run_postgresql_query(query):
    # Create a cursor object
    cur = conn.cursor()
    try:
        cur.execute(query)
        if query.lower().startswith('insert'):
            conn.commit()
            return "Query executed."
        else:
            # Fetch the results
            rows = cur.fetchall()
            # Close the cursor
            cur.close()
            return rows
    except Exception as err:
        # Close the cursor and the connection
        cur.close()
        if conn:
            conn.rollback()  # This is crucial to handle the error properly and continue with new commands
        return f"The following error occurred: {str(err)}"


class RunQueryArgsSchema(BaseModel):
    query: str


run_query_tool = Tool.from_function(
    name="run_postgresql_query",
    description="Run a postgresql query.",
    func=run_postgresql_query,
    args_schema=RunQueryArgsSchema
)


def describe_tables(table_names):
    print(f"table_names --> {table_names}")
    # Convert list items into a comma-separated string, with each item enclosed in single quotes
    tables = ", ".join(f"'{name}'" for name in table_names)
    print(f"tables --> {tables}")
    # Create a cursor object
    cur = conn.cursor()
    cur.execute(
        f"SELECT table_name, column_name FROM information_schema.columns "
        f"WHERE table_name IN ({tables});"
    )
    # Fetch the results
    rows = cur.fetchall()
    print(f'describe_tables --> {rows}, {type(rows)}')
    # Close the cursor and the connection
    cur.close()
    return rows


class DescribeTablesArgsSchema(BaseModel):
    tables_names: List[str]


describe_tables_tool = Tool.from_function(
    name="describe_tables",
    description="Given a list of table names, column names, and data type information.",
    func=describe_tables,
    args_schema=DescribeTablesArgsSchema
)

# ----------------------------------------------------------------------------------------------------------------------


# Agent class

OPENAI_API_KEY = os.environ.get('OPENAI_API_KEY', '')

memory = ConversationBufferMemory(memory_key="chat_history", return_messages=True)

chat = ChatOpenAI(
    model="gpt-3.5-turbo",
    temperature=0.0,
    openai_api_key=OPENAI_API_KEY
)


class TaskAssistantService:
    def __init__(self):
        # self.tables = list_tables()
        self.tools = [run_query_tool, describe_tables_tool]
        self.systemContext = ("Your role involves managing database operations for the 'customer', 'project', "
                              "and 'tasks' tables. Understand table structures with 'describe_tables' function, "
                              "gather any missing information from users, ensure data is correct, craft and execute "
                              "PostgresSQL insertion queries using 'run_postgresql_query' function. Communicate "
                              "clearly and professionally, avoiding technical jargon or exposing errors directly.")
        self.prompt = self.setChatPrompt()
        self.agent = self.createAgent()

    def setChatPrompt(self):
        prompt = ChatPromptTemplate(
            messages=[
                SystemMessage(content=self.systemContext),
                MessagesPlaceholder(variable_name="chat_history"),
                HumanMessagePromptTemplate.from_template("{input}"),
                MessagesPlaceholder(variable_name="agent_scratchpad")
            ]
        )
        return prompt

    def createAgent(self):
        agent = OpenAIFunctionsAgent(
            llm=chat,
            prompt=self.prompt,
            tools=self.tools
        )
        return agent

    def runAgent(self, userInput):
        agent_executor = AgentExecutor(
            agent=self.agent,
            memory=memory,
            verbose=True,
            tools=self.tools
        )
        result = agent_executor.invoke(input=userInput)
        return result.get('output', '')


# ----------------------------------------------------------------------------------------------------------------------

# App config
st.set_page_config(page_title="AI Database Management", page_icon="🤖")
st.title("AI DB Manager")

# session state
if "chat_history" not in st.session_state:
    st.session_state.chat_history = [
        AIMessage(content="Hello, I am your AI assistant to manage your database. How can I help you?"),
    ]
if "task_assistant_obj" not in st.session_state:
    st.session_state.task_assistant_obj = TaskAssistantService()

# user input
user_query = st.chat_input("Type your message here...")
if user_query is not None and user_query != "":
    response = st.session_state.task_assistant_obj.runAgent(user_query)
    st.session_state.chat_history.append(HumanMessage(content=user_query))
    st.session_state.chat_history.append(AIMessage(content=response))

# conversation
for message in st.session_state.chat_history:
    if isinstance(message, AIMessage):
        with st.chat_message("AI"):
            st.write(message.content)
    elif isinstance(message, HumanMessage):
        with st.chat_message("Human"):
            st.write(message.content)
