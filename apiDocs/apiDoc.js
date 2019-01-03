/**
 * @api {post} /api-token-auth/ Request Token
 * @apiName GetApiToken
 * @apiGroup Auth
 *
 * @apiParam {String} usename Users unique ID.
 * @apiParam {String} password Users password.
 *
 * @apiSuccess {String} token JWT_TOKEN.
 *
 * @apiSuccessExample Success-Response:
 *     HTTP/1.1 200 OK
 *     {
 *       "token": "JWT_TOKEN"
 *     }
 *
 * @apiError UserNotFound Cannot find the user with provided credentials.
 *
 * @apiErrorExample Error-Response:
 *     HTTP/1.1 400 Bad Request
 *     {
 *       "non_field_errors": ["Unable to log in with provided credentials."]
 *     }
 */

/**
 * @api {get} /bok_0_bookingskeys/ Get list of bok_0_bookingskeys
 * @apiName GetBok_0
 * @apiGroup Bok_0
 *
 * @apiHeader {String} Authorization "JWT " + JWT_TOKEN.
 * @apiHeader {String} ContentType "application/json".
 *
 * @apiHeaderExample {json} Request-Example:
 *     {
 *       "Authorization": "JWT *****************************",
 *       "Content-Type": "application/json"
 *     }
 *
 * @apiSuccess {Array} Objects Array of bok_0_bookingskeys.
 *
 * @apiSuccessExample Success-Response:
 *     HTTP/1.1 200 OK
 *     {
 *         [
 *               {
 *                  "pk_auto_id": 1,
 *                  "client_booking_id": "",
 *                  "filename": "111.xlsx",
 *                  "success": "0",
 *                  "timestampCreated": "2018-12-11T18:58:59.276184Z",
 *                  "client": "",
 *                  "v_client_pk_consigment_num": "8106245243",
 *                  "l_000_client_acct_number": 10001,
 *                  "l_011_client_warehouse_id": 1,
 *                  "l_012_client_warehouse_name": "Hanalt"
 *               },
 *               {
 *                  "pk_auto_id": 2,
 *                  "client_booking_id": "",
 *                  "filename": "111.xlsx",
 *                  "success": "0",
 *                  "timestampCreated": "2018-12-11T18:58:59.276184Z",
 *                  "client": "",
 *                  "v_client_pk_consigment_num": "8106245243",
 *                  "l_000_client_acct_number": 10001,
 *                  "l_011_client_warehouse_id": 1,
 *                  "l_012_client_warehouse_name": "Hanalt"
 *               }
 *          ]
 *     }
 *
 * @apiError SignatureError Cannot decode signature or has been already expired.
 *
 * @apiErrorExample Error-Response:
 *     HTTP/1.1 4xx Forbidden
 *     {
 *       "detail": "Error decoding signature."
 *     }
 */

/**
 * @api {post} /bok_0_bookingskeys/ Insert new bok_0_bookingskeys
 * @apiName AddBok_0
 * @apiGroup Bok_0
 *
 * @apiHeader {String} Authorization "JWT " + JWT_TOKEN.
 * @apiHeader {String} ContentType "application/json".
 *
 * @apiHeaderExample {json} Request-Example:
 *     {
 *       "Authorization": "JWT *****************************",
 *       "Content-Type": "application/json"
 *     }
 *
 * @apiParam {JSON} Object bok_0_bookingskeys.
 *
 * @apiParamExample {json} Request-Example:
 *      {
 *          "client_booking_id": "",
 *          "filename": "111.xlsx",
 *          "success": "0",
 *          "timestampCreated": "2018-12-11T18:58:59.276184Z",
 *          "client": "",
 *          "v_client_pk_consigment_num": "8106245243",
 *          "l_000_client_acct_number": 10001,
 *          "l_011_client_warehouse_id": 1,
 *          "l_012_client_warehouse_name": "Hanalt"
 *      }
 *
 * @apiSuccess {JSON} OBject Return created object.
 *
 * @apiSuccessExample Success-Response:
 *     HTTP/1.1 200 OK
 *     {
 *			"pk_auto_id": 2886,
 *          "client_booking_id": "",
 *          "filename": "111.xlsx",
 *          "success": "0",
 *          "timestampCreated": "2018-12-11T18:58:59.276184Z",
 *          "client": "",
 *          "v_client_pk_consigment_num": "8106245243",
 *          "l_000_client_acct_number": 10001,
 *          "l_011_client_warehouse_id": 1,
 *          "l_012_client_warehouse_name": "Hanalt"
 *     }
 *
 * @apiError SignatureError Cannot decode signature or has been already expired.
 *
 * @apiErrorExample Error-Response:
 *     HTTP/1.1 4xx Forbidden
 *     {
 *       "detail": "Error decoding signature."
 *     }
 */

