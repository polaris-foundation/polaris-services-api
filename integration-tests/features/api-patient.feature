Feature: API calls - patient API

  Background:
    Given RabbitMQ is running
      And the database is empty
      And the locations database is empty
      And the services API is running
      And a clinician exists

  Scenario: Add a patient.
    When we POST to dhos/v1/patient?type=GDM with data from test_1_post_patient/input_1.json
    Then the response matches test_1_post_patient/output_1.json

  Scenario: Get patient by ID.
    Given a GDM patient exists
    When we GET from dhos/v1/patient/{context.patient_uuid}?type=GDM
    Then the response matches test_2_get_patient_by_id/output_2.json

  Scenario: Patch update a patient
    Given a GDM patient exists
      And an alternate location exists
    When we PATCH to dhos/v1/patient/{context.patient_uuid}?type=GDM with data from test_4_patch_update_patient/input_4.json
    Then the response matches test_4_patch_update_patient/output_4.json

  Scenario: Bookmark a patient then remove the bookmark
    Given a GDM patient exists
    When we GET from dhos/v1/patient/{context.patient_uuid}?type=GDM
    Then the response matches test_2_get_patient_by_id/output_2.json
    When we POST to dhos/v1/location/{context.location_uuid}/patient/{context.patient_uuid}/bookmark with no data
    Then the response matches test_19_post_bookmark/output_19.json
    When we GET from dhos/v1/patient/{context.patient_uuid}?type=GDM
    Then the response matches test_20_get_patient_by_id/output_20.json
    When we DELETE to dhos/v1/location/{context.location_uuid}/patient/{context.patient_uuid}/bookmark with no data
    Then the response matches test_21_delete_bookmark/output_21.json
    When we GET from dhos/v1/patient/{context.patient_uuid}?type=GDM
    Then the response matches test_22_get_patient_by_id/output_22.json

  Scenario: Add an extra patient
    Given a GDM patient exists
    When we POST to dhos/v1/patient?type=GDM with data from test_5_post_patient/input_5.json
    Then the response matches test_5_post_patient/output_5.json

