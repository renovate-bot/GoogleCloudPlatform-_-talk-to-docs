class InvertedIndex:
    def build_map(self, docs):
        doc_mapping = {}
        for plan, documents in docs.items():
            texts = [x.page_content for x in documents]
            metadatas = [x.metadata for x in documents]
            docs_plan = {f"{plan}_{i}": (x, y) for i, (x, y) in enumerate(zip(texts, metadatas))}
            doc_mapping.update(docs_plan)
        return doc_mapping
    
