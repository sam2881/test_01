"""Unit tests for utility modules"""
import pytest
from unittest.mock import Mock, patch, MagicMock
import json


class TestPostgresClient:
    """Test PostgreSQL client utilities"""

    @patch('psycopg2.connect')
    def test_log_event_success(self, mock_connect):
        """Test successful event logging"""
        mock_cursor = Mock()
        mock_conn = Mock()
        mock_conn.cursor.return_value = mock_cursor
        mock_connect.return_value = mock_conn

        from utils.postgres_client import PostgresClient

        client = PostgresClient()
        result = client.log_event(
            event_id="test-123",
            agent_name="servicenow",
            event_type="task_received",
            payload={"description": "Test"},
            status="processing"
        )

        assert result is True
        mock_cursor.execute.assert_called_once()

    @patch('psycopg2.connect')
    def test_get_events(self, mock_connect):
        """Test retrieving events"""
        mock_cursor = Mock()
        mock_cursor.fetchall.return_value = [
            ("test-123", "servicenow", "task_received", "{}", "processing", "2025-01-15")
        ]
        mock_conn = Mock()
        mock_conn.cursor.return_value = mock_cursor
        mock_connect.return_value = mock_conn

        from utils.postgres_client import PostgresClient

        client = PostgresClient()
        events = client.get_events(agent_name="servicenow", limit=10)

        assert len(events) > 0
        assert events[0][0] == "test-123"

    @patch('psycopg2.connect')
    def test_connection_error(self, mock_connect):
        """Test handling connection errors"""
        mock_connect.side_effect = Exception("Connection failed")

        from utils.postgres_client import PostgresClient

        with pytest.raises(Exception):
            client = PostgresClient()
            client.log_event("test", "agent", "type", {})


class TestRedisClient:
    """Test Redis client utilities"""

    @patch('redis.Redis')
    def test_set_get_value(self, mock_redis):
        """Test setting and getting values"""
        mock_instance = Mock()
        mock_instance.set.return_value = True
        mock_instance.get.return_value = b'{"key": "value"}'
        mock_redis.return_value = mock_instance

        from utils.redis_client import RedisClient

        client = RedisClient()
        client.set("test_key", {"key": "value"})
        result = client.get("test_key")

        assert result["key"] == "value"

    @patch('redis.Redis')
    def test_delete_key(self, mock_redis):
        """Test deleting keys"""
        mock_instance = Mock()
        mock_instance.delete.return_value = 1
        mock_redis.return_value = mock_instance

        from utils.redis_client import RedisClient

        client = RedisClient()
        result = client.delete("test_key")

        assert result is True

    @patch('redis.Redis')
    def test_cache_expiry(self, mock_redis):
        """Test cache with expiry"""
        mock_instance = Mock()
        mock_instance.setex.return_value = True
        mock_redis.return_value = mock_instance

        from utils.redis_client import RedisClient

        client = RedisClient()
        result = client.set("test_key", {"data": "value"}, ttl=300)

        assert result is True
        mock_instance.setex.assert_called_once()


class TestKafkaClient:
    """Test Kafka client utilities"""

    @patch('kafka.KafkaProducer')
    def test_publish_event(self, mock_producer):
        """Test publishing events to Kafka"""
        mock_instance = Mock()
        mock_instance.send.return_value = Mock()
        mock_producer.return_value = mock_instance

        from utils.kafka_client import KafkaClient

        client = KafkaClient()
        result = client.publish_event(
            topic="agent.events",
            event={"task_id": "test-123", "type": "task_received"},
            key="test-123"
        )

        assert result is True
        mock_instance.send.assert_called_once()

    @patch('kafka.KafkaProducer')
    def test_publish_batch_events(self, mock_producer):
        """Test publishing batch events"""
        mock_instance = Mock()
        mock_producer.return_value = mock_instance

        from utils.kafka_client import KafkaClient

        client = KafkaClient()
        events = [
            {"task_id": f"test-{i}", "type": "test"}
            for i in range(5)
        ]

        result = client.publish_batch(topic="agent.events", events=events)

        assert result is True
        assert mock_instance.send.call_count == 5


