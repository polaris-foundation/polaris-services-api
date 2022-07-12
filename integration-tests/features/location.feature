Feature: API calls - location API

  Background:
    Given RabbitMQ is running
      And the database is empty
      And the locations database is empty
      And the services API is running
      And a clinician exists

  Scenario: Add a location
    When a new location is created
    And the location is retrieved
    Then the retrieved location matches that of the location request

  Scenario: Get patients by location
    Given a GDM patient exists
    When a list of patients is retrieved for the location and the product is GDM
    Then the GDM patient is found in the list of patients

  Scenario: Get patients by GDM endpoint
    Given a GDM patient exists
    When a list of GDM patients is retrieved for the location
    Then the patient is found in the list of GDM patients for location


  Scenario: Add an extra patient with dh product closed.
    Given a GDM patient exists
    And a closed GDM patient exists
    And a closed with reason PATIENT_CREATED_IN_ERROR GDM patient exists
    And a closed with reason OTHER_REASON GDM patient exists
    When a list of active GDM patients is retrieved for the location
    Then the 1st patient is found in the list of GDM patients for location
    When a list of inactive GDM patients including created in error is retrieved for the location
    Then the 1st patient is not found in the list of GDM patients for location
    And the 2nd patient is found in the list of GDM patients for location
    And the 3rd patient is found in the list of GDM patients for location
    And the 4th patient is found in the list of GDM patients for location

  Scenario: Get current and previous patients by location
    Given a GDM patient exists
    And another GDM patient exists
    And a closed with reason OTHER_REASON GDM patient exists
    When a list of patients is retrieved for the location and the product is GDM
    Then the 1st patient is found in the list of GDM patients for location
    And the 2nd patient is found in the list of GDM patients for location
    And the 3rd patient is found in the list of GDM patients for location

  Scenario: Create, get, and update a location
    When a new location is created
    Then the returned location matches that of the location request
    When the location is retrieved
    Then the retrieved location matches that of the location request
    When the location is updated
    Then the returned location matches that of the location request

  Scenario: Get all locations
    Given an alternate location exists
    When all locations are retrieved and the product is GDM
    Then the original location exists in the retrieved location list
    And the alternate location exists in the retrieved location list
