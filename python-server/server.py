import os
import gc
import numpy as np
import torch
import math
import logging
import argparse
import json
from flask import Flask, request, jsonify
from tqdm import tqdm
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from datasets import load_dataset

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class BM25Retriever:
    def __init__(self, corpus, k1=1.5, b=0.75, epsilon=0.25):
        """
        Initialize the BM25 retriever

        Args:
            corpus: List of documents, where each document is a list of tokens
            k1: Term frequency saturation parameter
            b: Document length normalization parameter
            epsilon: Smoothing parameter
        """
        self.corpus = corpus
        self.k1 = k1
        self.b = b
        self.epsilon = epsilon
        self.corpus_size = len(corpus)

        # Calculate document lengths and average document length
        self.doc_lengths = [len(doc) for doc in corpus]
        self.avg_doc_length = sum(self.doc_lengths) / self.corpus_size if self.corpus_size > 0 else 0

        # Calculate term frequencies in documents
        self.term_frequencies = {}
        for doc_id, doc in enumerate(corpus):
            for term in doc:
                if term not in self.term_frequencies:
                    self.term_frequencies[term] = {}
                if doc_id not in self.term_frequencies[term]:
                    self.term_frequencies[term][doc_id] = 0
                self.term_frequencies[term][doc_id] += 1

        # Calculate document frequencies for each term
        self.doc_frequencies = {term: len(docs) for term, docs in self.term_frequencies.items()}

        # Calculate IDF (Inverse Document Frequency) with smoothing
        self.idf = {term: math.log(1 + (self.corpus_size - freq + 0.5) / (freq + 0.5))
                    for term, freq in self.doc_frequencies.items()}

        logger.info(f"BM25: Indexed {len(corpus)} documents with {len(self.term_frequencies)} unique terms")

    def get_scores(self, query):
        """
        Calculate BM25 scores for a query against all documents

        Args:
            query: List of tokens representing the query

        Returns:
            numpy array of BM25 scores for each document
        """
        scores = np.zeros(self.corpus_size)

        for term in query:
            if term not in self.term_frequencies:
                continue

            term_idf = self.idf.get(term, 0)

            for doc_id, freq in self.term_frequencies[term].items():
                doc_length = self.doc_lengths[doc_id]
                numerator = freq * (self.k1 + 1)
                denominator = freq + self.k1 * (1 - self.b + self.b * doc_length / self.avg_doc_length)
                scores[doc_id] += term_idf * (numerator / denominator)

        return scores

    def get_top_k(self, query, k=100):
        """
        Get the top k documents for a given query

        Args:
            query: List of tokens representing the query
            k: Number of top documents to return

        Returns:
            Tuple of (document indices, scores) for top k documents
        """
        scores = self.get_scores(query)
        top_k = min(k, len(scores))

        # Get indices of top k scores
        top_indices = np.argsort(scores)[::-1][:top_k]
        top_scores = scores[top_indices]

        return top_indices, top_scores


class CosineSimRetriever:
    def __init__(self, corpus):
        """
        Initialize the cosine similarity retriever

        Args:
            corpus: List of documents, where each document is a list of tokens.
        """
        self.corpus = corpus

        # Use GPU if available
        self.device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
        if self.device.type == 'cpu':
            logger.info("Using CPU for cosine similarity calculations")
        else:
            logger.info(f"Using GPU for cosine similarity: {torch.cuda.get_device_name(0)}")

        # Convert tokenized documents to strings for TfidfVectorizer
        corpus_texts = [' '.join(doc) for doc in corpus]

        # Initialize TF-IDF feature vector with optimized parameters
        self.vectorizer = TfidfVectorizer(
            min_df=2,
            max_df=0.85,
            sublinear_tf=True,
            norm='l2',
            ngram_range=(1, 2)  # Include both unigrams and bigrams
        )

        # Fit TF-IDF vectorizer on corpus
        self.document_vectors = self.vectorizer.fit_transform(corpus_texts)

        num_features = len(self.vectorizer.get_feature_names_out())
        logger.info(f"Cosine: Vectorized {len(corpus)} documents with {num_features} features")

    def get_scores(self, query, doc_indices=None):
        """
        Calculate cosine similarity scores for a query

        Args:
            query: List of tokens representing the query.
            doc_indices: Optional indices of documents to score (for reranking).

        Returns:
            Numpy array with similarity scores.
        """
        query_text = ' '.join(query)
        query_vector = self.vectorizer.transform([query_text])

        if doc_indices is not None:
            # Only calculate similarities for specified document indices (for reranking)
            doc_vectors = self.document_vectors[doc_indices]
            similarities = cosine_similarity(query_vector, doc_vectors).flatten()
            return similarities
        else:
            # Calculate similarities for all documents
            similarities = cosine_similarity(query_vector, self.document_vectors).flatten()
            return similarities


