from pathlib import Path

from django.contrib import admin
from django.conf import settings
from django.conf.urls.static import static
from django.http import FileResponse, HttpResponse
from django.urls import path, include, re_path


def spa_index(request):
    """Serve the React SPA for any route that isn't /api/ or /admin/.
    In local dev you use the Vite server (port 5173) so this view is never hit.
    In production (Railway) Django serves everything from one process.
    """
    index_path = Path(settings.BASE_DIR) / 'frontend_build' / 'index.html'
    if not index_path.exists():
        return HttpResponse(
            '<h1>Frontend not built</h1>'
            '<p>Run: <code>cd frontend && npm run build && cp -r dist ../backend/frontend_build</code></p>',
            content_type='text/html',
            status=200,
        )
    return FileResponse(open(index_path, 'rb'), content_type='text/html')


urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/', include('esg.urls')),
    # Catch-all: must be last. Sends every other URL to the React app.
    re_path(r'^.*$', spa_index),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
