class ContentSecurityPolicyMiddleware:
    """
    Le Grin ne charge rien depuis l'extérieur : scripts, styles, polices et images
    viennent tous de ce serveur. On le dit au navigateur, qui bloquera donc tout
    script injecté même si une faille d'échappement passait un jour.
    """

    POLICY = (
        "default-src 'self'; "
        "img-src 'self' data: blob:; "
        "style-src 'self' 'unsafe-inline'; "
        "object-src 'none'; base-uri 'self'; form-action 'self'; frame-ancestors 'none'"
    )

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        response.headers.setdefault("Content-Security-Policy", self.POLICY)
        return response
