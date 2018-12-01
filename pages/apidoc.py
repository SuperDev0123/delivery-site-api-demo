"""
@api {post} /user/login/ User login
@apiName login
@apiGroup User

@apiParam {String} username Users unique name.
@apiParam {String} password Users password.

@apiSuccess {String} token JWT_TOKEN.

@apiSuccessExample Success-Response:
    HTTP/1.1 200 OK
    {
      "token": JWT_TOKEN
    }

@apiError UserNotFound The id of the User was not found.

@apiErrorExample Error-Response:
    HTTP/1.1 404 Not Found
    {
       "error": "UserNotFound"
    }
"""

"""
@api {get} /booking/ Booking detail
@apiName booking
@apiGroup Booking

@apiParam {String} id Id of Booking.
@apiParam {String} token JWT_TOKEN.

@apiSuccess {JSON} booking Booking object.

@apiSuccessExample Success-Response:
    HTTP/1.1 200 OK
    {
      "booking": {
      	name: '***',
      	author: '***',
      	...
      }
    }

@apiError BookingNotFound The id of the Booking was not found.

@apiErrorExample Error-Response:
    HTTP/1.1 404 Not Found
    {
       "error": "Booking Not Found"
    }
"""

"""
@api {get} /allbookings/ Bookings list
@apiName allbookings
@apiGroup Booking

@apiParam {String} token JWT_TOKEN.
@apiSuccess {JSON} booking Booking object.

@apiSuccessExample Success-Response:
    HTTP/1.1 200 OK
    {
      "allbookings": [
      	{
	      	name: '***',
	      	author: '***',
	      	...
	    },
	    {
	      	name: '***',
	      	author: '***',
	      	...
	    }
      ]	
    }

@apiError NoBookings No Bookings.

@apiErrorExample Error-Response:
    HTTP/1.1 404 Not Found
    {
       "error": "NoBookings"
    }
"""

"""
@api {post} /share/upload/ Upload a file
@apiName upload
@apiGroup Upload

@apiParam {String} token JWT_TOKEN.
@apiParam {BLOB} file File to upload.

@apiSuccess {String} name File name(prepend).

@apiError Upload Failed.

@apiErrorExample Error-Response:
    HTTP/1.1 404 Not Found
    {
       "error": "UploadFailed"
    }
"""

"""
@api {get} /share/upload/status/ Get status of uploaded file
@apiName upload_status
@apiGroup Upload

@apiParam {String} token JWT_TOKEN.
@apiParam {String} name File name.

@apiSuccess {Number} status_code Status of uploaded file.
@apiSuccess {error} [error] Error list of uploaded file.

@apiSuccessExample Success-Response:
    HTTP/1.1 200 OK
    {
      "status_code": 0,
      "error": ["Shipping To field shouldn't be empty - B90", ...]
    }
"""