/**
 * @api {get} /bok_1_headers/ Get list of bok_1_headers
 * @apiName GetBok_1
 * @apiGroup Bok_1
 *
 * @apiHeader {String} Authorization "JWT " + JWT_TOKEN.
 * @apiHeader {String} ContentType "application/json".
 *
 * @apiHeaderExample {json} Request-Example:
 *     {
 *       "Authorization": "JWT *****************************",
 *       "Content-Type": "application/json"
 *     }
 *
 * @apiSuccess {Array} Objects Array of bok_1_headers.
 *
 * @apiSuccessExample Success-Response:
 *     HTTP/1.1 200 OK
 *     {
 *         [
 *             {
 *			        "pk_auto_id": 1,
 *			        "client_booking_id": "470c2dc0-0a97-11e9-8c40-06bcff74a362",
 *			        "b_021_b_pu_avail_from_date": "2018-12-28T00:00:00Z",
 *			        "b_003_b_service_name": "R(Road)",
 *			        "b_500_b_client_cust_job_code": "731932",
 *			        "b_054_b_del_company": "DOWLING MCCARTHY TYRES PTY. LTD",
 *			        "b_000_b_total_lines": 2,
 *			        "b_053_b_del_address_street": "66 BASS HIGHWAY",
 *			        "b_058_b_del_address_suburb": "COOEE",
 *			        "b_057_b_del_address_state": "TAS",
 *			        "b_059_b_del_address_postalcode": 7320,
 *			        "v_client_pk_consigment_num": "8106722007",
 *			        "total_kg": 21.434,
 *			        "success": "1",
 *			        "warehouse": "",
 *			        "fk_client_id": "",
 *			        "date_processed": "2018-12-29T19:37:46.308295Z",
 *			        "pk_header_id": "",
 *			        "b_000_1_b_clientReference_RA_Numbers": "",
 *			        "b_000_2_b_price": 0,
 *			        "b_001_b_freight_provider": "",
 *			        "b_002_b_vehicle_type": "",
 *			        "b_005_b_created_for": "",
 *			        "b_006_b_created_for_email": "",
 *			        "b_007_b_ready_status": "",
 *			        "b_008_b_category": "",
 *			        "b_009_b_priority": "",
 *			        "b_010_b_notes": "",
 *			        "b_012_b_driver_bring_connote": false,
 *			        "b_013_b_package_job": false,
 *			        "b_014_b_pu_handling_instructions": "",
 *			        "b_015_b_pu_instructions_contact": "",
 *			        "b_016_b_pu_instructions_address": "",
 *			        "b_017_b_pu_warehouse_num": "",
 *			        "b_018_b_pu_warehouse_bay": "",
 *			        "b_019_b_pu_tail_lift": false,
 *			        "b_020_b_pu_num_operators": 0,
 *			        "b_022_b_pu_avail_from_time_hour": 0,
 *			        "b_023_b_pu_avail_from_time_minute": 0,
 *			        "b_024_b_pu_by_date": "2018-12-29T19:37:19.884587Z",
 *			        "b_025_b_pu_by_time_hour": 0,
 *			        "b_026_b_pu_by_time_minute": 0,
 *			        "b_027_b_pu_address_type": "",
 *			        "b_028_b_pu_company": "",
 *			        "b_029_b_pu_address_street_1": "",
 *			        "b_030_b_pu_address_street_2": "",
 *			        "b_031_b_pu_address_state": "",
 *			        "b_032_b_pu_address_suburb": "",
 *			        "b_033_b_pu_address_postalcode": "",
 *			        "b_034_b_pu_address_country": "",
 *			        "b_035_b_pu_contact_full_name": "",
 *			        "b_036_b_pu_email_group": "",
 *			        "b_037_b_pu_email": "",
 *			        "b_038_b_pu_phone_main": "",
 *			        "b_039_b_pu_phone_mobile": "",
 *			        "b_040_b_pu_communicate_via": "",
 *			        "b_041_b_del_tail_lift": false,
 *			        "b_042_b_del_num_operators": 0,
 *			        "b_043_b_del_instructions_contact": "",
 *			        "b_044_b_del_instructions_address": "",
 *			        "b_045_b_del_warehouse_bay": "",
 *			        "b_046_b_del_warehouse_number": "",
 *			        "b_047_b_del_avail_from_date": "2018-12-29T19:37:34.797670Z",
 *			        "b_048_b_del_avail_from_time_hour": 0,
 *			        "b_049_b_del_avail_from_time_minute": 0,
 *			        "b_050_b_del_by_date": "2018-12-29T19:37:36.687407Z",
 *			        "b_051_b_del_by_time_hour": 0,
 *			        "b_052_b_del_by_time_minute": 0,
 *			        "b_055_b_del_address_street_1": "",
 *			        "b_056_b_del_address_street_2": "",
 *			        "b_060_b_del_address_country": "",
 *			        "b_061_b_del_contact_full_name": "",
 *			        "b_062_b_del_email_group": "",
 *			        "b_063_b_del_email": "",
 *			        "b_064_b_del_phone_main": "",
 *			        "b_065_b_del_phone_mobile": "",
 *			        "b_066_b_del_communicate_via": "",
 *			        "b_500_b_client_UOM": "",
 *			        "b_501_b_client_code": "",
 *			        "pu_addressed_saved": "",
 *			        "b_client_max_book_amount": 0,
 *			        "vx_serviceType_XXX": "",
 *			        "z_createdTimeStamp": "2018-12-29T19:37:50.116039Z"
 *             },
 *             {
 *			        "pk_auto_id": 2,
 *			        "client_booking_id": "470c2dc0-0a97-11e9-8c40-06bcff74a362",
 *			        "b_021_b_pu_avail_from_date": "2018-12-28T00:00:00Z",
 *			        "b_003_b_service_name": "R(Road)",
 *			        "b_500_b_client_cust_job_code": "731932",
 *			        "b_054_b_del_company": "DOWLING MCCARTHY TYRES PTY. LTD",
 *			        "b_000_b_total_lines": 2,
 *			        "b_053_b_del_address_street": "66 BASS HIGHWAY",
 *			        "b_058_b_del_address_suburb": "COOEE",
 *			        "b_057_b_del_address_state": "TAS",
 *			        "b_059_b_del_address_postalcode": 7320,
 *			        "v_client_pk_consigment_num": "8106722007",
 *			        "total_kg": 21.434,
 *			        "success": "1",
 *			        "warehouse": "",
 *			        "fk_client_id": "",
 *			        "date_processed": "2018-12-29T19:37:46.308295Z",
 *			        "pk_header_id": "",
 *			        "b_000_1_b_clientReference_RA_Numbers": "",
 *			        "b_000_2_b_price": 0,
 *			        "b_001_b_freight_provider": "",
 *			        "b_002_b_vehicle_type": "",
 *			        "b_005_b_created_for": "",
 *			        "b_006_b_created_for_email": "",
 *			        "b_007_b_ready_status": "",
 *			        "b_008_b_category": "",
 *			        "b_009_b_priority": "",
 *			        "b_010_b_notes": "",
 *			        "b_012_b_driver_bring_connote": false,
 *			        "b_013_b_package_job": false,
 *			        "b_014_b_pu_handling_instructions": "",
 *			        "b_015_b_pu_instructions_contact": "",
 *			        "b_016_b_pu_instructions_address": "",
 *			        "b_017_b_pu_warehouse_num": "",
 *			        "b_018_b_pu_warehouse_bay": "",
 *			        "b_019_b_pu_tail_lift": false,
 *			        "b_020_b_pu_num_operators": 0,
 *			        "b_022_b_pu_avail_from_time_hour": 0,
 *			        "b_023_b_pu_avail_from_time_minute": 0,
 *			        "b_024_b_pu_by_date": "2018-12-29T19:37:19.884587Z",
 *			        "b_025_b_pu_by_time_hour": 0,
 *			        "b_026_b_pu_by_time_minute": 0,
 *			        "b_027_b_pu_address_type": "",
 *			        "b_028_b_pu_company": "",
 *			        "b_029_b_pu_address_street_1": "",
 *			        "b_030_b_pu_address_street_2": "",
 *			        "b_031_b_pu_address_state": "",
 *			        "b_032_b_pu_address_suburb": "",
 *			        "b_033_b_pu_address_postalcode": "",
 *			        "b_034_b_pu_address_country": "",
 *			        "b_035_b_pu_contact_full_name": "",
 *			        "b_036_b_pu_email_group": "",
 *			        "b_037_b_pu_email": "",
 *			        "b_038_b_pu_phone_main": "",
 *			        "b_039_b_pu_phone_mobile": "",
 *			        "b_040_b_pu_communicate_via": "",
 *			        "b_041_b_del_tail_lift": false,
 *			        "b_042_b_del_num_operators": 0,
 *			        "b_043_b_del_instructions_contact": "",
 *			        "b_044_b_del_instructions_address": "",
 *			        "b_045_b_del_warehouse_bay": "",
 *			        "b_046_b_del_warehouse_number": "",
 *			        "b_047_b_del_avail_from_date": "2018-12-29T19:37:34.797670Z",
 *			        "b_048_b_del_avail_from_time_hour": 0,
 *			        "b_049_b_del_avail_from_time_minute": 0,
 *			        "b_050_b_del_by_date": "2018-12-29T19:37:36.687407Z",
 *			        "b_051_b_del_by_time_hour": 0,
 *			        "b_052_b_del_by_time_minute": 0,
 *			        "b_055_b_del_address_street_1": "",
 *			        "b_056_b_del_address_street_2": "",
 *			        "b_060_b_del_address_country": "",
 *			        "b_061_b_del_contact_full_name": "",
 *			        "b_062_b_del_email_group": "",
 *			        "b_063_b_del_email": "",
 *			        "b_064_b_del_phone_main": "",
 *			        "b_065_b_del_phone_mobile": "",
 *			        "b_066_b_del_communicate_via": "",
 *			        "b_500_b_client_UOM": "",
 *			        "b_501_b_client_code": "",
 *			        "pu_addressed_saved": "",
 *			        "b_client_max_book_amount": 0,
 *			        "vx_serviceType_XXX": "",
 *			        "z_createdTimeStamp": "2018-12-29T19:37:50.116039Z"
 *              }
 *          ]
 *     }
 *
 * @apiError SignatureError Cannot decode signature or has been already expired.
 *
 * @apiErrorExample Error-Response:
 *     HTTP/1.1 4xx Forbidden
 *     {
 *       "detail": "Error decoding signature."
 *     }
 */