class BM25CosineReranker:
    def __init__(self, corpus, bm25_k1=1.5, bm25_b=0.75, rerank_count=100):
        """
        Initialize BM25 + Cosine similarity reranker

        Args:
            corpus: List of documents, where each document is a list of tokens
            bm25_k1: Term frequency saturation parameter for BM25
            bm25_b: Document length normalization parameter for BM25
            rerank_count: Number of top BM25 candidates to re-rank with cosine similarity
        """
        self.bm25_retriever = BM25Retriever(corpus, k1=bm25_k1, b=bm25_b)
        self.cosine_retriever = CosineSimRetriever(corpus)
        self.rerank_count = rerank_count
        logger.info(f"Will re-rank top {rerank_count} BM25 results using cosine similarity")

    def retrieve(self, query, alpha=0.5, top_k=10):
        """
        Retrieve and rerank documents for a query using a weighted combination
        of BM25 and cosine similarity scores

        Args:
            query: List of tokens representing the query
            alpha: Weight for BM25 score (1-alpha will be weight for cosine score)
            top_k: Number of top results to return

        Returns:
            Tuple of (reranked document indices, reranked scores)
        """
        # Step 1: Get top-k documents from BM25
        bm25_indices, bm25_scores = self.bm25_retriever.get_top_k(query, k=self.rerank_count)

        # Step 2: Get cosine similarity scores for these documents
        cosine_scores = self.cosine_retriever.get_scores(query, bm25_indices)

        # Step 3: Normalize both sets of scores to [0,1] range
        if len(bm25_scores) > 0:
            bm25_max = np.max(bm25_scores) if np.max(bm25_scores) > 0 else 1
            bm25_scores_norm = bm25_scores / bm25_max
        else:
            bm25_scores_norm = bm25_scores

        if len(cosine_scores) > 0:
            cosine_max = np.max(cosine_scores) if np.max(cosine_scores) > 0 else 1
            cosine_scores_norm = cosine_scores / cosine_max
        else:
            cosine_scores_norm = cosine_scores

        # Step 4: Combine the normalized scores with the weighting parameter
        combined_scores = alpha * bm25_scores_norm + (1 - alpha) * cosine_scores_norm

        # Step 5: Rerank based on combined scores
        rerank_order = np.argsort(combined_scores)[::-1]
        reranked_indices = bm25_indices[rerank_order]
        reranked_scores = combined_scores[rerank_order]

        # Return only the top_k results
        return reranked_indices[:top_k], reranked_scores[:top_k]


