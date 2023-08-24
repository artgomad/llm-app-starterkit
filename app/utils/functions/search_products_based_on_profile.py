import json
from app.utils.vectorstores.Faiss import Faiss


def search_products_based_on_profile(customer_profile_update, knowledge_base, score_threshold):

    searchQuery = json.dumps(customer_profile_update)

    faiss = Faiss(file_name=knowledge_base)

    all_product_info, context_for_LLM = faiss.vector_search(
        query=searchQuery, number_of_outputs=5)

    print("score_threshold")
    print(score_threshold)

    context_for_LLM = "\n\n".join(
        f"Full product information: {json.dumps(doc['metadata'], indent=2)}"
        for doc in all_product_info
    )

    print('context_for_LLM = ')
    print(context_for_LLM)

    # Remove all the products with a score higher than 0.5
    all_product_info = [
        doc for doc in all_product_info if doc['metadata']['score'] < score_threshold]

    print("filtered products")
    print(all_product_info)

    return all_product_info, context_for_LLM
