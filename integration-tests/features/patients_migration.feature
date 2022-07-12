Feature: Patients migration
  As a software engineer
  I want to migrate patient data to postgres
  So that I can move off Neo4J

  Background:
    Given RabbitMQ is running
    And the services API is running
    And the database is empty
    And the locations database is empty
    And the RabbitMQ queues are empty

  # Increase these numbers for performance testing.
  Scenario: Patients are migrated
    Given 100 patients exist in neo4j
    And a clinician exists
    And we are timing this step
    When we migrate the patients
    Then it took less than 15 seconds to complete
    When we fetch the patients from services API (postgres)
    Then we received all of the expected patients from services API
    And the migrated patients have the same details as the originals
