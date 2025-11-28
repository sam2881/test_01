# #!/usr/bin/env python3
"""
3-Cluster BERTopic Analyzer for Domain Classification
Implements STEP 1 of enhanced workflow:
- Cluster A: ServiceNow/ITSM incidents
- Cluster B: Jira/DevOps/Development tasks
- Cluster C: Data/ETL/Platform issues
"""
import json
import os
import pickle
from typing import List, Dict, Tuple
import pandas as pd
import numpy as np
from bertopic import BERTopic
from sentence_transformers import SentenceTransformer
from sklearn.cluster import KMeans
from umap import UMAP
import structlog

logger = structlog.get_logger()


class ThreeClusterAnalyzer:
    """
    Enhanced BERTopic analyzer that enforces 3 domain clusters:
    - Cluster 0: ServiceNow/ITSM (infrastructure, incidents, operations)
    - Cluster 1: Jira/DevOps (development, code, deployments)
    - Cluster 2: Data/ETL (pipelines, databases, data quality)
    """

    # Domain keywords for supervised clustering
    DOMAIN_KEYWORDS = {
        "servicenow": ["incident", "outage", "downtime", "infrastructure", "server", "network",
                       "cpu", "memory", "disk", "service", "restart", "failure", "alert"],
        "jira": ["code", "bug", "feature", "deployment", "build", "test", "pull request",
                 "merge", "commit", "branch", "ci/cd", "pipeline", "kubernetes", "docker"],
        "data": ["database", "query", "etl", "airflow", "dag", "sql", "postgres", "mysql",
                 "data", "pipeline", "transform", "schema", "table", "connection pool"]
    }

    def __init__(self, model_path: str = None):
        self.model_path = model_path or "/home/samrattidke600/ai_agent_app/data/models/three_cluster_bertopic"

        # Initialize embedding model
        self.embedding_model = SentenceTransformer('all-MiniLM-L6-v2')

        # KMeans for exactly 3 clusters
        self.kmeans_model = KMeans(n_clusters=3, random_state=42, n_init=10)

        # UMAP for dimensionality reduction
        self.umap_model = UMAP(
            n_neighbors=15,
            n_components=5,
            min_dist=0.0,
            metric='cosine',
            random_state=42
        )

        # BERTopic model
        self.topic_model = None

        # Cluster centroids for fast classification
        self.cluster_centroids = None

        # Cluster metadata
        self.cluster_info = {
            0: {"name": "ServiceNow_ITSM", "keywords": [], "sample_count": 0},
            1: {"name": "Jira_DevOps", "keywords": [], "sample_count": 0},
            2: {"name": "Data_ETL", "keywords": [], "sample_count": 0}
        }

    def load_incidents(self, incidents_file: str) -> Tuple[List[str], pd.DataFrame]:
        """Load incidents from JSON file"""
        with open(incidents_file, 'r') as f:
            incidents = json.load(f)

        df = pd.DataFrame(incidents)

        # Create combined text for topic modeling
        documents = []
        for inc in incidents:
            text = f"{inc['title']} {inc['description']}"
            documents.append(text)

        logger.info("incidents_loaded", count=len(documents))
        return documents, df

    def _assign_domain_labels(self, documents: List[str]) -> List[int]:
        """
        Assign initial domain labels based on keyword matching
        This helps guide the clustering toward 3 meaningful domains
        """
        labels = []

        for doc in documents:
            doc_lower = doc.lower()

            # Count keyword matches for each domain
            scores = {
                0: sum(1 for kw in self.DOMAIN_KEYWORDS["servicenow"] if kw in doc_lower),
                1: sum(1 for kw in self.DOMAIN_KEYWORDS["jira"] if kw in doc_lower),
                2: sum(1 for kw in self.DOMAIN_KEYWORDS["data"] if kw in doc_lower)
            }

            # Assign to domain with highest score (default to 0 if no matches)
            assigned_label = max(scores, key=scores.get) if sum(scores.values()) > 0 else 0
            labels.append(assigned_label)

        logger.info("domain_labels_assigned",
                    servicenow=labels.count(0),
                    jira=labels.count(1),
                    data=labels.count(2))

        return labels

    def train_model(self, documents: List[str]) -> Tuple[List[int], np.ndarray]:
        """
        Train 3-cluster model:
        1. Generate embeddings
        2. Use KMeans to create exactly 3 clusters
        3. Train BERTopic on top of clusters
        4. Store cluster centroids
        """
        logger.info("training_three_cluster_model", docs=len(documents))

        # Generate embeddings
        logger.info("generating_embeddings")
        embeddings = self.embedding_model.encode(documents, show_progress_bar=True)

        # Apply UMAP for dimensionality reduction
        logger.info("applying_umap_reduction")
        reduced_embeddings = self.umap_model.fit_transform(embeddings)

        # KMeans clustering for exactly 3 clusters
        logger.info("kmeans_clustering")
        cluster_labels = self.kmeans_model.fit_predict(reduced_embeddings)

        # Store cluster centroids (in reduced space)
        self.cluster_centroids = self.kmeans_model.cluster_centers_

        logger.info("clustering_complete",
                    cluster_0=list(cluster_labels).count(0),
                    cluster_1=list(cluster_labels).count(1),
                    cluster_2=list(cluster_labels).count(2))

        # Map clusters to domains based on keyword overlap
        cluster_domain_mapping = self._map_clusters_to_domains(documents, cluster_labels)

        # Remap cluster IDs to match domain semantics
        remapped_labels = [cluster_domain_mapping[c] for c in cluster_labels]

        logger.info("cluster_domain_mapping", mapping=cluster_domain_mapping)

        # Train BERTopic on fixed clusters
        self.topic_model = BERTopic(
            embedding_model=self.embedding_model,
            umap_model=self.umap_model,
            nr_topics=3,
            calculate_probabilities=False,
            verbose=True
        )

        # Fit with pre-computed embeddings and cluster labels
        topics = self.topic_model.fit_transform(documents, embeddings=embeddings, y=remapped_labels)[0]

        return remapped_labels, embeddings

    def _map_clusters_to_domains(self, documents: List[str], cluster_labels: List[int]) -> Dict[int, int]:
        """
        Map KMeans cluster IDs to domain IDs based on keyword overlap
        Returns: {kmeans_cluster_id: domain_id}
        """
        cluster_domain_scores = {0: {}, 1: {}, 2: {}}

        # For each cluster, count keyword matches for each domain
        for cluster_id in [0, 1, 2]:
            cluster_docs = [doc for doc, label in zip(documents, cluster_labels) if label == cluster_id]

            # Score each domain
            for domain_id, domain_name in enumerate(["servicenow", "jira", "data"]):
                score = 0
                for doc in cluster_docs:
                    doc_lower = doc.lower()
                    score += sum(1 for kw in self.DOMAIN_KEYWORDS[domain_name] if kw in doc_lower)
                cluster_domain_scores[cluster_id][domain_id] = score

        # Greedy assignment: assign each cluster to its best-matching domain
        mapping = {}
        used_domains = set()

        # Sort clusters by total keyword matches (descending)
        sorted_clusters = sorted(cluster_domain_scores.keys(),
                                 key=lambda c: sum(cluster_domain_scores[c].values()),
                                 reverse=True)

        for cluster_id in sorted_clusters:
            # Find best domain that hasn't been used
            best_domain = max(
                [d for d in range(3) if d not in used_domains],
                key=lambda d: cluster_domain_scores[cluster_id][d],
                default=None
            )
            if best_domain is not None:
                mapping[cluster_id] = best_domain
                used_domains.add(best_domain)

        # Fill in any missing mappings
        for cluster_id in [0, 1, 2]:
            if cluster_id not in mapping:
                mapping[cluster_id] = next(d for d in range(3) if d not in used_domains)
                used_domains.add(mapping[cluster_id])

        return mapping

    def get_cluster_keywords(self, cluster_id: int, top_n: int = 20) -> List[str]:
        """Get top keywords for a specific cluster"""
        if not self.topic_model:
            raise ValueError("Model not trained yet")

        topic_keywords = self.topic_model.get_topic(cluster_id)
        if topic_keywords:
            return [word for word, _ in topic_keywords[:top_n]]
        return []

    def assign_clusters_to_incidents(
        self,
        df: pd.DataFrame,
        cluster_labels: List[int],
        embeddings: np.ndarray
    ) -> pd.DataFrame:
        """Assign cluster information to incidents DataFrame"""
        df['cluster_id'] = cluster_labels
        df['cluster_name'] = df['cluster_id'].map(lambda cid: self.cluster_info[cid]['name'])

        # Get keywords for each cluster
        for cluster_id in [0, 1, 2]:
            keywords = self.get_cluster_keywords(cluster_id, 10)
            self.cluster_info[cluster_id]['keywords'] = keywords
            self.cluster_info[cluster_id]['sample_count'] = list(cluster_labels).count(cluster_id)

        df['cluster_keywords'] = df['cluster_id'].apply(
            lambda cid: ', '.join(self.cluster_info[cid]['keywords'])
        )

        # Store embeddings (for future similarity search)
        df['embedding'] = list(embeddings)

        return df

    def classify_new_ticket(self, ticket_text: str) -> Dict:
        """
        Classify a new ticket into one of 3 clusters
        Returns: {"cluster_id": int, "cluster_name": str, "confidence": float}
        """
        if self.cluster_centroids is None:
            raise ValueError("Model not trained yet. Call train_model() first.")

        # Generate embedding
        embedding = self.embedding_model.encode([ticket_text])[0]

        # Reduce dimensionality
        reduced_embedding = self.umap_model.transform([embedding])[0]

        # Find nearest centroid
        distances = np.linalg.norm(self.cluster_centroids - reduced_embedding, axis=1)
        cluster_id = int(np.argmin(distances))

        # Calculate confidence (inverse of distance, normalized)
        min_distance = distances[cluster_id]
        max_distance = np.max(distances)
        confidence = 1.0 - (min_distance / max_distance) if max_distance > 0 else 1.0

        return {
            "cluster_id": cluster_id,
            "cluster_name": self.cluster_info[cluster_id]['name'],
            "confidence": float(confidence),
            "keywords": self.cluster_info[cluster_id]['keywords'][:5]
        }

    def save_model(self):
        """Save the trained model and cluster metadata"""
        os.makedirs(self.model_path, exist_ok=True)

        # Save BERTopic model
        if self.topic_model:
            self.topic_model.save(os.path.join(self.model_path, "bertopic_model"))

        # Save cluster centroids and metadata
        metadata = {
            "cluster_centroids": self.cluster_centroids.tolist() if self.cluster_centroids is not None else None,
            "cluster_info": self.cluster_info
        }

        with open(os.path.join(self.model_path, "cluster_metadata.pkl"), 'wb') as f:
            pickle.dump(metadata, f)

        # Save UMAP and KMeans models
        with open(os.path.join(self.model_path, "umap_model.pkl"), 'wb') as f:
            pickle.dump(self.umap_model, f)

        with open(os.path.join(self.model_path, "kmeans_model.pkl"), 'wb') as f:
            pickle.dump(self.kmeans_model, f)

        logger.info("model_saved", path=self.model_path)

    def load_model(self):
        """Load a saved model"""
        model_dir = os.path.join(self.model_path, "bertopic_model")
        metadata_file = os.path.join(self.model_path, "cluster_metadata.pkl")

        if os.path.exists(model_dir) and os.path.exists(metadata_file):
            # Load BERTopic
            self.topic_model = BERTopic.load(model_dir)

            # Load cluster metadata
            with open(metadata_file, 'rb') as f:
                metadata = pickle.load(f)
                self.cluster_centroids = np.array(metadata["cluster_centroids"]) if metadata["cluster_centroids"] else None
                self.cluster_info = metadata["cluster_info"]

            # Load UMAP and KMeans
            with open(os.path.join(self.model_path, "umap_model.pkl"), 'rb') as f:
                self.umap_model = pickle.load(f)

            with open(os.path.join(self.model_path, "kmeans_model.pkl"), 'rb') as f:
                self.kmeans_model = pickle.load(f)

            logger.info("model_loaded", path=self.model_path)
            return True
        return False

    def analyze_incidents(
        self,
        incidents_file: str,
        output_file: str = None
    ) -> Tuple[Dict, pd.DataFrame]:
        """Complete 3-cluster analysis pipeline"""
        # Load incidents
        documents, df = self.load_incidents(incidents_file)

        # Train model
        cluster_labels, embeddings = self.train_model(documents)

        # Assign clusters to incidents
        df = self.assign_clusters_to_incidents(df, cluster_labels, embeddings)

        # Create summary
        summary = {
            "total_incidents": len(df),
            "num_clusters": 3,
            "cluster_distribution": df['cluster_id'].value_counts().to_dict(),
            "clusters": []
        }

        # Add detailed cluster information
        for cluster_id in [0, 1, 2]:
            cluster_detail = {
                "cluster_id": cluster_id,
                "cluster_name": self.cluster_info[cluster_id]['name'],
                "count": self.cluster_info[cluster_id]['sample_count'],
                "keywords": self.cluster_info[cluster_id]['keywords'],
                "percentage": round(100 * self.cluster_info[cluster_id]['sample_count'] / len(df), 2)
            }
            summary['clusters'].append(cluster_detail)

        # Save results (without embeddings in JSON)
        if output_file:
            df_to_save = df.drop(columns=['embedding'])
            df_to_save.to_json(output_file, orient='records', indent=2)
            logger.info("results_saved", file=output_file)

        # Save model
        self.save_model()

        # Save summary
        summary_file = output_file.replace('.json', '_3cluster_summary.json') if output_file else None
        if summary_file:
            with open(summary_file, 'w') as f:
                json.dump(summary, f, indent=2)

        return summary, df


