from django.http import HttpResponseBadRequest


class SecurityPolicyMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if len(request.META.get("HTTP_ACCEPT_LANGUAGE", "")) > 500:
            return HttpResponseBadRequest("Invalid language header.")
        request.language = request.session.get("language", "en")
        if request.language not in ("en", "mr", "hi"):
            request.language = "en"
        response = self.get_response(request)
        response["Content-Security-Policy"] = (
            "default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; font-src 'self'; connect-src 'self'; media-src 'self' blob:; frame-src 'none'; frame-ancestors 'none'; object-src 'none'; base-uri 'self'; form-action 'self'"
        )
        if request.path.startswith("/appointments/") and request.path.endswith("/pay/"):
            # Razorpay Checkout is loaded only on the explicit payment page.
            response["Content-Security-Policy"] = (
                "default-src 'self'; script-src 'self' https://checkout.razorpay.com; style-src 'self' 'unsafe-inline'; img-src 'self' data: https://*.razorpay.com; font-src 'self'; connect-src 'self' https://api.razorpay.com; media-src 'self' blob:; frame-src https://api.razorpay.com https://checkout.razorpay.com; frame-ancestors 'none'; object-src 'none'; base-uri 'self'; form-action 'self'"
            )
        response["Referrer-Policy"] = "no-referrer"
        response["Permissions-Policy"] = (
            "camera=(self), microphone=(self), geolocation=(), payment=()"
        )
        response["Cross-Origin-Opener-Policy"] = "same-origin"
        response["X-Content-Type-Options"] = "nosniff"
        if not request.path.startswith("/static/"):
            response["Cache-Control"] = "no-store, private"
        return response
