Feature: Location hierarchy performance
  As a clinician
  I want to create and retrieve many locations
  So that I can manage patient care

  Background:
    Given RabbitMQ is running
    And the database is empty
    And the locations database is empty
    And the services API is running
    And a clinician exists

  # Increase these numbers for performance testing. e.g. 2, 100, 10, 5 gives 10,000 locations
  Scenario: Many locations are retrieved
    Given 4 hospitals each with 10 wards each with 10 bays of 5 beds exists in postgres
    And we are timing this step
    When we fetch the location hierarchy
    Then it took less than 20 seconds to complete
    And we received all of the expected locations
