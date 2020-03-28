from api.models import API_booking_quotes

def analyse_booking_quotes_table(bookingIds):
    analyses = {}
    results = []
    num_no_pricing = 0
    for bookingId in bookingIds:
        print('bookingId', bookingId)
        api_booking_quotes = API_booking_quotes.objects.filter(fk_booking_id = bookingId)

        if len(api_booking_quotes) == 0:
            num_no_pricing = num_no_pricing + 1

        for api_booking_quote in api_booking_quotes:
            print('api_booking_quote', api_booking_quote)

            if not api_booking_quote.fk_freight_provider_id in analyses:
                fp_analyses = {}
                fp_analyses['*'] = {
                    "count": 1,
                    "min_price": api_booking_quote.fee,
                    "avg_price": api_booking_quote.fee,
                    "max_price": api_booking_quote.fee,
                }
            else:
                fp_analyses = analyses[api_booking_quote.fk_freight_provider_id]
                all_fp_analysis = fp_analyses["*"] 
                if api_booking_quote.fee > all_fp_analysis["max_price"]:
                    all_fp_analysis["max_price"] = api_booking_quote.fee

                if api_booking_quote.fee < all_fp_analysis["min_price"]:                    
                    all_fp_analysis["min_price"] = api_booking_quote.fee

                all_fp_analysis["avg_price"] = (
                    (all_fp_analysis["avg_price"] * all_fp_analysis["count"] + api_booking_quote.fee )
                    / 
                    (all_fp_analysis["count"] + 1)
                )
                all_fp_analysis["count"] = all_fp_analysis["count"] + 1
                fp_analyses["*"] = all_fp_analysis

            if api_booking_quote.service_name in fp_analyses:
                service_analysis = fp_analyses[api_booking_quote.service_name]

                if api_booking_quote.fee > service_analysis["max_price"]:
                    service_analysis["max_price"] = api_booking_quote.fee

                if api_booking_quote.fee < service_analysis["min_price"]:                    
                    service_analysis["min_price"] = api_booking_quote.fee

                service_analysis["avg_price"] = (
                    (service_analysis["avg_price"] * service_analysis["count"] + api_booking_quote.fee )
                    / 
                    (service_analysis["count"] + 1)
                )

                service_analysis["count"] = service_analysis["count"] + 1
                fp_analyses[api_booking_quote.service_name] = service_analysis

            # else if api_booking_quote.service_name is not None:
            # Not sure how we can handle service name is None
            else:
                service_analysis = {
                    "count": 1,
                    "min_price": api_booking_quote.fee,
                    "avg_price": api_booking_quote.fee,
                    "max_price": api_booking_quote.fee,
                }


            fp_analyses[api_booking_quote.service_name] = service_analysis
            analyses[api_booking_quote.fk_freight_provider_id] = fp_analyses

    results.append({ 
    	"fp_name": "No-Pricing", 
    	"count" : num_no_pricing ,
    	"min_price": "0",
    	"avg_price": "0",
    	"max_price": "0",
    })

    for fp_name in analyses:
        fp_analyses = analyses[fp_name]

        for service_name in fp_analyses:
            print(service_name)
            service_analysis = fp_analyses[service_name]

            result = {}
            result["fp_name"] = fp_name
            result["service_name"] = service_name
            result["count"] = service_analysis["count"]
            result["min_price"] = service_analysis["min_price"]
            result["avg_price"] = service_analysis["avg_price"]
            result["max_price"] = service_analysis["max_price"]

            results.append(result)
            print(service_analysis)

    return results