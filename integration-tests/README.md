# dhos-services-api Integration Tests
This folder contains service-level integration tests for the Services API.

## Running the tests
```
# run tests
$ make test-local
```

## Test development
```
$ DHOS_SERVICES_BASE_URL=http://localhost:5000 \
  PROXY_URL=http://localhost \
  HS_ISSUER=http://localhost/ \
  HS_KEY=secret \
  RABBITMQ_HOST=localhost \
  RABBITMQ_USERNAME=guest \
  RABBITMQ_PASSWORD=guest \
  NEO4J_DB_URL=localhost \
  SYSTEM_JWT_SCOPE="delete:gdm_article delete:gdm_sms read:audit_event read:gdm_activation read:gdm_answer_all read:gdm_bg_reading_all \
    read:gdm_clinician_all read:gdm_location_all read:gdm_medication read:gdm_message_all read:gdm_patient_all \
    read:gdm_pdf read:gdm_question read:gdm_rule read:gdm_sms read:gdm_survey_all read:gdm_telemetry \
    read:gdm_telemetry_all read:gdm_trustomer read:location_by_ods read:send_clinician read:send_device \
    read:send_encounter read:send_entry_identifier read:send_location read:send_observation read:send_patient \
    read:send_pdf read:send_rule read:send_trustomer write:audit_event write:gdm_activation write:gdm_alert \
    write:gdm_article write:gdm_clinician_all write:gdm_csv write:gdm_location write:gdm_medication \
    write:gdm_message_all write:gdm_patient_all write:patient_all write:gdm_pdf write:gdm_question write:gdm_sms write:gdm_survey \
    write:gdm_telemetry write:hl7_message write:send_clinician write:send_clinician_all write:send_device \
    write:send_encounter write:send_location write:send_observation write:send_patient write:send_pdf" \
  behave --no-capture --logging-level DEBUG
```
