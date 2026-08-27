import logging
from typing import Any, Iterable, Optional, Union

from confluent_kafka import SerializingProducer
from confluent_kafka.schema_registry import SchemaRegistryClient
from confluent_kafka.schema_registry.avro import AvroSerializer
from confluent_kafka.serialization import StringSerializer
from sqlmodel import SQLModel, inspect

from app.core.config import settings

logger = logging.getLogger(__name__)


class KafkaProducer:
    def __init__(self, topic: str) -> None:
        self.topic: str = topic
        self.producer: Optional[SerializingProducer] = self._create_producer(
            self.topic
        )

    def _create_producer(self, topic: str) -> Optional[SerializingProducer]:
        if not settings.KAFKA_BOOTSTRAP_SERVERS:
            return None

        schema_registry_client = SchemaRegistryClient(
            {
                "url": settings.SCHEMA_REGISTRY_URL,
            }
        )

        subject = f"{topic}-value"
        try:
            registered_schema = schema_registry_client.get_latest_version(
                subject
            )
        except Exception as e:
            raise RuntimeError(f"Schema not found: {subject}") from e

        avro_serializer = AvroSerializer(
            schema_registry_client,
            registered_schema.schema.schema_str,
        )

        return SerializingProducer(
            {
                "bootstrap.servers": settings.KAFKA_BOOTSTRAP_SERVERS,
                "key.serializer": StringSerializer("utf-8"),
                "value.serializer": avro_serializer,
            }
        )

    def send(self, objects: Union[SQLModel, Iterable[SQLModel]]) -> None:
        if not self.producer:
            return
        if isinstance(objects, SQLModel):
            objects = [objects]
        for obj in objects:
            self.producer.produce(
                self.topic,
                key=self._build_key(obj),
                value=obj.model_dump(by_alias=True),
                on_delivery=self._delivery_callback,
            )

    def flush(self) -> None:
        if self.producer:
            self.producer.flush()

    def _build_key(self, obj: SQLModel) -> str:
        inspection = inspect(obj)
        if inspection is None:
            raise ValueError("Unable to inspect object")
        mapper = inspection.mapper
        pk_fields = [col.key for col in mapper.primary_key]

        values = []
        for f in pk_fields:
            v = getattr(obj, f)
            if v is None:
                raise ValueError(f"Primary key {f} is None")
            values.append(str(v))

        return ":".join(values)

    def _delivery_callback(self, err: Optional[Any], msg: Any) -> None:
        if err:
            logger.error("Kafka delivery failed: %s", err)
        else:
            logger.debug(
                "Delivered to %s [%s] key=%s",
                msg.topic(),
                msg.partition(),
                msg.key(),
            )
