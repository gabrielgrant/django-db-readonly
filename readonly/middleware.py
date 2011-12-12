from .exceptions import DatabaseWriteDenied
from django.conf import settings
from django.http import HttpResponse
from django.utils.encoding import iri_to_uri
from django.views.generic import TemplateView

class HttpResponseReload(HttpResponse):
    """
    Reload page and stay on the same page from where request was made.
    """
    status_code = 302
    
    def __init__(self, request):
        HttpResponse.__init__(self)
        referer = request.META.get('HTTP_REFERER')
        self['Location'] = iri_to_uri(referer or "/")


class DatabaseReadOnlyMiddleware(object):
    def process_exception(self, request, exception):
        # Only process DatabaseWriteDenied exceptions
        if not isinstance(exception, DatabaseWriteDenied):
            return None
        
        # Handle the exception
        if request.method == 'POST':
            if getattr(settings, 'DB_READ_ONLY_MIDDLEWARE_MESSAGE', False):
                from django.contrib import messages
                messages.error(request, 'The site is currently in read-only '
                    'mode. Please try editing later.')
            
            # Try to redirect to this page's GET version
            return HttpResponseReload(request)
        else:
            # We can't do anything about this error
            return HttpResponse('The site is currently in read-only mode. '
                'Please try again later.')

class ReadOnlyTemplateView(TemplateView):
    template_name = 'readonly/readonly.html'
    def get_template_names(self):
        template_names = []
        if self.request.method == 'GET':
            get_template = getattr(settings, 'DB_READ_ONLY_GET_TEMPLATE_NAME', None)
            template_names.append(get_template)
            template_names.append('readonly/get.html')
        else:
            post_template = getattr(settings, 'DB_READ_ONLY_POST_TEMPLATE_NAME', None)
            template_names.append(post_template)
            template_names.append('readonly/post.html')
        default_template = getattr(settings, 'DB_READ_ONLY_TEMPLATE_NAME', None)
        template_names.append(default_template)
        template_names = [t for t in template_names if t]  # filter "None"s
        template_names.extend(super(ReadOnlyTemplateView, self).get_template_names())
        return template_names

    # other handle methods the same as get
    def head(self, request, *args, **kwargs):
        return self.get(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        return self.get(request, *args, **kwargs)

    def options(self, request, *args, **kwargs):
        return self.get(request, *args, **kwargs)

    def delete(self, request, *args, **kwargs):
        return self.get(request, *args, **kwargs)

    def put(self, request, *args, **kwargs):
        return self.get(request, *args, **kwargs)

class DatabaseReadOnlyViewMiddleware(object):
    view_class = ReadOnlyTemplateView
    def process_exception(self, request, exception):
        if isinstance(exception, DatabaseWriteDenied):
            # Only handle the correct exceptions
            return self.view_class.as_view()(request)
