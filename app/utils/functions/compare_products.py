from app.utils.vectorstores.Faiss import Faiss


def compare_products(function_output, knowledge_base, context):

    searchQuery = function_output.get('product_name', "")

    field = function_output.get('field', "")
    search_terms = function_output.get('search_terms', [])

    faiss = Faiss(file_name=knowledge_base)

    all_product_info, context_for_LLM = faiss.searchByField(
        field, search_terms)

    # If the search fails we make sure to pass the context to the next LLM call
    if not context_for_LLM:
        context_for_LLM = context

    return all_product_info, context_for_LLM
