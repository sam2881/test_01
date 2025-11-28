#!/usr/bin/env python3
"""BERTopic Analysis for Incident Clustering"""
import json
import os
from typing import List, Dict, Tuple
import pandas as pd
from bertopic import BERTopic
from sentence_transformers import SentenceTransformer
from umap import UMAP
from hdbscan import HDBSCAN
import structlog

logger = structlog.get_logger()


class IncidentTopicAnalyzer:
    """Analyze and cluster incidents using BERTopic"""

    def __init__(self, model_path: str = None):
        self.model_path = model_path or "/home/samrattidke600/ai_agent_app/data/models/bertopic_incidents"

        # Initialize embedding model
        self.embedding_model = SentenceTransformer('all-MiniLM-L6-v2')

        # Initialize UMAP for dimensionality reduction
        self.umap_model = UMAP(
            n_neighbors=15,
            n_components=5,
            min_dist=0.0,
            metric='cosine',
            random_state=42
        )

        # Initialize HDBSCAN for clustering
        self.hdbscan_model = HDBSCAN(
            min_cluster_size=5,
            metric='euclidean',
            cluster_selection_method='eom',
            prediction_data=True
        )

        # Initialize BERTopic
        self.topic_model = None

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

    def train_model(self, documents: List[str], min_topic_size: int = 3):
        """Train BERTopic model on incidents"""
        logger.info("training_bertopic_model", docs=len(documents))

        self.topic_model = BERTopic(
            embedding_model=self.embedding_model,
            umap_model=self.umap_model,
            hdbscan_model=self.hdbscan_model,
            min_topic_size=min_topic_size,
            nr_topics="auto",
            calculate_probabilities=True,
            verbose=True
        )

        # Fit the model
        topics, probabilities = self.topic_model.fit_transform(documents)

        logger.info(
            "bertopic_training_complete",
            num_topics=len(set(topics)) - 1,  # -1 for outlier topic
            outliers=sum(1 for t in topics if t == -1)
        )

        return topics, probabilities

    def get_topic_info(self) -> pd.DataFrame:
        """Get information about discovered topics"""
        if not self.topic_model:
            raise ValueError("Model not trained yet")

        return self.topic_model.get_topic_info()

    def get_topic_keywords(self, topic_id: int, top_n: int = 10) -> List[Tuple[str, float]]:
        """Get top keywords for a specific topic"""
        if not self.topic_model:
            raise ValueError("Model not trained yet")

        return self.topic_model.get_topic(topic_id)[:top_n]

    def assign_topics_to_incidents(
        self,
        df: pd.DataFrame,
        topics: List[int],
        probabilities: List[List[float]]
    ) -> pd.DataFrame:
        """Assign topic information to incidents DataFrame"""
        df['topic_id'] = topics
        df['topic_probability'] = [max(probs) if len(probs) > 0 else 0.0 for probs in probabilities]

        # Get topic names
        topic_info = self.get_topic_info()
        topic_names = dict(zip(topic_info['Topic'], topic_info['Name']))

        df['topic_name'] = df['topic_id'].map(topic_names)

        # Get representative keywords for each incident's topic
        df['topic_keywords'] = df['topic_id'].apply(
            lambda tid: ', '.join([word for word, _ in self.get_topic_keywords(tid, 5)])
            if tid != -1 else 'outlier'
        )

        return df

    def save_model(self):
        """Save the trained model"""
        if not self.topic_model:
            raise ValueError("No model to save")

        os.makedirs(self.model_path, exist_ok=True)
        self.topic_model.save(self.model_path)
        logger.info("model_saved", path=self.model_path)

    def load_model(self):
        """Load a saved model"""
        if os.path.exists(self.model_path):
            self.topic_model = BERTopic.load(self.model_path)
            logger.info("model_loaded", path=self.model_path)
            return True
        return False

    def analyze_incidents(
        self,
        incidents_file: str,
        output_file: str = None
    ) -> Dict:
        """Complete analysis pipeline"""
        # Load incidents
        documents, df = self.load_incidents(incidents_file)

        # Train model
        topics, probabilities = self.train_model(documents)

        # Assign topics to incidents
        df = self.assign_topics_to_incidents(df, topics, probabilities)

        # Get topic statistics
        topic_info = self.get_topic_info()

        # Create summary
        summary = {
            "total_incidents": len(df),
            "num_topics": len(set(topics)) - 1,
            "outliers": sum(1 for t in topics if t == -1),
            "topic_distribution": df['topic_id'].value_counts().to_dict(),
            "topics": []
        }

        # Add detailed topic information
        for _, row in topic_info.iterrows():
            if row['Topic'] != -1:  # Skip outlier topic
                topic_detail = {
                    "topic_id": int(row['Topic']),
                    "topic_name": row['Name'],
                    "count": int(row['Count']),
                    "keywords": ', '.join([word for word, _ in self.get_topic_keywords(row['Topic'], 10)])
                }
                summary['topics'].append(topic_detail)

        # Save results
        if output_file:
            df.to_json(output_file, orient='records', indent=2)
            logger.info("results_saved", file=output_file)

        # Save model
        self.save_model()

        # Save summary
        summary_file = output_file.replace('.json', '_summary.json') if output_file else None
        if summary_file:
            with open(summary_file, 'w') as f:
                json.dump(summary, f, indent=2)

        return summary, df


def main():
    """Main execution"""
    analyzer = IncidentTopicAnalyzer()

    incidents_file = "/home/samrattidke600/ai_agent_app/data/demo_data/incidents_100.json"
    output_file = "/home/samrattidke600/ai_agent_app/data/demo_data/incidents_with_topics.json"

    print("🔍 Starting BERTopic Analysis...")
    print(f"📁 Input: {incidents_file}")

    summary, df = analyzer.analyze_incidents(incidents_file, output_file)

    print("\n✅ Analysis Complete!")
    print(f"\n📊 Summary:")
    print(f"  Total Incidents: {summary['total_incidents']}")
    print(f"  Topics Discovered: {summary['num_topics']}")
    print(f"  Outliers: {summary['outliers']}")

    print(f"\n🏷️  Topics:")
    for topic in summary['topics'][:10]:  # Show top 10 topics
        print(f"  Topic {topic['topic_id']}: {topic['topic_name']}")
        print(f"    Count: {topic['count']}")
        print(f"    Keywords: {topic['keywords'][:100]}...")
        print()

    print(f"\n💾 Output saved to: {output_file}")
    print(f"💾 Model saved to: {analyzer.model_path}")


if __name__ == "__main__":
    main()
