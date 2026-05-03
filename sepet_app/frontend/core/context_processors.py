from datetime import datetime

def inject_globals(request):
    """Injects global variables into all templates."""
    return {
        'current_year': datetime.now().year,
        'canonical_url': request.build_absolute_uri(),
    }