/**
 * @api {post} /bok_1_headers/ Insert new bok_1_headers
 * @apiName AddBok_1
 * @apiGroup Bok_1
 *
 * @apiHeader {String} Authorization "JWT " + JWT_TOKEN.
 * @apiHeader {String} ContentType "application/json".
 *
 * @apiHeaderExample {json} Request-Example:
 *     {
 *       "Authorization": "JWT *****************************",
 *       "Content-Type": "application/json"
 *     }
 *
 * @apiParam {JSON} Object bok_1_headers.
 *
 * @apiParamExample {json} Request-Example:
 *      {
 *	        "client_booking_id": "470c2dc0-0a97-11e9-8c40-06bcff74a362",
 *	        "b_021_b_pu_avail_from_date": "2018-12-28T00:00:00Z",
 *	        "b_003_b_service_name": "R(Road)",
 *	        "b_500_b_client_cust_job_code": "731932",
 *	        "b_054_b_del_company": "DOWLING MCCARTHY TYRES PTY. LTD",
 *	        "b_000_b_total_lines": 2,
 *	        "b_053_b_del_address_street": "66 BASS HIGHWAY",
 *	        "b_058_b_del_address_suburb": "COOEE",
 *	        "b_057_b_del_address_state": "TAS",
 *	        "b_059_b_del_address_postalcode": 7320,
 *	        "v_client_pk_consigment_num": "8106722007",
 *	        "total_kg": 21.434,
 *	        "success": "1",
 *	        "warehouse": "",
 *	        "fk_client_id": "",
 *	        "date_processed": "2018-12-29T19:37:46.308295Z",
 *	        "pk_header_id": "",
 *	        "b_000_1_b_clientReference_RA_Numbers": "",
 *	        "b_000_2_b_price": 0,
 *	        "b_001_b_freight_provider": "",
 *	        "b_002_b_vehicle_type": "",
 *	        "b_005_b_created_for": "",
 *	        "b_006_b_created_for_email": "",
 *	        "b_007_b_ready_status": "",
 *	        "b_008_b_category": "",
 *	        "b_009_b_priority": "",
 *	        "b_010_b_notes": "",
 *	        "b_012_b_driver_bring_connote": false,
 *	        "b_013_b_package_job": false,
 *	        "b_014_b_pu_handling_instructions": "",
 *	        "b_015_b_pu_instructions_contact": "",
 *	        "b_016_b_pu_instructions_address": "",
 *	        "b_017_b_pu_warehouse_num": "",
 *	        "b_018_b_pu_warehouse_bay": "",
 *	        "b_019_b_pu_tail_lift": false,
 *	        "b_020_b_pu_num_operators": 0,
 *	        "b_022_b_pu_avail_from_time_hour": 0,
 *	        "b_023_b_pu_avail_from_time_minute": 0,
 *	        "b_024_b_pu_by_date": "2018-12-29T19:37:19.884587Z",
 *	        "b_025_b_pu_by_time_hour": 0,
 *	        "b_026_b_pu_by_time_minute": 0,
 *	        "b_027_b_pu_address_type": "",
 *	        "b_028_b_pu_company": "",
 *	        "b_029_b_pu_address_street_1": "",
 *	        "b_030_b_pu_address_street_2": "",
 *	        "b_031_b_pu_address_state": "",
 *	        "b_032_b_pu_address_suburb": "",
 *	        "b_033_b_pu_address_postalcode": "",
 *	        "b_034_b_pu_address_country": "",
 *	        "b_035_b_pu_contact_full_name": "",
 *	        "b_036_b_pu_email_group": "",
 *	        "b_037_b_pu_email": "",
 *	        "b_038_b_pu_phone_main": "",
 *	        "b_039_b_pu_phone_mobile": "",
 *	        "b_040_b_pu_communicate_via": "",
 *	        "b_041_b_del_tail_lift": false,
 *	        "b_042_b_del_num_operators": 0,
 *	        "b_043_b_del_instructions_contact": "",
 *	        "b_044_b_del_instructions_address": "",
 *	        "b_045_b_del_warehouse_bay": "",
 *	        "b_046_b_del_warehouse_number": "",
 *	        "b_047_b_del_avail_from_date": "2018-12-29T19:37:34.797670Z",
 *	        "b_048_b_del_avail_from_time_hour": 0,
 *	        "b_049_b_del_avail_from_time_minute": 0,
 *	        "b_050_b_del_by_date": "2018-12-29T19:37:36.687407Z",
 *	        "b_051_b_del_by_time_hour": 0,
 *	        "b_052_b_del_by_time_minute": 0,
 *	        "b_055_b_del_address_street_1": "",
 *	        "b_056_b_del_address_street_2": "",
 *	        "b_060_b_del_address_country": "",
 *	        "b_061_b_del_contact_full_name": "",
 *	        "b_062_b_del_email_group": "",
 *	        "b_063_b_del_email": "",
 *	        "b_064_b_del_phone_main": "",
 *	        "b_065_b_del_phone_mobile": "",
 *	        "b_066_b_del_communicate_via": "",
 *	        "b_500_b_client_UOM": "",
 *	        "b_501_b_client_code": "",
 *	        "pu_addressed_saved": "",
 *	        "b_client_max_book_amount": 0,
 *	        "vx_serviceType_XXX": "",
 *	        "z_createdTimeStamp": "2018-12-29T19:37:50.116039Z"
 *     }
 *
 * @apiSuccess {JSON} OBject Return created object.
 *
 * @apiSuccessExample Success-Response:
 *     HTTP/1.1 200 OK
 *      {
 *	        "pk_auto_id": 3,
 *	        "client_booking_id": "470c2dc0-0a97-11e9-8c40-06bcff74a362",
 *	        "b_021_b_pu_avail_from_date": "2018-12-28T00:00:00Z",
 *	        "b_003_b_service_name": "R(Road)",
 *	        "b_500_b_client_cust_job_code": "731932",
 *	        "b_054_b_del_company": "DOWLING MCCARTHY TYRES PTY. LTD",
 *	        "b_000_b_total_lines": 2,
 *	        "b_053_b_del_address_street": "66 BASS HIGHWAY",
 *	        "b_058_b_del_address_suburb": "COOEE",
 *	        "b_057_b_del_address_state": "TAS",
 *	        "b_059_b_del_address_postalcode": 7320,
 *	        "v_client_pk_consigment_num": "8106722007",
 *	        "total_kg": 21.434,
 *	        "success": "1",
 *	        "warehouse": "",
 *	        "fk_client_id": "",
 *	        "date_processed": "2018-12-29T19:37:46.308295Z",
 *	        "pk_header_id": "",
 *	        "b_000_1_b_clientReference_RA_Numbers": "",
 *	        "b_000_2_b_price": 0,
 *	        "b_001_b_freight_provider": "",
 *	        "b_002_b_vehicle_type": "",
 *	        "b_005_b_created_for": "",
 *	        "b_006_b_created_for_email": "",
 *	        "b_007_b_ready_status": "",
 *	        "b_008_b_category": "",
 *	        "b_009_b_priority": "",
 *	        "b_010_b_notes": "",
 *	        "b_012_b_driver_bring_connote": false,
 *	        "b_013_b_package_job": false,
 *	        "b_014_b_pu_handling_instructions": "",
 *	        "b_015_b_pu_instructions_contact": "",
 *	        "b_016_b_pu_instructions_address": "",
 *	        "b_017_b_pu_warehouse_num": "",
 *	        "b_018_b_pu_warehouse_bay": "",
 *	        "b_019_b_pu_tail_lift": false,
 *	        "b_020_b_pu_num_operators": 0,
 *	        "b_022_b_pu_avail_from_time_hour": 0,
 *	        "b_023_b_pu_avail_from_time_minute": 0,
 *	        "b_024_b_pu_by_date": "2018-12-29T19:37:19.884587Z",
 *	        "b_025_b_pu_by_time_hour": 0,
 *	        "b_026_b_pu_by_time_minute": 0,
 *	        "b_027_b_pu_address_type": "",
 *	        "b_028_b_pu_company": "",
 *	        "b_029_b_pu_address_street_1": "",
 *	        "b_030_b_pu_address_street_2": "",
 *	        "b_031_b_pu_address_state": "",
 *	        "b_032_b_pu_address_suburb": "",
 *	        "b_033_b_pu_address_postalcode": "",
 *	        "b_034_b_pu_address_country": "",
 *	        "b_035_b_pu_contact_full_name": "",
 *	        "b_036_b_pu_email_group": "",
 *	        "b_037_b_pu_email": "",
 *	        "b_038_b_pu_phone_main": "",
 *	        "b_039_b_pu_phone_mobile": "",
 *	        "b_040_b_pu_communicate_via": "",
 *	        "b_041_b_del_tail_lift": false,
 *	        "b_042_b_del_num_operators": 0,
 *	        "b_043_b_del_instructions_contact": "",
 *	        "b_044_b_del_instructions_address": "",
 *	        "b_045_b_del_warehouse_bay": "",
 *	        "b_046_b_del_warehouse_number": "",
 *	        "b_047_b_del_avail_from_date": "2018-12-29T19:37:34.797670Z",
 *	        "b_048_b_del_avail_from_time_hour": 0,
 *	        "b_049_b_del_avail_from_time_minute": 0,
 *	        "b_050_b_del_by_date": "2018-12-29T19:37:36.687407Z",
 *	        "b_051_b_del_by_time_hour": 0,
 *	        "b_052_b_del_by_time_minute": 0,
 *	        "b_055_b_del_address_street_1": "",
 *	        "b_056_b_del_address_street_2": "",
 *	        "b_060_b_del_address_country": "",
 *	        "b_061_b_del_contact_full_name": "",
 *	        "b_062_b_del_email_group": "",
 *	        "b_063_b_del_email": "",
 *	        "b_064_b_del_phone_main": "",
 *	        "b_065_b_del_phone_mobile": "",
 *	        "b_066_b_del_communicate_via": "",
 *	        "b_500_b_client_UOM": "",
 *	        "b_501_b_client_code": "",
 *	        "pu_addressed_saved": "",
 *	        "b_client_max_book_amount": 0,
 *	        "vx_serviceType_XXX": "",
 *	        "z_createdTimeStamp": "2018-12-29T19:37:50.116039Z"
 *     }
 *
 * @apiError SignatureError Cannot decode signature or has been already expired.
 *
 * @apiErrorExample Error-Response:
 *     HTTP/1.1 4xx Forbidden
 *     {
 *       "detail": "Error decoding signature."
 *     }
 */