# FIXME: This broke with changes to minimal GDM patient, to be fixed in PLAT-694
#  Scenario: Updating a patient
#    Given a minimal GDM patient exists
#      And many clinicians exist
#    When we PATCH to dhos/v1/patient/{context.patient_uuid} with data from test_23_patch_update_patient_with_visit/input_23.json
#    Then the response matches test_23_patch_update_patient_with_visit/output_23.json
#    When we PATCH to dhos/v1/patient/{context.patient_uuid} with data from test_24_patch_note_to_record/input_24.json
#    Then the response matches test_24_patch_note_to_record/output_24.json
#    When we PATCH to dhos/v1/patient/{context.patient_uuid} with data from test_25_patch_update_history/input_25.json
#    Then the response matches test_25_patch_update_history/output_25.json
#    When we PATCH to dhos/v1/patient/{context.patient_uuid} with data from test_26_patch_pregnancy_to_record/input_26.json
#    Then the response matches test_26_patch_pregnancy_to_record/output_26.json
#      And we save {context.output[record][pregnancies][0][uuid]} as pregnancy_uuid
#    When we PATCH to dhos/v1/patient/{context.patient_uuid} with data from test_27_patch_delivery_to_pregnancy/input_27.json
#    Then the response matches test_27_patch_delivery_to_pregnancy/output_27.json
#      And we save {context.output[record][pregnancies][0][deliveries][0][uuid]} as delivery_uuid
#      And we save {context.output[record][pregnancies][0][deliveries][0][patient][uuid]} as baby_uuid
#    When we PATCH to dhos/v1/patient/{context.patient_uuid} with data from test_28_patch_delivery/input_28.json
#    Then the response matches test_28_patch_delivery/output_28.json
#    When we PATCH to dhos/v1/patient/{context.patient_uuid} with data from test_29_patch_new_product/input_29.json
#    Then the response matches test_29_patch_new_product/output_29.json
#    When we PATCH to dhos/v1/patient/{context.patient_uuid} with data from test_31_patch_different_product_on_open_patient/input_31.json
#    Then the response matches test_31_patch_different_product_on_open_patient/output_31.json

  Scenario: Updating management plan
    Given a GDM patient exists
      And we GET from dhos/v1/patient/{context.patient_uuid}?type=GDM
      And we save {context.output[record][diagnoses][0][uuid]} as diagnosis_uuid
      And we save {context.output[record][diagnoses][0][management_plan][doses][0][uuid]} as dose_uuid
    When we PATCH to dhos/v1/patient/{context.patient_uuid} with data from test_32_patch_management_plan_update/input_32.json
    Then the response matches test_32_patch_management_plan_update/output_32.json
    When we PATCH to dhos/v1/patient/{context.patient_uuid} with data from test_33_patch_new_diagnosis/input_33.json
    Then the response matches test_33_patch_new_diagnosis/output_33.json
      And we save {context.output[record][diagnoses][0][uuid]} as diagnosis2_uuid
    When we PATCH to dhos/v1/patient/{context.patient_uuid} with data from test_34_patch_update_diagnosis/input_34.json
    Then the response matches test_34_patch_update_diagnosis/output_34.json

  Scenario: Get abbreviated patient
    Given a GDM patient exists
      And acting as a patient user
    When we GET from dhos/v1/patient-abbreviated/{context.patient_uuid}
    Then the response matches test_35_get_abbreviated_patient/output_35.json

  Scenario: Fail to close a patient with missing required fields
    Given a GDM patient exists
      And we GET from dhos/v1/patient/{context.patient_uuid}?type=GDM
      And we save {context.output[dh_products][0][uuid]} as dh_product_uuid
    When we POST to dhos/v1/patient/{context.patient_uuid}/product/{context.dh_product_uuid}/close with data from test_36_fail_close_patient/input_36.json with status 400
    Then the response matches test_36_fail_close_patient/output_36.json

  Scenario: Close a patient
    Given a GDM patient exists
      And we GET from dhos/v1/patient/{context.patient_uuid}?type=GDM
      And we save {context.output[dh_products][0][uuid]} as dh_product_uuid
    When we POST to dhos/v1/patient/{context.patient_uuid}/product/{context.dh_product_uuid}/close with data from test_37_close_patient/input_37.json
    Then the response matches test_37_close_patient/output_37.json

  Scenario: Delete diagnosis from patient
    Given a GDM patient exists
      And we GET from dhos/v1/patient/{context.patient_uuid}?type=GDM
      And we save {context.output[record][diagnoses][0][uuid]} as diagnosis_uuid
    When we PATCH to dhos/v1/patient/{context.patient_uuid}/delete with data from test_38_delete_diagnosis_from_patient/input_38.json
    Then the response matches test_38_delete_diagnosis_from_patient/output_38.json

  Scenario: Delete dh_product from patient
    Given a GDM patient exists
      And we GET from dhos/v1/patient/{context.patient_uuid}?type=GDM
      And we save {context.output[dh_products][0][uuid]} as dh_product_uuid
    When we PATCH to dhos/v1/patient/{context.patient_uuid}/delete with data from test_40_delete_dh_product_from_patient/input_40.json
    Then the response matches test_40_delete_dh_product_from_patient/output_40.json

  Scenario: Delete pregnancy from patient
    Given a GDM patient exists
      And we GET from dhos/v1/patient/{context.patient_uuid}?type=GDM
      And we save {context.output[record][pregnancies][0][uuid]} as pregnancy_uuid
    When we PATCH to dhos/v1/patient/{context.patient_uuid}/delete with data from test_41_delete_pregnancy_from_patient/input_41.json
    Then the response matches test_41_delete_pregnancy_from_patient/output_41.json

  Scenario: Delete delivery from pregnancy
    Given a GDM patient exists
      And we GET from dhos/v1/patient/{context.patient_uuid}?type=GDM
      And we save {context.output[record][pregnancies][0][uuid]} as pregnancy_uuid
      And we save {context.output[record][pregnancies][0][deliveries][0][uuid]} as delivery_uuid
    When we PATCH to dhos/v1/patient/{context.patient_uuid}/delete with data from test_42_delete_delivery_from_pregnancy/input_42.json
    Then the response matches test_42_delete_delivery_from_pregnancy/output_42.json

  Scenario: Try to add a patient with missing required fields
    When we POST to dhos/v1/patient?type=GDM with data from test_43_fail_post_patient/input_43.json with status 400
    Then the response matches test_43_fail_post_patient/output_43.json

  Scenario: 2nd Fail to close a patient with missing required fields
    Given a GDM patient exists
      And we GET from dhos/v1/patient/{context.patient_uuid}?type=GDM
      And we save {context.output[dh_products][0][uuid]} as dh_product_uuid
      And we save {context.output[record][pregnancies][0][uuid]} as pregnancy_uuid
    When we PATCH to dhos/v1/patient/{context.patient_uuid} with data from test_44_fail_close_patient_2/input_44_a.json
      And we POST to dhos/v1/patient/{context.patient_uuid}/product/{context.dh_product_uuid}/close with data from test_44_fail_close_patient_2/input_44.json with status 400
    Then the response matches test_44_fail_close_patient_2/output_44.json

  Scenario: Patient accepts terms agreement
    Given a GDM patient exists
      And acting as a patient user
    When we POST to dhos/v1/patient/{context.patient_uuid}/terms_agreement with data from test_46_post_patient_terms_agreement/input_46.json
    Then the response matches test_46_post_patient_terms_agreement/output_46.json

  Scenario: Clinician stops monitoring a patient
    Given a GDM patient exists
      And we GET from dhos/v1/patient/{context.patient_uuid}?type=GDM
      And we save {context.output[dh_products][0][uuid]} as dh_product_uuid
    When we POST to dhos/v1/patient/{context.patient_uuid}/product/{context.dh_product_uuid}/stop_monitoring with no data
    Then the response matches test_60_stop_monitoring_patient/output_60.json

  Scenario: Clinician starts monitoring a patient
    Given a GDM patient exists
      And we GET from dhos/v1/patient/{context.patient_uuid}?type=GDM
      And we save {context.output[dh_products][0][uuid]} as dh_product_uuid
    When we POST to dhos/v1/patient/{context.patient_uuid}/product/{context.dh_product_uuid}/stop_monitoring with no data
    And we POST to dhos/v1/patient/{context.patient_uuid}/product/{context.dh_product_uuid}/start_monitoring with no data
    Then the response matches test_61_start_monitoring_patient/output_61.json
