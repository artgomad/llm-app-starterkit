import json
from app.utils.vectorstores.Faiss import Faiss


def read_product_details(function_output, knowledge_base):

    searchQuery = function_output.get('product_name', "")

    faiss = Faiss(file_name=knowledge_base)

    all_product_info, context_for_LLM = faiss.vector_search(
        query=searchQuery, number_of_outputs=1)

    context_for_LLM = "\n\n".join(
        f"Full product information: {json.dumps(doc['metadata'], indent=2)}"
        for doc in all_product_info
    )

    print('All Product info = ')
    print(context_for_LLM)

    return all_product_info, context_for_LLM