class MSMarcoSearchEngine:
    def __init__(self, sample_size=10000, cache_dir=None):
        """
        Initialize the MS MARCO search engine
        
        Args:
            sample_size: Number of passages to load from MS MARCO dataset
            cache_dir: Directory to cache the dataset
        """
        self.sample_size = sample_size
        self.cache_dir = cache_dir
        self.documents = []  # List of tokenized documents
        self.doc_metadata = []  # Metadata for each document
        
        # Load MS MARCO dataset
        self.load_msmarco_dataset()
        
        # Initialize the reranker
        self.reranker = BM25CosineReranker(
            self.documents,
            bm25_k1=1.5,
            bm25_b=0.75,
            rerank_count=100
        )
    
    def load_msmarco_dataset(self):
        """Load and preprocess the MS MARCO dataset"""
        logger.info(f"Loading MS MARCO dataset (sample size: {self.sample_size})...")
        
        try:
            # Load dataset from Hugging Face
            dataset = load_dataset("ms_marco", "v2.1", split=f"train[:{self.sample_size}]", cache_dir=self.cache_dir)
            
            # Process the dataset
            for i, item in enumerate(tqdm(dataset, desc="Processing MS MARCO passages")):
                # Extract all passages from each item
                for j, passage in enumerate(item['passages']['passage_text']):
                    passage_id = f"{item['query_id']}_{j}"
                    
                    # Tokenize passage (lowercase and split)
                    tokens = passage.lower().split()
                    
                    if tokens:  # Skip empty passages
                        self.documents.append(tokens)
                        
                        # Store metadata
                        self.doc_metadata.append({
                            'id': passage_id,
                            'query_id': item['query_id'],
                            'query': item['query'],
                            'passage': passage,
                            'is_selected': item['passages']['is_selected'][j]
                        })
            
            logger.info(f"Loaded {len(self.documents)} passages from MS MARCO dataset")
            
        except Exception as e:
            logger.error(f"Error loading MS MARCO dataset: {str(e)}")
            raise
    
    def search(self, query_text, top_k=10, alpha=0.5):
        """
        Search for documents matching the query
        
        Args:
            query_text: The search query text
            top_k: Number of top results to return
            alpha: Weight for BM25 score vs cosine score
            
        Returns:
            List of search results with document information and scores
        """
        # Tokenize the query
        query_tokens = query_text.lower().split()
        
        # Get top documents using the reranker
        top_indices, scores = self.reranker.retrieve(query_tokens, alpha=alpha, top_k=top_k)
        
        # Prepare search results
        results = []
        for i, (idx, score) in enumerate(zip(top_indices, scores)):
            doc_info = self.doc_metadata[idx]
            results.append({
                'rank': i + 1,
                'id': doc_info['id'],
                'query_id': doc_info['query_id'],
                'score': float(score),
                'passage': doc_info['passage'],
                'is_selected': bool(doc_info['is_selected'])
            })
        
        return results


# Create Flask app
app = Flask(__name__)

# Global search engine instance
search_engine = None

@app.route('/search', methods=['GET'])
def search():
    """Handle search requests"""
    query = request.args.get('q', '')
    top_k = int(request.args.get('k', 10))
    alpha = float(request.args.get('alpha', 0.5))
    
    if not query:
        return jsonify({'error': 'Query parameter "q" is required'}), 400
    
    try:
        results = search_engine.search(query, top_k=top_k, alpha=alpha)
        return jsonify({
            'query': query,
            'results_count': len(results),
            'results': results
        })
    except Exception as e:
        logger.error(f"Search error: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/health', methods=['GET'])
def health():
    """Health check endpoint"""
    return jsonify({
        'status': 'ok', 
        'document_count': len(search_engine.documents) if search_engine else 0
    })

def main():
    parser = argparse.ArgumentParser(description='MS MARCO Search Server')
    parser.add_argument('--port', type=int, default=5000, help='Port to run the server on')
    parser.add_argument('--host', type=str, default='0.0.0.0', help='Host to run the server on')
    parser.add_argument('--sample-size', type=int, default=10000, help='Number of MS MARCO passages to load')
    parser.add_argument('--cache-dir', type=str, default=None, help='Directory to cache the dataset')
    args = parser.parse_args()
    
    global search_engine
    
    # Initialize search engine
    try:
        logger.info("Initializing MS MARCO search engine...")
        search_engine = MSMarcoSearchEngine(sample_size=args.sample_size, cache_dir=args.cache_dir)
        
        # Check if documents were loaded
        if not search_engine.documents:
            logger.error("No documents were loaded. Exiting.")
            return
        
        # Start the Flask server
        logger.info(f"Starting server on {args.host}:{args.port}")
        app.run(host=args.host, port=args.port, debug=False)
    except Exception as e:
        logger.error(f"Error initializing search engine: {str(e)}")
        raise

if __name__ == "__main__":
    main()