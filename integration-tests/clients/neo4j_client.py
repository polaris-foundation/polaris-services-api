from typing import Dict, Generator, List

from behave import fixture
from behave.runner import Context
from environs import Env
from neo4j import Driver, GraphDatabase, Session, StatementResult, Transaction

env: Env = Env()
NEO4J_HOST: str = env.str("NEO4J_DB_URL", "neo4j")
NEO4J_PORT: int = env.int("NEO4J_DB_PORT", 7687)
NEO4J_CONNECTION: str = f"bolt://{NEO4J_HOST}:{NEO4J_PORT}"


@fixture
def clear_neo4j_database(context: Context) -> Generator[Session, None, None]:
    driver: Driver = GraphDatabase.driver(NEO4J_CONNECTION)
    session: Session

    with driver.session() as session:
        session.write_transaction(lambda tx: tx.run("MATCH(n) DETACH DELETE(n)"))
        yield session


def execute_cypher(
    context: Context, cypher: str, parameters: Dict = None
) -> StatementResult:
    def _execute_cypher(transaction: Transaction) -> List:
        return transaction.run(statement=cypher, parameters=parameters)

    driver: Driver = GraphDatabase.driver(NEO4J_CONNECTION)
    session: Session

    with driver.session() as session:
        return session.write_transaction(_execute_cypher)
