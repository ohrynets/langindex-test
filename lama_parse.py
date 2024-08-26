from dotenv import load_dotenv
load_dotenv()
from llama_index.core.agent import ReActAgent
from llama_index.llms.openai import OpenAI
from llama_index.core.tools import FunctionTool
from llama_index.core import SimpleDirectoryReader, VectorStoreIndex, Settings
from llama_index.llms.ollama import Ollama
import os
from llama_index.core import SimpleDirectoryReader
from llama_index.core.readers.base import BaseReader
from llama_index.core import Document
import pymupdf4llm
from llama_index.embeddings.ollama import OllamaEmbedding
from llama_index.core import VectorStoreIndex
import nest_asyncio
from llama_index.embeddings.huggingface import HuggingFaceEmbedding
from chromadb.utils.embedding_functions import OpenCLIPEmbeddingFunction
from llama_index.core.indices import MultiModalVectorStoreIndex
from llama_index.vector_stores.qdrant import QdrantVectorStore
from llama_index.core import SimpleDirectoryReader, StorageContext
from chromadb.utils.data_loaders import ImageLoader
import chromadb
from llama_index.core.node_parser.file.markdown import MarkdownNodeParser

# set defalut text and image embedding functions
embedding_function = OpenCLIPEmbeddingFunction()
nest_asyncio.apply()
mrkdown_parser = MarkdownNodeParser()
class PdfFileReader(BaseReader):

    def load_data(self, file, extra_info={}):
        md_content = pymupdf4llm.to_markdown(file, write_images=True, page_chunks=True, image_path="pdf_images/")
        # load_data returns a list of Document objects
        nodes = []
        for d in md_content:
            res = mrkdown_parser.aget_nodes_from_documents(d)
            for n in res:
                print(n)
            doc_id = f"{d['metadata']['title']}:{d['metadata']['page']}"
            doc = Document(text=d['text'], id_=doc_id, extra_info={**extra_info, **d['metadata']})
            nodes.append(doc)
        return nodes

# settings

#print(f"OLLAMA_BASE_URL:{ollama_base_url}")
#Settings.llm = OpenAI(model="gpt-3.5-turbo", temperature=0)
ollama_base_url=os.environ['OLLAMA_BASE_URL']
ollama = Ollama(model="llama3.1:8b", request_timeout=120.0, base_url=ollama_base_url)
ollama_embeding = OllamaEmbedding(model_name="nomic-embed-text", request_timeout=120.0, base_url=ollama_base_url, ollama_additional_kwargs={"mirostat": 0},)
hf_embed_model = HuggingFaceEmbedding(model_name="BAAI/bge-small-en-v1.5")
Settings.llm = ollama
Settings.embed_model = hf_embed_model
#Settings.llm = OpenAI(model="gpt-3.5-turbo", temperature=0)
# set up parser

# use SimpleDirectoryReader to parse our file
file_extractor={".pdf": PdfFileReader()}
# rag pipeline

# load it again to confirm it worked
from llama_index.core import StorageContext, load_index_from_storage



image_loader = ImageLoader()

# create client and a new collection
chroma_client = chromadb.EphemeralClient()
chroma_collection = chroma_client.create_collection(
    "multimodal_collection",
    embedding_function=embedding_function,
    data_loader=image_loader,
)

#if directory exists, load the index from storage
if os.path.exists("./storage"):
    index = load_index_from_storage(
        StorageContext.from_defaults(persist_dir="./storage")
    )
else:
    reader = SimpleDirectoryReader(input_dir="/mnt/docs", file_extractor=file_extractor).load_data(show_progress=True)
    index = VectorStoreIndex.from_documents(reader, show_progress=True)
    print("ref_docs ingested: ", len(index.ref_doc_info))
    print("number of input documents: ", len(reader))    
    # save the initial index
    index.storage_context.persist(persist_dir="./storage")

# Check if embedding model is loaded correctly
print(index.summary)
    
retriever = index.as_retriever(verbose=True)
response = retriever.retrieve("new neighbor behaved churlishly ")
for res in response:
    print(res.text)