def main():
    """Main execution"""
    analyzer = ThreeClusterAnalyzer()

    incidents_file = "/home/samrattidke600/ai_agent_app/data/demo_data/incidents_100.json"
    output_file = "/home/samrattidke600/ai_agent_app/data/demo_data/incidents_3cluster.json"

    print("🔍 Starting 3-Cluster BERTopic Analysis...")
    print(f"📁 Input: {incidents_file}")
    print("\n🎯 Target Clusters:")
    print("  Cluster 0: ServiceNow/ITSM (infrastructure, incidents)")
    print("  Cluster 1: Jira/DevOps (development, code)")
    print("  Cluster 2: Data/ETL (pipelines, databases)")

    summary, df = analyzer.analyze_incidents(incidents_file, output_file)

    print("\n✅ Analysis Complete!")
    print(f"\n📊 Summary:")
    print(f"  Total Incidents: {summary['total_incidents']}")
    print(f"  Clusters: {summary['num_clusters']}")

    print(f"\n🏷️  Cluster Distribution:")
    for cluster in summary['clusters']:
        print(f"\n  {cluster['cluster_name']} (Cluster {cluster['cluster_id']}):")
        print(f"    Count: {cluster['count']} ({cluster['percentage']}%)")
        print(f"    Keywords: {', '.join(cluster['keywords'][:10])}")

    print(f"\n💾 Output saved to: {output_file}")
    print(f"💾 Model saved to: {analyzer.model_path}")

    # Test classification
    print("\n🧪 Testing Classification:")
    test_tickets = [
        "High CPU utilization on web server causing slow response times",
        "Failed deployment - build pipeline error in Jenkins",
        "Airflow DAG timeout - database connection pool exhausted"
    ]

    for ticket in test_tickets:
        result = analyzer.classify_new_ticket(ticket)
        print(f"\n  Ticket: {ticket[:60]}...")
        print(f"  → Cluster: {result['cluster_name']} (confidence: {result['confidence']:.2%})")
        print(f"  → Keywords: {', '.join(result['keywords'])}")


if __name__ == "__main__":
    main()