/**
 * @api {get} /bok_2_lines/ Get list of bok_2_lines
 * @apiName GetBok_2
 * @apiGroup Bok_2
 *
 * @apiHeader {String} Authorization "JWT " + JWT_TOKEN.
 * @apiHeader {String} ContentType "application/json".
 *
 * @apiHeaderExample {json} Request-Example:
 *     {
 *       "Authorization": "JWT *****************************",
 *       "Content-Type": "application/json"
 *     }
 *
 * @apiSuccess {Array} Objects Array of bok_2_lines.
 *
 * @apiSuccessExample Success-Response:
 *     HTTP/1.1 200 OK
 *     {
 *         [
 *             {
 *                  "pk_auto_id": 1,
 *                  "client_booking_id": 2,
 *                  "l_501_client_UOM": "100",
 *                  "l_009_weight_per_each": 10,
 *                  "l_010_totaldim": 1,
 *                  "l_500_client_run_code": "1",
 *                  "l_003_item": "Box",
 *                  "v_client_pk_consigment_num": "310010",
 *                  "l_cubic_weight": 10,
 *                  "l_002_qty": 0,
 *                  "success": 0,
 *                  "fk_header_id": 10,
 *                  "e_pallet_type": "pallet type 0",
 *                  "e_item_type": "item type 0",
 *                  "e_item_type_new": "item type new",
 *                  "date_processed": "date parocessed",
 *                  "l_001_type_of_packaging": "type of packaging",
 *                  "l_005_dim_length": 20,
 *                  "l_006_dim_width": 10,
 *                  "l_007_dim_height": 10,
 *                  "l_008_weight_UOM": 100,
 *                  "l_009_weight_per_each_original": "Kgs",
 *                  "l_500_b_client_cust_job_code": "001",
 *                  "z_createdTimeStamp": "2018-12-11T18:58:59.276184Z"
 *              },
 *             {
 *                  "pk_auto_id": 2,
 *                  "client_booking_id": 2,
 *                  "l_501_client_UOM": "100",
 *                  "l_009_weight_per_each": 10,
 *                  "l_010_totaldim": 1,
 *                  "l_500_client_run_code": "1",
 *                  "l_003_item": "Box",
 *                  "v_client_pk_consigment_num": "310010",
 *                  "l_cubic_weight": 10,
 *                  "l_002_qty": 0,
 *                  "success": 0,
 *                  "fk_header_id": 10,
 *                  "e_pallet_type": "pallet type 0",
 *                  "e_item_type": "item type 0",
 *                  "e_item_type_new": "item type new",
 *                  "date_processed": "date parocessed",
 *                  "l_001_type_of_packaging": "type of packaging",
 *                  "l_005_dim_length": 20,
 *                  "l_006_dim_width": 10,
 *                  "l_007_dim_height": 10,
 *                  "l_008_weight_UOM": 100,
 *                  "l_009_weight_per_each_original": "Kgs",
 *                  "l_500_b_client_cust_job_code": "001",
 *                  "z_createdTimeStamp": "2018-12-11T18:58:59.276184Z"
 *              }
 *          ]
 *     }
 *
 * @apiError SignatureError Cannot decode signature or has been already expired.
 *
 * @apiErrorExample Error-Response:
 *     HTTP/1.1 4xx Forbidden
 *     {
 *       "detail": "Error decoding signature."
 *     }
 */

