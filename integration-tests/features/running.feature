Feature: dhos-services-api is running

  Scenario: ensure the dhos-services-api /running endpoint responds
    Given dhos-services-api has been started
      When we fetch from /running
      Then the result is 200