class TestRAGClient:
    """Test RAG (Retrieval Augmented Generation) utilities"""

    @patch('weaviate.Client')
    def test_weaviate_query(self, mock_client):
        """Test Weaviate vector search"""
        mock_instance = Mock()
        mock_instance.query.get.return_value.with_near_text.return_value.with_limit.return_value.do.return_value = {
            "data": {
                "Get": {
                    "Incident": [
                        {
                            "incident_id": "INC0011234",
                            "description": "Similar incident",
                            "_additional": {"certainty": 0.91}
                        }
                    ]
                }
            }
        }
        mock_client.return_value = mock_instance

        from rag.weaviate_client import WeaviateRAG

        rag = WeaviateRAG()
        results = rag.search_similar_incidents(
            query="API Gateway timeout",
            limit=5
        )

        assert len(results) > 0
        assert results[0]["incident_id"] == "INC0011234"

    @patch('neo4j.GraphDatabase.driver')
    def test_neo4j_query(self, mock_driver):
        """Test Neo4j graph query"""
        mock_session = Mock()
        mock_session.run.return_value = [
            {"cause": "High CPU", "resolution": "Scale instances", "count": 5}
        ]
        mock_driver_instance = Mock()
        mock_driver_instance.session.return_value.__enter__.return_value = mock_session
        mock_driver.return_value = mock_driver_instance

        from rag.neo4j_client import Neo4jGraph

        graph = Neo4jGraph()
        results = graph.find_causal_relationships(
            symptom="502 errors"
        )

        assert len(results) > 0
        assert results[0]["cause"] == "High CPU"


class TestDSPyModules:
    """Test DSPy optimization modules"""

    def test_routing_signature(self):
        """Test DSPy routing signature"""
        from dspy_service.signatures import RoutingSignature

        sig = RoutingSignature()

        assert hasattr(sig, 'task_description')
        assert hasattr(sig, 'selected_agent')

    @patch('dspy.OpenAI')
    def test_routing_module(self, mock_dspy):
        """Test DSPy routing module"""
        mock_instance = Mock()
        mock_instance.return_value = Mock(
            selected_agent="servicenow",
            confidence=0.95
        )
        mock_dspy.return_value = mock_instance

        from dspy_service.modules import TaskRouter

        router = TaskRouter()
        result = router(task_description="API Gateway down")

        assert result.selected_agent in ["servicenow", "jira", "github", "infra", "data"]

    def test_dspy_evaluation_metric(self):
        """Test DSPy evaluation metrics"""
        from dspy_service.evaluators import routing_accuracy

        # Mock predictions and ground truth
        predictions = [
            {"selected_agent": "servicenow"},
            {"selected_agent": "jira"},
            {"selected_agent": "servicenow"}
        ]
        ground_truth = [
            {"correct_agent": "servicenow"},
            {"correct_agent": "jira"},
            {"correct_agent": "jira"}
        ]

        accuracy = routing_accuracy(predictions, ground_truth)

        assert 0.0 <= accuracy <= 1.0
        assert accuracy == pytest.approx(0.667, rel=0.1)


class TestHITLModule:
    """Test Human-in-the-Loop utilities"""

    @patch('utils.postgres_client.PostgresClient')
    def test_create_approval_request(self, mock_postgres):
        """Test creating HITL approval request"""
        mock_instance = Mock()
        mock_instance.log_event.return_value = True
        mock_postgres.return_value = mock_instance

        from hitl.approval_manager import create_approval_request

        result = create_approval_request(
            approval_type="routing_override",
            incident_id="INC0012345",
            routing_decision={
                "selected_agent": "infrastructure",
                "confidence": 0.92
            }
        )

        assert "approval_id" in result
        assert result["status"] == "pending"

    def test_approval_timeout(self):
        """Test approval timeout handling"""
        from hitl.approval_manager import check_approval_timeout
        from datetime import datetime, timedelta

        approval = {
            "approval_id": "apr_test_123",
            "created_at": (datetime.utcnow() - timedelta(minutes=35)).isoformat(),
            "timeout_minutes": 30
        }

        is_timeout = check_approval_timeout(approval)

        assert is_timeout is True

    def test_approval_not_timeout(self):
        """Test approval within timeout"""
        from hitl.approval_manager import check_approval_timeout
        from datetime import datetime, timedelta

        approval = {
            "approval_id": "apr_test_456",
            "created_at": (datetime.utcnow() - timedelta(minutes=15)).isoformat(),
            "timeout_minutes": 30
        }

        is_timeout = check_approval_timeout(approval)

        assert is_timeout is False


class TestTopicModeling:
    """Test BERTopic classification"""

    @patch('bertopic.BERTopic')
    def test_classify_incident(self, mock_bertopic):
        """Test incident classification with BERTopic"""
        mock_model = Mock()
        mock_model.transform.return_value = ([0], [[0.87, 0.10, 0.03]])
        mock_bertopic.load.return_value = mock_model

        from topic_modeling.classifier import classify_incident

        result = classify_incident(
            description="API Gateway returning 502 errors"
        )

        assert "domain" in result
        assert result["domain"] in ["ServiceNow", "Jira", "Data"]
        assert "confidence" in result

    def test_topic_model_training(self):
        """Test BERTopic model training"""
        from topic_modeling.train import train_topic_model

        # Mock training data
        documents = [
            "API Gateway timeout error",
            "Database connection failed",
            "Bug in payment validation code",
            "Server CPU usage high"
        ] * 10  # Repeat for sufficient data

        model = train_topic_model(documents, n_topics=3)

        assert model is not None
        assert hasattr(model, 'transform')
