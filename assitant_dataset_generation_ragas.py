from assistant.multi_document_agent.personal_assitant import MultiDocumentAssistantAgentsPack
from assistant.multi_document_agent.personal_assitant import PdfFileReader
from dotenv import load_dotenv
load_dotenv(verbose=True, override=True)
import os
from langfuse.llama_index import LlamaIndexCallbackHandler
from llama_index.core.callbacks import CallbackManager
import uuid
from llama_index.core import Settings
from llama_index.llms.ollama import Ollama
from llama_index.embeddings.huggingface import HuggingFaceEmbedding
from llama_index.core.response.pprint_utils import pprint_response
from llama_index.embeddings.ollama import OllamaEmbedding
from llama_index.core.evaluation import RelevancyEvaluator
from llama_index.core.llama_dataset.generator import RagDatasetGenerator
from llama_index.core import SimpleDirectoryReader
import duckdb
import ragas
from ragas.testset.generator import TestsetGenerator
from ragas.testset.evolutions import simple, reasoning, multi_context
from llama_index.llms.openai import OpenAI
from llama_index.embeddings.openai import OpenAIEmbedding
from llama_index.core.node_parser import MarkdownNodeParser
import nltk
import spacy
from llama_index.llms.azure_openai import AzureOpenAI
from ragas.run_config import RunConfig

nltk.download('punkt_tab')
spacy.cli.download("en_core_web_md")
from llama_index.core.node_parser import (
    SemanticDoubleMergingSplitterNodeParser,
    LanguageConfig,
)
import pandas as pd

def export_nodes(nodes, table_name:str):
    nodes_content = [n.text for n in nodes]
    # Create pandas dataframe from array of strings
    nodes_df = pd.DataFrame(nodes_content, columns=["text"])

    duckdb.sql(f"CREATE TABLE {table_name} AS SELECT * FROM nodes_df")
    duckdb.sql(f"COPY (SELECT * FROM {table_name}) TO '{table_name}.parquet' (FORMAT PARQUET)")
    
ollama_base_url=os.environ['OLLAMA_BASE_URL']
pdf_images_path=os.environ['PDF_IMAGES_STORE_PATH']
docs_store_path=os.environ['DOCS_STORE_PATH']
langfuse_url = os.environ['LANGFUSE_URL']
langfuse_public_key = os.environ['LANGFUSE_PUBLIC_KEY']
langfuse_secret_key = os.environ['LANGFUSE_SECRET_KEY']
storage_dir = os.environ['STORAGE_DIR']
openai_api_version=os.getenv('OPENAI_API_VERSION')
azure_openai_endpoint=os.getenv('AZURE_OPENAI_ENDPOINT','https://ai-proxy.lab.epam.com')
azure_openai_api_key=os.getenv('AZURE_OPENAI_API_KEY')
azure_openai_model=os.getenv('AZURE_OPENAI_MODEL')
evaluation_ds = os.getenv('EVALUATION_DS')
#Configure 
session_id = str(uuid.uuid4())
print(f"Session_id: {session_id}")
print(f"Ollama Url: {ollama_base_url}")
print(f"Langfuse Url: {langfuse_url}")

langfuse_callback_handler = LlamaIndexCallbackHandler(
    public_key=langfuse_public_key,
    secret_key=langfuse_secret_key,
    host=langfuse_url,
    session_id=session_id,
    debug=False,
)
#Settings.callback_manager = CallbackManager([langfuse_callback_handler])
ollama = Ollama(model="llama3.1:8b", request_timeout=120.0, base_url=ollama_base_url, 
                is_function_calling_model=True)

ollama_agent = Ollama(model="llama3.2:latest", request_timeout=240.0, base_url=ollama_base_url, 
                is_function_calling_model=True)
embed_model = OllamaEmbedding(model_name="bge-m3", request_timeout=240.0, base_url=ollama_base_url)
#nvidia = NVIDIA(model="meta/llama-3.1-70b-instruct")
#critic_llm = OpenAI(model="gpt-4-turbo")
#critic_llm = Ollama(model="mistral-nemo:latest", request_timeout=240.0, base_url=ollama_base_url)

azurellm = AzureOpenAI(
    engine=azure_openai_model,
    model=azure_openai_model,
    api_key=azure_openai_api_key,
    azure_endpoint=azure_openai_endpoint,
    api_version=openai_api_version,
)

critic_llm = azurellm
Settings.llm = azurellm
Settings.embed_model = embed_model
print(f"Folder with documents:{docs_store_path}")
file_extractor={".pdf": PdfFileReader(pdf_images_path, page_chunks=True)}
#reader = SimpleDirectoryReader(input_dir=docs_store_path, num_files_limit=10, file_extractor=file_extractor)
reader = SimpleDirectoryReader(input_dir=docs_store_path, num_files_limit=10, file_extractor=file_extractor)            
documents = reader.load_data(show_progress=True)

#Download model python3 -m spacy download en_core_web_md
config = LanguageConfig(language="english", spacy_model="en_core_web_md")
from llama_index.core.node_parser import SentenceSplitter
parser = MarkdownNodeParser()

markdown_pages = parser.get_nodes_from_documents(documents)

sentence_splitter = SentenceSplitter(
    chunk_size=2000,
    chunk_overlap=200,
)

splitter = SemanticDoubleMergingSplitterNodeParser(
    language_config=config,
    initial_threshold=0.4,
    appending_threshold=0.6,
    merging_threshold=0.6,
    max_chunk_size=3000,
    merging_range=3,
    splitter=[sentence_splitter]
)
nodes = splitter.get_nodes_from_documents(markdown_pages)
#nodes = splitter.get_nodes_from_documents(documents)
export_nodes(documents, "documents")
export_nodes(markdown_pages, "markdown_pages")
export_nodes(nodes, "nodes_text")

runConfig = RunConfig()
runConfig.max_workers = 4

generator = TestsetGenerator.from_llama_index(
    generator_llm=critic_llm,
    critic_llm=critic_llm,
    embeddings=embed_model,
    run_config=runConfig
)
# generate testset
def generate_eval_test(nodes, evaluation_ds=evaluation_ds):
    runConfig2 = RunConfig()
    runConfig2.max_workers = 4
    
    eval_testset = generator.generate_with_llamaindex_docs(
        nodes,
        test_size=100,
        distributions={simple: 0.3, reasoning: 0.40, multi_context: 0.30},
        with_debugging_logs=True,
        is_async=True,
        run_config=runConfig2
    )
    eval_questions_df = eval_testset.to_pandas()
    duckdb.sql("CREATE TABLE eval_data AS SELECT * FROM eval_questions_df")
    duckdb.sql("INSERT INTO eval_data SELECT * FROM eval_questions_df")
    duckdb.sql(f"COPY (SELECT * FROM eval_data) TO '{evaluation_ds}' (FORMAT PARQUET)")
    return eval_questions_df

generated_quesries = generate_eval_test(nodes, evaluation_ds)