/**
 * @api {post} /bok_2_lines/ Insert new bok_2_lines
 * @apiName AddBok_2
 * @apiGroup Bok_2
 *
 * @apiHeader {String} Authorization "JWT " + JWT_TOKEN.
 * @apiHeader {String} ContentType "application/json".
 *
 * @apiHeaderExample {json} Request-Example:
 *     {
 *       "Authorization": "JWT *****************************",
 *       "Content-Type": "application/json"
 *     }
 *
 * @apiParam {JSON} Object bok_2_lines.
 *
 * @apiParamExample {json} Request-Example:
 *      {
 *          "client_booking_id": 2,
 *          "l_501_client_UOM": "100",
 *          "l_009_weight_per_each": 10,
 *          "l_010_totaldim": 1,
 *          "l_500_client_run_code": "1",
 *          "l_003_item": "Box",
 *          "v_client_pk_consigment_num": "310010",
 *          "l_cubic_weight": 10,
 *          "l_002_qty": 0,
 *          "success": 0,
 *          "fk_header_id": 10,
 *          "e_pallet_type": "pallet type 0",
 *          "e_item_type": "item type 0",
 *          "e_item_type_new": "item type new",
 *          "date_processed": "date parocessed",
 *          "l_001_type_of_packaging": "type of packaging",
 *          "l_005_dim_length": 20,
 *          "l_006_dim_width": 10,
 *          "l_007_dim_height": 10,
 *          "l_008_weight_UOM": 100,
 *          "l_009_weight_per_each_original": "Kgs",
 *          "l_500_b_client_cust_job_code": "001",
 *          "z_createdTimeStamp": "2018-12-11T18:58:59.276184Z"
 *      }
 *
 * @apiSuccess {JSON} OBject Return created object.
 *
 * @apiSuccessExample Success-Response:
 *     HTTP/1.1 200 OK
 *      {
 *          "pk_auto_id": 1,
 *          "client_booking_id": 2,
 *          "l_501_client_UOM": "100",
 *          "l_009_weight_per_each": 10,
 *          "l_010_totaldim": 1,
 *          "l_500_client_run_code": "1",
 *          "l_003_item": "Box",
 *          "v_client_pk_consigment_num": "310010",
 *          "l_cubic_weight": 10,
 *          "l_002_qty": 0,
 *          "success": 0,
 *          "fk_header_id": 10,
 *          "e_pallet_type": "pallet type 0",
 *          "e_item_type": "item type 0",
 *          "e_item_type_new": "item type new",
 *          "date_processed": "date parocessed",
 *          "l_001_type_of_packaging": "type of packaging",
 *          "l_005_dim_length": 20,
 *          "l_006_dim_width": 10,
 *          "l_007_dim_height": 10,
 *          "l_008_weight_UOM": 100,
 *          "l_009_weight_per_each_original": "Kgs",
 *          "l_500_b_client_cust_job_code": "001",
 *          "z_createdTimeStamp": "2018-12-11T18:58:59.276184Z"
 *      }
 *
 * @apiError SignatureError Cannot decode signature or has been already expired.
 *
 * @apiErrorExample Error-Response:
 *     HTTP/1.1 4xx Forbidden
 *     {
 *       "detail": "Error decoding signature."
 *     }
 */
