Feature: Create patient and record

  Background:
    Given RabbitMQ is running
      And the database is empty
      And the locations database is empty
      And the services API is running

  Scenario: Patient and record is created and published
    Given a clinician exists
    When acting as a superclinician user
    When a new patient is posted successfully
    Then the patient is saved in the database
      And a AUDIT_MESSAGE message is published to RabbitMQ

  Scenario: Viewing a patient publishes an audit message
    Given a clinician exists
      And a GDM patient exists
      And the RabbitMQ queues are empty
     When I view the patient
     Then a AUDIT_MESSAGE message is published to RabbitMQ

  Scenario: Patient is updated
    Given a clinician exists
      And a GDM patient exists
      And the RabbitMQ queues are empty
     When I update the patient

  Scenario: Get list of UUIDs
    Given a clinician exists
    When acting as a superclinician user
    When a new patient is posted successfully
    Then a request for patient UUIDs returns list of UUIDs

  Scenario: Get list of UUIDs
    Given a clinician exists
    When acting as a superclinician user
    When a new patient is posted successfully
    Then a request for the patient list returns the patient
