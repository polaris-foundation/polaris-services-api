Feature: Clinician migration
  As a software engineer
  I want to migrate clinicians to the users-api
  So that I can move off Neo4J

  Background:
    Given RabbitMQ is running
    And the services API is running
    And the database is empty
    And the locations database is empty
    And the users database is empty
    And the RabbitMQ queues are empty

  # Increase these numbers for performance testing.
  Scenario: Clinicians are migrated
    Given 100 clinicians exist in neo4j
    And we are timing this step
    When we migrate the clinicians
    Then it took less than 10 seconds to complete
    When we fetch the clinicians from users API
    Then we received all of the expected clinicians from users API
    And the migrated clinicians have the same details as the originals
    And the migrated clinicians can log in via the Users API
